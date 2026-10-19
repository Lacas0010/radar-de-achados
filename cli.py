import argparse
import sys
import json
import csv
from engine.regions import REGIONS, list_all_regions
from scrapers.coordinator import search_used_items

def main():
    parser = argparse.ArgumentParser(
        description="Achador de Itens Usados - OLX & Facebook Marketplace",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--item", "-i", type=str, default=None, help="Nome do item a buscar (ex: 'ps5', 'iphone 13')")
    parser.add_argument(
        "--region", "-r", type=str, default="df_brasilia",
        help="Chave da região (ex: 'df_brasilia', 'sp_capital', 'rj_capital', 'mg_bh', 'pr_curitiba', 'brasil'). Use --list-regions para ver todas."
    )
    parser.add_argument("--min", type=float, default=None, help="Preço mínimo (R$)")
    parser.add_argument("--max", type=float, default=None, help="Preço máximo (R$)")
    parser.add_argument(
        "--sources", "-s", nargs="+", default=["olx", "facebook"],
        choices=["olx", "facebook"], help="Fontes de busca (padrão: olx facebook)"
    )
    parser.add_argument(
        "--sort", choices=["price_asc", "best_deal", "price_desc"], default="price_asc",
        help="Ordenação: 'price_asc' (menor preço), 'best_deal' (maior desconto), 'price_desc'"
    )
    parser.add_argument("--exclude", nargs="+", default=None, help="Palavras a excluir (ex: quebrado defeito)")
    parser.add_argument("--export-csv", type=str, default=None, help="Caminho do arquivo CSV para exportar os resultados")
    parser.add_argument("--export-json", type=str, default=None, help="Caminho do arquivo JSON para exportar os resultados")
    parser.add_argument("--list-regions", action="store_true", help="Lista todas as regiões disponíveis e sai")

    args = parser.parse_args()

    if args.list_regions:
        print("\n=== REGIÕES DISPONÍVEIS ===")
        for r in list_all_regions():
            print(f"  • {r['key']:<15} -> {r['name']}")
        print()
        sys.exit(0)

    if not args.item:
        parser.error("O argumento --item/-i é obrigatório para realizar a busca. Ex: python cli.py --item 'ps5'")

    print("=" * 70)
    print("  ACHADOR DE ITENS USADOS | OLX & FACEBOOK MARKETPLACE")
    print("=" * 70)
    print(f"Buscando por: '{args.item}'")
    print(f"Região: {REGIONS.get(args.region, {}).get('name', args.region)}")
    print(f"Fontes: {', '.join(args.sources).upper()}")
    if args.min or args.max:
        print(f"Faixa de Preço: R$ {args.min or 0:.2f} até R$ {args.max or 'Sem limite'}")
    print("-" * 70)
    print("Buscando anúncios em tempo real... aguarde...")

    result = search_used_items(
        query=args.item,
        region_key=args.region,
        sources=args.sources,
        min_price=args.min,
        max_price=args.max,
        exclude_keywords=args.exclude,
        sort_by=args.sort
    )

    stats = result["stats"]
    items = result["items"]

    print("\n" + "=" * 70)
    print("  RESULTADOS E ANÁLISE DE MERCADO")
    print("=" * 70)
    print(f"Total de itens válidos: {stats['total']}")
    if stats['total'] > 0:
        print(f"Menor Preço Encontrado: R$ {stats['min_price']:,.2f}")
        print(f"Preço Mediano de Mercado: R$ {stats['median_price']:,.2f}")
        print(f"Preço Médio: R$ {stats['avg_price']:,.2f}")
        print(f"Super Achados identificados: {stats['super_deals_count']}")
        print("-" * 70)

        for idx, item in enumerate(items, 1):
            badge = ""
            if item["deal_tag"] == "SUPER_ACHADO":
                badge = f"[🔥 SUPER ACHADO - {item['deal_score']}% abaixo da mediana]"
            elif item["deal_tag"] == "OTIMO_PRECO":
                badge = f"[💎 ÓTIMO PREÇO - {item['deal_score']}% abaixo da mediana]"
            elif item["deal_tag"] == "PRECO_JUSTO":
                badge = "[⚖️ Preço Justo]"
            else:
                badge = "[⚠️ Acima da Média]"

            print(f"\n#{idx} [{item['source']}] {item['price_formatted']} {badge}")
            print(f"    Título: {item['title']}")
            print(f"    Localização: {item['location']}")
            if item.get("date_posted"):
                print(f"    Data: {item['date_posted']}")
            print(f"    Link: {item['url']}")

        # Exportações se solicitadas
        if args.export_csv:
            with open(args.export_csv, mode="w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(["ID", "Origem", "Título", "Preço", "Preço Formatado", "Classificação", "Score (%)", "Localização", "Data", "Link"])
                for it in items:
                    writer.writerow([
                        it["id"], it["source"], it["title"], it["price"], it["price_formatted"],
                        it["deal_tag"], it["deal_score"], it["location"], it.get("date_posted", ""), it["url"]
                    ])
            print(f"\n[+] Resultados exportados com sucesso para '{args.export_csv}'!")

        if args.export_json:
            with open(args.export_json, mode="w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"[+] Resultados exportados com sucesso para '{args.export_json}'!")
    else:
        print("Nenhum anúncio encontrado com os filtros atuais.")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    main()
