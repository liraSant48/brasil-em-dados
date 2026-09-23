# Brasil em Dados

Análise exploratória da execução da despesa federal com dados abertos do Portal da Transparência. Projeto de portfólio que conecta **Python, SQL, DuckDB, Power BI e Git**, com rastreabilidade, testes e reconciliação financeira.

O recorte inicial é **janeiro de 2026**. Os rankings abrangem os órgãos presentes no arquivo carregado, sem restrição ao Ministério da Fazenda. A integridade interna **não comprova, isoladamente, a completude de toda a execução federal**.

## Resultados validados

| Verificação | Resultado |
| --- | ---: |
| Registros | 48.519 |
| Códigos de órgão superior | 36 |
| Códigos de programa | 179 |
| Total pago do exercício no recorte | **R$ 414.272.570.651,27** |
| Diferença: soma dos programas − total pago | **R$ 0,00** |
| Pagamentos de restos a pagar, separados | R$ 147.955.708.343,19 |

Consulte [as consultas e resultados completos](RESULTADOS_JANEIRO_2026.md). O Total Pago também foi validado pelo responsável pelo projeto no Desktop antes do refinamento visual. A versão escura ainda precisa de conferência de renderização e interações no aplicativo.

## Fonte e tecnologias

Fonte declarada: [Portal da Transparência — Despesas: Execução](https://portaldatransparencia.gov.br/download-de-dados/despesas-execucao). Entrada local: `data/raw/202601_Despesas.zip`, com `202601_Despesas.csv`, 47 colunas, separador `;` e codificação estimada cp1252.

- **Python:** inspeção, leitura em lotes, exportação e verificações.
- **SQL e DuckDB:** staging, transformações e consultas analíticas com precisão decimal.
- **Power BI:** Power Query, modelo TMDL, medidas DAX e relatório PBIR.
- **Git:** versionamento posterior de código, documentação e definições do projeto, após revisão.

Os scripts não fazem downloads. Dados, banco, cache e ambiente virtual não são distribuídos pelo repositório.

## Pipeline e pastas

```text
ZIP local → Python → DuckDB staging (texto) → SQL analítico (DECIMAL)
          → SQL de exportação → CSVs validados → Power Query → DAX → PBIR
```

**Os arquivos analíticos são preparados por SQL.** A tabela principal mantém os registros para combinar filtros, sem joins ou agregação prévia. Detalhes: [Arquitetura](docs/ARQUITETURA.md) e [Metodologia](docs/METODOLOGIA.md).

```text
src/                         # Inspeção, carga, exportação e ferramentas PBIR
sql/                         # Transformações e consultas de validação
  powerbi/                   # Projeção principal e agregações alternativas
tests/                       # Dados fictícios, integridade e contratos PBIR
docs/                        # Arquitetura, metodologia e publicação
  imagens/                   # Capturas reais futuras
data/                        # Conteúdo local ignorado pelo Git
  raw/                       # ZIP original
  processed/                 # CSVs, candidatos PBIR e backups
powerbi/
  Brasil_em_Dados.pbip
  Brasil_em_Dados.Report/
  Brasil_em_Dados.SemanticModel/
requirements.txt
RESULTADOS_JANEIRO_2026.md
```

## Instalação e execução

Pré-requisitos: Python, Power BI Desktop compatível com PBIP/TMDL/PBIR e, para versionamento, Git. Ambiente local validado: Python 3.14, DuckDB 1.5.5 e PyArrow 25.0.1. Na raiz do projeto, em PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Esses são comandos para reprodução; nenhuma biblioteca foi baixada nesta etapa. Disponibilize o ZIP correspondente ao período em `data/raw/` e execute:

```powershell
.\.venv\Scripts\python.exe -X utf8 src\inspect_data.py data\raw\202601_Despesas.zip
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -X utf8 src\load_data.py data\raw\202601_Despesas.zip
.\.venv\Scripts\python.exe -X utf8 src\export_powerbi.py
```

O banco é criado em `data/brasil_em_dados.duckdb`. A carga transacional substitui o snapshot; reexecutar não acrescenta registros duplicados. O ZIP não é alterado, e a exportação abre o banco em modo somente leitura.

## Consultas e transformações

- `sql/01_build_analytics.sql`: seis medidas separadas em `DECIMAL(20,2)`; conversão brasileira sem float, negativos preservados, vazio como NULL e zero como zero. Valores inválidos interrompem a carga.
- `sql/02_count.sql` a `sql/06_top_acoes.sql`: contagens, totais e rankings, com janeiro de 2026 explícito.
- `sql/07_quality.sql` a `sql/09_dimensions.sql`: vazios, zeros, negativos, registros integralmente iguais e dimensões ausentes.
- `sql/powerbi/`: principal e três agregações alternativas.

| CSV | Linhas | Diferença do total pago frente à principal |
| --- | ---: | ---: |
| `despesas_bi.csv` | 48.519 | R$ 0,00 |
| `despesas_por_orgao.csv` | 36 | R$ 0,00 |
| `despesas_por_programa.csv` | 179 | R$ 0,00 |
| `despesas_por_acao.csv` | 1.214 | R$ 0,00 |

**Não some nem anexe as agregações à principal.** Elas não são dimensões. Empenho, liquidação, pagamento e pagamento de restos a pagar são medidas separadas; não se somam estágios como despesas adicionais.

## Abrir e configurar o PBIP

1. Gere `data/processed/despesas_bi.csv`.
2. Abra `powerbi/Brasil_em_Dados.pbip` no Desktop.
3. Em **Transformar dados**, selecione `despesas_bi` e ajuste o caminho da etapa `Fonte` para seu CSV. Na cópia de publicação há um marcador `C:\CONFIGURAR_CAMINHO\...`, não um arquivo real.
4. Preserve delimitador `;`, UTF-8 (65001), códigos como Texto e medidas em `Currency.Type` com cultura de leitura `en-US`. O CSV usa ponto decimal; o modelo apresenta números em `pt-BR`.
5. Atualize e confira 48.519 registros e Total Pago de R$ 414.272.570.651,27 sem filtros.

A página de validação foi preservada. **Visão Geral** contém quatro cartões, dois gráficos, três filtros e detalhe em reais exatos. Programas usam códigos textuais para não juntar códigos de nomes iguais. O auxiliar dos programas 0905–0908 não substitui grupo de despesa nem classifica todo o programa 0909 como dívida.

Cartões e eixos usam unidades automáticas nativas; rótulos das barras e detalhe mantêm reais exatos. As medidas não dividem valores nem perdem centavos. Confira os sufixos de milhões/bilhões e as interações no Desktop. Veja o [guia de importação](powerbi/GUIA_POWER_BI.md) e o [relatório do refinamento](docs/REFINAMENTO.md).

## Testes e validações

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
powershell -NoProfile -ExecutionPolicy Bypass -File src\validate_pbir.ps1 -Candidate powerbi\Brasil_em_Dados.Report\definition\pages
powershell -NoProfile -ExecutionPolicy Bypass -File src\validate_tmdl.ps1
```

Os validadores usam recursos já instalados com o Power BI, sem rede. A opção ExecutionPolicy vale apenas para o processo, sem alterar política persistente. Para extrair os esquemas locais, consulte [docs/REFINAMENTO.md](docs/REFINAMENTO.md).

A suíte cobre conversões, NULL/zero, códigos, negativos, rollback, reexecução, reconciliação, releitura dos CSVs, referências PBIR, interações configuradas, contraste e cópia sem caminho pessoal. O resultado atualizado está no relatório do refinamento.

**Testes locais não substituem renderização e seleção no Desktop.** Nenhuma medida foi alterada para mascarar resultados em branco.

## Limitações e atualização

- A conciliação interna não comprova cobertura integral ou autenticidade da origem do arquivo.
- Negativos e nomes aparentemente truncados foram preservados; sua causa não foi inferida.
- Os totais incluem dívida pública, não apenas gastos em serviços públicos.
- Classificações não comprovam causas econômicas/políticas, eficácia, irregularidade ou beneficiário final.
- O snapshot é mensal, sem série temporal. O comportamento de cartões em branco não foi reproduzido no Desktop nesta etapa.

Para reprocessar o mesmo snapshot, repita testes, carga e exportação e atualize o PBIP. Para outro mês, revise a restrição em Python, datas das consultas, título estático e documentação. Não renomeie outro período para contornar validações. Vários meses exigem chave de origem e estratégia incremental antes de anexar registros.

## Preparação para publicação

A fonte M local conserva um caminho pessoal. **Não execute `git add .` diretamente nesta pasta antes de tratar esse caminho.** Prepare uma cópia revisável sem mudar o projeto de trabalho:

```powershell
.\.venv\Scripts\python.exe -X utf8 src\prepare_publication.py --prepare
```

Revise `data/processed/publicacao_<data_hora>/` e siga [docs/PUBLICACAO.md](docs/PUBLICACAO.md). A ferramenta não executa Git, commits ou publicação. Sua auditoria heurística não dispensa revisão humana.

## Imagens do dashboard

Espaço reservado para **capturas reais** depois da conferência no Desktop:

- Visão Geral sem filtros, com período e unidades legíveis.
- Filtros combinados e detalhe em reais exatos.
- Página de validação com o total reconciliado.

Salve as capturas revisadas em `docs/imagens/` e acrescente seus links aqui. Nenhuma imagem fictícia foi incluída.
