# Contributing to Rash Rolamentos

Thank you for your interest in contributing to **Rash Rolamentos** and the **RashBot** agentic platform!

Please review the following minimalist guidelines before submitting code.

---

## 🛠️ Development Workflow

### 1. Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (Modern Python package manager)
- Git

### 2. Fork & Clone
```bash
git clone https://github.com/<your-username>/rash-rolamentos.git
cd rash-rolamentos
```

### 3. Create a Feature Branch
```bash
git checkout -b feat/my-new-feature
```

### 4. Install Dependencies
```bash
# Sync dependencies and development tools:
uv sync --all-extras --dev
```

### 5. Environment Setup
```bash
# Copy environment configuration
cp .env.example .env

# Configure your GEMINI_API_KEY inside .env
```

---

## 🧪 Quality Checks & Testing

Before submitting a Pull Request, all automated checks must pass:

```bash
# 1. Run Ruff linter:
uv run ruff check .

# 2. Run automated test suite:
uv run pytest -v

# 3. Verify deterministic database integrity:
uv run python src/test_db.py
```

---

## 📝 Commit Conventions

We enforce [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New features (e.g., new tools, UI components, catalog parameters).
- `fix:` Bug fixes or SQL query corrections.
- `docs:` Documentation improvements (`README.md`, `PRD.md`, `ARCHITECTURE.md`).
- `test:` Adding or refactoring unit/integration tests.
- `refactor:` Code changes that neither fix a bug nor add a feature.
- `perf:` Performance optimizations or token efficiency gains.
- `chore:` Dependency updates, CI workflows, or maintenance.

---

## 🚀 Submitting a Pull Request

1. Push your branch to GitHub:
   ```bash
   git push origin feat/my-new-feature
   ```
2. Open a Pull Request targeting the `main` branch.
3. Ensure CI pipeline passes on GitHub Actions.
4. Describe your changes clearly with relevant screenshots if modifying the Streamlit UI.
