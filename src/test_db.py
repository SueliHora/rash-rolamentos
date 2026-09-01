"""
src/test_db.py
==============
Suite de testes funcionais para src/database.py.

Testa todas as funções da camada de acesso ao banco com casos
reais baseados no seed do rash.db. Usa apenas stdlib (unittest)
para não adicionar dependências extras.

Uso:
    uv run python src/test_db.py
"""

import logging
import pathlib
import sys
import unittest

# Garante que 'src/' está no path independentemente de onde o teste é executado
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import database as db

# Silencia logs durante os testes (só mostra WARNING+)
logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

# ── Cores ANSI para output legível no terminal ─────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


def sep(titulo: str = "") -> None:
    line = "-" * 60
    if titulo:
        print(f"\n{CYAN}{BOLD}{line}{RESET}")
        print(f"{CYAN}{BOLD}  {titulo}{RESET}")
        print(f"{CYAN}{BOLD}{line}{RESET}")
    else:
        print(f"{CYAN}{line}{RESET}")


# =============================================================================
#  CASO 1 — consultar_produtos_por_aplicacao
# =============================================================================
class TestConsultarPorAplicacao(unittest.TestCase):

    def test_busca_por_motor_eletrico(self):
        """Deve retornar rolamentos indicados para motor elétrico."""
        sep("TESTE: consultar_produtos_por_aplicacao('motor eletrico')")
        resultados = db.consultar_produtos_por_aplicacao("motor eletrico")
        print(f"  Encontrados: {len(resultados)} produto(s)")
        for r in resultados:
            print(f"    [{r['codigo']:<15}] {r['tipo']} — R$ {r['preco_unitario']:.2f} "
                  f"| Estoque: {r['estoque_qtd']}")
        self.assertGreater(len(resultados), 0, "Nenhum produto encontrado para 'motor eletrico'")
        codigos = [r["codigo"] for r in resultados]
        # O 6204-2RSH é o rolamento mais indicado para motores elétricos no seed
        self.assertIn("6204-2RSH", codigos)

    def test_busca_por_britador_mineracao(self):
        """Deve retornar o 22318-E para britadores."""
        sep("TESTE: consultar_produtos_por_aplicacao('britador')")
        resultados = db.consultar_produtos_por_aplicacao("britador")
        print(f"  Encontrados: {len(resultados)} produto(s)")
        for r in resultados:
            print(f"    [{r['codigo']:<15}] {r['tipo']} — R$ {r['preco_unitario']:.2f}")
        self.assertTrue(any(r["codigo"] == "22318-E" for r in resultados))

    def test_busca_multiplos_termos(self):
        """Busca com múltiplos termos deve refinar resultados (AND)."""
        sep("TESTE: consultar_produtos_por_aplicacao('fuso maquina ferramenta')")
        resultados = db.consultar_produtos_por_aplicacao("fuso maquina ferramenta")
        print(f"  Encontrados: {len(resultados)} produto(s)")
        for r in resultados:
            print(f"    [{r['codigo']:<15}] {r['tipo']}")
        # 7208-BE e 7310-BECBP são para fusos de máquinas-ferramenta
        self.assertGreater(len(resultados), 0)

    def test_busca_sem_resultado(self):
        """Termo inexistente deve retornar lista vazia."""
        sep("TESTE: consultar_produtos_por_aplicacao('submarino nuclear')")
        resultados = db.consultar_produtos_por_aplicacao("submarino nuclear")
        print(f"  Encontrados: {len(resultados)} produto(s) [esperado: 0]")
        self.assertEqual(resultados, [])

    def test_termo_vazio_retorna_vazio(self):
        """Termo vazio deve retornar lista vazia sem erro."""
        sep("TESTE: consultar_produtos_por_aplicacao('')")
        resultados = db.consultar_produtos_por_aplicacao("")
        print(f"  Retornou lista vazia: {resultados == []}")
        self.assertEqual(resultados, [])

    def test_retorno_contem_campos_esperados(self):
        """Cada item deve conter todos os campos do schema."""
        resultados = db.consultar_produtos_por_aplicacao("bomba")
        if resultados:
            campos_esperados = {
                "id", "codigo", "tipo",
                "diametro_interno_mm", "diametro_externo_mm", "largura_mm",
                "aplicacao_recomendada", "preco_unitario", "estoque_qtd"
            }
            self.assertTrue(campos_esperados.issubset(resultados[0].keys()))


