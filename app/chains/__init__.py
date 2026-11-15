"""app.chains — LCEL pipelines for query classification and RAG answering.

Modules:
- classify.py    Classify user query as KNOWLEDGE_QUERY or ACTION_REQUEST
- answer.py      Full RAG LCEL chain: retrieve → format → prompt → LLM → validate
"""
