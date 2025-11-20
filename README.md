# Speak Buddy C

Speak Buddy C is a concept for a game-like web app that helps learners practice spoken English in under five minutes per day. The experience blends quick calibration for new users with daily practice rounds that feel like short, guided conversations.

## Key Objectives
- Keep each practice session under five minutes and cap interactions at five questions.
- Deliver a sense of progress through clear guidance, targeted feedback, and small wins.
- Use an LLM to generate prompts, judge responses, and provide next-step coaching.

## Core Experiences
### New User Level Check
1. Start a short warm-up conversation (up to five turns) to estimate speaking level.
2. The app calls an LLM to generate each question and to evaluate the spoken reply.
3. The evaluation tags the response with CEFR-like hints (e.g., A2, B1) and short rationales.
4. The next question uses the prior Q&A and the provisional level to adjust complexity.
5. After five questions or an early confident classification, the user receives a brief summary and a suggested starting track.

### Daily Practice Round
1. The app selects a fresh topic and shows it up front so the user can respond first.
2. The user records a short answer; the app sends the transcript to the LLM for feedback.
3. The LLM returns a focused bullet point to improve (pronunciation, structure, pace, filler words, etc.) and a one-sentence tip.
4. The user retries with the tip in mind; the app replies with a short, encouraging note.
5. Repeat until five exchanges or the daily timebox is reached, then show a quick win message and a “Come back tomorrow” nudge.

## System Highlights
- **LLM integration:** Prompts include conversation history, user level, and the single improvement focus for the next turn. Responses are kept concise (1–2 sentences and a bullet point).
- **Voice-first UI:** Large record button, waveform or mic indicator, and playful progress markers (e.g., badges for completing a streak).
- **Safety:** Keep prompts neutral; avoid sensitive topics. Provide a “skip topic” control.
- **Session memory:** Store recent turns client-side during a round; persist anonymized transcripts for analytics only if the user opts in.

## Suggested Next Steps
- Draft high-level UI wireframes for the calibration flow and daily round.
- Define exact LLM prompt templates and guardrails.
- Build a minimal web client with a mocked LLM endpoint to exercise the loop.
- Add analytics events for session start, completion, retry, and topic skip.

## Running the text prototype
This repository now includes a lightweight text prototype that exercises the onboarding and daily practice logic.

### Setup
1. Ensure Python 3.10+ is available.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. (Optional) Provide an OpenAI API key to use a live model:
   ```bash
   export OPENAI_API_KEY=your_key_here
   export OPENAI_MODEL=gpt-4o-mini  # override if desired
   ```

Without an API key, the prototype uses deterministic fallback logic for demo/testing.

### Run onboarding level check
```bash
python -m speakbuddy.cli level-check
```
This asks up to five questions, estimates a CEFR-like level, and stops early when confidence is high.

### Run a daily practice round
```bash
python -m speakbuddy.cli daily --topic "Ordering coffee"
```
The daily loop asks you to answer first, then returns one focus bullet, a micro tip, and encouragement on each turn (max five turns).

### Tests
Run the small test suite (uses the fallback logic, no API key required):
```bash
pytest
```
