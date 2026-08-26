"""
data/seed.py
============
Script de seed para o banco SQLite do RashBot.

Cria o banco `data/rash.db`, aplica o schema e popula a
tabela `produtos` com 15 rolamentos industriais realistas,
com medidas padronizadas (ISO/DIN) e aplicações mecânicas
detalhadas — garantindo zero alucinação do modelo de linguagem
conforme requisito do PRD §3.2 (Consulta Determinística).

Uso:
    python data/seed.py
"""

import sqlite3
import pathlib
import sys
import textwrap

# ── Caminhos ─────────────────────────────────────────────────
BASE_DIR    = pathlib.Path(__file__).resolve().parent          # data/
SCHEMA_FILE = BASE_DIR / "schema.sql"
DB_FILE     = BASE_DIR / "rash.db"


# ── Dados de seed ─────────────────────────────────────────────
# Formato: (codigo, tipo, d_interno, d_externo, largura, aplicacao, preco, estoque)
PRODUTOS: list[tuple] = [
    # --- Rolamentos Rígidos de Esferas (Deep Groove Ball Bearings) ---
    (
        "6004-2RSH",
        "Rolamento Rígido de Esferas",
        20.0, 42.0, 12.0,
        "Motores elétricos de baixa potência, bombas centrífugas de pequeno porte, "
        "ventiladores axiais, eixos de transmissão leve. Vedação dupla em borracha "
        "resistente a poeira e respingos de óleo.",
        18.50, 150
    ),
    (
        "6204-2RSH",
        "Rolamento Rígido de Esferas",
        20.0, 47.0, 14.0,
        "Motores elétricos monofásicos e trifásicos de até 2 CV, compressores de ar "
        "de pequeno porte, redutores de velocidade, eixos de máquinas agrícolas leves. "
        "Alta velocidade admissível; vedação bilateral.",
        22.90, 200
    ),
    (
        "6304-2RSH",
        "Rolamento Rígido de Esferas",
        20.0, 52.0, 15.0,
        "Motores elétricos industriais de até 5 CV, eixos de bombas de engrenagem, "
        "transportadores de correia compactos. Suporta cargas radiais moderadas com "
        "leve carga axial.",
        31.40, 120
    ),
    (
        "6206-2RSH",
        "Rolamento Rígido de Esferas",
        30.0, 62.0, 16.0,
        "Motores elétricos de 3 a 15 CV, bombas industriais de médio porte, "
        "ventiladores centrífugos, eixos de redutores e motoventiladores. "
        "Boa resistência a vibração e temperatura de até 120 °C.",
        38.70, 180
    ),
    (
        "6310-2Z",
        "Rolamento Rígido de Esferas",
        50.0, 110.0, 27.0,
        "Motores elétricos de 15 a 75 CV, bombas de alta vazão, compressores "
        "industriais, ventiladores de grande porte. Tampa metálica (Z) para "
        "ambientes com partículas abrasivas grossas.",
        89.20, 75
    ),
    # --- Rolamentos de Rolos Cilíndricos (Cylindrical Roller Bearings) ---
    (
        "NU210-E",
        "Rolamento de Rolos Cilíndricos",
        50.0, 90.0, 20.0,
        "Caixas de câmbio industriais, redutores de engrenagem de alta carga, "
        "eixos principais de tornos CNC e fresadoras. Suporta cargas radiais muito "
        "elevadas; permite deslocamento axial do eixo.",
        145.00, 60
    ),
    (
        "NU312-E",
        "Rolamento de Rolos Cilíndricos",
        60.0, 130.0, 31.0,
        "Laminadores de aço, redutores de grande porte, moinhos de bolas, "
        "prensas excêntricas. Alta capacidade de carga dinâmica; ideal para "
        "velocidades moderadas e cargas pesadas contínuas.",
        298.00, 35
    ),
    # --- Rolamentos Autocompensadores de Rolos (Spherical Roller Bearings) ---
    (
        "22212-E",
        "Rolamento Autocompensador de Rolos",
        60.0, 110.0, 28.0,
        "Agitadores industriais, ventiladores de processos, transportadores de "
        "correia pesados, moinhos de martelo e picadores. Compensa desalinhamento "
        "angular de até 1,5°; suporta cargas combinadas elevadas.",
        412.00, 40
    ),
    (
        "22318-E",
        "Rolamento Autocompensador de Rolos",
        90.0, 190.0, 64.0,
        "Britadores de mandíbula, moinhos de bolas de grande porte, "
        "redutores de alto torque da indústria mineradora, guindastes industriais. "
        "Capacidade de carga estática muito elevada; compensa até 2° de desalinhamento.",
        1_240.00, 12
    ),
    # --- Rolamentos de Esferas de Contato Angular (Angular Contact Ball Bearings) ---
    (
        "7208-BE",
        "Rolamento de Esferas de Contato Angular",
        40.0, 80.0, 18.0,
        "Fusos de máquinas-ferramenta (tornos CNC, centros de usinagem), "
        "bombas de alta pressão, compressores de parafuso. "
        "Ângulo de contato 40°; suporta carga axial elevada em um sentido.",
        187.50, 55
    ),
    (
        "7310-BECBP",
        "Rolamento de Esferas de Contato Angular",
        50.0, 110.0, 27.0,
        "Fusos de fresadoras de alta velocidade, eixos de retificadoras, "
        "caixas de câmbio de precisão. Montagem pareada para absorver cargas "
        "axiais em ambos os sentidos; tolerância P5.",
        345.00, 28
    ),
    # --- Rolamentos de Rolos Cônicos (Tapered Roller Bearings) ---
    (
        "32210-J2",
        "Rolamento de Rolos Cônicos",
        50.0, 90.0, 24.5,
        "Diferenciais automotivos industriais, eixos de rodas de veículos "
        "pesados, redutores de ângulo reto, guindastes de carga. "
        "Excelente para cargas combinadas; pré-carga ajustável pelo anel separador.",
        167.00, 80
    ),
    (
        "30310-D",
        "Rolamento de Rolos Cônicos",
        50.0, 110.0, 29.25,
        "Eixos de rodas de caminhões e equipamentos off-road, pontes rolantes, "
        "eixos de extrusoras plásticas. Alta rigidez axial; ângulo de contato maior "
        "para maior absorção de carga axial.",
        234.00, 50
    ),
    # --- Rolamentos de Agulhas (Needle Roller Bearings) ---
    (
        "NK35/20",
        "Rolamento de Agulhas",
        35.0, 45.0, 20.0,
        "Eixos de bielas em compressores alternativos, pedais de máquinas "
        "industriais, atuadores hidráulicos compactos, caixas de câmbio "
        "de empilhadeiras. Perfil radial ultrafino; ideal para espaços confinados.",
        52.80, 95
    ),
    # --- Rolamentos de Esferas de Pressão Axial (Thrust Ball Bearings) ---
    (
        "51210",
        "Rolamento de Esferas de Pressão Axial",
        50.0, 78.0, 22.0,
        "Macacos hidráulicos, prensas de parafuso, mesas giratórias de "
        "máquinas-ferramenta, válvulas de controle de fluxo industrial. "
        "Suporta exclusivamente cargas axiais puras em um sentido; "
        "velocidade rotacional moderada.",
        76.30, 65
    ),
]


