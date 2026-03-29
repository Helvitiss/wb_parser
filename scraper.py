from __future__ import annotations

import csv
import json
import random
import time
from pathlib import Path

import loguru
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import settings
from models import Product

logger = loguru.logger


class WbScraper:
    def __init__(self, params: dict | None = None, url: str | None = None, headers: dict | None = None):
        self.params = params or settings.PARAMS
        self.url = url or settings.BASE_URL
        self.headers = headers or settings.HEADERS

        self.session = self._build_session()
        self.session.cookies.update(settings.COOKIES)

        self._basket_hosts = [f"basket-{i:02d}.wbbasket.ru" for i in range(1, 31)]
        self._basket_host_cache_by_vol: dict[int, str] = {}
        self._last_basket_host: str | None = None

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=settings.RETRY_TOTAL,
            backoff_factor=0.7,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update(self.headers)
        return session

    @staticmethod
    def _extract_price_rub(product: dict) -> int | None:
        for key in ("salePriceU", "priceU"):
            value = product.get(key)
            if isinstance(value, int):
                return value // 100

        candidates: list[int] = []
        for size in product.get("sizes") or []:
            if not isinstance(size, dict):
                continue
            price = size.get("price")
            if not isinstance(price, dict):
                continue
            for key in ("product", "basic"):
                value = price.get(key)
                if isinstance(value, int):
                    candidates.append(value // 100)

        return min(candidates) if candidates else None

    @staticmethod
    def _extract_product_url(product_id: int) -> str:
        return f"https://www.wildberries.ru/catalog/{product_id}/detail.aspx"

    @staticmethod
    def _extract_seller_url(supplier_id: int | None) -> str | None:
        if isinstance(supplier_id, int) and supplier_id > 0:
            return f"https://www.wildberries.ru/seller/{supplier_id}"
        return None

    @staticmethod
    def _extract_sizes_csv(product: dict) -> str:
        values: list[str] = []
        for size in product.get("sizes") or []:
            if not isinstance(size, dict):
                continue
            raw = (size.get("origName") or size.get("name") or "").strip()
            if raw and raw != "0" and raw not in values:
                values.append(raw)
        return ", ".join(values)

    @staticmethod
    def _build_characteristics_json(listing_product: dict, detail_card: dict | None) -> str:
        if detail_card:
            payload = {
                "grouped_options": detail_card.get("grouped_options") or [],
                "options": detail_card.get("options") or [],
            }
        else:
            meta = listing_product.get("meta") or {}
            payload = {"characteristics": meta.get("characteristics") or []}
        return json.dumps(payload, ensure_ascii=False)

    @staticmethod
    def _vol_and_part(nm_id: int) -> tuple[int, int]:
        return nm_id // 100000, nm_id // 1000

    def _candidate_hosts(self, vol: int) -> list[str]:
        hosts = self._basket_hosts.copy()

        cached = self._basket_host_cache_by_vol.get(vol)
        if cached in hosts:
            hosts.remove(cached)
            hosts.insert(0, cached)

        if self._last_basket_host in hosts:
            hosts.remove(self._last_basket_host)
            hosts.insert(0, self._last_basket_host)

        return hosts[: max(1, settings.CARD_HOST_ATTEMPTS)]

    def _load_card_json(self, nm_id: int) -> tuple[str | None, dict | None]:
        vol, part = self._vol_and_part(nm_id)

        for host in self._candidate_hosts(vol):
            url = f"https://{host}/vol{vol}/part{part}/{nm_id}/info/ru/card.json"
            try:
                response = self.session.get(url, timeout=settings.CARD_TIMEOUT_SEC)
            except requests.RequestException:
                continue

            if response.status_code != 200:
                continue

            if "application/json" not in response.headers.get("content-type", ""):
                continue

            try:
                card = response.json()
            except ValueError:
                continue

            self._basket_host_cache_by_vol[vol] = host
            self._last_basket_host = host
            return host, card

        return None, None

    @staticmethod
    def _extract_images_csv(nm_id: int, basket_host: str | None, listing_product: dict, detail_card: dict | None) -> str:
        if not basket_host:
            return ""

        photo_count = 0
        if detail_card:
            media = detail_card.get("media")
            if isinstance(media, dict):
                value = media.get("photo_count")
                if isinstance(value, int):
                    photo_count = value

        if photo_count <= 0:
            pics = listing_product.get("pics")
            if isinstance(pics, int):
                photo_count = pics

        if photo_count <= 0:
            return ""

        vol, part = nm_id // 100000, nm_id // 1000
        urls = [
            f"https://{basket_host}/vol{vol}/part{part}/{nm_id}/images/big/{index}.webp"
            for index in range(1, photo_count + 1)
        ]
        return ",".join(urls)

    def _to_product(self, listing_product: dict) -> Product | None:
        nm_id = listing_product.get("id")
        if not isinstance(nm_id, int):
            return None

        basket_host, detail_card = self._load_card_json(nm_id)
        description = ""
        if detail_card and isinstance(detail_card.get("description"), str):
            description = detail_card["description"]

        return Product(
            article=nm_id,
            name=listing_product.get("name", ""),
            product_url=self._extract_product_url(nm_id),
            price_rub=self._extract_price_rub(listing_product),
            description=description,
            image_urls_csv=self._extract_images_csv(nm_id, basket_host, listing_product, detail_card),
            characteristics_json=self._build_characteristics_json(listing_product, detail_card),
            seller_name=listing_product.get("supplier"),
            seller_url=self._extract_seller_url(listing_product.get("supplierId")),
            sizes_csv=self._extract_sizes_csv(listing_product),
            stock_total=listing_product.get("totalQuantity"),
            rating=listing_product.get("reviewRating") or listing_product.get("rating"),
            feedbacks=listing_product.get("feedbacks") or listing_product.get("nmFeedbacks"),
        )

    def _deserialize(self, page_json: dict) -> list[Product]:
        items = page_json.get("products") or []
        products: list[Product] = []

        logger.info(f"start enrich for {len(items)} products")
        for index, item in enumerate(items, start=1):
            product = self._to_product(item)
            if product:
                products.append(product)
            if index % 10 == 0:
                logger.info(f"enriched {index}/{len(items)} products")

        return products

    def scrape_by_page(self, query: str, page: int = 1) -> dict | None:
        params = self.params.copy()
        params["query"] = query
        params["page"] = str(page)

        try:
            response = self.session.get(self.url, params=params, timeout=settings.TIMEOUT_SEC)
        except requests.RequestException as exc:
            logger.error(f"request failed: query={query} page={page} error={exc}")
            return None

        if response.status_code != 200:
            if response.status_code == 498:
                logger.error(
                    "WB returned 498 (cookies expired/invalid). "
                    "Update WB_X_WBAAS_TOKEN and run again."
                )
            else:
                logger.error(f"bad status: query={query} page={page} status={response.status_code}")
            return None

        try:
            return response.json()
        except ValueError as exc:
            logger.error(f"json decode failed: query={query} page={page} error={exc}")
            return None

    def get_all_products(self, query: str, max_pages: int = 3) -> list[Product]:
        all_products: list[Product] = []

        for page in range(1, max_pages + 1):
            page_json = self.scrape_by_page(query=query, page=page)
            if page_json is None:
                break

            if page_json.get("error"):
                logger.error(f"wb error payload: query={query} page={page} payload={page_json}")
                break

            products = self._deserialize(page_json)
            logger.info(f"query={query} page={page} items={len(products)}")

            if not products:
                break

            all_products.extend(products)
            time.sleep(random.uniform(settings.MIN_DELAY_SEC, settings.MAX_DELAY_SEC))

        return all_products

    @staticmethod
    def save_to_csv(products: list[Product], output_path: str) -> None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            "product_url",
            "article",
            "name",
            "price_rub",
            "description",
            "image_urls_csv",
            "characteristics_json",
            "seller_name",
            "seller_url",
            "sizes_csv",
            "stock_total",
            "rating",
            "feedbacks",
        ]

        with path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            for product in products:
                writer.writerow(product.to_row())


WbScrapper = WbScraper
