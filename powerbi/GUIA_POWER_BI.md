# Importação dos dados — Missão 05

> Este guia documenta a preparação/importação dos CSVs. O relatório já foi construído e refinado posteriormente; veja [o estado visual atual](../docs/REFINAMENTO.md). As regras de tipos e reconciliação abaixo continuam aplicáveis.

## Arquivo principal

Importe `data/processed/despesas_bi.csv`. Ele contém 48.519 registros de janeiro de 2026, com uma linha por registro do DuckDB, e 17 colunas. Não há JOIN, DISTINCT, remoção de duplicatas, filtro de órgão ou agregação na consulta principal. A exportação inclui todos os períodos presentes no banco; nesta carga existe somente janeiro de 2026.

`id_registro` corresponde a `_linha_csv`, identificador técnico do registro de origem, não uma chave de negócio. É único neste snapshot; não deve ser usado como chave global ao combinar outros arquivos ou meses. Registros com dimensões e valores iguais continuam separados.

| Colunas | Tipo na importação |
| --- | --- |
| `id_registro` | Número inteiro; não resumir |
| `periodo` | Data, formato de entrada `yyyy-MM-dd` |
| `codigo_orgao_superior`, `codigo_funcao`, `codigo_programa`, `codigo_acao`, `codigo_grupo_despesa` | Texto; não resumir |
| `nome_orgao_superior`, `nome_funcao`, `nome_programa`, `nome_acao`, `nome_grupo_despesa` | Texto |
| `classificacao_programa_divida` | Texto |
| `valor_empenhado`, `valor_liquidado`, `valor_pago`, `valor_restos_pagos` | Número decimal fixo; cultura de leitura `en-US` |

`periodo` usa o primeiro dia do mês como representação mensal; não é a data diária do pagamento. Cada campo de código/nome foi selecionado explicitamente do esquema real, sem corrigir rótulos da fonte. A tabela permite combinar filtros de órgão, função, programa, ação e grupo sobre os mesmos registros.

## Formato e configuração regional

- CSV com cabeçalho, separador **ponto e vírgula (`;`)**, codificação **UTF-8 com BOM** (65001).
- Valores monetários com **ponto decimal**, duas casas, sem separador de milhares: `1234.56`, `-12.50`, `0.00`.
- Valores monetários NULL são campos vazios; não converter vazios em zero.
- Aspas e campos com delimitadores/quebras de linha seguem o escape padrão CSV. Não conte linhas físicas para contar registros.

No Power BI Desktop, use **Obter dados > Texto/CSV**, escolha a codificação UTF-8 e o delimitador ponto e vírgula. Desative a detecção automática de tipos, ou remova a etapa automática **Tipo Alterado** antes de definir os tipos manualmente. CSV não carrega um esquema de tipos: transformar `0905` em número e depois em texto já perde o zero inicial.

Em **Transformar dados**, mantenha todas as colunas `codigo_*` como **Texto**. Para as quatro medidas monetárias, trate campos vazios como `null` e escolha **Alterar tipo > Usando localidade**, **Número decimal fixo**, **Inglês (Estados Unidos)**. Isso lê o ponto decimal corretamente. Depois, a exibição pode usar moeda brasileira e duas casas (`R$`, português do Brasil), sem mudar os valores. O tipo decimal fixo do Power BI tem limite menor que `DECIMAL(20,2)` do DuckDB; a carga atual está dentro desse limite, mas futuras bases precisam ser verificadas.

