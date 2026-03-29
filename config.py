import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    BASE_URL = "https://www.wildberries.ru/__internal/search/exactmatch/ru/common/v18/search"

    TIMEOUT_SEC = int(os.getenv("WB_TIMEOUT_SEC", "20"))
    RETRY_TOTAL = int(os.getenv("WB_RETRY_TOTAL", "3"))
    MIN_DELAY_SEC = float(os.getenv("WB_MIN_DELAY_SEC", "1.0"))
    MAX_DELAY_SEC = float(os.getenv("WB_MAX_DELAY_SEC", "2.5"))

    CARD_TIMEOUT_SEC = float(os.getenv("WB_CARD_TIMEOUT_SEC", "3"))
    CARD_HOST_ATTEMPTS = int(os.getenv("WB_CARD_HOST_ATTEMPTS", "6"))

    HEADERS = {
        "User-Agent": os.getenv(
            "WB_USER_AGENT",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:148.0) Gecko/20100101 Firefox/148.0",
        ),
        "Accept": "*/*",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "deviceid": os.getenv("WB_DEVICE_ID", "site_1dd4cff355d34b62bc2f8f53385d0565"),
        "x-queryid": os.getenv("WB_QUERY_ID", "qid478298887177453046320260326130756"),
        "x-requested-with": "XMLHttpRequest",
        "x-spa-version": os.getenv("WB_SPA_VERSION", "14.3.1"),
        "x-userid": os.getenv("WB_USER_ID", "0"),
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }

    PARAMS = {
        "ab_daily_autotest": "test_group2",
        "appType": "1",
        "curr": "rub",
        "dest": "-1257786",
        "hide_vflags": "4294967296",
        "lang": "ru",
        "page": "1",
        "query": "null",
        "resultset": "catalog",
        "spp": "30",
        "suppressSpellcheck": "false",
    }

    COOKIES = {}
    token = os.getenv("WB_X_WBAAS_TOKEN")
    if token:
        COOKIES["x_wbaas_token"] = token


settings = Settings()

