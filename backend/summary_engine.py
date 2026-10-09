import json
from dotenv import load_dotenv
from anthropic import Anthropic, APIError
import time

load_dotenv()

client = Anthropic()

# System prompts for respective summary type
dossier_system_prompt = """
You are an OSINT analyst maintaining a running dossier on a monitored target.
You will be given the complete set of search results collected for this target
to date. Write a current, standing summary of what is known: who or what the
target is, the significant developments, and any recurring themes across the
results.

Ground every statement in the provided results and do not speculate beyond
them. Where results conflict or are uncertain, note the uncertainty rather
than resolving it. Organize by significance, not chronology. Keep the dossier
roughly 500 words. Prioritize the most significant findings over exhaustive coverage,
 omit sections that would be empty or speculative rather than noting their absence.
 """
digest_system_prompt = """
You are an OSINT analyst writing a daily briefing for a monitored target.
You will be given a set of new search results that surfaced since the last
report. Write a short briefing with a one-line headline followed by a brief
narrative (2-4 sentences) explaining what these results collectively suggest.

Ground every statement in the provided results. Do not infer facts,
motivations, or events that the snippets do not directly support — if the
results are thin or ambiguous, say so plainly rather than filling the gap.
Lead with what matters most. Do not restate every result; synthesize.
"""


# Formatting alerts into labeled text for clean handover to Anthropic model
def format_alerts(alerts: list[dict]):
    formatted = []
    for alert in alerts:
        strip = (
            f"Alert {alert.get('id')}:\n"
            f"Title: {alert.get('title') or 'untitled'}\n"
            f"Source: {alert.get('source') or 'unknown'}\n"
            f"Snippet: {alert.get('snippet') or 'no snippet'}"
        )
        formatted.append(strip)
    return "\n\n".join(formatted)


# Formatting alerts into a json schema per call, and locks severity to enum and alert ids to themselves
def build_schema(alerts: list[dict]):
    ids = [alert["id"] for alert in alerts]
    return {
        "type": "object",
        "properties": {
            "headline": {"type": "string"},
            "narrative": {"type": "string"},
            "severity": {"type": "string", "enum": ["low", "medium", "high"]},
            "alert_ids": {"type": "array", "items": {"type": "integer", "enum": ids}},
        },
        "required": ["headline", "narrative", "severity", "alert_ids"],
        "additionalProperties": False,
    }


# the bulk of this program, determines summary type and then runs Anthropic api query
def generate_summary(kind: str, alerts: list[dict]):

    # effort controls how much the model thinks (thinking is always on for this model)
    config = {"effort": "medium"}
    if kind == "digest":
        sys = digest_system_prompt
        config["format"] = {"type": "json_schema", "schema": build_schema(alerts)}
    elif kind == "dossier":
        sys = dossier_system_prompt
    else:
        raise ValueError("generation type not defined")

    formatted = format_alerts(alerts)

    try:
        t0 = time.perf_counter()
        prompt = client.beta.messages.create(
            model="claude-opus-5-5",
            # room for the model's thinking as well as the reply
            max_tokens=16000,
            system=sys,
            messages=[{"role": "user", "content": formatted}],
            output_config=config,
            # reroute to another model if a safety classifier declines the request
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
        elapsed = time.perf_counter() - t0
        if prompt.stop_reason == "refusal":
            return {"success": False, "error": "model declined the request"}
        if prompt.stop_reason != "end_turn":
            return {"success": False, "error": f"stopped early: {prompt.stop_reason}"}
        # the response starts with thinking blocks, so take the text block
        text = next((b.text for b in prompt.content if b.type == "text"), None)
        if text is None:
            return {"success": False, "error": "response had no text"}
        # Need that json loads to format the json string into a python dict for handling
        return_result = json.loads(text) if kind == "digest" else text
        return {
            "success": True,
            "results": return_result,
            "seconds": round(elapsed, 2),
            "input_tokens": prompt.usage.input_tokens,
            "output_tokens": prompt.usage.output_tokens,
        }
    except (APIError, json.JSONDecodeError) as error:
        return {"success": False, "error": f"{type(error).__name__}: {error}"}
