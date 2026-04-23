import pandas as pd
from utils import (
    parse_budget,
    safe_div,
    compute_ctr,
    compute_cpc,
    compute_conversion_rate,
    compute_roas,
    compute_acos
)
from openai import OpenAI
# client = OpenAI()


def compute_metrics(row):
    impressions = row["Impressions"]
    clicks = row["Clicks"]
    spend = row["Spend"]
    orders = row["Orders"]
    sales = row["Sales"]

    ctr = compute_ctr(clicks, impressions)
    cpc = compute_cpc(spend, clicks)
    conversion_rate = compute_conversion_rate(orders, clicks)
    roas = compute_roas(sales, spend)
    acos = compute_acos(spend, sales)

    return ctr, cpc, conversion_rate, roas, acos


def label_campaign(roas):
    if roas > 3:
        return "Scale"
    elif roas >= 1:
        return "Optimize"
    return "Pause"


def analyze_campaigns(file_path):
    df = pd.read_csv(file_path)

    results = []

    for _, row in df.iterrows():
        try:
            campaign = row["Campaigns"]

            budget = parse_budget(row["Budget"])
            impressions = int(row["Impressions"] or 0)
            clicks = int(row["Clicks"] or 0)
            spend = float(row["Spend"] or 0)
            orders = int(row["Orders"] or 0)
            sales = float(row["Sales"] or 0)

            ctr, cpc, conversion_rate, roas, acos = compute_metrics({
                "Impressions": impressions,
                "Clicks": clicks,
                "Spend": spend,
                "Orders": orders,
                "Sales": sales
            })

            label = label_campaign(roas)

            results.append({
                "campaign_name": campaign,
                "budget": budget,
                "impressions": impressions,
                "clicks": clicks,
                "spend": spend,
                "orders": orders,
                "sales": sales,
                "ctr": round(ctr, 2),
                "cpc": round(cpc, 2),
                "conversion_rate": round(conversion_rate, 2),
                "roas": round(roas, 2),
                "acos": round(acos, 2),
                "label": label
            })

        except Exception as e:
            print(f"Skipped row due to error: {e}")
            continue

    analyzed_df = pd.DataFrame(results)
    analyzed_df.to_csv("data/campaigns_analyzed.csv", index=False)

    return results, get_summary()

import pandas as pd
from utils import compute_roas, safe_div


def get_summary(file_path="data/campaigns_analyzed.csv"):
    df = pd.read_csv(file_path)

    if df.empty:
        return {}

    total_spend = df["spend"].sum()
    total_sales = df["sales"].sum()

    overall_roas = compute_roas(total_sales, total_spend)

    best_row = df.loc[df["roas"].idxmax()]
    worst_row = df.loc[df["roas"].idxmin()]

    label_counts = df["label"].value_counts().to_dict()

    # ensure all labels exist
    for label in ["Scale", "Optimize", "Pause"]:
        label_counts.setdefault(label, 0)

    pause_spend = df[df["label"] == "Pause"]["spend"].sum()
    wasted_spend_pct = safe_div(pause_spend, total_spend) * 100

    return {
        "total_spend": round(total_spend, 2),
        "total_sales": round(total_sales, 2),
        "overall_roas": round(overall_roas, 2),
        "best_campaign": {
            "name": best_row["campaign_name"],
            "roas": round(best_row["roas"], 2)
        },
        "worst_campaign": {
            "name": worst_row["campaign_name"],
            "roas": round(worst_row["roas"], 2)
        },
        "label_breakdown": label_counts,
        "wasted_spend_pct": round(wasted_spend_pct, 2)
    }


