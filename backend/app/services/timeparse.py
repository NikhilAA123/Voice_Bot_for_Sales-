"""Natural spoken time parsing – PRD Day 8 requirement.

Turns "call me back tomorrow morning", "Monday 5 PM", "in 2 days",
"kal shaam ko" into a concrete timezone-aware datetime (Asia/Kolkata).

Deliberately rule-based and deterministic: scheduling must never depend on
an LLM's mood. Unknown expressions return None so the caller can ask again.
"""
import re
from datetime import datetime, timedelta
from typing import Optional, Tuple
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

_DEFAULT_HOUR = 11          # bare "tomorrow" -> 11:00 IST
_PART_OF_DAY_HOURS = {
    "morning": 11,
    "subah": 11,
    "afternoon": 14,
    "dopahar": 14,
    "evening": 18,
    "shaam": 18,
    "shyam": 18,
    "night": 20,
    "raat": 20,
}

_WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
    # Hinglish
    "somvaar": 0, "mangalvaar": 1, "budhvaar": 2, "guruvaar": 3,
    "shukravaar": 4, "shanivaar": 5, "ravivaar": 6,
}


def _ist_now() -> datetime:
    return datetime.now(IST)


_CLOCK_RE = re.compile(
    r"(?:\bat\s+(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?|baje)?\b)"   # at 5 / at 5:30 pm / at 11 baje
    r"|\b(\d{1,2}):(\d{2})\s*(a\.?m\.?|p\.?m\.?)?"                        # 17:00 / 10:30 pm
    r"|\b(\d{1,2})\s*(a\.?m\.?|p\.?m\.?|baje)\b",                          # 5pm / 11 am / 6 baje
    re.IGNORECASE,
)


def _match_clock(text: str):
    """Return (hour, minute, marker) from an explicit clock mention, else None."""
    match = _CLOCK_RE.search(text)
    if not match:
        return None
    if match.group(1):                                  # "at ..." form
        return int(match.group(1)), int(match.group(2) or 0), match.group(3)
    if match.group(4):                                  # "H:MM ..." form
        return int(match.group(4)), int(match.group(5)), match.group(6)
    return int(match.group(7)), 0, match.group(8)       # "5pm" form


def _apply_part_of_day(dt: datetime, text: str) -> Tuple[datetime, bool]:
    """Set hour from an explicit clock time or 'morning/evening/...'.

    Returns (datetime, explicit_clock_time_given).
    """
    clock = _match_clock(text)
    if clock:
        hour, minute, marker = clock
        if marker:
            marker = marker.replace(".", "").lower()
            if marker == "pm" and hour < 12:
                hour += 12
            elif marker == "baje" and hour <= 7:
                hour += 12                              # "6 baje" said for evening
            elif marker == "am" and hour == 12:
                hour = 0
        elif hour <= 7:
            # No marker and small hour: "call at 5" means evening.
            hour += 12
        if 0 <= hour <= 23:
            return dt.replace(hour=hour, minute=minute, second=0, microsecond=0), True

    for label, hour in _PART_OF_DAY_HOURS.items():
        if re.search(rf"\b{label}\b", text):
            return dt.replace(hour=hour, minute=0, second=0, microsecond=0), False

    return dt.replace(hour=_DEFAULT_HOUR, minute=0, second=0, microsecond=0), False


def _next_weekday(today: datetime, target: int) -> datetime:
    days_ahead = (target - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7          # "Monday" said on a Monday means next Monday
    return today + timedelta(days=days_ahead)


def parse_callback_time(text: str, *, now: Optional[datetime] = None) -> Optional[datetime]:
    """Parse a natural spoken callback time into an aware IST datetime.

    Returns None when no recognizable day/time is present – the agent should
    ask the caller to repeat rather than guess (PRD: unknown stays unknown).
    """
    if not text or not text.strip():
        return None

    now = now or _ist_now()
    low = text.lower()
    base_day: Optional[datetime] = None
    explicit_relative_days: Optional[int] = None

    # --- day resolution -----------------------------------------------------
    if re.search(r"\baaj\b|\btoday\b", low):
        base_day = now
    elif re.search(r"\bk(?:a|aa)l\b|\btomorrow\b", low):
        base_day = now + timedelta(days=1)
    elif re.search(r"\bparso\b|day after tomorrow", low):
        base_day = now + timedelta(days=2)
    elif re.search(r"\bin\s+(?:a|one)?\s*week\b|\bnext week\b|\bhafte\b", low):
        base_day = now + timedelta(days=7)
    else:
        rel = re.search(r"\bin\s+(\d+)\s+days?\b", low)
        if rel:
            explicit_relative_days = int(rel.group(1))
            base_day = now + timedelta(days=explicit_relative_days)
        else:
            weekday = next((wd for name, wd in _WEEKDAYS.items() if re.search(rf"\b{name}", low)), None)
            if weekday is not None:
                base_day = _next_weekday(now, weekday)

    if base_day is None:
        # A bare clock time ("can you call at 6") still schedules today/tomorrow.
        candidate, explicit = _apply_part_of_day(now, low)
        if explicit and candidate > now - timedelta(minutes=1):
            return candidate
        return None

    base_day = base_day.replace(minute=0, second=0, microsecond=0)
    result, _explicit = _apply_part_of_day(base_day, low)

    # If only a weekday was named without a time-of-day, keep default slot.
    return result


# ---------------------------------------------------------------------------
# Barrier extraction helper used by the WARM flow (PRD section 9.2 / US-06)
# ---------------------------------------------------------------------------

_BARRIER_PATTERNS = [
    r"\bbudget\b", r"\btiming\b", r"\btime nahi\b", r"\bno time\b",
]


def extract_barrier(transcript: str) -> Optional[str]:
    """Best-effort barrier capture until Claude takes over extraction."""
    low = transcript.lower()
    for pattern in _BARRIER_PATTERNS:
        if re.search(pattern, low):
            return pattern.strip("\\b")
    return None
