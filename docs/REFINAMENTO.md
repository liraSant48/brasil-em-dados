# Refinamento visual e preparação do portfólio

## Estado inspecionado

Foram preservadas as páginas `Página 1` (validação) e `Visão Geral`, seus identificadores e a ordem. O Desktop havia acrescentado metadados como projeções ativas e cartões de filtro vazios; esses metadados foram mantidos. Não havia repositório `.git` nem Git disponível no terminal, portanto não há diff de commits ou staging a apresentar.

Backup integral anterior à aplicação:

```text
data/processed/backups/dark_20260922_232056/Brasil_em_Dados.Report/
```

Essa pasta é ignorada pelo Git e fica fora de `powerbi/`. O manifesto ao lado registra hashes de DuckDB, CSVs, ZIP e arquivos do modelo/SQL. O README anterior também foi guardado nessa pasta. As alterações PBIR foram preparadas em `data/processed/pbir_dark_candidate/` e validadas antes da aplicação.

## Alterações

Foram alterados `page.json` e os onze visuais existentes de `definition/pages/b6d202601000000000001/`; foi acrescentado o visual de detalhe `b6d20260100000000012`. Nenhum arquivo da página de validação, índice de páginas, tema global, configurações locais ou modelo foi modificado.

| Elemento | Cor |
| --- | --- |
| Página | `#0F1115` |
| Cartões, gráficos, filtros e detalhe | `#171A21` |
| Bordas e linhas discretas | `#2A2F3A` |
| Cabeçalho | `#12324A` |
| Texto principal / secundário | `#F3F4F6` / `#AAB2BF` |
| Valores dos quatro cartões | `#32D583` |
| Realce dos filtros | `#22C55E` |
| Barras por órgão / programa | `#2F6FED` / `#14B8A6` |

As duas cores restantes da paleta de barras (`#1F4E79`, `#34D399`) ficam reservadas para uma futura necessidade de séries; não foram introduzidas séries fictícias para utilizá-las. Cores consistentes identificam cada gráfico. O contraste dos textos e valores contra os fundos usados passou no critério de razão mínima 4,5:1. Isso não substitui uma avaliação visual de acessibilidade no Desktop.

A página tem 1600 × 1440 e `FitToWidth`: o bloco analítico superior mantém seu alinhamento, e o detalhe fica abaixo, com rolagem quando necessária. Não há sobreposição ou elemento fora dos limites.

## Formatação monetária segura

Foi removida a escala fixa `,,,` com sufixo `bi` de todas as projeções de medida da página. O formato exato, apenas visual, é:

```text
"R$" #,0.00;-"R$" #,0.00;"R$" #,0.00
```

- Cartões: `labelDisplayUnits = 0` (automático), duas casas, usando o recurso nativo de unidades conforme magnitude. Valores grandes podem aparecer em bilhões e menores em milhões/milhares, conforme o formatador e idioma do Desktop.
- Eixos: unidades automáticas; os ticks são referências da escala, não valores individuais de despesa.
- Rótulos das barras: `labelDisplayUnits = 1` (sem escala), duas casas em reais, posicionados fora da barra, texto claro e fundo escuro para contraste. Rótulos que não couberem precisam ser conferidos no Desktop; o detalhe e o tooltip oferecem alternativa exata.
- Tooltips monetários e tabela de detalhe: projeções com o formato exato, sem dividir a medida por bilhões.

A tabela inclui `id_registro` para manter cada registro separado, código/nome do programa, código da ação, órgão, grupo e as quatro medidas. Seu contexto acompanha os filtros da página. Não utiliza os CSVs agregados nem duplica a fonte.

Essa solução evita o zero artificial causado pela escala fixa dos valores pequenos, sem inventar uma expressão PBIR de unidade dinâmica ou alterar DAX. Unidades automáticas ainda exigem teste de apresentação no Desktop; a precisão exata continua disponível no detalhe. Não foram acrescentados COALESCE, arredondamentos nas medidas, divisões, trocas de tipo ou tratamento de negativos como positivos.

## Investigação das interações

**Observado nos arquivos:** havia uma seleção salva no slicer de órgão para Advocacia-Geral da União. O SQL confirmou 137 registros, 9 códigos de programa e R$ 55.693.928,70 pagos nesse recorte. A seleção salva foi removida somente do estado inicial, depois do backup, para abrir com todos os órgãos.

