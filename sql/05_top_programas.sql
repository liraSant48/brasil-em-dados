SELECT "Código Programa Orçamentário", "Nome Programa Orçamentário",
       sum("Valor Pago (R$)") AS valor_pago
FROM despesas WHERE periodo = DATE '2026-01-01'
GROUP BY "Código Programa Orçamentário", "Nome Programa Orçamentário"
ORDER BY valor_pago DESC NULLS LAST, "Código Programa Orçamentário", "Nome Programa Orçamentário"
LIMIT 10;
