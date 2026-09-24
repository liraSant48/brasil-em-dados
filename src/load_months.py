"""Carga incremental em banco separado; não altera o snapshot validado de janeiro."""
import argparse
from decimal import Decimal
import json
from pathlib import Path
import shutil
import sys
import tempfile

import duckdb

try:
    from .load_data import ROOT, COLUMNS, load_data, sha256, quote
    from .download_months import months
    from .export_powerbi import EXPORTS, SQL as EXPORT_SQL, validate
except ImportError:
    from load_data import ROOT, COLUMNS, load_data, sha256, quote
    from download_months import months
    from export_powerbi import EXPORTS, SQL as EXPORT_SQL, validate

JAN_HASH = '67b6889a213eff3c733dacda454aae104e38358c058ab871469e12e9b342b8af'
JAN_PAID = Decimal('414272570651.27')
JAN_ROWS = 48519
MONTH_SQL = ROOT / 'sql/multimensal'


def validate_all(con):
    for table, filename in EXPORTS.items():
        con.execute(f'CREATE OR REPLACE TEMP VIEW {table} AS ' +
                    (EXPORT_SQL / filename).read_text(encoding='utf-8').strip().rstrip(';'))
    count, metrics = validate(con)
    monthly = con.execute((MONTH_SQL / '01_validacao_mensal.sql').read_text(encoding='utf-8'))
    names = [c[0] for c in monthly.description]
    result = [dict(zip(names, row)) for row in monthly.fetchall()]
    # Meses e agregações conservam somas, nulos e contagens separadamente.
    for table in EXPORTS:
        if table == 'despesas_bi':
            continue
        for name in metrics:
            for left, right in [('despesas_bi', table), (table, 'despesas_bi')]:
                query = f'''SELECT periodo, sum({name}) FROM {left} GROUP BY periodo
                            EXCEPT SELECT periodo, sum({name}) FROM {right} GROUP BY periodo'''
                if con.execute(query).fetchall():
                    raise ValueError(f'Reconciliação mensal falhou: {table}.{name}')
        if con.execute(f'''SELECT periodo, count(*) FROM despesas_bi GROUP BY periodo
            EXCEPT SELECT periodo, sum(quantidade_registros) FROM {table} GROUP BY periodo''').fetchall():
            raise ValueError('Contagens por período divergentes.')
    if con.execute('''SELECT periodo::VARCHAR, count(*) FROM despesas GROUP BY periodo
        EXCEPT SELECT strptime(periodo,'%Y/%m')::DATE::VARCHAR, registros FROM carga_metadata''').fetchall():
        raise ValueError('Metadados não correspondem às linhas carregadas.')
    if con.execute('SELECT periodo FROM carga_metadata GROUP BY periodo HAVING count(*)<>1').fetchall():
        raise ValueError('Mais de uma origem registrada para o mesmo mês.')
    # Linhas de conteúdo igual não são excluídas: posições distintas são identidades distintas.
    dimensions = ', '.join(quote(name) for name in COLUMNS)
    duplicates = con.execute(f'''SELECT "Ano e mês do lançamento", sum(n-1)
        FROM (SELECT {dimensions}, count(*) n FROM staging_despesas GROUP BY ALL HAVING count(*)>1)
        GROUP BY "Ano e mês do lançamento" ORDER BY 1''').fetchall()
    if con.execute('SELECT count(*), count(DISTINCT _linha_csv) FROM staging_despesas').fetchone() != (count, count):
        raise ValueError('Identidade/cardinalidade staging diverge da tabela analítica.')
    reconciliation = []
    for name in metrics:
        value = con.execute(f'SELECT sum(total) FROM (SELECT sum({name}) total FROM despesas_bi GROUP BY periodo)').fetchone()[0]
        if value != metrics[name][0]:
            raise ValueError('Soma dos meses não corresponde ao acumulado.')
        reconciliation.append({'comparacao': 'soma_mensal', 'medida': name, 'total': value,
                               'diferenca': value - metrics[name][0] if value is not None else None})
        for table in list(EXPORTS)[1:]:
            total = con.execute(f'SELECT sum({name}) FROM {table}').fetchone()[0]
            reconciliation.append({'comparacao': table, 'medida': name, 'total': total,
                                   'diferenca': total - metrics[name][0] if total is not None else None})
    return {'registros': count, 'mensal': result, 'valor_pago': str(metrics['valor_pago'][0]),
            'totais': {name: values[0] for name, values in metrics.items()},
            'negativos': {name: values[2] for name, values in metrics.items()},
            'reconciliacao_detalhada': reconciliation,
            'identidades_duplicadas': 0,
            'linhas_de_conteudo_repetido_preservadas': duplicates,
            'reconciliacao': 'Quatro medidas e contagens reconciliadas por mês e no acumulado.'}


