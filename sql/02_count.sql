SELECT (SELECT count(*) FROM staging_despesas) AS linhas_staging,
       count(*) AS linhas_analiticas,
       count(DISTINCT _linha_csv) AS identificadores_distintos,
       min(periodo) AS periodo_minimo, max(periodo) AS periodo_maximo
FROM despesas;