def get_insights(file_path="data/campaigns_analyzed.csv"):
    df = pd.read_csv(file_path)

    flagged = []

    total_wasted_spend = 0

    for _, row in df.iterrows():
        campaign = row["campaign_name"]
        spend = row["spend"]
        orders = row["orders"]
        ctr = row["ctr"]
        acos = row["acos"]
        roas = row["roas"]
        budget = row["budget"]

        # 1. High ACOS
        if acos > 80:
            flagged.append({
                "campaign_name": campaign,
                "issue": "High ACOS (inefficient spend)",
                "metric_value": f"ACOS: {round(acos,2)}%",
                "recommendation": "Reduce Budget",
                "reason": "You are spending heavily relative to revenue. Lower bids or refine targeting to improve efficiency."
            })

        # 2. Low CTR
        if ctr < 0.3:
            flagged.append({
                "campaign_name": campaign,
                "issue": "Low CTR (poor engagement)",
                "metric_value": f"CTR: {round(ctr,2)}%",
                "recommendation": "Review Creative",
                "reason": "Ad impressions are not converting into clicks. Improve creatives, titles, or audience targeting."
            })

        # 3. Spend but no orders (critical)
        if spend > 0 and orders == 0:
            total_wasted_spend += spend

            flagged.append({
                "campaign_name": campaign,
                "issue": "Spend with zero conversions",
                "metric_value": f"Spend: ₹{spend}, Orders: 0",
                "recommendation": "Pause",
                "reason": "This campaign is burning budget without generating any conversions. Pausing immediately prevents further loss."
            })

        # 4. ROAS = 0 but budget active
        if roas == 0 and budget > 0:
            flagged.append({
                "campaign_name": campaign,
                "issue": "Zero ROAS with active budget",
                "metric_value": f"ROAS: 0, Budget: ₹{budget}",
                "recommendation": "Reallocate Budget",
                "reason": "Budget is allocated to a non-performing campaign. Shift budget to high-ROAS campaigns."
            })

    return {
        "flagged_campaigns": flagged,
        "total_flagged": len(flagged),
        "summary": f"{len(flagged)} issues detected. Estimated wasted spend: ₹{round(total_wasted_spend,2)}"
    }

def build_ai_prompt(df):
    total_campaigns = len(df)

    avg_ctr = df["ctr"].mean()
    avg_roas = df["roas"].mean()
    avg_acos = df["acos"].mean()
    avg_conversion = df["conversion_rate"].mean()

    scale_count = (df["label"] == "Scale").sum()
    optimize_count = (df["label"] == "Optimize").sum()
    pause_count = (df["label"] == "Pause").sum()

    top_campaigns = df.nlargest(3, "roas")[["campaign_name", "roas"]].to_dict("records")
    worst_campaigns = df.nsmallest(3, "roas")[["campaign_name", "roas"]].to_dict("records")

    prompt = f"""
You are an Amazon Ads performance expert.

Analyze the following account-level performance:

CAMPAIGN OVERVIEW:
- Total campaigns: {total_campaigns}
- Scale: {scale_count}, Optimize: {optimize_count}, Pause: {pause_count}

AVERAGE METRICS:
- CTR: {avg_ctr:.2f}%
- ROAS: {avg_roas:.2f}
- ACOS: {avg_acos:.2f}%
- Conversion Rate: {avg_conversion:.2f}%

TOP PERFORMING CAMPAIGNS:
{top_campaigns}

WORST PERFORMING CAMPAIGNS:
{worst_campaigns}

TASK:
1. Explain how each metric is performing (CTR, ROAS, ACOS, Conversion Rate)
2. Identify the biggest problems in this account
3. Suggest top 3 actionable recommendations ranked by impact
4. Highlight wasted budget risks
5. Keep response structured and concise
"""

    return prompt


def call_ai(prompt):
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content

def ask_ai(file_path="data/campaigns_analyzed.csv"):
    df = pd.read_csv(file_path)

    if df.empty:
        return {"error": "No data available"}

    prompt = build_ai_prompt(df)

    ai_response = call_ai(prompt)

    return {
        "prompt": prompt,
        "ai_response": ai_response
    }