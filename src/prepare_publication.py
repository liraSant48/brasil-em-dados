"""Audita e prepara uma cópia revisável para publicação. Não executa Git ou rede.

A fonte M é anonimizada SOMENTE na cópia; o projeto de trabalho é preservado.
O destino precisa ser novo e fica sob data/processed (ignorado pelo Git).
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = ('.gitignore', 'README.md', 'requirements.txt', 'RESULTADOS_JANEIRO_2026.md')
FOLDERS = ('src', 'sql', 'tests', 'docs', 'powerbi')
SKIP_DIRS = {'.git', '.venv', 'venv', 'env', '__pycache__', '.pytest_cache', '.local', 'backups', 'backup', 'credentials', 'secrets'}
SKIP_FILES = {'localSettings.json', 'cache.abf', '.DS_Store', 'Thumbs.db', 'Desktop.ini', 'tokens.json', '.env'}
ALLOWED = {'.py', '.ps1', '.sql', '.md', '.json', '.pbip', '.pbir', '.pbism', '.tmdl', '.png', '.jpg', '.jpeg', '.svg'}
SECRET = re.compile(r'ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|(?i:Bearer)\s+[A-Za-z0-9_.-]{20,}')
PRIVATE_PATH = re.compile(r'[A-Za-z]:[\\/]+Users[\\/]+[^\\/"\s]+', re.I)
EMAIL = re.compile(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}')


def candidates(root=None):
    root = ROOT if root is None else Path(root)
    result = [root / name for name in ROOT_FILES if (root / name).is_file()]
    for folder in FOLDERS:
        for path in (root / folder).rglob('*'):
            if not path.is_file() or any(part in SKIP_DIRS for part in path.relative_to(root).parts):
                continue
            if path.name in SKIP_FILES or path.name.startswith(('.env', 'credentials', 'secrets', 'client_secret', 'service-account')):
                continue
            if '.pbi' in path.parts and path.name != 'editorSettings.json':
                continue
            if path.suffix.lower() in ALLOWED or path.name in ('.platform', '.gitkeep'):
                result.append(path)
    return sorted(result)


def audit(root=None):
    root = ROOT if root is None else Path(root)
    findings = []
    files = candidates(root)
    for path in files:
        rel = str(path.relative_to(root))
        if path.stat().st_size > 10 * 1024 * 1024:
            findings.append({'arquivo': rel, 'tipo': 'arquivo_maior_10_MiB'})
        if path.suffix.lower() in ('.png', '.jpg', '.jpeg'):
            continue
        text = path.read_text(encoding='utf-8-sig')
        # Somente localização/tipo: nunca imprime o possível segredo.
        for number, line in enumerate(text.splitlines(), 1):
            for kind, pattern in [('caminho_pessoal', PRIVATE_PATH), ('possivel_email', EMAIL), ('possivel_segredo', SECRET)]:
                if pattern.search(line):
                    findings.append({'arquivo': rel, 'linha': number, 'tipo': kind})
    return {'arquivos_candidatos': len(files), 'maior_arquivo_bytes': max((p.stat().st_size for p in files), default=0), 'achados': findings}


def prepare(destination):
    destination = Path(destination).resolve()
    allowed_root = (ROOT / 'data/processed').resolve()
    if not destination.is_relative_to(allowed_root) or destination == allowed_root or destination.exists():
        raise ValueError('O destino deve ser uma pasta nova dentro de data/processed.')
    source_audit = audit()
    if any(f['tipo'] in ('possivel_segredo', 'arquivo_maior_10_MiB') for f in source_audit['achados']):
        raise ValueError('Auditoria encontrou possível segredo ou arquivo grande; revisar antes de preparar.')
    destination.mkdir(parents=True)
    hashes = {}
    for source in candidates():
        rel = source.relative_to(ROOT)
        target = destination / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        hashes[str(rel)] = hashlib.sha256(source.read_bytes()).hexdigest()
        shutil.copy2(source, target)
    tmdl = destination / 'powerbi/Brasil_em_Dados.SemanticModel/definition/tables/despesas_bi.tmdl'
    content = tmdl.read_text(encoding='utf-8')
    content, changes = re.subn(r'File\.Contents\("[^"]*despesas_bi\.csv"\)',
        lambda _: 'File.Contents("C:\\CONFIGURAR_CAMINHO\\brasil-em-dados\\data\\processed\\despesas_bi.csv")', content)
    if changes != 1:
        raise ValueError('Fonte inesperada: cópia não está pronta; nenhuma alteração na fonte local foi feita.')
    tmdl.write_text(content, encoding='utf-8')
    for rel in ('data/raw/.gitkeep', 'data/processed/.gitkeep'):
        path = destination / rel; path.parent.mkdir(parents=True, exist_ok=True); path.touch()
    result = audit(destination)
    if result['achados']:
        raise ValueError('A cópia ainda tem achados: ' + json.dumps(result['achados']))
    assert all(hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == digest for rel, digest in hashes.items())
    # Manifesto fica ao lado da cópia, não entre arquivos destinados ao Git.
    (destination.parent / (destination.name + '_audit.json')).write_text(json.dumps(
        {'origem': source_audit, 'copia': result, 'fonte_anonimizada_na_copia': True, 'arquivos_originais_inalterados': True},
        ensure_ascii=False, indent=2), encoding='utf-8')
    return {'copia': str(destination), **result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true', help='Cria cópia nova, sem git init/add/commit/push')
    args = parser.parse_args()
    result = prepare(ROOT / 'data/processed' / ('publicacao_' + datetime.now().strftime('%Y%m%d_%H%M%S'))) if args.prepare else audit()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
