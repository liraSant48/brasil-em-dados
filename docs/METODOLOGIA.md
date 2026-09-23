# Metodologia e limites de interpretação

## Fonte, período e unidade de análise

Fonte declarada: [Portal da Transparência — Despesas: Execução](https://portaldatransparencia.gov.br/download-de-dados/despesas-execucao).

O recorte inicial utiliza janeiro de 2026: `202601_Despesas.zip`, membro `202601_Despesas.csv`, 47 colunas e 48.519 registros. A base carregada contém 36 códigos de órgão superior e 179 códigos de programa. Não há filtro exclusivo para o Ministério da Fazenda.

O hash do ZIP processado é `67b6889a213eff3c733dacda454aae104e38358c058ab871469e12e9b342b8af`. Ele identifica este arquivo local, mas não autentica sua origem. **A integridade interna dos resultados não comprova, isoladamente, a completude de toda a execução federal.** Não houve conciliação externa com outro demonstrativo.

## Tratamento

- Todos os campos entram na staging como texto, incluindo códigos com zeros à esquerda. O contrato de cabeçalho usa os nomes reais, inclusive grafias originais.
- O CSV é lido diretamente do ZIP, sem alteração ou extração permanente, com separador `;` e cp1252. A codificação foi estimada na inspeção.
- Na tabela analítica, valores como `-1.234,56` tornam-se `-1234.56` em `DECIMAL(20,2)`, sem conversão intermediária para float. Campos monetários vazios tornam-se NULL; zeros permanecem zero.
- Formatos inválidos, precisão excedida e mais de duas casas não são corrigidos silenciosamente: a carga falha e a transação é revertida.
- Não se eliminam registros aparentemente duplicados. Comparar as 47 células é um diagnóstico, não uma definição de chave de negócio.
- `periodo = 2026-01-01` representa o mês, não uma data diária de pagamento. Não há evolução temporal simulada.

## Medidas financeiras

| Medida | Tratamento na análise |
| --- | --- |
| Empenhado | Coluna e medida próprias |
| Liquidado | Coluna e medida próprias |
| Pago | `Valor Pago (R$)` / `Total Pago`: pagamentos do exercício registrados no recorte |
| Restos a pagar pagos | Coluna e medida próprias, separadas dos pagamentos do exercício |
| Restos inscritos/cancelados | Mantidos no DuckDB e nas consultas de validação; não adicionados ao pago |

Empenho, liquidação e pagamento são estágios distintos, não despesas adicionais a somar entre si. Tampouco se adicionam pagamentos de restos ao indicador denominado Total Pago. Os nomes descrevem a medida do arquivo, sem inferir finalidade ou beneficiário final.

O total pago é **R$ 414.272.570.651,27**. A soma de todos os programas, sem limite Top 10, é idêntica, com diferença **R$ 0,00**. Pagamentos de restos a pagar totalizam separadamente **R$ 147.955.708.343,19**.

## Dívida e classificações

O auxiliar de programa identifica exclusivamente:

- `0905`: serviço da dívida interna — juros e amortizações;
- `0906`: serviço da dívida externa — juros e amortizações;
- `0907`: refinanciamento da dívida interna;
- `0908`: refinanciamento da dívida externa.

Esses programas permanecem no total. A classificação segue os códigos de operações especiais dos [anexos da LOA 2026](https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2026/lei/anexos/l15346-26-anexo-volume2.pdf), conferidos na etapa anterior.

O grupo de despesa é uma classificação independente. `Demais programas` não significa ausência de despesa relacionada à dívida: o recorte contém R$ 1.098.407,39 no grupo 6, programa 0909, ação 00Q3. Não se classifica todo o programa 0909 como dívida.

## Apresentação e filtros

Os cartões e eixos utilizam unidades automáticas nativas, conforme a magnitude; as projeções não dividem ou transformam os valores. Rótulos de barras, tooltips monetários e tabela de detalhe usam reais com duas casas, sem escala fixa em bilhões. Assim, um valor pequeno não é formatado pelo arquivo como zero por uma divisão por bilhões. A seleção final do sufixo e a renderização das unidades automáticas precisam ser verificadas no Desktop.

O identificador do programa é seu código textual. Foram encontrados 14 nomes associados a códigos distintos; usar somente o nome agruparia programas diferentes. O eixo e o filtro usam código, enquanto o nome aparece no tooltip e na tabela de detalhe.

Selecionar uma barra produz um contexto de seleção. **Realce cruzado** destaca a parcela selecionada, mantendo outras referências visíveis; **filtragem cruzada** restringe os registros de destino. A página refinada define filtragem entre barras, cartões, outro gráfico e detalhe; cliques nas barras não reconfiguram os menus dos filtros. As segmentações continuam filtrando os visuais.

Havia uma seleção salva para Advocacia-Geral da União, removida apenas do estado inicial da página após backup. O SQL confirmou 137 registros e R$ 55.693.928,70 nesse recorte. Isso não comprova a causa do comportamento “Em branco”, que não foi reproduzido no Desktop. Contextos sem registros ou valores nulos devem continuar visíveis como tais: não se adicionou COALESCE nem se alteraram medidas para simular zero.

## Qualidade e interpretação

Na carga validada não foram encontrados valores monetários vazios/inválidos nem registros integralmente idênticos. Foram preservados 53 valores pagos negativos, 451 valores negativos de restos inscritos e um valor negativo de restos pagos. Sua causa não foi inferida.

Há rótulos aparentemente truncados na fonte. O arquivo não oferece uma explicação causal dos gastos, nem permite concluir eficácia, irregularidade ou impacto econômico/político. Classificações orçamentárias não equivalem a causalidade.

## Atualização responsável

A carga atual aceita somente `2026/01` e substitui um único snapshot. Para outro mês, revise validação de período, consultas com data fixa, documentação e título do dashboard. Para vários meses, projete uma chave composta de origem/registro e uma carga incremental antes de anexar dados. Reexecute todos os testes, reconcilie as medidas e valide filtros e formatação no Desktop.
