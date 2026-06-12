# SafarnāmaGPT 🕌
**Pakistan Tourism Chatbot — RAG + Quantized LLM (runs fully offline)**

SafarnāmaGPT is an AI travel assistant specializing in Pakistan tourism. It uses
Retrieval-Augmented Generation (RAG) to answer questions about destinations,
culture, trekking, heritage sites, cuisine, and travel logistics — all powered
by a local GGUF-quantized LLM with no API keys or cloud services required.

---

## Architecture

```
Web Scraper ──► data/raw/*.txt
                     │
              build_index.py
                     │
              FAISS vector store ──► RAG retriever ──► Llama 3.2 (GGUF) ──► Streamlit UI
```

- **LLM**: Llama 3.2 3B Instruct Q4_K_M via `llama-cpp-python` (CPU)
- **Embeddings**: `all-MiniLM-L6-v2` (sentence-transformers, local)
- **Vector store**: FAISS (local files, no server)
- **Data**: ~40 pages scraped from Wikipedia, Wikivoyage

---

## Setup

### 0. Clone the repository
```powershell
git clone https://github.com/fozankhana/SafarnamaGPT.git
cd SafarnamaGPT
```
> Don't have Git? Download it from https://git-scm.com/download/win

### 1. Prerequisites
- Python 3.11 (https://python.org)
- Git (https://git-scm.com)
- 4 GB free RAM, ~3 GB disk space

### 2. Create virtual environment
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
# If execution policy error:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 3. Install dependencies
```powershell
pip install --upgrade pip
pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
pip install -r requirements.txt
```
> The `--extra-index-url` flag fetches the pre-built CPU wheel for llama-cpp-python.
> Building from source requires MSVC and takes 10+ minutes.
> **Note:** NumPy is pinned to 1.26.4 — do not upgrade it; NumPy 2.x breaks `faiss-cpu`.

### 4. Download the GGUF model (~2 GB)
```powershell
python -c "
from huggingface_hub import hf_hub_download
hf_hub_download(
    'bartowski/Llama-3.2-3B-Instruct-GGUF',
    'Llama-3.2-3B-Instruct-Q4_K_M.gguf',
    local_dir='models'
)
"
```
Alternatively download manually and place it in the `models/` folder.

### 5. Scrape tourism data (~3-5 minutes)
```powershell
python scripts\scrape_data.py
```
Saves ~40 cleaned text files to `data/raw/`.

### 6. Build the vector index (~2 minutes)
```powershell
python scripts\build_index.py
```
Downloads `all-MiniLM-L6-v2` (~90 MB) on first run. Builds FAISS index in `data/vectorstore/`.

### 7. Launch the app
```powershell
streamlit run app.py
```
Open your browser at **http://localhost:8501**

---

## How to Use

1. **Open the app** — your browser opens automatically at `http://localhost:8501`
2. **Ask a question** — type any Pakistan travel question in the chat box, for example:
   - *"What are the best treks in Gilgit-Baltistan?"*
   - *"Tell me about the Badshahi Mosque in Lahore."*
   - *"What is the best time to visit Hunza Valley?"*
3. **Get an answer** — the RAG pipeline retrieves relevant passages from scraped tourism data, then the LLM generates a grounded response
4. **Start a new chat** — click **New Chat** in the sidebar to clear the conversation
5. **Browse history** — previous conversations are listed in the sidebar and can be reopened at any time

> **Tip:** The sidebar shows which LLM backend is active and has a password field to enter your Groq API key.
> You can also pass the key as an environment variable before launching:
> ```powershell
> $env:GROQ_API_KEY = "gsk_..."   # get a free key at console.groq.com
> streamlit run app.py
> ```
> **No Groq key?** Switch to the fully-offline local model by editing [config.py](config.py):
> ```python
> use_groq: bool = False   # uses Llama-3.2-3B-Instruct-Q4_K_M.gguf from models/
> ```

---

## Mobile App (Android & iOS)

The `Safarnama Tourism App/` folder contains a full Flutter app that connects to a
FastAPI backend wrapping the same RAG pipeline.

### Architecture
```
Flutter App (Android/iOS)  ──HTTP+SSE──►  FastAPI backend (Render cloud)
                                                   │
                                          src/rag.py + src/llm.py (Groq)
```

### Step 1 — Deploy the backend to Render (free)
1. Push this repo to GitHub (already done at `github.com/fozankhana/SafarnamaGPT`)
2. Go to [render.com](https://render.com) → New → Web Service → connect your GitHub repo
3. Render auto-detects `render.yaml` and configures everything
4. Add environment variable `GROQ_API_KEY` in the Render dashboard
5. Note your service URL, e.g. `https://safarnamagpt-api.onrender.com`

### Step 2 — Install Flutter
Download from [flutter.dev](https://docs.flutter.dev/get-started/install/windows) and
add `flutter/bin` to your PATH.

### Step 3 — Build the Android APK
```powershell
cd "Safarnama Tourism App"
.\build_apk.ps1
```
The APK is output to `build\app\outputs\flutter-apk\app-release.apk`.
Transfer it to your Android phone and install (enable "Install from unknown sources" first).

### Step 4 — Configure the app
On first launch open **Settings** (⚙ icon) and enter:
- Your backend URL from Step 1
- Your Groq API key (`gsk_...` — free at [console.groq.com](https://console.groq.com))

### iOS
Open `Safarnama Tourism App/` in Xcode, set your Team ID, and run on device or simulator.

---

## Configuration

Edit `config.py` to change:
| Setting | Default | Notes |
|---------|---------|-------|
| `model_filename` | `Llama-3.2-3B-Instruct-Q4_K_M.gguf` | Any GGUF model in `models/` |
| `model_family` | `llama3` | Use `mistral` for Mistral models |
| `n_threads` | `4` | CPU threads for inference |
| `n_gpu_layers` | `0` | Set to `-1` for full GPU offload |
| `retrieval_top_k` | `4` | Chunks retrieved per query |
| `chunk_size` | `512` | Characters per chunk |

---

## Tips

- **Faster responses**: Use a smaller model (Phi-3 Mini 3.8B Q4) or reduce `max_tokens`
- **GPU acceleration**: Set `n_gpu_layers = -1` in config.py if you have NVIDIA GPU + CUDA
- **Better quality**: Try `Llama-3.2-3B-Instruct-Q8_0.gguf` (3.4 GB, higher accuracy)
- **More data**: Add more URLs to `SCRAPE_TARGETS` in `scripts/scrape_data.py` and rebuild the index

---

## Project Structure

```
├── app.py                      Streamlit chat UI (web)
├── api.py                      FastAPI backend for mobile app
├── config.py                   Central configuration
├── requirements.txt            Web app dependencies
├── requirements-api.txt        Mobile backend dependencies
├── Procfile                    Render/Railway start command
├── render.yaml                 One-click Render deployment
├── src/
│   ├── rag.py                  RAG pipeline (retrieve + generate)
│   ├── llm.py                  LLM wrapper (Groq + local GGUF)
│   ├── embedder.py             sentence-transformers wrapper
│   └── utils.py                Shared helpers
├── scripts/
│   ├── scrape_data.py          Web scraper → data/raw/
│   └── build_index.py          Chunker + FAISS index builder
├── data/
│   ├── raw/                    Scraped .txt files (gitignored)
│   └── vectorstore/            FAISS index files
├── models/                     GGUF model files (gitignored)
└── Safarnama Tourism App/      Flutter mobile app (Android + iOS)
    ├── lib/
    │   ├── main.dart           App entry point
    │   ├── screens/            ChatScreen, HistoryScreen
    │   ├── widgets/            SettingsSheet
    │   ├── services/           ApiService (HTTP + SSE)
    │   └── models/             Conversation, ChatEvent, SourceDoc
    ├── android/                Android project files
    ├── pubspec.yaml            Flutter dependencies
    └── build_apk.ps1           One-click APK build script
```
