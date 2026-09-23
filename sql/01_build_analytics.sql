-- Conversão estrita: não arredondar silenciosamente nem transformar inválidos em NULL.
CREATE OR REPLACE MACRO br_decimal(value) AS (
    CASE
        WHEN trim(value) = '' THEN NULL::DECIMAL(20,2)
        WHEN regexp_full_match(trim(value), '[+-]?([0-9]+|[0-9]{1,3}(\.[0-9]{3})+)(,[0-9]{1,2})?')
        THEN CAST(replace(replace(trim(value), '.', ''), ',', '.') AS DECIMAL(20,2))
        ELSE error('Valor monetário brasileiro inválido: ' || value)
    END
);

-- Mantém nomes originais, dimensões e códigos; uma linha analítica por linha staging.
CREATE OR REPLACE TABLE despesas AS
SELECT * REPLACE (
    br_decimal("Valor Empenhado (R$)") AS "Valor Empenhado (R$)",
    br_decimal("Valor Liquidado (R$)") AS "Valor Liquidado (R$)",
    br_decimal("Valor Pago (R$)") AS "Valor Pago (R$)",
    br_decimal("Valor Restos a Pagar Inscritos (R$)") AS "Valor Restos a Pagar Inscritos (R$)",
    br_decimal("Valor Restos a Pagar Cancelado (R$)") AS "Valor Restos a Pagar Cancelado (R$)",
    br_decimal("Valor Restos a Pagar Pagos (R$)") AS "Valor Restos a Pagar Pagos (R$)"
), strptime("Ano e mês do lançamento", '%Y/%m')::DATE AS periodo
FROM staging_despesas;