# =============================================================================
#  CASO 2 — consultar_por_dimensoes
# =============================================================================
class TestConsultarPorDimensoes(unittest.TestCase):

    def test_dimensoes_exatas_6204(self):
        """Busca com dimensões exatas do 6204-2RSH (ø20 × ø47 × 14 mm)."""
        sep("TESTE: consultar_por_dimensoes(20.0, 47.0, 14.0)")
        resultados = db.consultar_por_dimensoes(20.0, 47.0, 14.0)
        print(f"  Encontrados: {len(resultados)} produto(s)")
        for r in resultados:
            print(f"    [{r['codigo']:<15}] {r['diametro_interno_mm']} x "
                  f"{r['diametro_externo_mm']} x {r['largura_mm']} mm — R$ {r['preco_unitario']:.2f}")
        codigos = [r["codigo"] for r in resultados]
        self.assertIn("6204-2RSH", codigos)

    def test_dimensoes_sem_largura(self):
        """Busca sem largura retorna todos com di/de compatíveis."""
        sep("TESTE: consultar_por_dimensoes(50.0, 90.0)  — sem largura")
        resultados = db.consultar_por_dimensoes(50.0, 90.0)
        print(f"  Encontrados: {len(resultados)} produto(s)")
        for r in resultados:
            print(f"    [{r['codigo']:<15}] {r['diametro_interno_mm']} x "
                  f"{r['diametro_externo_mm']} x {r['largura_mm']} mm")
        # NU210-E (50x90x20) e 32210-J2 (50x90x24.5) devem aparecer
        codigos = [r["codigo"] for r in resultados]
        self.assertIn("NU210-E",  codigos)
        self.assertIn("32210-J2", codigos)

    def test_dimensoes_com_tolerancia_ampla(self):
        """Com tolerância de 5 mm deve retornar mais resultados."""
        sep("TESTE: consultar_por_dimensoes(20.0, 47.0, tolerancia_mm=5.0)")
        strict  = db.consultar_por_dimensoes(20.0, 47.0, tolerancia_mm=1.0)
        ampla   = db.consultar_por_dimensoes(20.0, 47.0, tolerancia_mm=5.0)
        print(f"  Tolerancia 1mm: {len(strict)} produto(s)")
        print(f"  Tolerancia 5mm: {len(ampla)} produto(s)")
        self.assertGreaterEqual(len(ampla), len(strict))

    def test_dimensoes_inexistentes(self):
        """Dimensões sem correspondência devem retornar lista vazia."""
        sep("TESTE: consultar_por_dimensoes(999.0, 9999.0)")
        resultados = db.consultar_por_dimensoes(999.0, 9999.0)
        print(f"  Encontrados: {len(resultados)} produto(s) [esperado: 0]")
        self.assertEqual(resultados, [])

    def test_retorno_ordenado_por_proximidade(self):
        """O primeiro resultado deve ser o mais próximo das dimensões solicitadas."""
        resultados = db.consultar_por_dimensoes(20.0, 47.0, 14.0)
        if len(resultados) > 0:
            self.assertEqual(resultados[0]["codigo"], "6204-2RSH")


