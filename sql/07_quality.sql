-- UNPIVOT INCLUDE NULLS mantém vazios convertidos para NULL na contagem.
WITH valores AS (
    SELECT medida, valor FROM despesas
    UNPIVOT INCLUDE NULLS (valor FOR medida IN (
        "Valor Empenhado (R$)", "Valor Liquidado (R$)", "Valor Pago (R$)",
        "Valor Restos a Pagar Inscritos (R$)", "Valor Restos a Pagar Cancelado (R$)",
        "Valor Restos a Pagar Pagos (R$)"
    ))
)
SELECT medida, count(*) AS registros,
       count(*) FILTER (WHERE valor IS NULL) AS vazios,
       count(*) FILTER (WHERE valor = 0) AS zeros,
       count(*) FILTER (WHERE valor < 0) AS negativos
FROM valores GROUP BY medida ORDER BY medida;
