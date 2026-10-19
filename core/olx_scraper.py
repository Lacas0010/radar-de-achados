import re
import json
import urllib.parse
from typing import List, Optional, Dict, Any
from playwright.sync_api import sync_playwright
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

def extrair_ads_next_data(html_content: str, uf: str) -> List[Anuncio]:
    """
    Extrai o payload JSON do __NEXT_DATA__ via regex no HTML cru da requisição,
    sem aguardar seletores visuais ou renderização DOM.
    """
    anuncios: List[Anuncio] = []
    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html_content, re.DOTALL)
    if not match:
        return []

    try:
        data = json.loads(match.group(1))
        # Navega na árvore do Next.js
        page_props = data.get("props", {}).get("pageProps", {})
        ads_raw = page_props.get("ads", [])
        
        # Algumas versões da OLX usam initialReduxState ou searchResult
        if not ads_raw:
            ads_raw = page_props.get("searchResult", {}).get("ads", [])
            
        if not ads_raw and "initialReduxState" in page_props:
            redux = page_props.get("initialReduxState", {})
            ads_raw = redux.get("adList", {}).get("ads", [])

        print(f"[OLX API Direct] Encontrados {len(ads_raw)} anúncios no payload __NEXT_DATA__")

        for ad in ads_raw:
            # Ignora banners ou anúncios de terceiros
            if ad.get("isAdverts") or not ad.get("subject"):
                continue

            title = ad.get("subject", "").strip()
            if not title:
                continue

            raw_price = ad.get("price") or ad.get("priceValue") or ad.get("formattedPrice") or "0"
            price = parse_price(str(raw_price))
            
            # URL
            url = ad.get("url") or ""
            if url and not url.startswith("http"):
                url = f"https://www.olx.com.br{url}"

            # Extração da galeria completa de imagens
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

            # Localização detalhada
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

def scrape_olx(
    termo: str,
    uf: str = "sp",
    preco_min: float = 0.0,
    preco_max: Optional[float] = None,
    max_items: int = 40
) -> List[Anuncio]:
    """
    Extrai anúncios da OLX Brasil com bypass de renderização DOM através
    do payload JSON direto do __NEXT_DATA__, com fallback seguro para DOM.
    """
    uf_clean = uf.lower().strip()
    encoded_query = urllib.parse.quote_plus(termo.strip())
    
    url_base = f"https://www.olx.com.br/estado-{uf_clean}" if uf_clean != "brasil" else "https://www.olx.com.br/brasil"
    params = [f"q={encoded_query}"]
    
    if preco_min and preco_min > 0:
        params.append(f"ps={int(preco_min)}")
    if preco_max and preco_max > 0:
        params.append(f"pe={int(preco_max)}")
        
    url = f"{url_base}?{'&'.join(params)}"
    print(f"[OLX] Acessando URL: {url}")
    
    anuncios: List[Anuncio] = []
    
    try:
        from core.stealth import STEALTH_LAUNCH_ARGS, get_stealth_context_options, apply_stealth_to_page
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=STEALTH_LAUNCH_ARGS
            )
            context = browser.new_context(**get_stealth_context_options())
            page = context.new_page()
            apply_stealth_to_page(page)
            
            # Navega na página
            page.goto(url, wait_until="domcontentloaded", timeout=25000)
            
            # 1. TENTATIVA RÁPIDA: Interceptação Direta de API (__NEXT_DATA__)
            html_raw = page.content()
            direct_ads = extrair_ads_next_data(html_raw, uf=uf_clean)
            
            if direct_ads:
                anuncios = direct_ads[:max_items]
                browser.close()
                print(f"[OLX] Sucesso via __NEXT_DATA__: {len(anuncios)} anúncios extraídos com galeria completa.")
                return anuncios

            # 2. FALLBACK SEGURO: Extração via DOM se __NEXT_DATA__ não estiver presente
            print("[OLX] __NEXT_DATA__ não detectado. Ativando fallback DOM com scroll...")
            page.wait_for_timeout(1500)
            for _ in range(4):
                page.mouse.wheel(0, 1000)
                page.wait_for_timeout(350)

            raw_cards = page.evaluate("""() => {
                const results = [];
                const sections = document.querySelectorAll('section');
                for (const s of sections) {
                    const a = s.querySelector('a[data-testid="adcard-link"]') || s.querySelector('a');
                    if (!a || !a.href || a.href.includes('desapega') || !a.href.includes('olx.com.br')) continue;
                    
                    const text = s.innerText || '';
                    const match = text.match(/R\\$\\s*([\\d\\.]+)/);
                    if (!match) continue;
                    
                    const h2 = s.querySelector('h2');
                    const title = (h2 ? h2.innerText : (a.title || '')).trim();
                    if (!title) continue;
                    
                    let imgSrc = '';
                    const pictureSource = s.querySelector('picture source');
                    if (pictureSource && pictureSource.getAttribute('srcset')) {
                        const parts = pictureSource.getAttribute('srcset').split(',');
                        imgSrc = parts[parts.length - 1].trim().split(' ')[0];
                    }
                    if (!imgSrc || !imgSrc.startsWith('http')) {
                        const img = s.querySelector('img');
                        if (img) {
                            imgSrc = img.currentSrc || img.src || img.getAttribute('data-src') || '';
                            if ((!imgSrc || imgSrc.startsWith('data:')) && img.getAttribute('srcset')) {
                                const parts = img.getAttribute('srcset').split(',');
                                imgSrc = parts[parts.length - 1].trim().split(' ')[0];
                            }
                        }
                    }
                    if (imgSrc && (imgSrc.startsWith('data:') || !imgSrc.startsWith('http'))) {
                        imgSrc = '';
                    }
                    
                    const lines = text.split('\\n').map(l => l.trim()).filter(Boolean);
                    let loc = '';
                    let datePost = '';
                    for (const l of lines) {
                        if (l.includes('Hoje,') || l.includes('Ontem,') || /\\d{1,2}\\/\\d{1,2}/.test(l)) {
                            datePost = l;
                        } else if ((l.includes(',') || l.includes(' - ')) && !l.includes('R$') && !l.includes('juros') && !l.includes('Frete') && !l.includes('Entrega')) {
                            loc = l;
                        }
                    }
                    
                    results.push({
                        titulo: title,
                        preco_texto: match[0],
                        url: a.href,
                        imagem_url: imgSrc,
                        localizacao: loc,
                        data_publicacao: datePost
                    });
                }
                return results;
            }""")

            browser.close()

            seen_urls = set()
            for r in raw_cards:
                u = r["url"]
                if u in seen_urls:
                    continue
                seen_urls.add(u)
                
                num_preco = parse_price(r["preco_texto"])
                anuncio = Anuncio(
                    titulo=r["titulo"],
                    preco=num_preco,
                    localizacao=r["localizacao"] or f"Estado {uf.upper()}",
                    url=u,
                    plataforma="OLX",
                    imagem_url=r["imagem_url"] or None,
                    imagens=[r["imagem_url"]] if r["imagem_url"] else [],
                    data_publicacao=r["data_publicacao"] or None
                )
                anuncios.append(anuncio)
                if len(anuncios) >= max_items:
                    break

    except Exception as e:
        print(f"[OLX] Erro ao extrair anúncios: {e}")

    print(f"[OLX] Sucesso: {len(anuncios)} anúncios extraídos.")
    return anuncios
