# PRD — Agente de Vendas Técnicas | Rash Rolamentos Industriais

## 1. O Negócio e os Envolvidos
* **Empresa:** Rash Rolamentos Industriais (Distribuidora de rolamentos, mancais e vedações técnicas para o setor industrial).
* **Cliente que contratou (Dono/Operações):** Carlos Rash, Diretor Comercial.
  * *Preocupações do Carlos:* Medo de a IA inventar medidas/códigos incompatíveis, prometer preços fora da tabela de atacado, fechar pedidos sem validação de estoque real e emitir propostas formais sem revisão humana.
* **Produto:** *RashBot* — Assistente técnico de vendas e triagem para WhatsApp/Web.
* **Público-alvo:** Compradores de indústrias, mecânicos de manutenção e gerentes de fábrica que buscam peças por aplicação (ex: "preciso de rolamento para motor de alta rotação que suporte vibração") e não pelo código exato do catálogo.

---

## 2. O Problema
Compradores industriais perdem tempo tentando decifrar catálogos técnicos ou desistem de orçamentos pela demora no atendimento manual. A equipe da Rash gasta horas respondendo perguntas repetitivas de especificação técnica básica em vez de fechar contratos de alto valor.

---

## 3. Escopo da Versão 1 (MVP)

### O que ENTRA no escopo:
1. **Atendimento Consultivo:** Entender a aplicação mecânica descrita pelo cliente em linguagem natural e sugerir os modelos compatíveis.
2. **Consulta Determinística:** Estoque, medidas (diâmetro interno, externo, largura) e preços consultados diretamente em banco de dados fixo (nada inventado pelo modelo).
3. **Fluxo Human-in-the-Loop:** Quando o cliente solicita a cotação formal, o agente resume o pedido e coloca o status em "Aguardando Aprovação". A emissão da proposta final exige o clique/aprovação de um vendedor humano.
4. **Governança e Custo:** Registro de tokens/custo por atendimento e mascaramento de dados sensíveis de clientes (LGPD).

### O que FICA DE FORA da primeira versão:
* Integração direta com gateway de pagamento real.
* Emissão automática de Nota Fiscal eletrônica.
* Integração direta com ERP legado da fábrica.

---

## 4. Métricas de Sucesso
* 100% de precisão nos preços e códigos de peças informados (zero alucinação de catálogo).
* Redução do tempo de montagem de orçamento técnico de 4 horas para menos de 5 minutos.
* Zero propostas enviadas ao cliente sem a trava de aprovação humana.