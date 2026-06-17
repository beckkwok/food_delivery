from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import Update
from telegram.ext import ConversationHandler

from bot.handlers import (
    AWAITING_CONFIRMATION,
    cancel,
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


@pytest.mark.usefixtures("mock_gspread")
class TestStart:
    async def test_reply_contains_menu(self) -> None:
        update = _make_update("/start")
        context = MagicMock()
        await start(update, context)
        reply = update.message.reply_text
        reply.assert_awaited_once()
        text = reply.call_args[0][0]
        assert "S1" in text
        assert "Teriyaki" in text
        assert "£9.00" in text
        assert "照燒雞扒丼" in text


@pytest.mark.usefixtures("mock_gspread")
class TestHandleMessage:
    async def test_feedback_rating(self, mocker) -> None:
        mocker.patch.object(SheetsClient, "write_feedback")
        chat_id = 123
        mark_feedback_pending(chat_id)
        update = _make_update("5 Great food!", chat_id=chat_id)
        context = MagicMock()
        result = await handle_message(update, context)
        assert result == ConversationHandler.END
        update.message.reply_text.assert_awaited_with(
            "Thanks for your feedback! 🙏 Hope to serve you again soon."
        )
        assert chat_id not in pending_feedback

    async def test_feedback_invalid_rating(self) -> None:
        chat_id = 123
        mark_feedback_pending(chat_id)
        update = _make_update("just a comment", chat_id=chat_id)
        context = MagicMock()
        result = await handle_message(update, context)
        assert result == ConversationHandler.END
        update.message.reply_text.assert_awaited_with(
            "Please reply with a rating 1-5 and optional comment (e.g. **5 Great food!**)"
        )

    async def test_greeting_intent(self, mocker) -> None:
        mocker.patch(
            "bot.handlers.process_customer_message",
            return_value={"intent": "greeting", "reply": "Hello!", "data": {}},
        )
        update = _make_update("hi")
        context = MagicMock()
        result = await handle_message(update, context)
        assert result == ConversationHandler.END
        update.message.reply_text.assert_awaited_with("Hello!")

    async def test_order_intent_enters_confirmation(self, mocker) -> None:
        mocker.patch(
            "bot.handlers.process_customer_message",
            return_value={
                "intent": "order",
                "reply": "Got it!",
                "data": {
                    "items": [{"item_id": "S1", "name": "Teriyaki Chicken", "quantity": 2, "unit_price": 9.00}],
                    "total": 18.00,
                },
            },
        )
        update = _make_update("2 teriyaki chicken")
        context = MagicMock()
        result = await handle_message(update, context)
        assert result == AWAITING_CONFIRMATION
        reply_text = update.message.reply_text.call_args[0][0]
        assert "Order Summary" in reply_text
        assert "£18.00" in reply_text
        assert 123 in user_conversations

    async def test_unknown_intent(self, mocker) -> None:
        mocker.patch(
            "bot.handlers.process_customer_message",
            return_value={"intent": "unknown", "reply": "Sorry?", "data": {}},
        )
        update = _make_update("xyz")
        context = MagicMock()
        result = await handle_message(update, context)
        assert result == ConversationHandler.END
        update.message.reply_text.assert_awaited_with("Sorry?")


@pytest.mark.usefixtures("mock_gspread")
class TestConfirmOrder:
    async def test_confirm_creates_order(self, mocker) -> None:
        mocker.patch.object(SheetsClient, "create_order", return_value="ORD-TEST")
        mocker.patch.object(SheetsClient, "write_feedback")
        chat_id = 123
        user_conversations[chat_id] = {
            "pending_order": {"customer_name": "Tester"},
            "items": [{"item_id": "S1", "name": "Chicken Bowl", "quantity": 1, "unit_price": 9.00}],
            "total": 9.00,
        }
        update = _make_update("confirm", chat_id=chat_id)
        context = MagicMock()
        result = await confirm_order(update, context)
        assert result == ConversationHandler.END
        update.message.reply_text.assert_awaited()
        text = update.message.reply_text.call_args[0][0]
        assert "confirmed" in text.lower()
        assert chat_id not in user_conversations

    async def test_cancel(self) -> None:
        chat_id = 123
        user_conversations[chat_id] = {"items": []}
        update = _make_update("cancel", chat_id=chat_id)
        context = MagicMock()
        result = await confirm_order(update, context)
        assert result == ConversationHandler.END
        update.message.reply_text.assert_awaited_with(
            "Order cancelled. Send your order again anytime!"
        )
        assert chat_id not in user_conversations

    async def test_no_pending_order(self) -> None:
        update = _make_update("confirm", chat_id=999)
        context = MagicMock()
        result = await confirm_order(update, context)
        assert result == ConversationHandler.END
        update.message.reply_text.assert_awaited_with(
            "No pending order found. Send your order again."
        )


class TestCancel:
    async def test_cancels_and_clears_state(self) -> None:
        chat_id = 123
        user_conversations[chat_id] = {"items": []}
        update = _make_update("/cancel", chat_id=chat_id)
        context = MagicMock()
        result = await cancel(update, context)
        assert result == ConversationHandler.END
        assert chat_id not in user_conversations


class TestMarkFeedbackPending:
    def test_adds_chat_id(self) -> None:
        pending_feedback.clear()
        mark_feedback_pending(42)
        assert 42 in pending_feedback

    def test_idempotent(self) -> None:
        pending_feedback.clear()
        mark_feedback_pending(42)
        mark_feedback_pending(42)
        assert len(pending_feedback) == 1
