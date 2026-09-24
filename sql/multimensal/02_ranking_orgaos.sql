-- Parâmetros: início e fim inclusivos (DATE); ranking acumulado no intervalo.
SELECT codigo_orgao_superior, nome_orgao_superior, sum(valor_pago) AS valor_pago
FROM despesas_bi
WHERE periodo BETWEEN CAST(? AS DATE) AND CAST(? AS DATE)
GROUP BY codigo_orgao_superior, nome_orgao_superior
ORDER BY valor_pago DESC NULLS LAST, codigo_orgao_superior, nome_orgao_superior
LIMIT 10;
