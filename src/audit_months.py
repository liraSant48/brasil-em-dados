"""Auditoria integral dos ZIPs locais, sem rede, extração permanente ou banco."""
import argparse
import csv
from datetime import datetime, timezone
from decimal import Decimal, localcontext
import io
import json
from pathlib import Path
import re
import sys
import zipfile

try:
    from .load_data import ROOT, COLUMNS, MONEY_COLUMNS, sha256, quote
    from .load_months import JAN_HASH
    from .download_months import months
    from .inspect_data import inspect_stream
except ImportError:
    from load_data import ROOT, COLUMNS, MONEY_COLUMNS, sha256, quote
    from load_months import JAN_HASH
    from download_months import months
    from inspect_data import inspect_stream


def audit_zip(path, period):
    path = Path(path)
    if not path.is_file():
        raise ValueError(f'ZIP ausente: {path.name}')
    digest = sha256(path)
    if period == '202601' and digest != JAN_HASH:
        raise ValueError('Hash de janeiro diverge da referência validada.')
    with zipfile.ZipFile(path) as archive:
        files = archive.infolist()
        if len(files) != 1 or files[0].filename != f'{period}_Despesas.csv':
            raise ValueError(f'{path.name}: esperado exatamente um CSV com nome mensal correspondente.')
        member = files[0]
        if archive.testzip() is not None:
            raise ValueError(f'{path.name}: CRC inválido.')
        with archive.open(member) as binary:
            sample = inspect_stream(binary)
        header = sample['columns']
        if len(header) != len(COLUMNS) or set(header) != set(COLUMNS):
            raise ValueError(f'{path.name}: esquema divergente; ausentes={sorted(set(COLUMNS)-set(header))}; extras={sorted(set(header)-set(COLUMNS))}')
        if sample['encoding'] != 'cp1252' or sample['delimiter'] != ';':
            raise ValueError(f'{path.name}: codificação/separador divergem do carregador: {sample["encoding"]}/{sample["delimiter"]!r}.')
        amounts = {name: {'soma': Decimal(0), 'negativos': 0, 'nulos': 0} for name in MONEY_COLUMNS}
        rows = 0
        with archive.open(member) as binary, io.TextIOWrapper(binary, encoding='cp1252', newline='') as stream, localcontext() as ctx:
            ctx.prec = 50
            reader = csv.reader(stream, delimiter=';', strict=True)
            next(reader)
            money_positions = [(header.index(name), name) for name in MONEY_COLUMNS]
            period_position = header.index('Ano e mês do lançamento')
            for rows, row in enumerate(reader, 1):
                if len(row) != len(header):
                    raise ValueError(f'{path.name}, registro {rows}: largura inválida.')
                if row[period_position] != period[:4]+'/'+period[4:]:
                    raise ValueError(f'{path.name}, registro {rows}: período divergente.')
                for position, name in money_positions:
                    raw = row[position].strip()
                    if not raw:
                        amounts[name]['nulos'] += 1
                        continue
                    if not re.fullmatch(r'[+-]?([0-9]+|[0-9]{1,3}(\.[0-9]{3})+)(,[0-9]{1,2})?', raw):
                        raise ValueError(f'{path.name}, registro {rows}, {name}: tipo monetário inválido.')
                    value = Decimal(raw.replace('.', '').replace(',', '.'))
                    if abs(value) >= Decimal('1000000000000000000'):
                        raise ValueError(f'{path.name}, registro {rows}: valor excede DECIMAL(20,2).')
                    amounts[name]['soma'] += value
                    amounts[name]['negativos'] += value < 0
            if not rows:
                raise ValueError(f'{path.name}: CSV sem registros.')
        if sha256(path) != digest:
            raise ValueError(f'{path.name}: ZIP mudou durante a inspeção.')
    return {'arquivo': path.name, 'bytes': path.stat().st_size, 'sha256': digest,
            'periodo': period[:4]+'/'+period[4:], 'membro': member.filename,
            'csv_bytes': member.file_size, 'colunas': len(header), 'cabecalho': header,
            'ordem_cabecalho_referencia': header == COLUMNS,
            'codificacao_estimada': sample['encoding'], 'separador': sample['delimiter'],
            'registros': rows, 'metricas_origem': amounts, 'crc': 'OK',
            'tipos': 'Dimensões texto; seis campos monetários validados integralmente; período mensal validado.'}


def audit_months(raw, start='202601', end='202608'):
    return {'inspecionado_em_utc': datetime.now(timezone.utc).isoformat(),
            'nota': 'Data de inspeção local; não é a data de coleta nem autenticação da origem.',
            'arquivos': [audit_zip(Path(raw)/f'{p}_Despesas.zip', p) for p in months(start, end)]}


def reconcile_inventory(con, inventory):
    """Compara a leitura independente dos seis valores com cada mês do DuckDB."""
    source = {r['periodo']: r for r in inventory['arquivos']}
    loaded = dict(con.execute('SELECT periodo, sha256 FROM carga_metadata').fetchall())
    if set(source) != set(loaded):
        raise ValueError('Inventário local e banco contêm períodos diferentes.')
    for period, item in source.items():
        if loaded[period] != item['sha256']:
            raise ValueError(f'{period}: hash no banco difere da inspeção local.')
        actual_count = con.execute('SELECT count(*) FROM despesas WHERE "Ano e mês do lançamento"=?', [period]).fetchone()[0]
        if actual_count != item['registros']:
            raise ValueError(f'{period}: contagem do CSV difere do banco.')
        for name in MONEY_COLUMNS:
            column = quote(name)
            sums, negative, nulls = con.execute(f'''SELECT sum({column}),
                count(*) FILTER (WHERE {column}<0), count(*) FILTER (WHERE {column} IS NULL)
                FROM despesas WHERE "Ano e mês do lançamento"=?''', [period]).fetchone()
            metric = item['metricas_origem'][name]
            expected_sum = None if metric['nulos'] == item['registros'] else Decimal(str(metric['soma']))
            if (sums, negative, nulls) != (expected_sum, metric['negativos'], metric['nulos']):
                raise ValueError(f'{period}: divergência CSV/banco em {name}.')
    return 'Oito arquivos (ou intervalo solicitado), seis valores por mês e hashes reconciliados com leitura independente.'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw', type=Path, default=ROOT/'data/raw')
    parser.add_argument('--start', default='202601')
    parser.add_argument('--end', default='202608')
    parser.add_argument('--output', type=Path, default=ROOT/'data/processed/inspecao_multimensal.json')
    args = parser.parse_args()
    try:
        result = audit_months(args.raw, args.start, args.end)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, default=str, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        for item in result['arquivos']:
            print(json.dumps({k:v for k,v in item.items() if k not in ('cabecalho', 'metricas_origem')}, ensure_ascii=False))
    except Exception as exc:
        print(f'Inspeção interrompida: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
