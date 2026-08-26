"""Zero-cost end-to-end simulator.

Replays realistic multi-turn conversations (English, Hinglish, Telugu
mixed) against a RUNNING backend – no voice platform, no WhatsApp
account, no spend. Exercises the exact code paths a live Retell call will.

Usage:
    1. start the API:   uvicorn app.main:app --port 8000   (from backend/)
    2. run:             python ../../scripts/simulate_call.py   [or absolute path]
"""
import json
import sys
import time
import uuid

import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_URL = "http://localhost:8000"

CONVERSATIONS = {
    "HOT (English, direct)": [
        "Hello, yes tell me",
        "I sell handmade jewellery online, around 200 products. I need payment gateway and inventory management.",
        "Budget is around 3 lakh, and I want to launch within one month.",
        "Sounds good, send me the details on WhatsApp.",
    ],
    "WARM (Hinglish, barrier + callback)": [
        "Haan bolo, website ki kya baat hai?",
        "Interest toh hai, budget thoda tight hai abhi.",
        "My brother handles these decisions, main unse baat karungi.",
        "Aap kal shaam ko call kar lijiye.",
    ],
    "COLD (exploring)": [
        "Kya hai ye?",
        "Just looking around for now, no need right now.",
    ],
    "MIXED (Telugu-English code switch)": [
        "Website kavali naaku, telugulo cheppandi",
        "I need online store, my budget is 2 lakh within this month, how soon can you start?",
    ],
}


def run_conversation(client: httpx.Client, name: str, turns: list[str]) -> dict:
    call_sid = f"SIM-{uuid.uuid4().hex[:10]}"
    print(f"\n{'=' * 60}\n{name}   [{call_sid}]\n{'=' * 60}")

    summary = {"intent": None, "whatsapp": None, "callback": None}
    for i, turn in enumerate(turns, 1):
        payload = {
            "call_sid": call_sid,
            "transcript": turn,
            "is_final": True,
            "language": "mixed",
        }
        response = client.post(f"{BASE_URL}/webhooks/voice", json=payload)
        response.raise_for_status()
        data = response.json()

        bot_reply = data.get("reply") or "(listening...)"
        print(f"  caller> {turn}")
        print(f"  agent > {bot_reply}")
        if data.get("intent"):
            print(
                f"          intent={data['intent']} conf={data['confidence']} "
                f"signals={data['signals']} action={data['next_action']}"
            )
        if data.get("whatsapp"):
            # Track whether it ever fired – later duplicates are correct behaviour.
            if data["whatsapp"].get("fired"):
                summary["whatsapp"] = data["whatsapp"]
            print(f"          whatsapp -> {data['whatsapp']}")
        if data.get("callback_scheduled_at"):
            summary["callback"] = data["callback_scheduled_at"]
            print(f"          callback booked -> {data['callback_scheduled_at']}")
        summary["intent"] = data.get("intent") or summary["intent"]
        time.sleep(0.1)

    return summary


def main() -> int:
    try:
        client = httpx.Client(timeout=30)
        client.get(f"{BASE_URL}/health").raise_for_status()
    except Exception:
        print("Backend not running on :8000 – start uvicorn first.")
        return 1

    results = {name: run_conversation(client, name, turns) for name, turns in CONVERSATIONS.items()}

    print(f"\n{'=' * 60}\nSUMMARY\n{'=' * 60}")
    ok = True
    expected = {
        "HOT (English, direct)": ("HOT", "fired"),
        "WARM (Hinglish, barrier + callback)": ("WARM", "booked"),
        "COLD (exploring)": ("COLD", None),
        "MIXED (Telugu-English code switch)": ("HOT", "fired"),
    }
    for name, result in results.items():
        want_intent, extra = expected[name]
        checks = [result["intent"] == want_intent]
        if extra == "fired":
            checks.append(bool(result["whatsapp"]) and result["whatsapp"].get("fired"))
        if extra == "booked":
            checks.append(bool(result["callback"]))
        passed = all(checks)
        ok &= passed
        print(f"  {'PASS' if passed else 'FAIL'}  {name}: {json.dumps(result)}")

    print("\nALL SCENARIOS PASSED" if ok else "\nSOME SCENARIOS FAILED")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
