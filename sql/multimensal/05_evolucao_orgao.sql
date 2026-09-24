-- Meses ausentes não são preenchidos com zero.
SELECT periodo, codigo_orgao_superior, nome_orgao_superior,
       sum(valor_pago) AS valor_pago
FROM despesas_bi
WHERE periodo BETWEEN CAST(? AS DATE) AND CAST(? AS DATE)
GROUP BY periodo, codigo_orgao_superior, nome_orgao_superior
ORDER BY periodo, codigo_orgao_superior, nome_orgao_superior;
