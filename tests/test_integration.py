from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import Update
from telegram.ext import ConversationHandler

from bot.handlers import (
    AWAITING_CONFIRMATION,
    confirm_order,
    handle_message,
    mark_feedback_pending,
    pending_feedback,
    start,
    user_conversations,
)
from sheets.client import SheetsClient


@pytest.fixture(autouse=True)
def reset_state() -> None:
    user_conversations.clear()
    pending_feedback.clear()


def _make_update(text: str, chat_id: int = 123,
                 first_name: str = "TestUser") -> MagicMock:
    user = MagicMock()
    user.first_name = first_name
    user.last_name = "User"
    message = MagicMock()
    message.text = text
    message.reply_text = AsyncMock()
    chat = MagicMock()
    chat.id = chat_id
    update = MagicMock(spec=Update)
    update.effective_user = user
    update.effective_chat = chat
    update.message = message
    return update


def _stub_deepseek_order(mocker, overrides: dict | None = None) -> None:
    data = {
        "items": [{"item_id": "S1", "name": "Teriyaki Chicken", "quantity": 2, "unit_price": 9.00}],
        "total": 18.00,
        "customer_name": "John Smith",
        "telephone": "07700 900123",
        "delivery_address": "Flat 3, 10 London Road",
        "delivery_time": "12:30",
        "allergies": "None",
        "special_instructions": "",
    }
    if overrides:
        data.update(overrides)
    payload = json.dumps({"intent": "order", "reply": "Got it!", "data": data})
    mock_resp = mocker.MagicMock()
    mock_resp.raise_for_status = mocker.MagicMock()
    mock_resp.json.return_value = {"choices": [{"message": {"content": payload}}]}
    mocker.patch("agent.llm_client.httpx.Client").return_value.__enter__.return_value.post.return_value = mock_resp


# ── Integration: full order flow ──────────────────────────────────────────

@pytest.mark.usefixtures("mock_gspread")
class TestFullOrderFlow:
    async def test_complete_order_from_message_to_sheet(self, mocker) -> None:
        _stub_deepseek_order(mocker)
        sheets = SheetsClient()
        mocker.spy(sheets, "create_order")

        update = _make_update(
            "2 teriyaki chicken, John Smith, 07700 900123, Flat 3, 12:30"
        )
        context = MagicMock()

        result = await handle_message(update, context)
        assert result == AWAITING_CONFIRMATION
        reply = update.message.reply_text.call_args[0][0]
        assert "Order Summary" in reply
        assert "John Smith" in reply
        assert "07700 900123" in reply
        assert "Flat 3" in reply
        assert "£18.00" in reply

        update2 = _make_update("confirm", chat_id=123)
        result2 = await confirm_order(update2, context)
        assert result2 == ConversationHandler.END

        confirm_reply = update2.message.reply_text.call_args[0][0]
        assert "Order confirmed" in confirm_reply
        assert 123 not in user_conversations

    async def test_order_written_to_sheet(self, mocker) -> None:
        _stub_deepseek_order(mocker)
        ws = mocker.patch.object(SheetsClient, "_worksheet")
        ws.return_value = MagicMock()

        update = _make_update(
            "2 teriyaki chicken, John, 07700, Flat 3"
        )
        result = await handle_message(update, MagicMock())
        assert result == AWAITING_CONFIRMATION

        sheets = SheetsClient()
        mocker.patch.object(sheets, "create_order", wraps=sheets.create_order)
        update2 = _make_update("confirm", chat_id=123)
        await confirm_order(update2, MagicMock())

        call = sheets.create_order.mock_calls[0]
        _, kwargs = call[0], call[2]
        assert kwargs.get("customer_name") == "John Smith"
        assert kwargs.get("telephone") == "07700 900123"
        assert kwargs.get("delivery_address") == "Flat 3, 10 London Road"
        assert kwargs.get("total") == 18.00


# ── Integration: multi-step collection ────────────────────────────────────

