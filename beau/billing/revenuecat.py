import logging

import httpx

from beau.core.config import REVENUECAT_API_KEY, REVENUECAT_ENTITLEMENT

logger = logging.getLogger(__name__)

_REVENUECAT_BASE = "https://api.revenuecat.com/v1"


def is_entitled(user_id: str, feature: str) -> bool:
    """Check if user has entitlement for feature via RevenueCat."""
    if not REVENUECAT_API_KEY:
        return True  # free tier when no key
    try:
        subscriber = _get_subscriber(user_id)
        if subscriber is None:
            logger.warning("RevenueCat: subscriber %s not found", user_id)
            return False
        entitlements = subscriber.get("subscriber", {}).get("entitlements", {})
        for entitlement in entitlements.values():
            if entitlement.get("product_id") == feature or entitlement.get("id") == feature:
                if entitlement.get("is_active"):
                    return True
        return False
    except Exception as e:
        logger.warning("RevenueCat check failed for %s: %s", user_id, e)
        return False


def _get_subscriber(user_id: str) -> dict | None:
    """Fetch subscriber from RevenueCat API."""
    url = f"{_REVENUECAT_BASE}/subscribers/{user_id}"
    headers = {
        "Authorization": f"Bearer {REVENUECAT_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(url, headers=headers)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 403:
                logger.warning("RevenueCat: invalid API key (403)")
            elif resp.status_code == 404:
                logger.warning("RevenueCat: subscriber %s not found (404)", user_id)
            else:
                logger.warning("RevenueCat: unexpected %s for %s", resp.status_code, user_id)
    except Exception as e:
        logger.warning("RevenueCat request failed: %s", e)
    return None
