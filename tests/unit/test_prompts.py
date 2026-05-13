from datetime import date

from travel_assistant.agent.prompts import build_system_prompt


def test_prompt_contains_todays_date():
    today = date.today()
    prompt = build_system_prompt(today)
    assert today.isoformat() in prompt


def test_prompt_date_changes_with_argument():
    d1 = date(2026, 1, 15)
    d2 = date(2027, 6, 30)
    assert "2026-01-15" in build_system_prompt(d1)
    assert "2027-06-30" in build_system_prompt(d2)
    assert "2027-06-30" not in build_system_prompt(d1)


def test_prompt_instructs_use_of_conversation_history():
    prompt = build_system_prompt(date.today())
    assert "conversation history" in prompt.lower()


def test_prompt_instructs_extracting_tool_params_from_history():
    prompt = build_system_prompt(date.today())
    assert "earlier messages" in prompt.lower() or "earlier in the same conversation" in prompt.lower()


def test_prompt_instructs_language_matching():
    prompt = build_system_prompt(date.today())
    assert "same language" in prompt.lower()


def test_prompt_instructs_next_future_date_assumption():
    prompt = build_system_prompt(date.today())
    assert "next future" in prompt.lower() or "next occurrence" in prompt.lower()
