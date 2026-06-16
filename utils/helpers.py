import uuid
from datetime import datetime


def generate_order_id() -> str:
    date_part = datetime.now().strftime("%y%m%d")
    unique_part = uuid.uuid4().hex[:6].upper()
    return f"ORD-{date_part}-{unique_part}"


def format_price(amount: float) -> str:
    return f"\u00a3{amount:.2f}"


def language_tag(text: str) -> str:
    has_cjk = any("\u4e00" <= c <= "\u9fff" or "\u3040" <= c <= "\u30ff" for c in text)
    return "zh" if has_cjk else "en"
