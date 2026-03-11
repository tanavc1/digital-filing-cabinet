# 📁 Digital Filing Cabinet


https://github.com/user-attachments/assets/153a7e74-f413-4094-b759-13a088a69479


**Your intelligent, multi-modal knowledge base.**

The Digital Filing Cabinet is a powerful RAG (Retrieval-Augmented Generation) system that turns your documents—text, PDFs, and *images*—into a searchable, conversational knowledge base. It combines state-of-the-art vector search with traditional keyword search to answer complex questions instantly.

## 🚀 Features

-   **🧠 Hybrid Search**: Merges semantic understanding (bi-encoder vectors) with keyword precision (BM25) followed by a Cross-Encoder re-ranker for top-tier accuracy.
-   **👁️ Multi-Modal Vision**: Upload charts, diagrams, screenshots, or whiteboard photos. Note: Requires `GEMINI_API_KEY`.
    -   *Automatic Analysis*: The system uses Gemini Vision 2.0 to describe images in detail.
    -   *Searchable*: You can ask questions like "What is the trend in the sales chart?" and get accurate answers based on the image content.
-   **📄 Advanced Processing**:
    -   **PDFs**: Hybrid extractor cleans text and runs OCR on scanned pages (using RapidOCR).
    -   **Images**: Direct image ingestion via `/ingest/image`.
-   **💬 Conversational UI**: A modern Next.js frontend with streaming responses, history, and source citations.
-   **🛡️ Production Ready**: Rate limiting, strict error handling, CORS security, and automated CI/CD tests.

## 🛠️ Quick Start

### Prerequisites
-   **Python 3.10+** (Recommend 3.11/3.12)
-   **Node.js 18+**
-   **API Keys**:
    -   `OPENAI_API_KEY`: For answer generation and embeddings.
    -   `GEMINI_API_KEY`: For vision/image analysis capabilities.

### 1. Backend Setup

```bash
# Clone the repository
git clone https://github.com/tanavchinthapatla/digital-filing-cabinet.git
cd digital-filing-cabinet

# Install Python dependencies
pip install -r requirements.txt

# Configure Environment
# Create a .env file with your keys
echo "OPENAI_API_KEY=sk-..." > .env
echo "GEMINI_API_KEY=AIza..." >> .env
echo "DB_PATH=./lancedb_data" >> .env

# Run the Backend
sh start_pilot.sh
# Server runs on http://localhost:8000
```

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run the Development Server
npm run dev
# App opens at http://localhost:3000
```

## 🧪 Testing

We include robust automated tests to ensure system integrity.

```bash
# Run Core Evidence Verification (Text/PDF RAG)
python verify_evidence.py

# Run Vision Verification (Image Gen -> Search)
# Requires GEMINI_API_KEY
python verify_vision.py
```

## 📚 Architecture

-   **Frontend**: Next.js 15 (App Router), TailwindCSS, Lucide Icons.
-   **Backend**: FastAPI, Uvicorn, SlowAPI (Rate Limiting).
-   **AI Engines**:
    -   **LLM**: OpenAI GPT-4o (or configured model).
    -   **Vision**: Google Gemini 2.0 Flash.
    -   **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2`.
    -   **Reranker**: `cross-encoder/ms-marco-MiniLM-L-6-v2` (MPS/CPU optimized).
-   **Database**: LanceDB (Embedded Vector Store).

## 🔒 Security

-   **API Keys**: Securely managed via `.env`. Errors are sanitized to strictly hide keys from client.
-   **Validation**: All inputs validated via Pydantic.
-   **Rate Limiting**: Query endpoint limited to 10 req/min/user.

---