def bootstrap(seed, database, january_zip):
    seed, database, january_zip = map(Path, (seed, database, january_zip))
    if seed.resolve() == database.resolve() or database.resolve() == (ROOT / 'data/brasil_em_dados.duckdb').resolve():
        raise ValueError('O banco original de janeiro está protegido.')
    if not seed.is_file() or not january_zip.is_file():
        raise ValueError('Banco validado e ZIP de janeiro são obrigatórios.')
    if sha256(january_zip) != JAN_HASH:
        raise ValueError('Hash de janeiro diverge da referência validada.')
    with duckdb.connect(str(seed), read_only=True) as con:
        data = con.execute('SELECT periodo, count(*), sum("Valor Pago (R$)") FROM despesas GROUP BY periodo').fetchall()
        if len(data) != 1 or str(data[0][0]) != '2026-01-01' or data[0][1:] != (JAN_ROWS, JAN_PAID):
            raise ValueError('Banco inicial não corresponde à validação de janeiro.')
        if con.execute('SELECT sha256, periodo, registros FROM carga_metadata').fetchall() != [(JAN_HASH, '2026/01', JAN_ROWS)]:
            raise ValueError('Proveniência de janeiro divergente.')
    if not database.exists():
        database.parent.mkdir(parents=True, exist_ok=True)
        before = sha256(seed)
        with seed.open('rb') as src, database.open('xb') as dst:
            shutil.copyfileobj(src, dst)
        if sha256(database) != before or sha256(seed) != before:
            raise ValueError('Banco inicial mudou durante a cópia; não continuar.')
    with duckdb.connect(str(database)) as con:
        current_jan = con.execute('SELECT count(*), sum("Valor Pago (R$)") FROM despesas WHERE periodo=DATE \'2026-01-01\'').fetchone()
        if current_jan != (JAN_ROWS, JAN_PAID):
            raise ValueError('Janeiro do banco incremental diverge da referência; carga bloqueada.')
        # Compara todas as células de janeiro com o snapshot, incluindo staging e IDs.
        con.execute("ATTACH '" + str(seed.resolve()).replace("'", "''") + "' AS baseline (READ_ONLY)")
        for table in ('despesas', 'staging_despesas'):
            for left, right in [(table, 'baseline.'+table), ('baseline.'+table, table)]:
                if con.execute(f'''SELECT * FROM {left} WHERE "Ano e mês do lançamento"='2026/01'
                    EXCEPT ALL SELECT * FROM {right} WHERE "Ano e mês do lançamento"='2026/01' ''').fetchall():
                    raise ValueError('Células de janeiro divergem do banco validado.')
        con.execute('CREATE TABLE IF NOT EXISTS incremental_control (version INTEGER)')
        if con.execute('SELECT count(*) FROM incremental_control').fetchone()[0] == 0:
            con.execute('INSERT INTO incremental_control VALUES (1)')
        validate_all(con)


