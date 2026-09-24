-- Quatro medidas independentes no intervalo selecionado; sem somar estágios.
SELECT count(*) AS registros,
       sum(valor_empenhado) AS valor_empenhado,
       sum(valor_liquidado) AS valor_liquidado,
       sum(valor_pago) AS valor_pago,
       sum(valor_restos_pagos) AS valor_restos_pagos
FROM despesas_bi
WHERE periodo BETWEEN CAST(? AS DATE) AND CAST(? AS DATE);
