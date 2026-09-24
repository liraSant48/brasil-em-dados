-- Valores independentes: nunca somar estágios nem adicionar RAP ao pago do exercício.
SELECT periodo, count(*) AS registros,
       sum(valor_pago) AS valor_pago,
       sum(valor_empenhado) AS valor_empenhado,
       sum(valor_liquidado) AS valor_liquidado,
       sum(valor_restos_pagos) AS valor_restos_pagos,
       count(*) FILTER (WHERE valor_pago < 0) AS negativos_pago,
       count(*) FILTER (WHERE valor_empenhado < 0) AS negativos_empenhado,
       count(*) FILTER (WHERE valor_liquidado < 0) AS negativos_liquidado,
       count(*) FILTER (WHERE valor_restos_pagos < 0) AS negativos_restos_pagos,
       count(*) FILTER (WHERE valor_pago IS NULL) AS nulos_pago
FROM despesas_bi
GROUP BY periodo
ORDER BY periodo;
