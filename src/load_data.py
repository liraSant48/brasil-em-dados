"""Carga local e transacional de um snapshot mensal; não acessa a rede."""

import argparse
import csv
from decimal import Context, Decimal
import hashlib
import io
import json
import re
from pathlib import Path
import sys
import zipfile

import duckdb
import pyarrow as pa

ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / "sql"
COLUMNS = json.loads((ROOT / "src/despesas_columns.json").read_text(encoding="utf-8"))
MONEY_COLUMNS = [name for name in COLUMNS if name.startswith("Valor ")]
SOURCE = "https://portaldatransparencia.gov.br/download-de-dados/despesas-execucao"


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def quote(name):
    return '"' + name.replace('"', '""') + '"'


def load_data(path, database, member=None, batch_size=5000, period='2026/01'):
    """Valida um único mês; o carregador incremental usa um banco temporário."""
    if not re.fullmatch(r'[0-9]{4}/(0[1-9]|1[0-2])', period):
        raise ValueError('Período esperado no formato AAAA/MM.')
    path, database = Path(path), Path(database)
    if not path.is_file():
        raise ValueError(f"ZIP local não encontrado: {path}")
    if path.resolve() == database.resolve():
        raise ValueError("O banco não pode ser o arquivo de entrada.")
    if batch_size < 1:
        raise ValueError("batch_size deve ser positivo.")
    digest = sha256(path)
    with zipfile.ZipFile(path) as archive:
        candidates = [e for e in archive.infolist() if not e.is_dir() and e.filename.lower().endswith('.csv')]
        if member is not None:
            candidates = [e for e in candidates if e.filename == member]
        if len(candidates) != 1:
            raise ValueError("Selecione exatamente um CSV com --member.")
        entry = candidates[0]
        with archive.open(entry) as binary, io.TextIOWrapper(binary, encoding="cp1252", newline="") as stream:
            reader = csv.reader(stream, delimiter=";", strict=True)
            header = next(reader, None)
            if header is None or len(header) != len(set(header)) or set(header) != set(COLUMNS):
                missing = sorted(set(COLUMNS) - set(header or []))
                extra = sorted(set(header or []) - set(COLUMNS))
                raise ValueError(f"Cabeçalho incompatível: esperadas 47 colunas únicas. Ausentes: {missing}; extras: {extra}")
            database.parent.mkdir(parents=True, exist_ok=True)
            with duckdb.connect(str(database)) as con:
                if con.execute("SELECT count(*) FROM information_schema.tables WHERE table_name='incremental_control'").fetchone()[0]:
                    raise ValueError('Banco incremental: use load_months.py; substituição integral bloqueada.')
                con.execute("BEGIN TRANSACTION")
                try:
                    definitions = ', '.join(f'{quote(name)} VARCHAR NOT NULL' for name in header)
                    con.execute(f"CREATE OR REPLACE TABLE staging_despesas ({definitions}, _linha_csv BIGINT PRIMARY KEY)")
                    total = 0
                    batch = []
                    decimal_context = Context(prec=50)
                    expected_sums = {name: Decimal(0) for name in MONEY_COLUMNS}
                    expected_present = {name: 0 for name in MONEY_COLUMNS}

                    def insert_batch():
                        arrays = [pa.array(values, type=pa.string()) for values in zip(*batch)]
                        table = pa.Table.from_arrays(arrays, names=header)
                        table = table.append_column('_linha_csv', pa.array(range(total - len(batch) + 1, total + 1), type=pa.int64()))
                        con.register('_batch', table)
                        try:
                            con.execute('INSERT INTO staging_despesas SELECT * FROM _batch')
                        finally:
                            con.unregister('_batch')

                    period_index = header.index("Ano e mês do lançamento")
                    for total, row in enumerate(reader, start=1):
                        if len(row) != len(header):
                            raise ValueError(f"Registro {total}: esperadas 47 colunas, recebidas {len(row)}.")
                        if row[period_index] != period:
                            raise ValueError(f"Registro {total}: período diferente de {period}: {row[period_index]!r}")
                        for name in MONEY_COLUMNS:
                            value = row[header.index(name)].strip()
                            if not value:
                                continue
                            if not re.fullmatch(r'[+-]?([0-9]+|[0-9]{1,3}(\.[0-9]{3})+)(,[0-9]{1,2})?', value):
                                raise ValueError(f"Registro {total}, coluna {name}: valor inválido {value!r}")
                            amount = Decimal(value.replace('.', '').replace(',', '.'))
                            if abs(amount) >= Decimal('1000000000000000000'):
                                raise ValueError(f"Registro {total}, coluna {name}: excede DECIMAL(20,2).")
                            expected_sums[name] = decimal_context.add(expected_sums[name], amount)
                            expected_present[name] += 1
                        batch.append(row)
                        if len(batch) == batch_size:
                            insert_batch()
                            batch.clear()
                    if batch:
                        insert_batch()
                    if total == 0:
                        raise ValueError("CSV sem registros.")
                    con.execute((SQL / '01_build_analytics.sql').read_text(encoding='utf-8'))
                    counts = con.execute('SELECT (SELECT count(*) FROM staging_despesas), count(*), count(DISTINCT _linha_csv) FROM despesas').fetchone()
                    if counts != (total, total, total):
                        raise ValueError(f"Contagens divergentes: CSV={total}, banco={counts}")
                    # Reconcilia seis somas/contagens com Decimal Python, sem float.
                    for name in MONEY_COLUMNS:
                        actual = con.execute(f'SELECT sum({quote(name)}), count({quote(name)}) FROM despesas').fetchone()
                        expected = (expected_sums[name] if expected_present[name] else None, expected_present[name])
                        if actual != expected:
                            raise ValueError(f"Reconciliação monetária falhou em {name}: {actual} != {expected}")
                    # Compara cada dimensão textual pela posição no CSV.
                    unchanged = [name for name in header if name not in MONEY_COLUMNS]
                    differences = ' OR '.join(f's.{quote(name)} IS DISTINCT FROM d.{quote(name)}' for name in unchanged)
                    if con.execute(f'SELECT count(*) FROM staging_despesas s JOIN despesas d USING (_linha_csv) WHERE {differences}').fetchone()[0]:
                        raise ValueError("Dimensões textuais foram alteradas.")
                    if sha256(path) != digest:
                        raise ValueError("O ZIP mudou durante a leitura; carga cancelada.")
                    con.execute('''CREATE OR REPLACE TABLE carga_metadata (
                        origem VARCHAR, arquivo VARCHAR, membro VARCHAR, sha256 VARCHAR,
                        periodo VARCHAR, codificacao VARCHAR, separador VARCHAR,
                        colunas INTEGER, registros BIGINT, carregado_em TIMESTAMPTZ,
                        duckdb_version VARCHAR)''')
                    con.execute('INSERT INTO carga_metadata VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, current_timestamp, ?)',
                                [SOURCE, path.name, entry.filename, digest, period, 'cp1252', ';', len(header), total, duckdb.__version__])
                    con.execute('COMMIT')
                except Exception:
                    con.execute('ROLLBACK')
                    raise
    return {'registros': total, 'sha256': digest, 'database': str(database)}


