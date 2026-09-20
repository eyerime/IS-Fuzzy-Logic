import time
from collections import deque

import uvicorn
from fastapi import FastAPI, HTTPException
from fuzzy_engine import ThreatFuzzyEngine
from pydantic import BaseModel

app = FastAPI()
engine = ThreatFuzzyEngine()

# Deque to store request data as tuples: (timestamp, status)
# This allows us to track traffic over a rolling 10-second window
traffic_log = deque()


class TrafficPayload(BaseModel):
    status: str


@app.post("/traffic")
async def process_traffic(payload: TrafficPayload):
    current_time = time.time()

    # Log the incoming request
    traffic_log.append((current_time, payload.status))

    # Remove requests older than 10 seconds
    while traffic_log and traffic_log[0][0] < current_time - 10:
        traffic_log.popleft()

    # Calculate live metrics
    total_requests = len(traffic_log)
    req_per_sec = total_requests / 10.0  # Average over the 10-second window

    error_count = sum(1 for req in traffic_log if req[1] == "error")
    err_rate = (error_count / total_requests * 100) if total_requests > 0 else 0

    # Cap request rate at 100 to match the fuzzy engine's Universe of Discourse
    capped_req_rate = min(req_per_sec, 100)

    # Process through the Mamdani engine
    threat_score = engine.compute_threat(capped_req_rate, err_rate)

    # Enforce network thresholds
    if threat_score >= 75:
        # Severe Threat: Drop the connection
        raise HTTPException(
            status_code=403, detail=f"Blocked. Threat Level: {threat_score:.1f}%"
        )
    elif threat_score >= 41:
        # Suspicious: Would trigger CAPTCHA in production
        return {"status": "challenged", "threat_level": round(threat_score, 1)}
    else:
        # Safe: Process normally
        return {"status": "allowed", "threat_level": round(threat_score, 1)}


if __name__ == "__main__":
    # Runs the server locally on port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
