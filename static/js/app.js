/**
 * Radar de Achados 2.0 - Frontend Application Logic (Shadcn UI Version)
 * Features:
 * - Filtros em Tabs (Todos, Super Achados, Ótimo Preço, Quedas, Mais Recentes, Suspeitos)
 * - Facetas Dinâmicas de Submodelos (NLP/Regex: OLED, V2, Desbloqueado, etc.)
 * - Calculadora de Contraproposta no Card com cópia de mensagem PIX
 * - Galeria de Fotos em Modal / Carousel
 * - Modo Sentinela 24/7 com Webhooks Discord / Telegram
 * - Exportação em CSV e JSON
 * - Alternância entre Grade e Lista
 */

let currentItems = [];
let filteredItems = [];
let currentQuery = "";
let currentRegionName = "";
let currentView = localStorage.getItem("radar_view_mode") || "grid";
let activeTab = "all";
let activeSubmodelFilter = null;

// Estado da Galeria
let galleryCurrentImages = [];
let galleryCurrentIndex = 0;

document.addEventListener("DOMContentLoaded", () => {
    // Inicializar ícones Lucide
    if (window.lucide) {
        lucide.createIcons();
    }

    const searchForm = document.getElementById("search-form");
    const queryInput = document.getElementById("search-query");
    const regionSelect = document.getElementById("search-region");
    const toggleFiltersBtn = document.getElementById("toggle-filters-btn");
    const advancedFiltersPanel = document.getElementById("advanced-filters-panel");
    const filtersChevron = document.getElementById("filters-chevron");
    const exportCsvBtn = document.getElementById("export-csv-btn");
    const exportJsonBtn = document.getElementById("export-json-btn");
    const viewGridBtn = document.getElementById("view-grid-btn");
    const viewListBtn = document.getElementById("view-list-btn");

    // Sentinela Modal Elements
    const openSentinelaBtn = document.getElementById("open-sentinela-btn");
    const closeSentinelaBtn = document.getElementById("close-sentinela-btn");
    const sentinelaModal = document.getElementById("sentinela-modal");
    const sentinelaBackdrop = document.getElementById("sentinela-backdrop");
    const sentinelaForm = document.getElementById("sentinela-form");
    const sentinelaStopBtn = document.getElementById("sentinela-stop-btn");

    // Galeria Modal Elements
    const galleryModal = document.getElementById("gallery-modal");
    const galleryBackdrop = document.getElementById("gallery-backdrop");
    const closeGalleryBtn = document.getElementById("close-gallery-btn");
    const galleryPrevBtn = document.getElementById("gallery-prev-btn");
    const galleryNextBtn = document.getElementById("gallery-next-btn");

    // Inicializar botões de visualização (Grade / Lista)
    if (viewGridBtn && viewListBtn) {
        viewGridBtn.addEventListener("click", () => setViewMode("grid"));
        viewListBtn.addEventListener("click", () => setViewMode("list"));
        updateViewButtons();
    }

    // Toggle de filtros avançados
    toggleFiltersBtn.addEventListener("click", () => {
        const isHidden = advancedFiltersPanel.classList.contains("hidden");
        if (isHidden) {
            advancedFiltersPanel.classList.remove("hidden");
            filtersChevron.classList.add("rotate-180");
        } else {
            advancedFiltersPanel.classList.add("hidden");
            filtersChevron.classList.remove("rotate-180");
        }
    });


    // Tabs de filtragem rápida (Shadcn Tabs)
    const tabButtons = document.querySelectorAll(".tab-filter-btn");
    tabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetTab = btn.getAttribute("data-tab");
            setActiveTab(targetTab);
        });
    });

    // Submissão do formulário de busca
    searchForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const query = queryInput.value.trim();
        if (!query) return;

        const region = regionSelect.value;
        const selectedRegionText = regionSelect.options[regionSelect.selectedIndex].text;
        
        const sources = [];
        if (document.getElementById("source_olx").checked) sources.push("olx");
        if (document.getElementById("source_facebook").checked) sources.push("facebook");

        if (sources.length === 0) {
            showToast("Selecione ao menos uma plataforma de busca.", "destructive");
            return;
        }

        const minPriceVal = document.getElementById("min_price").value;
        const maxPriceVal = document.getElementById("max_price").value;
        const sortBy = document.getElementById("sort_by").value;
        const excludeKeywordsRaw = document.getElementById("exclude_keywords").value;

        const minPrice = minPriceVal ? parseFloat(minPriceVal) : null;
        const maxPrice = maxPriceVal ? parseFloat(maxPriceVal) : null;
        const apenasNovosEl = document.getElementById("apenas_novos");
        const apenasNovos = apenasNovosEl ? apenasNovosEl.checked : false;
        const excludeKeywords = excludeKeywordsRaw
            ? excludeKeywordsRaw.split(",").map(k => k.trim()).filter(Boolean)
            : [];

        await executeSearch({
            query,
            region,
            regionName: selectedRegionText,
            sources,
            minPrice,
            maxPrice,
            sortBy,
            excludeKeywords,
            apenasNovos
        });
    });

    // Exportar CSV
    exportCsvBtn.addEventListener("click", () => exportData("csv"));
    // Exportar JSON
    exportJsonBtn.addEventListener("click", () => exportData("json"));

    // Controles do Modal Sentinela
    openSentinelaBtn.addEventListener("click", () => {
        sentinelaModal.classList.remove("hidden");
        carregarStatusSentinela();
    });
    closeSentinelaBtn.addEventListener("click", () => sentinelaModal.classList.add("hidden"));
    sentinelaBackdrop.addEventListener("click", () => sentinelaModal.classList.add("hidden"));

    sentinelaForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const termo = document.getElementById("sentinela-termo").value.trim();
        const region = document.getElementById("sentinela-region").value;
        const intervalo = parseInt(document.getElementById("sentinela-intervalo").value);
        const tetoVal = document.getElementById("sentinela-teto").value;
        const precoTeto = tetoVal ? parseFloat(tetoVal) : null;
        const tipoWebhook = document.getElementById("sentinela-tipo-webhook").value;
        const webhookUrl = document.getElementById("sentinela-webhook-url").value.trim();

        try {
            const resp = await fetch("/api/sentinela/start", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    termo,
                    region,
                    intervalo_minutos: intervalo,
                    preco_teto: precoTeto,
                    apenas_super_achados: true,
                    webhook_url: webhookUrl || null,
                    webhook_tipo: tipoWebhook
                })
            });
            const res = await resp.json();
            if (resp.ok) {
                showToast("Modo Sentinela 24/7 ativado com sucesso!");
                sentinelaModal.classList.add("hidden");
                atualizarBadgeSentinela(true);
            } else {
                showToast(res.detail || "Erro ao ativar Sentinela.", "destructive");
            }
        } catch (err) {
            showToast("Falha na conexão com o Sentinela.", "destructive");
        }
    });

    sentinelaStopBtn.addEventListener("click", async () => {
        try {
            await fetch("/api/sentinela/stop", { method: "POST" });
            showToast("Modo Sentinela pausado.");
            atualizarBadgeSentinela(false);
            sentinelaModal.classList.add("hidden");
        } catch (e) {
            showToast("Erro ao pausar Sentinela.", "destructive");
        }
    });

    // Controles do Modal da Galeria
    closeGalleryBtn.addEventListener("click", fecharGaleria);
    galleryBackdrop.addEventListener("click", fecharGaleria);
    galleryPrevBtn.addEventListener("click", () => navegarGaleria(-1));
    galleryNextBtn.addEventListener("click", () => navegarGaleria(1));

    document.addEventListener("keydown", (e) => {
        if (!galleryModal.classList.contains("hidden")) {
            if (e.key === "Escape") fecharGaleria();
            if (e.key === "ArrowLeft") navegarGaleria(-1);
            if (e.key === "ArrowRight") navegarGaleria(1);
        }
    });

    // Carregar status inicial do sentinela
    carregarStatusSentinela();
});

