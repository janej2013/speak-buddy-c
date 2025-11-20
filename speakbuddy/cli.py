import argparse
import os
from typing import Optional

from .llm import LLMClient
from .session import DailyPracticeSession, LevelCheckSession


def build_client() -> LLMClient:
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    return LLMClient(api_key=api_key, model=model)


def run_level_check():
    client = build_client()
    session = LevelCheckSession(client)
    question = session.start()
    print(f"Coach: {question}")
    while not session.state.completed:
        user_input = input("You: ")
        result = session.process_response(user_input)
        print(f"Coach: {result['next_question']}")
        if result["completed"]:
            print("\nSummary: " + session.summary())
            break


def run_daily_practice(topic: Optional[str]):
    default_topic = "Ordering at a café"
    topic_to_use = topic or default_topic
    client = build_client()
    session = DailyPracticeSession(topic=topic_to_use, llm_client=client)

    print(f"Today's topic: {topic_to_use}")
    while not session.state.completed:
        transcript = input("You (speak freely, then type a recap): ")
        feedback = session.coach(transcript)
        if "message" in feedback:
            print(feedback["message"])
            break
        print(f"Focus: {feedback['focus']}")
        print(f"Tip: {feedback['tip']}")
        print(f"Encouragement: {feedback['encouragement']}\n")
        if feedback["completed"]:
            print("\nGreat job! " + session.recap())
            break


def main():
    parser = argparse.ArgumentParser(description="Speak Buddy C prototype (text-based)")
    subparsers = parser.add_subparsers(dest="command")

    level_check_parser = subparsers.add_parser("level-check", help="Run onboarding speaking level check")
    level_check_parser.set_defaults(func=lambda args: run_level_check())

    practice_parser = subparsers.add_parser("daily", help="Run a daily practice round")
    practice_parser.add_argument("--topic", help="Topic for the daily round", required=False)
    practice_parser.set_defaults(func=lambda args: run_daily_practice(args.topic))

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
