from serpapi import GoogleSearch
import os
import json
from dotenv import load_dotenv

load_dotenv()

def build_query(
    person: str = None,
    organization: str = None,
    keywords: list = None,
    include_sites: list = None,
    exclude_sites: list = None,
) -> str:
    parts = []

    if person:
        parts.append(f'"{person}"')
    if organization:
        parts.append(f'"{organization}"')
    if keywords:
        for kw in keywords:
            parts.append(f'"{kw}"')
    if include_sites:
        site_clause = " OR ".join(f"site:{s}" for s in include_sites)
        parts.append(f"({site_clause})")
    if exclude_sites:
        for s in exclude_sites:
            parts.append(f"-site:{s}")

    return " ".join(parts)


def run_dork(
    person: str = None,
    organization: str = None,
    keywords: list = None,
    include_sites: list = None,
    exclude_sites: list = None,
    hours: int = 24,
    num_results: int = 10,
):
    query = build_query(
        person=person,
        organization=organization,
        keywords=keywords,
        include_sites=include_sites,
        exclude_sites=exclude_sites,
    )

    if not query.strip():
        return {"success": False, "error": "At least one search parameter is required."}

    search = GoogleSearch({
        "engine": "google",
        "q": query,
        "google_domain": "google.com",
        "hl": "en",
        "gl": "us",
        "tbs": "qdr:d",
        "num": num_results,
        "api_key": os.getenv("SERPAPI_KEY")
    })

    data = search.get_dict()
    organic = data.get("organic_results", [])

    results = []
    for item in organic:
        results.append({
            "title": item.get("title"),
            "link": item.get("link"),
            "snippet": item.get("snippet"),
            "source": item.get("source"),
            "date": item.get("date"),
        })

    return {"success": True, "query": query, "results": results}


if __name__ == "__main__":
    output = run_dork(keywords=["ransomware", "data breach"])
    print(json.dumps(output, indent=2))