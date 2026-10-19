import asyncio
import io
import csv
import json
import statistics
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from engine.regions import list_all_regions, get_region_info
from main import buscar_itens
from core.sentinela import configurar_sentinela, parar_sentinela, get_sentinela_instance

app = FastAPI(
    title="Achador de Itens Usados - OLX & Facebook Marketplace",
    description="Localizador e comparador de ofertas de itens usados por região com inteligência IQR e sentinela",
    version="2.0.0"
)

# Montar arquivos estáticos e templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

class SearchRequest(BaseModel):
    query: str
    region: str = "df_brasilia"
    sources: List[str] = ["olx", "facebook"]
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    exclude_keywords: Optional[List[str]] = None
    sort_by: str = "price_asc"
    ignore_fake_prices: bool = True
    apenas_novos: bool = False

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Página inicial com o painel de busca e resultados."""
    regions = list_all_regions()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"regions": regions}
    )

@app.get("/api/regions")
async def get_regions():
    """Retorna lista de regiões brasileiras mapeadas."""
    return {"regions": list_all_regions()}

@app.post("/api/search")
async def api_search(req: SearchRequest):
    """Executa a busca concorrente com análise IQR, NLP de submodelos e zonas geográficas."""
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="O termo de busca não pode ser vazio.")

    # Extrai o estado (UF) da chave da região (ex: 'df_brasilia' -> 'df')
    uf = req.region.split('_')[0] if '_' in req.region else req.region
    if uf == "brasil":
        uf = "sp"

    anuncios = await asyncio.to_thread(
        buscar_itens,
        termo=req.query,
        uf=uf,
        preco_min=req.min_price or 0.0,
        preco_max=req.max_price,
        ignorar_palavras=req.exclude_keywords,
        fontes=req.sources,
        apenas_novos=req.apenas_novos
    )

    items_dict = [a.to_dict() for a in anuncios]
    
    # Coleta de facetas e submodelos disponíveis no lote
    submodels_set = set()
    zones_set = set()
    for it in items_dict:
        for sm in it.get("submodels", []):
            submodels_set.add(sm)
        if it.get("geo_zone"):
            zones_set.add(it.get("geo_zone"))

    # Ordenação conforme seleção do usuário
    if req.sort_by == "price_desc":
        items_dict.sort(key=lambda x: x["price"], reverse=True)
    elif req.sort_by == "best_deal":
        items_dict.sort(key=lambda x: (not x.get("is_suspicious", False), x["deal_score"]), reverse=True)
    elif req.sort_by == "price_drop":
        items_dict.sort(key=lambda x: (x.get("price_drop") or 0.0), reverse=True)
    else:
        items_dict.sort(key=lambda x: x["price"])

    # Estatísticas
    total = len(items_dict)
    prices = [it["price"] for it in items_dict if not it.get("is_suspicious")] if total > 0 else [0.0]
    if not prices:
        prices = [it["price"] for it in items_dict] or [0.0]

    min_p = min(prices) if prices else 0.0
    max_p = max(prices) if prices else 0.0
    med_p = statistics.median(prices) if prices else 0.0
    avg_p = statistics.mean(prices) if prices else 0.0
    
    super_deals = sum(1 for it in items_dict if it.get("deal_tag") == "SUPER_ACHADO" and not it.get("is_suspicious"))
    novos_count = sum(1 for it in items_dict if it.get("is_novo"))
    price_drops = sum(1 for it in items_dict if (it.get("price_drop") or 0.0) > 0)
    suspicious_count = sum(1 for it in items_dict if it.get("is_suspicious"))

    return {
        "success": True,
        "query": req.query,
        "region_info": get_region_info(req.region),
        "data": {
            "items": items_dict,
            "available_submodels": sorted(list(submodels_set)),
            "available_zones": sorted(list(zones_set)),
            "stats": {
                "total": total,
                "min_price": min_p,
                "max_price": max_p,
                "median_price": round(med_p, 2),
                "avg_price": round(avg_p, 2),
                "super_deals_count": super_deals,
                "novos_count": novos_count,
                "price_drops_count": price_drops,
                "suspicious_count": suspicious_count
            }
        }
    }

class ExportRequest(BaseModel):
    items: List[dict]
    filename: Optional[str] = "achados_usados"

@app.post("/api/export/csv")
async def export_csv(req: ExportRequest):
    """Exporta os resultados da busca em formato CSV estruturado para download."""
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    
    writer.writerow([
        "Origem", "Título", "Preço (R$)", "Preço Anterior (R$)", "Queda (R$)", 
        "Classificação", "Economia (%)", "Submodelos", "Zona / Bairro", "Distância", "Suspeito", "Link Anúncio"
    ])
    
    for item in req.items:
        writer.writerow([
            item.get("source", item.get("plataforma", "")),
            item.get("title", item.get("titulo", "")),
            item.get("price", 0.0),
            item.get("previous_price", ""),
            item.get("price_drop", ""),
            item.get("classificacao", item.get("deal_tag", "")),
            f"{item.get('deal_score', 0.0)}%",
            ", ".join(item.get("submodels", [])),
            item.get("geo_zone", item.get("location", "")),
            item.get("distance_level", "central"),
            "SIM" if item.get("is_suspicious") else "NAO",
            item.get("url", "")
        ])
        
    output.seek(0)
    csv_bytes = output.getvalue().encode("utf-8-sig")
    fname = req.filename if req.filename.endswith(".csv") else f"{req.filename}.csv"
    
    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={fname}"}
    )

@app.post("/api/export/json")
async def export_json(req: ExportRequest):
    """Exporta o dump analítico completo dos resultados em formato JSON."""
    fname = req.filename if req.filename.endswith(".json") else f"{req.filename}.json"
    json_bytes = json.dumps(req.items, ensure_ascii=False, indent=2).encode("utf-8")
    
    return StreamingResponse(
        io.BytesIO(json_bytes),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={fname}"}
    )

# ==============================================================================
# Rotas do Modo Sentinela (Monitoramento Ativo 24/7 em Background)
# ==============================================================================

class SentinelaStartRequest(BaseModel):
    termo: str
    region: str = "df_brasilia"
    intervalo_minutos: int = 15
    preco_teto: Optional[float] = None
    apenas_super_achados: bool = True
    webhook_url: Optional[str] = None
    webhook_tipo: str = "discord"

@app.post("/api/sentinela/start")
async def api_start_sentinela(req: SentinelaStartRequest):
    """Inicia ou reconfigura o monitoramento automático em background com alertas webhook."""
    if not req.termo.strip():
        raise HTTPException(status_code=400, detail="O termo de monitoramento é obrigatório.")
        
    uf = req.region.split('_')[0] if '_' in req.region else req.region
    task = configurar_sentinela(
        termo=req.termo.strip(),
        uf=uf,
        intervalo_minutos=req.intervalo_minutos,
        preco_teto=req.preco_teto,
        apenas_super_achados=req.apenas_super_achados,
        webhook_url=req.webhook_url.strip() if req.webhook_url else None,
        webhook_tipo=req.webhook_tipo
    )
    return {"success": True, "message": "Modo Sentinela ativado com sucesso!", "sentinela": task.to_dict()}

@app.post("/api/sentinela/stop")
async def api_stop_sentinela():
    """Para o monitoramento sentinela ativo."""
    parado = parar_sentinela()
    return {"success": True, "message": "Modo Sentinela pausado com sucesso.", "ativo": False}

@app.get("/api/sentinela/status")
async def api_sentinela_status():
    """Retorna o status atual, contagem de alertas e histórico do Sentinela."""
    inst = get_sentinela_instance()
    if not inst:
        return {"ativo": False, "sentinela": None}
    return {"ativo": inst.ativo, "sentinela": inst.to_dict()}

if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 60)
    print("  RADAR DE ACHADOS | SERVIDOR WEB 2.0 (SHADCN UI)")
    print("=" * 60)
    print("Acesse no seu navegador: http://localhost:8000")
    print("Pressione Ctrl + C para encerrar.")
    print("=" * 60 + "\n")
    uvicorn.run(app, host="127.0.0.1", port=8000)