@pytest.mark.usefixtures("mock_gspread")
class TestMultiStepOrder:
    async def test_collects_missing_fields_over_two_messages(self, mocker) -> None:
        first_payload = json.dumps({
            "intent": "order", "reply": "Need more info",
            "data": {
                "items": [{"item_id": "S1", "name": "Teriyaki Chicken", "quantity": 2, "unit_price": 9.00}],
                "total": 18.00, "customer_name": "", "telephone": "",
                "delivery_address": "", "delivery_time": "", "allergies": "",
                "special_instructions": "",
            },
        })
        second_payload = json.dumps({
            "intent": "order", "reply": "Got it!",
            "data": {
                "items": [{"item_id": "S1", "name": "Teriyaki Chicken", "quantity": 2, "unit_price": 9.00}],
                "total": 18.00, "customer_name": "John Smith",
                "telephone": "07700 900123",
                "delivery_address": "Flat 3, 10 London Road",
                "delivery_time": "", "allergies": "",
                "special_instructions": "",
            },
        })
        mock_resp = mocker.MagicMock()
        mock_resp.raise_for_status = mocker.MagicMock()
        mock_resp.json.side_effect = [
            {"choices": [{"message": {"content": first_payload}}]},
            {"choices": [{"message": {"content": second_payload}}]},
        ]
        mocker.patch("agent.llm_client.httpx.Client").return_value.__enter__.return_value.post.return_value = mock_resp

        update = _make_update("2 teriyaki chicken")
        context = MagicMock()
        result = await handle_message(update, context)
        assert result == ConversationHandler.END
        reply = update.message.reply_text.call_args[0][0]
        assert "your name" in reply.lower()
        assert 123 in user_conversations
        assert user_conversations[123]["stage"] == "collecting_info"

        update2 = _make_update(
            "My name is John Smith, phone 07700 900123, "
            "address Flat 3, 10 London Road",
            chat_id=123,
        )
        result2 = await handle_message(update2, context)
        assert result2 == AWAITING_CONFIRMATION
        reply2 = update2.message.reply_text.call_args[0][0]
        assert "Order Summary" in reply2
        assert "John Smith" in reply2


# ── Integration: feedback flow ────────────────────────────────────────────

@pytest.mark.usefixtures("mock_gspread")
class TestFeedbackFlow:
    async def test_feedback_response_written_to_sheet(self, mocker) -> None:
        sheets = SheetsClient()
        mocker.spy(sheets, "write_feedback")

        mark_feedback_pending(123)
        update = _make_update("5 Great food!", chat_id=123)
        result = await handle_message(update, MagicMock())
        assert result == ConversationHandler.END

        sheets.write_feedback.assert_called_once()
        call = sheets.write_feedback.mock_calls[0]
        _, kwargs = call[0], call[2]
        assert kwargs.get("rating") == 5
        assert "Great food!" in kwargs.get("comment", "")

    async def test_feedback_clears_pending_set(self, mocker) -> None:
        sheets = SheetsClient()
        mocker.spy(sheets, "write_feedback")

        mark_feedback_pending(123)
        assert 123 in pending_feedback
        update = _make_update("3 Okay", chat_id=123)
        await handle_message(update, MagicMock())
        assert 123 not in pending_feedback


# ── Integration: /start command ──────────────────────────────────────────

@pytest.mark.usefixtures("mock_gspread")
class TestStartCommand:
    async def test_start_reply_contains_menu(self) -> None:
        update = _make_update("/start")
        context = MagicMock()
        await start(update, context)
        reply = update.message.reply_text.call_args[0][0]
        assert "S1" in reply
        assert "Teriyaki" in reply
        assert "£9.00" in reply
        assert "phone" in reply.lower()


# ── Integration: error propagation ───────────────────────────────────────

@pytest.mark.usefixtures("mock_gspread")
class TestErrorHandling:
    async def test_deepseek_api_error_returns_fallback(self, mocker) -> None:
        mock_resp = mocker.MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("API timeout")
        mocker.patch("agent.llm_client.httpx.Client").return_value.__enter__.return_value.post.return_value = mock_resp

        update = _make_update("2 teriyaki chicken")
        result = await handle_message(update, MagicMock())
        assert result == ConversationHandler.END
        update.message.reply_text.assert_called_once()

    async def test_sheets_write_error_does_not_crash_bot(self, mocker) -> None:
        _stub_deepseek_order(mocker)
        mocker.patch.object(
            SheetsClient, "create_order",
            side_effect=Exception("Sheets unavailable"),
        )

        chat_id = 123
        user_conversations[chat_id] = {
            "pending_order": {"customer_name": "Tester", "telephone": "07700", "delivery_address": "Flat 3"},
            "items": [{"item_id": "S1", "name": "Chicken", "quantity": 1, "unit_price": 9.00}],
            "total": 9.00,
        }
        update = _make_update("confirm", chat_id=chat_id)
        with pytest.raises(Exception, match="Sheets unavailable"):
            await confirm_order(update, MagicMock())
