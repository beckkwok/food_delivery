from __future__ import annotations

import json

import pytest

from agent.llm_client import DeepSeekClient
from agent.order_parser import process_customer_message
from agent.prompts import SYSTEM_PROMPT_TEMPLATE, FEEDBACK_PROMPT
from sheets.client import SheetsClient


class TestPrompts:
    def test_system_prompt_formatting(self, sample_menu_json: str) -> None:
        prompt = SYSTEM_PROMPT_TEMPLATE.format(menu_json=sample_menu_json)
        assert sample_menu_json in prompt
        assert "Teriyaki Chicken Rice Bowl" in prompt
        assert "照燒雞扒丼" in prompt

    def test_feedback_prompt_formatting(self) -> None:
        prompt = FEEDBACK_PROMPT.format(
            order_id="ORD-123", items="Teriyaki Chicken x2"
        )
        assert "ORD-123" in prompt
        assert "Teriyaki Chicken x2" in prompt

    def test_system_prompt_mentions_output_format(self) -> None:
        assert "intent" in SYSTEM_PROMPT_TEMPLATE
        assert "reply" in SYSTEM_PROMPT_TEMPLATE
        assert "json" in SYSTEM_PROMPT_TEMPLATE.lower()


class TestDeepSeekClient:
    def test_chat_returns_parsed_json(self, mock_deepseek) -> None:
        client = DeepSeekClient()
        result = client.chat("system prompt", "user message")
        assert isinstance(result, dict)
        assert result["intent"] == "order"

    def test_chat_raises_on_http_error(self, mocker) -> None:
        mock_response = mocker.MagicMock()
        mock_response.raise_for_status.side_effect = Exception("API error")
        mock_client = mocker.patch("httpx.Client")
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response

        client = DeepSeekClient()
        with pytest.raises(Exception, match="API error"):
            client.chat("sys", "msg")

    def test_simple_chat_returns_string(self, mock_deepseek) -> None:
        mock_deepseek.return_value.__enter__.return_value.post.return_value.json.return_value = {
            "choices": [{"message": {"content": "hello"}}]
        }
        client = DeepSeekClient()
        result = client.simple_chat("sys", "msg")
        assert result == "hello"


@pytest.mark.usefixtures("mock_gspread")
class TestOrderParser:
    def test_process_customer_message_returns_dict(self, sample_menu_json: str, mocker) -> None:
        mocker.patch.object(SheetsClient, "get_menu_json", return_value=sample_menu_json)

        mock_response = mocker.MagicMock()
        mock_response.raise_for_status = mocker.MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": json.dumps({
                "intent": "order",
                "reply": "Sure!",
                "data": {
                    "items": [{"item_id": "S1", "name": "Teriyaki Chicken", "quantity": 1, "unit_price": 9.00}],
                    "total": 9.00,
                },
            })}}]
        }
        httpx_mock = mocker.patch("agent.llm_client.httpx.Client")
        httpx_mock.return_value.__enter__.return_value.post.return_value = mock_response

        result = process_customer_message("1 teriyaki chicken")
        assert isinstance(result, dict)
        assert result["intent"] == "order"

    def test_non_dict_result_fallback(self, mocker) -> None:
        mocker.patch.object(SheetsClient, "get_menu_json", return_value="[]")
        mock_response = mocker.MagicMock()
        mock_response.raise_for_status = mocker.MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "not json"}}]
        }
        httpx_mock = mocker.patch("agent.llm_client.httpx.Client")
        httpx_mock.return_value.__enter__.return_value.post.return_value = mock_response

        result = process_customer_message("hello")
        assert result["intent"] == "unknown"
