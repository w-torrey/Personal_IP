import serpapi
from serpapi import GoogleSearch
# import os is for 
import os
from dotenv import load_dotenv
# doing json output for now, we can change later
import json




# just basically load the .env file variables into this python script
load_dotenv()

def run_dork(person, organization, hours=24, num_results=10):
    search = GoogleSearch({
        "engine": "google",
        "q": f'"{person}" AND "{organization}"',
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

    return {"success": True, "results": results}


# Run directly for testing
if __name__ == "__main__":
    output = run_dork("Kathryn Horgan", "State Street")
    print(json.dumps(output, indent=2))
