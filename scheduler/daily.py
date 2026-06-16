from __future__ import annotations

from datetime import datetime, date

from telegram.ext import Application

from config.settings import OWNER_TELEGRAM_ID
from sheets.client import SheetsClient
from bot.handlers import mark_feedback_pending


async def send_daily_summary(app: Application) -> None:
    if not OWNER_TELEGRAM_ID:
        return

    sheets = SheetsClient()
    today = date.today().isoformat()
    orders = sheets.get_orders_by_date(today)

    new_orders = [o for o in orders if o.get("Status") == "New"]
    confirmed = [o for o in orders if o.get("Status") == "Confirmed"]

    if not orders:
        msg = f"📋 **Daily Summary — {today}**\n\nNo orders today. Enjoy the quiet day!"
    else:
        lines = [f"📋 **Daily Summary — {today}**"]
        lines.append(f"\n🆕 **New ({len(new_orders)}):**")
        for o in new_orders:
            items = o.get("Items", "?")
            lines.append(f"  {o['OrderID']} — {items} — £{o.get('Total', 0)}")
        lines.append(f"\n✅ **Confirmed ({len(confirmed)}):**")
        for o in confirmed:
            items = o.get("Items", "?")
            lines.append(f"  {o['OrderID']} — {items} — £{o.get('Total', 0)}")
        lines.append(f"\n💰 **Total revenue today: £{sum(float(o.get('Total', 0)) for o in orders):.2f}**")
        msg = "\n".join(lines)

    try:
        await app.bot.send_message(chat_id=OWNER_TELEGRAM_ID, text=msg)
    except Exception:
        pass


async def ask_feedback_for_yesterday(app: Application) -> None:
    if not OWNER_TELEGRAM_ID:
        return

    sheets = SheetsClient()
    yesterday = date.today().isoformat()
    delivered = sheets.get_orders_by_date(yesterday)
    delivered = [o for o in delivered if o.get("Status") in ("Confirmed", "Delivered")]

    for order in delivered:
        chat_id = int(order.get("TelegramID", 0))
        if not chat_id:
            continue
        try:
            msg = (
                f"Hi {order.get('CustomerName', 'there')}! 👋\n"
                f"Hope you enjoyed your recent order ({order['OrderID']}).\n"
                f"Could you rate us 1-5 and leave a quick comment?\n"
                f"(Reply like: **5 Great food!**)"
            )
            await app.bot.send_message(chat_id=chat_id, text=msg)
            mark_feedback_pending(chat_id)
        except Exception:
            pass