/**
 * Executa a busca assíncrona na API com análise IQR e enriquecimento
 */
async function executeSearch(params) {
    const { query, region, regionName, sources, minPrice, maxPrice, sortBy, excludeKeywords, apenasNovos } = params;

    const loadingSection = document.getElementById("loading-state");
    const resultsSection = document.getElementById("results-section");
    const statsSection = document.getElementById("stats-section");
    const emptySection = document.getElementById("empty-state");
    const searchBtn = document.getElementById("search-btn");
    const btnText = searchBtn.querySelector(".btn-text");
    const btnLoader = searchBtn.querySelector(".btn-loader");
    const loadingStepText = document.getElementById("loading-step-text");

    loadingSection.classList.remove("hidden");
    resultsSection.classList.add("hidden");
    statsSection.classList.add("hidden");
    emptySection.classList.add("hidden");
    btnText.classList.add("hidden");
    btnLoader.classList.remove("hidden");
    btnLoader.classList.add("inline-flex");
    searchBtn.disabled = true;

    const messages = [
        "Interceptando payload __NEXT_DATA__ da OLX Brasil...",
        "Escutando respostas GraphQL /api/graphql/ do Facebook...",
        "Analisando distribuição de preços e calculando margem IQR...",
        "Classificando submodelos via Regex/NLP e mapeando zonas..."
    ];
    let msgIdx = 0;
    const progressInterval = setInterval(() => {
        msgIdx = (msgIdx + 1) % messages.length;
        loadingStepText.textContent = messages[msgIdx];
    }, 2200);

    try {
        const response = await fetch("/api/search", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                query,
                region,
                sources,
                min_price: minPrice,
                max_price: maxPrice,
                exclude_keywords: excludeKeywords,
                sort_by: sortBy,
                ignore_fake_prices: true,
                apenas_novos: apenasNovos
            })
        });

        clearInterval(progressInterval);

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || "Falha ao buscar itens.");
        }

        const data = await response.json();
        const result = data.data;

        currentItems = result.items || [];
        currentQuery = query;
        currentRegionName = regionName;
        activeSubmodelFilter = null;
        activeTab = "all";

        renderResults(query, regionName, result);

    } catch (error) {
        clearInterval(progressInterval);
        console.error("Erro na busca:", error);
        showToast(`Erro na busca: ${error.message}`, "destructive");
    } finally {
        loadingSection.classList.add("hidden");
        btnText.classList.remove("hidden");
        btnLoader.classList.add("hidden");
        btnLoader.classList.remove("inline-flex");
        searchBtn.disabled = false;
    }
}

/**
 * Renderiza métricas, facetas de submodelos e cards de resultados
 */
