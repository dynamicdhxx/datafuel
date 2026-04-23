from fastapi import FastAPI
from service import get_insights, ask_ai, get_summary, analyze_campaigns

app = FastAPI()

@app.get("/analyze")
def analyze():
    results, summary = analyze_campaigns("data/campaigns.csv")

    return {
        "campaigns": results,
        "summary": summary
    }

@app.get("/summary")
def summary():
    return get_summary()

@app.get("/insights")
def insights():
    return get_insights()

@app.get("/ask-ai")
def ask_ai_endpoint():
    return ask_ai()