Referências Microsoft: [conector Texto/CSV](https://learn.microsoft.com/en-us/power-query/connectors/text-csv) e [tipos e localidade no Power Query](https://learn.microsoft.com/en-us/power-query/data-types).

## Agregações alternativas e relações

| Arquivo em `data/processed/` | Granularidade | Linhas nesta carga |
| --- | --- | ---: |
| `despesas_bi.csv` | Registro de origem | 48.519 |
| `despesas_por_orgao.csv` | Período + código/nome do órgão superior | 36 |
| `despesas_por_programa.csv` | Período + código/nome do programa + classificação auxiliar | 179 |
| `despesas_por_acao.csv` | Período + código/nome do programa + código/nome da ação + classificação auxiliar | 1.214 |

As três agregações incluem as mesmas quatro medidas, calculadas separadamente por SQL, e `quantidade_registros` (inteiro), a contagem de registros de origem por grupo. O programa contextualiza a ação; o código da ação sozinho não é usado como chave global.

**Para a análise com filtros combinados, importe apenas `despesas_bi.csv`. Não há relações a criar nesta etapa.** As agregações são visões alternativas para conferência ou uso isolado, não dimensões. Se importadas para conferência, mantenha-as desconectadas e desative/remova relações automáticas entre elas e a tabela principal. Não anexe nem some essas tabelas entre si ou à principal: isso duplicaria os valores.

A agregação por programa reúne todos os órgãos e não suporta filtro por órgão. A agregação por ação reúne órgãos e grupos de despesa. Essas limitações não existem na tabela principal. O relatório posterior utiliza a tabela principal, sem ligar essas agregações como dimensões.

## Classificações e medidas

`classificacao_programa_divida` identifica **exclusivamente** os códigos textuais `0905`, `0906`, `0907` e `0908` como `Programa específico de dívida`. Os demais recebem `Demais programas`, inclusive `0909`. Esse rótulo não significa que os demais programas não contenham despesas relacionadas à dívida.

O grupo de despesa continua independente, com seu código e nome originais. Em particular, grupo 2 e grupo 6 não são substituídos pela classificação de programa. A validação anterior identificou valores do grupo 6 no programa 0909; a regra não classifica todo esse programa como dívida nem exclui qualquer valor do total.

Empenho, liquidação, pagamento e pagamento de restos a pagar são medidas distintas. **Não some estágios de execução como despesas adicionais.** `valor_pago` não inclui `valor_restos_pagos`. Mantenha sinais negativos; classificações orçamentárias não explicam causas, beneficiários finais ou eficácia dos gastos.

## Validações executadas

Na exportação, o banco é aberto em modo somente leitura. Views temporárias executam os arquivos SQL em `sql/powerbi/`; nenhuma tabela persistente é alterada. A subpasta evita misturar as consultas de exportação com o relatório da Missão 04.

- 48.519 registros na origem e na tabela principal; mesmos identificadores, todos únicos, sem multiplicação de linhas.
- Quatro somas reconciliadas com a origem e com cada agregação. Total pago de **R$ 414.272.570.651,27** em cada arquivo, com diferença **R$ 0,00**.
- Contagens não nulas e quantidades de negativos da tabela principal iguais às da origem.
- Preservados 53 valores pagos negativos e 1 valor negativo de restos pagos. Não há negativos de empenhado ou liquidado nesta carga. Agregações podem compensar sinais dentro de grupos, por isso a checagem de negativos é feita na principal.
- Todos os CSVs são relidos integralmente, comparando contagem e hash das células textuais com o resultado SQL exportado, incluindo códigos, valores, nomes e vazios.
- Hashes do banco e do ZIP inalterados após a execução real.
- 21 testes automatizados aprovados, incluindo dados fictícios com negativos, NULL, zero, códigos com zeros à esquerda, caracteres CSV especiais, reexecução e rejeição de identidade duplicada/coluna ausente.

`data/processed/validacao_exportacao.json` registra as contagens, os totais pagos, as diferenças e os negativos. Os arquivos são locais e continuam ignorados pelo Git. Não foi validada a importação dentro do aplicativo Power BI nesta etapa.

## Reexecutar

```powershell
.\.venv\Scripts\python.exe -X utf8 src\export_powerbi.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

O script substitui os quatro CSVs e o relatório de validação a partir do banco atual; não acrescenta registros a exportações anteriores. Também aceita `--database` e `--output`. Em caso de erro, não utilize uma exportação parcial: corrija o problema e reexecute até a validação concluir.
