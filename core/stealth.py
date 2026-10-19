"""
Módulo de ajuste fino anti-detecção (Stealth) para o Playwright Chromium.
Elimina flags de automação, emula navegadores reais e configura cabeçalhos autênticos.
"""

from typing import List, Dict, Any, Optional

STEALTH_LAUNCH_ARGS: List[str] = [
    '--disable-blink-features=AutomationControlled',
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--disable-infobars',
    '--disable-dev-shm-usage',
    '--disable-background-timer-throttling',
    '--disable-backgrounding-occluded-windows',
    '--disable-renderer-backgrounding',
    '--ignore-certificate-errors',
    '--ignore-certificate-errors-spki-list',
    '--window-position=0,0'
]

REAL_USER_HEADERS: Dict[str, str] = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Sec-Ch-Ua": '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1"
}

STEALTH_INIT_SCRIPT = """
// 1. Elimina navigator.webdriver
delete Object.getPrototypeOf(navigator).webdriver;
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined,
    configurable: true
});

// 2. Simula o objeto window.chrome presente em navegadores reais
if (!window.chrome) {
    window.chrome = {
        runtime: {},
        loadTimes: function() {},
        csi: function() {},
        app: {}
    };
}

// 3. Emula idiomas pt-BR nativos
Object.defineProperty(navigator, 'languages', {
    get: () => ['pt-BR', 'pt', 'en-US', 'en'],
    configurable: true
});

// 4. Emula lista de plugins reais para não retornar lista vazia
Object.defineProperty(navigator, 'plugins', {
    get: () => [
        { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
        { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
        { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' }
    ],
    configurable: true
});

// 5. Spoof de renderizador WebGL para evitar SwiftShader/Mesa de instâncias headless
try {
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        // UNMASKED_VENDOR_WEBGL
        if (parameter === 37445) {
            return 'Intel Inc.';
        }
        // UNMASKED_RENDERER_WEBGL
        if (parameter === 37446) {
            return 'Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0';
        }
        return getParameter.apply(this, arguments);
    };
} catch(e) {}
"""

def get_stealth_context_options(storage_state_path: Optional[str] = None) -> Dict[str, Any]:
    """Retorna o dicionário de opções para context.new_context() com stealth ativo."""
    opts = {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
        "viewport": {"width": 1280, "height": 850},
        "locale": "pt-BR",
        "timezone_id": "America/Sao_Paulo",
        "extra_http_headers": REAL_USER_HEADERS,
        "device_scale_factor": 1,
        "has_touch": False,
        "is_mobile": False
    }
    if storage_state_path:
        opts["storage_state"] = storage_state_path
    return opts

def apply_stealth_to_page(page):
    """Injeta os scripts de stealth na página antes de qualquer script externo rodar."""
    page.add_init_script(STEALTH_INIT_SCRIPT)
