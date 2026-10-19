import urllib.parse
from typing import List
from playwright.sync_api import sync_playwright
from scrapers.base import Listing
from engine.regions import get_region_info
from engine.analyzer import parse_price, format_currency

def scrape_olx(query: str, region_key: str = "sp_capital", max_items: int = 40) -> List[Listing]:
    """
    Busca anúncios na OLX Brasil na região selecionada usando Playwright com anti-detecção.
    """
    region = get_region_info(region_key)
    olx_path = region.get("olx_path", "estado-sp/sao-paulo-e-regiao")
    encoded_query = urllib.parse.quote_plus(query.strip())
    
    url = f"https://www.olx.com.br/{olx_path}?q={encoded_query}"
    print(f"[OLX] Iniciando busca: {url}")
    
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
            page.wait_for_timeout(2000)

            # Scroll para carregar itens com content-visibility
            page.evaluate("""async () => {
                for (let i = 0; i < 5; i++) {
                    window.scrollBy(0, 1000);
                    await new Promise(r => setTimeout(r, 350));
                }
            }""")
            page.wait_for_timeout(1000)

            raw_list = page.evaluate("""() => {
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
                    
                    const img = s.querySelector('img');
                    let imgSrc = '';
                    if (img) {
                        imgSrc = img.currentSrc || img.src || img.getAttribute('data-src') || '';
                        if ((!imgSrc || imgSrc.startsWith('data:')) && img.getAttribute('srcset')) {
                            const parts = img.getAttribute('srcset').split(',');
                            imgSrc = parts[parts.length - 1].trim().split(' ')[0];
                        }
                    }
                    
                    // Localização e Data
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
                        title: title,
                        priceText: match[0],
                        url: a.href,
                        image: imgSrc,
                        location: loc,
                        date: datePost
                    });
                }
                return results;
            }""")

            browser.close()

            # Normalizar para Listing
            seen_urls = set()
            for r in raw_list:
                u = r["url"]
                if u in seen_urls:
                    continue
                seen_urls.add(u)
                
                num_price = parse_price(r["priceText"])
                ad_id = u.split('-')[-1].split('?')[0]
                
                listing = Listing(
                    id=f"olx_{ad_id}",
                    title=r["title"],
                    price=num_price,
                    price_formatted=format_currency(num_price) if num_price > 0 else r["priceText"],
                    url=u,
                    image=r["image"],
                    location=r["location"] or region["name"],
                    source="OLX",
                    date_posted=r["date"]
                )
                items.append(listing)
                if len(items) >= max_items:
                    break

    except Exception as e:
        print(f"[OLX] Erro durante a busca: {e}")

    print(f"[OLX] Total de itens encontrados: {len(items)}")
    return items
