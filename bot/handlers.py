from __future__ import annotations

import re

from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler

from agent.order_parser import process_customer_message
from config.settings import OWNER_TELEGRAM_ID
from sheets.client import SheetsClient

AWAITING_CONFIRMATION = 1

user_conversations: dict[int, dict] = {}
pending_feedback: set[int] = set()


def mark_feedback_pending(chat_id: int) -> None:
    pending_feedback.add(chat_id)


async def start(update: Update, context: CallbackContext) -> int | None:
    user = update.effective_user
    reply = (
        f"Hello {user.first_name if user else 'there'}! Welcome to our Japanese takeaway. 🍱\n\n"
        f"Menu:\n"
        f"S1. Teriyaki Chicken Rice Bowl w/ Miso Soup — \u00a39.00\n"
        f"S2. Okonomiyaki — \u00a312.50\n"
        f"R1. Beef Rice Bowl w/ Miso Soup — \u00a39.50\n"
        f"R2. Karaage Fried Chicken Rice Bowl w/ Miso Soup — \u00a39.00\n"
        f"R3. Chicken & Egg Rice Bowl w/ Miso Soup — \u00a38.00\n\n"
        f"Order by saying e.g. \"2 teriyaki chicken and 1 beef bowl\" or \"兩份照燒雞扒丼\"."
    )
    await update.message.reply_text(reply)


async def handle_message(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    chat_id = update.effective_chat.id if update.effective_chat else 0
    text = update.message.text.strip() if update.message else ""

    sheets = SheetsClient()
    sheets.upsert_customer(
        telegram_id=chat_id,
        first_name=user.first_name if user else "Guest",
        last_name=user.last_name or "",
    )

    if chat_id in pending_feedback:
        match = re.match(r"^(\d)\s*(.*)", text)
        if match:
            rating = int(match.group(1))
            if 1 <= rating <= 5:
                pending_feedback.discard(chat_id)
                sheets.write_feedback(
                    order_id="",
                    telegram_id=chat_id,
                    customer_name=user.first_name if user else "Guest",
                    rating=rating,
                    comment=match.group(2).strip(),
                )
                await update.message.reply_text(
                    "Thanks for your feedback! 🙏 Hope to serve you again soon."
                )
                return ConversationHandler.END
        await update.message.reply_text(
            "Please reply with a rating 1-5 and optional comment (e.g. **5 Great food!**)"
        )
        return ConversationHandler.END

    result = process_customer_message(text)
    intent = result.get("intent", "unknown")
    reply = result.get("reply", "How can I help you?")
    data = result.get("data", {})

    if intent == "order":
        items = data.get("items", [])
        total = data.get("total", 0)
        if items and total > 0:
            summary_lines = ["**Order Summary:**"]
            for item in items:
                summary_lines.append(
                    f"  - {item.get('name', '?')} x{item.get('quantity', 1)} "
                    f"@ \u00a3{item.get('unit_price', 0):.2f}"
                )
            summary_lines.append(f"\n**Total: \u00a3{total:.2f}**")
            if data.get("allergies"):
                summary_lines.append(f"Allergies: {data['allergies']}")
            if data.get("delivery_address"):
                summary_lines.append(f"Deliver to: {data['delivery_address']}")
            if data.get("delivery_time"):
                summary_lines.append(f"Delivery time: {data['delivery_time']}")
            summary_lines.append(
                "\nReply **Confirm** to place this order, or tell me what to change."
            )

            user_conversations[chat_id] = {
                "pending_order": data,
                "items": items,
                "total": total,
            }
            await update.message.reply_text("\n".join(summary_lines))
            return AWAITING_CONFIRMATION

    await update.message.reply_text(reply)
    return ConversationHandler.END


async def confirm_order(update: Update, context: CallbackContext) -> int:
    chat_id = update.effective_chat.id if update.effective_chat else 0
    text = update.message.text.strip().lower() if update.message else ""

    if text in ("confirm", "confirm order", "yes", "y", "確認", "係"):
        conv = user_conversations.get(chat_id)
        if not conv:
            await update.message.reply_text("No pending order found. Send your order again.")
            return ConversationHandler.END

        data = conv["pending_order"]
        sheets = SheetsClient()
        order_id = sheets.create_order(
            customer_name=data.get("customer_name", "Guest"),
            telegram_id=chat_id,
            items=conv["items"],
            total=conv["total"],
            allergies=data.get("allergies", ""),
            instructions=data.get("special_instructions", ""),
            delivery_address=data.get("delivery_address", ""),
            delivery_time=data.get("delivery_time", ""),
            language="zh/en",
        )

        user_conversations.pop(chat_id, None)

        msg = (
            f"Order confirmed! ✅\n"
            f"Order ID: {order_id}\n"
            f"Total: \u00a3{conv['total']:.2f}\n\n"
            f"Your food will be prepared and delivered. Thank you! 🍱"
        )
        await update.message.reply_text(msg)

        await _notify_owner(context, order_id, conv)
    else:
        user_conversations.pop(chat_id, None)
        await update.message.reply_text(
            "Order cancelled. Send your order again anytime!"
        )

    return ConversationHandler.END


async def _notify_owner(context: CallbackContext, order_id: str, conv: dict) -> None:
    if not OWNER_TELEGRAM_ID:
        return
    items_str = "\n".join(
        f"  {it.get('name', '?')} x{it.get('quantity', 1)}"
        for it in conv.get("items", [])
    )
    msg = (
        f"\U0001f195 **New Order!**\n"
        f"Order ID: {order_id}\n"
        f"Items:\n{items_str}\n"
        f"Total: \u00a3{conv['total']:.2f}\n"
        f"Allergies: {conv['pending_order'].get('allergies', 'None')}"
    )
    try:
        await context.bot.send_message(chat_id=OWNER_TELEGRAM_ID, text=msg)
    except Exception:
        pass


async def cancel(update: Update, context: CallbackContext) -> int:
    chat_id = update.effective_chat.id if update.effective_chat else 0
    user_conversations.pop(chat_id, None)
    await update.message.reply_text("Action cancelled. Message me anytime to order!")
    return ConversationHandler.END
