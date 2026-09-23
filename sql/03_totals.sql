-- Medidas independentes: NÃO somar estágios nem adicionar restos a pagar ao pago.
SELECT count(*) AS registros,
       sum("Valor Empenhado (R$)") AS empenhado,
       sum("Valor Liquidado (R$)") AS liquidado,
       sum("Valor Pago (R$)") AS pago,
       sum("Valor Restos a Pagar Inscritos (R$)") AS restos_inscritos,
       sum("Valor Restos a Pagar Cancelado (R$)") AS restos_cancelados,
       sum("Valor Restos a Pagar Pagos (R$)") AS restos_pagos
FROM despesas WHERE periodo = DATE '2026-01-01';
