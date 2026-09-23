-- Uma linha por registro de origem. Sem JOIN, DISTINCT, agregação ou filtro de órgão.
SELECT _linha_csv AS id_registro, periodo,
       "Código Órgão Superior" AS codigo_orgao_superior,
       "Nome Órgão Superior" AS nome_orgao_superior,
       "Código Função" AS codigo_funcao,
       "Nome Função" AS nome_funcao,
       "Código Programa Orçamentário" AS codigo_programa,
       "Nome Programa Orçamentário" AS nome_programa,
       "Código Ação" AS codigo_acao,
       "Nome Ação" AS nome_acao,
       "Código Grupo de Despesa" AS codigo_grupo_despesa,
       "Nome Grupo de Despesa" AS nome_grupo_despesa,
       "Valor Empenhado (R$)" AS valor_empenhado,
       "Valor Liquidado (R$)" AS valor_liquidado,
       "Valor Pago (R$)" AS valor_pago,
       "Valor Restos a Pagar Pagos (R$)" AS valor_restos_pagos,
       CASE WHEN "Código Programa Orçamentário" IN ('0905', '0906', '0907', '0908')
            THEN 'Programa específico de dívida'
            ELSE 'Demais programas'
       END AS classificacao_programa_divida
FROM despesas
ORDER BY id_registro;
