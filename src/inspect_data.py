"""Inspeciona CSVs locais sem extrair ZIPs ou converter códigos em números."""

import argparse
import codecs
import csv
import io
import json
from contextlib import ExitStack
from itertools import islice
from pathlib import Path
import sys
import zipfile


SAMPLE_BYTES = 65536
SAMPLE_ROWS = 3
# Nomes conferidos no cabeçalho de 202601_Despesas.csv, dentro do ZIP local.
SAMPLE_COLUMNS = (
    "Ano e mês do lançamento",
    "Nome Órgão Superior",
    "Nome Programa Orçamentário",
    "Nome Ação",
    "Valor Pago (R$)",
)


class InspectionError(ValueError):
    """Entrada inválida ou formato que não pôde ser identificado."""


def detect_encoding(sample):
    """BOM é conclusivo; sem BOM, a identificação é uma estimativa."""
    for bom, encoding in (
        (codecs.BOM_UTF32_LE, "utf-32"),
        (codecs.BOM_UTF32_BE, "utf-32"),
        (codecs.BOM_UTF8, "utf-8-sig"),
        (codecs.BOM_UTF16_LE, "utf-16"),
        (codecs.BOM_UTF16_BE, "utf-16"),
    ):
        if sample.startswith(bom):
            return encoding
    for encoding in ("utf-8", "cp1252", "latin-1"):
        try:
            codecs.getincrementaldecoder(encoding)().decode(sample, final=False)
            return encoding
        except UnicodeDecodeError:
            continue


def inspect_stream(stream, encoding=None, delimiter=None):
    # A sondagem tem tamanho fixo, inclusive para arquivos comprimidos.
    sample = stream.read(SAMPLE_BYTES)
    if not sample:
        raise InspectionError("O CSV está vazio.")
    chosen_encoding = encoding or detect_encoding(sample)
    text = codecs.getincrementaldecoder(chosen_encoding)().decode(sample, final=False)
    if any(ord(char) < 32 and char not in "\r\n\t" for char in text):
        raise InspectionError("Conteúdo binário ou codificação incompatível; use --encoding.")
    if delimiter is None:
        # O cabeçalho evita que um registro cortado no fim da sondagem interfira.
        try:
            delimiter = csv.Sniffer().sniff(text.splitlines()[0], delimiters=";,\t|").delimiter
        except (csv.Error, IndexError) as exc:
            raise InspectionError(
                "Separador não identificado; informe --delimiter (também para CSV de uma coluna)."
            ) from exc
    if len(delimiter) != 1 or delimiter in "\r\n":
        raise InspectionError("O separador deve ser um único caractere, sem quebra de linha.")
    stream.seek(0)
    wrapper = io.TextIOWrapper(stream, encoding=chosen_encoding, newline="")
    try:
        reader = csv.reader(wrapper, delimiter=delimiter, strict=True)
        columns = next(reader, None)
        if not columns or any(not name.strip() for name in columns):
            raise InspectionError("O CSV precisa ter um cabeçalho com nomes de colunas não vazios.")
        rows = list(islice(reader, SAMPLE_ROWS))
        for index, row in enumerate(rows, start=1):
            if len(row) != len(columns):
                raise InspectionError(
                    f"Registro {index}: esperadas {len(columns)} colunas, encontradas {len(row)}."
                )
        return {"encoding": chosen_encoding, "delimiter": delimiter, "columns": columns, "rows": rows}
    finally:
        wrapper.detach()


def inspect_file(path, member=None, encoding=None, delimiter=None):
    path = Path(path)
    if not path.is_file():
        raise InspectionError(f"Arquivo não encontrado ou não é um arquivo regular: {path}")
    with ExitStack() as stack:
        if path.suffix.lower() == ".zip":
            archive = stack.enter_context(zipfile.ZipFile(path))
            entries = archive.infolist()
            print("Arquivos internos do ZIP:")
            for entry in entries:
                print(f"  {entry.filename!r} ({entry.file_size} bytes)")
            candidates = [e for e in entries if not e.is_dir() and e.filename.lower().endswith(".csv")]
            if not candidates:
                raise InspectionError("O ZIP não contém arquivos CSV.")
            if member is not None:
                matches = [e for e in candidates if e.filename == member]
                if len(matches) != 1:
                    raise InspectionError("--member deve identificar exatamente um CSV dentro do ZIP.")
                selected = matches[0]
            elif len(candidates) == 1:
                selected = candidates[0]
            else:
                for index, entry in enumerate(candidates, start=1):
                    print(f"  [{index}] {entry.filename!r}")
                try:
                    choice = int(input("Selecione o número do CSV: "))
                except (ValueError, EOFError) as exc:
                    raise InspectionError("Seleção inválida; informe um número ou use --member.") from exc
                if not 1 <= choice <= len(candidates):
                    raise InspectionError("Número de seleção fora do intervalo.")
                selected = candidates[choice - 1]
            print(f"CSV selecionado: {selected.filename!r}")
            stream = stack.enter_context(archive.open(selected))
        elif path.suffix.lower() == ".csv":
            if member is not None:
                raise InspectionError("--member só se aplica a arquivos ZIP.")
            stream = stack.enter_context(path.open("rb"))
        else:
            raise InspectionError("Formato inválido: informe um arquivo .csv ou .zip.")
        return inspect_stream(stream, encoding, delimiter)


def display_result(result):
    """Projeta somente a apresentação; mantém colunas e valores originais."""
    print(f"Codificação: {result['encoding']} (estimada quando não há BOM; ajustável com --encoding)")
    print(f"Separador: {result['delimiter']!r}")
    print(f"Quantidade de colunas: {len(result['columns'])}")
    print("Colunas:")
    for index, name in enumerate(result["columns"], start=1):
        print(f"  {index:02d}. {name}")

    selected = []
    for name in SAMPLE_COLUMNS:
        if name not in result["columns"]:
            print(f"Aviso: coluna ausente no cabeçalho: {name}")
        else:
            selected.append((name, result["columns"].index(name)))
    if not selected:
        print("Amostra indisponível: nenhuma das colunas solicitadas existe no cabeçalho.")
        return
    rows = result["rows"][:SAMPLE_ROWS]
    print(f"\nAmostra: {len(rows)} registros (máximo de {SAMPLE_ROWS}, além do cabeçalho):")
    for index, row in enumerate(rows, start=1):
        print(f"\nRegistro {index}:")
        for name, position in selected:
            print(f"  {name}: {json.dumps(row[position], ensure_ascii=False)}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="Caminho do CSV ou ZIP local")
    parser.add_argument("--member", help="Nome completo do CSV dentro do ZIP")
    parser.add_argument("--encoding", help="Substitui a estimativa automática, por exemplo cp1252")
    parser.add_argument("--delimiter", help="Substitui o separador automático, por exemplo ';'")
    args = parser.parse_args(argv)
    try:
        result = inspect_file(args.path, args.member, args.encoding, args.delimiter)
    except (InspectionError, OSError, UnicodeError, LookupError, csv.Error,
            zipfile.BadZipFile, RuntimeError, NotImplementedError, EOFError) as exc:
        print(f"Erro ao inspecionar: {exc}", file=sys.stderr)
        return 1
    display_result(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
