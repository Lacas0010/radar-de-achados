# 🎯 Radar de Achados 2.0 | OLX Brasil & Facebook Marketplace

> Comparador e localizador inteligente de itens usados com **Shadcn UI (Zinc Dark)**, **análise estatística IQR contra golpes**, **detecção de submodelos por Regex/NLP**, **Modo Sentinela 24/7 com Webhooks para Discord/Telegram** e **extração direta de API/GraphQL**.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Playwright](https://img.shields.io/badge/Playwright-1.40+-2EAD33.svg?style=flat&logo=playwright&logoColor=white)](https://playwright.dev)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?style=flat&logo=python&logoColor=white)](https://python.org)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-Shadcn_Zinc-06B6D4.svg?style=flat&logo=tailwindcss&logoColor=white)](https://tailwindcss.com)

---

## ✨ Principais Funcionalidades

### 1. 🧠 Inteligência de Busca e Filtragem
- **Detecção de Modelo por Regex/NLP:** Identifica automaticamente versões e submodelos em títulos descuidos (ex.: `OLED`, `V1`, `V2`, `Lite`, `Desbloqueado`, `Bloqueado`, `Chip Picofly`, `RP2040`, `PS5 Slim`, `64GB`, `128GB`, etc.) gerando facetas em chips clicáveis no topo da listagem.
- **Margem de Segurança por Desvio Interquartil (IQR):** Calcula quartis ($Q1, Q3$) e o intervalo interquartil ($\text{IQR} = Q3 - Q1$). Se o preço for inferior a $Q1 - 1.5 \times \text{IQR}$, o anúncio é rotulado como **`⚠️ Preço Suspeito (Possível Golpe)`** e isolado em uma aba própria, protegendo você de fraudes ou itens com defeitos ocultos.
- **Filtro de Raio Geográfico Real:** Mapeamento inteligente de bairros e cidades em zonas: `📍 Central / Metrô`, `🚗 Região Metropolitana` e `⚠️ Distante / Entorno` para planejar retiradas presenciais seguras.

### 2. ⚡ Robustez e Bypass de Renderização DOM
- **OLX Direct `__NEXT_DATA__`:** Extração direta do payload JSON injetado pelo Next.js no HTML cru, capturando galeria completa de fotos em alta resolução, localização detalhada e data em milissegundos sem aguardar seletores voláteis.
- **Facebook Marketplace GraphQL Interception:** Escuta em tempo real da rota `/api/graphql/` da Meta via `page.on("response", ...)`, capturando as entidades de classificados em JSON puro.
- **Anti-Detecção (Stealth Playwright):** Camuflagem de WebGL, spoofing de headers, desativação de `navigator.webdriver` e reutilização de sessão (`storage_state.json`).

### 3. 🚨 Modo Sentinela 24/7 (Background Worker)
- **Monitoramento em Segundo Plano:** Roda periodicamente (a cada 10, 15, 30 ou 60 minutos) procurando novidades e itens abaixo do teto de preço configurado.
- **Disparo de Webhooks para Discord & Telegram:** Envia cards visuais (Embeds) contendo foto do produto, título, valor anunciado, percentual de economia e link direto clicável.
- **Histórico de Preços e Variações (SQLite):** Rastreia reduções de valor ao longo do tempo. Quando o anunciante baixa o preço, o card recebe a badge **`📉 Baixou R$ 250!`**.

### 4. 🎨 Frontend Shadcn UI (Zinc Dark Theme)
- **Calculadora de Contraproposta no Card (Oferta PIX):** Simula automaticamente 3 propostas realistas no PIX (-10% Leve, -15% Recomendado, -20% Agressivo) com botão de 1 clique para copiar mensagem pronta para o chat do vendedor.
- **Galeria de Fotos com Modal / Carousel:** Permite navegar por todas as fotos capturadas do produto sem sair do painel, com setas, miniaturas e atalhos de teclado (`ESC`, `←`, `→`).
- **Tabs de Filtro Rápido:** Abas para alternar entre `Todos`, `🔥 Super Achados`, `💎 Ótimo Preço`, `📉 Quedas`, `📦 Recentes` e `⚠️ Suspeitos`.
- **Alternância Grade / Lista:** Modos de visualização responsivos com persistência no `localStorage`.
- **Exportação Dupla:** Baixe os dados filtrados em formato `.csv` ou dump analítico `.json`.

---

## 🏗️ Arquitetura do Projeto

```
achador_de_itens/
│
├── core/
│   ├── olx_scraper.py         # Extração rápida via __NEXT_DATA__ e fallback DOM
│   ├── fb_marketplace.py      # Interceptação GraphQL e extração por spans
│   ├── database.py            # Persistência SQLite, histórico e quedas de preço
│   ├── sentinela.py           # Worker de monitoramento 24/7 e webhooks Discord/Telegram
│   └── stealth.py             # Args de inicialização e evasão antibot do Playwright
│
├── engine/
│   ├── analyzer.py            # Cálculo de mediana, percentis IQR e pontuação
│   ├── nlp_parser.py          # Extrator Regex/NLP de submodelos e especificações
│   ├── geo.py                 # Classificador de zonas geográficas e proximidade
│   └── regions.py             # Mapeamento de capitais e regiões brasileiras
│
├── models/
│   └── item.py                # Dataclass Anuncio com tipagem completa e serialização
│
├── templates/
│   └── index.html             # Interface web completa no padrão Shadcn UI
│
├── static/
│   ├── css/style.css          # Design tokens (Zinc Dark), animações e modais
│   └── js/app.js              # Lógica de estados, tabs, calculadora PIX e galeria
│
├── app.py                     # API REST FastAPI e servidor web
├── main.py                    # Orquestrador unificado concorrente e modo CLI
├── iniciar.bat                # Inicializador automatizado com 1 clique para Windows
├── buscar_terminal.bat        # Inicializador rápido para terminal
└── requirements.txt           # Dependências do projeto
```

---

## 🚀 Como Iniciar

### Pré-requisitos
- **Python 3.10+** instalado no sistema.
- Navegadores do Playwright instalados.

### 1. Inicialização em 1 Clique (Windows)
Basta dar dois cliques no arquivo:
```cmd
iniciar.bat
```
O script verifica o ambiente, libera a porta 8000 se necessário, inicia o servidor FastAPI e disponibiliza o painel em:
👉 **`http://localhost:8000`**

---

### 2. Execução Manual via Terminal

1. **Clone o repositório:**
   ```bash
   git clone https://github.com/SEU_USUARIO/radar-de-achados.git
   cd radar-de-achados
   ```

2. **Crie e ative um ambiente virtual (opcional, recomendado):**
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   ```

3. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

4. **Inicie o servidor Web:**
   ```bash
   python app.py
   ```

---

### 3. Caça de Ofertas via Terminal (CLI)

Você também pode utilizar o Radar diretamente pelo terminal:

```bash
# Busca interativa simples:
python main.py

# Busca direta com filtros:
python main.py --termo "Switch OLED" --uf df --min 1200 --max 1800

# Filtrar apenas novos anúncios desde a última varredura:
python main.py --termo "PS5" --uf sp --apenas-novos
```

---

## 🔔 Configurando Alertas no Discord / Telegram

1. Abra o painel em `http://localhost:8000`.
2. Clique no botão **Sentinela** na barra superior.
3. Configure o termo (ex.: `Nintendo Switch OLED`), a região e o teto máximo de preço.
4. Cole o link do seu Webhook do Discord ou Token do Bot do Telegram.
5. Clique em **Ativar Sentinela**. O sistema passará a vigiar em background e notificará seu canal assim que uma pechincha for encontrada!

---

## 🛡️ Licença
Distribuído sob a licença MIT. Consulte `LICENSE` para mais informações.
