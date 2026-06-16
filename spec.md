# Food Delivery Bot — Specification

## 1. Overview

LLM-powered food ordering assistant for a Japanese takeaway SME. Customers place orders via Telegram using natural language (Cantonese, English, or mixed). DeepSeek parses free-form messages into structured orders. Orders are stored in Google Sheets. The owner receives real-time notifications, a daily summary at 10:30 AM, and feedback requests are sent to customers at 8 PM.

## 2. System Architecture

```
┌─────────────┐     ┌──────────────┐     ┌───────────┐     ┌───────────────┐
│  Customer    │────▶│  Telegram    │────▶│  DeepSeek │────▶│  Google       │
│  (Telegram)  │◀────│  Bot (PTB)   │◀────│  LLM      │◀────│  Sheets       │
└─────────────┘     └──────┬───────┘     └───────────┘     └───────────────┘
                           │
                    ┌──────▼───────┐
                    │  APScheduler │
                    │  (10:30/20:00)│
                    └──────────────┘
```

### 2.1 Components

| Component | Technology | Responsibility |
|---|---|---|
| Telegram Bot | python-telegram-bot v20+ | Message routing, conversation states, notifications |
| LLM Agent | DeepSeek API (httpx) | NL → structured order parsing, multi-language support |
| Data Layer | gspread (Google Sheets) | Menu, Orders, Customers, Feedback storage |
| Scheduler | APScheduler (asyncio) | Daily 10:30 summary, 20:00 feedback requests |
| Reporting | pandas + openpyxl | Monthly P&L and customer feedback aggregation |

## 3. Google Sheets Schema

A single workbook with 4 worksheets:

### 3.1 Orders Sheet

| Column | Type | Description |
|---|---|---|
| OrderID | TEXT | Auto-generated (ORD-yymmdd-XXXXXX) |
| TelegramID | TEXT | Customer's Telegram chat ID |
| CustomerName | TEXT | Customer's display name |
| Items | JSON | Array of {item_id, name, quantity, unit_price} |
| Total | FLOAT | Calculated order total (GBP) |
| Allergies | TEXT | Customer-reported allergies or restrictions |
| SpecialInstructions | TEXT | Any special requests |
| DeliveryAddress | TEXT | Delivery location |
| DeliveryTime | TEXT | Requested delivery time |
| Status | TEXT | New → Confirmed → Delivered → Cancelled |
| Language | TEXT | Language tag (zh/en) |
| CreatedAt | DATETIME | ISO 8601 timestamp |
| UpdatedAt | DATETIME | ISO 8601 timestamp |

### 3.2 Menu Sheet

| Column | Type | Description |
|---|---|---|
| ItemID | TEXT | e.g. S1, S2, R1, R2, R3 |
| Name_EN | TEXT | English item name |
| Name_ZH | TEXT | Chinese (Cantonese) item name |
| Name_JP | TEXT | Japanese item name |
| Category | TEXT | Set, Rice, Sides, Drinks |
| Price | FLOAT | Price in GBP |
| Allergens | TEXT | Emoji-based allergen indicators (🐔🐮🥚) |
| Available | BOOLEAN | Whether item is currently available |

### 3.3 Customers Sheet

| Column | Type | Description |
|---|---|---|
| CustomerID | TEXT | Auto-generated (CUST-{TelegramID}) |
| TelegramID | TEXT | Chat ID for messaging |
| FirstName | TEXT | From Telegram profile |
| LastName | TEXT | From Telegram profile |
| Phone | TEXT | Optional customer-provided phone |
| Address | TEXT | Default delivery address |
| TotalOrders | INTEGER | Lifetime order count |
| LastOrderDate | TEXT | Date of most recent order |
| FirstSeen | DATETIME | First interaction timestamp |

### 3.4 Feedback Sheet

| Column | Type | Description |
|---|---|---|
| FeedbackID | TEXT | Auto-generated (FB-{OrderID}) |
| OrderID | TEXT | Related order |
| TelegramID | TEXT | Customer identifier |
| CustomerName | TEXT | Customer display name |
| Rating | INTEGER | 1-5 scale |
| Comment | TEXT | Free-text comment |
| Date | DATETIME | Submission timestamp |

## 4. Conversation Flow

### 4.1 Order Flow

