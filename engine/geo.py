import re
from typing import Dict, Any, Tuple

# Mapeamento de Zonas por Região / Estado
# Categorias:
# - central: Região central ou com metrô fácil (distância < 15km)
# - metropolitana: Cidades satélites ou municípios vizinhos conurbados (15km - 35km)
# - distante: Entorno ou interior do estado (> 35km)

ZONE_MAPPINGS = {
    # Distrito Federal e Entorno
    "df": {
        "central": [
            "plano piloto", "asa norte", "asa sul", "sudoeste", "octogonal", 
            "noroeste", "lago sul", "lago norte", "cruzeiro", "setor militar",
            "setor de club", "vila planalto", "varjao"
        ],
        "metropolitana": [
            "taguatinga", "aguas claras", "águas claras", "guara", "guará",
            "vicente pires", "ceilandia", "ceilândia", "samambaia", "nucleo bandeirante",
            "núcleo bandeirante", "riacho fundo", "candangolandia", "candangolândia",
            "arniqueira", "park way", "sobradinho", "recanto das emas", "gama", "santa maria"
        ],
        "distante": [
            "valparaiso", "valparaíso", "aguas lindas", "águas lindas", "novo gama",
            "luziania", "luziânia", "cidade ocidental", "formosa", "planaltina",
            "braslandia", "brazlândia", "itapoa", "itapoã", "paranoa", "paranoá", "sao sebastiao", "são sebastião"
        ]
    },
    # São Paulo
    "sp": {
        "central": [
            "centro", "bela vista", "consolação", "consolacao", "pinheiros", "vila mariana",
            "moema", "perdizes", "itaim bibi", "jardins", "cerqueira cesar", "santa cecilia",
            "higienopolis", "higienópolis", "paraíso", "paraiso", "santana", "tatuape", "tatuapé",
            "vila madalena", "morumbi", "lapa", "mooca", "saúde", "saude"
        ],
        "metropolitana": [
            "guarulhos", "santo andre", "santo andré", "sao bernardo", "são bernardo",
            "sao caetano", "são caetano", "osasco", "barueri", "diadema", "alphaville",
            "carapicuiba", "carapicuíba", "cotia", "taboao da serra", "taboão da serra",
            "maua", "mauá", "itaquaquecetuba", "mogi das cruzes", "suzano"
        ],
        "distante": [
            "campinas", "sorocaba", "santos", "baixada santista", "jundiai", "jundiaí",
            "sao jose dos campos", "são josé dos campos", "ribeirao preto", "ribeirão preto",
            "piracicaba", "bauru", "americana", "taubate", "taubaté"
        ]
    },
    # Rio de Janeiro
    "rj": {
        "central": [
            "copacabana", "ipanema", "leblon", "botafogo", "flamengo", "catete",
            "laranjeiras", "centro", "tijuca", "barra da tijuca", "recreio", "recreio dos bandeirantes",
            "humaita", "humaitá", "lagoa", "sao conrado", "são conrado", "maracana", "maracanã"
        ],
        "metropolitana": [
            "meier", "méier", "madureira", "campo grande", "bangu", "ilha do governador",
            "jacarepagua", "jacarepaguá", "niteroi", "niterói", "sao goncalo", "são gonçalo"
        ],
        "distante": [
            "duque de caxias", "nova iguacu", "nova iguaçu", "belford roxo", "sao joao de meriti",
            "são joão de meriti", "itaborai", "itaboraí", "mage", "magé", "petropolis", "petrópolis",
            "teresopolis", "teresópolis", "marica", "maricá", "cabo frio"
        ]
    }
}

def analyze_location_proximity(location_raw: str, state_uf: str = "df") -> Tuple[str, str]:
    """
    Analisa a string de localização do anúncio e retorna:
    - (nome_da_zona_identificada, nivel_distancia)
    nivel_distancia pode ser 'central', 'metropolitana' ou 'distante'.
    """
    if not location_raw:
        return "Região Geral", "central"

    loc_lower = location_raw.lower()
    uf_key = state_uf.lower().strip()
    
    # Se a UF não estiver cadastrada explicitamente, tenta deduzir ou usa DF/SP como padrão
    regions_to_check = [uf_key] if uf_key in ZONE_MAPPINGS else ["df", "sp", "rj"]

    for r in regions_to_check:
        mapping = ZONE_MAPPINGS.get(r, {})
        
        # 1. Checa zona central
        for place in mapping.get("central", []):
            if place in loc_lower:
                return place.title(), "central"

        # 2. Checa zona metropolitana
        for place in mapping.get("metropolitana", []):
            if place in loc_lower:
                return place.title(), "metropolitana"

        # 3. Checa zona distante / entorno
        for place in mapping.get("distante", []):
            if place in loc_lower:
                return f"{place.title()} (Entorno)", "distante"

    # Se não deu match específico, extrai o primeiro token antes de vírgula ou traço
    clean_name = location_raw.split(",")[0].split("-")[0].strip()
    return clean_name or "Localização Geral", "central"
