import os
import json
from dotenv import load_dotenv
from anthropic import Anthropic, APIError

load_dotenv()

client = Anthropic()

dossier_system_prompt = """
You are an OSINT analyst maintaining a running dossier on a monitored target.
You will be given the complete set of search results collected for this target
to date. Write a current, standing summary of what is known: who or what the
target is, the significant developments, and any recurring themes across the
results.

Ground every statement in the provided results and do not speculate beyond
them. Where results conflict or are uncertain, note the uncertainty rather
than resolving it. Organize by significance, not chronology. This is a
reference document, so favor completeness and clarity over brevity.
 """
digest_system_prompt = ("""
You are an OSINT analyst writing a daily briefing for a monitored target.
You will be given a set of new search results that surfaced since the last
report. Write a short briefing with a one-line headline followed by a brief
narrative (2-4 sentences) explaining what these results collectively suggest.

Ground every statement in the provided results. Do not infer facts,
motivations, or events that the snippets do not directly support — if the
results are thin or ambiguous, say so plainly rather than filling the gap.
Lead with what matters most. Do not restate every result; synthesize.
""")

def format_alerts(alerts:list[dict]):
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
    

    
    


        
def generate(kind: str, alerts:list[dict]):

    if kind == "digest":
        sys = digest_system_prompt
        tok = 1000
    elif kind == "dossier": 
        sys = dossier_system_prompt
        tok = 10000
    else: 
        raise ValueError("generation type not defined")
    
    formatted = format_alerts(alerts)

    try: 
        prompt = client.messages.create(
            model="claude-opus-4-8",
            max_tokens=tok,
            system=sys,
            messages=[{"role": "user", "content": formatted}]
        )
        return {"success": True, "results": prompt.content[0].text} 
    except APIError as error:
        return {"success": False, "error": str(error)}


 