```
Customer                    Bot                         DeepSeek              Sheets
   │                         │                            │                     │
   ├─ "2個 teriyaki chicken──┤                            │                     │
   │   同 1個 beef bowl"     │                            │                     │
   │                         ├── process_customer_message─┤                     │
   │                         │    (system prompt + menu)  │                     │
   │                         │◀──── JSON response ───────┤                     │
   │                         │    {intent: "order",       │                     │
   │                         │     items: [...],          │                     │
   │                         │     total: 27.50}          │                     │
   │                         │                            │                     │
   │◀─── Order Summary ──────┤                            │                     │
   │    2x Teriyaki Chicken  │                            │                     │
   │    1x Beef Bowl         │                            │                     │
   │    Total: £27.50        │                            │                     │
   │    "Reply Confirm"      │                            │                     │
   │                         │                            │                     │
   ├─ "Confirm" ─────────────┤                            │                     │
   │                         ├── SheetsClient.create_order─────────────────────▶
   │                         │◀─────────────────────────── OrderID: ORD-240215─┤
   │◀─── Order Confirmed ────┤                            │                     │
   │    Order ID: ORD-...    │                            │                     │
   │                         ├── notify_owner()           │                     │
   │                         │    (Telegram msg to owner) │                     │
```

### 4.2 State Machine

```
                        ┌──────────┐
                        │   IDLE   │◀────────────────────────────┐
                        └────┬─────┘                             │
                             │ User sends message                 │
                             ▼                                    │
                     ┌───────────────┐                            │
                     │  LLM Parsing  │                            │
                     └───────┬───────┘                            │
                             │                                    │
              ┌──────────────┼──────────────┐                     │
              ▼              ▼              ▼                     │
        ┌──────────┐  ┌────────────┐  ┌──────────┐               │
        │  Order   │  │ Query/Menu │  │ Unknown  │               │
        └────┬─────┘  └──────┬─────┘  └────┬─────┘               │
             │               │             │                      │
             ▼               ▼             ▼                      │
      ┌─────────────┐  Reply info    Ask clarifying              │
      │  Summary +  │  & return      & return to IDLE            │
      │  Ask Confirm│  to IDLE                                   │
      └──────┬──────┘                                            │
             │                                                    │
             ▼                                                    │
      ┌─────────────┐                                            │
      │ AWAITING_   │                                            │
      │ CONFIRMATION│                                            │
      └──────┬──────┘                                            │
             │                                                    │
       ┌─────┴─────┐                                             │
       ▼           ▼                                              │
   ┌──────┐   ┌────────┐                                         │
   │Confirm│   │ Cancel │                                         │
   └──┬───┘   └───┬────┘                                         │
      │           │                                               │
      ▼           └─────────────── to IDLE ──────────────────────┘
  Write to
  Sheets +
  Notify
  Owner
      │
      ▼
   to IDLE
```

### 4.3 Feedback Flow

```
  8 PM trigger → Bot fetches today's delivered orders
               → For each customer, sends feedback request
               → Adds chat_id to pending_feedback set
               → Customer replies "5 Great food!"
               → Bot detects rating pattern
               → Writes to Feedback sheet
               → Removes from pending_feedback
```

## 5. LLM Agent Design

### 5.1 System Prompt Structure

```
- Role: Japanese takeaway assistant
- Language: Accepts Cantonese, English, Japanese, mixed input
- Menu: Injected dynamically from Google Sheets at each request
- Capabilities: order, modify, cancel, query menu, general Q&A
- Output: JSON with intent + reply + structured data
```

### 5.2 Output JSON Schema

```json
{
  "intent": "order | modify | cancel | query | general | greeting | unknown",
  "reply": "Natural language response to customer (max 3-4 sentences)",
  "data": {
    "items": [
      {
        "item_id": "S1",
        "name": "照燒雞扒丼",
        "quantity": 2,
        "unit_price": 9.00
      }
    ],
    "total": 18.00,
    "delivery_address": "Flat 3, 10 London Road",
    "delivery_time": "12:30",
    "allergies": "shellfish",
    "special_instructions": "extra miso soup",
    "customer_name": "John"
  }
}
```

### 5.3 Matching Rules

