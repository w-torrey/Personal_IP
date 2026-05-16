import serpapi
from serpapi import GoogleSearch
# import os is for 
import os
from dotenv import load_dotenv
# doing json output for now, we can change later
import json




# just basically load the .env file variables into this python script
load_dotenv()

results = GoogleSearch({
  "engine": "google",
  # main input
  #"q": '"Mark Thompson" AND "Wentworth"',
  "q": '"Larry Fink" AND "BlackRock"',

  # defines google domain to use
  "google_domain": "google.com",

  "hl": "en",
  #defines the country to use for the Google search
  "gl": "us",

  # this is the date format, qdr:d is past 24 hrs, and the hourly is &tbs=qdr:h, i think we should stick with daily for now
  # something to take into account: Sort by Date: &tbs=sbd:1 (Forces results to be sorted by newest firs
  "tbs": "qdr:d",

  # API key loaded
  "api_key": os.getenv("SERPAPI_KEY")
}).get_dict()

print(json.dumps(results, indent=2))
