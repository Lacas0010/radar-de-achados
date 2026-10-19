import concurrent.futures
from typing import List, Dict, Any, Optional
from scrapers.base import Listing
from scrapers.olx import scrape_olx
from scrapers.facebook import scrape_facebook
from engine.analyzer import analyze_and_rank_listings

def search_used_items(
    query: str,
    region_key: str = "sp_capital",
    sources: Optional[List[str]] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    exclude_keywords: Optional[List[str]] = None,
    sort_by: str = "price_asc",
    ignore_fake_prices: bool = True,
    max_items_per_source: int = 40
) -> Dict[str, Any]:
    """
    Executa a busca simultânea nas plataformas selecionadas (OLX e Facebook Marketplace)
    e retorna os melhores preços analisados e organizados.
    """
    if sources is None:
        sources = ["olx", "facebook"]

    all_listings: List[Listing] = []

    tasks = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        if "olx" in sources:
            tasks.append(
                executor.submit(scrape_olx, query=query, region_key=region_key, max_items=max_items_per_source)
            )
        if "facebook" in sources:
            tasks.append(
                executor.submit(scrape_facebook, query=query, region_key=region_key, max_items=max_items_per_source)
            )

        for future in concurrent.futures.as_completed(tasks):
            try:
                results = future.result()
                all_listings.extend(results)
            except Exception as e:
                print(f"[Coordinator] Falha ao executar tarefa de scraping: {e}")

    # Processamento, filtragem de preços irreais e ranqueamento
    analyzed = analyze_and_rank_listings(
        listings=all_listings,
        min_price=min_price,
        max_price=max_price,
        exclude_keywords=exclude_keywords,
        sort_by=sort_by,
        ignore_fake_prices=ignore_fake_prices
    )

    return analyzed
