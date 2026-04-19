git add .gitignore pyproject.toml README.md environment.yml .env.example
git commit -m "feat: initial project structure and configuration"
git add src/api src/memory src/config src/llm src/utils
git commit -m "feat: implement backend API, session memory, and utility modules"
git add src/agents src/pdf src/evaluation
git commit -m "feat: core AI orchestration with LangGraph and PDF parsing engine"
git add src/ui
git commit -m "feat: modernized Streamlit UI with Pastel Theme and Live PDF Preview"
git add tests
git commit -m "test: add initial test suite"
git add .
git commit -m "chore: final project structure and remaining files"
