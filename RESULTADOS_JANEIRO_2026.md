# Resultados — janeiro de 2026

Resultados calculados sobre todos os registros do arquivo local, não sobre a amostra.

- Fonte declarada: https://portaldatransparencia.gov.br/download-de-dados/despesas-execucao
- Entrada: data/raw/202601_Despesas.zip, membro 202601_Despesas.csv.
- SHA-256: 67b6889a213eff3c733dacda454aae104e38358c058ab871469e12e9b342b8af.
- Período validado em todas as linhas: 2026/01.
- 47 colunas originais; 48.519 registros; cp1252; separador ponto e vírgula.
- Duas cargas completas concluídas, com contagens e resultados das consultas idênticos.
- Valores monetários abaixo em reais, com ponto decimal e sem separador de milhares.
- Seis somas e contagens não nulas reconciliadas entre Decimal Python e SQL.

## 02_count.sql

| linhas_staging | linhas_analiticas | identificadores_distintos | periodo_minimo | periodo_maximo |
| --- | --- | --- | --- | --- |
| 48519 | 48519 | 48519 | 2026-01-01 | 2026-01-01 |

## 03_totals.sql

| registros | empenhado | liquidado | pago | restos_inscritos | restos_cancelados | restos_pagos |
| --- | --- | --- | --- | --- | --- | --- |
| 48519 | 1707316089907.31 | 509934472511.29 | 414272570651.27 | 145958220.44 | 2321447466.48 | 147955708343.19 |

## 04_top_orgaos.sql

| Código Órgão Superior | Nome Órgão Superior | valor_pago |
| --- | --- | --- |
| 25000 | Ministério da Fazenda | 354711908288.51 |
| 33000 | Ministério da Previdência Social | 23784481368.55 |
| 55000 | Ministério do Desenvolvimento e Assistência | 13329634635.69 |
| 36000 | Ministério da Saúde | 9978145385.61 |
| 26000 | Ministério da Educação | 4381774573.14 |
| 40000 | Ministério do Trabalho e Emprego | 2559968947.92 |
| 52000 | Ministério da Defesa | 1984162013.19 |
| 53000 | Ministério da Integração e do Desenvolvime | 1349058151.52 |
| 32000 | Ministério de Minas e Energia | 591527473.70 |
| 56000 | Ministério das Cidades | 551711257.21 |

## 05_top_programas.sql

| Código Programa Orçamentário | Nome Programa Orçamentário | valor_pago |
| --- | --- | --- |
| 0907 | OPERACOES ESPECIAIS: REFINANCIAMENTO DA DIVIDA INTERNA | 228275925137.08 |
| 0905 | OPERACOES ESPECIAIS: SERVICO DA DIVIDA INTERNA (JUROS EAMORTIZACOES) | 97384007373.28 |
| 0903 | OPERACOES ESPECIAIS: TRANSFERENCIAS CONSTITUCIONAIS E AS DECORRENTES DE LEGISLACAO ESPECIFICA | 25864384397.24 |
| 2314 | PREVIDENCIA SOCIAL: PROMOCAO, GARANTIA DE DIREITOS E CIDADANIA | 18607632496.13 |
| 5128 | BOLSA FAMILIA: PROTECAO SOCIAL POR MEIO DA TRANSFERENCIA DE RENDA E DA ARTICULACAO DE POLITICAS PUBLICAS | 13050942400.00 |
| 5118 | ATENCAO ESPECIALIZADA A SAUDE | 5407677391.14 |
| 5131 | PROTECAO SOCIAL PELO SISTEMA UNICO DE ASSISTENCIA SOCIAL (SUAS) | 5183697046.24 |
| 0902 | OPERACOES ESPECIAIS: FINANCIAMENTOS COM RETORNO | 4724888185.19 |
| 5111 | EDUCACAO BASICA DEMOCRATICA, COM QUALIDADE E EQUIDADE | 3472524673.57 |
| 0032 | PROGRAMA DE GESTAO E MANUTENCAO DO PODER EXECUTIVO | 3298499676.60 |

## 06_top_acoes.sql

