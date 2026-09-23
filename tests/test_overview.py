"""Contratos da página PBIR: vínculos, granularidade e interações dos filtros."""
import json
from pathlib import Path
import re
import unittest

from src.build_overview import PAGE_ID, REPORT, ROOT
from src.refine_overview import EXACT


class OverviewTests(unittest.TestCase):
    def setUp(self):
        self.folder = REPORT / 'definition/pages' / PAGE_ID
        self.page = json.loads((self.folder / 'page.json').read_text(encoding='utf-8'))
        self.visuals = [json.loads(p.read_text(encoding='utf-8')) for p in self.folder.glob('visuals/*/visual.json')]

    def test_registered_page_and_visual_counts(self):
        pages = json.loads((REPORT / 'definition/pages/pages.json').read_text(encoding='utf-8'))
        self.assertEqual(pages['pageOrder'].count(PAGE_ID), 1)
        self.assertIn('38ecfd56a6347e3147a0', pages['pageOrder'])
        self.assertEqual(self.page['displayName'], 'Visão Geral')
        types = [v['visual']['visualType'] for v in self.visuals]
        self.assertEqual(types.count('card'), 4)
        self.assertEqual(types.count('clusteredBarChart'), 2)
        self.assertEqual(types.count('slicer'), 3)
        self.assertEqual(len({v['name'] for v in self.visuals}), len(self.visuals))

    def test_fields_exist_and_measures_are_not_replaced(self):
        tmdl = (ROOT / 'powerbi/Brasil_em_Dados.SemanticModel/definition/tables/despesas_bi.tmdl').read_text(encoding='utf-8')
        measures = set(re.findall(r"^\tmeasure '([^']+)'", tmdl, re.M))
        columns = set(re.findall(r'^\tcolumn (\w+)', tmdl, re.M))

        def walk(value):
            if isinstance(value, list):
                for item in value:
                    walk(item)
            elif isinstance(value, dict):
                for key, item in value.items():
                    if key in ('Measure', 'Column'):
                        self.assertEqual(item['Expression']['SourceRef']['Entity'], 'despesas_bi')
                        self.assertIn(item['Property'], measures if key == 'Measure' else columns)
                    walk(item)
        for visual in self.visuals:
            walk(visual)
        self.assertIn("measure 'Total Pago' = SUM('despesas_bi'[valor_pago])", tmdl)
        self.assertNotIn(' bi', tmdl)

    def test_programs_keep_code_identity(self):
        charts = [v for v in self.visuals if v['visual']['visualType'] == 'clusteredBarChart']
        categories = [v['visual']['query']['queryState']['Category']['projections'][0]['field']['Column']['Property'] for v in charts]
        self.assertIn('codigo_programa', categories)
        self.assertNotIn('nome_programa', categories)
        for chart in charts:
            measure = chart['visual']['query']['queryState']['Y']['projections'][0]
            self.assertEqual(measure['field']['Measure']['Property'], 'Total Pago')
            self.assertEqual(measure['format'], EXACT)
            # O Desktop salva cartões de filtro vazios mesmo sem restrição.
            for configured in chart.get('filterConfig', {}).get('filters', []):
                self.assertFalse(configured.get('filter'))
                self.assertNotEqual(configured.get('type'), 'TopN')

    def test_slicers_filter_all_analytical_visuals(self):
        interactions = {(i['source'], i['target']): i['type'] for i in self.page['visualInteractions']}
        analytical = [v for v in self.visuals if v['visual']['visualType'] != 'textbox']
        for source in analytical:
            if source['visual']['visualType'] != 'slicer':
                continue
            for target in analytical:
                if source['name'] != target['name']:
                    self.assertEqual(interactions[(source['name'], target['name'])], 'DataFilter')


if __name__ == '__main__':
    unittest.main()
