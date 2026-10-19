import os
import json
import urllib.parse
from typing import List, Optional, Dict, Any
from playwright.sync_api import sync_playwright
from models.item import Anuncio
from core.olx_scraper import parse_price
from core.stealth import STEALTH_LAUNCH_ARGS, get_stealth_context_options, apply_stealth_to_page

UF_TO_FB_CITY = {
    "sp": "saopaulo",
    "df": "brasilia",
    "rj": "riodejaneiro",
    "mg": "belohorizonte",
    "pr": "curitiba",
    "rs": "portoalegre",
    "sc": "florianopolis",
    "ba": "salvador",
    "ce": "fortaleza",
    "go": "goiania",
    "pe": "recife",
    "es": "vitoria"
}

STORAGE_STATE_FILE = "storage_state.json"

def salvar_sessao_facebook():
    """
    Função auxiliar para o usuário autenticar manualmente no Facebook
    e salvar a sessão em 'storage_state.json', evitando bloqueios.
    """
    print("\n[Facebook] Abrindo navegador para login manual...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://www.facebook.com/login")
        print("[Facebook] Faça login na sua conta e pressione ENTER aqui quando terminar...")
        input()
        context.storage_state(path=STORAGE_STATE_FILE)
        print(f"[Facebook] Sessão salva com sucesso em '{STORAGE_STATE_FILE}'!")
        browser.close()

def extrair_listings_graphql(payload: Dict[str, Any], city_slug: str, uf: str) -> List[Anuncio]:
    """
    Extrai anúncios a partir da árvore JSON retornada pela rota GraphQL /api/graphql/ do Facebook.
    """
    anuncios: List[Anuncio] = []
    
    # Função recursiva auxiliar para encontrar objetos 'listing' ou 'feed_units'
    def buscar_listings(node):
        if isinstance(node, dict):
            # Se for um nó de listing direto
            if "marketplace_listing_title" in node and ("listing_price" in node or "formatted_price" in node):
                title = node.get("marketplace_listing_title", "")
                
                # Preço
                price_obj = node.get("listing_price", {})
                price_str = price_obj.get("formatted_amount") if isinstance(price_obj, dict) else str(node.get("formatted_price", "0"))
                price_num = parse_price(price_str)
                
                # ID e URL
                item_id = str(node.get("id") or "")
                url = f"https://www.facebook.com/marketplace/item/{item_id}/" if item_id else ""
                
                # Imagem primária e galeria
                images = []
                primary_photo = node.get("primary_listing_photo", {})
                if isinstance(primary_photo, dict) and "image" in primary_photo:
                    uri = primary_photo["image"].get("uri")
                    if uri: images.append(uri)
                    
                photos_list = node.get("listing_photos", [])
                if isinstance(photos_list, list):
                    for p in photos_list:
                        if isinstance(p, dict) and "image" in p:
                            u = p["image"].get("uri")
                            if u and u not in images:
                                images.append(u)

                # Localização
                loc_obj = node.get("location", {})
                city = ""
                if isinstance(loc_obj, dict):
                    reverse = loc_obj.get("reverse_geocode", {})
                    city = reverse.get("city") or loc_obj.get("city") or ""
                location = city or f"{city_slug.capitalize()}, {uf.upper()}"

                if title and url:
                    anuncios.append(Anuncio(
                        titulo=title,
                        preco=price_num,
                        localizacao=location,
                        url=url,
                        plataforma="Facebook Marketplace",
                        imagem_url=images[0] if images else None,
                        imagens=images,
                        id=item_id
                    ))
                return

            for v in node.values():
                buscar_listings(v)
        elif isinstance(node, list):
            for it in node:
                buscar_listings(it)

    buscar_listings(payload)
    return anuncios

