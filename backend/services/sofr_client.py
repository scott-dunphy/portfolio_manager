import time
from datetime import datetime, date
from json import JSONDecodeError
from typing import List, Dict, Optional

import requests
from requests import RequestException

CHATHAM_SOFR_URL = 'https://www.chathamfinancial.com/getrates/285116'
CACHE_TTL_SECONDS = 60 * 60  # 1 hour
REQUEST_HEADERS = {
    'Accept': 'application/json',
    'User-Agent': 'PortfolioManager/1.0 (+https://github.com/portfolio-manager)'
}

_cache: Dict[str, object] = {
    'timestamp': None,
    'curve_date': None,
    'rates': None,
}


def _refresh_cache() -> bool:
    try:
        response = requests.get(CHATHAM_SOFR_URL, timeout=10, headers=REQUEST_HEADERS)
        response.raise_for_status()
        payload = response.json()
        curve_date = datetime.fromisoformat(payload['CurveDate']).date()
        rates = []
        for point in payload.get('Rates', []):
            rate_date = datetime.fromisoformat(point['Date']).date()
            rates.append({'date': rate_date, 'rate': float(point['Rate'])})

        rates.sort(key=lambda item: item['date'])

        _cache['timestamp'] = time.time()
        _cache['curve_date'] = curve_date
        _cache['rates'] = rates
        return True
    except (RequestException, JSONDecodeError, KeyError, ValueError):
        # Keep whatever (if any) cached data we already had; caller will fall back.
        return False


def _ensure_cache():
    if not _cache['rates'] or not _cache['timestamp']:
        _refresh_cache()
        return
    if time.time() - _cache['timestamp'] > CACHE_TTL_SECONDS:
        _refresh_cache()


def get_forward_rate(target_date: date) -> Optional[float]:
    _ensure_cache()
    rates: List[Dict[str, object]] = _cache['rates'] or []
    if not rates:
        return None

    previous_rate = rates[0]['rate']
    for point in rates:
        if point['date'] > target_date:
            break
        previous_rate = point['rate']
    return previous_rate
