def parse_budget(budget_str):
    if not budget_str:
        return 0.0

    cleaned = str(budget_str).replace("\u20b9", "").replace(",", "").strip()

    if cleaned == "":
        return 0.0

    try:
        return float(cleaned)
    except ValueError:
        return 0.0

def safe_div(numerator, denominator):
    if denominator in (0, None):
        return 0.0
    try:
        return numerator / denominator
    except Exception:
        return 0.0


def compute_ctr(clicks, impressions):
    return round(safe_div(clicks, impressions) * 100, 4)


def compute_cpc(spend, clicks):
    return round(safe_div(spend, clicks), 4)


def compute_conversion_rate(orders, clicks):
    return round(safe_div(orders, clicks) * 100, 4)


def compute_roas(sales, spend):
    return round(safe_div(sales, spend), 4)


def compute_acos(spend, sales):
    return round(safe_div(spend, sales) * 100, 4)