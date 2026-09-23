SELECT count(*) FILTER (WHERE trim("Código Órgão Superior") = '' OR trim("Nome Órgão Superior") = '') AS orgao_vazio,
       count(*) FILTER (WHERE trim("Código Programa Orçamentário") = '' OR trim("Nome Programa Orçamentário") = '') AS programa_vazio,
       count(*) FILTER (WHERE trim("Código Ação") = '' OR trim("Nome Ação") = '') AS acao_vazia
FROM despesas;
