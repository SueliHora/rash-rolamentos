# Diretrizes para Agentes de IA — Rash Rolamentos

Este documento define os padrões técnicos, restrições arquiteturais e diretrizes de desenvolvimento para agentes de IA e desenvolvedores que trabalham no repositório **Rash Rolamentos Industriais**.

---

## 1. Visão Geral & Filosofia Arquitetural

O **RashBot** é um agente autônomo de vendas técnicas B2B com governança **Human-in-the-Loop (HITL)** e **Catálogo Determinístico**.

### ⚠️ Regra de Ouro: Zero Alucinação de Catálogo

- Parâmetros dimensionais (diâmetro interno, diâmetro externo, largura, folga radial), códigos ISO, estoque e preços **NUNCA** devem ser inferidos ou calculados probabilisticamente pelo modelo de linguagem.

- Todas as informações técnicas e comerciais devem ser obtidas exclusivamente via chamadas às funções do módulo `src/database.py` e tools do `src/tools.py`.

---

## 2. Gerenciamento de Dependências com `uv`

Este projeto utiliza o **[uv](https://docs.astral.sh/uv/)** e o arquivo `pyproject.toml` como única fonte de verdade para o ambiente Python (>= 3.11).

### Diretrizes de Execução:

- **Sincronizar ambiente:** `uv sync`
- **Executar scripts:** `uv run python <script.py>`
- **Executar a aplicação:** `uv run streamlit run app.py`
- **Executar testes:** `uv run python src/test_db.py` e `uv run python src/test_agent.py`
- **Adicionar pacotes:** `uv add <pacote>`
- **Proibido:** Não execute `pip install` solto nem crie ou referencie arquivos `requirements.txt`.

---

## 3. Segurança & Isolamento de Credenciais

- O arquivo `.env` contém chaves confidenciais e **NUNCA** deve ser commitado no repositório Git (protegido via `.gitignore`).
- Sempre mantenha o `.env.example` atualizado com a lista de variáveis exigidas:
  ```env
  GEMINI_API_KEY=sua_chave_aqui
  GEMINI_MODEL=gemini-1.5-flash
  LOG_LEVEL=INFO
  ```
- O modelo primário configurado para chamadas do Google GenAI é `gemini-1.5-flash`.

---

## 4. Integridade do Catálogo de Dados (SQLite)

- O banco de dados operacional é mantido em `data/rash.db` com DDL definido em `data/schema.sql` e script de seed determinístico em `data/seed.py`.
- **Nunca quebre schemas ou tabelas existentes:**
  - `produtos`: Armazena códigos ISO, tipo de rolamento, dimensões ($d, D, B$), folga, capacidade de carga e preço base.
  - `estoque`: Armazena saldo atual por produto com restrições de integridade.
  - `pedidos` & `itens_pedido`: Armazena cotações e o status de aprovação (`AGUARDANDO_APROVACAO`, `APROVADO`, `REJEITADO`).
  - `auditoria_ia`: Rastreia tokens de entrada, saída e latência por sessão.

---

## 5. Estrutura do Código-Fonte (`src/`)

- `src/agent.py`: Orquestrador LangGraph (`StateGraph`, `MemorySaver`, nós `llm` e `tools`, lista de fallback de modelos).
- `src/database.py`: Camada de acesso a dados com transações e consultas determinísticas parametrizadas (protegidas contra SQL Injection).
- `src/tools.py`: Ferramentas LangChain vinculadas ao agente com tipagem rigorosa e docstrings explícitas.
- `src/test_db.py` e `src/test_agent.py`: Suítes de testes unitários e de integração.

---

## 6. Validação e Testes Obrigatórios

Antes de finalizar qualquer modificação no código ou nas ferramentas do agente, execute as suítes de validação:

```bash
# 1. Validar integridade e regras de negócio do banco:
uv run python src/test_db.py

# 2. Validar raciocínio e execução de tools do agente:
uv run python src/test_agent.py
```

---

## 7. Padrão de Commits Semânticos (Conventional Commits)

Utilize o padrão **Conventional Commits** em todas as alterações do repositório:

- `feat:` Nova funcionalidade no agente, interface ou catálogo.
- `fix:` Correção de bugs, queries SQL ou tratamento de exceções.
- `docs:` Atualizações em documentação (`README.md`, `ADR`, `AGENTS.md`, `PRD.md`).
- `test:` Inclusão ou refatoração de testes automatizados.
- `refactor:` Modificações no código que não alteram comportamento público.
- `perf:` Melhorias de desempenho ou otimização de queries/tokens.
- `chore:` Manutenção de arquivos de configuração ou rotinas de build.
