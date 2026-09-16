import logging

logger = logging.getLogger(__name__)

def is_entitled(user_id: str, feature: str) -> bool:
    from beau.core.config import REVENUECAT_API_KEY
    if not REVENUECAT_API_KEY:
        return True  # free tier when no key
    # TODO: call RevenueCat MCP https://api.revenuecat.com/v1/subscribers/<user_id>
    logger.warning("BILLING_UNAVAILABLE: RevenueCat check not implemented, denying entitlement")
    return False
