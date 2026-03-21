# 🧠 Structured Extraction Intelligence Engine (v2.0)

> **The Enterprise-Grade Data Algebra Orchestrator: Unstructured Assets ➔ Immutable Relational Intelligence.**

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-000000?style=flat&logo=nextdotjs)](https://nextjs.org/)
[![Redis](https://img.shields.io/badge/Redis-DC382D?style=flat&logo=redis)](https://redis.io/)
[![Ollama](https://img.shields.io/badge/Ollama-000000?style=flat)](https://ollama.com/)
[![Tesseract](https://img.shields.io/badge/OCR-Tesseract-blue?style=flat)](https://github.com/tesseract-ocr/tesseract)

An elite, high-scale **AI SaaS Production Stack** designed to ingest complex, unstructured content matrices—dense PDFs, visual screenshots (OCR), and raw text streams—and dismantle them into strictly-typed, sub-millisecond JSON trees. Engineered for boundless multi-tenant concurrency and edge performance.

---

## 🌍 The Core Pipeline Constraint

In the age of Large Language Models, deterministic applications break because LLMs return non-deterministic, conversational syntax. 

The **Structured Extraction Intelligence Engine** resolves this state drift by binding loose attention vectors into structured **Pydantic Data Schemas** strictly enforcing data types, constraints, and valid relational anchors.

---

## ⚙️ Advanced System Architecture

### 🔄 Distributed Node Topology

```text
[ USER UI ] (React 18 / Zustand Client States)
     ┇
     ▼ 
[ API GATEWAY ] (FastAPI uvicorn workers)
     ┇
     ┣━━▶ 🔐 [ Auth Hardening ]: Silent JWT Key Rotation Interceptor
     ┣━━▶ 📈 [ Billing Guard ]: Deterministic Quota Exhaustion (402 Limits)
     ┗━━▶ ⚡ [ Edge Cache ]: SHA-256 State Hashing (Redis)
                            ⬇️ (Cache Hit: Bypass Queue, Stream <10ms)
[ ASYNC WORKER POOL ] (ARQ Master nodes)
     ┇
     ┣━━━▶ 📄 [ Ingestion ]: Tesseract Vision Maps / PyPDF Ingress
     ┣━━━▶ 🤖 [ LLM Orchestration ]: local llama.cpp / Ollama cluster
     ┗━━━▶ 🧪 [ Validation ]: Micro-Rerun Sanitizations & Schema Locks
     ┇
     ▼
[ DATA BACKPLANE ]
     ┣━━▶ 📦 [ Postgres ]: NullPool async thread delegation
     ┗━━▶ 📈 [ COGS Tracking ]: LLM Token calculation & margins auditing
```

---

## 🔥 Operations Complexity Matrices

To optimize compute limits and overhead expensing to protect system safety margins, workloads are dispatched across tiered capabilities:

### 🟢 **Simple Mode** (Sub-Second Operations)
*   **Default Engine**: `gemma:2b` Local Graph
*   **Ideal Core**: Clean invoices, scan parsing, standard lists grids.
*   **Logic Model**: High-speed, single-shot inference dispatch routing to local clusters.

### 🟡 **Advanced Mode** (Semantic Context Compression)
*   **Default Engine**: `phi3:mini` Default
*   **Ideal Core**: Lengthy contracts, recursive resumes, large PDFs files.
*   **Logic Model**: Overlapping sliding-window chunking matrix. Aggregates broken text into parallel vector buffers and reduces duplicates prior to final validation structures.

### 🔴 **Reasoning Mode** (Chain-of-Thought Rerun)
*   **Default Engine**: `mistral:latest` / Cloud Lookup
*   **Ideal Core**: Ambiguous tables, dense spreadsheets, medical diagnostics documents.
*   **Logic Model**: **Double-Pass Evaluation loop**. Directs the model to extract content, analyzes returned confidence anomalies, notes failures, and performs explicit prompt re-extractions of critical fields.

---

## 🧠 Core LLM Engineering Frameworks

Deterministic outcomes from probabilistic models demand advanced prompt framing and error correction subsystems:

### 1. **Zero-Overhead Sanitizers**
Models frequently leak string-residuals (e.g. ````json ... ```` wrapper frames). The router intercepts chunk streams mid-flight, automatically stripping markdown anchors, fixing missing trailing brackets, and converting Single-quote indices to clean `JSON` standards without forcing a full model rerun.

### 2. **Continuous heartbeats (SSE Generator)**
Waiting for heavy 30,000-token PDF inferences crashes browser proxies. The backend translates the static load into a **Server-Sent Events (SSE)** response stream, injecting standard `[HB]` heartbeat ticks every ~2s to hold browser `EventSource` and socket listeners perpetually active for massive generations.

---

## ⚡ High-Scale SaaS Optimization (v2.0 Upgrade)

Engineered natively to handle thousands of concurrent tenant streams without smashing local server limits:

| Infrastructure Layer | Advanced Implementation details | Engineering Margin |
| :--- | :--- | :--- |
| **Connection Pooling** | `NullPool` architecture offloads internal locking entirely onto Postgres balancers (PgBouncer). | Zero connection exhaustions under sudden massive traffic surges. |
| **SaaS Billing & Quotas** | Strict requests tracking threshold injected into API gates. | "Free" trial containers lock securely at 50 queries/day threshold with hard HTTP 402 lockouts. |
| **Edge Cache (Redis)** | Stringified Dictionary `separators=(",", ":")` sort keys. | Guarantees absolute deterministic Cache Hashing over identical document nodes. |
| **Security Credentials** | Axios/Fetch silent JWT Rotation Interceptor. | Intercepts `401 Unauthorized` inside React and silently renews access keys to keep active sessions fluid. |

---

## 🧪 Что I Learned (Engineering Post-Mortem)

*   **MissingGreenlet Concurrency conflicts**: Highly async FastAPI setups crash if sub-threads attempt recursive SQL deletions concurrently on implicit ORM attributes. Migrated safely to explicit `Relationship` joins to maintain boundless CPU frame rates.
*   **Redis lists buffers**: Speed tests previously failed because iterative pub/subs didn't wait efficient delays. Setup fully blocking lists pops with explicit `timeout=0.5` pauses loading CPU bottlenecks completely.

---

## 🚀 How to Run (Cluster Deployment)

#### **1. Database & Cache layer**
Ensure PostgreSQL is active and standard Redis nodes are mapped safely on standard ports (`6379`).

#### **2. Backend setup**
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Concurrently trigger standard operations:
uvicorn main:app --port 8000 --reload
# ARQ Background Worker Loop:
arq worker.WorkerSettings
```

#### **3. Frontend Dashboard**
```bash
cd frontend
npm install
npm run dev
```

---

## 🔥 Advanced Future Evolutions

- [ ] **Adaptive Routing Engine**: Automated token allocation dynamically redirecting over 2,000 words into Cloud fallbacks before executing Local threads.
- [ ] **Dashboard visual query visualizers**: Elastic-search nodes allowing full text retrieval on loaded parsed extraction grids in real-time.

---

> 📌 **Final Statement**: Static web scraping frameworks are obsolete. This engine treats unstructured formats as dynamic relational algebras, providing consistent Data reliability across Local LLM matrix operations.
