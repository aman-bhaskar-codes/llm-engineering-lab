# Structured Extraction Intelligence Engine

A production-grade, multi-model AI system that converts unstructured text and documents into rigorously structured JSON data — with **real-time token streaming**, **automatic model fallback**, and a **resilient fail-open architecture**.

Built with **FastAPI**, **React (Next.js)**, **Zustand**, **PostgreSQL**, **Redis**, and optionally **Neo4j**.

## ⭐ Key Features

| Feature | Description |
|---|---|
| **Real-Time Streaming** | Token-by-token SSE streaming via Redis pub/sub buffer — zero data loss even on late connections |
| **Multi-Model Inference** | Local-first (Ollama: `qwen2.5:3b`, `phi`) with automatic cloud fallback (Gemini) |
| **Three Extraction Modes** | `Simple` (fast), `Advanced` (multi-step for noisy data), `Reasoning` (chain-of-thought with think logs) |
| **Async Job Processing** | Background workers via `arq` + Redis for non-blocking, scalable extraction |
| **Semantic Memory** | PostgreSQL persistence + optional Neo4j graph memory for entity relationships |
| **Fail-Open Design** | Neo4j down? Redis down? The system keeps working — every external dependency is optional |
| **JWT Authentication** | Secure user sessions with access/refresh token rotation |
| **Rate Limiting** | Redis-backed rate limiting to protect extraction endpoints |

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Frontend (Next.js / React / Zustand)                        │
│  ┌──────────┐ ┌──────────┐ ┌────────────┐ ┌──────────────┐  │
│  │ ChatArea │ │ Composer │ │ OutputTabs │ │  Settings    │  │
│  └────┬─────┘ └────┬─────┘ └──────┬─────┘ └──────────────┘  │
│       │ SSE Stream  │ POST         │                          │
└───────┼─────────────┼──────────────┼──────────────────────────┘
        │             │              │
┌───────┼─────────────┼──────────────┼──────────────────────────┐
│  FastAPI Gateway     │              │                          │
│  ┌───────────────────┴──────────────┘                    │    │
│  │  POST /extract → enqueue_job() → returns job_id       │    │
│  │  GET  /extract/{id}/stream → SSE (polls Redis buffer) │    │
│  └───────────────────────────────────────────────────────┘    │
│                          │                                    │
│  ┌───────────────────────┴────────────────────────────────┐  │
│  │  arq Worker                                             │  │
│  │  ┌──────────┐  ┌───────────┐  ┌─────────────────────┐  │  │
│  │  │  Model   │→ │  Engine   │→ │  Redis Buffer       │  │  │
│  │  │  Router  │  │ (S/A/R)   │  │  chunks:{id}        │  │  │
│  │  └──────────┘  └───────────┘  │  done:{id}          │  │  │
│  │  Ollama ←→ Gemini (fallback)  │  result:{id}        │  │  │
│  │                                └─────────────────────┘  │  │
│  └─────────────────────────────────────────────────────────┘  │
│                          │                                    │
│  ┌─────────┐  ┌──────────┴──┐  ┌──────────┐                 │
│  │ Redis   │  │ PostgreSQL  │  │  Neo4j   │  (optional)      │
│  │ Cache   │  │ Persistence │  │  Graph   │                  │
│  └─────────┘  └─────────────┘  └──────────┘                 │
└───────────────────────────────────────────────────────────────┘
```

## 💻 Quick Start

### Prerequisites
- Python 3.11+ with `uv` or `pip`
- Node.js 18+
- PostgreSQL (running)
- Redis (running)
- [Ollama](https://ollama.com/) (recommended for local inference)

### 1. Clone & Setup Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Run database migrations
alembic upgrade head

# Start the API server
uvicorn main:app --port 8000

# In a separate terminal — start the background worker
PYTHONPATH=. arq worker.WorkerSettings
```

### 2. Setup Frontend
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000` in your browser.

### 3. Pull Local Models (Recommended)
```bash
ollama serve       # Start Ollama
ollama pull qwen2.5:3b
ollama pull phi
```

## 🔧 Environment Variables

| Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | — | Gemini API key (used as cloud fallback) |
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6379` | Redis URL for cache, streaming, and rate limiting |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL_NAME` | `qwen2.5:3b` | Default local model |
| `NEO4J_URI` | `bolt://localhost:7687` | Neo4j bolt URI (optional) |
| `JWT_SECRET` | `dev-secret-change-me` | **Change in production!** |

## 📁 Project Structure

```
backend/
├── api/routes.py          # FastAPI endpoints + SSE streaming
├── engine/
│   ├── simple_engine.py   # Fast single-pass extraction
│   ├── advanced_engine.py # Multi-step chunked extraction
│   └── reasoning_engine.py# Chain-of-thought extraction
├── llm/
│   ├── ollama_client.py   # Local inference via Ollama
│   ├── gemini_client.py   # Cloud inference via Gemini
│   └── model_router.py    # Automatic model selection + fallback
├── worker.py              # arq background job processor
├── core/                  # Config, models, prompts
├── db/                    # SQLAlchemy models + repositories
├── memory/                # Semantic extraction + Neo4j graph
└── utils/                 # JSON parser, chunker, embeddings

frontend/
├── src/components/
│   ├── app/AppShell.tsx   # Main application shell
│   ├── chat/              # ChatArea, ChatComposer
│   ├── output/            # OutputTabs (JSON viewer)
│   ├── sidebar/           # Session history + memory panel
│   └── settings/          # Model config, login
├── src/lib/api.ts         # API client with SSE support
├── src/state/             # Zustand store (persistent)
└── src/types/             # TypeScript type definitions
```

## 🔒 Security
- JWT-based authentication with access/refresh token rotation
- Full CORS configuration
- Redis-backed rate limiting on extraction endpoints
- Input sanitization on all user-provided text

## 📄 License
MIT
