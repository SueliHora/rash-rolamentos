# ADR-001: Definição de Stack Tecnológica, Catálogo Determinístico e Governança HITL

- **Status:** Aprovado
- **Data:** 2026-08-26
- **Autora / Decisora:** Sueli Hora (Analytics & AI Engineer)
- **Repositório:** [rash-rolamentos](https://github.com/SueliHora/rash-rolamentos.git)

---

## 1. Contexto & Problema de Negócio

A **Rash Rolamentos Industriais** atua na distribuição B2B de componentes mecânicos de alta precisão (rolamentos de esferas, rolos cônicos, autocompensadores e mancais). O processo tradicional de vendas e triagem técnica enfrenta dois grandes desafios:

1. **Inviabilidade de Erros Dimensionais e Técnicos:** Em engenharia mecânica industrial, uma divergência milimétrica em um diâmetro de eixo ($d$), diâmetro externo ($D$) ou largura ($B$) resulta em falha de montagem ou parada crítica de linha de produção (*downtime*).
2. **Risco de Alucinação em Preços e Prazos:** Modelos de linguagem generativos (LLMs) operando sem amarras determinísticas tendem a inventar preços fora da tabela de atacado, supor disponibilidade de estoque ou fechar pedidos sem alçada comercial.

---

## 2. Decisões Arquiteturais

### 2.1. Catálogo Determinístico Relacional (SQLite) vs. RAG Vetorial

* **Decisão:** Rejeitar RAG vetorial para consulta de dados dimensionais e comerciais em favor de um banco de dados relacional determinístico (**SQLite 3**).
* **Justificativa:** Embeddings e busca por similaridade vetorial (RAG) são probabilísticos e ineficazes para distinção precisa de atributos numéricos (ex.: diferenciar 20 mm de 22 mm). O SQLite garante consultas SQL exatas com filtros dimensionais, tolerâncias paramétricas e integridade relacional entre produtos, especificações, estoque e preços.

### 2.2. Orquestração com LangGraph e Tool Calling

* **Decisão:** Utilizar **LangGraph** estruturado como um `StateGraph` cíclico conectado ao modelo **Google Gemini 1.5 Flash** (`langchain-google-genai`).
* **Justificativa:** O grafo define nós bem delimitados para raciocínio (`llm_node`) e execução de ferramentas determinísticas (`tools_node`). A persistência de estado em memória com `MemorySaver` (`thread_id`) viabiliza conversas multi-turnos contextuais sem perda de parâmetros técnicos coletados.

### 2.3. Trava de Governança Human-in-the-Loop (HITL) no Streamlit

* **Decisão:** Implementar barreira de segurança humana (*Human-in-the-Loop*) na interface **Streamlit**.
* **Justificativa:** Toda cotação formal gerada pelo agente nasce no estado `AGUARDANDO_APROVACAO`. Pedidos com alto volume ($\ge 10$ unidades) ou descontos acima da alçada padrão ($> 15\%$) exigem aprovação explícita de um operador humano no painel lateral de governança antes da confirmação final.

---

## 3. Consequências

### 3.1. Consequências Positivas
- **100% de Precisão Mecânica:** Dimensões, códigos ISO e preços são lidos diretamente do banco `data/rash.db`, eliminando alucinações de catálogo.
- **Conformidade e Governança:** Registro auditável de tokens, custos por sessão e pedidos pendentes de validação.
- **Experiência do Usuário:** Interface Streamlit interativa e ágil para clientes e operadores.

### 3.2. Trade-offs & Mitigações
- **Manutenção de Schema:** Mudanças no portfólio exigem atualização do script `data/seed.py` e esquema relacional `data/schema.sql`.
- **Intervenção Manual:** Pedidos de grande porte exigem tempo de resposta do operador humano, trade-off necessário para garantir a segurança financeira da operação.