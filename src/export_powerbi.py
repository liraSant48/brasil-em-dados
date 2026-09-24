"""Exporta consultas SQL para CSV, sem modificar o banco de origem."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

import duckdb

ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / 'sql/powerbi'
EXPORTS = {
    'despesas_bi': '01_despesas_bi.sql',
    'despesas_por_orgao': '02_por_orgao.sql',
    'despesas_por_programa': '03_por_programa.sql',
    'despesas_por_acao': '04_por_acao.sql',
    'despesas_por_mes': '05_por_mes.sql',
}
MEASURES = {
    'valor_empenhado': 'Valor Empenhado (R$)',
    'valor_liquidado': 'Valor Liquidado (R$)',
    'valor_pago': 'Valor Pago (R$)',
    'valor_restos_pagos': 'Valor Restos a Pagar Pagos (R$)',
}


def profile(con, table, names):
    result = {}
    for alias, name in names.items():
        result[alias] = con.execute(
            f'SELECT sum("{name}"), count("{name}"), '
            f'count(*) FILTER (WHERE "{name}" < 0) FROM {table}'
        ).fetchone()
    return result


def validate(con):
    """Cardinalidade, identidades, quatro somas, nulos e sinais da projeção."""
    counts = con.execute('''SELECT (SELECT count(*) FROM despesas), count(*),
        count(DISTINCT id_registro) FROM despesas_bi''').fetchone()
    if counts[0] == 0 or len(set(counts)) != 1:
        raise ValueError(f'Contagem/identidade inválida; possível multiplicação de registros: {counts}')
    for left, right in (
        ('SELECT _linha_csv FROM despesas', 'SELECT id_registro FROM despesas_bi'),
        ('SELECT id_registro FROM despesas_bi', 'SELECT _linha_csv FROM despesas'),
    ):
        if con.execute(f'SELECT count(*) FROM ({left} EXCEPT ALL {right})').fetchone()[0]:
            raise ValueError('Identificadores de origem divergentes.')
    source = profile(con, 'despesas', MEASURES)
    main = profile(con, 'despesas_bi', {name: name for name in MEASURES})
    if source != main:
        raise ValueError('Somas, nulos ou negativos divergentes da origem.')
    for table in list(EXPORTS)[1:]:
        for name in MEASURES:
            actual = con.execute(f'SELECT sum({name}) FROM {table}').fetchone()[0]
            if actual != main[name][0]:
                raise ValueError(f'Agregação não reconciliada: {table}.{name}')
        if con.execute(f'SELECT sum(quantidade_registros) FROM {table}').fetchone()[0] != counts[0]:
            raise ValueError(f'Contagem agregada divergente: {table}')
    return counts[0], main


def digest_row(digest, row):
    digest.update((json.dumps(row, ensure_ascii=False) + '\n').encode('utf-8'))


def write_csv(con, table, path):
    """Leitura em lotes e validação de todas as células após reler o CSV."""
    cursor = con.execute(f'SELECT * FROM {table}')
    header = [item[0] for item in cursor.description]
    expected = hashlib.sha256()
    count = 0
    with path.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.writer(stream, delimiter=';', lineterminator='\n')
        writer.writerow(header)
        while batch := cursor.fetchmany(5000):
            for row in batch:
                values = ['' if value is None else str(value) for value in row]
                writer.writerow(values)
                digest_row(expected, values)
                count += 1
    actual = hashlib.sha256()
    read_count = 0
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.reader(stream, delimiter=';')
        if next(reader) != header:
            raise ValueError(f'Cabeçalho alterado na exportação: {path}')
        for row in reader:
            digest_row(actual, row)
            read_count += 1
    if read_count != count or actual.digest() != expected.digest():
        raise ValueError(f'CSV diverge do resultado SQL: {path}')
    return count


def export_data(database, output):
    database, output = Path(database), Path(output)
    summary = {}
    # Somente views temporárias da sessão; não cria tabelas no banco original.
    with duckdb.connect(str(database), read_only=True) as con:
        con.execute('BEGIN TRANSACTION')
        for table, filename in EXPORTS.items():
            query = (SQL / filename).read_text(encoding='utf-8').strip().rstrip(';')
            con.execute(f'CREATE TEMP VIEW {table} AS {query}')
        count, metrics = validate(con)
        output.mkdir(parents=True, exist_ok=True)
        for table in EXPORTS:
            path = output / f'{table}.csv'
            rows = write_csv(con, table, path)
            total = con.execute(f'SELECT sum(valor_pago) FROM {table}').fetchone()[0]
            summary[table] = {'linhas': rows, 'valor_pago': str(total), 'diferenca': str(total - metrics['valor_pago'][0]) if total is not None else None}
        con.execute('COMMIT')
    result = {'registros_origem': count, 'arquivos': summary,
              'negativos_principal': {name: values[2] for name, values in metrics.items()},
              'validacao': 'Quatro somas reconciliadas; identidades preservadas; CSVs relidos integralmente.'}
    (output / 'validacao_exportacao.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=ROOT / 'data/brasil_em_dados.duckdb')
    parser.add_argument('--output', type=Path, default=ROOT / 'data/processed')
    args = parser.parse_args(argv)
    try:
        print(json.dumps(export_data(args.database, args.output), ensure_ascii=False, indent=2))
    except (ValueError, OSError, duckdb.Error) as exc:
        print(f'Erro na exportação: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
