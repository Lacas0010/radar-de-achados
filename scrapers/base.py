from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any

@dataclass
class Listing:
    id: str
    title: str
    price: float
    price_formatted: str
    url: str
    image: str
    location: str
    source: str
    date_posted: str = ""
    deal_score: float = 0.0     # Percentual de desconto em relação à mediana (ex: +25% mais barato)
    deal_tag: str = "PRECO_JUSTO" # SUPER_ACHADO, OTIMO_PRECO, PRECO_JUSTO, ACIMA_MEDIA
    is_outlier: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
