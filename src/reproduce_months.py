"""Reconstrói jan–ago/2026 somente dos ZIPs; escreve em staging novo, sem rede.

Execução: python -B -m src.reproduce_months
As comparações com dados anteriores são opcionais e ocorrem após a geração.
"""
import argparse
from collections import Counter
import csv
from datetime import date, datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

import duckdb

from .load_data import ROOT, load_data, sha256
from .load_months import bootstrap, append_month, validate_all
from .audit_months import audit_months, reconcile_inventory
from .export_months import export_months
from .export_powerbi import SQL, MEASURES

PERIODS = tuple(f'2026{m:02}' for m in range(1, 9))
EXPECTED = dict(zip(MEASURES, map(Decimal, (
    '4862235542202.17', '3952437544425.00',
    '3845794556513.32', '230505665779.05'))))


def local_path(value, staging=False):
    relative = Path(value)
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('Use caminho relativo dentro da raiz do projeto.')
    resolved = (ROOT / relative).resolve()
    if not resolved.is_relative_to(ROOT) or any(
            part.startswith('publicacao') for part in relative.parts):
        raise ValueError('Caminho fora do projeto ou dentro de cópia de publicação.')
    if staging and (not resolved.is_relative_to(ROOT / 'data/_staging')
                    or resolved == ROOT / 'data/_staging'):
        raise ValueError('A saída deve ser uma pasta nova dentro de data/_staging.')
    return resolved


def discover(raw):
    found = {p.name[:6]: p for p in raw.iterdir()
             if p.is_file() and re.fullmatch(r'20260[1-8]_Despesas\.zip', p.name)}
    missing = set(PERIODS) - found.keys()
    if missing:
        raise ValueError('ZIPs ausentes: ' + ', '.join(sorted(missing)))
    return [found[m] for m in PERIODS]


def check_headers(inventory):
    reference = inventory['arquivos'][0]['cabecalho']
    for item in inventory['arquivos']:
        if item['cabecalho'] != reference:
            raise ValueError(f"Cabeçalho/ordem incompatível: {item['arquivo']}")


