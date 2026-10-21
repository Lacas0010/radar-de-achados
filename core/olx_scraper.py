import re
import json
import urllib.parse
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup
from models.item import Anuncio

def parse_price(price_str: str) -> float:
    """Converte string de preço (ex: 'R$ 2.500,00' ou 'R$ 399') para float."""
    if not price_str:
        return 0.0
    cleaned = re.sub(r'[^\d,]', '', str(price_str))
    if ',' in cleaned:
        cleaned = cleaned.replace('.', '').replace(',', '.')
    else:
        cleaned = cleaned.replace('.', '')
    try:
        return float(cleaned)
    except:
        return 0.0

def extrair_ads_html(html_content: str, uf: str) -> List[Anuncio]:
    """
    Extrai anúncios do HTML renderizado da OLX (App Router / Next.js SSR),
    analisando os cartões semânticos 'section.olx-adcard'.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    cards = soup.select("section.olx-adcard, [data-mode='horizontal'], div.olx-adcard")
    if not cards:
        cards = soup.find_all(
            lambda tag: tag.name in ["section", "article", "div"] and tag.get("class") and any("adcard" in str(c).lower() for c in tag.get("class"))
        )

    anuncios: List[Anuncio] = []
    seen_urls = set()

    for c in cards:
        a = c.select_one("a.olx-adcard__link") or c.select_one("a[data-testid='adcard-link']") or c.select_one("a[href]")
        if not a or not a.get("href"):
            continue

        url = a.get("href", "").strip()
        if not url or "desapega" in url:
            continue
        if not url.startswith("http"):
            url = f"https://www.olx.com.br{url}"

        if url in seen_urls:
            continue
        seen_urls.add(url)

        # ID do anúncio a partir do sufixo numérico da URL
        id_match = re.search(r'-(\d{7,12})', url)
        ad_id = id_match.group(1) if id_match else None

        # Título
        title_elem = c.select_one(".olx-adcard__title") or c.select_one("h2") or a
        title = a.get("title") or (title_elem.get_text(strip=True) if title_elem else "")
        if not title:
            continue

        # Preço
        price_elem = c.select_one(".olx-adcard__price") or c.select_one("h3")
        price_text = price_elem.get_text(strip=True) if price_elem else ""
        if not price_text:
            p_match = re.search(r'R\$\s*[\d\.]+(?:,\d{2})?', c.get_text())
            price_text = p_match.group(0) if p_match else "0"
        price_num = parse_price(price_text)

        # Localização
        loc_elem = c.select_one(".olx-adcard__location")
        location = loc_elem.get_text(strip=True) if loc_elem else f"Estado {uf.upper()}"

        # Data de publicação
        date_elem = c.select_one(".olx-adcard__date")
        date_post = date_elem.get_text(strip=True) if date_elem else None

        # Imagem primária
        img_url = ""
        img = c.find("img")
        if img:
            img_url = img.get("src") or img.get("data-src") or ""
            if (not img_url or img_url.startswith("data:")) and img.get("srcset"):
                parts = img.get("srcset").split(",")
                img_url = parts[-1].strip().split(" ")[0]
        if not img_url:
            source = c.find("source")
            if source and source.get("srcset"):
                parts = source.get("srcset").split(",")
                img_url = parts[-1].strip().split(" ")[0]

        if img_url and (img_url.startswith("data:") or not img_url.startswith("http")):
            img_url = None

        images_list = [img_url] if img_url else []

        anuncio = Anuncio(
            titulo=title,
            preco=price_num,
            localizacao=location,
            url=url,
            plataforma="OLX",
            imagem_url=img_url,
            imagens=images_list,
            data_publicacao=date_post,
            id=f"olx_{ad_id}" if ad_id else None
        )
        anuncios.append(anuncio)

    return anuncios

def extrair_ads_next_data(html_content: str, uf: str) -> List[Anuncio]:
    """
    Fallback legado: Extrai o payload JSON do __NEXT_DATA__ caso presente.
    """
    anuncios: List[Anuncio] = []
    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html_content, re.DOTALL)
    if not match:
        return []

    try:
        data = json.loads(match.group(1))
        page_props = data.get("props", {}).get("pageProps", {})
        ads_raw = page_props.get("ads", [])

        if not ads_raw:
            ads_raw = page_props.get("searchResult", {}).get("ads", [])

        if not ads_raw and "initialReduxState" in page_props:
            redux = page_props.get("initialReduxState", {})
            ads_raw = redux.get("adList", {}).get("ads", [])

        for ad in ads_raw:
            if ad.get("isAdverts") or not ad.get("subject"):
                continue

            title = ad.get("subject", "").strip()
            if not title:
                continue

            raw_price = ad.get("price") or ad.get("priceValue") or ad.get("formattedPrice") or "0"
            price = parse_price(str(raw_price))

            url = ad.get("url") or ""
            if url and not url.startswith("http"):
                url = f"https://www.olx.com.br{url}"

            images_list = []
            raw_images = ad.get("images", [])
            for img_item in raw_images:
                if isinstance(img_item, dict):
                    img_url = img_item.get("original") or img_item.get("thumbnail") or img_item.get("url")
                    if img_url and img_url.startswith("http"):
                        images_list.append(img_url)
                elif isinstance(img_item, str) and img_item.startswith("http"):
                    images_list.append(img_item)

            primary_img = images_list[0] if images_list else None

            location_parts = []
            loc_obj = ad.get("location", {})
            if isinstance(loc_obj, dict):
                if loc_obj.get("neighborhood"):
                    location_parts.append(loc_obj.get("neighborhood"))
                if loc_obj.get("municipality"):
                    location_parts.append(loc_obj.get("municipality"))
                if loc_obj.get("uf"):
                    location_parts.append(loc_obj.get("uf"))

            location_str = ", ".join(location_parts) if location_parts else (ad.get("locationText") or f"Estado {uf.upper()}")
            date_pub = ad.get("date") or ad.get("displayDate") or None

            anuncio = Anuncio(
                titulo=title,
                preco=price,
                localizacao=location_str,
                url=url,
                plataforma="OLX",
                imagem_url=primary_img,
                imagens=images_list,
                data_publicacao=date_pub
            )
            anuncios.append(anuncio)

    except Exception as e:
        print(f"[OLX API Direct] Erro ao parsear __NEXT_DATA__: {e}")

    return anuncios

def _build_olx_url(termo: str, uf: str, preco_min: float = 0.0, preco_max: Optional[float] = None, page_num: int = 1) -> str:
    uf_clean = uf.lower().strip()
    encoded_query = urllib.parse.quote_plus(termo.strip())
    url_base = f"https://www.olx.com.br/estado-{uf_clean}" if uf_clean != "brasil" else "https://www.olx.com.br/brasil"
    params = [f"q={encoded_query}"]

    if preco_min and preco_min > 0:
        params.append(f"ps={int(preco_min)}")
    if preco_max and preco_max > 0:
        params.append(f"pe={int(preco_max)}")
    if page_num > 1:
        params.append(f"o={page_num}")

    return f"{url_base}?{'&'.join(params)}"

def scrape_olx_curl(
    termo: str,
    uf: str = "sp",
    preco_min: float = 0.0,
    preco_max: Optional[float] = None,
    max_items: int = 40
) -> List[Anuncio]:
    """
    Busca rápida via curl_cffi com personificação de Chrome (TLS JA3/JA4 real).
    Bypassa Cloudflare e extrai anúncios diretamente do SSR da OLX em ~1.5s.
    """
    from curl_cffi import requests as cffi_requests

    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Sec-Ch-Ua": '"Chromium";v="131", "Not_A Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1"
    }

    anuncios: List[Anuncio] = []
    page = 1
    max_pages = 2 if max_items > 45 else 1

    while len(anuncios) < max_items and page <= max_pages:
        url = _build_olx_url(termo, uf, preco_min, preco_max, page_num=page)
        print(f"[OLX TLS-Stealth] Conectando a {url} (pág {page})...")

        resp = cffi_requests.get(url, impersonate="chrome124", headers=headers, timeout=12)
        if resp.status_code != 200:
            print(f"[OLX TLS-Stealth] Status HTTP {resp.status_code} na página {page}.")
            break

        html = resp.text
        # Tenta extração via HTML moderno primeiro
        novos = extrair_ads_html(html, uf=uf)
        if not novos:
            # Fallback para Next Data se houver
            novos = extrair_ads_next_data(html, uf=uf)

        if not novos:
            print(f"[OLX TLS-Stealth] Nenhum anúncio retornado na página {page}.")
            break

        anuncios.extend(novos)
        page += 1

    return anuncios[:max_items]

def scrape_olx_playwright(
    termo: str,
    uf: str = "sp",
    preco_min: float = 0.0,
    preco_max: Optional[float] = None,
    max_items: int = 40
) -> List[Anuncio]:
    """
    Fallback secundário usando Playwright Chromium com scripts stealth.
    """
    from playwright.sync_api import sync_playwright
    from core.stealth import STEALTH_LAUNCH_ARGS, get_stealth_context_options, apply_stealth_to_page

    url = _build_olx_url(termo, uf, preco_min, preco_max, page_num=1)
    print(f"[OLX Playwright Fallback] Acessando URL: {url}")
    anuncios: List[Anuncio] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=STEALTH_LAUNCH_ARGS
        )
        context = browser.new_context(**get_stealth_context_options())
        page = context.new_page()
        apply_stealth_to_page(page)

        page.goto(url, wait_until="domcontentloaded", timeout=25000)
        page.wait_for_timeout(1500)

        html_raw = page.content()
        browser.close()

        anuncios = extrair_ads_html(html_raw, uf=uf)
        if not anuncios:
            anuncios = extrair_ads_next_data(html_raw, uf=uf)

    return anuncios[:max_items]

def scrape_olx(
    termo: str,
    uf: str = "sp",
    preco_min: float = 0.0,
    preco_max: Optional[float] = None,
    max_items: int = 40
) -> List[Anuncio]:
    """
    Função principal de busca na OLX Brasil.
    Prioriza o scraper TLS-Stealth via curl_cffi (bypass total de Cloudflare e resposta ultrarrápida),
    com fallback automático para Playwright caso necessário.
    """
    anuncios: List[Anuncio] = []

    # 1. Tentativa Primária: TLS Fingerprint Real (Bypass de Cloudflare)
    try:
        anuncios = scrape_olx_curl(termo, uf, preco_min, preco_max, max_items)
        if anuncios:
            print(f"[OLX] Sucesso via TLS-Stealth: {len(anuncios)} anúncios extraídos.")
            return anuncios
    except Exception as e:
        print(f"[OLX] Falha no método TLS-Stealth: {e}. Acionando fallback Playwright...")

    # 2. Fallback Secundário: Playwright com stealth
    try:
        anuncios = scrape_olx_playwright(termo, uf, preco_min, preco_max, max_items)
        print(f"[OLX] Sucesso via Playwright Fallback: {len(anuncios)} anúncios extraídos.")
    except Exception as e:
        print(f"[OLX] Falha no fallback Playwright: {e}")

    return anuncios
