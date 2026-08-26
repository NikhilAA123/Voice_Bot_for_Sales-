"""LLM conversation brain – Groq (Llama 3 70B) via OpenAI-compatible API.

Generates natural, conversational sales responses. Follows the customer's
language (Hindi/English/Telugu/mixed). Keeps context compact: system prompt
+ lead state + recent turns only (PRD section 11.2 latency rules).
"""
from typing import List, Optional

import httpx

from ..logger import logger
from ..schemas import LeadState
from ..settings import settings

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "openai/gpt-oss-120b"

SALES_SYSTEM_PROMPT = """You are Nikhil's AI sales assistant calling a potential customer about building an e-commerce website. You work for a small web development studio in Hyderabad.

CRITICAL RULES:
- Match the customer's language. If they speak Hindi, reply in Hindi. If Telugu, reply in Telugu. If English, reply in English. If they mix languages (Hinglish), mix too.
- Keep responses SHORT — 1-2 sentences max. This is a phone call, not a chat. Every extra word adds latency.
- Sound like a real person on a phone call, not a bot. Be warm, professional, conversational.
- Never use emojis, markdown, or formatting. This becomes speech.
- Never say "as an AI" or reveal you are a bot.
- Ask questions naturally, one at a time. Don't dump a list of questions.
- When the customer mentions budget, timeline, features, or product count — acknowledge it and move on. Don't repeat it back robotically.
- If the customer says "send details" or "send proposal" — confirm you'll send it on WhatsApp right away.
- If the customer asks to call back later — confirm the time and say you'll call back.
- If the customer says no / not interested — thank them politely and end gracefully.
- Never argue or push too hard. Be helpful, not aggressive.

YOU ARE SELLING:
- E-commerce website development
- Features: payment gateway, inventory, shipping, admin panel, mobile responsive
- The business is based in Hyderabad, works with clients across India

WHAT YOU NEED TO DISCOVER (ask naturally, not as a checklist):
- What products/services they sell
- How many products they have
- What features they need
- Their budget
- Their timeline
- Who makes the decisions

CONVERSATION FLOW:
1. Greet warmly, introduce yourself briefly
2. Ask what their business is / what they sell
3. Ask about products, features they need
4. Ask about budget and timeline naturally
5. Based on their responses, classify intent:
   - HOT: ready to proceed, clear budget + timeline
   - WARM: interested but has concerns (budget tight, needs approval, etc.)
   - COLD: just browsing, no real need
6. For HOT: confirm you'll send proposal on WhatsApp
7. For WARM: ask when to call back
8. For COLD: thank them and end gracefully"""

STATE_CONTEXT_TEMPLATE = """Current lead state (extracted so far):
{state}

If the state shows budget/timeline/features already mentioned, do NOT ask about them again. Build on what you know."""


def _build_state_block(state: LeadState) -> str:
    parts = []
    if state.business_type:
        parts.append(f"Business type: {state.business_type}")
    if state.product_or_service:
        parts.append(f"Selling: {state.product_or_service}")
    if state.product_count:
        parts.append(f"Products: {state.product_count}")
    if state.features:
        parts.append(f"Features needed: {', '.join(state.features)}")
    if state.budget:
        parts.append(f"Budget: {state.budget}")
    if state.timeline:
        parts.append(f"Timeline: {state.timeline}")
    if state.decision_maker:
        parts.append(f"Decision maker: {state.decision_maker}")
    if state.pain_points:
        parts.append(f"Pain points: {', '.join(state.pain_points)}")
    if state.barrier:
        parts.append(f"Barrier/concern: {state.barrier}")
    return "\n".join(parts) if parts else "No information extracted yet."


def _build_messages(
    history: List[dict],
    state: LeadState,
    latest_customer_turn: str,
) -> list[dict]:
    """Build the message array for the API call. Compact: system + state + last 8 turns."""
    system_content = SALES_SYSTEM_PROMPT + "\n\n" + STATE_CONTEXT_TEMPLATE.format(
        state=_build_state_block(state)
    )

    messages = [{"role": "system", "content": system_content}]

    # Keep only the last 8 turns for latency (PRD section 11.2)
    recent = history[-8:] if len(history) > 8 else history
    for turn in recent:
        messages.append(turn)

    # Add the latest customer turn if not already the last in history
    if not history or history[-1].get("content") != latest_customer_turn:
        messages.append({"role": "user", "content": latest_customer_turn})

    return messages


async def generate_reply(
    history: List[dict],
    state: LeadState,
    latest_customer_turn: str,
) -> str:
    """Call Groq LLM to generate the next bot reply. Returns empty string on failure."""
    api_key = settings.GROQ_API_KEY.get_secret_value()
    if not api_key:
        logger.warning("GROQ_API_KEY not set – falling back to empty reply")
        return ""

    messages = _build_messages(history, state, latest_customer_turn)

    payload = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": 120,
        "temperature": 0.7,
        "top_p": 0.9,
    }

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.post(
                GROQ_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
            if response.status_code >= 400:
                logger.error("Groq API error {}: {}", response.status_code, response.text[:200])
                return ""
            data = response.json()
            reply = data["choices"][0]["message"]["content"].strip()
            logger.info("LLM reply ({} tokens): {}", data.get("usage", {}).get("completion_tokens", "?"), reply[:80])
            return reply
    except Exception as exc:
        logger.error("Groq LLM call failed: {}", exc)
        return ""