As interações de saída dos gráficos não estavam explicitamente definidas. Não foi possível reproduzir a interface nesta etapa; esses achados não comprovam a causa relatada dos cartões em branco.

Configuração aplicada:

- Segmentações → cartões, gráficos, detalhe e outras segmentações: `DataFilter`.
- Barra selecionada → cartões, outro gráfico e detalhe: `DataFilter`.
- Barras → segmentações: `NoFilter`, preservando as escolhas dos menus.
- Seleção de uma linha da tabela de detalhe → outros visuais: `NoFilter`.

Seleção é a ação do usuário; realce cruzado destaca uma parcela e pode conservar o total de referência; filtragem restringe o conjunto de linhas de destino. A configuração agora escolhe filtragem explicitamente. Combinações sem registros podem produzir BLANK legitimamente; isso não foi mascarado. Códigos de programa continuam textuais e não são agrupados apenas pelo nome.

## Validações

- 32 testes automatizados aprovados: suíte anterior mais refinamento e publicação.
- 16 arquivos JSON das páginas, visuais e índice aprovados nos esquemas oficiais locais.
- TMDL desserializado com o componente nativo instalado: 3 tabelas e 5 expressões de medida conferidas. O modelo permaneceu byte a byte inalterado.
- Mesmos nomes de tabela/colunas/medidas; posições dentro da página, identidades únicas e ausência de sobreposição.
- Total pago: **R$ 414.272.570.651,27**, 48.519 registros. Soma dos programas e das agregações exportadas reconciliada, diferença **R$ 0,00**.
- 53 pagamentos negativos preservados; sinais e centavos mantidos no banco e CSVs.
- Banco, ZIP, CSVs, SQLs, fonte M e configurações locais preservados por comparação de hashes.

Os esquemas JSON vieram da instalação local do Desktop 2.157.1354.0; não houve downloads. TMDL não é JSON: sua validação usa `TmdlSerializer`, não um esquema PBIR.

Para extrair os esquemas em outro ambiente Windows que já tenha Power BI instalado pela Microsoft Store:

```powershell
$pbiInstall = (Get-AppxPackage *PowerBI*).InstallLocation
.\.venv\Scripts\python.exe -X utf8 -c "from pathlib import Path; from src.build_overview import local_schemas; import sys; local_schemas(Path(sys.argv[1]))" "$pbiInstall"
```

Os validadores PowerShell atuais localizam essa instalação pela Store. Outra distribuição/versão do Desktop pode exigir ajustar a localização dos assemblies e extrair esquemas compatíveis; não baixe nem substitua esquemas silenciosamente. Os scripts `build_overview.py` e `refine_overview.py` produzem candidatos e backup, não aplicam alterações ao relatório automaticamente.

## Conferir no Power BI Desktop

1. Reabrir o PBIP e verificar abertura sem avisos, cores, fontes, rótulos, rolagem e detalhe.
2. Limpar seleções, conferir R$ 414.272.570.651,27 no detalhe/validação e a abreviação correspondente no cartão.
3. Filtrar órgãos/programas com valores menores e negativos: conferir unidades automáticas e valor exato no detalhe, especialmente R$ 0,01 e R$ -0,01 em testes controlados, sem inventá-los na base oficial.
4. Selecionar uma barra por vez, limpar a seleção e combinar filtros de órgão/programa/grupo. Conferir se cartões, outro gráfico e detalhe usam o mesmo contexto.
5. Se aparecer BLANK, registrar seleção, filtros ativos, medida e contagem de linhas. Distinguir contexto vazio, realce e filtragem antes de afirmar a causa.
6. Conferir se o tooltip respeita o formato exato e se as relações automáticas de data existentes não introduzem contexto inesperado.

A validação dos arquivos não equivale à execução dessas interações ou ao cálculo DAX em um mecanismo ativo. A causa original do relato “Em branco” permanece sem confirmação empírica.

## Preparação para publicação

O `.gitignore` foi reforçado para backups, tokens e artefatos locais, preservando PBIP/PBIR/TMDL e `editorSettings.json`. A auditoria encontrou um caminho pessoal na fonte M local, que foi mantido. A cópia preparada por `prepare_publication.py` troca somente esse caminho por um marcador e exclui dados, cache, segredos e backups. Veja [PUBLICACAO.md](PUBLICACAO.md).

Arquivos de trabalho continuam sem Git inicializado. Não houve commit, criação de remoto, push, download, publicação ou alteração destrutiva. A próxima etapa depende da revisão dos arquivos e da conferência no Desktop.