function renderResults(query, regionName, data) {
    const stats = data.stats;
    const items = data.items;
    const availableSubmodels = data.available_submodels || [];

    const resultsSection = document.getElementById("results-section");
    const statsSection = document.getElementById("stats-section");
    const emptySection = document.getElementById("empty-state");

    if (!items || items.length === 0) {
        emptySection.classList.remove("hidden");
        statsSection.classList.add("hidden");
        resultsSection.classList.add("hidden");
        return;
    }

    // Atualizar Métricas
    document.getElementById("stat-total").textContent = stats.total;
    document.getElementById("stat-min-price").textContent = formatBRL(stats.min_price);
    document.getElementById("stat-median-price").textContent = formatBRL(stats.median_price);
    document.getElementById("stat-super-deals").textContent = stats.super_deals_count;
    document.getElementById("stat-price-drops").textContent = stats.price_drops_count || 0;

    // Alerta de Itens Suspeitos (IQR Outliers)
    const suspiciousBadge = document.getElementById("stat-suspicious-badge");
    const suspiciousCountEl = document.getElementById("stat-suspicious-count");
    const tabSuspiciousBtn = document.getElementById("tab-btn-suspicious");
    
    if (stats.suspicious_count > 0) {
        suspiciousCountEl.textContent = stats.suspicious_count;
        suspiciousBadge.classList.remove("hidden");
        tabSuspiciousBtn.classList.remove("hidden");
        document.getElementById("tab-count-suspicious").textContent = stats.suspicious_count;
    } else {
        suspiciousBadge.classList.add("hidden");
        tabSuspiciousBtn.classList.add("hidden");
    }

    statsSection.classList.remove("hidden");

    // Título e Informações dos Resultados
    document.getElementById("results-query-label").textContent = `"${query}"`;
    document.getElementById("results-location-label").textContent = `Região: ${regionName} • ${stats.total} anúncios validados`;

    // Atualizar Contadores das Tabs
    updateTabCounters(items);

    // Renderizar Chips de Facetas de Submodelos (NLP/Regex)
    renderSubmodelFacets(availableSubmodels);

    // Aplicar filtros e renderizar itens
    applyFiltersAndRender();

    resultsSection.classList.remove("hidden");
}

/**
 * Atualiza contadores nas abas superiores
 */
function updateTabCounters(items) {
    const total = items.length;
    const superCount = items.filter(it => it.deal_tag === "SUPER_ACHADO" && !it.is_suspicious).length;
    const greatCount = items.filter(it => it.deal_tag === "OTIMO_PRECO" && !it.is_suspicious).length;
    const dropsCount = items.filter(it => (it.price_drop || 0) > 0).length;

    document.getElementById("tab-count-all").textContent = total;
    document.getElementById("tab-count-super").textContent = superCount;
    document.getElementById("tab-count-great").textContent = greatCount;
    document.getElementById("tab-count-drops").textContent = dropsCount;
}

/**
 * Renderiza os chips de facetas para submodelos detectados por Regex/NLP
 */
function renderSubmodelFacets(submodels) {
    const container = document.getElementById("facets-container");
    const wrapper = document.getElementById("submodels-chips-wrapper");
    wrapper.innerHTML = `<span class="text-xs text-muted-foreground mr-1">Submodelos e Versões:</span>`;

    if (!submodels || submodels.length === 0) {
        container.classList.add("hidden");
        return;
    }

    // Botão Limpar Filtro
    const allBtn = document.createElement("button");
    allBtn.type = "button";
    allBtn.className = `rounded-full px-2.5 py-0.5 text-[11px] font-medium transition-all ${!activeSubmodelFilter ? 'bg-primary text-primary-foreground font-semibold' : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'}`;
    allBtn.textContent = "Todos os Modelos";
    allBtn.addEventListener("click", () => {
        activeSubmodelFilter = null;
        renderSubmodelFacets(submodels);
        applyFiltersAndRender();
    });
    wrapper.appendChild(allBtn);

    submodels.forEach(sm => {
        const chip = document.createElement("button");
        chip.type = "button";
        const isActive = activeSubmodelFilter === sm;
        chip.className = `rounded-full px-2.5 py-0.5 text-[11px] font-medium transition-all ${isActive ? 'bg-primary text-primary-foreground font-semibold shadow-sm' : 'bg-secondary text-secondary-foreground hover:bg-secondary/80 border border-border/40'}`;
        chip.textContent = sm;
        chip.addEventListener("click", () => {
            activeSubmodelFilter = isActive ? null : sm;
            renderSubmodelFacets(submodels);
            applyFiltersAndRender();
        });
        wrapper.appendChild(chip);
    });

    container.classList.remove("hidden");
}

/**
 * Alterna a aba ativa e re-filtra a listagem
 */
function setActiveTab(tab) {
    activeTab = tab;
    const tabButtons = document.querySelectorAll(".tab-filter-btn");
    tabButtons.forEach(btn => {
        const isSelected = btn.getAttribute("data-tab") === tab;
        if (isSelected) {
            btn.classList.add("bg-background", "text-foreground", "shadow-sm");
            btn.classList.remove("text-muted-foreground");
        } else {
            btn.classList.remove("bg-background", "text-foreground", "shadow-sm");
            btn.classList.add("text-muted-foreground");
        }
    });
    applyFiltersAndRender();
}

/**
 * Aplica os filtros ativos de Tabs e Facetas e renderiza os cards
 */
function applyFiltersAndRender() {
    let result = [...currentItems];

    // 1. Filtro da Tab Ativa
    if (activeTab === "super_deals") {
        result = result.filter(it => it.deal_tag === "SUPER_ACHADO" && !it.is_suspicious);
    } else if (activeTab === "great_deals") {
        result = result.filter(it => it.deal_tag === "OTIMO_PRECO" && !it.is_suspicious);
    } else if (activeTab === "price_drops") {
        result = result.filter(it => (it.price_drop || 0) > 0);
    } else if (activeTab === "newest") {
        result.sort((a, b) => (b.is_novo ? 1 : 0) - (a.is_novo ? 1 : 0));
    } else if (activeTab === "suspicious") {
        result = result.filter(it => it.is_suspicious);
    }

    // 2. Filtro de Submodelo Selecionado
    if (activeSubmodelFilter) {
        result = result.filter(it => it.submodels && it.submodels.includes(activeSubmodelFilter));
    }

    filteredItems = result;
    renderCurrentItems();
}

