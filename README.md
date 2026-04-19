# 🚀 Logly — Ask your logs anything.

An AI-powered local web app that helps engineers debug system logs using a **RAG (Retrieval-Augmented Generation)** pipeline.

**Stack**: FastAPI · React · Ollama (`gemma:2b`) · sentence-transformers · FAISS

---

## ⚡ Quick Start

### 1. Install Ollama

Download from [https://ollama.com/download](https://ollama.com/download) and install.

Then pull the model:
```bash
ollama pull gemma:2b
```

Verify it's running:
```bash
ollama serve          # starts Ollama (runs automatically on Windows after install)
curl http://localhost:11434/api/tags
```

---

### 2. Backend Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
python main.py
```

Backend runs at **http://localhost:8000**

Check health: [http://localhost:8000/health](http://localhost:8000/health)

> **Note**: First run downloads `all-MiniLM-L6-v2` (~90MB) automatically.

---

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at **http://localhost:5173**

---

## 🚀 Usage

1. Open [http://localhost:5173](http://localhost:5173)
2. **Upload a log file** — drag-and-drop a `.log` or `.txt` file into the sidebar
3. **Ask questions** — type in the chat, e.g.:
   - *"What errors occurred and why?"*
   - *"Which service had the most issues?"*
   - *"What caused the high memory usage?"*
4. Click **Summarize Log** for a full AI-generated overview
5. Upload a second file and click **Compare Logs** for a diff analysis

---

## 📁 Project Structure

```
Log_Analyzer/
├── backend/
│   ├── main.py          # FastAPI app + endpoints
│   ├── rag.py           # RAG pipeline + Ollama client
│   ├── embedding.py     # sentence-transformers + FAISS
│   ├── utils.py         # chunking, classification helpers
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── App.jsx
│       ├── index.css
│       └── components/
│           ├── FileUpload.jsx
│           ├── ChatInterface.jsx
│           ├── MessageBubble.jsx
│           └── ActionButtons.jsx
└── data/
    └── logs/
        └── sample.log   # Test file with mixed ERROR/WARNING/INFO entries
```

---

## 🔌 API Endpoints

| Method | Endpoint       | Description                           |
|--------|----------------|---------------------------------------|
| GET    | `/health`      | Health check + Ollama status          |
| POST   | `/upload-log`  | Upload & process a log file           |
| POST   | `/ask`         | Ask a question (RAG pipeline)         |
| POST   | `/summarize`   | Generate log summary                  |
| POST   | `/compare`     | Compare two uploaded log files        |
| GET    | `/files`       | List all processed files              |

---

## ⚙️ Configuration

Set these environment variables (or create a `backend/.env` file):

```env
OLLAMA_BASE_URL=http://localhost:11434   # default
OLLAMA_MODEL=gemma:2b                    # or llama3 for better quality
```

---

## 🧠 How It Works

```
Upload .log file
      │
      ▼
  Chunk into ~200-char segments
      │
      ▼
  Embed with all-MiniLM-L6-v2 (local)
      │
      ▼
  Store in FAISS IndexFlatL2 (in-memory)
      │
  User asks question
      │
      ▼
  Embed question → FAISS search top-5 chunks
      │
      ▼
  Send chunks + question to Ollama (gemma:2b)
      │
      ▼
  Return AI answer + source chunks
```

---

## 📦 Dependencies (Total ~2.6GB, one-time)

| Dependency | Size |
|---|---|
| Ollama runtime | ~500MB |
| `gemma:2b` model | ~1.7GB |
| `all-MiniLM-L6-v2` | ~90MB (auto-download) |
| Python packages | ~200MB |
| Node modules | ~150MB |
