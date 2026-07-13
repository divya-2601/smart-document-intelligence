# 🧠 Smart Document Intelligence

A multi-PDF semantic retrieval and grounded answer synthesis platform powered by **Google Gemini** and **Pinecone**. Upload documents, ask questions in natural language, and receive accurate answers backed by citations — all through an intuitive Streamlit interface.

---

## ✨ Features

| Feature | Description |
|---|---|
| **PDF Ingestion & Chunking** | Upload PDFs, extract text with PyMuPDF, and split into semantically meaningful chunks using LangChain text splitters |
| **Vector Embeddings** | Generate high-dimensional embeddings via Google Gemini (`gemini-embedding-2`) with configurable dimensionality |
| **Semantic Search** | Store and query embeddings in Pinecone for fast, cosine-similarity-based retrieval |
| **RAG Chat Interface** | Conversational Q&A with streaming responses, chat history persistence, and source citations |
| **PromptOps Console** | Create, version, edit, and activate prompt templates with a full lifecycle management UI |
| **Prompt Comparison** | Side-by-side A/B evaluation of different prompt templates on the same query and context |
| **Analytics Dashboard** | Real-time metrics including response latencies, prompt usage distribution, citation frequency, and retrieval confidence |
| **User Feedback** | Thumbs-up / thumbs-down feedback on responses, persisted for evaluation |
| **Configurable Settings** | Adjust Top-K retrieval count and similarity score thresholds at runtime |

---

## 🏗️ Architecture

```
smart-document-intelligence/
├── app.py                    # Main Streamlit entry point & page routing
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variable template
├── .streamlit/
│   └── config.toml           # Streamlit server configuration
├── assets/
│   └── style.css             # Custom CSS theme
├── src/
│   ├── database.py           # SQLite schema & CRUD operations
│   ├── embeddings.py         # Gemini embedding wrapper
│   ├── pdf_processor.py      # PDF parsing & chunking (PyMuPDF)
│   ├── rag_pipeline.py       # RAG orchestration with Gemini LLM
│   ├── utils.py              # Shared helper utilities
│   └── vector_store.py       # Pinecone vector database integration
└── ui_pages/
    ├── Home.py               # Landing page
    ├── Workspace.py           # Document upload & chat workspace
    ├── Analytics.py           # Performance analytics dashboard
    ├── PromptOps.py           # Prompt template management
    ├── Prompt_Comparison.py   # A/B prompt comparison
    └── Settings.py            # RAG configuration & connection info
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+**
- A [Google AI API key](https://aistudio.google.com/apikey) (for Gemini models)
- A [Pinecone API key](https://www.pinecone.io/) with a serverless index

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/smart-document-intelligence.git
   cd smart-document-intelligence
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate        # macOS / Linux
   venv\Scripts\activate           # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and fill in your actual API keys:
   ```
   GOOGLE_API_KEY=your_google_api_key_here
   PINECONE_API_KEY=your_pinecone_api_key_here
   PINECONE_INDEX=your_pinecone_index_name_here
   ```

### Running the Application

```bash
streamlit run app.py
```

The application will open in your browser at `http://localhost:8501`.

---

## 🛠️ Technologies Used

| Technology | Purpose |
|---|---|
| [Streamlit](https://streamlit.io/) | Web UI framework |
| [Google Gemini](https://ai.google.dev/) | LLM for answer generation & text embeddings |
| [Pinecone](https://www.pinecone.io/) | Serverless vector database for semantic search |
| [PyMuPDF (fitz)](https://pymupdf.readthedocs.io/) | PDF text extraction |
| [LangChain Text Splitters](https://python.langchain.com/) | Recursive text chunking |
| [Plotly](https://plotly.com/python/) | Interactive analytics charts |
| [SQLite](https://www.sqlite.org/) | Local metadata, chat history, and feedback storage |

---

## 📄 License

This project is provided as-is for educational and personal use. See [LICENSE](LICENSE) for details.