/**
 * Renderiza os itens no container respeitando o layout (grade ou lista)
 */
function renderCurrentItems() {
    const listingsGrid = document.getElementById("listings-grid");
    if (!listingsGrid) return;

    if (currentView === "grid") {
        listingsGrid.className = "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6";
    } else {
        listingsGrid.className = "flex flex-col space-y-4";
    }

    listingsGrid.innerHTML = "";

    if (filteredItems.length === 0) {
        listingsGrid.innerHTML = `
            <div class="col-span-full rounded-xl border border-border bg-card/60 p-8 text-center text-muted-foreground space-y-2">
                <p class="text-sm font-medium">Nenhum anúncio corresponde aos filtros selecionados.</p>
                <button type="button" class="text-xs text-primary underline" onclick="resetFilters()">Limpar filtros</button>
            </div>
        `;
        return;
    }

    filteredItems.forEach(item => {
        const card = currentView === "grid" ? createShadcnGridCard(item) : createShadcnListCard(item);
        listingsGrid.appendChild(card);
    });

    if (window.lucide) {
        lucide.createIcons();
    }
}

function resetFilters() {
    activeTab = "all";
    activeSubmodelFilter = null;
    setActiveTab("all");
}

/**
 * Altera o modo de visualização entre grade e lista
 */
function setViewMode(mode) {
    if (currentView === mode) return;
    currentView = mode;
    try {
        localStorage.setItem("radar_view_mode", mode);
    } catch (e) {}
    updateViewButtons();
    renderCurrentItems();
}

function updateViewButtons() {
    const viewGridBtn = document.getElementById("view-grid-btn");
    const viewListBtn = document.getElementById("view-list-btn");
    if (!viewGridBtn || !viewListBtn) return;

    const activeClasses = ["bg-background", "text-foreground", "shadow-sm"];
    const inactiveClasses = ["text-muted-foreground", "hover:text-foreground", "hover:bg-background/40"];

    if (currentView === "grid") {
        viewGridBtn.classList.add(...activeClasses);
        viewGridBtn.classList.remove(...inactiveClasses);
        viewListBtn.classList.remove(...activeClasses);
        viewListBtn.classList.add(...inactiveClasses);
    } else {
        viewListBtn.classList.add(...activeClasses);
        viewListBtn.classList.remove(...inactiveClasses);
        viewGridBtn.classList.remove(...activeClasses);
        viewGridBtn.classList.add(...inactiveClasses);
    }
}

/**
 * Extrai e normaliza os dados de um item para exibição nos cards
 */
function getCardData(item) {
    const isOlx = item.source === "OLX" || item.plataforma === "OLX";
    const sourceBadgeClass = isOlx ? "bg-purple-600/90 text-white" : "bg-blue-600/90 text-white";
    const sourceLabel = isOlx ? "OLX" : "Facebook";

    let dealBadgeHtml = "";
    if (item.is_suspicious) {
        dealBadgeHtml = `
            <span class="inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-semibold bg-rose-600 text-white shadow-sm backdrop-blur" title="${escapeHtml(item.suspicious_reason || 'Outlier estatístico inferior')}">
                <i data-lucide="alert-triangle" class="h-3 w-3"></i>
                Preço Suspeito (IQR)
            </span>
        `;
    } else if (item.deal_tag === "SUPER_ACHADO" || item.classificacao?.includes("SUPER")) {
        dealBadgeHtml = `
            <span class="inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-semibold bg-emerald-500/90 text-white shadow-sm backdrop-blur">
                <i data-lucide="flame" class="h-3 w-3"></i>
                Super Achado (${item.deal_score || item.desconto_percentual}% off)
            </span>
        `;
    } else if (item.deal_tag === "OTIMO_PRECO" || item.classificacao?.includes("ÓTIMO")) {
        dealBadgeHtml = `
            <span class="inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-semibold bg-sky-500/90 text-white shadow-sm backdrop-blur">
                <i data-lucide="gem" class="h-3 w-3"></i>
                Ótimo Preço (${item.deal_score || item.desconto_percentual}% off)
            </span>
        `;
    } else {
        dealBadgeHtml = `
            <span class="inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium bg-secondary/80 text-muted-foreground border border-border/60 shadow-sm backdrop-blur">
                Preço de Mercado
            </span>
        `;
    }

    const isNovo = item.is_novo !== false;
    const novoBadgeHtml = isNovo ? `
        <span class="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-bold bg-primary text-primary-foreground tracking-wide uppercase shadow-sm">
            <i data-lucide="sparkles" class="h-2.5 w-2.5"></i>
            Novo
        </span>
    ` : '';

    // Badge de Queda de Preço
    const priceDrop = item.price_drop || 0;
    const dropBadgeHtml = priceDrop > 0 ? `
        <span class="inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-bold bg-amber-500/15 text-amber-400 border border-amber-500/30 shadow-sm" title="Preço anterior: ${item.previous_price_formatted}">
            <i data-lucide="trending-down" class="h-3 w-3"></i>
            Baixou R$ ${priceDrop.toFixed(0)}!
        </span>
    ` : '';

    // Badge de Zona Geográfica
    let geoBadgeClass = "bg-secondary text-muted-foreground border-border/40";
    if (item.distance_level === "central") {
        geoBadgeClass = "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
    } else if (item.distance_level === "metropolitana") {
        geoBadgeClass = "bg-sky-500/10 text-sky-400 border-sky-500/20";
    } else if (item.distance_level === "distante") {
        geoBadgeClass = "bg-amber-500/10 text-amber-400 border-amber-500/20";
    }

    // Chips de submodelos para o card
    const submodelChips = (item.submodels || []).slice(0, 3).map(sm => `
        <span class="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium bg-secondary text-secondary-foreground border border-border/50">
            ${escapeHtml(sm)}
        </span>
    `).join("");

    // Imagem
    const imgUrl = item.image || item.imagem_url;
    const imagesList = item.images && item.images.length > 0 ? item.images : (imgUrl ? [imgUrl] : []);
    const photosCount = imagesList.length;

    let imageHtml = "";
    if (imgUrl && imgUrl.startsWith("http")) {
        imageHtml = `
            <img 
                src="${escapeHtml(imgUrl)}" 
                alt="${escapeHtml(item.title || item.titulo)}" 
                referrerpolicy="no-referrer"
                loading="lazy" 
                class="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105 cursor-pointer" 
                onclick="event.stopPropagation(); abrirGaleriaModal('${escapeHtml(item.id || item.url)}')"
                onerror="this.classList.add('hidden'); this.nextElementSibling.classList.remove('hidden');"
            >
            <div class="hidden h-full w-full flex items-center justify-center text-muted-foreground bg-muted">
                <i data-lucide="image-off" class="h-8 w-8 opacity-40"></i>
            </div>
        `;
    } else {
        imageHtml = `<div class="h-full w-full flex items-center justify-center text-muted-foreground bg-muted"><i data-lucide="image" class="h-8 w-8 opacity-40"></i></div>`;
    }

    return {
        titleText: item.title || item.titulo || "",
        priceFormatted: item.price_formatted || formatBRL(item.price || item.preco),
        rawPrice: item.price || item.preco || 0,
        locationText: item.location || item.localizacao || "Localização não informada",
        geoZone: item.geo_zone || "Região Principal",
        geoBadgeClass,
        dateText: item.date_posted || item.data_publicacao || "",
        discountScore: item.deal_score || item.desconto_percentual || 0,
        sourceLabel,
        sourceBadgeClass,
        dealBadgeHtml,
        novoBadgeHtml,
        dropBadgeHtml,
        submodelChips,
        imageHtml,
        imagesList,
        photosCount,
        itemId: item.id || item.url,
        url: item.url || "#"
    };
}

