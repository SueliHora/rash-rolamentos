# Product Requirements Document (PRD) — RashBot: B2B Technical Sales & Governance Agent

## 1. Executive Summary & Problem Statement

### 1.1 Business Context
**Rash Rolamentos Industriais** is an industrial distributor specializing in high-precision rolling bearings, housings, and technical seals for manufacturing, mining, pulp and paper, and agribusiness sectors.

### 1.2 The Problem
- **LLM Hallucination in Technical Quotations:** Generic generative AI chatbots hallucinate mechanical dimensions (inner diameter, outer diameter, width), ISO part numbers, load ratings, and commercial pricing. In mission-critical industrial B2B sales, a quoted bearing with the wrong clearance or dimensional tolerance can cause equipment seizure, severe operational downtime, and catastrophic financial/legal liabilities.
- **Quotation Bottlenecks:** Industrial buyers often submit vague requirements (e.g., "bearing for a vibrating screen under high temperatures") rather than exact part codes. Technical sales engineers spend hours manually cross-referencing catalogs, calculating volume discounts, and verifying warehouse inventory instead of closing high-value commercial agreements.
- **Uncontrolled Commercial Exposure:** Autonomous agents that close orders without human oversight present severe commercial risks (e.g., unauthorized deep discounts or stock reservations for out-of-catalog items).

---

## 2. Value Proposition & Business Impact

| Metric / Objective | Traditional Process | With RashBot Agent | Impact |
| :--- | :--- | :--- | :--- |
| **Catalog Accuracy** | Prone to human/AI transcription errors | **100% Deterministic** via SQLite engine | **0% Hallucination** on dimensions, codes, and base prices |
| **Quote Turnaround Time** | 2 to 4 hours per request | **< 30 seconds** interactive response | **> 90% reduction** in lead response latency |
| **Commercial Governance** | Ad-hoc manual verification | **Human-in-the-Loop (HITL)** triggers | 100% policy enforcement on high volume & discounts |
| **Cost & Token Auditability** | Unmonitored overhead | Session-based token & latency audit | Transparent ROI & operational observability |

---

## 3. Scope of the Solution (MVP)

### 3.1 In-Scope Features
1. **Consultative Natural Language Querying:** Translates user-described mechanical operating conditions (vibration, high temperature, radial/axial loads) into ISO bearing recommendations.
2. **Deterministic Catalog Resolution:** Direct parameter extraction against normalized SQLite tables (`produtos`, `estoque`, `pedidos`, `itens_pedido`).
3. **Structured Quotation & Order Generation:** Automated drafting of formal quotes with tier-based volume discounts.
4. **Human-in-the-Loop (HITL) Governance Workflow:** Automatic state transition to `AGUARDANDO_APROVACAO` when order volume exceeds threshold ($\ge 10$ units) or requested discount exceeds policy ($> 15\%$). Final release requires human manager sign-off.
5. **Session Cost & Observability:** Real-time token consumption, latency, and audit logs recorded per interaction.

### 3.2 Out-of-Scope (Future Iterations)
- Direct integration with third-party payment gateways.
- Automatic fiscal invoice (NF-e) generation.
- Real-time legacy ERP bidirectional synchronization.

---

## 4. Functional & Non-Functional Requirements

### 4.1 Functional Requirements (FR)
- **FR-01 (Consultative Search):** The agent must identify compatible ISO bearing series given operating keywords (e.g., electric motor, jaw crusher, centrifugal pump).
- **FR-02 (Dimensional Search):** The agent must query exact inner diameter ($d$), outer diameter ($D$), and width ($B$) with optional radial clearance ($C3$, etc.).
- **FR-03 (Inventory & Pricing):** Stock levels and prices must be retrieved deterministically from the database and never estimated.
- **FR-04 (Order Registration):** Quotes must capture customer name, tax ID (CNPJ/CPF), item codes, quantities, and applied discount rates.
- **FR-05 (HITL Approval Gate):** Quotes exceeding business thresholds must require manual approval in the managerial dashboard before formal release.

### 4.2 Non-Functional Requirements (NFR)
- **NFR-01 (Zero Hallucination):** 0% tolerance for non-catalog mechanical parameters or fake part numbers.
- **NFR-02 (Performance):** Agent response latency $\le 3$ seconds per reasoning turn under standard network conditions.
- **NFR-03 (Security & Privacy):** SQL injection prevention via strictly parameterized queries; PII compliance (LGPD) with sensitive data masking in logs.
- **NFR-04 (State Persistence):** Thread-level conversation state maintained using LangGraph `MemorySaver`.

---

## 5. Success Metrics & Validation

- **Zero Tolerance Policy:** Zero unapproved formal quotes issued.
- **Coverage:** 100% test coverage for deterministic database queries and tool routing.
- **Adoption:** Seamless management handoff via Streamlit-based interactive governance dashboard.