def canonical_row(header, row):
    """Representação tipada, preservando texto, NULL, centavos e identidade."""
    result = []
    for name, value in zip(header, row):
        if name in MEASURES:
            result.append(None if value is None or value == ''
                          else format(Decimal(str(value)).quantize(Decimal('.01')), '.2f'))
        elif name == 'id_registro':
            result.append(str(int(value)))
        elif name == 'periodo':
            result.append(date.fromisoformat(str(value)).isoformat())
        else:
            result.append(value)
    return json.dumps(result, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


def logical_profile(header, rows):
    hashes = Counter()
    totals = {key: Decimal(0) for key in MEASURES}
    monthly = Counter()
    for row in rows:
        if len(row) != len(header):
            raise ValueError('Largura de registro inválida na comparação.')
        hashes[hashlib.sha256(canonical_row(header, row)).hexdigest()] += 1
        record = dict(zip(header, row))
        monthly[str(record['periodo'])] += 1
        for name in MEASURES:
            if record[name] not in ('', None):
                totals[name] += Decimal(str(record[name]))
    digest = hashlib.sha256()
    for key, count in sorted(hashes.items()):
        digest.update(f'{key}:{count}\n'.encode('ascii'))
    return {'schema': header, 'rows': sum(hashes.values()), 'monthly': dict(monthly),
            'totals': totals, 'multiset_sha256': digest.hexdigest()}, hashes


def csv_profile(path, january=False):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.reader(stream, delimiter=';', strict=True)
        header = next(reader)
        period = header.index('periodo')
        rows = (row for row in reader if not january or row[period] == '2026-01-01')
        return logical_profile(header, rows)


def compare(left, right, label):
    a, ah = left
    b, bh = right
    difference = sum((ah - bh).values()) + sum((bh - ah).values())
    if a != b or difference:
        raise ValueError(f'{label}: divergência; esperado={a}; obtido={b}; '
                         f'registros divergentes={difference}. Nenhuma promoção permitida.')
    return {'igualdade_logica': True, 'registros_divergentes': 0, **a}


def build(run):
    raw = ROOT / 'data/raw'
    inputs = discover(raw)
    inventory = audit_months(raw)
    check_headers(inventory)
    run.mkdir(parents=True, exist_ok=False)
    (run / 'inventario.json').write_text(json.dumps(inventory, default=str,
        ensure_ascii=False, indent=2), encoding='utf-8')
    seed = run / 'janeiro_reconstruido.duckdb'
    database = run / 'consolidado.duckdb'
    load_data(inputs[0], seed)
    bootstrap(seed, database, inputs[0])
    for period, path in zip(PERIODS[1:], inputs[1:]):
        append_month(path, database, period[:4] + '/' + period[4:])
        print('Carregado:', period, flush=True)
    with duckdb.connect(str(database), read_only=True) as con:
        result = validate_all(con)
        result['origem'] = reconcile_inventory(con, inventory)
        if result['registros'] != 495572 or result['mensal'][0]['registros'] != 48519:
            raise ValueError(f'Contagens divergentes: {result["registros"]}')
        for key, expected in EXPECTED.items():
            actual = result['totais'][key]
            if actual != expected:
                raise ValueError(f'{key}: esperado={expected}; obtido={actual}; diferença={actual-expected}')
        schema = con.execute('DESCRIBE despesas_bi').fetchall()
        for name, dtype, *_ in schema:
            if name in MEASURES and dtype != 'DECIMAL(20,2)':
                raise ValueError(f'Tipo monetário inválido: {name}: {dtype}')
            if name.startswith('codigo_') and dtype != 'VARCHAR':
                raise ValueError(f'Código não textual: {name}')
        result['schema_sql'] = schema
    export_months(database, run / 'export', inventory=inventory)
    for item, path in zip(inventory['arquivos'], inputs):
        if sha256(path) != item['sha256']:
            raise ValueError('Entrada alterada durante a execução.')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='data/_staging/reproducao_' +
                        datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    parser.add_argument('--compare-csv', help='CSV anterior, somente leitura após gerar.')
    parser.add_argument('--compare-january-db', help='Snapshot validado, somente leitura após gerar.')
    args = parser.parse_args()
    output = local_path(args.output, staging=True)
    if output.exists():
        raise ValueError('Staging já existe; escolha outra pasta. Nada será sobrescrito.')
    reference = local_path(args.compare_csv) if args.compare_csv else None
    january = local_path(args.compare_january_db) if args.compare_january_db else None
    report = {}
    for n in (1, 2):
        report[f'execucao_{n}'] = build(output / f'run{n}')
    a = output / 'run1/export/despesas_bi.csv'
    b = output / 'run2/export/despesas_bi.csv'
    report['idempotencia'] = compare(csv_profile(a), csv_profile(b), 'Idempotência')
    if report['execucao_1'] != report['execucao_2']:
        raise ValueError('Perfis mensais, tipos ou reconciliações não são idênticos.')
    if reference:
        report['powerbi'] = compare(csv_profile(reference), csv_profile(a), 'Consolidado Power BI')
        report['powerbi']['hash_binario_igual'] = sha256(reference) == sha256(a)
    if january:
        with duckdb.connect(str(january), read_only=True) as con:
            cursor = con.execute((SQL / '01_despesas_bi.sql').read_text(encoding='utf-8'))
            header = [c[0] for c in cursor.description]
            profile = logical_profile(header, iter(cursor.fetchone, None))
        report['janeiro'] = compare(profile, csv_profile(a, january=True), 'Janeiro validado')
        # Todas as 47 colunas e identidades, além da projeção utilizada no Power BI.
        with duckdb.connect(str(output / 'run1/janeiro_reconstruido.duckdb'), read_only=True) as con:
            con.execute("ATTACH '" + str(january).replace("'", "''") + "' AS baseline (READ_ONLY)")
            for table in ('staging_despesas', 'despesas'):
                for left, right in ((table, 'baseline.'+table), ('baseline.'+table, table)):
                    if con.execute(f'SELECT count(*) FROM (SELECT * FROM {left} EXCEPT ALL SELECT * FROM {right})').fetchone()[0]:
                        raise ValueError(f'Janeiro: células divergentes em {table}')
        report['janeiro']['igualdade_47_colunas'] = True
    (output / 'resultado.json').write_text(json.dumps(report, default=str,
        ensure_ascii=False, indent=2), encoding='utf-8')
    print('Validação concluída:', output.relative_to(ROOT).as_posix(), flush=True)


if __name__ == '__main__':
    main()
