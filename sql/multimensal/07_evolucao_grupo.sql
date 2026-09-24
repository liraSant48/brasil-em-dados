SELECT periodo, codigo_grupo_despesa, nome_grupo_despesa,
       sum(valor_empenhado) AS valor_empenhado,
       sum(valor_liquidado) AS valor_liquidado,
       sum(valor_pago) AS valor_pago,
       sum(valor_restos_pagos) AS valor_restos_pagos
FROM despesas_bi
WHERE periodo BETWEEN CAST(? AS DATE) AND CAST(? AS DATE)
GROUP BY periodo, codigo_grupo_despesa, nome_grupo_despesa
ORDER BY periodo, codigo_grupo_despesa, nome_grupo_despesa;
