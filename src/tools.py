"""
src/tools.py
============
Ferramentas LangChain para o RashBot.

Cada ferramenta é um wrapper @tool em torno das funções de
src/database.py, com schemas Pydantic explícitos para que o
LLM saiba EXATAMENTE quais parâmetros passar.

Princípio central (PRD §3.2):
  O modelo NUNCA inventa dados. Ele chama estas ferramentas e
  apresenta ao cliente apenas o que o banco retornar.
"""

import json
import logging
from typing import Optional

from langchain_core.tools import tool

import database as db

logger = logging.getLogger(__name__)


# ── Helpers de formatação ─────────────────────────────────────────────────────

def _fmt_produto(p: dict) -> str:
    """Formata um produto como texto legível para o LLM."""
    estoque_str = f"{p['estoque_qtd']} un." if p["estoque_qtd"] > 0 else "SEM ESTOQUE"
    return (
        f"• Código: {p['codigo']}\n"
        f"  Tipo: {p['tipo']}\n"
        f"  Dimensões: ø{p['diametro_interno_mm']}mm (interno) × "
        f"ø{p['diametro_externo_mm']}mm (externo) × {p['largura_mm']}mm (largura)\n"
        f"  Aplicação: {p['aplicacao_recomendada']}\n"
        f"  Preço unitário: R$ {p['preco_unitario']:.2f}\n"
        f"  Estoque: {estoque_str}"
    )


# ── Ferramentas ───────────────────────────────────────────────────────────────

@tool
def tool_consultar_aplicacao(termo: str) -> str:
    """
    Busca rolamentos e peças industriais compatíveis com uma descrição
    de aplicação mecânica em linguagem natural.

    Use esta ferramenta quando o cliente descrever:
    - O equipamento onde o rolamento será instalado
      (ex: 'motor elétrico', 'bomba centrífuga', 'britador de mandíbula')
    - A condição de operação (ex: 'alta rotação', 'carga pesada', 'vibração')
    - O setor industrial (ex: 'mineração', 'agricultura', 'siderurgia')

    NÃO use esta ferramenta para buscar por código de peça (ex: '6204-2RSH').
    Para busca por código, use tool_verificar_estoque_preco.

    Args:
        termo: Descrição da aplicação mecânica ou condição de trabalho.
               Pode conter múltiplas palavras (ex: 'motor eletrico bomba').

    Returns:
        Lista formatada dos rolamentos compatíveis com preço e estoque,
        ou mensagem informando que nenhum produto foi encontrado.
    """
    logger.info("tool_consultar_aplicacao(termo=%r)", termo)

    try:
        produtos = db.consultar_produtos_por_aplicacao(termo)
    except Exception as exc:
        logger.error("Erro em tool_consultar_aplicacao: %s", exc)
        return (
            "Desculpe, ocorreu um erro interno ao consultar o catálogo. "
            "Por favor, tente novamente em instantes."
        )

    if not produtos:
        return (
            f"Não encontrei rolamentos no catálogo para a aplicação '{termo}'.\n"
            "Sugestões:\n"
            "  • Tente descrever o equipamento com outras palavras\n"
            "  • Informe as dimensões (diâmetro interno × externo × largura em mm)\n"
            "  • Entre em contato com nossa equipe técnica para consulta especializada"
        )

    linhas = [f"Encontrei {len(produtos)} rolamento(s) para '{termo}':\n"]
    for p in produtos:
        linhas.append(_fmt_produto(p))
    return "\n".join(linhas)


