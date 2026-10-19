"""
Ficheiro de testes temporário e inspeção para a OLX.
Use para testar URLs, seletores e respostas antes de integrar no core.
"""
from core.olx_scraper import scrape_olx

def test_probe():
    termo = "ps5"
    uf = "df"
    print(f"=== TESTE DE EXTRAÇÃO: OLX ({termo} em {uf.upper()}) ===")
    
    anuncios = scrape_olx(termo=termo, uf=uf, preco_min=500, preco_max=4500, max_items=10)
    
    print(f"\nTotal extraído no probe: {len(anuncios)}")
    for idx, a in enumerate(anuncios, 1):
        print(f"#{idx} [R$ {a.preco:,.2f}] {a.titulo[:50]} | Local: {a.localizacao} | Img: {bool(a.imagem_url)}")
        print(f"    URL: {a.url}")

if __name__ == "__main__":
    test_probe()
