"""Natural time parsing tests – deterministic, injected 'now'.

Reference moment: Sunday 23 Aug 2026, 15:00 IST (a real date, chosen so
weekday arithmetic is easy: Monday = tomorrow).
"""
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from app.services.timeparse import IST, parse_callback_time

NOW = datetime(2026, 8, 23, 15, 0, tzinfo=IST)


def parse(text):
    return parse_callback_time(text, now=NOW)


def test_tomorrow_morning():
    assert parse("call me back tomorrow morning") == datetime(2026, 8, 24, 11, 0, tzinfo=IST)


def test_tomorrow_explicit_pm():
    assert parse("tomorrow at 5 pm") == datetime(2026, 8, 24, 17, 0, tzinfo=IST)


def test_weekday_with_time():
    # Today is Sunday -> "Monday" means the 24th.
    assert parse("Monday 5 pm") == datetime(2026, 8, 24, 17, 0, tzinfo=IST)


def test_in_two_days_defaults_to_slot():
    assert parse("in 2 days") == datetime(2026, 8, 25, 11, 0, tzinfo=IST)


def test_in_days_with_clock():
    assert parse("in 2 days at 6 pm") == datetime(2026, 8, 25, 18, 0, tzinfo=IST)


def test_hinglish_kal_shaam():
    assert parse("aap kal shaam ko call kar lijiye") == datetime(2026, 8, 24, 18, 0, tzinfo=IST)


def test_hinglish_parso_subah():
    assert parse("parso subah baat karte hain") == datetime(2026, 8, 25, 11, 0, tzinfo=IST)


def test_next_week():
    assert parse("next week possible?") == datetime(2026, 8, 30, 11, 0, tzinfo=IST)


def test_today_evening():
    assert parse("aaj shaam") == datetime(2026, 8, 23, 18, 0, tzinfo=IST)


def test_bare_at_hour_small_means_evening():
    assert parse("can you call at 7") == datetime(2026, 8, 23, 19, 0, tzinfo=IST)


def test_bare_am_time_before_now_ok_when_morning():
    now_early = NOW.replace(hour=9)
    result = parse_callback_time("call at 11", now=now_early)
    assert result == datetime(2026, 8, 23, 11, 0, tzinfo=IST)


def test_past_time_returns_none_so_agent_reasks():
    # "at 11" when it is already 15:00 – never schedule in the past.
    assert parse("call at 11") is None


def test_24h_clock():
    now_noon = NOW.replace(hour=12)
    assert parse_callback_time("17:00", now=now_noon) == datetime(2026, 8, 23, 17, 0, tzinfo=IST)


def test_baje_marker():
    assert parse("5 baje") == datetime(2026, 8, 23, 17, 0, tzinfo=IST)


@pytest.mark.parametrize("text", ["whenever you want", "", None])
def test_unparseable_returns_none(text):
    assert parse(text) is None


def test_minutes_are_kept():
    assert parse("tomorrow at 10:45 am") == datetime(2026, 8, 24, 10, 45, tzinfo=IST)
