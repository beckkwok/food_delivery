from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import gspread
from google.oauth2.service_account import Credentials

from config.settings import GOOGLE_SHEETS_CREDENTIALS_PATH, GOOGLE_SHEET_ID
from sheets.schema import SHEET_DEFINITIONS
from utils.helpers import generate_order_id


class SheetsClient:
    _instance: SheetsClient | None = None

    def __new__(cls) -> SheetsClient:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_file(
            GOOGLE_SHEETS_CREDENTIALS_PATH, scopes=scopes
        )
        self.gc = gspread.authorize(creds)
        self.sh = self.gc.open_by_key(GOOGLE_SHEET_ID)
        self._initialized = True

    # -- helpers -----------------------------------------------------------

    def _worksheet(self, name: str):
        return self.sh.worksheet(name)

    def _ensure_header(self, ws, headers: list[str]) -> None:
        existing = ws.row_values(1)
        if existing != headers:
            ws.clear()
            ws.append_row(headers)

    def _append_row(self, sheet_name: str, row: list[Any]) -> None:
        ws = self._worksheet(sheet_name)
        ws.append_row(row, value_input_option="USER_ENTERED")

    def _get_all_records(self, sheet_name: str) -> list[dict[str, Any]]:
        ws = self._worksheet(sheet_name)
        return ws.get_all_records()

    # -- menu --------------------------------------------------------------

    def get_menu(self) -> list[dict[str, Any]]:
        return self._get_all_records("Menu")

    def get_menu_json(self) -> str:
        items = self.get_menu()
        return json.dumps([it for it in items if str(it.get("Available", "TRUE")).upper() == "TRUE"], ensure_ascii=False)

    # -- orders ------------------------------------------------------------

    def create_order(self, customer_name: str, telephone: str, telegram_id: int,
                     items: list[dict], total: float, allergies: str,
                     instructions: str, delivery_address: str,
                     delivery_time: str, language: str) -> str:
        order_id = generate_order_id()
        now = datetime.now().isoformat()
        row = [
            order_id,
            str(telegram_id),
            customer_name,
            telephone,
            json.dumps(items, ensure_ascii=False),
            total,
            allergies,
            instructions,
            delivery_address,
            delivery_time,
            "New",
            language,
            now,
            now,
        ]
        self._append_row("Orders", row)
        return order_id

    def get_orders_by_status(self, *statuses: str) -> list[dict[str, Any]]:
        all_orders = self._get_all_records("Orders")
        if not statuses:
            return all_orders
        return [o for o in all_orders if o.get("Status") in statuses]

    def get_orders_by_date(self, date_str: str) -> list[dict[str, Any]]:
        all_orders = self._get_all_records("Orders")
        return [o for o in all_orders if o.get("CreatedAt", "").startswith(date_str)]

    def update_order_status(self, order_id: str, new_status: str) -> None:
        ws = self._worksheet("Orders")
        records = ws.get_all_records()
        header = ws.row_values(1)
        status_col = header.index("Status") + 1
        updated_col = header.index("UpdatedAt") + 1
        for i, rec in enumerate(records, start=2):
            if rec.get("OrderID") == order_id:
                ws.update_cell(i, status_col, new_status)
                ws.update_cell(i, updated_col, datetime.now().isoformat())
                break

    # -- customers ---------------------------------------------------------

    def upsert_customer(self, telegram_id: int, first_name: str,
                        last_name: str = "", phone: str = "",
                        address: str = "") -> None:
        ws = self._worksheet("Customers")
        records = ws.get_all_records()
        header = ws.row_values(1)

        name_col = header.index("FirstName") + 1
        phone_col = header.index("Phone") + 1
        addr_col = header.index("Address") + 1
        id_col = header.index("TelegramID") + 1

        for i, rec in enumerate(records, start=2):
            if str(rec.get("TelegramID")) == str(telegram_id):
                if first_name:
                    ws.update_cell(i, name_col, first_name)
                if phone:
                    ws.update_cell(i, phone_col, phone)
                if address:
                    ws.update_cell(i, addr_col, address)
                return

        now = datetime.now().isoformat()
        row = [
            f"CUST-{telegram_id}",
            str(telegram_id),
            first_name,
            last_name,
            phone,
            address,
            0,
            "",
            now,
        ]
        ws.append_row(row, value_input_option="USER_ENTERED")

    # -- feedback ----------------------------------------------------------

    def write_feedback(self, order_id: str, telegram_id: int,
                       customer_name: str, rating: int,
                       comment: str) -> None:
        now = datetime.now().isoformat()
        row = [
            f"FB-{order_id}",
            order_id,
            str(telegram_id),
            customer_name,
            rating,
            comment,
            now,
        ]
        self._append_row("Feedback", row)

    # -- report ------------------------------------------------------------

    def get_monthly_data(self, year: int, month: int) -> dict[str, Any]:
        prefix = f"{year}-{month:02d}"
        orders = self._get_all_records("Orders")
        feedback = self._get_all_records("Feedback")
        filtered_orders = [o for o in orders if o.get("CreatedAt", "").startswith(prefix)]
        filtered_feedback = [f for f in feedback if f.get("Date", "").startswith(prefix)]
        total_revenue = sum(float(o.get("Total", 0)) for o in filtered_orders)
        return {
            "year": year,
            "month": month,
            "total_orders": len(filtered_orders),
            "total_revenue": total_revenue,
            "average_order": total_revenue / len(filtered_orders) if filtered_orders else 0,
            "orders": filtered_orders,
            "feedback": filtered_feedback,
        }
