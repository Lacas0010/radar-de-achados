import re
import statistics
from typing import List, Dict, Any, Optional
from models.item import Anuncio
from engine.nlp_parser import extract_submodels_and_specs
from engine.geo import analyze_location_proximity

DEFAULT_EXCLUDE_KEYWORDS = [
    "com defeito",
    "para pecas",
    "para peças",
    "sucata",
    "bloqueado",
    "bloqueio",
    "icloud",
    "quebrado",
    "tela trincada",
    "compro",
    "compramos",
    "procuro",
    "so a carcaça",
    "só carcaça",
    "so a caixa",
    "só a caixa",
    "caixa vazia",
    "nao liga",
    "não liga"
]

def parse_price(price_str: str) -> float:
    """Converte string de preço (ex: 'R$ 2.450,00' ou 'R$ 399') em float."""
    if not price_str:
        return 0.0
    cleaned = re.sub(r'[^\d,]', '', price_str)
    if ',' in cleaned:
        cleaned = cleaned.replace('.', '').replace(',', '.')
    else:
        cleaned = cleaned.replace('.', '')
    try:
        return float(cleaned)
    except:
        return 0.0

def format_currency(val: float) -> str:
    """Formata float em padrão brasileiro R$ 1.234,00"""
    return f"R$ {val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def calculate_iqr_thresholds(prices: List[float]) -> Dict[str, float]:
    """
    Calcula Quartis (Q1, Q3), Intervalo Interquartil (IQR = Q3 - Q1)
    e Limiar Inferior de Outliers (Q1 - 1.5 * IQR) usando cluster típico
    para evitar que o próprio outlier infle o IQR em amostras pequenas.
    """
    if not prices:
        return {"q1": 0.0, "q3": 0.0, "iqr": 0.0, "lower_bound": 0.0, "upper_bound": 0.0}

    med = statistics.median(prices)
    
    # Amostra de referência sem outliers extremos iniciais (< 30% da mediana)
    clean_sample = [p for p in prices if p >= (med * 0.30)]
    if len(clean_sample) < 4:
        clean_sample = prices

    if len(clean_sample) < 4:
        return {
            "q1": round(med * 0.85, 2),
            "q3": round(med * 1.15, 2),
            "iqr": round(med * 0.30, 2),
            "lower_bound": round(med * 0.55, 2),
            "upper_bound": round(med * 1.6, 2)
        }

    try:
        q1, q2, q3 = statistics.quantiles(clean_sample, n=4)
    except:
        sorted_p = sorted(clean_sample)
        n = len(sorted_p)
        q1 = sorted_p[int(n * 0.25)]
        q3 = sorted_p[int(n * 0.75)]

    iqr = max(q3 - q1, 0.0)
    lower_bound = round(max(q1 - (1.5 * iqr), med * 0.45), 2)
    upper_bound = round(q3 + (1.5 * iqr), 2)

    return {
        "q1": round(q1, 2),
        "q3": round(q3, 2),
        "iqr": round(iqr, 2),
        "lower_bound": lower_bound,
        "upper_bound": upper_bound
    }

