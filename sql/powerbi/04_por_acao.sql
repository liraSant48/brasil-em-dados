-- Ação contextualizada pelo programa; reúne todos os órgãos e grupos de despesa.
SELECT periodo, codigo_programa, nome_programa, codigo_acao, nome_acao,
       classificacao_programa_divida, count(*) AS quantidade_registros,
       sum(valor_empenhado) AS valor_empenhado,
       sum(valor_liquidado) AS valor_liquidado,
       sum(valor_pago) AS valor_pago,
       sum(valor_restos_pagos) AS valor_restos_pagos
FROM despesas_bi
GROUP BY periodo, codigo_programa, nome_programa, codigo_acao, nome_acao,
         classificacao_programa_divida
ORDER BY periodo, codigo_programa, codigo_acao, nome_programa, nome_acao;
