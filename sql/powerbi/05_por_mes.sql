-- Visão alternativa. Não anexar nem somar à principal.
SELECT periodo, count(*) AS quantidade_registros,
       sum(valor_empenhado) AS valor_empenhado,
       sum(valor_liquidado) AS valor_liquidado,
       sum(valor_pago) AS valor_pago,
       sum(valor_restos_pagos) AS valor_restos_pagos
FROM despesas_bi
GROUP BY periodo
ORDER BY periodo;