| Código Programa Orçamentário | Nome Programa Orçamentário | Código Ação | Nome Ação | valor_pago |
| --- | --- | --- | --- | --- |
| 0907 | OPERACOES ESPECIAIS: REFINANCIAMENTO DA DIVIDA INTERNA | 0365 | REFINANCIAMENTO DA DIVIDA PUBLICA MOBILIARIA FEDERAL INTERNA | 228275925137.08 |
| 0905 | OPERACOES ESPECIAIS: SERVICO DA DIVIDA INTERNA (JUROS EAMORTIZACOES) | 0455 | SERVICOS DA DIVIDA PUBLICA FEDERAL INTERNA | 97384007373.28 |
| 2314 | PREVIDENCIA SOCIAL: PROMOCAO, GARANTIA DE DIREITOS E CIDADANIA | 00SJ | BENEFICIOS PREVIDENCIARIOS | 18590316706.12 |
| 5128 | BOLSA FAMILIA: PROTECAO SOCIAL POR MEIO DA TRANSFERENCIA DE RENDA E DA ARTICULACAO DE POLITICAS PUBLICAS | 8442 | TRANSFERENCIA DIRETA E CONDICIONADA DE RENDA AS FAMILIAS BENEFICIARIAS DO PROGRAMA BOLSA FAMILIA | 13050942400.00 |
| 0903 | OPERACOES ESPECIAIS: TRANSFERENCIAS CONSTITUCIONAIS E AS DECORRENTES DE LEGISLACAO ESPECIFICA | 0045 | TRANSFERENCIA AO FUNDO DE PARTICIPACAO DOS MUNICIPIOS - FPM (CF, ART.159) | 9963169958.46 |
| 0903 | OPERACOES ESPECIAIS: TRANSFERENCIAS CONSTITUCIONAIS E AS DECORRENTES DE LEGISLACAO ESPECIFICA | 0044 | TRANSFERENCIA AO FUNDO DE PARTICIPACAO DOS ESTADOS E DO DISTRITO FEDERAL - FPE (CF, ART.159) | 9520362277.64 |
| 5118 | ATENCAO ESPECIALIZADA A SAUDE | 8585 | ATENCAO A SAUDE DA POPULACAO PARA PROCEDIMENTOS EM MEDIA E ALTA COMPLEXIDADE | 5249381752.76 |
| 0903 | OPERACOES ESPECIAIS: TRANSFERENCIAS CONSTITUCIONAIS E AS DECORRENTES DE LEGISLACAO ESPECIFICA | 0C33 | TRANSFERENCIA AO FUNDO DE MANUTENCAO E DESENVOLVIMENTO DA EDUCACAO BASICA E DE VALORIZACAO DOS PROFISSIONAIS DA EDUCACAO - FUNDEB | 4935878192.88 |
| 5111 | EDUCACAO BASICA DEMOCRATICA, COM QUALIDADE E EQUIDADE | 00SB | COMPLEMENTACAO DA UNIAO AO FUNDO DE MANUTENCAO E DESENVOLVIMENTO DA EDUCACAO BASICA E DE VALORIZACAO DOS PROFISSIONAIS DA EDUCACAO - FUNDEB | 3462014287.45 |
| 0906 | OPERACOES ESPECIAIS: SERVICO DA DIVIDA EXTERNA (JUROS EAMORTIZACOES) | 0425 | SERVICOS DA DIVIDA PUBLICA FEDERAL EXTERNA | 3183569998.33 |

## 07_quality.sql

| medida | registros | vazios | zeros | negativos |
| --- | --- | --- | --- | --- |
| Valor Empenhado (R$) | 48519 | 0 | 23189 | 0 |
| Valor Liquidado (R$) | 48519 | 0 | 34479 | 0 |
| Valor Pago (R$) | 48519 | 0 | 40657 | 53 |
| Valor Restos a Pagar Cancelado (R$) | 48519 | 0 | 47121 | 0 |
| Valor Restos a Pagar Inscritos (R$) | 48519 | 0 | 48052 | 451 |
| Valor Restos a Pagar Pagos (R$) | 48519 | 0 | 13181 | 1 |

## 08_duplicates.sql

| grupos_identicos | repeticoes_excedentes |
| --- | --- |
| 0 | 0 |

## 09_dimensions.sql

| orgao_vazio | programa_vazio | acao_vazia |
| --- | --- | --- |
| 0 | 0 | 0 |