| Customer says | Matches ItemID | Match method |
|---|---|---|
| "teriyaki chicken" | S1 | English name substring |
| "照燒雞扒丼" | S1 | Chinese exact match |
| "チキン丼" | S1 | Japanese substring |
| "S1" | S1 | Item ID exact match |
| "chicken rice bowl" | S1, R2, R3 | Ambiguous → ask clarifying |
| "beef bowl" / "牛丼" | R1 | Name alias |

## 6. Scheduler Jobs

| Job | Time | Trigger | Action |
|---|---|---|---|
| Daily Summary | 10:30 daily | `cron hour=10 minute=30` | Fetch today's orders, group by status, send to owner via Telegram |
| Feedback Request | 20:00 daily | `cron hour=20 minute=0` | Fetch delivered orders, send feedback prompt to each customer |

## 7. Owner Notifications

### 7.1 New Order Alert

Sent immediately when a customer confirms an order.

```
🆕 New Order!
Order ID: ORD-240215-A1B2C3
Items:
  Teriyaki Chicken Rice Bowl x2
  Beef Rice Bowl x1
Total: £27.50
Allergies: shellfish
```

### 7.2 Daily Summary

Sent at 10:30 AM with all orders for the current day.

```
📋 Daily Summary — 2026-06-16

🆕 New (2):
  ORD-240616-XXX — [{"name":...}] — £18.00
  ORD-240616-YYY — [{"name":...}] — £9.50

✅ Confirmed (1):
  ORD-240616-ZZZ — [{"name":...}] — £12.50

💰 Total revenue today: £40.00
```

## 8. Configuration

### 8.1 Environment Variables (.env)

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Yes | Bot token from BotFather |
| `DEEPSEEK_API_KEY` | Yes | API key from DeepSeek platform |
| `DEEPSEEK_API_URL` | No | Default: https://api.deepseek.com/v1/chat/completions |
| `GOOGLE_SHEETS_CREDENTIALS_PATH` | Yes | Path to service account JSON |
| `GOOGLE_SHEET_ID` | Yes | ID from Google Sheets URL |
| `OWNER_TELEGRAM_ID` | Yes | Owner's Telegram user ID for notifications |

## 9. Error Handling

| Scenario | Behavior |
|---|---|
| DeepSeek API timeout | Retry once, then respond with "Service busy, please try again" |
| Google Sheets write failure | Log error, inform owner via Telegram |
| Invalid LLM JSON response | Catch JSON decode error, return "I didn't understand, please rephrase" |
| Telegram API failure | Log and continue (non-blocking) |
| Missing env vars | Log error and exit at startup |
| Unknown intent from LLM | Fall back to "How can I help you?" generic reply |

## 10. Security

- API keys stored in `.env` (not committed)
- Google service account JSON in `credentials/` (gitignored)
- No payment handling — all payments are cash/card on delivery
- No persistent database beyond Google Sheets (no passwords or PII stored)
- Telegram chat IDs used as customer identifiers (no phone numbers required)

## 11. Menu (Demo Data)

| ID | English | Chinese | Japanese | Category | Price | Allergens |
|---|---|---|---|---|---|---|
| S1 | Teriyaki Chicken Rice Bowl w/ Miso Soup | 照燒雞扒丼 | 照り焼きチキン丼 | Set | £9.00 | 🐔 |
| S2 | Okonomiyaki | 大阪焼 | お好み焼き | Set | £12.50 | — |
| R1 | Beef Rice Bowl w/ Miso Soup | 牛肉飯（牛丼） | 牛丼 | Rice | £9.50 | 🐮 |
| R2 | Karaage Fried Chicken Rice Bowl w/ Miso Soup | 唐揚炸雞丼 | 鶏の唐揚げ丼 | Rice | £9.00 | — |
| R3 | Chicken & Egg Rice Bowl w/ Miso Soup | 親子丼 | 鶏の親子丼 | Rice | £8.00 | 🐔🥚 |

## 12. Future Considerations

- **Payment integration** — Stripe or PayPal for pre-payment
- **WhatsApp channel** — Replace Telegram with WhatsApp Business API for production
- **Order history per customer** — Full customer portal view
- **Inventory tracking** — Link orders to ingredient stock
- **Delivery partner integration** — Uber Direct / Deliveroo logistics
- **SMS fallback** — For customers without Telegram
- **Multi-outlet** — Support multiple kitchen locations
