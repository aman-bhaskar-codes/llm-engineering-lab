# Structured Extraction Intelligence Engine

![chat_history_fix_verified_1774027236284](https://github.com/user-attachments/assets/replace-with-actual-screenshot-url) <!-- Replace with your own screenshot URL for GitHub -->

A production-grade, multi-model AI system designed to convert unstructured text and documents into rigorously structured JSON data. 

Built with **FastAPI**, **React (Next.js)**, **Zustand**, and **PostgreSQL**, this engine acts as a resilient, fail-open pipeline that prioritizes local LLM inference (Ollama) for low latency and privacy, with seamless fallback to cloud models (Gemini).

## 🚀 Key Features

- **Multi-Model Inference:** 
  - **Local First:** Defaults to `qwen2.5:3b` and `phi` via Ollama for sub-10 second latency and absolute data privacy.
  - **Cloud Fallback:** Instantly switch to `gemini-2.5-flash` for complex reasoning tasks.
- **Three Core Modes:**
  - `Simple`: Fast, direct extraction for well-formatted text.
  - `Advanced`: Multi-step extraction designed for noisy data or OCR output.
  - `Reasoning`: Chain-of-thought processing that guarantees the highest quality extraction and logic verification.
- **Resilient Memory Systems (Fail-Open):** 
  - Uses robust **Redis** caching to eliminate duplicate API calls.
  - **PostgreSQL** for persistent conversation history and extraction metadata.
  - Optional **Neo4j** integration for semantic relationship graphs mapping entities across conversations.
- **Unified Pipeline:** All interactions (regardless of mode) flow through a rock-solid, typed JSON pipeline that guarantees schema adherence.

## 🛠️ Architecture

```mermaid
graph TD
    UI[Frontend (React/Zustand)] --> API[FastAPI Gateway]
    API --> Cache[Redis Cache]
    API --> Router[Model Router]
    Router --> Ollama[Local: Qwen/Phi]
    Router --> Gemini[Cloud: Gemini]
    Ollama & Gemini --> Parser[JSON Sanitization Pipeline]
    Parser --> DB[PostgreSQL]
    Parser --> Neo4j[Graph Memory - Optional]
```

## 💻 Local Quickstart

### 1. Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL
- Redis
- [Ollama](https://ollama.com/) (optional but recommended for local inference)

### 2. Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Set up your environment variables
cp .env.example .env
# Edit .env to add your database URLs and API keys

# Apply Alembic migrations
alembic upgrade head

# Run the server
uvicorn main:app --reload --port 8000
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
The app will be running at `http://localhost:3000`.

### 4. Pull Local Models (Optional)
If you want to run the engine locally without utilizing cloud APIs:
```bash
ollama pull qwen2.5:3b
ollama pull phi
```

## 🔒 Security
- JWT-based authentication system.
- Full CORS configuration.
- Rate limiting implemented via Redis sorted sets to protect the extraction endpoints.

## 📄 License
MIT
