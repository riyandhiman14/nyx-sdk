#!/usr/bin/env python3
"""
AI Agent demo using Nyx AgentBrowser + Gemini.

Perceive-decide-act loop: snapshot the page, ask the LLM for a JSON action,
execute it, repeat.

Usage:
    pip install nyx-browser google-genai
    python agent_gemini.py "Find the price of the cheapest book on books.toscrape.com"
"""

import asyncio
import json
import sys

from google import genai

from nyx import AgentBrowser
from nyx.agent_prompt import AGENT_SYSTEM_PROMPT

client = genai.Client()
MODEL = "gemini-2.5-flash"


def format_snapshot(snap) -> str:
    """Format a Snapshot into a compact string for the LLM."""
    elements = "\n".join(
        f"  [{e.get('tag')} id={e.get('action_id', '')}"
        + (f" name={a['name']}" if (a := e.get("attributes", {})).get("name") else "")
        + (f' placeholder="{a["placeholder"]}"' if a.get("placeholder") else "")
        + (f" href={a['href'][:60]}" if a.get("href") else "")
        + f"] {(e.get('text') or '')[:80]}"
        for e in snap.elements[:60]
    )
    return (
        f"URL: {snap.url}\n"
        f"Title: {snap.title}\n"
        f"Text: {snap.page_text[:1000]}\n"
        f"Elements:\n{elements}\n"
        f"has_more: {snap.has_more}"
    )


def parse_json_action(text: str) -> dict | None:
    """Extract a JSON object from LLM output, stripping markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None


async def run_agent(task: str, *, max_steps: int = 15, headless: bool = True):
    print(f"\n--- Task: {task}\n")

    async with await AgentBrowser.launch(headless=headless) as browser:
        history = [
            {"role": "user", "parts": [{"text": f"{AGENT_SYSTEM_PROMPT}\n\nTask: {task}"}]}
        ]

        for step in range(1, max_steps + 1):
            snap = await browser.snapshot(full=True)
            state = format_snapshot(snap)
            history.append({"role": "user", "parts": [{"text": state}]})

            reply = client.models.generate_content(
                model=MODEL, contents=history
            ).text.strip()

            print(f"  [{step}] {reply}")
            history.append({"role": "model", "parts": [{"text": reply}]})

            cmd = parse_json_action(reply)
            if cmd is None:
                history.append({"role": "user", "parts": [
                    {"text": "Invalid JSON. Respond with a single JSON object."}
                ]})
                continue

            action = cmd.get("action")

            # Done
            if action == "done":
                result = cmd.get("result", "")
                print(f"\n  Result: {result}")
                await browser.screenshot(path="result.png")
                return result

            # Execute
            target = cmd.pop("target", None)
            cmd.pop("action", None)
            try:
                snap = await browser.act(action, target, **cmd)
                print(f"    -> {action} {target or ''}")
            except Exception as e:
                err = str(e)[:150]
                print(f"    x  {err}")
                history.append({"role": "user", "parts": [
                    {"text": f"Error: {err}. Try a different target or approach."}
                ]})

        print("\n  Max steps reached.")
        return None


if __name__ == "__main__":
    task = " ".join(sys.argv[1:]) or "What is the title of the first book on books.toscrape.com?"
    asyncio.run(run_agent(task))
