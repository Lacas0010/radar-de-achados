import urllib.parse
from typing import List
from playwright.sync_api import sync_playwright
from scrapers.base import Listing
from engine.regions import get_region_info
from engine.analyzer import parse_price, format_currency

def scrape_facebook(query: str, region_key: str = "sp_capital", max_items: int = 40) -> List[Listing]:
    """
    Busca anúncios no Facebook Marketplace na cidade/região selecionada usando Playwright.
    """
    region = get_region_info(region_key)
    city_slug = region.get("fb_city", "saopaulo")
    encoded_query = urllib.parse.quote_plus(query.strip())
    
    url = f"https://www.facebook.com/marketplace/{city_slug}/search?query={encoded_query}"
    print(f"[Facebook Marketplace] Iniciando busca: {url}")
    
    items: List[Listing] = []
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-setuid-sandbox'
                ]
            )
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
                viewport={"width": 1280, "height": 900},
                locale="pt-BR"
            )
            page = context.new_page()
            page.add_init_script('delete Object.getPrototypeOf(navigator).webdriver')
            
            page.goto(url, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(2500)

            # Scroll para carregar mais anúncios
            page.evaluate("""async () => {
                for (let i = 0; i < 5; i++) {
                    window.scrollBy(0, 1000);
                    await new Promise(r => setTimeout(r, 400));
                }
            }""")
            page.wait_for_timeout(1200)

            raw_list = page.evaluate("""() => {
                const results = [];
                const links = document.querySelectorAll('a[href*="/marketplace/item/"]');
                for (const a of links) {
                    const href = a.getAttribute('href') || '';
                    const fullUrl = href.startsWith('http') ? href : ('https://www.facebook.com' + href.split('?')[0]);
                    
                    const text = a.innerText || '';
                    const lines = text.split('\\n').map(l => l.trim()).filter(Boolean);
                    
                    let priceText = '';
                    let title = '';
                    let location = '';
                    
                    for (let i = 0; i < lines.length; i++) {
                        const l = lines[i];
                        if (!priceText && (l.includes('R$') || l.toLowerCase() === 'grátis' || l.toLowerCase() === 'gratis')) {
                            priceText = l;
                        } else if (priceText && !title) {
                            title = l;
                        } else if (title && !location) {
                            location = l;
                        }
                    }
                    
                    const img = a.querySelector('img');
                    const imgSrc = img ? img.src : '';
                    
                    if (title && priceText) {
                        results.push({
                            title: title,
                            priceText: priceText,
                            url: fullUrl,
                            image: imgSrc,
                            location: location
                        });
                    }
                }
                return results;
            }""")

            browser.close()

            seen_urls = set()
            for r in raw_list:
                u = r["url"]
                if u in seen_urls:
                    continue
                seen_urls.add(u)
                
                num_price = parse_price(r["priceText"])
                # Extrair ID do item do facebook
                item_id = "fb_" + (u.rstrip('/').split('/')[-1] if '/' in u else str(len(seen_urls)))
                
                listing = Listing(
                    id=item_id,
                    title=r["title"],
                    price=num_price,
                    price_formatted=format_currency(num_price) if num_price > 0 else r["priceText"],
                    url=u,
                    image=r["image"],
                    location=r["location"] or region["name"],
                    source="Facebook Marketplace"
                )
                items.append(listing)
                if len(items) >= max_items:
                    break

    except Exception as e:
        print(f"[Facebook Marketplace] Erro durante a busca: {e}")

    print(f"[Facebook Marketplace] Total de itens encontrados: {len(items)}")
    return items
