from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class Product:
    article: int
    name: str
    product_url: str
    price_rub: int | None = None
    description: str = ""
    image_urls_csv: str = ""
    characteristics_json: str = ""
    seller_name: str | None = None
    seller_url: str | None = None
    sizes_csv: str = ""
    stock_total: int | None = None
    rating: float | None = None
    feedbacks: int | None = None

    def to_row(self) -> dict[str, Any]:
        return asdict(self)

