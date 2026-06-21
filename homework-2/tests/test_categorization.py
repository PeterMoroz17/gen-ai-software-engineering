import pytest

from src.classifier import classify
from src.models import Category, Priority


class TestCategorization:
    def test_account_access_login_password_keywords(self):
        r = classify(
            "Cannot login to account",
            "I forgot my password and the 2fa authentication code is not working at all.",
        )
        assert r.category == Category.account_access

    def test_technical_issue_production_down_urgent(self):
        r = classify(
            "Production down critical outage",
            "The entire platform has crashed with 500 errors. Production is down and data loss is occurring.",
        )
        assert r.category == Category.technical_issue
        assert r.priority == Priority.urgent

    def test_billing_question_invoice_refund_medium(self):
        r = classify(
            "Refund for overcharge on invoice",
            "I was charged twice for my subscription and need a full refund of the billing fee.",
        )
        assert r.category == Category.billing_question
        assert r.priority == Priority.medium

    def test_feature_request_suggestion_low_priority(self):
        r = classify(
            "Feature suggestion: add dark mode",
            "It would be nice to have a dark theme option available in the application settings.",
        )
        assert r.category == Category.feature_request
        assert r.priority == Priority.low

    def test_bug_report_steps_to_reproduce(self):
        r = classify(
            "Bug: application crash when clicking save",
            "Steps to reproduce: open a document, make a change, click save. App crashes immediately.",
        )
        assert r.category == Category.bug_report
        assert r.priority == Priority.medium

    def test_no_matching_keywords_returns_other(self):
        r = classify(
            "Hello there friend",
            "This is completely unrelated text with absolutely no specific support topic at all.",
        )
        assert r.category == Category.other
        assert r.priority == Priority.medium

    def test_priority_high_from_blocking_asap_keywords(self):
        r = classify(
            "Blocking issue needs fix",
            "This is very important and is blocking our entire development team. Need fix asap.",
        )
        assert r.priority == Priority.high

    def test_priority_low_from_cosmetic_minor_keywords(self):
        r = classify(
            "Minor cosmetic issue with button",
            "The button border color is slightly off. Not urgent at all, just a minor visual thing.",
        )
        assert r.priority == Priority.low

    def test_medium_priority_is_default_when_no_keywords_match(self):
        r = classify("hello there", "this is completely unrelated text with no priority signals")
        assert r.priority == Priority.medium

    def test_confidence_score_is_float_between_0_and_1(self):
        r = classify(
            "Login broken password reset",
            "I cannot access my account and need help with the password and credentials reset.",
        )
        assert isinstance(r.confidence, float)
        assert 0.0 <= r.confidence <= 1.0

    def test_keywords_found_non_empty_when_category_matched(self):
        r = classify(
            "Invoice billing question refund",
            "I need a refund for the invoice charge on my monthly subscription payment.",
        )
        assert r.category != Category.other
        assert isinstance(r.keywords_found, list)
        assert len(r.keywords_found) > 0
