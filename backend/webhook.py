import hmac
import hashlib
import subprocess
from fastapi import FastAPI, Request, HTTPException
import uvicorn

app = FastAPI()

SECRET = "0778dd0e38df943eb28a71aaea09fb2ce90e1184f1d35a4dadfae6863288a8b5"
DEPLOY_SCRIPT = "/home/ipuser/IndexPulse/deploy.sh"

@app.post("/webhook")
async def webhook(request: Request):
    signature = request.headers.get("X-Hub-Signature-256")
    if not signature:
        raise HTTPException(status_code=403, detail="No signature")

    body = await request.body()
    expected = "sha256=" + hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=403, detail="Invalid signature")

    subprocess.Popen(["/bin/bash", DEPLOY_SCRIPT])
    return {"status": "deploy triggered"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9000)
