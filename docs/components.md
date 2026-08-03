# Component Overview

## Backend



### auth.py

Authentication utilities including bcrypt password hashing and JWT creation and verification.


### database.py

This is our PostgreSQL data layer. Contains all SQL methods for watchlists, results, users, digests, and dossiers. This layer is isolated from the client side, strictly interacts with main and scheduler.


### dork_engine.py

This is our SerpAPI integration layer. Builds queries into Google dork strings for watchlists and executes a handoff and return from SerpAPI which is then normalized. 


### main.py

FastAPI app entry point. Defines all HTTP endpoints and enforces JWT auth on certain protected routes. Configures CORS and serves the React frontend as static files. The general purpose of this program is to control interactions between clients and our data layer.


### scheduler.py

This is our automated sweep layer, running at 8pm daily using APScheduler, also houses an on-demand run now. For each watchlist: a dork is run, results are deduplicated and saved, and then both a digest and dossier are generated.


### summary_engine.py

This is our Anthropic API integration layer. Formats alerts, builds a return schema (digests only) to prevent hallucinated alert IDs from the AI model, and executes a handoff and return from Anthropic API for summary generation.


## Frontend




NOTE: The frontend was scaffolded using Vite, all raw application code lives in App.jsx, the other files in /frontend are Vite boilerplate.


### App.jsx

Single file React dashboard style frontend. Renders category board, alert cards, watchlist management menu, AI summary, and login gateway. 


## Deployment



### deploy.yml

Github actions file to enable CI/CD, pulls new pushes from main and rebuilds the frontend and redeploys the FastAPI service.


## Config


### reqs.txt

A list of all the python dependencies required for this project to work

### frontend/package.json

Required JS dependencies and scripts for the frontend

### backend/.env.example

Required environment variable relevant to backend functionality

