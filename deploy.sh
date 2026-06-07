#!/bin/bash

echo "=== IndexPulse Deploy $(date) ===" >> /home/ipuser/IndexPulse/deploy.log

cd /home/ipuser/IndexPulse
git pull origin main >> /home/ipuser/IndexPulse/deploy.log 2>&1

cd /home/ipuser/IndexPulse/frontend
npm run build >> /home/ipuser/IndexPulse/deploy.log 2>&1

pkill -f "uvicorn main:app" >> /home/ipuser/IndexPulse/deploy.log 2>&1
sleep 2

cd /home/ipuser/IndexPulse/backend
source /home/ipuser/IndexPulse/venv/bin/activate
nohup /home/ipuser/IndexPulse/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 >> /home/ipuser/IndexPulse/deploy.log 2>&1 &

echo "=== Deploy complete ===" >> /home/ipuser/IndexPulse/deploy.log
