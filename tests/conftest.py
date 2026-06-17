from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from sheets.client import SheetsClient


@pytest.fixture(autouse=True)
def reset_sheets_singleton() -> Generator[None, None, None]:
    SheetsClient._instance = None
    SheetsClient._initialized = False  # type: ignore[attr-defined]
    yield


@pytest.fixture
def mock_gspread(mocker) -> Generator[dict[str, Any], None, None]:
    mock_ws = MagicMock()
    mock_ws.row_values.return_value = [
        "CustomerID", "TelegramID", "FirstName", "LastName",
        "Phone", "Address", "TotalOrders", "LastOrderDate", "FirstSeen",
    ]
    mock_ws.get_all_records.return_value = []
    mock_ws.append_row = MagicMock()

    mock_sh = MagicMock()
    mock_sh.worksheet.return_value = mock_ws

    mock_gc = MagicMock()
    mock_gc.open_by_key.return_value = mock_sh

    mocker.patch("google.oauth2.service_account.Credentials.from_service_account_file")
    mocker.patch("gspread.authorize", return_value=mock_gc)

    return {
        "gc": mock_gc,
        "sh": mock_sh,
        "ws": mock_ws,
    }


@pytest.fixture
def mock_deepseek(mocker) -> Generator[MagicMock, None, None]:
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"intent": "order", "reply": "Sure!", "data": {"items": [], "total": 0}}'
                }
            }
        ]
    }
    mock_client = mocker.patch("httpx.Client")
    mock_client.return_value.__enter__.return_value.post.return_value = mock_response
    return mock_client


@pytest.fixture
def sample_menu_json() -> str:
    return (
        '[{"ItemID":"S1","Name_EN":"Teriyaki Chicken Rice Bowl w/ Miso Soup",'
        '"Name_ZH":"照燒雞扒丼","Price":9.00,"Available":true},'
        '{"ItemID":"R1","Name_EN":"Beef Rice Bowl w/ Miso Soup",'
        '"Name_ZH":"牛肉飯（牛丼）","Price":9.50,"Available":true}]'
    )
