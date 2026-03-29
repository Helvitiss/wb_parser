from scraper import WbScraper


QUERY = "пальто"
MAX_PAGES = 1
OUTPUT_PATH = "output/products.csv"


def main() -> None:
    scraper = WbScraper()
    products = scraper.get_all_products(query=QUERY, max_pages=MAX_PAGES)
    scraper.save_to_csv(products, OUTPUT_PATH)
    print(f"Saved {len(products)} products to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
