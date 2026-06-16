"""
Run this script once to create the Google Sheets tabs and seed the menu.
Usage: python seed_menu.py
"""
from __future__ import annotations

import gspread
from google.oauth2.service_account import Credentials

from config.settings import GOOGLE_SHEETS_CREDENTIALS_PATH, GOOGLE_SHEET_ID
from sheets.schema import SHEET_DEFINITIONS, MENU_HEADERS, ORDERS_HEADERS, CUSTOMERS_HEADERS, FEEDBACK_HEADERS

MENU_DATA = [
    ["S1", "Teriyaki Chicken Rice Bowl w/ Miso Soup", "照燒雞扒丼", "照り焼きチキン丼", "Set", 9.00, "🐔", True],
    ["S2", "Okonomiyaki", "大阪焼", "お好み焼き", "Set", 12.50, "", True],
    ["R1", "Beef Rice Bowl w/ Miso Soup", "牛肉飯（牛丼）", "牛丼", "Rice", 9.50, "🐮", True],
    ["R2", "Karaage Fried Chicken Rice Bowl w/ Miso Soup", "唐揚炸雞丼", "鶏の唐揚げ丼", "Rice", 9.00, "", True],
    ["R3", "Chicken & Egg Rice Bowl w/ Miso Soup", "親子丼", "鶏の親子丼", "Rice", 8.00, "🐔🥚", True],
]


def seed() -> None:
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(
        GOOGLE_SHEETS_CREDENTIALS_PATH, scopes=scopes
    )
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(GOOGLE_SHEET_ID)

    headers_map = {
        "Menu": MENU_HEADERS,
        "Orders": ORDERS_HEADERS,
        "Customers": CUSTOMERS_HEADERS,
        "Feedback": FEEDBACK_HEADERS,
    }

    for name, definition in SHEET_DEFINITIONS.items():
        try:
            ws = sh.worksheet(name)
            print(f"Worksheet '{name}' already exists — clearing and re-seeding headers.")
            ws.clear()
        except gspread.WorksheetNotFound:
            if definition["tab_index"] < len(sh.worksheets()):
                ws = sh.add_worksheet(title=name, rows=100, cols=20)
            else:
                ws = sh.add_worksheet(title=name, rows=100, cols=20)
            print(f"Created worksheet '{name}'.")

        headers = headers_map.get(name, [])
        ws.append_row(headers, value_input_option="USER_ENTERED")

    ws_menu = sh.worksheet("Menu")
    for row in MENU_DATA:
        ws_menu.append_row(row, value_input_option="USER_ENTERED")

    print("Menu seeded successfully!")
    print(f"\nSeeded {len(MENU_DATA)} menu items:")
    for item in MENU_DATA:
        print(f"  {item[0]}: {item[1]} — £{item[4]}")


if __name__ == "__main__":
    seed()
