-- A identidade da ação inclui seu programa.
SELECT codigo_programa, nome_programa, codigo_acao, nome_acao,
       sum(valor_pago) AS valor_pago
FROM despesas_bi
WHERE periodo BETWEEN CAST(? AS DATE) AND CAST(? AS DATE)
GROUP BY codigo_programa, nome_programa, codigo_acao, nome_acao
ORDER BY valor_pago DESC NULLS LAST, codigo_programa, codigo_acao, nome_acao
LIMIT 10;