@tool
def tool_consultar_dimensoes(
    diametro_interno_mm: float,
    diametro_externo_mm: float,
    largura_mm: Optional[float] = None,
    tolerancia_mm: float = 1.0,
) -> str:
    """
    Busca rolamentos compatíveis pelas dimensões em milímetros.

    Use esta ferramenta quando o cliente fornecer as medidas do rolamento,
    seja para substituição de peça desgastada ou especificação técnica.
    As buscas aceitam uma tolerância configurável (padrão ±1 mm).

    Args:
        diametro_interno_mm: Diâmetro interno (furo) em milímetros. Obrigatório.
        diametro_externo_mm: Diâmetro externo em milímetros. Obrigatório.
        largura_mm:          Largura/espessura do rolamento em mm. Opcional —
                             se omitida, não filtra por largura.
        tolerancia_mm:       Margem de tolerância por dimensão em mm (padrão 1.0).
                             Use 2.0 ou 3.0 se a busca exata não retornar resultados.

    Returns:
        Lista dos rolamentos compatíveis com dimensões, preço e estoque,
        ordenada por proximidade dimensional.
    """
    logger.info(
        "tool_consultar_dimensoes(di=%.1f, de=%.1f, l=%s, tol=%.1f)",
        diametro_interno_mm, diametro_externo_mm, largura_mm, tolerancia_mm
    )

    try:
        produtos = db.consultar_por_dimensoes(
            diametro_interno=diametro_interno_mm,
            diametro_externo=diametro_externo_mm,
            largura=largura_mm,
            tolerancia_mm=tolerancia_mm,
        )
    except Exception as exc:
        logger.error("Erro em tool_consultar_dimensoes: %s", exc)
        return (
            "Desculpe, ocorreu um erro ao consultar as dimensões. "
            "Por favor, tente novamente."
        )

    dim_str = (
        f"ø{diametro_interno_mm}mm × ø{diametro_externo_mm}mm"
        + (f" × {largura_mm}mm" if largura_mm else "")
    )

    if not produtos:
        return (
            f"Não encontrei rolamentos com dimensões próximas de {dim_str} "
            f"(tolerância ±{tolerancia_mm}mm).\n"
            "Sugestões:\n"
            "  • Aumente a tolerância (ex: tolerancia_mm=3.0)\n"
            "  • Verifique se as medidas foram aferidas corretamente\n"
            "  • Consulte nossa equipe para alternativas compatíveis"
        )

    linhas = [f"Encontrei {len(produtos)} rolamento(s) próximo(s) de {dim_str}:\n"]
    for p in produtos:
        linhas.append(_fmt_produto(p))
    return "\n".join(linhas)


@tool
def tool_verificar_estoque_preco(codigo_produto: str) -> str:
    """
    Verifica estoque disponível, preço unitário e especificações completas
    de um rolamento pelo código ISO/DIN (ex: '6204-2RSH', '22212-E').

    Use esta ferramenta quando:
    - O cliente fornecer um código de peça específico
    - Você precisar confirmar preço e disponibilidade antes de gerar cotação
    - O cliente perguntar se determinada peça está em estoque

    IMPORTANTE: Sempre use esta ferramenta para confirmar preço e
    disponibilidade ANTES de chamar tool_gerar_cotacao.

    Args:
        codigo_produto: Código ISO/DIN do rolamento. A busca é
                        case-insensitive (ex: '6204-2rsh' == '6204-2RSH').

    Returns:
        Especificações completas do produto com preço e estoque atuais,
        ou mensagem informando que o código não foi encontrado.
    """
    logger.info("tool_verificar_estoque_preco(codigo=%r)", codigo_produto)

    try:
        produto = db.verificar_estoque_e_preco(codigo_produto)
    except Exception as exc:
        logger.error("Erro em tool_verificar_estoque_preco: %s", exc)
        return (
            "Desculpe, ocorreu um erro ao consultar o produto. "
            "Por favor, tente novamente."
        )

    if not produto:
        return (
            f"O código '{codigo_produto}' não foi encontrado no nosso catálogo.\n"
            "Verifique se o código está correto. Você pode buscar por aplicação "
            "ou dimensões usando as outras ferramentas disponíveis."
        )

    disponibilidade = (
        f"✅ Em estoque: {produto['estoque_qtd']} unidades"
        if produto["disponivel"]
        else "❌ Produto sem estoque no momento"
    )

    return (
        f"📦 Produto encontrado:\n\n"
        f"{_fmt_produto(produto)}\n\n"
        f"Status: {disponibilidade}"
    )


