"""Integridade em ZIPs fictícios; não depende do arquivo oficial."""

import csv
from decimal import Decimal
import io
from pathlib import Path
import tempfile
import unittest
import zipfile

import duckdb

from src.load_data import COLUMNS, MONEY_COLUMNS, SQL, load_data, report, sha256


class LoadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = self.root / 'teste.duckdb'
        self.zip = self.root / 'ficticio.zip'

    def row(self, paid='1.234,56'):
        row = {name: 'Fictício' for name in COLUMNS}
        for name in COLUMNS:
            if name.startswith('Código'):
                row[name] = '00001'
        for name in MONEY_COLUMNS:
            row[name] = '0,00'
        row['Ano e mês do lançamento'] = '2026/01'
        row['Valor Pago (R$)'] = paid
        row['Valor Empenhado (R$)'] = '2.000,00'
        row['Valor Liquidado (R$)'] = '1.500,00'
        row['Valor Restos a Pagar Pagos (R$)'] = '500,00'
        return row

    def write_zip(self, rows, header=None):
        header = COLUMNS if header is None else header
        text = io.StringIO(newline='')
        writer = csv.writer(text, delimiter=';')
        writer.writerow(header)
        for row in rows:
            writer.writerow([row[name] for name in header])
        with zipfile.ZipFile(self.zip, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('ficticio.csv', text.getvalue().encode('cp1252'))

    def test_full_load_types_nulls_negatives_and_reexecution(self):
        rows = [self.row(value) for value in ('1.234,56', '-234,56', '', '0,00', '0,00')]
        self.write_zip(rows, list(reversed(COLUMNS)))
        original = sha256(self.zip)
        for _ in range(2):
            self.assertEqual(load_data(self.zip, self.db, batch_size=2)['registros'], 5)
            with duckdb.connect(str(self.db), read_only=True) as con:
                self.assertEqual(con.execute('SELECT count(*) FROM staging_despesas').fetchone()[0], 5)
                schema = dict(con.execute('DESCRIBE staging_despesas').fetchall()[i][:2] for i in range(48))
                self.assertTrue(all(schema[name] == 'VARCHAR' for name in COLUMNS))
                values = con.execute('SELECT "Valor Pago (R$)", "Código Ação" FROM despesas ORDER BY _linha_csv').fetchall()
                self.assertEqual([v[0] for v in values], [Decimal('1234.56'), Decimal('-234.56'), None, Decimal('0'), Decimal('0')])
                self.assertTrue(all(v[1] == '00001' for v in values))
                self.assertEqual(con.execute('SELECT "Valor Pago (R$)" FROM staging_despesas WHERE _linha_csv=3').fetchone()[0], '')
                totals = con.execute((SQL / '03_totals.sql').read_text(encoding='utf-8')).fetchone()
                self.assertEqual(totals[:4], (5, Decimal('10000'), Decimal('7500'), Decimal('1000')))
                self.assertEqual(totals[-1], Decimal('2500'))
                duplicates = con.execute((SQL / '08_duplicates.sql').read_text(encoding='utf-8')).fetchone()
                self.assertEqual(duplicates, (1, 1))
                self.assertEqual(con.execute('SELECT registros, sha256 FROM carga_metadata').fetchall(), [(5, original)])
                for name in MONEY_COLUMNS:
                    self.assertEqual(con.execute(f'SELECT typeof("{name}") FROM despesas LIMIT 1').fetchone()[0], 'DECIMAL(20,2)')
            self.assertIn('09_dimensions.sql', report(self.db))
        self.assertEqual(sha256(self.zip), original)
        self.assertFalse((self.root / 'ficticio.csv').exists())

    def test_invalid_values_rollback(self):
        self.write_zip([self.row()])
        load_data(self.zip, self.db)
        for value in ('1,234', '12.34,56', 'abc', '1e3', '1000000000000000000,00'):
            with self.subTest(value=value):
                self.write_zip([self.row('0'), self.row(value)])
                with self.assertRaises(ValueError):
                    load_data(self.zip, self.db, batch_size=1)
                with duckdb.connect(str(self.db), read_only=True) as con:
                    self.assertEqual(con.execute('SELECT "Valor Pago (R$)" FROM despesas').fetchall(), [(Decimal('1234.56'),)])
                    self.assertEqual(con.execute('SELECT count(*) FROM staging_despesas').fetchone()[0], 1)

    def test_invalid_header_and_period(self):
        for header in (COLUMNS[:-1], COLUMNS + [COLUMNS[0]]):
            self.write_zip([self.row()], header)
            with self.assertRaisesRegex(ValueError, 'Cabeçalho'):
                load_data(self.zip, self.db)
        row = self.row()
        row['Ano e mês do lançamento'] = '2026/02'
        self.write_zip([row])
        with self.assertRaisesRegex(ValueError, 'período'):
            load_data(self.zip, self.db)

    def test_empty_and_malformed_rows(self):
        self.write_zip([])
        with self.assertRaisesRegex(ValueError, 'sem registros'):
            load_data(self.zip, self.db)
        with zipfile.ZipFile(self.zip, 'w') as archive:
            archive.writestr('ficticio.csv', (';'.join(COLUMNS) + '\n001;faltando\n').encode('cp1252'))
        with self.assertRaisesRegex(ValueError, '47 colunas'):
            load_data(self.zip, self.db)

    def test_sql_decimal_rules(self):
        with duckdb.connect() as con:
            con.execute('CREATE TABLE staging_despesas (' + ','.join('"' + name + '" VARCHAR' for name in COLUMNS) + ')')
            con.execute((SQL / '01_build_analytics.sql').read_text(encoding='utf-8'))
            for value, expected in [('  -1.234,56  ', Decimal('-1234.56')), ('', None), ('0', Decimal('0')), ('+12,3', Decimal('12.30')), ('999999999999999999,99', Decimal('999999999999999999.99'))]:
                self.assertEqual(con.execute('SELECT br_decimal(?)', [value]).fetchone()[0], expected)
            for value in ('inválido', '1,234', '1.23,45', '1000000000000000000,00'):
                with self.assertRaises(duckdb.Error):
                    con.execute('SELECT br_decimal(?)', [value]).fetchone()


if __name__ == '__main__':
    unittest.main()
