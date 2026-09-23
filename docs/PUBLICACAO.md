# Revisão antes de publicar

## Estado local

Na inspeção desta etapa não havia pasta `.git` e o executável Git não estava disponível no terminal. Portanto, não existem alterações pendentes no índice a relatar nem histórico para comparar. Foram usados backups, hashes e comparação de arquivos. Não foi executado `git init`, `add`, `commit`, `remote` ou `push`.

O arquivo TMDL de trabalho contém um caminho absoluto do Windows com o nome do usuário na chamada `File.Contents`. **Não publique diretamente a pasta de trabalho com `git add .`.** A fonte local foi preservada por solicitação do usuário.

## Cópia preparada

```powershell
.\.venv\Scripts\python.exe -X utf8 src\prepare_publication.py
.\.venv\Scripts\python.exe -X utf8 src\prepare_publication.py --prepare
```

O primeiro comando audita os arquivos candidatos; o segundo cria uma pasta nova `data/processed/publicacao_<data_hora>/`. Não instala software nem executa Git ou rede.

A cópia contém código, SQL, testes, documentação, PBIP/PBIR/TMDL, tema, `.platform` e configurações compartilhadas necessárias. Na cópia, e somente nela, a fonte CSV recebe o marcador `C:\CONFIGURAR_CAMINHO\brasil-em-dados\data\processed\despesas_bi.csv`. Quem clonar deve configurar seu próprio caminho no Power Query. Nenhuma medida DAX é modificada.

O manifesto de auditoria fica ao lado da cópia, fora dela. Revise a cópia completa antes de qualquer commit. A busca por padrões de tokens/e-mails/caminhos é uma verificação heurística, não uma certificação de ausência de informação sensível.

## O que entra no Git

- `README.md`, `requirements.txt`, `.gitignore`, `RESULTADOS_JANEIRO_2026.md`.
- `src/`, `sql/`, `tests/` e `docs/`.
- `powerbi/*.pbip`, definições `.pbir`, `.pbism`, JSONs PBIR, arquivos TMDL, recursos de tema e `.platform`.
- `.pbi/editorSettings.json`, compartilhado pelo modelo; não ignorar indiscriminadamente toda a pasta `.pbi`.
- Marcadores `.gitkeep` de pastas vazias e capturas reais revisadas quando existirem.

## O que fica fora

`.venv`, dados brutos/processados, DuckDB/WAL, CSVs, cache `.pbi/cache.abf`, `.pbi/localSettings.json`, credenciais, tokens, chaves privadas, backups, esquemas extraídos localmente e pastas de publicação geradas. `data/**` continua protegido. Não use `git add -f` para contornar essas regras.

Os identificadores de objetos `.platform` não são credenciais. Não há capturas de tela incluídas nesta etapa. Os arquivos JSON de tema e definição são necessários; o maior candidato inspecionado tinha cerca de 100 kB, sem arquivos de dados grandes na seleção.

## Comandos propostos, somente depois da revisão

Abra um terminal **na cópia de publicação**, após instalar Git por sua própria gestão de ambiente. Não execute estes comandos na pasta original sem tratar o caminho pessoal.

```powershell
git init -b main
git status --short --untracked-files=all
git check-ignore -v .venv/exemplo data/raw/202601_Despesas.zip data/brasil_em_dados.duckdb powerbi/Brasil_em_Dados.SemanticModel/.pbi/cache.abf
git add .gitignore README.md requirements.txt RESULTADOS_JANEIRO_2026.md src sql tests docs powerbi data/raw/.gitkeep data/processed/.gitkeep
git diff --cached --stat
git diff --cached --check
git diff --cached
# Somente após aprovação do conteúdo staged:
# git commit -m "Adiciona Brasil em Dados: análise de janeiro de 2026"
```

Não há criação de remoto ou push nesta etapa. Se qualquer arquivo inesperado aparecer, interrompa a preparação e revise a seleção.

## LinkedIn e imagens

Reserve imagens em `docs/imagens/` para capturas reais de Visão Geral e validação após abrir o Desktop. Revise nomes de usuário, caminhos, notificações e informações do ambiente antes de adicioná-las. O README contém um espaço reservado, sem imagem fictícia.

Uma futura apresentação pode descrever o pipeline Python → DuckDB/SQL → Power BI, o recorte mensal, os testes e a reconciliação. Evite afirmar cobertura integral do Governo Federal ou atribuir causas econômicas/políticas aos pagamentos sem documentação. Nenhum texto foi publicado nesta etapa.
