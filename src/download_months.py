"""Plano offline por padrão. A rede só é acessada com --execute."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import urllib.request
from urllib.parse import urlsplit
import zipfile
import csv
import io

try:
    from .load_data import ROOT, SOURCE, COLUMNS
except ImportError:
    from load_data import ROOT, SOURCE, COLUMNS


def months(start, end):
    if not all(re.fullmatch(r'\d{4}(0[1-9]|1[0-2])', s) for s in (start, end)) or start > end:
        raise ValueError('Intervalo inválido; use AAAAMM e início <= fim.')
    year, month = int(start[:4]), int(start[4:])
    result = []
    while f'{year:04}{month:02}' <= end:
        result.append(f'{year:04}{month:02}')
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return result


def plan(start='202602', end='202608'):
    periods = months(start, end)
    if '202601' in periods:
        raise ValueError('Janeiro de 2026 está protegido: não baixar novamente.')
    return [{'periodo': p, 'arquivo': f'{p}_Despesas.zip', 'url': SOURCE + '/' + p} for p in periods]


class OfficialRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urlsplit(newurl)
        if parsed.scheme != 'https' or parsed.hostname != 'portaldatransparencia.gov.br':
            raise ValueError('Redirecionamento fora do domínio oficial; revisar URL antes de continuar.')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(item, output, opener=None):
    """Não sobrescreve ZIP/manifesto; mantém .part se houver falha para inspeção."""
    output = Path(output)
    target = output / item['arquivo']
    partial = output / (item['arquivo'] + '.part')
    manifest = output / (item['arquivo'] + '.json')
    if any(p.exists() for p in (target, partial, manifest)):
        raise ValueError(f'Arquivo existente para {item["periodo"]}; nada será sobrescrito.')
    output.mkdir(parents=True, exist_ok=True)
    opener = opener or urllib.request.build_opener(OfficialRedirect()).open
    digest = hashlib.sha256()
    size = 0
    with opener(item['url'], timeout=90) as response:
        if response.status != 200:
            raise ValueError(f'HTTP inesperado: {response.status}')
        if urlsplit(response.geturl()).hostname != 'portaldatransparencia.gov.br':
            raise ValueError('Origem final não autorizada.')
        mime = response.headers.get('Content-Type', '').split(';')[0].lower()
        if mime not in ('application/zip', 'application/x-zip-compressed', 'application/octet-stream'):
            raise ValueError(f'Formato HTTP inesperado: {mime!r}')
        length = response.headers.get('Content-Length')
        with partial.open('xb') as out:
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > 512 * 1024 * 1024:
                    raise ValueError('ZIP excede limite preventivo de 512 MiB; revisar antes de continuar.')
                digest.update(chunk)
                out.write(chunk)
        if length is not None and size != int(length):
            raise ValueError('Download incompleto: tamanho diverge de Content-Length.')
    with zipfile.ZipFile(partial) as archive:
        entries = archive.infolist()
        if len(entries) != 1 or entries[0].filename != item['arquivo'].replace('.zip', '.csv'):
            raise ValueError('ZIP inesperado: esperado um único CSV mensal com nome correspondente.')
        if entries[0].file_size > 2 * 1024**3 or entries[0].flag_bits & 1:
            raise ValueError('CSV excede 2 GiB ou está criptografado.')
        if archive.testzip() is not None:
            raise ValueError('CRC inválido no ZIP.')
        with archive.open(entries[0]) as binary, io.TextIOWrapper(binary, encoding='cp1252', newline='') as stream:
            header = next(csv.reader(stream, delimiter=';'), [])
            if len(header) != len(COLUMNS) or set(header) != set(COLUMNS):
                raise ValueError('Cabeçalho diferente das 47 colunas esperadas; revisar fonte.')
    # Windows: rename recusa destino existente. Não usar replace.
    if target.exists():
        raise ValueError('Destino apareceu durante a coleta; operação interrompida.')
    partial.rename(target)
    record = {**item, 'bytes': size, 'coletado_em_utc': datetime.now(timezone.utc).isoformat(),
              'sha256': digest.hexdigest(), 'origem': SOURCE}
    with manifest.open('x', encoding='utf-8') as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start', default='202602')
    parser.add_argument('--end', default='202608')
    parser.add_argument('--output', type=Path, default=ROOT / 'data/raw')
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    try:
        items = plan(args.start, args.end)
        if args.execute:
            for item in items:
                print(json.dumps(fetch(item, args.output), ensure_ascii=False))
        else:
            print(json.dumps({'modo': 'PLANO; nenhuma conexão de rede', 'arquivos': items}, ensure_ascii=False, indent=2))
    except Exception as exc:
        print(f'Coleta interrompida: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
