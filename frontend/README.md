# Structured Extraction Intelligence Engine (Frontend)

ChatGPT-style UI for generating structured JSON from documents/text.

## Quick start

1. Start the backend (FastAPI) on `http://localhost:8000` (see repo root).
2. From `frontend/`:

```bash
npm install
npm run dev
```

3. Open `http://127.0.0.1:3000`.

### Backend URL

Set (optional):

```bash
export NEXT_PUBLIC_API_BASE_URL="http://localhost:8000/api/v1"
```

If `POST /api/v1/extract` is not implemented yet, text extraction falls back to converting text into a temporary PDF and calling `POST /api/v1/extract-file`.

## Folder layout

- `src/app/` Next.js app router (root layout + `/` entry).
- `src/components/`
  - `app/` app shell (sidebar + top bar + chat area)
  - `chat/` composer + chat rendering
  - `output/` JSON/Pretty/Reasoning views
  - `sidebar/` episodic + semantic memory panel
  - `settings/` settings + placeholder login
  - `ui/` shadcn/ui-style primitives
- `src/lib/`
  - `api.ts` API client (React Query not required here yet; calls are mutation-like)
  - `semantic.ts` semantic tag extraction from model output
  - `utils.ts` `cn()` helper
- `src/state/` Zustand store (chat history + settings + semantic insights)

