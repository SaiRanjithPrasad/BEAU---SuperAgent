import pytest
from unittest.mock import patch, Mock


def test_revenuecat_no_key_is_free():
    from beau.billing.revenuecat import is_entitled
    with patch("beau.billing.revenuecat.REVENUECAT_API_KEY", ""):
        assert is_entitled("user1", "beau_pro") is True


def test_revenuecat_active_entitlement():
    from beau.billing.revenuecat import is_entitled
    subscriber = {
        "subscriber": {
            "entitlements": {
                "entitlement_1": {
                    "id": "beau_pro",
                    "product_id": "beau_pro",
                    "is_active": True,
                }
            }
        }
    }
    with patch("beau.billing.revenuecat.REVENUECAT_API_KEY", "test_key"), \
         patch("beau.billing.revenuecat._get_subscriber", return_value=subscriber):
        assert is_entitled("user1", "beau_pro") is True


def test_revenuecat_inactive_entitlement():
    from beau.billing.revenuecat import is_entitled
    subscriber = {
        "subscriber": {
            "entitlements": {
                "entitlement_1": {
                    "id": "beau_pro",
                    "product_id": "beau_pro",
                    "is_active": False,
                }
            }
        }
    }
    with patch("beau.billing.revenuecat.REVENUECAT_API_KEY", "test_key"), \
         patch("beau.billing.revenuecat._get_subscriber", return_value=subscriber):
        assert is_entitled("user1", "beau_pro") is False


def test_revenuecat_no_entitlement():
    from beau.billing.revenuecat import is_entitled
    subscriber = {
        "subscriber": {"entitlements": {}}
    }
    with patch("beau.billing.revenuecat.REVENUECAT_API_KEY", "test_key"), \
         patch("beau.billing.revenuecat._get_subscriber", return_value=subscriber):
        assert is_entitled("user1", "beau_pro") is False


def test_revenuecat_api_403_is_false():
    from beau.billing.revenuecat import is_entitled
    with patch("beau.billing.revenuecat.REVENUECAT_API_KEY", "test_key"), \
         patch("beau.billing.revenuecat._get_subscriber", return_value=None):
        assert is_entitled("user1", "beau_pro") is False


def test_revenuecat_api_exception_is_false():
    from beau.billing.revenuecat import is_entitled
    with patch("beau.billing.revenuecat.REVENUECAT_API_KEY", "test_key"), \
         patch("beau.billing.revenuecat._get_subscriber", side_effect=Exception("network error")):
        assert is_entitled("user1", "beau_pro") is False


def test_revenuecat_api_error_404():
    from beau.billing.revenuecat import is_entitled, _get_subscriber
    with patch("beau.billing.revenuecat.REVENUECAT_API_KEY", "test_key"), \
         patch("beau.billing.revenuecat._get_subscriber", return_value=None):
        result = _get_subscriber("missing_user")
        assert result is None
        assert is_entitled("missing_user", "beau_pro") is False