/**
 * Cria o Card vertical no formato de Grade (Grid)
 */
function createShadcnGridCard(item) {
    const data = getCardData(item);
    const card = document.createElement("article");
    card.className = "shadcn-card rounded-xl border border-border bg-card text-card-foreground shadow-sm overflow-hidden flex flex-col justify-between group relative";

    card.innerHTML = `
        <div>
            <!-- Imagem e Badges Superiores -->
            <div class="relative w-full aspect-[4/3] bg-muted overflow-hidden border-b border-border/40">
                ${data.imageHtml}
                <div class="absolute top-2.5 left-2.5 right-2.5 flex items-center justify-between gap-1 pointer-events-none">
                    <div class="flex items-center gap-1.5">
                        ${data.novoBadgeHtml}
                        <span class="inline-flex items-center rounded px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wider ${data.sourceBadgeClass} shadow-sm backdrop-blur">
                            ${data.sourceLabel}
                        </span>
                    </div>
                    ${data.dealBadgeHtml}
                </div>

                <!-- Botão Flutuante de Galeria -->
                ${data.photosCount > 1 ? `
                    <button 
                        type="button" 
                        class="absolute bottom-2 right-2 rounded-md bg-black/70 hover:bg-black/90 text-white text-[11px] font-medium px-2 py-1 flex items-center gap-1 backdrop-blur shadow"
                        onclick="abrirGaleriaModal('${escapeHtml(data.itemId)}')"
                        title="Ver todas as ${data.photosCount} fotos"
                    >
                        <i data-lucide="images" class="h-3 w-3"></i>
                        <span>${data.photosCount} fotos</span>
                    </button>
                ` : ''}
            </div>

            <!-- Corpo do Card -->
            <div class="p-4 space-y-3">
                <!-- Badges de Submodelos e Queda de Preço -->
                <div class="flex flex-wrap items-center gap-1.5 min-h-[20px]">
                    ${data.dropBadgeHtml}
                    ${data.submodelChips}
                </div>

                <h3 class="text-sm font-semibold text-foreground line-clamp-2 leading-snug tracking-tight" title="${escapeHtml(data.titleText)}">
                    ${escapeHtml(data.titleText)}
                </h3>

                <div class="flex items-baseline gap-2">
                    <span class="text-2xl font-bold tracking-tight text-foreground">${escapeHtml(data.priceFormatted)}</span>
                    ${data.discountScore > 0 ? `<span class="inline-flex items-center rounded px-1.5 py-0.5 text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">-${data.discountScore}%</span>` : ''}
                </div>

                <!-- Localização e Proximidade -->
                <div class="pt-2 border-t border-border/40 space-y-1.5 text-xs text-muted-foreground">
                    <div class="flex items-center justify-between gap-2">
                        <div class="flex items-center gap-1.5 truncate">
                            <i data-lucide="map-pin" class="h-3.5 w-3.5 flex-shrink-0"></i>
                            <span class="truncate">${escapeHtml(data.locationText)}</span>
                        </div>
                        <span class="inline-flex items-center rounded px-1.5 py-0.2 text-[10px] font-medium border ${data.geoBadgeClass} flex-shrink-0">
                            ${escapeHtml(data.geoZone)}
                        </span>
                    </div>

                    ${data.dateText ? `
                    <div class="flex items-center gap-1.5 truncate text-[11px]">
                        <i data-lucide="clock" class="h-3 w-3 flex-shrink-0"></i>
                        <span class="truncate">${escapeHtml(data.dateText)}</span>
                    </div>
                    ` : ''}
                </div>
            </div>
        </div>

        <!-- Footer com Botões de Ação e Calculadora PIX -->
        <div class="p-4 pt-0 space-y-2">
            <div class="grid grid-cols-2 gap-2">
                <!-- Botão Oferta PIX (Calculadora de Contraproposta) -->
                <button 
                    type="button" 
                    class="inline-flex items-center justify-center gap-1.5 rounded-md border border-border bg-secondary hover:bg-secondary/80 text-foreground h-9 px-2 text-xs font-medium transition-colors shadow-sm"
                    onclick="abrirCalculadoraPix(this, ${data.rawPrice}, '${escapeHtml(data.titleText.replace(/'/g, ''))}')"
                    title="Simular contraproposta no PIX"
                >
                    <i data-lucide="badge-percent" class="h-3.5 w-3.5 text-emerald-400"></i>
                    <span>Oferta PIX</span>
                </button>

                <!-- Botão Abrir Anúncio -->
                <a 
                    href="${escapeHtml(data.url)}" 
                    target="_blank" 
                    rel="noopener noreferrer" 
                    class="inline-flex items-center justify-center gap-1.5 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 h-9 px-2 text-xs font-medium transition-colors shadow-sm"
                >
                    <span>Ver no ${data.sourceLabel}</span>
                    <i data-lucide="external-link" class="h-3.5 w-3.5"></i>
                </a>
            </div>
        </div>
    `;

    return card;
}

