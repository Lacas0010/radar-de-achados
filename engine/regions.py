"""
Mapeamento de Regiões para OLX Brasil e Facebook Marketplace.
Permite selecionar estados ou regiões metropolitanas específicas.
"""

REGIONS = {
    "df_brasilia": {
        "name": "Distrito Federal - Brasília e Entorno",
        "state": "DF",
        "olx_path": "estado-df",
        "fb_city": "brasilia"
    },
    "sp_capital": {
        "name": "São Paulo - Capital e Região Metropolitana",
        "state": "SP",
        "olx_path": "estado-sp/sao-paulo-e-regiao",
        "fb_city": "saopaulo"
    },
    "sp_campinas": {
        "name": "São Paulo - Campinas e Região",
        "state": "SP",
        "olx_path": "estado-sp/grande-campinas",
        "fb_city": "campinas"
    },
    "sp_litoral": {
        "name": "São Paulo - Baixada Santista e Litoral",
        "state": "SP",
        "olx_path": "estado-sp/baixada-santista-e-litoral-sul",
        "fb_city": "santos"
    },
    "sp_estado": {
        "name": "São Paulo - Todo o Estado",
        "state": "SP",
        "olx_path": "estado-sp",
        "fb_city": "saopaulo"
    },
    "rj_capital": {
        "name": "Rio de Janeiro - Capital e Região",
        "state": "RJ",
        "olx_path": "estado-rj/rio-de-janeiro-e-regiao",
        "fb_city": "riodejaneiro"
    },
    "rj_estado": {
        "name": "Rio de Janeiro - Todo o Estado",
        "state": "RJ",
        "olx_path": "estado-rj",
        "fb_city": "riodejaneiro"
    },
    "mg_bh": {
        "name": "Minas Gerais - Belo Horizonte e Região",
        "state": "MG",
        "olx_path": "estado-mg/belo-horizonte-e-regiao",
        "fb_city": "belohorizonte"
    },
    "mg_estado": {
        "name": "Minas Gerais - Todo o Estado",
        "state": "MG",
        "olx_path": "estado-mg",
        "fb_city": "belohorizonte"
    },
    "pr_curitiba": {
        "name": "Paraná - Curitiba e Região",
        "state": "PR",
        "olx_path": "estado-pr/curitiba-e-regiao",
        "fb_city": "curitiba"
    },
    "pr_estado": {
        "name": "Paraná - Todo o Estado",
        "state": "PR",
        "olx_path": "estado-pr",
        "fb_city": "curitiba"
    },
    "rs_poa": {
        "name": "Rio Grande do Sul - Porto Alegre e Região",
        "state": "RS",
        "olx_path": "estado-rs/regioes-de-porto-alegre-torres-e-santa-cruz-do-sul",
        "fb_city": "portoalegre"
    },
    "rs_estado": {
        "name": "Rio Grande do Sul - Todo o Estado",
        "state": "RS",
        "olx_path": "estado-rs",
        "fb_city": "portoalegre"
    },
    "sc_floripa": {
        "name": "Santa Catarina - Florianópolis e Região",
        "state": "SC",
        "olx_path": "estado-sc/florianopolis-e-regiao",
        "fb_city": "florianopolis"
    },
    "sc_estado": {
        "name": "Santa Catarina - Todo o Estado",
        "state": "SC",
        "olx_path": "estado-sc",
        "fb_city": "florianopolis"
    },
    "go_goiania": {
        "name": "Goiás - Goiânia e Região",
        "state": "GO",
        "olx_path": "estado-go/goiania-e-regiao",
        "fb_city": "goiania"
    },
    "ba_salvador": {
        "name": "Bahia - Salvador e Região",
        "state": "BA",
        "olx_path": "estado-ba/salvador",
        "fb_city": "salvador"
    },
    "pe_recife": {
        "name": "Pernambuco - Recife e Região",
        "state": "PE",
        "olx_path": "estado-pe/grande-recife",
        "fb_city": "recife"
    },
    "ce_fortaleza": {
        "name": "Ceará - Fortaleza e Região",
        "state": "CE",
        "olx_path": "estado-ce/fortaleza-e-regiao",
        "fb_city": "fortaleza"
    },
    "brasil": {
        "name": "Brasil - Todo o País (Nacional)",
        "state": "BR",
        "olx_path": "brasil",
        "fb_city": "saopaulo"
    }
}

def get_region_info(region_key: str):
    """Retorna dados de configuração da região escolhida."""
    return REGIONS.get(region_key, REGIONS["sp_capital"])

def list_all_regions():
    """Retorna lista formatada de regiões disponíveis para a UI/CLI."""
    return [
        {"key": k, "name": v["name"], "state": v["state"]}
        for k, v in REGIONS.items()
    ]
