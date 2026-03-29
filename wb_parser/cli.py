import argparse

from scraper import WbScraper


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MVP Wildberries parser")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--pages", type=int, default=3, help="Max pages to parse")
    parser.add_argument("--output", default="output/products.csv", help="CSV output path")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    scraper = WbScraper()
    products = scraper.get_all_products(query=args.query, max_pages=args.pages)
    scraper.save_to_csv(products, args.output)
    print(f"Saved {len(products)} products to {args.output}")


if __name__ == "__main__":
    main()
