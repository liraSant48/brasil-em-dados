-- Igualdade das 47 células não comprova identidade da despesa: nada é removido.
WITH grupos AS (
    SELECT * EXCLUDE (_linha_csv), count(*) AS ocorrencias
    FROM staging_despesas GROUP BY ALL
)
SELECT count(*) FILTER (WHERE ocorrencias > 1) AS grupos_identicos,
       coalesce(sum(ocorrencias - 1) FILTER (WHERE ocorrencias > 1), 0) AS repeticoes_excedentes
FROM grupos;
