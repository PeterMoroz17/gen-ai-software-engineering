from agents.common import mask_account


def test_mask_account_masks_proportionally():
    assert mask_account("ACC-1001") == "****1001"


def test_mask_account_handles_empty_value():
    assert mask_account("") == "****"
    assert mask_account(None) == "****"


def test_mask_account_handles_short_value():
    assert mask_account("A1") == "**"
