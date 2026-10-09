from serpapi import GoogleSearch  # serp api client from google search
import os
import json
import logging
from dotenv import load_dotenv

load_dotenv()  # able to read .env

logger = logging.getLogger(__name__)


def build_query(
    # this function basically creates phrases that are all wrapped in quotes to send to query
    keywords: list = None,
    or_keywords: list = None,
    # testing out excluding the keywords (-"word")
    exclude_keywords: list = None,
    include_sites: list = None,
    exclude_sites: list = None,
    # returns s ingle google query ("jackson" "morrow" "something")
) -> str:

    parts = []
    # ^^ for build query
    # takes in each query before joining

    if keywords:
        for kw in keywords:
            parts.append(f'"{kw}"')  # bread and butter of SERP API allowing the request
            # through each keyword by itself from parts and rap them in quotes allowing for dork

    if exclude_keywords:
        for kw in exclude_keywords:
            parts.append(f'-"{kw}"')
            # wrap in quoutes but insert "-" to allow it to be excluded

    # or keywords
    if or_keywords:
        or_clause = " OR ".join(f'"{kw}"' for kw in or_keywords)
        parts.append(f"({or_clause})")

    if include_sites:
        site_clause = " OR ".join(f"site:{s}" for s in include_sites)
        parts.append(f"({site_clause})")
        # include sites using OR operator to split up allowing to come from multiple of those sites
    if exclude_sites:
        for s in exclude_sites:
            parts.append(f"-site:{s}")
            # keyword of those sites just to be excluded

    return " ".join(parts)  # join everythign into spaces


# Google's time filter: qdr:d is the past day, qdr:w the past week. These are the
# documented forms; hour counts like qdr:h24 returned nothing through SerpAPI
def time_filter(hours: int) -> str:
    if hours <= 1:
        return "qdr:h"
    if hours <= 24:
        return "qdr:d"
    if hours <= 24 * 7:
        return "qdr:w"
    return "qdr:m"


# main dork function interacting with serpAPI
def run_dork(
    # build it up
    keywords: list = None,
    or_keywords: list = None,
    exclude_keywords: list = None,
    include_sites: list = None,
    exclude_sites: list = None,
    hours: int = 24,
):
    # use function above
    query = build_query(
        keywords=keywords,
        or_keywords=or_keywords,
        exclude_keywords=exclude_keywords,
        include_sites=include_sites,
        exclude_sites=exclude_sites,
    )

    # if not nothing gets passed through through an error to terminal
    if not query.strip():
        return {"success": False, "error": "At least one search parameter is required."}

    # configure SerpAPI call
    search = GoogleSearch(
        {
            "engine": "google",  # googles engine
            "q": query,  # type queryt
            "google_domain": "google.com",
            "hl": "en",  # english
            "gl": "us",
            "tbs": time_filter(hours),
            "api_key": os.getenv("SERPAPI_KEY"),  # grab api key
        }
    )

    data = search.get_dict()  # gets results back in dictinoary

    # SerpAPI reports failures (bad key, used-up quota) in an "error" field,
    # but it also uses that field for a plain empty search, which isn't a failure
    error = data.get("error")
    if error and "hasn't returned any results" not in error:
        return {"success": False, "query": query, "error": f"SerpAPI: {error}"}
    if error:
        logger.info(f"SerpAPI returned no results (tbs={time_filter(hours)}): {error}")

    organic = data.get("organic_results", [])  # make it usable for db

    # extract only the necessary fields
    # just aprase out title link snippet source date
    results = []
    for item in organic:
        results.append(
            {
                "title": item.get("title"),
                "link": item.get("link"),
                "snippet": item.get("snippet"),
                "source": item.get("source"),
                "date": item.get("date"),
            }
        )
    # checl
    return {"success": True, "query": query, "results": results}


# test with standalone file
if __name__ == "__main__":
    output = run_dork(keywords=["ransomware", "data breach"])

    print(json.dumps(output, indent=2))  # huh
