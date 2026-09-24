-- Abrange todos os órgãos no intervalo informado; códigos distintos permanecem separados.
SELECT codigo_programa, nome_programa, sum(valor_pago) AS valor_pago
FROM despesas_bi
WHERE periodo BETWEEN CAST(? AS DATE) AND CAST(? AS DATE)
GROUP BY codigo_programa, nome_programa
ORDER BY valor_pago DESC NULLS LAST, codigo_programa, nome_programa
LIMIT 10;
