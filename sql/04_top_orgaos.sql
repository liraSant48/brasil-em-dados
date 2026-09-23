SELECT "Código Órgão Superior", "Nome Órgão Superior",
       sum("Valor Pago (R$)") AS valor_pago
FROM despesas WHERE periodo = DATE '2026-01-01'
GROUP BY "Código Órgão Superior", "Nome Órgão Superior"
ORDER BY valor_pago DESC NULLS LAST, "Código Órgão Superior", "Nome Órgão Superior"
LIMIT 10;
