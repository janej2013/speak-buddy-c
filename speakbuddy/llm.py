import json
from dataclasses import dataclass
from typing import Dict, List, Optional
from urllib import request


@dataclass
class LevelCheckResult:
    next_question: str
    level_tag: str
    confidence: float
    rationale: str


@dataclass
class PracticeFeedback:
    focus_bullet: str
    tip: str
    encouragement: str
    should_end: bool


class LLMClient:
    """Lightweight wrapper around an LLM API with an offline fallback."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model
        self._fallback_question_bank = [
            "What did you do today?",
            "Tell me about your favorite food.",
            "What kind of movies do you like?",
            "Describe a place you want to visit.",
            "What do you enjoy doing on weekends?",
        ]
        self._practice_focuses = [
            "Pronunciation: slow down and enunciate key nouns.",
            "Sentence structure: use one clear main clause.",
            "Fillers: reduce ums/ahs by pausing briefly.",
            "Vocabulary: add one descriptive adjective.",
            "Pace: keep answers under 20 seconds.",
        ]

    def generate_level_check(self, history: List[Dict[str, str]]) -> LevelCheckResult:
        if not self.api_key:
            return self._fallback_level_check(history)

        prompt = self._render_level_check_prompt(history)
        payload = {
            "model": self.model,
            "messages": prompt,
            "temperature": 0.4,
            "response_format": {"type": "json_object"},
        }
        response = self._call_openai(payload)
        content = json.loads(response)
        return LevelCheckResult(
            next_question=content.get("next_question", "Tell me about your day."),
            level_tag=content.get("level_tag", "A2"),
            confidence=float(content.get("confidence", 0.3)),
            rationale=content.get("rationale", "Based on vocabulary range."),
        )

    def generate_practice_feedback(
        self, topic: str, last_focus: Optional[str], transcript: str, turn_index: int
    ) -> PracticeFeedback:
        if not self.api_key:
            return self._fallback_practice_feedback(topic, last_focus, transcript, turn_index)

        prompt = self._render_practice_prompt(topic, last_focus, transcript, turn_index)
        payload = {
            "model": self.model,
            "messages": prompt,
            "temperature": 0.4,
            "response_format": {"type": "json_object"},
        }
        response = self._call_openai(payload)
        content = json.loads(response)
        return PracticeFeedback(
            focus_bullet=content.get("focus_bullet", "Pronunciation: slow down."),
            tip=content.get("tip", "Aim for one clear sentence."),
            encouragement=content.get("encouragement", "Nice effort!"),
            should_end=bool(content.get("should_end", False)),
        )

    def _call_openai(self, payload: Dict) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        req = request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]

    def _render_level_check_prompt(self, history: List[Dict[str, str]]):
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a friendly English speaking coach. Ask brief, everyday questions. "
                    "Suggest a CEFR-like level tag (A1-C1) with confidence 0-1 and a 2-sentence rationale. "
                    "Return JSON with next_question, level_tag, confidence, rationale."
                ),
            },
            {
                "role": "user",
                "content": "Here are the recent turns:",
            },
        ]
        for turn in history:
            messages.append({"role": "user", "content": turn["user"]})
            if "assistant" in turn:
                messages.append({"role": "assistant", "content": turn["assistant"]})
        messages.append(
            {
                "role": "user",
                "content": "Respond with the JSON payload only.",
            }
        )
        return messages

    def _render_practice_prompt(
        self, topic: str, last_focus: Optional[str], transcript: str, turn_index: int
    ) -> List[Dict[str, str]]:
        system = {
            "role": "system",
            "content": (
                "You are an encouraging English speaking coach. Keep replies concise. "
                "Return JSON with focus_bullet, tip, encouragement, should_end."
            ),
        }
        user_msg = {
            "role": "user",
            "content": json.dumps(
                {
                    "topic": topic,
                    "transcript": transcript,
                    "last_focus": last_focus,
                    "turn_index": turn_index,
                }
            ),
        }
        return [system, user_msg]

    def _fallback_level_check(self, history: List[Dict[str, str]]) -> LevelCheckResult:
        user_turns = [h for h in history if "user" in h]
        turn_index = len(user_turns)
        question = self._fallback_question_bank[turn_index % len(self._fallback_question_bank)]
        word_count = sum(len(h["user"].split()) for h in user_turns)
        if word_count > 60:
            level_tag = "B2"
        elif word_count > 40:
            level_tag = "B1"
        elif word_count > 20:
            level_tag = "A2"
        else:
            level_tag = "A1"
        confidence = min(0.25 + 0.15 * turn_index + word_count * 0.003, 0.95)
        rationale = (
            "Longer answers with varied verbs suggest stronger fluency."
            if word_count > 30
            else "Short, simple phrases suggest beginner confidence."
        )
        return LevelCheckResult(
            next_question=question,
            level_tag=level_tag,
            confidence=round(confidence, 2),
            rationale=rationale,
        )

    def _fallback_practice_feedback(
        self, topic: str, last_focus: Optional[str], transcript: str, turn_index: int
    ) -> PracticeFeedback:
        focus = self._practice_focuses[turn_index % len(self._practice_focuses)]
        tip = "Aim for one clear idea and a closing sentence."
        encouragement = "Nice progress—let's try that again!"
        should_end = turn_index >= 4 or len(transcript.split()) > 80
        return PracticeFeedback(
            focus_bullet=f"{focus} (Topic: {topic})",
            tip=tip,
            encouragement=encouragement,
            should_end=should_end,
        )
