"""tests.unit — Fast isolated unit tests.

Rules for unit tests:
- NEVER call real LLM APIs (mock them with unittest.mock)
- NEVER write to or read from real ChromaDB (use in-memory or mocks)
- NEVER require .env to be set up
- Tests must run in under 1 second each
- Use fixtures in conftest.py for shared test data
"""
