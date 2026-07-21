from serpapi import GoogleSearch # serp api client from google search
import os
import json
from dotenv import load_dotenv 

load_dotenv() # able to read .env

def build_query(
        # this function basically creates phrases that are all wrapped in quotes to send to query
    keywords: list = None,
    or_keywords: list =None,
    # testing out excluding the keywords (-"word")
    exclude_keywords: list =None,
    include_sites: list = None,
    exclude_sites: list = None,
    # returns s ingle google query ("jackson" "morrow" "something")
) -> str:
    
    parts = [] 
    # ^^ for build query
    # takes in each query before joining

    if keywords:
        for kw in keywords:
            parts.append(f'"{kw}"') # bread and butter of SERP API allowing the request
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
    

    return " ".join(parts) # join everythign into spaces

# main dork function interacting with serpAPI
def run_dork(
        # build it up
    keywords: list = None,
    or_keywords: list = None,
    exclude_keywords: list = None,
    include_sites: list = None,
    exclude_sites: list = None,
    hours: int = 24,
    # num_results: int = 10,  (Commenting this out for now so that we can just ge a lot of output for now... before hand this was just returning 10 results when there could have been 50+ returnable possibly)
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
    search = GoogleSearch({
        "engine": "google", # googles engine
        "q": query, # type queryt
        "google_domain": "google.com",
        "hl": "en", # english
        "gl": "us",
        "tbs": "qdr:d", # set for last 24 hours ( we should see if we can change this to a certain amount of hours and check in with the scheduler )
        # "num": num_results, # num results that can be defined later but is set as 10 as of now 
        # commenting out ^^^
        "api_key": os.getenv("SERPAPI_KEY")  # grab api key
    })

    data = search.get_dict() # gets results back in dictinoary
    organic = data.get("organic_results", []) # make it usable for db 


# extract only the necessary fields 
# just aprase out title link snippet source date
    results = []
    for item in organic:
        results.append({
            "title": item.get("title"),
            "link": item.get("link"),
            "snippet": item.get("snippet"),
            "source": item.get("source"),
            "date": item.get("date"),
        })
# checl
    return {"success": True, "query": query, "results": results}

# test with standalone file
if __name__ == "__main__":
    output = run_dork(keywords=["ransomware", "data breach"])

    print(json.dumps(output, indent=2)) # huh