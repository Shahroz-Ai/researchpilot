import json
import os
import re
import time

from dotenv import load_dotenv
from groq import Groq

from tools import TOOL_SCHEMAS, run_tool

load_dotenv()


def get_api_key():
    """Read the key from .env locally, or from Streamlit secrets when deployed."""
    key = os.getenv("GROQ_API_KEY")
    if key:
        return key
    try:
        import streamlit as st

        return st.secrets["GROQ_API_KEY"]
    except Exception:
        return None


client = Groq(api_key=get_api_key())

# Main model first, then fallbacks
MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
]

MAX_STEPS = 8
MAX_DUPLICATES = 3
NOTE_CHARS = 2500
NOTES_TOTAL_CHARS = 14000

SYSTEM_PROMPT = """You are ResearchPilot, a careful research agent.

You have three tools: web_search, read_page, and calculator.

How to work:
1. Break the question into what you need to find out.
2. Use web_search to find sources. When comparing several items (brands, products, countries), search for each item separately.
3. Use read_page on promising URLs. If the result says the page continues, call read_page again with the given start value instead of re-reading the beginning.
4. Use calculator for any math. Do not do math in your head.
5. Never repeat the exact same call. If a search gives nothing new, change the query or write the answer.
6. Stop once you have enough evidence.
"""

FINAL_PROMPT = """You are ResearchPilot. You cannot use tools now. Write the final report
using ONLY the research notes provided.

Rules:
- Write a clear, structured report in Markdown.
- Only state facts that appear in the notes. If a figure or detail was not found, write "not found in sources". Never estimate or fill gaps from general knowledge.
- If sources disagree, say so.
- Cite with plain numbers like [1], [2], numbered in order starting from 1, matching the Sources list. Never use special citation marks.
- Do not add details such as range per charge, battery type, or rankings unless the notes state them. When you call something the cheapest or the best, check it against the actual numbers in the notes.
- The Sources section must list full URLs (https://...), not article titles.
- Use plain Markdown only. Do not use HTML tags such as <br>.
- End with a "Sources" section listing only URLs that appear in the notes.
"""


def call_model(messages, use_tools=True, retries=2):
    """Call the LLM with retry and model fallback. Returns a message or None."""
    for model in MODELS:
        for attempt in range(retries):
            try:
                kwargs = {"model": model, "messages": messages, "temperature": 0.3}
                if use_tools:
                    kwargs["tools"] = TOOL_SCHEMAS
                response = client.chat.completions.create(**kwargs)
                return response.choices[0].message
            except Exception as e:
                message = str(e)
                print(f"[{model}] attempt {attempt + 1} failed: {message[:100]}")
                # A missing model or a bad request will not recover, so try the next model
                if "404" in message or "400" in message:
                    break
                time.sleep(2 * (attempt + 1))
    return None


def force_final(question, notes):
    """Write the final report from collected notes, with no tools involved."""
    gathered = "\n\n".join(notes)[:NOTES_TOTAL_CHARS]
    messages = [
        {"role": "system", "content": FINAL_PROMPT},
        {
            "role": "user",
            "content": f"Question: {question}\n\nResearch notes:\n{gathered}",
        },
    ]
    return call_model(messages, use_tools=False)


def _run_agent(question, max_steps=MAX_STEPS):
    """Run the agent loop. Yields events so a UI can show progress live."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    seen_calls = set()
    notes = []
    duplicates = 0

    for step in range(1, max_steps + 1):
        msg = call_model(messages)
        if msg is None:
            yield {"type": "error", "content": "All models failed. Please try again."}
            return

        # No tool requested: the model is giving its final answer
        if not msg.tool_calls:
            # Ask for the report through the notes-based prompt for consistent quality
            if notes:
                final = force_final(question, notes)
                if final is not None:
                    yield {"type": "final", "content": final.content or ""}
                    return
            yield {"type": "final", "content": msg.content or ""}
            return

        # Record the model's tool request in the conversation
        messages.append(
            {
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ],
            }
        )

        # Run every requested tool and send results back
        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}

            yield {
                "type": "tool_call",
                "step": step,
                "name": tc.function.name,
                "args": args,
            }

            call_key = (tc.function.name, json.dumps(args, sort_keys=True))
            if call_key in seen_calls:
                duplicates += 1
                result = "You already made this exact call. Change the query, read a different part of the page, or write your final answer."
            else:
                seen_calls.add(call_key)
                result = run_tool(tc.function.name, args)
                notes.append(
                    f"[{tc.function.name} {json.dumps(args)}]\n{result[:NOTE_CHARS]}"
                )

            yield {"type": "tool_result", "name": tc.function.name, "result": result}
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

        # The agent is stuck repeating itself: stop and write the report
        if duplicates >= MAX_DUPLICATES:
            break

    # Step limit or repeat limit reached: write the report from collected notes
    msg = force_final(question, notes)
    if msg is None:
        yield {"type": "error", "content": "All models failed. Please try again."}
    else:
        yield {"type": "final", "content": msg.content or ""}


def clean_citations(text):
    """Turn special citation marks like 【1†L1-L4】 into plain [1]."""
    return re.sub(r"【(\d+)[^】]*】", r"[\1]", text)


def run_agent(question, max_steps=MAX_STEPS):
    """Public entry point: runs the agent and cleans the final report."""
    for event in _run_agent(question, max_steps):
        if event["type"] == "final":
            event["content"] = clean_citations(event["content"])
        yield event


if __name__ == "__main__":
    question = input("Research question: ").strip()
    for event in run_agent(question):
        if event["type"] == "tool_call":
            print(f"\n🔧 Step {event['step']}: {event['name']}({event['args']})")
        elif event["type"] == "tool_result":
            print(f"   ↳ got {len(event['result'])} characters")
        elif event["type"] == "final":
            print("\n" + "=" * 60)
            print(event["content"])
        elif event["type"] == "error":
            print("\n❌", event["content"])