# ── Funções ───────────────────────────────────────────────────

def create_database(conn: sqlite3.Connection, schema_path: pathlib.Path) -> None:
    """Aplica o schema SQL ao banco de dados."""
    schema_sql = schema_path.read_text(encoding="utf-8")
    conn.executescript(schema_sql)
    conn.commit()
    print(f"  [OK] Schema aplicado de: {schema_path}")


def seed_produtos(conn: sqlite3.Connection, produtos: list[tuple]) -> int:
    """
    Insere os produtos de catálogo no banco.
    Usa INSERT OR IGNORE para ser idempotente (re-executável sem duplicar).
    Retorna o número de linhas efetivamente inseridas.
    """
    sql = textwrap.dedent("""
        INSERT OR IGNORE INTO produtos
            (codigo, tipo, diametro_interno_mm, diametro_externo_mm,
             largura_mm, aplicacao_recomendada, preco_unitario, estoque_qtd)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """).strip()

    cursor = conn.cursor()
    cursor.executemany(sql, produtos)
    conn.commit()
    return cursor.rowcount  # -1 quando executemany; usaremos outro modo abaixo


def seed_produtos_verbose(conn: sqlite3.Connection, produtos: list[tuple]) -> int:
    """Versão verbosa: insere um por um e imprime o resultado."""
    sql = """
        INSERT OR IGNORE INTO produtos
            (codigo, tipo, diametro_interno_mm, diametro_externo_mm,
             largura_mm, aplicacao_recomendada, preco_unitario, estoque_qtd)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    cursor = conn.cursor()
    inserted = 0
    for produto in produtos:
        cursor.execute(sql, produto)
        if cursor.rowcount == 1:
            inserted += 1
            print(f"  [OK] Inserido: {produto[0]:15s} | {produto[1]}")
        else:
            print(f"  [--] Ja existe: {produto[0]:15s} | {produto[1]}")
    conn.commit()
    return inserted


def print_summary(conn: sqlite3.Connection) -> None:
    """Imprime um resumo do banco após o seed."""
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM produtos")
    total_produtos = cursor.fetchone()[0]

    cursor.execute("SELECT tipo, COUNT(*) as qtd FROM produtos GROUP BY tipo ORDER BY qtd DESC")
    por_tipo = cursor.fetchall()

    cursor.execute("SELECT MIN(preco_unitario), MAX(preco_unitario), AVG(preco_unitario) FROM produtos")
    preco_min, preco_max, preco_avg = cursor.fetchone()

    cursor.execute("SELECT SUM(estoque_qtd) FROM produtos")
    estoque_total = cursor.fetchone()[0]

    print("\n" + "-" * 60)
    print(f"  RESUMO DO BANCO -- rash.db")
    print("-" * 60)
    print(f"  Total de produtos     : {total_produtos}")
    print(f"  Estoque total (pecas) : {estoque_total}")
    print(f"  Preco minimo          : R$ {preco_min:>8.2f}")
    print(f"  Preco maximo          : R$ {preco_max:>8.2f}")
    print(f"  Preco medio           : R$ {preco_avg:>8.2f}")
    print("\n  Produtos por tipo:")
    for tipo, qtd in por_tipo:
        print(f"    - {tipo:<45} {qtd:>2} item(ns)")
    print("-" * 60)


# ── Entry point ───────────────────────────────────────────────

def main() -> None:
    print("\n[RashBot] Database Seed")
    print("=" * 60)

    if not SCHEMA_FILE.exists():
        print(f"[ERRO] Arquivo de schema nao encontrado: {SCHEMA_FILE}", file=sys.stderr)
        sys.exit(1)

    print(f"  -> Banco de dados: {DB_FILE}")

    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("PRAGMA foreign_keys = ON")

        print("\n[1/2] Aplicando schema...")
        create_database(conn, SCHEMA_FILE)

        print("\n[2/2] Inserindo produtos...")
        inserted = seed_produtos_verbose(conn, PRODUTOS)

        print(f"\n  [DONE] {inserted} produto(s) novo(s) inserido(s) de {len(PRODUTOS)} total.")
        print_summary(conn)

    print(f"\n[OK] Banco pronto em: {DB_FILE.resolve()}\n")


if __name__ == "__main__":
    main()
