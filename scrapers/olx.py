import re
import urllib.parse
from typing import List
from bs4 import BeautifulSoup
from scrapers.base import Listing
from engine.regions import get_region_info
from engine.analyzer import parse_price, format_currency

def scrape_olx_curl(query: str, region_key: str = "sp_capital", max_items: int = 40) -> List[Listing]:
    from curl_cffi import requests as cffi_requests
    
    region = get_region_info(region_key)
    olx_path = region.get("olx_path", "estado-sp/sao-paulo-e-regiao")
    encoded_query = urllib.parse.quote_plus(query.strip())
    
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

    items: List[Listing] = []
    page = 1
    max_pages = 2 if max_items > 45 else 1
    seen_urls = set()

    while len(items) < max_items and page <= max_pages:
        url = f"https://www.olx.com.br/{olx_path}?q={encoded_query}"
        if page > 1:
            url += f"&o={page}"
            
        print(f"[OLX TLS-Stealth] Conectando a {url}...")
        resp = cffi_requests.get(url, impersonate="chrome124", headers=headers, timeout=12)
        if resp.status_code != 200:
            print(f"[OLX TLS-Stealth] Status HTTP {resp.status_code}")
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select("section.olx-adcard, [data-mode='horizontal'], div.olx-adcard")

        if not cards:
            break

        for c in cards:
            a = c.select_one("a.olx-adcard__link") or c.select_one("a[data-testid='adcard-link']") or c.select_one("a[href]")
            if not a or not a.get("href"):
                continue

            u = a.get("href", "").strip()
            if not u or "desapega" in u:
                continue
            if not u.startswith("http"):
                u = f"https://www.olx.com.br{u}"

            if u in seen_urls:
                continue
            seen_urls.add(u)

            title_elem = c.select_one(".olx-adcard__title") or c.select_one("h2") or a
            title = a.get("title") or (title_elem.get_text(strip=True) if title_elem else "")
            if not title:
                continue

            price_elem = c.select_one(".olx-adcard__price") or c.select_one("h3")
            price_text = price_elem.get_text(strip=True) if price_elem else ""
            if not price_text:
                p_match = re.search(r'R\$\s*[\d\.]+(?:,\d{2})?', c.get_text())
                price_text = p_match.group(0) if p_match else "0"

            num_price = parse_price(price_text)
            
            loc_elem = c.select_one(".olx-adcard__location")
            location = loc_elem.get_text(strip=True) if loc_elem else region["name"]

            date_elem = c.select_one(".olx-adcard__date")
            date_post = date_elem.get_text(strip=True) if date_elem else ""

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
                img_url = ""

            ad_id = u.split('-')[-1].split('?')[0]

            listing = Listing(
                id=f"olx_{ad_id}",
                title=title,
                price=num_price,
                price_formatted=format_currency(num_price) if num_price > 0 else price_text,
                url=u,
                image=img_url,
                location=location,
                source="OLX",
                date_posted=date_post
            )
            items.append(listing)
            if len(items) >= max_items:
                break

        page += 1

    return items

def scrape_olx_playwright(query: str, region_key: str = "sp_capital", max_items: int = 40) -> List[Listing]:
    from playwright.sync_api import sync_playwright
    from core.stealth import STEALTH_LAUNCH_ARGS, get_stealth_context_options, apply_stealth_to_page
    
    region = get_region_info(region_key)
    olx_path = region.get("olx_path", "estado-sp/sao-paulo-e-regiao")
    encoded_query = urllib.parse.quote_plus(query.strip())
    url = f"https://www.olx.com.br/{olx_path}?q={encoded_query}"
    
    items: List[Listing] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=STEALTH_LAUNCH_ARGS)
        context = browser.new_context(**get_stealth_context_options())
        page = context.new_page()
        apply_stealth_to_page(page)
        
        page.goto(url, wait_until="domcontentloaded", timeout=25000)
        page.wait_for_timeout(1500)
        html_raw = page.content()
        browser.close()

        soup = BeautifulSoup(html_raw, "html.parser")
        cards = soup.select("section.olx-adcard, [data-mode='horizontal'], div.olx-adcard")
        seen_urls = set()
        for c in cards:
            a = c.select_one("a.olx-adcard__link") or c.select_one("a[data-testid='adcard-link']") or c.select_one("a[href]")
            if not a or not a.get("href"):
                continue
            u = a.get("href", "").strip()
            if not u or "desapega" in u:
                continue
            if not u.startswith("http"):
                u = f"https://www.olx.com.br{u}"
            if u in seen_urls:
                continue
            seen_urls.add(u)

            title_elem = c.select_one(".olx-adcard__title") or c.select_one("h2") or a
            title = a.get("title") or (title_elem.get_text(strip=True) if title_elem else "")
            price_elem = c.select_one(".olx-adcard__price") or c.select_one("h3")
            price_text = price_elem.get_text(strip=True) if price_elem else ""
            num_price = parse_price(price_text)

            loc_elem = c.select_one(".olx-adcard__location")
            location = loc_elem.get_text(strip=True) if loc_elem else region["name"]
            date_elem = c.select_one(".olx-adcard__date")
            date_post = date_elem.get_text(strip=True) if date_elem else ""

            img_url = ""
            img = c.find("img")
            if img:
                img_url = img.get("src") or img.get("data-src") or ""

            ad_id = u.split('-')[-1].split('?')[0]
            listing = Listing(
                id=f"olx_{ad_id}",
                title=title,
                price=num_price,
                price_formatted=format_currency(num_price) if num_price > 0 else price_text,
                url=u,
                image=img_url,
                location=location,
                source="OLX",
                date_posted=date_post
            )
            items.append(listing)
            if len(items) >= max_items:
                break

    return items

def scrape_olx(query: str, region_key: str = "sp_capital", max_items: int = 40) -> List[Listing]:
    """
    Busca anúncios na OLX Brasil na região selecionada com bypass de Cloudflare (curl_cffi)
    e fallback automático para Playwright.
    """
    try:
        items = scrape_olx_curl(query=query, region_key=region_key, max_items=max_items)
        if items:
            print(f"[OLX] Total de itens encontrados via TLS-Stealth: {len(items)}")
            return items
    except Exception as e:
        print(f"[OLX] Falha no método TLS-Stealth: {e}. Tentando fallback Playwright...")

    try:
        items = scrape_olx_playwright(query=query, region_key=region_key, max_items=max_items)
        print(f"[OLX] Total de itens encontrados via Playwright: {len(items)}")
        return items
    except Exception as e:
        print(f"[OLX] Erro durante a busca: {e}")

    return []
