SELECT periodo, codigo_programa, nome_programa, sum(valor_pago) AS valor_pago
FROM despesas_bi
WHERE periodo BETWEEN CAST(? AS DATE) AND CAST(? AS DATE)
GROUP BY periodo, codigo_programa, nome_programa
ORDER BY periodo, codigo_programa, nome_programa;
