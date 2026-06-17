from __future__ import annotations

from sheets.schema import (
    CUSTOMERS_HEADERS,
    FEEDBACK_HEADERS,
    MENU_HEADERS,
    ORDERS_HEADERS,
    SHEET_DEFINITIONS,
)


class TestOrdersHeaders:
    def test_has_required_columns(self) -> None:
        required = {"OrderID", "Items", "Total", "Status", "CreatedAt"}
        assert required.issubset(set(ORDERS_HEADERS))

    def test_length(self) -> None:
        assert len(ORDERS_HEADERS) == 14


class TestMenuHeaders:
    def test_has_required_columns(self) -> None:
        required = {"ItemID", "Name_EN", "Name_ZH", "Price", "Available"}
        assert required.issubset(set(MENU_HEADERS))

    def test_length(self) -> None:
        assert len(MENU_HEADERS) == 8


class TestCustomersHeaders:
    def test_has_required_columns(self) -> None:
        required = {"TelegramID", "FirstName", "TotalOrders"}
        assert required.issubset(set(CUSTOMERS_HEADERS))

    def test_length(self) -> None:
        assert len(CUSTOMERS_HEADERS) == 9


class TestFeedbackHeaders:
    def test_has_required_columns(self) -> None:
        required = {"OrderID", "Rating", "Comment", "Date"}
        assert required.issubset(set(FEEDBACK_HEADERS))

    def test_length(self) -> None:
        assert len(FEEDBACK_HEADERS) == 7


class TestSheetDefinitions:
    def test_all_sheets_defined(self) -> None:
        assert set(SHEET_DEFINITIONS.keys()) == {"Orders", "Menu", "Customers", "Feedback"}

    def test_increasing_tab_indices(self) -> None:
        indices = [d["tab_index"] for d in SHEET_DEFINITIONS.values()]
        assert indices == sorted(indices)
        assert len(set(indices)) == len(indices)

    def test_headers_match_sheet_name(self) -> None:
        for name, defn in SHEET_DEFINITIONS.items():
            if name == "Orders":
                assert defn["headers"] is ORDERS_HEADERS
            elif name == "Menu":
                assert defn["headers"] is MENU_HEADERS
            elif name == "Customers":
                assert defn["headers"] is CUSTOMERS_HEADERS
            elif name == "Feedback":
                assert defn["headers"] is FEEDBACK_HEADERS
