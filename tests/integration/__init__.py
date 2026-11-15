"""tests.integration — Integration tests for EKIP.

These tests run with real components (real ChromaDB, real API calls where needed).

IMPORTANT:
    - These tests REQUIRE .env to be set up with a valid GOOGLE_API_KEY
    - They are slower than unit tests (may take 5-30 seconds each)
    - Run separately from unit tests: pytest tests/integration/
    - Use sparingly — prefer unit tests with mocks for most coverage
"""
