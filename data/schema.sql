-- =============================================================
--  RashBot — Schema do Banco de Dados
--  Distribuidora Rash Rolamentos Industriais
--  SQLite3
-- =============================================================

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- -------------------------------------------------------------
--  Tabela: produtos
--  Catálogo de rolamentos e peças industriais.
--  Preços e medidas são consultados deterministicamente pelo
--  agente — nunca inventados pelo modelo de linguagem.
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS produtos (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo                 TEXT    NOT NULL UNIQUE,          -- ex: '6204-2RSH', '22212-E'
    tipo                   TEXT    NOT NULL,                 -- ex: 'Rolamento Rígido de Esferas'
    diametro_interno_mm    REAL    NOT NULL,
    diametro_externo_mm    REAL    NOT NULL,
    largura_mm             REAL    NOT NULL,
    aplicacao_recomendada  TEXT    NOT NULL,
    preco_unitario         REAL    NOT NULL CHECK (preco_unitario >= 0),
    estoque_qtd            INTEGER NOT NULL DEFAULT 0 CHECK (estoque_qtd >= 0),
    created_at             TIMESTAMP DEFAULT (datetime('now','localtime'))
);

-- -------------------------------------------------------------
--  Tabela: pedidos
--  Cabeçalho de cada cotação/pedido gerado pelo agente.
--  status permanece em 'AGUARDANDO_APROVACAO' até que um
--  vendedor humano aprove (Human-in-the-Loop).
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pedidos (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_nome     TEXT    NOT NULL,
    cliente_contato  TEXT    NOT NULL,                      -- WhatsApp / e-mail (mascarado na exibição)
    status           TEXT    NOT NULL DEFAULT 'AGUARDANDO_APROVACAO'
                             CHECK (status IN (
                                 'AGUARDANDO_APROVACAO',
                                 'APROVADO',
                                 'REJEITADO',
                                 'CANCELADO',
                                 'ENTREGUE'
                             )),
    total            REAL    NOT NULL DEFAULT 0.0 CHECK (total >= 0),
    data_criacao     TIMESTAMP DEFAULT (datetime('now','localtime'))
);

-- -------------------------------------------------------------
--  Tabela: itens_pedido
--  Linha de item de cada pedido (N itens por pedido).
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS itens_pedido (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id      INTEGER NOT NULL REFERENCES pedidos(id)  ON DELETE CASCADE,
    produto_id     INTEGER NOT NULL REFERENCES produtos(id) ON DELETE RESTRICT,
    quantidade     INTEGER NOT NULL CHECK (quantidade > 0),
    preco_unitario REAL    NOT NULL CHECK (preco_unitario >= 0)  -- preço no momento do pedido
);

-- -------------------------------------------------------------
--  Tabela: auditoria_ia
--  Registro de tokens e custo estimado por atendimento.
--  Governança de custo conforme exigência do PRD §3.4.
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS auditoria_ia (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id           TEXT,                              -- ID da sessão do agente (opcional)
    prompt_tokens        INTEGER NOT NULL DEFAULT 0,
    completion_tokens    INTEGER NOT NULL DEFAULT 0,
    custo_estimado_usd   REAL    NOT NULL DEFAULT 0.0,
    created_at           TIMESTAMP DEFAULT (datetime('now','localtime'))
);

-- -------------------------------------------------------------
--  Índices para performance
-- -------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_produtos_codigo  ON produtos (codigo);
CREATE INDEX IF NOT EXISTS idx_produtos_tipo    ON produtos (tipo);
CREATE INDEX IF NOT EXISTS idx_pedidos_status   ON pedidos  (status);
CREATE INDEX IF NOT EXISTS idx_itens_pedido_pid ON itens_pedido (pedido_id);
CREATE INDEX IF NOT EXISTS idx_auditoria_date   ON auditoria_ia (created_at);
