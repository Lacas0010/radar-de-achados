import sys
import argparse
import statistics
import concurrent.futures
from typing import List, Optional
from models.item import Anuncio
from core.olx_scraper import scrape_olx
from core.fb_marketplace import scrape_facebook_marketplace, salvar_sessao_facebook
from core.database import processar_e_salvar_anuncios, obter_estatisticas_banco

DEFAULT_IGNORE_WORDS = [
    "compro",
    "procuro",
    "troco",
    "troca",
    "defeito",
    "sucata",
    "quebrado",
    "bloqueado",
    "pecas",
    "peças",
    "icloud",
    "só carcaça",
    "so a caixa",
    "caixa vazia"
]

def buscar_itens(
    termo: str,
    uf: str = "df",
    preco_min: float = 0.0,
    preco_max: Optional[float] = None,
    ignorar_palavras: Optional[List[str]] = None,
    fontes: Optional[List[str]] = None,
    apenas_novos: bool = False
) -> List[Anuncio]:
    """
    Função principal que orquestra a busca concorrente na OLX e Facebook Marketplace,
    normaliza os anúncios, aplica filtros, calcula a mediana e persiste no SQLite
    para identificar novidades em cada varredura.
    """
    if fontes is None:
        fontes = ["olx", "facebook"]

    ignorar = [p.lower().strip() for p in (ignorar_palavras or DEFAULT_IGNORE_WORDS)]
    todos_anuncios: List[Anuncio] = []

    print(f"\n[Radar] Buscando '{termo}' no estado/região '{uf.upper()}'...")
    if preco_min > 0 or preco_max is not None:
        print(f"[Radar] Filtro de preço: R$ {preco_min:.2f} até R$ {preco_max or 'Sem limite'}")

    # Execução concorrente em paralelo com Playwright Stealth
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futuros = {}
        if "olx" in fontes:
            futuros[executor.submit(scrape_olx, termo, uf, preco_min, preco_max)] = "OLX"
        if "facebook" in fontes:
            futuros[executor.submit(scrape_facebook_marketplace, termo, uf, preco_min, preco_max)] = "Facebook"

        for fut in concurrent.futures.as_completed(futuros):
            origem = futuros[fut]
            try:
                res = fut.result()
                todos_anuncios.extend(res)
            except Exception as e:
                print(f"[Aviso] Falha ao consultar {origem}: {e}")

    if not todos_anuncios:
        return []

    # 1. Análise Estatística Avançada (IQR), Regex/NLP de Submodelos e Mapeamento Geográfico
    from engine.analyzer import analyze_and_rank_listings
    analysis_result = analyze_and_rank_listings(
        listings=todos_anuncios,
        min_price=preco_min if preco_min > 0 else None,
        max_price=preco_max,
        exclude_keywords=ignorar,
        sort_by="price_asc",
        ignore_fake_prices=True,
        uf=uf
    )
    
    anuncios_analisados: List[Anuncio] = []
    for it in analysis_result["items"]:
        anuncio_obj = Anuncio(
            titulo=it["title"],
            preco=it["price"],
            localizacao=it["location"],
            url=it["url"],
            plataforma=it["source"],
            imagem_url=it.get("image") or None,
            imagens=it.get("images") or [],
            data_publicacao=it.get("date_posted") or None,
            desconto_percentual=it.get("deal_score") or 0.0,
            classificacao=it.get("classificacao") or ("⚠️ POSSÍVEL GOLPE / SUSPEITO" if it.get("is_suspicious") else "⚖️ PREÇO DE MERCADO"),
            id=it.get("id"),
            submodelos=it.get("submodels") or [],
            zona_geografica=it.get("geo_zone"),
            nivel_distancia=it.get("distance_level") or "central",
            is_suspeito=it.get("is_suspicious", False),
            motivo_suspeita=it.get("suspicious_reason")
        )
        anuncios_analisados.append(anuncio_obj)

    # 2. Persistência Leve (SQLite): Processa, identifica itens novos e histórico de variações
    anuncios_processados, total_novos = processar_e_salvar_anuncios(anuncios_analisados)
    print(f"[Banco SQLite] {total_novos} novos anúncios registrados nesta varredura.")

    # 3. Filtro opcional: listar apenas o que é novidade
    if apenas_novos:
        anuncios_processados = [a for a in anuncios_processados if a.is_novo]

    # Ordena pelo menor preço
    anuncios_processados.sort(key=lambda x: x.preco)
    return anuncios_processados

