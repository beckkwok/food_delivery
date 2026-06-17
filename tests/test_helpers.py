from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

from utils.helpers import format_price, generate_order_id, language_tag


class TestGenerateOrderId:
    def test_format(self) -> None:
        with patch("utils.helpers.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 6, 17)
            mock_dt.now.strftime = datetime.strftime
            oid = generate_order_id()
        parts = oid.split("-")
        assert len(parts) == 3
        assert parts[0] == "ORD"
        assert parts[1] == "260617"
        assert len(parts[2]) == 6
        assert parts[2].isalnum()

    def test_uniqueness(self) -> None:
        ids = {generate_order_id() for _ in range(100)}
        assert len(ids) == 100


class TestFormatPrice:
    def test_integer_price(self) -> None:
        assert format_price(9) == "\u00a39.00"

    def test_float_price(self) -> None:
        assert format_price(12.50) == "\u00a312.50"

    def test_zero(self) -> None:
        assert format_price(0) == "\u00a30.00"


class TestLanguageTag:
    def test_english_only(self) -> None:
        assert language_tag("hello world") == "en"

    def test_cantonese(self) -> None:
        assert language_tag("照燒雞扒丼") == "zh"

    def test_japanese(self) -> None:
        assert language_tag("お好み焼き") == "zh"

    def test_mixed(self) -> None:
        assert language_tag("2個 teriyaki chicken 同 1個 beef bowl") == "zh"

    def test_empty(self) -> None:
        assert language_tag("") == "en"

    def test_numbers_and_symbols(self) -> None:
        assert language_tag("123!@#") == "en"
