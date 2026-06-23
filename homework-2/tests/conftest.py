import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.storage import store


@pytest.fixture(autouse=True)
def fresh_store():
    store.clear()
    yield
    store.clear()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def ticket_payload():
    return {
        "customer_id": "123",
        "customer_email": "john@example.com",
        "customer_name": "John",
        "subject": "Login issue",
        "description": "Cannot login to my account anymore",
    }


@pytest.fixture
def sample_payload():
    return {
        "customer_id": "cust-001",
        "customer_email": "alice@example.com",
        "customer_name": "Alice Smith",
        "subject": "Cannot access my account",
        "description": "I have been unable to log into my account for the past two days. Please help.",
        "metadata": {"source": "web_form"},
    }
