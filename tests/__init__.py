"""tests — EKIP test suite.

Structure:
    unit/         Fast, isolated tests. Mock all external calls (LLM, ChromaDB).
    integration/  Tests with real components. Use sparingly, need .env setup.

Run all tests:
    pytest

Run only unit tests (fast, no .env needed):
    pytest tests/unit/

Run with coverage:
    pytest --cov=app tests/unit/
"""
