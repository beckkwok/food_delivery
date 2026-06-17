from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from sheets.client import SheetsClient


@pytest.mark.usefixtures("mock_gspread")
class TestSheetsClient:
    def test_singleton(self) -> None:
        a = SheetsClient()
        b = SheetsClient()
        assert a is b

    def test_create_order(self, mock_gspread) -> None:
        ws = mock_gspread["ws"]
        client = SheetsClient()
        oid = client.create_order(
            customer_name="John",
            telegram_id=12345,
            items=[{"item_id": "S1", "name": "Teriyaki Chicken", "quantity": 1, "unit_price": 9.00}],
            total=9.00,
            allergies="",
            instructions="",
            delivery_address="Flat 1",
            delivery_time="12:30",
            language="en",
        )
        assert oid.startswith("ORD-")
        assert ws.append_row.called
        args = ws.append_row.call_args
        row = args[1]["values"] if "values" in args[1] else args[0][0]
        if "values" in args[1]:
            row = args[1]["values"]
        else:
            row = args[0][0] if args[0] else args[1].get("values", [])
        assert row[0] == oid
        assert row[1] == "12345"
        assert row[2] == "John"

    def test_get_menu(self, mock_gspread) -> None:
        ws = mock_gspread["ws"]
        ws.get_all_records.return_value = [
            {"ItemID": "S1", "Name_EN": "Chicken Bowl", "Available": True}
        ]
        client = SheetsClient()
        menu = client.get_menu()
        assert len(menu) == 1
        assert menu[0]["ItemID"] == "S1"

    def test_get_menu_json_filters_unavailable(self, mock_gspread) -> None:
        ws = mock_gspread["ws"]
        ws.get_all_records.return_value = [
            {"ItemID": "S1", "Name_EN": "Chicken Bowl", "Available": True},
            {"ItemID": "S2", "Name_EN": "Sold Out Item", "Available": False},
        ]
        client = SheetsClient()
        raw = client.get_menu_json()
        items = json.loads(raw)
        assert len(items) == 1
        assert items[0]["ItemID"] == "S1"

    def test_get_orders_by_status(self, mock_gspread) -> None:
        ws = mock_gspread["ws"]
        ws.get_all_records.return_value = [
            {"OrderID": "O1", "Status": "New"},
            {"OrderID": "O2", "Status": "Confirmed"},
            {"OrderID": "O3", "Status": "New"},
        ]
        client = SheetsClient()
        results = client.get_orders_by_status("New")
        assert len(results) == 2
        assert all(r["Status"] == "New" for r in results)

    def test_get_orders_by_status_all(self, mock_gspread) -> None:
        ws = mock_gspread["ws"]
        ws.get_all_records.return_value = [
            {"OrderID": "O1", "Status": "New"},
            {"OrderID": "O2", "Status": "Confirmed"},
        ]
        client = SheetsClient()
        results = client.get_orders_by_status()
        assert len(results) == 2

    def test_get_orders_by_date(self, mock_gspread) -> None:
        ws = mock_gspread["ws"]
        ws.get_all_records.return_value = [
            {"OrderID": "O1", "CreatedAt": "2026-06-17T10:00:00"},
            {"OrderID": "O2", "CreatedAt": "2026-06-16T15:00:00"},
        ]
        client = SheetsClient()
        results = client.get_orders_by_date("2026-06-17")
        assert len(results) == 1
        assert results[0]["OrderID"] == "O1"

    def test_update_order_status(self, mock_gspread) -> None:
        ws = mock_gspread["ws"]
        ws.row_values.return_value = ["OrderID", "Items", "Status", "UpdatedAt"]
        ws.get_all_records.return_value = [
            {"OrderID": "O1", "Items": "x", "Status": "New", "UpdatedAt": ""},
        ]
        client = SheetsClient()
        client.update_order_status("O1", "Confirmed")
        assert ws.update_cell.called

    def test_upsert_customer_new(self, mock_gspread) -> None:
        ws = mock_gspread["ws"]
        ws.get_all_records.return_value = []
        client = SheetsClient()
        client.upsert_customer(telegram_id=999, first_name="Alice", last_name="W")
        assert ws.append_row.called

    def test_upsert_customer_existing(self, mock_gspread) -> None:
        ws = mock_gspread["ws"]
        ws.get_all_records.return_value = [
            {"TelegramID": "999", "FirstName": "Alice"}
        ]
        client = SheetsClient()
        client.upsert_customer(telegram_id=999, first_name="Alice", last_name="W")
        assert not ws.append_row.called

    def test_write_feedback(self, mock_gspread) -> None:
        ws = mock_gspread["ws"]
        client = SheetsClient()
        client.write_feedback(
            order_id="O1", telegram_id=123, customer_name="Bob",
            rating=5, comment="Great!",
        )
        assert ws.append_row.called

    def test_get_monthly_data(self, mock_gspread, mocker) -> None:
        ws_orders = mocker.MagicMock()
        ws_orders.get_all_records.return_value = [
            {"OrderID": "O1", "Total": "20.00", "CreatedAt": "2026-06-01T12:00:00", "Status": "Delivered"},
            {"OrderID": "O2", "Total": "15.00", "CreatedAt": "2026-06-15T12:00:00", "Status": "Delivered"},
            {"OrderID": "O3", "Total": "10.00", "CreatedAt": "2026-07-01T12:00:00", "Status": "Delivered"},
        ]
        ws_feedback = mocker.MagicMock()
        ws_feedback.get_all_records.return_value = []

        sh = mock_gspread["sh"]
        sh.worksheet.side_effect = lambda name: {"Orders": ws_orders, "Feedback": ws_feedback}.get(name, mock_gspread["ws"])

        client = SheetsClient()
        report = client.get_monthly_data(2026, 6)
        assert report["year"] == 2026
        assert report["month"] == 6
        assert report["total_orders"] == 2
        assert report["total_revenue"] == 35.00
        assert report["average_order"] == 17.50
