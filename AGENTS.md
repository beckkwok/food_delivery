# AGENTS.md — Food Delivery Bot

## Project Overview
LLM-powered food ordering assistant for a Japanese takeaway SME. Customers order via Telegram; DeepSeek parses Cantonese/English/Japanese mixed messages; orders stored in Google Sheets; owner gets notifications + daily summary.

## Commands

### Run the bot
```bash
python main.py
```

### Seed/refresh Google Sheets menu
```bash
python seed_menu.py
```

### Generate monthly report
```bash
python -m reports.monthly
```

### Install dependencies
```bash
pip install -r requirements.txt
```

## Project Structure
```
main.py              # Entry point — bot + APScheduler
seed_menu.py         # One-time Google Sheets setup + menu seed
bot/                 # Telegram bot logic (PTB v20+)
agent/               # DeepSeek LLM integration
sheets/              # Google Sheets CRUD (gspread)
scheduler/           # APScheduler jobs (10:30 summary, 20:00 feedback)
reports/             # Monthly P&L + feedback aggregation
config/settings.py   # Env vars via python-dotenv
utils/helpers.py     # Order ID gen, price format, language detection
```

## Key Architecture Decisions
- **Singleton pattern** for `SheetsClient` — one auth per process
- **ConversationHandler** for 2-step order confirmation (entry -> AWAITING_CONFIRMATION -> confirm/cancel)
- **DeepSeek JSON mode** for structured order parsing from free-form text
- **APScheduler** for daily cron jobs (no external dependency)
- **`pending_feedback` set** (in-memory) tracks which customers were asked for feedback

## Setup Checklist
1. Create Telegram bot via BotFather -> get token
2. Enable Google Sheets API -> create service account -> download JSON to `credentials/`
3. Get DeepSeek API key
4. Copy `.env.example` -> `.env` and fill values
5. `pip install -r requirements.txt`
6. `python seed_menu.py`
7. `python main.py`

## Menu Items (seeded)
| ID | EN | ZH | Price |
|---|---|---|---|
| S1 | Teriyaki Chicken Rice Bowl w/ Miso Soup | 照燒雞扒丼 | £9.00 |
| S2 | Okonomiyaki | 大阪焼 | £12.50 |
| R1 | Beef Rice Bowl w/ Miso Soup | 牛肉飯（牛丼） | £9.50 |
| R2 | Karaage Fried Chicken Rice Bowl w/ Miso Soup | 唐揚炸雞丼 | £9.00 |
| R3 | Chicken & Egg Rice Bowl w/ Miso Soup | 親子丼 | £8.00 |
