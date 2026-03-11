# 📁 Digital Filing Cabinet

<div align="center">

<video src="https://github.com/user-attachments/assets/153a7e74-f413-4094-b759-13a088a69479" width="600"></video>

**Your documents. Your machine. Your answers.**

A local-first intelligent document system that runs entirely on your computer.
Upload PDFs, Word docs, PowerPoints, spreadsheets, and images — then ask questions in plain English.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Local First](https://img.shields.io/badge/AI-100%25_Local-purple.svg)](#-local-models)

</div>

---

## 🚀 One-Click Setup

```bash
git clone https://github.com/tanavc1/digital-filing-cabinet.git
cd digital-filing-cabinet
./setup.sh
```

That's it. The setup script will:
- ✅ Install **[Ollama](https://ollama.com)** (local AI runtime) if not present
- ✅ Pull the **phi4-mini** text model and **qwen3-vl** vision model
- ✅ Install all Python and Node.js dependencies
- ✅ Create config files with local-first defaults

Then start the app:
```bash
sh scripts/start_pilot.sh
# Open http://localhost:3000
```

**No API keys.** No cloud accounts. No sign-ups.

---

## 🧠 Local Models

Every AI component runs on your machine. Nothing is sent to the cloud.

| Component | Model | Size | Purpose |
|-----------|-------|------|---------|
| **Text LLM** | `phi4-mini` via [Ollama](https://ollama.com) | ~2.5 GB | Answer generation, evidence extraction, query rewriting |
| **Vision LLM** | `qwen3-vl:8b` via [Ollama](https://ollama.com) | ~5 GB | Chart analysis, diagram understanding, scanned doc OCR |
| **Embeddings** | `BAAI/bge-small-en-v1.5` | ~130 MB | Semantic search vectors (auto-downloaded on first run) |
| **Reranker** | `ms-marco-MiniLM-L-6-v2` | ~90 MB | Cross-encoder for result quality scoring (auto-downloaded) |
| **Vector DB** | LanceDB (embedded) | — | Serverless, no separate process needed |

### Hardware Requirements

- **Apple Silicon** (M1–M4): MPS acceleration auto-detected, ~4–8 GB RAM for all models
- **NVIDIA GPU**: CUDA auto-detected for faster inference
- **CPU-only**: Works fine, just slower on first query while models load
- Models lazy-load only when needed — they don't consume memory until you use them

---

## ✨ What It Does

### 📄 Upload Any Document

| Format | What Happens |
|--------|-------------|
| **PDF** | Text extraction + OCR on scanned pages (RapidOCR) |
| **Word (.docx)** | Full text + structure extraction via Docling |
| **PowerPoint (.pptx)** | Slide-by-slide content extraction |
| **Excel (.xlsx)** | Tabular data extraction |
| **Markdown / Text** | Heading-aware chunking |
| **HTML** | Content extraction with structure |
| **Images** (PNG, JPG, GIF, WebP) | Vision AI describes content, then indexes it for search |
| **ZIP archives** | Bulk upload a folder of mixed files |

### 🔍 Ask Questions, Get Cited Answers

The system combines three search methods for accuracy:

1. **BM25 keyword search** — catches exact names, numbers, legal terms
2. **Semantic vector search** (`bge-small-en-v1.5`) — understands meaning ("revenue growth" matches "sales increase")
3. **Cross-encoder reranking** (`ms-marco-MiniLM`) — re-scores results by true relevance

Every answer includes **exact citations** back to the source document and paragraph.

### 👁️ Vision Intelligence

Upload charts, diagrams, whiteboards, or scanned receipts. The local `qwen3-vl` model analyzes images and makes the content searchable.

*Example*: Upload a Q3 earnings chart → ask "What was the revenue trend?" → get an answer sourced from the image.

### 📈 Built to Scale

- **LanceDB query pushdown** — filters run at the storage layer, not in Python
- **In-memory BM25 cache** — keyword index loads once, not per query
- **Connection pooling** — Ollama connections reused across requests
- **Workspace isolation** — organize docs into separate collections

### 📋 Audit & Compliance

- Automated document audits against question templates
- Clause tracking and risk assessment
- Side-by-side document comparison
- Playbook engine for structured analysis
- Export to CSV/Excel

---

## ☁️ Optional: Cloud Providers

The system works 100% locally by default. But if you prefer faster cloud models, you can switch:

### Use OpenAI for Text LLM
```env
# In your .env file:
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
```

### Use Google Gemini for Vision
```env
# In your .env file:
VISION_PROVIDER=gemini
GEMINI_API_KEY=AIza-your-key-here
```

You can toggle between local and cloud mode in the **Settings** page of the app, or set it in your `.env` file. Embeddings and reranking always run locally regardless of provider choice.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│               Your Computer                      │
│                                                  │
│   Next.js UI ──▶ FastAPI Backend                │
│   :3000           :8000                          │
│                    │                             │
│                    ├── Ollama                    │
│                    │    phi4-mini  (text LLM)    │
│                    │    qwen3-vl   (vision LLM)  │
│                    │                             │
│                    ├── Python Models              │
│                    │    bge-small  (embeddings)   │
│                    │    ms-marco   (reranker)     │
│                    │                             │
│                    └── LanceDB (vectors + docs)  │
│                                                  │
│   Nothing leaves this box.                       │
└─────────────────────────────────────────────────┘
```

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 15, TailwindCSS, Lucide Icons |
| **API** | FastAPI, Uvicorn, SlowAPI (rate limiting) |
| **Text AI** | Ollama + phi4-mini (local) — or OpenAI (optional) |
| **Vision AI** | Ollama + qwen3-vl:8b (local) — or Gemini (optional) |
| **Embeddings** | BAAI/bge-small-en-v1.5 (always local) |
| **Reranker** | ms-marco-MiniLM-L-6-v2 (always local) |
| **Vector DB** | LanceDB (embedded, serverless) |
| **PDF/OCR** | PyMuPDF + RapidOCR |
| **Doc Parsing** | Docling (DOCX, PPTX, HTML) |

---

## ⚙️ Configuration

See [`.env.example`](.env.example) for all options. Minimal config:

```env
DB_PATH=./lancedb_data
ADMIN_PASSWORD=your-password
```

Everything else has sensible local-first defaults.

---

## 🔐 Security

- **Zero data exfiltration** — all AI local by default
- **Input validation** — Pydantic schemas on every endpoint
- **Rate limiting** — 10 req/min/user on query endpoints
- **Error sanitization** — keys and traces never leak to clients
- **Workspace isolation** — strict document scoping

---

## 📄 License

MIT

---

<div align="center">

**Your documents should stay on your machine.**

</div>