/**
 * Cria o Card horizontal no formato de Lista (List)
 */
function createShadcnListCard(item) {
    const data = getCardData(item);
    const card = document.createElement("article");
    card.className = "shadcn-card rounded-xl border border-border bg-card text-card-foreground shadow-sm overflow-hidden flex flex-col md:flex-row items-stretch group relative";

    card.innerHTML = `
        <!-- Imagem e Badges (Lateral no desktop, superior no mobile) -->
        <div class="relative w-full md:w-64 h-52 md:h-auto flex-shrink-0 bg-muted overflow-hidden border-b md:border-b-0 md:border-r border-border/40">
            ${data.imageHtml}
            <div class="absolute top-2.5 left-2.5 right-2.5 flex items-center justify-between gap-1 pointer-events-none">
                <div class="flex items-center gap-1.5">
                    ${data.novoBadgeHtml}
                    <span class="inline-flex items-center rounded px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wider ${data.sourceBadgeClass} shadow-sm backdrop-blur">
                        ${data.sourceLabel}
                    </span>
                </div>
                ${data.dealBadgeHtml}
            </div>

            ${data.photosCount > 1 ? `
                <button 
                    type="button" 
                    class="absolute bottom-2 right-2 rounded-md bg-black/70 hover:bg-black/90 text-white text-[11px] font-medium px-2 py-1 flex items-center gap-1 backdrop-blur shadow"
                    onclick="abrirGaleriaModal('${escapeHtml(data.itemId)}')"
                >
                    <i data-lucide="images" class="h-3 w-3"></i>
                    <span>${data.photosCount} fotos</span>
                </button>
            ` : ''}
        </div>

        <!-- Conteúdo do Anúncio em Lista -->
        <div class="flex-1 p-5 flex flex-col justify-between gap-4">
            <div class="space-y-2">
                <div class="flex flex-wrap items-center gap-2">
                    ${data.dropBadgeHtml}
                    ${data.submodelChips}
                    <span class="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium border ${data.geoBadgeClass}">
                        ${escapeHtml(data.geoZone)}
                    </span>
                </div>

                <h3 class="text-base font-semibold text-foreground tracking-tight leading-snug line-clamp-2 hover:text-primary transition-colors" title="${escapeHtml(data.titleText)}">
                    <a href="${escapeHtml(data.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(data.titleText)}</a>
                </h3>

                <div class="flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-muted-foreground pt-1">
                    <div class="flex items-center gap-1.5">
                        <i data-lucide="map-pin" class="h-3.5 w-3.5 flex-shrink-0"></i>
                        <span>${escapeHtml(data.locationText)}</span>
                    </div>
                    ${data.dateText ? `
                    <div class="flex items-center gap-1.5">
                        <i data-lucide="clock" class="h-3.5 w-3.5 flex-shrink-0"></i>
                        <span>${escapeHtml(data.dateText)}</span>
                    </div>
                    ` : ''}
                </div>
            </div>

            <!-- Preço e Botões de Ação -->
            <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pt-3 border-t border-border/40">
                <div class="flex items-baseline gap-2">
                    <span class="text-2xl font-bold tracking-tight text-foreground">${escapeHtml(data.priceFormatted)}</span>
                    ${data.discountScore > 0 ? `<span class="inline-flex items-center rounded px-2 py-0.5 text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">-${data.discountScore}%</span>` : ''}
                </div>

                <div class="flex items-center gap-2">
                    <button 
                        type="button" 
                        class="inline-flex items-center justify-center gap-1.5 rounded-md border border-border bg-secondary hover:bg-secondary/80 text-foreground h-9 px-3 text-xs font-medium transition-colors shadow-sm"
                        onclick="abrirCalculadoraPix(this, ${data.rawPrice}, '${escapeHtml(data.titleText.replace(/'/g, ''))}')"
                    >
                        <i data-lucide="badge-percent" class="h-3.5 w-3.5 text-emerald-400"></i>
                        <span>Oferta PIX</span>
                    </button>

                    <a 
                        href="${escapeHtml(data.url)}" 
                        target="_blank" 
                        rel="noopener noreferrer" 
                        class="inline-flex items-center justify-center gap-2 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 h-9 px-4 text-xs font-medium transition-colors shadow-sm"
                    >
                        <span>Ver no ${data.sourceLabel}</span>
                        <i data-lucide="external-link" class="h-3.5 w-3.5"></i>
                    </a>
                </div>
            </div>
        </div>
    `;

    return card;
}

