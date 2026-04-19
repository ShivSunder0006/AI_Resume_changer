# 🤖 End-to-End Job Application Agent

A production-ready AI system that **tailors your resume** to any job description while **preserving the exact formatting** of your original PDF.

## ✨ Features

- **Format-Preserving PDF Editing** — Uses PyMuPDF redaction+overlay to modify text at exact coordinates
- **LangGraph Agent Orchestration** — Multi-node agentic workflow with retry logic
- **Groq → Gemini LLM Fallback** — Primary fast inference with automatic failover
- **Validation Pipeline** — Automatic checks for layout, fonts, spacing, and section order
- **Evaluation Metrics** — Keyword match, ATS simulation, content integrity scoring
- **DOCX Fallback** — Alternative pipeline for complex PDFs

## 🚀 Quick Start

```bash
# 1. Create conda env
conda env create -f environment.yml
conda activate ai-resume-agent

# 2. Configure API keys
cp .env.example .env
# Edit .env with your Groq and Gemini API keys

# 3. Run the API
python -m uvicorn src.api.main:app --reload

# 4. Run the UI
streamlit run src/ui/app.py
```

## 📁 Architecture

```
src/
├── agents/    — LangGraph orchestration
├── api/       — FastAPI backend
├── config/    — Settings & env loading
├── evaluation/— Quality scoring
├── llm/       — Groq/Gemini router
├── memory/    — Conversation memory
├── pdf/       — Format-preserving PDF pipeline
└── ui/        — Streamlit frontend
```
