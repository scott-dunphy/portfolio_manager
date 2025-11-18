import threading
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

import requests

CHATHAM_URL = "https://www.chathamfinancial.com/getrates/278177"
CACHE_TTL_SECONDS = 3600  # 1 hour
_cache_lock = threading.Lock()
_forward_curve_cache = {
    "timestamp": None,
    "rates": []  # list of (date, rate)
}


def _fetch_forward_curve() -> List[tuple]:
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    }
    try:
        response = requests.get(CHATHAM_URL, headers=headers, timeout=10)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException:
        return []
    rates = []
    for entry in payload.get("Rates", []):
        date_str = entry.get("Date")
        rate_value = entry.get("Rate")
        if not date_str or rate_value is None:
            continue
        try:
            entry_date = datetime.fromisoformat(date_str[:10]).date()
            rates.append((entry_date, float(rate_value)))
        except ValueError:
            continue
    rates.sort(key=lambda item: item[0])
    return rates


def _get_cached_forward_curve() -> List[tuple]:
    with _cache_lock:
        timestamp = _forward_curve_cache["timestamp"]
        if timestamp and (datetime.utcnow() - timestamp) < timedelta(seconds=CACHE_TTL_SECONDS):
            return _forward_curve_cache["rates"]
        rates = _fetch_forward_curve()
        _forward_curve_cache["rates"] = rates
        _forward_curve_cache["timestamp"] = datetime.utcnow()
        return rates


def get_forward_treasury_rate(target_date: date) -> Optional[float]:
    rates = _get_cached_forward_curve()
    if not rates:
        return None
    for rate_date, rate_value in rates:
        if rate_date >= target_date:
            return rate_value
    return rates[-1][1]
