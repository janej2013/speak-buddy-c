from speakbuddy.llm import LLMClient
from speakbuddy.session import DailyPracticeSession, LevelCheckSession


def test_level_check_reaches_completion_with_fallback():
    client = LLMClient(api_key=None)
    session = LevelCheckSession(client, max_turns=3, stop_confidence=0.9)
    question = session.start()
    assert question

    for _ in range(3):
        result = session.process_response("I answered with a few sentences about my day.")
        if result["completed"]:
            break

    assert session.state.completed is True
    assert session.summary().startswith("Estimated level")


def test_daily_practice_cycles_feedback():
    client = LLMClient(api_key=None)
    session = DailyPracticeSession(topic="Ordering coffee", llm_client=client, max_turns=2)
    feedback = session.coach("I want a latte please.")
    assert "focus" in feedback
    assert feedback["turn_index"] == 1

    feedback = session.coach("Adding more details and clarity in my second try.")
    assert feedback["completed"] is True
    recap = session.recap()
    assert "Topic: Ordering coffee" in recap
