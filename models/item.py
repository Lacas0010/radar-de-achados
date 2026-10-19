from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, Any, List

@dataclass
class Anuncio:
    titulo: str
    preco: float
    localizacao: str
    url: str
    plataforma: str
    imagem_url: Optional[str] = None
    data_publicacao: Optional[str] = None
    desconto_percentual: Optional[float] = 0.0
    classificacao: Optional[str] = "PREÇO DE MERCADO"
    id: Optional[str] = None
    is_novo: bool = True
    
    # Novos campos para inteligência, histórico e galeria
    imagens: List[str] = field(default_factory=list)
    preco_anterior: Optional[float] = None
    variacao_preco: Optional[float] = None
    submodelos: List[str] = field(default_factory=list)
    zona_geografica: Optional[str] = None
    nivel_distancia: Optional[str] = "central" # 'central', 'metropolitana', 'distante'
    is_suspeito: bool = False
    motivo_suspeita: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Compatibilidade com a UI e exportação
        d["title"] = self.titulo
        d["price"] = self.preco
        d["price_formatted"] = f"R$ {self.preco:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        d["location"] = self.localizacao
        d["source"] = self.plataforma
        d["image"] = self.imagem_url or (self.imagens[0] if self.imagens else "")
        d["images"] = self.imagens if self.imagens else ([self.imagem_url] if self.imagem_url else [])
        d["date_posted"] = self.data_publicacao or ""
        d["deal_score"] = self.desconto_percentual or 0.0
        d["is_novo"] = self.is_novo
        
        # Histórico e Variação de Preço
        d["previous_price"] = self.preco_anterior
        if self.preco_anterior is not None:
            d["previous_price_formatted"] = f"R$ {self.preco_anterior:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        else:
            d["previous_price_formatted"] = None
        d["price_drop"] = self.variacao_preco
        
        # Inteligência de Submodelos e Geografia
        d["submodels"] = self.submodelos or []
        d["geo_zone"] = self.zona_geografica or "Região Principal"
        d["distance_level"] = self.nivel_distancia or "central"
        d["is_suspicious"] = self.is_suspeito
        d["suspicious_reason"] = self.motivo_suspeita or ""

        # Mapeamento do deal_tag para os estilos da UI
        if self.is_suspeito:
            d["deal_tag"] = "SUSPEITO"
        elif "SUPER" in (self.classificacao or ""):
            d["deal_tag"] = "SUPER_ACHADO"
        elif "ÓTIMO" in (self.classificacao or ""):
            d["deal_tag"] = "OTIMO_PRECO"
        elif "JUSTO" in (self.classificacao or "") or "MERCADO" in (self.classificacao or ""):
            d["deal_tag"] = "PRECO_JUSTO"
        else:
            d["deal_tag"] = "ACIMA_MEDIA"
            
        return d
