# ADR-001: Definição de Stack Tecnológica e Governança de Vendas

- **Status:** Aprovado
- **Data:** 2026-08-20
- **Decisores:** Sueli Hora (Analytics & AI Engineer)

---

## 1. Contexto
A **Rash Rolamentos Industriais** necessita de um assistente de vendas consultivo para triagem técnica. O cliente frequentemente desconhece o código exato da peça e descreve a aplicação por diâmetro, rotação ou esforço mecânico. O maior risco do negócio é o modelo de IA inventar medidas inexistentes, praticar preços defasados ou emitir pedidos sem conferência humana.

---

## 2. Decisões Arquiteturais

### 2.1 Stack Técnica
* **Linguagem:** Python 3.11+ (ecossistema maduro para IA e engenharia de dados).
* **Framework de Agentes / LLM:** Chamadas estruturadas de ferramentas (*Tool Calling*) com **LangChain / LangGraph** para encadeamento determinístico de etapas.
* **Banco de Dados Operacional:** **SQLite** (embutido, leve para MVP e determinístico) para armazenar o catálogo de peças, dimensões, estoque e tabela de preços.
* **Interface / API:** **FastAPI** para expor os endpoints de conversação e painel de aprovação.

### 2.2 Governança e Mitigação de Riscos
* **Zero Alucinação de Catálogo:** A LLM não tem permissão para responder preços ou medidas de memória. Toda resposta de catálogo é alimentada exclusivamente via retorno SQL/Tool Calling determinístico.
* **Human-in-the-Loop:** Quando o cliente atinge a etapa de fechamento/cotação formal, o status é alterado para `Aguardando_Aprovacao`, exigindo validação manual antes da emissão do documento.
* **Privacidade & LGPD:** Mascaramento de dados de contato do cliente nos logs e rastreabilidade do consumo de tokens por sessão.

---

## 3. Consequências
* **Positivas:** 100% de precisão nos preços e especificações fornecidos ao cliente; segurança operacional para a diretoria comercial.
* **Trade-offs:** Necessidade de manutenção de uma tabela de catálogo padronizada e dependência de aprovação humana para conclusão do pedido no MVP.