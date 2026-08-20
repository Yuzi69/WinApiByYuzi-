from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import httpx
import random
from typing import Optional

app = FastAPI(title="AYANO KOJI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

BIG = [5, 6, 7, 8, 9]
SMALL = [0, 1, 2, 3, 4]

WIN_EMOJI  = ["😎","🔥","💚","✅","🟢","🏆","⚡","💥","👑","🚀"]
LOSS_EMOJI = ["😢","❌","🔴","💔","😞","🥲","😵","🚫","😬","😓"]

WINGO_URL = "https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json"


def get_size(number: int) -> str:
    return "BIG" if number >= 5 else "SMALL"


async def fetch_wingo_history() -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(WINGO_URL)
        resp.raise_for_status()
        return resp.json()


@app.get("/")
async def root():
    return {
        "api": "AYANO KOJI→",
        "version": "1.0.0",
        "endpoints": {
            "predict": "/predict",
            "history": "/history?limit=10",
            "result":  "/result"
        }
    }


@app.get("/predict")
async def predict():
    """
    Current period prediction:
    - Fetches last 3 results from WinGo API
    - Momentum logic: if 2/3 recent are BIG → predict SMALL (contrarian)
    - Returns predicted size + a random number from opposite pool
    """
    data = await fetch_wingo_history()
    records = data["data"]["list"]

    last        = records[0]
    current_period = int(last["issueNumber"]) + 1

    # Trend from last 3 results
    trend = [get_size(int(r["number"])) for r in records[:3]]
    big_count   = trend.count("BIG")
    small_count = trend.count("SMALL")

    # Contrarian momentum strategy (same as HTML logic)
    if big_count >= 2:
        prediction = "BIG"
    else:
        prediction = "SMALL"

    # Predicted number from OPPOSITE pool
    opposite_pool = SMALL if prediction == "BIG" else BIG
    predicted_number = random.choice(opposite_pool)

    return {
        "period":           str(current_period),
        "prediction":       prediction,
        "predicted_number": predicted_number,
        "trend":            trend,
        "big_count":        big_count,
        "small_count":      small_count,
        "last_result": {
            "period": last["issueNumber"],
            "number": int(last["number"]),
            "size":   get_size(int(last["number"]))
        }
    }


@app.get("/result")
async def result():
    """
    Latest completed period result with win/loss check vs prediction logic.
    Compare last period prediction against actual result.
    """
    data = await fetch_wingo_history()
    records = data["data"]["list"]

    # Last 2 records: records[0] = just finished, records[1] = before that
    last      = records[0]
    prev3     = records[1:4]  # 3 records before last (these were the "trend" inputs)

    # Reconstruct what prediction WOULD have been for last period
    trend = [get_size(int(r["number"])) for r in prev3]
    big_count = trend.count("BIG")
    prediction = "BIG" if big_count >= 2 else "SMALL"

    # Actual result
    actual_number = int(last["number"])
    actual_size   = get_size(actual_number)

    # Win / Loss check
    won = (actual_size == prediction)
    if won:
        status = "WIN " + random.choice(WIN_EMOJI)
        outcome = "WIN"
    else:
        status = "LOSS " + random.choice(LOSS_EMOJI)
        outcome = "LOSS"

    return {
        "period":         last["issueNumber"],
        "prediction":     prediction,
        "actual_number":  actual_number,
        "actual_size":    actual_size,
        "outcome":        outcome,
        "status_label":   status,
        "trend_used":     trend
    }


@app.get("/history")
async def history(limit: int = Query(default=10, ge=1, le=50)):
    """
    Raw WinGo history with size labels.
    limit: 1-50 records (default 10)
    """
    data = await fetch_wingo_history()
    records = data["data"]["list"][:limit]

    results = []
    for r in records:
        num  = int(r["number"])
        size = get_size(num)
        results.append({
            "period": r["issueNumber"],
            "number": num,
            "size":   size,
            "color":  r.get("colour", "")
        })

    return {
        "count":   len(results),
        "records": results
    }
