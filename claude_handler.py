import os
from anthropic import Anthropic

_client = None

def get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client

SYSTEM_PROMPT_TEMPLATE = """\
You are a collaborative Staff Engineer interviewer. Your role is to guide the candidate \
through this process: clarify → design → implement → test → complexity → NFRs.

Rules:
- Do not give away solutions. Push back when steps are skipped.
- You may offer up to {max_hints} hints if the candidate explicitly asks. \
You have {remaining} remaining. Never offer hints unprompted.
- When giving a hint, begin your response with the exact token [HINT] on its own line, \
then your hint text. No other response should start with [HINT].
- When the candidate presents an approach and asks for feedback, give structured insight: \
what is strong, what is missing, what tradeoffs to consider. Do not give the full solution.
- Interview type: {mode}.
  - Algo: enforce Big-O analysis and edge case coverage.
  - System Design: emphasize capacity planning, component tradeoffs, and failure modes.

Problem: {problem_statement}"""

def build_system_prompt(
    mode: str, problem: str, max_hints: int, hints_remaining: int
) -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(
        mode=mode,
        problem_statement=problem,
        max_hints=max_hints,
        remaining=hints_remaining,
    )

def chat(messages: list[dict], system_prompt: str) -> dict:
    response = get_client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system_prompt,
        messages=messages,
    )
    content = response.content[0].text.strip()
    hint_used = content.startswith("[HINT]")
    if hint_used:
        content = content[len("[HINT]"):].lstrip("\n").strip()
    return {"content": content, "hint_used": hint_used}
