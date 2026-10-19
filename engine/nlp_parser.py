import re
from typing import List, Dict, Any

# Padrões de detecção para modelos, submodelos, variantes e especificações
MODEL_RULES = [
    # Nintendo Switch & Modchips
    {"tag": "OLED", "pattern": r"\boled\b", "category": "submodel"},
    {"tag": "Switch V2", "pattern": r"\b(v2|vers[aã]o\s*2|bateria\s*melhorada)\b", "category": "submodel"},
    {"tag": "Switch V1", "pattern": r"\b(v1|vers[aã]o\s*1)\b", "category": "submodel"},
    {"tag": "Switch Lite", "pattern": r"\blite\b", "category": "submodel"},
    {"tag": "Desbloqueado", "pattern": r"\b(desbloqueado|desbloqueio|cfw|atmosphere|tinfoil)\b", "category": "mod"},
    {"tag": "Bloqueado", "pattern": r"\b(bloqueado|bloq|travado|original)\b", "category": "mod"},
    {"tag": "Chip Picofly", "pattern": r"\bpicofly\b", "category": "modchip"},
    {"tag": "Chip RP2040", "pattern": r"\brp\s*2040\b", "category": "modchip"},
    {"tag": "Chip HWFLY", "pattern": r"\bhwfly\b", "category": "modchip"},

    # PlayStation
    {"tag": "PS5 Slim", "pattern": r"\bps5\s*slim\b|\bslim\b(?=.*ps5)", "category": "submodel"},
    {"tag": "PS5 Pro", "pattern": r"\bps5\s*pro\b|\bpro\b(?=.*ps5)", "category": "submodel"},
    {"tag": "PS5 Fat", "pattern": r"\bps5\s*(fat|m[ií]dia\s*f[ií]sica|digital)?\b", "category": "submodel"},
    {"tag": "Com Disco / Leitor", "pattern": r"\b(com\s*leitor|m[ií]dia\s*f[ií]sica|disc\s*edition)\b", "category": "feature"},
    {"tag": "Edição Digital", "pattern": r"\b(digital\s*edition|sem\s*leitor|all\s*digital)\b", "category": "feature"},

    # Xbox
    {"tag": "Series X", "pattern": r"\bseries\s*x\b|\bxbox\s*x\b", "category": "submodel"},
    {"tag": "Series S", "pattern": r"\bseries\s*s\b|\bxbox\s*s\b", "category": "submodel"},

    # iPhone / Smartphones
    {"tag": "Pro Max", "pattern": r"\bpro\s*max\b", "category": "submodel"},
    {"tag": "Pro", "pattern": r"\bpro\b(?!.*max)", "category": "submodel"},
    {"tag": "Plus", "pattern": r"\bplus\b", "category": "submodel"},
    {"tag": "Mini", "pattern": r"\bmini\b", "category": "submodel"},

    # GPUs (NVIDIA & AMD)
    {"tag": "Ti", "pattern": r"\bti\b", "category": "submodel"},
    {"tag": "Super", "pattern": r"\bsuper\b", "category": "submodel"},
    {"tag": "XT", "pattern": r"\bxt\b", "category": "submodel"},

    # Armazenamento
    {"tag": "64GB", "pattern": r"\b64\s*gb\b", "category": "storage"},
    {"tag": "128GB", "pattern": r"\b128\s*gb\b", "category": "storage"},
    {"tag": "256GB", "pattern": r"\b256\s*gb\b", "category": "storage"},
    {"tag": "512GB", "pattern": r"\b512\s*gb\b", "category": "storage"},
    {"tag": "1TB", "pattern": r"\b1\s*tb\b", "category": "storage"},
    {"tag": "2TB", "pattern": r"\b2\s*tb\b", "category": "storage"},

    # Condição / Acessórios
    {"tag": "Na Caixa", "pattern": r"\b(na\s*caixa|com\s*caixa|caixa\s*original)\b", "category": "condition"},
    {"tag": "Impecável", "pattern": r"\b(impec[aá]vel|como\s*novo|seminovo|perfeito)\b", "category": "condition"},
    {"tag": "Com Jogos", "pattern": r"\b(com\s*jogos|\+\s*jogos|com\s*\d+\s*jogos)\b", "category": "bundle"},
    {"tag": "2 Controles", "pattern": r"\b(2\s*controles|dois\s*controles|dois\s*joysticks)\b", "category": "bundle"}
]

def extract_submodels_and_specs(text: str) -> List[str]:
    """
    Analisa título e texto do anúncio com Regex/NLP leve,
    extraindo submodelos, especificações de desbloqueio, chips e memória.
    Retorna uma lista ordenada e desduplicada de tags.
    """
    if not text:
        return []

    text_lower = text.lower()
    matched_tags = []

    for rule in MODEL_RULES:
        if re.search(rule["pattern"], text_lower, re.IGNORECASE):
            tag = rule["tag"]
            if tag not in matched_tags:
                matched_tags.append(tag)

    # Regra de coerência: Se detectou "Switch V2", "Switch Lite" ou "OLED",
    # evite manter V1 se for apenas menção incidental
    if "OLED" in matched_tags and "Switch V1" in matched_tags:
        if not re.search(r"\bv1\b", text_lower):
            matched_tags.remove("Switch V1")

    return matched_tags
