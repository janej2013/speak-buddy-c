from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .llm import LLMClient, LevelCheckResult, PracticeFeedback


@dataclass
class Turn:
    user: str
    assistant: Optional[str] = None


@dataclass
class LevelCheckState:
    turns: List[Turn] = field(default_factory=list)
    latest_result: Optional[LevelCheckResult] = None
    completed: bool = False


class LevelCheckSession:
    """Handles up to five onboarding questions to estimate speaking level."""

    def __init__(self, llm_client: LLMClient, max_turns: int = 5, stop_confidence: float = 0.7):
        self.llm = llm_client
        self.max_turns = max_turns
        self.stop_confidence = stop_confidence
        self.state = LevelCheckState()

    def start(self) -> str:
        result = self.llm.generate_level_check([])
        self.state.latest_result = result
        self.state.turns.append(Turn(user="", assistant=result.next_question))
        return result.next_question

    def process_response(self, transcript: str) -> Dict:
        # Attach user response to prior assistant question
        if not self.state.turns:
            raise ValueError("Call start() before processing responses.")

        self.state.turns[-1].user = transcript
        history = [
            {"user": turn.user, "assistant": turn.assistant}
            for turn in self.state.turns
        ]
        result = self.llm.generate_level_check(history)
        self.state.latest_result = result
        self.state.turns.append(Turn(user="", assistant=result.next_question))

        self.state.completed = len(self.state.turns) - 1 >= self.max_turns or result.confidence >= self.stop_confidence
        return {
            "next_question": result.next_question,
            "level_tag": result.level_tag,
            "confidence": result.confidence,
            "rationale": result.rationale,
            "completed": self.state.completed,
        }

    def summary(self) -> str:
        if not self.state.latest_result:
            return "Level check has not started."
        return (
            f"Estimated level: {self.state.latest_result.level_tag} "
            f"(confidence {self.state.latest_result.confidence}). "
            f"Reason: {self.state.latest_result.rationale}"
        )


@dataclass
class PracticeTurn:
    transcript: str
    feedback: PracticeFeedback


@dataclass
class DailyPracticeState:
    topic: str
    turns: List[PracticeTurn] = field(default_factory=list)
    last_focus: Optional[str] = None
    completed: bool = False


class DailyPracticeSession:
    """Guides a daily 5-turn coaching loop around a topic."""

    def __init__(self, topic: str, llm_client: LLMClient, max_turns: int = 5):
        self.llm = llm_client
        self.state = DailyPracticeState(topic=topic)
        self.max_turns = max_turns

    def coach(self, transcript: str) -> Dict:
        if self.state.completed:
            return {"message": "Session already complete."}

        turn_index = len(self.state.turns)
        feedback = self.llm.generate_practice_feedback(
            topic=self.state.topic,
            last_focus=self.state.last_focus,
            transcript=transcript,
            turn_index=turn_index,
        )
        self.state.last_focus = feedback.focus_bullet
        self.state.turns.append(PracticeTurn(transcript=transcript, feedback=feedback))
        self.state.completed = feedback.should_end or len(self.state.turns) >= self.max_turns
        return {
            "focus": feedback.focus_bullet,
            "tip": feedback.tip,
            "encouragement": feedback.encouragement,
            "should_end": feedback.should_end,
            "turn_index": turn_index + 1,
            "completed": self.state.completed,
        }

    def recap(self) -> str:
        if not self.state.turns:
            return "No practice attempts yet."
        final_focus = self.state.last_focus or "a specific focus area"
        return (
            f"Topic: {self.state.topic}. Completed {len(self.state.turns)} turn(s). "
            f"Latest focus: {final_focus}. Nice work!"
        )