def scrape_facebook_marketplace(
    termo: str,
    uf: str = "sp",
    preco_min: float = 0.0,
    preco_max: Optional[float] = None,
    max_items: int = 40
) -> List[Anuncio]:
    """
    Extrai anúncios do Facebook Marketplace com interceptação GraphQL (/api/graphql/)
    e fallback automático para extração precisa por spans DOM.
    """
    city_slug = UF_TO_FB_CITY.get(uf.lower().strip(), "saopaulo")
    encoded_query = urllib.parse.quote_plus(termo.strip())
    
    url = f"https://www.facebook.com/marketplace/{city_slug}/search?query={encoded_query}"
    print(f"[Facebook] Acessando URL: {url}")
    
    anuncios: List[Anuncio] = []
    seen_urls = set()
    intercepted_ads: List[Anuncio] = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=STEALTH_LAUNCH_ARGS
            )

            storage_path = STORAGE_STATE_FILE if os.path.exists(STORAGE_STATE_FILE) else None
            if storage_path:
                print(f"[Facebook] Reutilizando sessão autenticada de '{STORAGE_STATE_FILE}'")

            context_kwargs = get_stealth_context_options(storage_state_path=storage_path)
            context = browser.new_context(**context_kwargs)
            page = context.new_page()
            apply_stealth_to_page(page)

            # 1. INTERCEPTAÇÃO GRAPHQL: Escuta respostas /api/graphql/ para extrair JSON nativo
            def handle_response(response):
                if "/api/graphql" in response.url:
                    try:
                        ct = response.headers.get("content-type", "")
                        if "json" in ct or "text" in ct:
                            text_body = response.text()
                            if text_body.startswith("for (;;);"):
                                text_body = text_body[9:]
                            payload = json.loads(text_body)
                            extracted = extrair_listings_graphql(payload, city_slug=city_slug, uf=uf)
                            if extracted:
                                intercepted_ads.extend(extracted)
                    except Exception:
                        pass

            page.on("response", handle_response)

            page.goto(url, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(2000)

            # Rolagem rápida
            for _ in range(4):
                page.mouse.wheel(0, 1000)
                page.wait_for_timeout(350)

            # Se conseguimos dados via GraphQL direto
            if intercepted_ads:
                print(f"[Facebook GraphQL] Interceptados com sucesso {len(intercepted_ads)} anúncios da rota GraphQL!")
                for a in intercepted_ads:
                    if a.url in seen_urls:
                        continue
                    seen_urls.add(a.url)
                    if preco_min > 0 and a.preco < preco_min:
                        continue
                    if preco_max is not None and preco_max > 0 and a.preco > preco_max:
                        continue
                    anuncios.append(a)
                    if len(anuncios) >= max_items:
                        break

            # 2. FALLBACK SEGURO: Extração DOM via Spans isolados
            if not anuncios:
                print("[Facebook] Ativando fallback DOM com spans isolados...")
                raw_cards = page.evaluate("""() => {
                    const BADGE_WORDS = ['acabou de chegar', 'em alta', 'novo', 'reservado', 'classificado', 'grátis', 'gratis'];
                    const links = document.querySelectorAll('a[href*="/marketplace/item/"]');
                    const results = [];
                    
                    for (const a of links) {
                        const href = a.getAttribute('href') || '';
                        const fullUrl = href.startsWith('http') ? href : ('https://www.facebook.com' + href.split('?')[0]);
                        
                        const spans = Array.from(a.querySelectorAll('span'))
                            .map(s => s.innerText ? s.innerText.trim() : '')
                            .filter(s => s.length > 0);
                            
                        let priceText = '';
                        let title = '';
                        let location = '';
                        
                        for (const s of spans) {
                            if (s.includes('R$') || s.toLowerCase() === 'grátis' || s.toLowerCase() === 'gratis') {
                                const m = s.match(/R\\$\\s*[\\d\\.]+/i);
                                priceText = m ? m[0] : s;
                                break;
                            }
                        }
                        
                        for (let i = spans.length - 1; i >= 0; i--) {
                            const s = spans[i];
                            if (s.includes(',') && !s.includes('R$')) {
                                location = s;
                                break;
                            }
                        }
                        
                        for (const s of spans) {
                            const lower = s.toLowerCase();
                            const isBadge = BADGE_WORDS.some(bw => lower === bw);
                            if (!s.includes('R$') && s !== location && !isBadge && s.length >= 2) {
                                title = s;
                                break;
                            }
                        }
                        
                        const img = a.querySelector('img');
                        let imgSrc = '';
                        if (img) {
                            imgSrc = img.currentSrc || img.src || img.getAttribute('data-src') || '';
                        }
                        
                        if (title && priceText) {
                            results.push({
                                title: title,
                                priceText: priceText,
                                location: location,
                                url: fullUrl,
                                image: imgSrc
                            });
                        }
                    }
                    return results;
                }""")

                for it in raw_cards:
                    u = it["url"]
                    if u in seen_urls:
                        continue
                    seen_urls.add(u)
                    
                    num_preco = parse_price(it["priceText"])
                    if preco_min > 0 and num_preco < preco_min:
                        continue
                    if preco_max is not None and preco_max > 0 and num_preco > preco_max:
                        continue
                        
                    anuncio = Anuncio(
                        titulo=it["title"],
                        preco=num_preco,
                        localizacao=it["location"] or f"{city_slug.capitalize()}, {uf.upper()}",
                        url=u,
                        plataforma="Facebook Marketplace",
                        imagem_url=it["image"] or None,
                        imagens=[it["image"]] if it["image"] else []
                    )
                    anuncios.append(anuncio)
                    if len(anuncios) >= max_items:
                        break

            browser.close()

    except Exception as e:
        print(f"[Facebook] Erro ao extrair anúncios: {e}")

    print(f"[Facebook] Sucesso: {len(anuncios)} anúncios extraídos.")
    return anuncios
