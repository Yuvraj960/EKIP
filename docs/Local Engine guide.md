# Dual-Engine Architecture & Local Ollama Setup Guide

## 1. Dual-Engine Architecture

EKIP decouples the text generation engine from the vector embedding engine. Both can be independently configured as either **HOSTED** (Google Gemini) or **LOCAL** (Ollama / Local OpenAI endpoint).

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          EKIP Engine Dispatcher                                 │
│                                                                                 │
│   ┌───────────────────────────────┐           ┌─────────────────────────────┐   │
│   │       INFERENCE_ENGINE        │           │      EMBEDDING_ENGINE       │   │
│   ├───────────────┬───────────────┤           ├─────────────┬───────────────┤   │
│   │    HOSTED     │     LOCAL     │           │   HOSTED    │     LOCAL     │   │
│   │ (Gemini Flash)│ (Ollama LLM)  │           │(Gemini Emb) │(Ollama Embed) │   │
│   └───────────────┴───────────────┘           └─────────────┴───────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Low-VRAM Optimization (4GB GPU Friendly)

Running local AI models often causes out-of-memory errors on modest laptops or workstations. EKIP is tested and optimized for **4GB VRAM hardware**:

| Component | Recommended Model | Approximate VRAM | Why It Fits |
|---|---|---|---|
| **Embeddings** | `nomic-embed-text` | **~274 MB** | Highly accurate 768-dim embeddings with virtually zero VRAM footprint. |
| **Inference** | `llama3.2:3b` | **~2.0 GB** | State-of-the-art 3B instruction-tuned model fitting comfortably in 4GB VRAM. |

---

## 3. Configuration Profiles

### Profile A: 100% Local & Offline (Zero Cloud Dependency)
Ideal for private codebases, proprietary internal documents, and offline development.

1. **Install and Start Ollama**:
   Download Ollama from [ollama.com](https://ollama.com/) and run:
   ```bash
   ollama pull nomic-embed-text
   ollama pull llama3.2:3b
   ```

2. **Configure `.env`**:
   ```ini
   INFERENCE_ENGINE=LOCAL
   INFERENCE_MODEL=llama3.2:3b

   EMBEDDING_ENGINE=LOCAL
   EMBEDDING_MODEL=nomic-embed-text

   OLLAMA_OR_ANY_LOCAL_ENDPOINT=http://localhost:11434
   ```

3. **Launch the Platform**:
   ```bash
   ekip start
   ```

---

### Profile B: Hybrid Setup (Local Embeddings + Hosted Gemini Chat)
Best for developers who want zero API costs for heavy document indexing, while leveraging Gemini's cloud speed for chat inference:

```ini
# Chat runs in Google Cloud
INFERENCE_ENGINE=HOSTED
INFERENCE_MODEL=gemini-3.1-flash-lite
GOOGLE_API_KEY=your_gemini_api_key_here

# Vector embeddings run 100% locally on your machine
EMBEDDING_ENGINE=LOCAL
EMBEDDING_MODEL=nomic-embed-text
OLLAMA_OR_ANY_LOCAL_ENDPOINT=http://localhost:11434
```

---

### Profile C: Hosted Cloud Default (Google Gemini)
Zero local installation required; works immediately with an API key:

```ini
INFERENCE_ENGINE=HOSTED
INFERENCE_MODEL=gemini-3.1-flash-lite

EMBEDDING_ENGINE=HOSTED
EMBEDDING_MODEL=models/gemini-embedding-001

GOOGLE_API_KEY=your_gemini_api_key_here
```

---

## 4. Verification

To verify that your selected engine profile is detected properly by the system:

```bash
uv run python -c "
from app.core.config import settings
print(f'Inference Engine: {settings.inference_engine.value} ({settings.inference_model})')
print(f'Embedding Engine: {settings.embedding_engine.value} ({settings.embedding_model})')
"
```
