"""Exportação de dados fictícios, sem dependência do banco real."""
import csv
import io
from pathlib import Path
import tempfile
import unittest
import zipfile

import duckdb

from src.export_powerbi import export_data
from src.load_data import COLUMNS, MONEY_COLUMNS, load_data, sha256


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = self.root / 'teste.duckdb'
        self.out = self.root / 'processed'
        text = io.StringIO(newline='')
        writer = csv.writer(text, delimiter=';')
        writer.writerow(COLUMNS)
        for index, (program, paid) in enumerate([('0905', '12,50'), ('0906', '-2,50'), ('0907', ''), ('0908', '0,00'), ('0909', '1,00')]):
            row = {name: 'Nome fictício; "teste"\ncontinuação' for name in COLUMNS}
            row.update({name: '0001' for name in COLUMNS if name.startswith('Código')})
            row.update({name: '0,00' for name in MONEY_COLUMNS})
            row['Ano e mês do lançamento'] = '2026/01'
            row['Código Programa Orçamentário'] = program
            row['Código Órgão Superior'] = '0001' if index % 2 else '0002'
            row['Código Grupo de Despesa'] = '6'
            row['Valor Pago (R$)'] = paid
            row['Valor Restos a Pagar Pagos (R$)'] = '-1,00'
            writer.writerow([row[name] for name in COLUMNS])
        archive = self.root / 'ficticio.zip'
        with zipfile.ZipFile(archive, 'w') as z:
            z.writestr('ficticio.csv', text.getvalue().encode('cp1252'))
        load_data(archive, self.db)

    def test_export_reconciliation_codes_signs_and_rerun(self):
        original = sha256(self.db)
        first = export_data(self.db, self.out)
        self.assertEqual(first['registros_origem'], 5)
        for result in first['arquivos'].values():
            self.assertEqual(result['valor_pago'], '11.00')
            self.assertEqual(result['diferenca'], '0.00')
        self.assertEqual(first['negativos_principal']['valor_pago'], 1)
        self.assertEqual(first['negativos_principal']['valor_restos_pagos'], 5)
        path = self.out / 'despesas_bi.csv'
        with path.open(encoding='utf-8-sig', newline='') as stream:
            rows = list(csv.DictReader(stream, delimiter=';'))
        self.assertEqual(len(rows), 5)
        self.assertEqual([r['valor_pago'] for r in rows], ['12.50', '-2.50', '', '0.00', '1.00'])
        self.assertEqual(rows[0]['codigo_programa'], '0905')
        self.assertEqual(rows[0]['codigo_acao'], '0001')
        self.assertIn('\n', rows[0]['nome_acao'])
        self.assertTrue(all(r['classificacao_programa_divida'] == 'Programa específico de dívida' for r in rows[:4]))
        self.assertEqual(rows[4]['classificacao_programa_divida'], 'Demais programas')
        self.assertEqual(rows[4]['codigo_grupo_despesa'], '6')
        old_csv = path.read_bytes()
        self.assertEqual(export_data(self.db, self.out), first)
        self.assertEqual(path.read_bytes(), old_csv)
        self.assertEqual(sha256(self.db), original)

    def test_duplicate_identity_is_rejected(self):
        with duckdb.connect(str(self.db)) as con:
            con.execute('INSERT INTO despesas SELECT * FROM despesas LIMIT 1')
        with self.assertRaisesRegex(ValueError, 'multiplicação'):
            export_data(self.db, self.out)
        self.assertFalse(self.out.exists())

    def test_missing_column_is_rejected(self):
        with duckdb.connect(str(self.db)) as con:
            con.execute('ALTER TABLE despesas DROP COLUMN "Nome Função"')
        with self.assertRaises(duckdb.Error):
            export_data(self.db, self.out)
        self.assertFalse(self.out.exists())


if __name__ == '__main__':
    unittest.main()
