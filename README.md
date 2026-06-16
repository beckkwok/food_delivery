# SME Food Delivery Bot

LLM-powered food ordering assistant. Customers order via Telegram (WhatsApp in production). DeepSeek handles natural language parsing (Cantonese/English/Japanese mixed). Orders recorded in Google Sheets. Owner gets daily summary at 10:30.

## Architecture

```
Customer (Telegram) → Telegram Bot → DeepSeek LLM → Google Sheets → Owner
                         ↕
              Conversation State (2-step confirm)
```

## Setup

### 1. Prerequisites

- Python 3.11+
- A Telegram account
- A Google account (for Sheets)
- A DeepSeek API key

### 2. Create a Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow prompts
3. Save the bot token (looks like `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)
4. Get your own Telegram user ID by messaging **@userinfobot**
5. Save both for `.env`

### 3. Set up Google Sheets

1. Go to https://console.cloud.google.com/
2. Create a new project (or select existing)
3. Enable **Google Sheets API** and **Google Drive API**
4. Go to **Credentials** → **Create Credentials** → **Service Account**
5. Download the JSON key file → save as `credentials/google-service-account.json`
6. Create a new Google Sheet and note its **Sheet ID** (from the URL: `https://docs.google.com/spreadsheets/d/THIS_IS_THE_ID/edit`)
7. Share the sheet with the service account email (found in the JSON file) as **Editor**

### 4. Get a DeepSeek API Key

1. Go to https://platform.deepseek.com/
2. Sign up and create an API key
3. Copy the key

### 5. Configure Environment

```bash
cp .env.example .env
```

Edit `.env`:

```ini
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
DEEPSEEK_API_KEY=sk-your-deepseek-api-key
GOOGLE_SHEETS_CREDENTIALS_PATH=./credentials/google-service-account.json
GOOGLE_SHEET_ID=your_google_sheet_id_here
OWNER_TELEGRAM_ID=your_telegram_user_id
```

### 6. Install Dependencies

```bash
pip install -r requirements.txt
```

### 7. Seed the Menu

```bash
python seed_menu.py
```

This creates the 4 sheets (Menu, Orders, Customers, Feedback) and populates the menu.

### 8. Run

```bash
python main.py
```

## Usage

### Customers

Customers message the Telegram bot with orders like:

- "2 teriyaki chicken and 1 okonomiyaki please"
- "我想 order 兩個照燒雞扒丼，送去 Flat 3, 10 London Road"
- "S1 x2, R1 x1 — deliver at 12:30, no allergies"

The bot will:
1. Parse items and calculate total
2. Ask for missing details (address, time, allergies)
3. Show order summary → customer confirms
4. Write order to Google Sheets
5. Notify the owner

### Owner

- **Real-time notifications** when new orders come in
- **Daily summary** at 10:30 AM — all orders for today, grouped by status
- **Google Sheets** is the source of truth — open it anytime to view orders

### Post-Delivery

At 8 PM, the bot sends feedback requests to customers who received orders that day.

## Monthly Reports

```bash
python -m reports.monthly
```

Generates a summary of orders and customer feedback for the current month.

## Project Structure

```
food_delivery/
├── bot/            # Telegram bot logic
│   ├── bot.py      # Application builder
│   └── handlers.py # Message handlers + conversation states
├── agent/          # DeepSeek LLM integration
│   ├── llm_client.py
│   ├── order_parser.py
│   └── prompts.py
├── sheets/         # Google Sheets integration
│   ├── client.py   # CRUD operations
│   └── schema.py   # Sheet structure definitions
├── scheduler/      # APScheduler jobs
│   └── daily.py    # 10:30 summary + feedback requests
├── reports/        # Monthly aggregation
│   └── monthly.py
├── config/
│   └── settings.py
├── utils/
│   └── helpers.py
├── main.py         # Entry point
├── seed_menu.py    # One-time setup script
├── .env.example
└── requirements.txt
```

## Customization

### Adding New Menu Items

Edit the Menu sheet directly in Google Sheets — the bot reads it live at order time.

### Changing Language Support

Edit `agent/prompts.py` — the system prompt controls language handling.

### Modifying Schedules

Edit `main.py` — APScheduler cron triggers for daily summary and feedback requests.
