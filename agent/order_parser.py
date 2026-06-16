from __future__ import annotations

from typing import Any

from agent.llm_client import DeepSeekClient
from agent.prompts import SYSTEM_PROMPT_TEMPLATE
from sheets.client import SheetsClient


def process_customer_message(message: str) -> dict[str, Any]:
    sheets = SheetsClient()
    menu_json = sheets.get_menu_json()
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(menu_json=menu_json)
    client = DeepSeekClient()
    result = client.chat(system_prompt, message)

    if not isinstance(result, dict):
        return {
            "intent": "unknown",
            "reply": "Sorry, I couldn't understand that. Could you rephrase?",
            "data": {},
        }

    if "intent" not in result:
        result["intent"] = "unknown"

    result.setdefault("reply", "How can I help you?")
    result.setdefault("data", {})

    return result