# =============================================================================
#  CASO 3 — verificar_estoque_e_preco
# =============================================================================
class TestVerificarEstoquePreco(unittest.TestCase):

    def test_produto_existente(self):
        """Deve retornar dict completo com estoque e preco do 6204-2RSH."""
        sep("TESTE: verificar_estoque_e_preco('6204-2RSH')")
        resultado = db.verificar_estoque_e_preco("6204-2RSH")
        print(f"  Produto : {resultado.get('codigo')}")
        print(f"  Tipo    : {resultado.get('tipo')}")
        print(f"  Preco   : R$ {resultado.get('preco_unitario'):.2f}")
        print(f"  Estoque : {resultado.get('estoque_qtd')} unidades")
        print(f"  Disponivel: {resultado.get('disponivel')}")
        self.assertEqual(resultado["codigo"], "6204-2RSH")
        self.assertAlmostEqual(resultado["preco_unitario"], 22.90)
        self.assertEqual(resultado["estoque_qtd"], 200)
        self.assertTrue(resultado["disponivel"])

    def test_produto_caro_britador(self):
        """Verifica o 22318-E — produto de alto valor (R$ 1.240,00)."""
        sep("TESTE: verificar_estoque_e_preco('22318-E')")
        resultado = db.verificar_estoque_e_preco("22318-E")
        print(f"  Preco   : R$ {resultado.get('preco_unitario'):.2f}")
        print(f"  Estoque : {resultado.get('estoque_qtd')} unidades")
        self.assertAlmostEqual(resultado["preco_unitario"], 1240.00)
        self.assertTrue(resultado["disponivel"])

    def test_case_insensitive(self):
        """Busca deve ser case-insensitive (maiúsculas/minúsculas)."""
        sep("TESTE: verificar_estoque_e_preco('6204-2rsh')  [lowercase]")
        resultado = db.verificar_estoque_e_preco("6204-2rsh")
        print(f"  Codigo retornado: {resultado.get('codigo')}")
        self.assertNotEqual(resultado, {})
        self.assertEqual(resultado["codigo"], "6204-2RSH")

    def test_produto_inexistente_retorna_dict_vazio(self):
        """Código inválido deve retornar dict vazio, não exceção."""
        sep("TESTE: verificar_estoque_e_preco('XPTO-9999')")
        resultado = db.verificar_estoque_e_preco("XPTO-9999")
        print(f"  Retornou vazio: {resultado == {}}")
        self.assertEqual(resultado, {})

    def test_campo_disponivel_presente(self):
        """O campo 'disponivel' deve estar presente e ser bool."""
        resultado = db.verificar_estoque_e_preco("6004-2RSH")
        self.assertIn("disponivel", resultado)
        self.assertIsInstance(resultado["disponivel"], bool)


