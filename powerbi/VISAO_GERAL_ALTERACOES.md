# Visão Geral — construção da primeira página analítica

> Registro histórico da construção inicial. O tema claro e a escala fixa descritos abaixo foram substituídos pelo [refinamento escuro](../docs/REFINAMENTO.md), que também acrescentou o detalhe e revisou as interações. Consulte esse documento para o estado atual.

## Escopo e arquivos

Foi acrescentada a página `Visão Geral` ao projeto `Brasil_em_Dados.pbip`, sem mudar o modelo semântico. A página anterior `Página 1` e seu visual de tabela foram preservados byte a byte.

- Nova pasta: `Brasil_em_Dados.Report/definition/pages/b6d202601000000000001/`.
- Novo `page.json`: tela 1600 × 1000, fundo claro, interações explícitas dos filtros.
- Onze novos `visuals/<id>/visual.json`: um cabeçalho com título/subtítulo, quatro cartões, dois gráficos de barras horizontais, três segmentações e uma nota de unidades.
- Alterado somente `Brasil_em_Dados.Report/definition/pages/pages.json` entre os arquivos já existentes: acrescenta a página ao final da ordem e a torna ativa.
- `src/build_overview.py`: prepara backup e arquivos candidatos; recusa sobrescrever uma página já registrada.
- `src/validate_pbir.ps1`: valida os arquivos contra esquemas oficiais disponíveis localmente.
- `tests/test_overview.py`: valida tipos de visual, campos, identidade dos programas e interações.

Não foram modificados `report.json`, o tema compartilhado, arquivos TMDL, medidas DAX, relações, configurações locais, credenciais, CSVs, SQLs, banco, ZIP ou `.gitignore`. Não houve downloads nem publicação.

## Composição e análise

A página usa azul-escuro `#13324F`, verde `#087F6D`, fundo `#F3F6FA` e cartões brancos, com margens e espaçamentos consistentes. O cabeçalho identifica janeiro de 2026. Não há série temporal.

Os cartões utilizam `Total Pago`, `Total Empenhado`, `Total Liquidado` e `Restos a Pagar Pagos`, cada um isoladamente. Os dois gráficos utilizam somente `Total Pago`, em ordem decrescente. Não há exclusão de dívida, filtro de valores positivos ou corte Top N; a navegação vertical dos gráficos permite acessar as categorias além das inicialmente visíveis.

As três segmentações filtram explicitamente todos os cartões, gráficos e demais segmentações por `DataFilter`, usando campos da mesma tabela `despesas_bi`. Não são necessárias relações adicionais.

### Identidade dos programas

A inspeção encontrou 14 nomes de programa associados a mais de um código na base atual. Por isso, o gráfico e a segmentação de programa usam `codigo_programa`, evitando somar códigos diferentes sob um único rótulo. O nome é exibido no tooltip do gráfico por uma agregação de consulta `Min(nome_programa)`; o código identifica um único nome nesta base. Não foi criada nova medida ou coluna. A função Min aqui seleciona esse nome, não um valor monetário.

Os órgãos são agrupados por `nome_orgao_superior`; nesta base não foram encontrados nomes de órgão associados a códigos distintos. Ao trocar de base, revise essas correspondências.

### Abreviação monetária

Os cartões e as projeções monetárias dos gráficos têm formato local ao visual:

```text
"R$" #,0,,,.00" bi";-"R$" #,0,,,.00" bi";"R$" #,0,,,.00" bi"
```

São três seções (positivo, negativo e zero), escala de bilhões e duas casas. As unidades automáticas dos visuais ficam desativadas (`labelDisplayUnits = 1`) para não aplicar escala duas vezes. Com a cultura `pt-BR` do modelo, o total esperado é `R$ 414,27 bi`. Valores pequenos podem arredondar para `R$ 0,00 bi`; isso não altera o dado nem elimina negativos. Os valores exatos continuam nas medidas e na tabela já existente. A renderização específica desse formato no Desktop ainda precisa ser conferida.

## Evidências de estrutura

Foram usados os mesmos formatos observados no relatório:

- Página: `page/2.1.0/schema.json`.
- Visual: `visualContainer/2.12.0/schema.json`.
- Configuração embutida: `visualConfigurationEmbedded/2.7.0/schema.json`.
- Ordem de páginas: `pagesMetadata/1.1.0/schema.json`.

Os esquemas foram extraídos dos recursos da instalação local Microsoft Power BI Desktop `2.157.1354.0`, em `bin/WebView2Resources/minerva/scripts/desktop.schema.json.*.min.js`. As propriedades específicas dos visuais foram confrontadas com `desktop.reportThemeSchema.json.min.js`, e funções de consulta com as definições dos visuais nativos. Não foram buscados arquivos na rede.

As referências entre esquemas foram agrupadas em namespaces distintos para evitar colisões de definições homônimas no validador .NET local. Não foram relaxadas regras de validação. A extração e seus hashes estão em `data/processed/pbir_local_schemas/`, ignorados pelo Git.

## Backup e recuperação

Backup integral utilizado antes da instalação:

```text
data/processed/report_backup_20260922_224642/Brasil_em_Dados.Report/
```

O arquivo `protected_hashes.json` ao lado do backup registra os hashes dos arquivos protegidos. A pasta inclui também os arquivos ocultos originais do relatório, sem alterar suas configurações.

Para desfazer com o Desktop fechado, restaure `definition/pages/pages.json` a partir desse backup. Isso retira a nova página da navegação. Para restauração integral, mantenha uma cópia do relatório atual e restaure a pasta completa do backup; não mescle versões do arquivo de ordem das páginas. Não é necessário restaurar o modelo semântico, pois ele não foi alterado.

## Validação e conferência no Desktop

Validações locais: sintaxe JSON, esquemas oficiais locais, nomes de campos/medidas existentes, identificadores únicos, limites da página, ausência de sobreposição, interações dos filtros, preservação da página anterior e hashes de fontes/modelo/configurações. A validação de esquema abrange os 15 arquivos JSON das duas páginas, seus visuais e o índice de páginas.

O formato monetário também foi conferido com o formatador numérico .NET em `pt-BR`, produzindo `R$ 414,27 bi`; isso não substitui a renderização do visual no Power BI.

Ainda é necessário abrir/reabrir `Brasil_em_Dados.pbip` no Desktop e verificar:

1. Abertura sem avisos e renderização dos onze visuais, especialmente textos longos e fontes.
2. Cartões em reais/bilhões, com vírgula decimal e duas casas; sem filtros, Total Pago deve mostrar `R$ 414,27 bi`, mantendo o valor exato previamente validado de R$ 414.272.570.651,27 na medida.
3. Gráficos com barras horizontais, ordenação, rolagem e nome do programa no tooltip.
4. Cada segmentação isoladamente e em combinação, conferindo os resultados contra os dados. Remova seleções ao conferir o total geral.
5. Valores pequenos arredondados apenas na apresentação e pagamentos de restos mantidos separados.

O título é estático e corresponde ao snapshot atual de janeiro de 2026. Caso a fonte passe a conter outros períodos, será necessário revisar o título ou acrescentar um filtro de período antes de reutilizar esta página.

Não houve teste de renderização nem execução das interações dentro do Desktop nesta etapa. As verificações locais não comprovam esses comportamentos em tempo de execução.