def main():
    parser = argparse.ArgumentParser(description="Achador de Itens Usados - OLX & Facebook Marketplace")
    parser.add_argument("--termo", "-t", type=str, default=None, help="Termo de pesquisa (ex: 'ps5', 'iphone 13')")
    parser.add_argument("--uf", "-u", type=str, default="sp", help="UF ou Estado (ex: 'sp', 'df', 'rj', 'mg', 'pr')")
    parser.add_argument("--min", type=float, default=0.0, help="Preço mínimo em R$")
    parser.add_argument("--max", type=float, default=None, help="Preço máximo em R$")
    parser.add_argument("--ignorar", nargs="+", default=None, help="Palavras a ignorar")
    parser.add_argument("--fontes", nargs="+", default=["olx", "facebook"], choices=["olx", "facebook"])
    parser.add_argument("--apenas-novos", action="store_true", help="Exibe apenas anúncios que são novidade desde a última varredura")
    parser.add_argument("--salvar-sessao-fb", action="store_true", help="Abre o navegador para autenticar e salvar sessão do Facebook")

    args = parser.parse_args()

    if args.salvar_sessao_fb:
        salvar_sessao_facebook()
        sys.exit(0)

    # Modo Interativo Amigável se o usuário não passar argumentos via terminal
    termo = args.termo
    uf = args.uf
    preco_min = args.min
    preco_max = args.max
    apenas_novos = args.apenas_novos

    if not termo:
        print("=" * 70)
        print("   RADAR DE ACHADOS | OLX & FACEBOOK MARKETPLACE")
        print("=" * 70)
        try:
            termo = input("\nO que você deseja buscar? (ex: ps5, iphone 13): ").strip()
            if not termo:
                print("Nenhum termo informado. Encerrando.")
                return
            
            uf_in = input("Qual o estado/UF? (ex: sp, df, rj, mg, pr) [Padrão: sp]: ").strip()
            if uf_in:
                uf = uf_in.lower()

            min_in = input("Preço mínimo em R$ (ENTER para sem mínimo): ").strip()
            if min_in:
                try:
                    preco_min = float(min_in.replace(',', '.'))
                except:
                    pass

            max_in = input("Preço máximo em R$ (ENTER para sem limite): ").strip()
            if max_in:
                try:
                    preco_max = float(max_in.replace(',', '.'))
                except:
                    pass

            novos_in = input("Listar apenas itens que são novidade? (s/N): ").strip().lower()
            if novos_in in ["s", "sim", "y", "yes"]:
                apenas_novos = True

        except (KeyboardInterrupt, EOFError):
            print("\nOperação cancelada.")
            return

    anuncios = buscar_itens(
        termo=termo,
        uf=uf,
        preco_min=preco_min,
        preco_max=preco_max,
        ignorar_palavras=args.ignorar,
        fontes=args.fontes,
        apenas_novos=apenas_novos
    )

    print("\n" + "=" * 75)
    print(f"  RESULTADOS: {len(anuncios)} ANÚNCIOS ENCONTRADOS" + (" (APENAS NOVIDADES)" if apenas_novos else ""))
    print("=" * 75)

    if not anuncios:
        print("Nenhum anúncio encontrado com os critérios fornecidos.")
        return

    for idx, a in enumerate(anuncios, 1):
        desc_info = f"({a.desconto_percentual}% off)" if a.desconto_percentual and a.desconto_percentual > 0 else ""
        novo_badge = "[✨ NOVO NO RADAR] " if a.is_novo else ""
        print(f"\n#{idx} {novo_badge}[{a.plataforma}] R$ {a.preco:,.2f} | {a.classificacao} {desc_info}")
        print(f"   Título: {a.titulo}")
        print(f"   Local : {a.localizacao}")
        print(f"   Link  : {a.url}")

    print("\n" + "=" * 75 + "\n")

if __name__ == "__main__":
    main()