@tool
def tool_gerar_cotacao(
    cliente_nome: str,
    cliente_contato: str,
    itens: str,
) -> str:
    """
    Gera uma cotação formal e salva no banco com status 'AGUARDANDO_APROVACAO'.

    ⚠️ REGRAS OBRIGATÓRIAS antes de chamar esta ferramenta:
    1. Você DEVE ter confirmado nome completo do cliente.
    2. Você DEVE ter confirmado o contato do cliente (WhatsApp ou e-mail).
    3. Você DEVE ter verificado preço e estoque de CADA item via
       tool_verificar_estoque_preco antes de incluir na cotação.
    4. Você DEVE confirmar os itens e quantidades com o cliente antes
       de registrar.

    A cotação gerada fica com status 'AGUARDANDO_APROVACAO'. Isso significa
    que um vendedor da Rash Rolamentos irá revisá-la antes de qualquer
    emissão de proposta formal ao cliente.

    Args:
        cliente_nome:    Nome completo do cliente ou empresa.
        cliente_contato: WhatsApp (com DDD) ou e-mail do cliente.
        itens:           JSON string com a lista de itens. Cada item deve ter:
                         - "produto_id": int  (ID do produto no catálogo)
                         - "codigo":     str  (código para referência)
                         - "quantidade": int  (quantidade solicitada)
                         - "preco_unitario": float (preço confirmado via ferramenta)
                         Exemplo:
                         '[{"produto_id": 2, "codigo": "6204-2RSH",
                            "quantidade": 10, "preco_unitario": 22.90}]'

    Returns:
        Confirmação da cotação criada com número do pedido e próximos passos,
        ou mensagem de erro em caso de falha de validação.
    """
    logger.info(
        "tool_gerar_cotacao(cliente=%r, contato=%r, itens_raw=%r)",
        cliente_nome, cliente_contato, itens
    )

    # ── Validações básicas do caller ─────────────────────────────────────────
    if not cliente_nome or not cliente_nome.strip():
        return (
            "❌ Nome do cliente não informado. Por favor, peça o nome completo "
            "do cliente ou empresa antes de gerar a cotação."
        )
    if not cliente_contato or not cliente_contato.strip():
        return (
            "❌ Contato do cliente não informado. Por favor, peça o WhatsApp "
            "(com DDD) ou e-mail antes de gerar a cotação."
        )

    # ── Parse do JSON de itens ───────────────────────────────────────────────
    try:
        lista_itens: list[dict] = json.loads(itens)
    except json.JSONDecodeError as exc:
        logger.error("JSON inválido em tool_gerar_cotacao: %s", exc)
        return (
            f"❌ Formato de itens inválido. O parâmetro 'itens' deve ser um "
            f"JSON válido. Erro: {exc}"
        )

    if not isinstance(lista_itens, list) or len(lista_itens) == 0:
        return "❌ A lista de itens está vazia. Inclua ao menos um produto."

    # ── Validação de campos obrigatórios por item ────────────────────────────
    for i, item in enumerate(lista_itens):
        for campo in ("produto_id", "quantidade", "preco_unitario"):
            if campo not in item:
                return (
                    f"❌ Item {i+1} está sem o campo obrigatório '{campo}'. "
                    "Verifique os dados e tente novamente."
                )
        if item["quantidade"] <= 0:
            return f"❌ Item {i+1}: quantidade deve ser maior que zero."

    # ── Criação da cotação ───────────────────────────────────────────────────
    try:
        pedido_id = db.criar_cotacao(
            cliente_nome=cliente_nome.strip(),
            cliente_contato=cliente_contato.strip(),
            itens=lista_itens,
        )
    except Exception as exc:
        logger.error("Erro ao criar cotação: %s", exc)
        return (
            "❌ Ocorreu um erro ao salvar a cotação. "
            f"Detalhe técnico: {exc}\n"
            "Por favor, tente novamente ou contate o suporte."
        )

    # ── Resumo do pedido para o cliente ─────────────────────────────────────
    total = sum(i["quantidade"] * i["preco_unitario"] for i in lista_itens)
    linhas_itens = []
    for item in lista_itens:
        cod   = item.get("codigo", f"ID:{item['produto_id']}")
        subtotal = item["quantidade"] * item["preco_unitario"]
        linhas_itens.append(
            f"  • {cod}: {item['quantidade']} un. × "
            f"R$ {item['preco_unitario']:.2f} = R$ {subtotal:.2f}"
        )

    return (
        f"✅ Cotação #{pedido_id} registrada com sucesso!\n\n"
        f"Cliente: {cliente_nome}\n"
        f"Contato: {cliente_contato}\n\n"
        f"Itens:\n" + "\n".join(linhas_itens) + "\n\n"
        f"Total: R$ {total:.2f}\n\n"
        f"📋 Status: AGUARDANDO APROVAÇÃO\n"
        f"Nossa equipe comercial irá revisar a cotação e entrar em contato "
        f"com você em breve para confirmação e envio da proposta formal.\n"
        f"Número da cotação para acompanhamento: #{pedido_id}"
    )


# ── Registro centralizado das ferramentas ─────────────────────────────────────
# Importado por agent.py
TOOLS = [
    tool_consultar_aplicacao,
    tool_consultar_dimensoes,
    tool_verificar_estoque_preco,
    tool_gerar_cotacao,
]
