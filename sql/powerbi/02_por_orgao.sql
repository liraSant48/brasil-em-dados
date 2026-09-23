-- Visão alternativa. Não somar à tabela principal nem relacionar como dimensão.
SELECT periodo, codigo_orgao_superior, nome_orgao_superior,
       count(*) AS quantidade_registros,
       sum(valor_empenhado) AS valor_empenhado,
       sum(valor_liquidado) AS valor_liquidado,
       sum(valor_pago) AS valor_pago,
       sum(valor_restos_pagos) AS valor_restos_pagos
FROM despesas_bi
GROUP BY periodo, codigo_orgao_superior, nome_orgao_superior
ORDER BY periodo, codigo_orgao_superior, nome_orgao_superior;
