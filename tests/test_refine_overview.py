import json
import unittest

from src.build_overview import PAGE_ID, REPORT
from src.refine_overview import refine, EXACT, DETAIL_ID, PALETTE


class RefinementTests(unittest.TestCase):
    def setUp(self):
        path = REPORT / 'definition/pages' / PAGE_ID
        self.page = json.loads((path / 'page.json').read_text(encoding='utf-8'))
        self.visuals = [json.loads(p.read_text(encoding='utf-8')) for p in sorted(path.glob('visuals/*/visual.json'))]

    def test_idempotent_and_preserves_input(self):
        before = json.dumps([self.page, self.visuals])
        first = refine(self.page, self.visuals)
        self.assertEqual(first, refine(*first))
        self.assertEqual(json.dumps([self.page, self.visuals]), before)

    def test_money_no_forced_billions_and_detail_identity(self):
        for v in self.visuals:
            kind = v['visual']['visualType']
            if kind == 'card':
                p = v['visual']['objects']['labels'][0]['properties']
                self.assertEqual(p['labelDisplayUnits']['expr']['Literal']['Value'], '0D')
                self.assertEqual(p['color']['solid']['color']['expr']['Literal']['Value'], "'" + PALETTE['money'] + "'")
            if kind == 'clusteredBarChart':
                p = v['visual']['objects']['labels'][0]['properties']
                self.assertEqual(p['labelDisplayUnits']['expr']['Literal']['Value'], '1D')
                self.assertEqual(p['labelPosition']['expr']['Literal']['Value'], "'OutsideEnd'")
            for role in v['visual'].get('query', {}).get('queryState', {}).values():
                for projection in role['projections']:
                    if 'Measure' in projection['field']:
                        self.assertEqual(projection['format'], EXACT)
                        self.assertNotIn(',,,', projection['format'])
        detail = next(v for v in self.visuals if v['name'] == DETAIL_ID)
        columns = [p['field']['Column']['Property'] for p in detail['visual']['query']['queryState']['Values']['projections'] if 'Column' in p['field']]
        self.assertIn('id_registro', columns)
        self.assertIn('codigo_programa', columns)

    def test_bar_interactions_and_initial_filters(self):
        pairs = {(i['source'], i['target']):i['type'] for i in self.page['visualInteractions']}
        bars = [v for v in self.visuals if v['visual']['visualType']=='clusteredBarChart']
        for bar in bars:
            for target in self.visuals:
                kind = target['visual']['visualType']
                if kind in ('card','tableEx'):
                    self.assertEqual(pairs[(bar['name'],target['name'])], 'DataFilter')
                if kind == 'slicer':
                    self.assertEqual(pairs[(bar['name'],target['name'])], 'NoFilter')
        for v in self.visuals:
            if v['visual']['visualType']=='slicer':
                self.assertTrue(all('filter' not in e['properties'] for e in v['visual'].get('objects',{}).get('general',[])))

    def test_contrast_and_layout(self):
        def luminance(hex_color):
            channels = [int(hex_color[i:i+2],16)/255 for i in (1,3,5)]
            rgb = [v/12.92 if v<=0.04045 else ((v+0.055)/1.055)**2.4 for v in channels]
            return sum(a*b for a,b in zip(rgb,(0.2126,0.7152,0.0722)))
        for foreground in ('text','secondary','money'):
            for background in ('card','page'):
                a,b=sorted([luminance(PALETTE[foreground]),luminance(PALETTE[background])])
                self.assertGreaterEqual((b+0.05)/(a+0.05),4.5)
        for i,v in enumerate(self.visuals):
            a=v['position']
            self.assertLessEqual(a['x']+a['width'],self.page['width'])
            self.assertLessEqual(a['y']+a['height'],self.page['height'])
            for w in self.visuals[i+1:]:
                b=w['position']
                self.assertTrue(a['x']+a['width']<=b['x'] or b['x']+b['width']<=a['x'] or a['y']+a['height']<=b['y'] or b['y']+b['height']<=a['y'])


if __name__ == '__main__':
    unittest.main()