# =============================================================================
#  CASO 4 — criar_cotacao
# =============================================================================
class TestCriarCotacao(unittest.TestCase):

    def _busca_produto(self, codigo: str) -> dict:
        return db.verificar_estoque_e_preco(codigo)

    def test_cotacao_simples(self):
        """Cria cotação com 1 item e valida o ID retornado."""
        sep("TESTE: criar_cotacao — 1 item (6204-2RSH x 10 unidades)")
        prod = self._busca_produto("6204-2RSH")
        itens = [{
            "produto_id":    prod["id"],
            "codigo":        prod["codigo"],
            "quantidade":    10,
            "preco_unitario": prod["preco_unitario"],
        }]
        pedido_id = db.criar_cotacao(
            cliente_nome="Metalurgica Souza Ltda",
            cliente_contato="+55 11 98765-4321",
            itens=itens,
        )
        print(f"  Pedido criado com ID: {pedido_id}")
        print(f"  Total esperado: R$ {10 * prod['preco_unitario']:.2f}")
        self.assertIsInstance(pedido_id, int)
        self.assertGreater(pedido_id, 0)

    def test_cotacao_multiplos_itens(self):
        """Cria cotação com múltiplos rolamentos diferentes."""
        sep("TESTE: criar_cotacao — 3 itens mistos")
        prod1 = self._busca_produto("6310-2Z")
        prod2 = self._busca_produto("22212-E")
        prod3 = self._busca_produto("NK35/20")
        itens = [
            {"produto_id": prod1["id"], "codigo": prod1["codigo"],
             "quantidade": 4,  "preco_unitario": prod1["preco_unitario"]},
            {"produto_id": prod2["id"], "codigo": prod2["codigo"],
             "quantidade": 2,  "preco_unitario": prod2["preco_unitario"]},
            {"produto_id": prod3["id"], "codigo": prod3["codigo"],
             "quantidade": 20, "preco_unitario": prod3["preco_unitario"]},
        ]
        total_esperado = (4 * prod1["preco_unitario"]
                        + 2 * prod2["preco_unitario"]
                        + 20 * prod3["preco_unitario"])
        pedido_id = db.criar_cotacao(
            cliente_nome="Industria Pesada Nordeste S/A",
            cliente_contato="compras@ipnordeste.com.br",
            itens=itens,
        )
        print(f"  Pedido criado com ID: {pedido_id}")
        print(f"  Total esperado: R$ {total_esperado:.2f}")
        for item in itens:
            print(f"    - {item['codigo']} x {item['quantidade']} "
                  f"= R$ {item['quantidade'] * item['preco_unitario']:.2f}")
        self.assertIsInstance(pedido_id, int)
        self.assertGreater(pedido_id, 0)

    def test_cotacao_lista_vazia_levanta_erro(self):
        """Lista de itens vazia deve levantar ValueError."""
        sep("TESTE: criar_cotacao — lista vazia (deve levantar ValueError)")
        with self.assertRaises(ValueError) as ctx:
            db.criar_cotacao("Cliente Teste", "contato@teste.com", [])
        print(f"  ValueError capturado: {ctx.exception}")

    def test_cotacao_quantidade_invalida(self):
        """Quantidade <= 0 deve levantar ValueError."""
        sep("TESTE: criar_cotacao — quantidade=0 (deve levantar ValueError)")
        prod = self._busca_produto("51210")
        with self.assertRaises(ValueError):
            db.criar_cotacao("Teste", "teste@x.com", [{
                "produto_id": prod["id"],
                "codigo": prod["codigo"],
                "quantidade": 0,
                "preco_unitario": prod["preco_unitario"],
            }])
        print("  ValueError capturado corretamente.")

    def test_status_padrao_aguardando_aprovacao(self):
        """Pedido criado deve ter status AGUARDANDO_APROVACAO."""
        import sqlite3 as _sq
        prod = self._busca_produto("7208-BE")
        itens = [{"produto_id": prod["id"], "codigo": prod["codigo"],
                  "quantidade": 1, "preco_unitario": prod["preco_unitario"]}]
        pedido_id = db.criar_cotacao("Teste Status", "status@teste.com", itens)

        conn = _sq.connect(db.DB_PATH)
        conn.row_factory = _sq.Row
        row = conn.execute(
            "SELECT status FROM pedidos WHERE id = ?", (pedido_id,)
        ).fetchone()
        conn.close()

        sep(f"TESTE: status do pedido #{pedido_id} deve ser AGUARDANDO_APROVACAO")
        print(f"  Status: {row['status']}")
        self.assertEqual(row["status"], "AGUARDANDO_APROVACAO")