/**
 * Calculadora de Contraproposta no Card (Popover Shadcn)
 */
function abrirCalculadoraPix(buttonEl, price, title) {
    // Remove qualquer popover existente
    const existing = document.getElementById("pix-calculator-popover");
    if (existing) {
        existing.remove();
        if (existing._triggerButton === buttonEl) return;
    }

    if (!price || price <= 0) {
        showToast("Preço do anúncio inválido para contraproposta.", "destructive");
        return;
    }

    const offer10 = Math.round(price * 0.90);
    const offer15 = Math.round(price * 0.85);
    const offer20 = Math.round(price * 0.80);

    const popover = document.createElement("div");
    popover.id = "pix-calculator-popover";
    popover._triggerButton = buttonEl;
    popover.className = "absolute z-50 w-72 rounded-xl border border-border bg-card p-4 shadow-2xl text-foreground text-xs space-y-3 animate-in fade-in";

    popover.innerHTML = `
        <div class="flex items-center justify-between border-b border-border/40 pb-2">
            <span class="font-semibold text-foreground flex items-center gap-1.5">
                <i data-lucide="calculator" class="h-4 w-4 text-emerald-400"></i>
                Contraproposta no PIX
            </span>
            <button type="button" class="text-muted-foreground hover:text-foreground p-0.5" onclick="this.closest('#pix-calculator-popover').remove()">
                <i data-lucide="x" class="h-3.5 w-3.5"></i>
            </button>
        </div>

        <p class="text-[11px] text-muted-foreground">Escolha uma faixa realista para copiar mensagem pronta para o chat:</p>

        <div class="space-y-1.5">
            <button type="button" class="w-full flex items-center justify-between p-2 rounded-lg border border-border/60 hover:bg-secondary/60 text-left transition-colors" onclick="copiarMensagemPix('${escapeHtml(title)}', ${offer10}, '-10%')">
                <div>
                    <span class="font-bold text-foreground">R$ ${offer10.toLocaleString('pt-BR')}</span>
                    <span class="text-[10px] text-muted-foreground ml-1.5">(-10% Leve)</span>
                </div>
                <span class="text-[10px] font-medium text-emerald-400">Copiar</span>
            </button>

            <button type="button" class="w-full flex items-center justify-between p-2 rounded-lg border border-border/60 hover:bg-secondary/60 text-left transition-colors" onclick="copiarMensagemPix('${escapeHtml(title)}', ${offer15}, '-15%')">
                <div>
                    <span class="font-bold text-foreground">R$ ${offer15.toLocaleString('pt-BR')}</span>
                    <span class="text-[10px] text-emerald-400 font-semibold ml-1.5">(-15% Recomendado)</span>
                </div>
                <span class="text-[10px] font-medium text-emerald-400">Copiar</span>
            </button>

            <button type="button" class="w-full flex items-center justify-between p-2 rounded-lg border border-border/60 hover:bg-secondary/60 text-left transition-colors" onclick="copiarMensagemPix('${escapeHtml(title)}', ${offer20}, '-20%')">
                <div>
                    <span class="font-bold text-foreground">R$ ${offer20.toLocaleString('pt-BR')}</span>
                    <span class="text-[10px] text-amber-400 ml-1.5">(-20% Agressivo)</span>
                </div>
                <span class="text-[10px] font-medium text-emerald-400">Copiar</span>
            </button>
        </div>
    `;

    // Posicionamento relativo ao card
    const card = buttonEl.closest(".shadcn-card");
    card.appendChild(popover);
    popover.style.bottom = "60px";
    popover.style.right = "16px";

    if (window.lucide) {
        lucide.createIcons();
    }
}

/**
 * Monta e copia a mensagem personalizada de oferta para o chat
 */
function copiarMensagemPix(title, valor, tag) {
    const cleanTitle = title.length > 30 ? title.substring(0, 30) + '...' : title;
    const msg = `Olá! Vi seu anúncio do ${cleanTitle}. Consegue fechar em R$ ${valor.toLocaleString('pt-BR')} no PIX retirando em mãos hoje?`;

    navigator.clipboard.writeText(msg).then(() => {
        showToast(`Mensagem de oferta (R$ ${valor.toLocaleString('pt-BR')}) copiada!`);
        const popover = document.getElementById("pix-calculator-popover");
        if (popover) popover.remove();
    }).catch(() => {
        showToast("Não foi possível copiar automaticamente para a área de transferência.", "destructive");
    });
}

/**
 * Galeria de Fotos em Modal / Carousel
 */
function abrirGaleriaModal(itemId) {
    const item = currentItems.find(it => (it.id === itemId || it.url === itemId));
    if (!item) return;

    const images = item.images && item.images.length > 0 ? item.images : (item.image ? [item.image] : []);
    if (images.length === 0) {
        showToast("Nenhuma foto disponível para este anúncio.", "destructive");
        return;
    }

    galleryCurrentImages = images;
    galleryCurrentIndex = 0;

    document.getElementById("gallery-item-title").textContent = item.title || item.titulo;
    document.getElementById("gallery-item-subtitle").textContent = `${item.price_formatted} • ${item.source} • ${item.location}`;

    atualizarExibicaoGaleria();
    document.getElementById("gallery-modal").classList.remove("hidden");
}

function fecharGaleria() {
    document.getElementById("gallery-modal").classList.add("hidden");
}

