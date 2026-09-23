-- Associação orçamentária, não explicação causal dos pagamentos.
SELECT "Código Programa Orçamentário", "Nome Programa Orçamentário",
       "Código Ação", "Nome Ação", sum("Valor Pago (R$)") AS valor_pago
FROM despesas WHERE periodo = DATE '2026-01-01'
GROUP BY "Código Programa Orçamentário", "Nome Programa Orçamentário", "Código Ação", "Nome Ação"
ORDER BY valor_pago DESC NULLS LAST, "Código Programa Orçamentário", "Código Ação",
         "Nome Programa Orçamentário", "Nome Ação"
LIMIT 10;