# =============================================================================
#  CASO 5 — registrar_auditoria
# =============================================================================
class TestRegistrarAuditoria(unittest.TestCase):

    def test_registro_basico(self):
        """Deve inserir registro na tabela auditoria_ia sem erros."""
        sep("TESTE: registrar_auditoria(512, 128, 0.000384)")
        # Não deve levantar exceção
        db.registrar_auditoria(
            prompt_tokens=512,
            completion_tokens=128,
            custo_usd=0.000384,
            session_id="test-session-001"
        )
        print("  Registro inserido sem erros.")

        # Confirma que foi persistido
        import sqlite3 as _sq
        conn = _sq.connect(db.DB_PATH)
        row = conn.execute(
            "SELECT * FROM auditoria_ia WHERE session_id = 'test-session-001' "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
        self.assertIsNotNone(row)
        print(f"  Registro confirmado no banco — ID: {row[0]}")

    def test_registro_sem_session_id(self):
        """session_id é opcional — None deve ser aceito."""
        sep("TESTE: registrar_auditoria — sem session_id")
        db.registrar_auditoria(
            prompt_tokens=1024,
            completion_tokens=256,
            custo_usd=0.00192,
        )
        print("  Registro sem session_id inserido corretamente.")

    def test_multiplos_registros_acumulam(self):
        """Múltiplas chamadas devem criar múltiplas linhas."""
        import sqlite3 as _sq
        sep("TESTE: registrar_auditoria — acumulacao de registros")

        conn = _sq.connect(db.DB_PATH)
        antes = conn.execute("SELECT COUNT(*) FROM auditoria_ia").fetchone()[0]
        conn.close()

        for i in range(3):
            db.registrar_auditoria(100 * i, 50 * i, 0.0001 * i, f"acum-{i}")

        conn = _sq.connect(db.DB_PATH)
        depois = conn.execute("SELECT COUNT(*) FROM auditoria_ia").fetchone()[0]
        conn.close()

        print(f"  Registros antes: {antes} | depois: {depois} | delta: {depois - antes}")
        self.assertEqual(depois - antes, 3)


# =============================================================================
#  CASO 6 — resumo_banco (health-check)
# =============================================================================
class TestResumoBanco(unittest.TestCase):

    def test_resumo_retorna_stats(self):
        """resumo_banco() deve retornar dict com estatísticas válidas."""
        sep("TESTE: resumo_banco()")
        resumo = db.resumo_banco()
        print(f"  Total de produtos   : {resumo['total_produtos']}")
        print(f"  Total de pedidos    : {resumo['total_pedidos']}")
        print(f"  Total de auditorias : {resumo['total_auditorias']}")
        print(f"  Estoque total       : {resumo['estoque_total']} pecas")
        print(f"  Caminho do banco    : {resumo['db_path']}")
        self.assertEqual(resumo["total_produtos"], 15)
        self.assertGreaterEqual(resumo["total_pedidos"], 0)
        self.assertGreater(resumo["estoque_total"], 0)


class TestEnsureDbResilience(unittest.TestCase):

    def test_ensure_db_com_novo_arquivo_temporario(self):
        """ensure_db deve criar o schema e popular o catálogo em um banco novo."""
        import tempfile
        sep("TESTE: ensure_db em arquivo temporário")
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_db = pathlib.Path(tmpdir) / "sub" / "rash_temp.db"
            self.assertFalse(temp_db.exists())

            db.ensure_db(db_file=temp_db)
            self.assertTrue(temp_db.exists())

            import sqlite3 as _sq
            conn = _sq.connect(temp_db)
            try:
                count = conn.execute("SELECT COUNT(*) FROM produtos").fetchone()[0]
                self.assertEqual(count, 15)
                print(f"  Banco temporário criado e populado com {count} produtos.")
            finally:
                conn.close()


# =============================================================================
#  Runner customizado com sumário colorido
# =============================================================================

class ColorTextTestResult(unittest.TextTestResult):
    def addSuccess(self, test):
        super().addSuccess(test)
        if self.showAll:
            self.stream.write(f"{GREEN}[PASS]{RESET} ")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        if self.showAll:
            self.stream.write(f"{RED}[FAIL]{RESET} ")

    def addError(self, test, err):
        super().addError(test, err)
        if self.showAll:
            self.stream.write(f"{RED}[ERROR]{RESET} ")


class ColorTextTestRunner(unittest.TextTestRunner):
    resultclass = ColorTextTestResult


if __name__ == "__main__":
    print(f"\n{BOLD}{CYAN}{'=' * 60}{RESET}")
    print(f"{BOLD}{CYAN}  RashBot — Suite de Testes: src/database.py{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 60}{RESET}\n")

    loader = unittest.TestLoader()
    suite  = unittest.TestSuite()

    # Registra os casos de teste na ordem lógica
    for caso in [
        TestConsultarPorAplicacao,
        TestConsultarPorDimensoes,
        TestVerificarEstoquePreco,
        TestCriarCotacao,
        TestRegistrarAuditoria,
        TestResumoBanco,
        TestEnsureDbResilience,
    ]:
        suite.addTests(loader.loadTestsFromTestCase(caso))

    runner = ColorTextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)

    sep()
    total   = result.testsRun
    falhas  = len(result.failures) + len(result.errors)
    passou  = total - falhas

    print("\n  Resultado Final:")
    print(f"  {GREEN}Passou : {passou}/{total}{RESET}")
    if falhas:
        print(f"  {RED}Falhou : {falhas}/{total}{RESET}")
    else:
        print(f"  {GREEN}Todos os testes passaram!{RESET}")
    print()

    sys.exit(0 if result.wasSuccessful() else 1)