def append_month(path, database, period):
    """Mesmo mês/hash é no-op. Alteração de arquivo exige revisão, nunca substitui."""
    path, database = Path(path), Path(database)
    if database.resolve() == (ROOT / 'data/brasil_em_dados.duckdb').resolve():
        raise ValueError('Banco original protegido.')
    if period == '2026/01':
        raise ValueError('Janeiro é incorporado apenas a partir do banco validado.')
    if not database.is_file():
        raise ValueError('Inicialize a cópia do banco antes de acrescentar meses.')
    digest = sha256(path)
    with duckdb.connect(str(database), read_only=True) as con:
        if not con.execute("SELECT count(*) FROM information_schema.tables WHERE table_name='incremental_control'").fetchone()[0]:
            raise ValueError('Banco não inicializado para atualização incremental.')
        old = con.execute('SELECT sha256 FROM carga_metadata WHERE periodo=?', [period]).fetchall()
        if old:
            if old != [(digest,)]:
                raise ValueError('Mês já carregado com outro hash; revisão manual necessária.')
            return {'periodo': period, 'status': 'já carregado; sem alterações'}
    with tempfile.TemporaryDirectory(prefix='brasil_mes_', dir=database.parent) as temporary:
        temp_db = Path(temporary) / 'mes.duckdb'
        loaded = load_data(path, temp_db, period=period)
        if loaded['sha256'] != digest:
            raise ValueError('ZIP mudou antes da carga.')
        if loaded['registros'] >= 1_000_000_000:
            raise ValueError('Mês excede espaço reservado para identificadores.')
        offset = int(period.replace('/', '')) * 1_000_000_000
        with duckdb.connect(str(database)) as con:
            con.execute('ATTACH ' + "'" + str(temp_db).replace("'", "''") + "' AS incoming (READ_ONLY)")
            con.execute('BEGIN TRANSACTION')
            try:
                if con.execute('SELECT count(*) FROM carga_metadata WHERE periodo=?', [period]).fetchone()[0]:
                    raise ValueError('Mês apareceu durante a carga; tente novamente.')
                for table in ('staging_despesas', 'despesas'):
                    con.execute(f'INSERT INTO {table} BY NAME SELECT * REPLACE (_linha_csv + {offset} AS _linha_csv) FROM incoming.{table}')
                con.execute('INSERT INTO carga_metadata SELECT * FROM incoming.carga_metadata')
                result = validate_all(con)
                if sha256(path) != digest:
                    raise ValueError('ZIP mudou durante a carga.')
                con.execute('COMMIT')
            except Exception:
                con.execute('ROLLBACK')
                raise
    return {'periodo': period, 'status': 'carregado', **result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw', type=Path, default=ROOT / 'data/raw')
    parser.add_argument('--seed', type=Path, default=ROOT / 'data/brasil_em_dados.duckdb')
    parser.add_argument('--database', type=Path, default=ROOT / 'data/brasil_em_dados_multimensal.duckdb')
    parser.add_argument('--start', default='202601')
    parser.add_argument('--end', default='202608')
    args = parser.parse_args()
    try:
        required = months(args.start, args.end)
        # Pré-validação evita apresentar execução incompleta como conjunto completo.
        for p in required:
            if not (args.raw / f'{p}_Despesas.zip').is_file():
                raise ValueError(f'Arquivo mensal ausente: {p}_Despesas.zip; nenhuma carga iniciada.')
        bootstrap(args.seed, args.database, args.raw / '202601_Despesas.zip')
        for p in required:
            if p != '202601':
                print(json.dumps(append_month(args.raw / f'{p}_Despesas.zip', args.database, p[:4]+'/'+p[4:]), default=str, ensure_ascii=False))
        with duckdb.connect(str(args.database), read_only=True) as con:
            print(json.dumps(validate_all(con), default=str, ensure_ascii=False, indent=2))
    except Exception as exc:
        print(f'Carga interrompida: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