def report(database):
    sections = []
    with duckdb.connect(str(database), read_only=True) as con:
        for path in sorted(SQL.glob('*.sql')):
            if path.name.startswith('01_'):
                continue
            cursor = con.execute(path.read_text(encoding='utf-8'))
            names = [c[0] for c in cursor.description]
            rows = cursor.fetchall()
            def cell(value):
                return ('NULL' if value is None else str(value)).replace('|', '\\|').replace('\n', ' ')
            sections.append('## ' + path.name + '\n\n' +
                            '| ' + ' | '.join(names) + ' |\n' +
                            '| ' + ' | '.join('---' for _ in names) + ' |\n' +
                            '\n'.join('| ' + ' | '.join(map(cell, row)) + ' |' for row in rows))
    return '\n\n'.join(sections) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', type=Path)
    parser.add_argument('--database', type=Path, default=ROOT / 'data/brasil_em_dados.duckdb')
    parser.add_argument('--member')
    args = parser.parse_args(argv)
    try:
        result = load_data(args.path, args.database, args.member)
        print(json.dumps(result, ensure_ascii=False))
        print(report(args.database))
    except (ValueError, OSError, csv.Error, UnicodeError, zipfile.BadZipFile, duckdb.Error, RuntimeError) as exc:
        print(f'Erro na carga: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
