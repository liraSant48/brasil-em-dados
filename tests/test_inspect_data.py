"""Somente dados fictícios, criados em diretório temporário."""

import csv
import copy
from contextlib import redirect_stdout, redirect_stderr
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from src.inspect_data import (
    InspectionError, SAMPLE_BYTES, SAMPLE_COLUMNS, display_result,
    inspect_file, inspect_stream, main,
)


class InspectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def csv(self, content, encoding="utf-8"):
        path = self.root / "ficticio.csv"
        path.write_bytes(content.encode(encoding))
        return path

    def test_encodings_and_separators(self):
        for encoding in ("utf-8", "utf-8-sig", "cp1252", "utf-16", "utf-32"):
            for delimiter in (";", ",", "\t", "|"):
                with self.subTest(encoding=encoding, delimiter=delimiter):
                    result = inspect_file(self.csv(f"código{delimiter}nome\n0001{delimiter}Órgão fictício\n", encoding))
                    self.assertEqual(result["rows"], [["0001", "Órgão fictício"]])
                    self.assertEqual(result["delimiter"], delimiter)
                    self.assertEqual(result["columns"], ["código", "nome"])

    def test_three_records_only(self):
        result = inspect_file(self.csv("codigo;nome\n" + "001;Fictício\n" * 3 + '"registro inválido'))
        self.assertEqual(len(result["rows"]), 3)

    def test_quoted_and_multiline_fields(self):
        result = inspect_file(self.csv('codigo;nome\n001;"Texto; fictício\ncontinuação"\n'))
        self.assertEqual(result["rows"], [["001", "Texto; fictício\ncontinuação"]])

    def test_bounded_read(self):
        class BoundedStream(io.BytesIO):
            def read(self, size=-1):
                self.assert_size(size)
                return super().read(size)

            def assert_size(self, size):
                if size < 0 or size > SAMPLE_BYTES:
                    raise AssertionError("Leitura sem limite")

        stream = BoundedStream(b"codigo;nome\n" + b"001;ficticio\n" * 100000)
        self.assertEqual(len(inspect_stream(stream)["rows"]), 3)
        self.assertLess(stream.tell(), SAMPLE_BYTES)

    def make_zip(self, files):
        path = self.root / "ficticio.zip"
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, content in files.items():
                archive.writestr(name, content)
        return path

    def test_zip_selection_and_listing(self):
        path = self.make_zip({"nota.txt": "fictício", "a.csv": "id;nome\n001;A", "pasta/b.CSV": "id;nome\n002;B"})
        output = io.StringIO()
        with redirect_stdout(output), patch("builtins.input", return_value="2"):
            result = inspect_file(path)
        self.assertEqual(result["rows"][0][0], "002")
        self.assertIn("nota.txt", output.getvalue())
        with redirect_stdout(io.StringIO()):
            self.assertEqual(inspect_file(path, member="a.csv")["rows"][0][0], "001")
            with self.assertRaises(InspectionError):
                inspect_file(path, member="ausente.csv")
            with patch("builtins.input", return_value="0"), self.assertRaises(InspectionError):
                inspect_file(path)
        self.assertFalse((self.root / "pasta").exists())

    def test_zip_single_csv_and_no_csv(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(inspect_file(self.make_zip({"a.csv": "id;nome\n001;A"}))["rows"], [["001", "A"]])
            with self.assertRaises(InspectionError):
                inspect_file(self.make_zip({"nota.txt": "texto"}))

    def test_invalid_csvs(self):
        for content in ("", "id;nome\n001", 'id;nome\n001;"aberto', "id;\n001;A", "\x00\x01"):
            with self.subTest(content=content), self.assertRaises((InspectionError, csv.Error)):
                inspect_file(self.csv(content))

    def test_single_column_override(self):
        result = inspect_file(self.csv("codigo\n0001\n"), delimiter=";", encoding="utf-8")
        self.assertEqual(result["rows"], [["0001"]])

    def test_cli_errors(self):
        invalid_zip = self.root / "invalido.zip"
        invalid_zip.write_bytes(b"nao e zip")
        invalid_extension = self.root / "arquivo.txt"
        invalid_extension.write_text("texto")
        for path in (self.root / "ausente.csv", invalid_zip, invalid_extension):
            with self.subTest(path=path), redirect_stderr(io.StringIO()) as errors:
                self.assertEqual(main([str(path)]), 1)
                self.assertIn("Erro ao inspecionar:", errors.getvalue())

    def test_cli_output(self):
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main([str(self.csv("id;nome\n0001;Fictício"))]), 0)
        self.assertIn("Quantidade de colunas: 2", output.getvalue())
        self.assertIn("  01. id\n  02. nome\n", output.getvalue())
        self.assertIn("Amostra indisponível", output.getvalue())
        for name in SAMPLE_COLUMNS:
            self.assertIn(f"Aviso: coluna ausente no cabeçalho: {name}", output.getvalue())

    def test_selected_columns_and_original_values(self):
        # Ordem diferente do cabeçalho real e coluna extra para testar a projeção.
        columns = ["Código fictício", *reversed(SAMPLE_COLUMNS)]
        row = ["00001", "0012,30", "Ação fictícia", "Programa fictício", "Órgão fictício", "2026/01"]
        path = self.csv(";".join(columns) + "\n" + (";".join(row) + "\n") * 4)
        original = path.read_bytes()
        result = inspect_file(path)
        before = copy.deepcopy(result)
        with redirect_stdout(io.StringIO()) as output:
            display_result(result)
        text = output.getvalue()
        self.assertEqual(result, before)
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(result["rows"][0][0], "00001")
        self.assertEqual(text.count("\nRegistro "), 3)
        sample = text.split("\nAmostra:", 1)[1]
        self.assertNotIn("Código fictício", sample)
        self.assertNotIn("00001", sample)
        self.assertIn('Valor Pago (R$): "0012,30"', sample)
        self.assertNotIn("total", sample.lower())
        for index, name in enumerate(columns, start=1):
            self.assertIn(f"  {index:02d}. {name}\n", text)
        for name in SAMPLE_COLUMNS:
            self.assertEqual(sample.count(f"  {name}:"), 3)

    def test_partial_missing_columns(self):
        path = self.csv("Valor Pago (R$);codigo\n0005,00;001")
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main([str(path)]), 0)
        text = output.getvalue()
        self.assertEqual(text.count("Aviso: coluna ausente"), 4)
        self.assertIn('Valor Pago (R$): "0005,00"', text)
        self.assertIn("Amostra: 1 registros", text)

    def test_header_without_records(self):
        with redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main([str(self.csv(";".join(SAMPLE_COLUMNS)))]), 0)
        self.assertIn("Amostra: 0 registros", output.getvalue())
        self.assertNotIn("Registro 1:", output.getvalue())


if __name__ == "__main__":
    unittest.main()
