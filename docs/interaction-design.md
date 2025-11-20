# Speak Buddy C Interaction and Prompt Design

This document outlines the conversation flow, LLM prompt patterns, and feedback logic for the first version of the app.

## Onboarding Speaking Level Check
- **Goal:** classify a new user’s speaking comfort level in ≤5 questions while keeping the tone welcoming.
- **Flow:**
  1. Greet the user with a light, open question (e.g., “What did you do today?”).
  2. After each user response, send transcript + prior turns to the LLM.
  3. The LLM returns: next question, provisional level tag (A1–C1), rationale (≤2 sentences), and a confidence score.
  4. Stop early if confidence is high; otherwise cap at five turns.
  5. Display a one-line summary and set the daily practice difficulty using the level tag.
- **Prompt skeleton:**
  - System: role as friendly English speaking coach; avoid sensitive topics; keep questions short.
  - User data: recent Q&A turns, maximum of five turns remaining, current confidence/level.
  - Response format: JSON with fields `next_question`, `level_tag`, `confidence`, `rationale`.

## Daily Practice Round
- **Goal:** quick 5-minute warm-up with targeted feedback and encouragement.
- **Flow per round:**
  1. Show a topic card (e.g., “Ordering at a café”). User records a response first.
  2. Send transcript + topic + last feedback focus to the LLM.
  3. LLM returns: one bullet for improvement focus, a micro-tip (≤1 sentence), and a short encouraging reply to play back.
  4. User retries once. Mark success if the retry addresses the focus; otherwise rotate to a new focus.
  5. Limit to five total exchanges; finish with a “streak” or “nice progress” toast.
- **Prompt skeleton:**
  - System: concise coach; celebrate small wins; return compact answers.
  - User data: topic, last focus, current turn index, transcript(s), and desired tone.
  - Response format: JSON with `focus_bullet`, `tip`, `encouragement`, `should_end`.

## LLM Guardrails
- Keep topics neutral and everyday; disallow politics, health, and personal data requests.
- Reject or replace empty or noisy transcripts with a gentle clarification request.
- Ensure every response fits on a mobile screen (≤280 characters per field).

## UX Notes
- Primary CTA is a single record/stop button with visual feedback (waveform or pulsing ring).
- Show progress as 1–5 dots; fill as turns complete.
- Offer “skip topic” and “mute feedback voice” toggles to keep control in the user’s hands.

## Analytics (future)
- Track events: `level_check_started`, `level_check_completed`, `daily_round_started`, `retry`, `focus_satisfied`, `topic_skipped`.
- Avoid storing raw audio unless the user opts in; prefer transcript-only for summaries.