function navegarGaleria(delta) {
    const total = galleryCurrentImages.length;
    if (total <= 1) return;
    galleryCurrentIndex = (galleryCurrentIndex + delta + total) % total;
    atualizarExibicaoGaleria();
}

function atualizarExibicaoGaleria() {
    const mainImg = document.getElementById("gallery-main-img");
    const counter = document.getElementById("gallery-counter");
    const thumbnailsWrapper = document.getElementById("gallery-thumbnails");

    const total = galleryCurrentImages.length;
    mainImg.src = galleryCurrentImages[galleryCurrentIndex];
    counter.textContent = `${galleryCurrentIndex + 1} / ${total}`;

    // Miniaturas
    thumbnailsWrapper.innerHTML = "";
    galleryCurrentImages.forEach((src, idx) => {
        const thumb = document.createElement("img");
        thumb.src = src;
        thumb.referrerPolicy = "no-referrer";
        thumb.className = `h-14 w-14 object-cover rounded-md cursor-pointer border-2 transition-all ${idx === galleryCurrentIndex ? 'border-primary ring-2 ring-primary/40' : 'border-border/60 opacity-60 hover:opacity-100'}`;
        thumb.addEventListener("click", () => {
            galleryCurrentIndex = idx;
            atualizarExibicaoGaleria();
        });
        thumbnailsWrapper.appendChild(thumb);
    });

    // Ocultar setas se houver apenas 1 foto
    document.getElementById("gallery-prev-btn").style.display = total > 1 ? "flex" : "none";
    document.getElementById("gallery-next-btn").style.display = total > 1 ? "flex" : "none";
}

/**
 * Modo Sentinela: Monitoramento Ativo em Background
 */
async function carregarStatusSentinela() {
    try {
        const resp = await fetch("/api/sentinela/status");
        const data = await resp.json();
        if (data && data.sentinela) {
            atualizarBadgeSentinela(data.ativo);
            const s = data.sentinela;
            if (s.termo) document.getElementById("sentinela-termo").value = s.termo;
            if (s.preco_teto) document.getElementById("sentinela-teto").value = s.preco_teto;
            if (s.intervalo_minutos) document.getElementById("sentinela-intervalo").value = s.intervalo_minutos;

            // Histórico de Alertas
            const alertasList = document.getElementById("sentinela-alertas-lista");
            if (s.ultimos_alertas && s.ultimos_alertas.length > 0) {
                alertasList.innerHTML = s.ultimos_alertas.map(a => `
                    <div class="flex items-center justify-between p-1.5 rounded bg-secondary/50 border border-border/40 text-[11px]">
                        <span class="truncate pr-2 font-medium">${escapeHtml(a.titulo)}</span>
                        <span class="font-bold text-emerald-400 flex-shrink-0">R$ ${a.preco.toLocaleString('pt-BR')} (${a.horario})</span>
                    </div>
                `).join("");
            }
        }
    } catch (e) {
        console.warn("Falha ao carregar status do Sentinela:", e);
    }
}

function atualizarBadgeSentinela(ativo) {
    const dot = document.getElementById("sentinela-status-dot");
    if (!dot) return;
    if (ativo) {
        dot.className = "h-2 w-2 rounded-full bg-emerald-500 pulse-glow";
        dot.title = "Sentinela Ativo 24/7";
    } else {
        dot.className = "h-2 w-2 rounded-full bg-muted-foreground";
        dot.title = "Sentinela Pausado";
    }
}

/**
 * Exportação de Dados (CSV e JSON)
 */
async function exportData(format = "csv") {
    const itemsToExport = filteredItems.length > 0 ? filteredItems : currentItems;
    if (!itemsToExport || itemsToExport.length === 0) {
        showToast("Nenhum anúncio disponível para exportar.", "destructive");
        return;
    }

    const endpoint = format === "json" ? "/api/export/json" : "/api/export/csv";
    const extension = format === "json" ? "json" : "csv";
    const filename = `achados_${(currentQuery || "radar").replace(/\s+/g, '_')}.${extension}`;

    try {
        const response = await fetch(endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                items: itemsToExport,
                filename: filename
            })
        });

        if (!response.ok) throw new Error("Falha na geração do arquivo.");

        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = downloadUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(downloadUrl);
        showToast(`Arquivo ${extension.toUpperCase()} baixado com sucesso!`);
    } catch (err) {
        console.error("Erro na exportação:", err);
        showToast("Erro ao exportar arquivo.", "destructive");
    }
}

/**
 * Toast Notification (Feedback instantâneo Shadcn UI)
 */
function showToast(message, variant = "default") {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    const isDestructive = variant === "destructive";
    toast.className = `toast-enter pointer-events-auto flex items-center gap-2 rounded-lg border px-4 py-2.5 text-xs font-medium shadow-lg backdrop-blur ${
        isDestructive
            ? 'border-destructive bg-destructive text-destructive-foreground'
            : 'border-border bg-card text-foreground'
    }`;

    toast.innerHTML = `
        <i data-lucide="${isDestructive ? 'alert-circle' : 'check-circle'}" class="h-4 w-4 flex-shrink-0 ${isDestructive ? 'text-destructive-foreground' : 'text-emerald-400'}"></i>
        <span>${escapeHtml(message)}</span>
    `;

    container.appendChild(toast);
    if (window.lucide) {
        lucide.createIcons();
    }

    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transition = "opacity 0.3s ease";
        setTimeout(() => toast.remove(), 300);
    }, 3200);
}

/**
 * Utilitários de Formatação
 */
function formatBRL(val) {
    if (!val && val !== 0) return "R$ 0,00";
    return new Intl.NumberFormat("pt-BR", {
        style: "currency",
        currency: "BRL"
    }).format(val);
}

function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