def analyze_and_rank_listings(
    listings: List[Anuncio],
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    exclude_keywords: Optional[List[str]] = None,
    sort_by: str = "price_asc",
    ignore_fake_prices: bool = True,
    uf: str = "df"
) -> Dict[str, Any]:
    """
    Filtra, extrai tokens de submodelo por NLP/Regex, analisa geografia real,
    calcula IQR para detecção de golpes/outliers e ranqueia as melhores ofertas.
    """
    if exclude_keywords is None:
        exclude_keywords = DEFAULT_EXCLUDE_KEYWORDS
    else:
        exclude_keywords = [k.lower().strip() for k in exclude_keywords if k.strip()]

    filtered: List[Anuncio] = []

    for item in listings:
        titulo_lower = item.titulo.lower()
        
        # 1. Filtro de palavras negativas com proteção para 'desbloqueado'
        has_negative = False
        for neg in exclude_keywords:
            if neg in ["bloqueado", "bloqueio"]:
                if re.search(r"(?<!des)\bbloquead[oa]s?\b", titulo_lower):
                    has_negative = True
                    break
            elif re.search(r"\b" + re.escape(neg) + r"\b", titulo_lower):
                has_negative = True
                break

        if has_negative:
            continue

        # 2. Filtro de preços falsos (R$ 0, R$ 1, R$ 2, etc.)
        if ignore_fake_prices and item.preco <= 10.0:
            continue

        # 3. Filtro de faixa de preço definido pelo usuário
        if min_price is not None and item.preco < min_price:
            continue
        if max_price is not None and item.preco > max_price:
            continue

        # 4. Enriquecimento com Detecção de Submodelos e Specs por Regex/NLP
        item.submodelos = extract_submodels_and_specs(item.titulo)

        # 5. Enriquecimento de Raio Geográfico e Proximidade
        zona_nome, nivel_dist = analyze_location_proximity(item.localizacao, state_uf=uf)
        item.zona_geografica = zona_nome
        item.nivel_distancia = nivel_dist

        filtered.append(item)

    if not filtered:
        return {
            "items": [],
            "stats": {
                "total": 0,
                "min_price": 0.0,
                "max_price": 0.0,
                "median_price": 0.0,
                "avg_price": 0.0,
                "super_deals_count": 0,
                "suspicious_count": 0,
                "q1": 0.0,
                "q3": 0.0,
                "iqr": 0.0,
                "lower_bound_iqr": 0.0
            },
            "available_submodels": []
        }

    prices = [it.preco for it in filtered]
    median_val = statistics.median(prices)
    avg_val = statistics.mean(prices)
    min_val = min(prices)
    max_val = max(prices)

    # Cálculo da Margem de Segurança por Desvio Interquartil (IQR)
    iqr_data = calculate_iqr_thresholds(prices)
    lower_bound = iqr_data["lower_bound"]

    super_deals = 0
    suspicious_count = 0
    all_submodels_set = set()

    # Classificação com proteção contra Outliers / Golpes
    for item in filtered:
        for tag in (item.submodelos or []):
            all_submodels_set.add(tag)

        # Verificação de Golpe / Anúncio Suspeito via IQR
        # Se o preço for absurdamente menor que o limiar inferior estatístico
        if item.preco < lower_bound and item.preco < (median_val * 0.40):
            item.is_suspeito = True
            item.motivo_suspeita = f"Preço de R$ {item.preco:,.2f} é outlier inferior (< R$ {lower_bound:,.2f}). Alta probabilidade de anúncio fraudulento."
            item.classificacao = "⚠️ POSSÍVEL GOLPE / SUSPEITO"
            item.desconto_percentual = round(((median_val - item.preco) / median_val) * 100.0, 1) if median_val > 0 else 0.0
            suspicious_count += 1
            continue

        item.is_suspeito = False

        if median_val > 0:
            discount_pct = ((median_val - item.preco) / median_val) * 100.0
            item.desconto_percentual = round(discount_pct, 1)

            if discount_pct >= 28.0:
                item.classificacao = "🔥 SUPER ACHADO"
                super_deals += 1
            elif discount_pct >= 14.0:
                item.classificacao = "💎 ÓTIMO PREÇO"
            elif discount_pct >= -12.0:
                item.classificacao = "⚖️ PREÇO DE MERCADO"
            else:
                item.classificacao = "⚠️ ACIMA DA MÉDIA"
        else:
            item.desconto_percentual = 0.0
            item.classificacao = "⚖️ PREÇO DE MERCADO"

    # Ordenação
    if sort_by == "price_asc":
        filtered.sort(key=lambda x: x.preco)
    elif sort_by == "price_desc":
        filtered.sort(key=lambda x: x.preco, reverse=True)
    elif sort_by == "best_deal":
        filtered.sort(key=lambda x: (not x.is_suspeito, x.desconto_percentual or 0.0), reverse=True)
    elif sort_by == "price_drop":
        filtered.sort(key=lambda x: (x.variacao_preco or 0.0))

    return {
        "items": [it.to_dict() for it in filtered],
        "stats": {
            "total": len(filtered),
            "min_price": min_val,
            "max_price": max_val,
            "median_price": round(median_val, 2),
            "avg_price": round(avg_val, 2),
            "super_deals_count": super_deals,
            "suspicious_count": suspicious_count,
            "q1": iqr_data["q1"],
            "q3": iqr_data["q3"],
            "iqr": iqr_data["iqr"],
            "lower_bound_iqr": iqr_data["lower_bound"]
        },
        "available_submodels": sorted(list(all_submodels_set))
    }
