"""Exportação multimensal isolada; recusa intervalos incompletos."""
import argparse
import json
from datetime import datetime
from pathlib import Path
import shutil
import sys
import duckdb
try:
    from .load_months import ROOT, validate_all, MONTH_SQL
    from .download_months import months
    from .export_powerbi import export_data, EXPORTS
    from .load_data import sha256
    from .audit_months import reconcile_inventory
except ImportError:
    from load_months import ROOT, validate_all, MONTH_SQL
    from download_months import months
    from export_powerbi import export_data, EXPORTS
    from load_data import sha256
    from audit_months import reconcile_inventory


def export_months(database, output, start='202601', end='202608', inventory=None):
    output = Path(output)
    if output.resolve() == (ROOT / 'data/processed').resolve():
        raise ValueError('Exportação original protegida; use uma subpasta multimensal.')
    expected = [p[:4]+'/'+p[4:] for p in months(start, end)]
    with duckdb.connect(str(database), read_only=True) as con:
        actual = [r[0] for r in con.execute('SELECT DISTINCT strftime(periodo,\'%Y/%m\') FROM despesas ORDER BY 1').fetchall()]
        if actual != expected:
            raise ValueError(f'Períodos da base {actual} diferem do intervalo solicitado {expected}.')
        validation = validate_all(con)
        if inventory is not None:
            validation['reconciliacao_zip_independente'] = reconcile_inventory(con, inventory)
        queries = {}
        for path in sorted(MONTH_SQL.glob('*.sql')):
            if path.name.startswith('01_'):
                continue
            cursor = con.execute(path.read_text(encoding='utf-8'), [start[:4]+'-'+start[4:]+'-01', end[:4]+'-'+end[4:]+'-01'])
            names = [c[0] for c in cursor.description]
            queries[path.name] = [dict(zip(names, row)) for row in cursor.fetchall()]
    result = export_data(database, output)
    (output / 'validacao_mensal.json').write_text(json.dumps({'validacao': validation, 'consultas': queries}, default=str, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    files = [f'{name}.csv' for name in EXPORTS] + ['validacao_exportacao.json', 'validacao_mensal.json']
    (output / 'manifesto_exportacao.json').write_text(json.dumps({name: sha256(output/name) for name in files}, indent=2)+'\n', encoding='utf-8')
    return result


def promote_export(source, output):
    """Promove arquivos validados com backup; não altera o PBIP nem a base de janeiro."""
    source, output = Path(source).resolve(), Path(output).resolve()
    if source == output:
        raise ValueError('Origem intermediária deve ser diferente da saída principal.')
    manifest = json.loads((source/'manifesto_exportacao.json').read_text(encoding='utf-8'))
    expected = {f'{name}.csv' for name in EXPORTS} | {'validacao_exportacao.json', 'validacao_mensal.json'}
    if set(manifest) != expected:
        raise ValueError('Manifesto de exportação incompleto ou inesperado.')
    for name, digest in manifest.items():
        if sha256(source/name) != digest:
            raise ValueError(f'Arquivo alterado após validação: {name}')
    validation = json.loads((source/'validacao_mensal.json').read_text(encoding='utf-8'))['validacao']
    if not validation['mensal'] or any(x['diferenca'] not in ('0.00', None) for x in validation['reconciliacao_detalhada']):
        raise ValueError('Reconciliação inválida; saída principal preservada.')
    files = sorted(expected | {'manifesto_exportacao.json'})
    changed = [name for name in files if not (output/name).exists() or sha256(output/name) != sha256(source/name)]
    if not changed:
        return {'status': 'saída principal já corresponde à exportação; sem alterações'}
    output.mkdir(parents=True, exist_ok=True)
    backup = output/'backups'/('exportacao_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    backup.mkdir(parents=True, exist_ok=False)
    for name in changed:
        if (output/name).exists():
            shutil.copy2(output/name, backup/name)
            if sha256(output/name) != sha256(backup/name):
                raise ValueError('Falha na verificação do backup; promoção cancelada.')
    # Cada substituição usa um arquivo completo. Backup permite recuperar o conjunto.
    try:
        for name in changed:
            pending = output/(name+'.multimensal-pending')
            with (source/name).open('rb') as src, pending.open('xb') as dst:
                shutil.copyfileobj(src, dst)
            if sha256(pending) != sha256(source/name):
                raise ValueError('Falha ao copiar arquivo validado.')
            pending.replace(output/name)
    except Exception:
        # Recupera somente arquivos anteriormente existentes, sem remover dados.
        for name in changed:
            if (backup/name).is_file():
                shutil.copy2(backup/name, output/name)
        raise
    return {'status': 'saída principal atualizada', 'backup': str(backup), 'arquivos': changed}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=ROOT / 'data/brasil_em_dados_multimensal.duckdb')
    parser.add_argument('--output', type=Path, default=ROOT / 'data/processed/multimensal')
    parser.add_argument('--start', default='202601')
    parser.add_argument('--end', default='202608')
    parser.add_argument('--promote-primary', action='store_true', help='Após validar, atualiza data/processed com backup dos arquivos anteriores.')
    parser.add_argument('--inventory', type=Path, default=ROOT/'data/processed/inspecao_multimensal.json')
    args = parser.parse_args()
    try:
        inventory = json.loads(args.inventory.read_text(encoding='utf-8'))
        print(json.dumps(export_months(args.database, args.output, args.start, args.end, inventory), ensure_ascii=False, indent=2))
        if args.promote_primary:
            print(json.dumps(promote_export(args.output, ROOT/'data/processed'), ensure_ascii=False, indent=2))
    except Exception as exc:
        print(f'Exportação interrompida: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
