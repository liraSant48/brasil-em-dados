"""Refina uma cópia PBIR para revisão; não altera DAX nem fontes de dados."""
import copy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil

if __package__:
    from .build_overview import PAGE_ID, REPORT, ROOT, SCHEMAS, color, literal, objects, field, write
else:
    from build_overview import PAGE_ID, REPORT, ROOT, SCHEMAS, color, literal, objects, field, write

STAGE = ROOT / 'data/processed/pbir_dark_candidate'
EXACT = '"R$" #,0.00;-"R$" #,0.00;"R$" #,0.00'
PALETTE = {'page': '#0F1115', 'card': '#171A21', 'border': '#2A2F3A',
           'header': '#12324A', 'text': '#F3F4F6', 'secondary': '#AAB2BF',
           'money': '#32D583', 'alternative': '#22C55E'}
DETAIL_ID = 'b6d20260100000000012'


def props(obj, group):
    return obj.setdefault(group, [{'properties': {}}])[0]['properties']


def exact_projection(name, measure=False, label=None):
    p = {'field': field(name, measure), 'queryRef': 'despesas_bi.' + name,
         'nativeQueryRef': name, 'displayName': label or name}
    if measure:
        p['format'] = EXACT
    return p


def refine(page, visuals):
    page, visuals = copy.deepcopy(page), copy.deepcopy(visuals)
    page['height'] = 1440
    page['displayOption'] = 'FitToWidth'
    props(page.setdefault('objects', {}), 'background').update(color=color(PALETTE['page']), transparency=literal(0))
    # Idempotente em uma cópia: a tabela é reconstruída, sem duplicá-la.
    visuals = [v for v in visuals if v['name'] != DETAIL_ID]
    for v in visuals:
        visual = v['visual']; kind = visual['visualType']
        containers = visual.setdefault('visualContainerObjects', {})
        props(containers, 'background').update(show=literal(True), color=color(PALETTE['card']), transparency=literal(0))
        props(containers, 'border').update(show=literal(True), color=color(PALETTE['border']), radius=literal(10))
        if 'title' in containers:
            props(containers, 'title')['fontColor'] = color(PALETTE['text'])
        if 'subTitle' in containers:
            props(containers, 'subTitle')['fontColor'] = color(PALETTE['secondary'])
        for role in visual.get('query', {}).get('queryState', {}).values():
            for projection in role['projections']:
                if 'Measure' in projection['field']:
                    projection['format'] = EXACT
        obj = visual.setdefault('objects', {})
        if kind == 'textbox':
            is_header = v['name'].endswith('00001')
            props(containers, 'background')['color'] = color(PALETTE['header'] if is_header else PALETTE['page'])
            props(containers, 'border')['show'] = literal(False)
            paragraphs = props(obj, 'general')['paragraphs']
            for i, paragraph in enumerate(paragraphs):
                for run in paragraph['textRuns']:
                    run.setdefault('textStyle', {})['color'] = PALETTE['text'] if is_header and i == 0 else PALETTE['secondary']
            if not is_header:
                v['position'].update(y=1382, height=34)
                paragraphs[0]['textRuns'][0]['value'] = 'Janeiro de 2026 • Cartões e eixos com unidades automáticas. Rótulos e detalhe em R$ exatos. Restos pagos separados.'
        elif kind == 'card':
            props(obj, 'general')['formatString'] = literal(EXACT)
            props(obj, 'labels').update(color=color(PALETTE['money']), labelDisplayUnits=literal(0), labelPrecision=literal(2))
        elif kind == 'clusteredBarChart':
            program = visual['query']['queryState']['Category']['projections'][0]['field']['Column']['Property'] == 'codigo_programa'
            props(obj, 'dataPoint')['defaultColor'] = color('#14B8A6' if program else '#2F6FED')
            props(obj, 'categoryAxis')['labelColor'] = color(PALETTE['text'])
            props(obj, 'valueAxis').update(labelColor=color(PALETTE['secondary']), gridlineColor=color(PALETTE['border']),
                                           labelDisplayUnits=literal(0), labelPrecision=literal(2))
            props(obj, 'labels').update(color=color(PALETTE['text']), labelDisplayUnits=literal(1), labelPrecision=literal(2),
                                        fontSize=literal(9), labelPosition=literal('OutsideEnd'), labelOverflow=literal(True),
                                        enableBackground=literal(True), backgroundColor=color(PALETTE['card']), backgroundTransparency=literal(0))
            # A medida no tooltip também tem formato exato, não escala em bilhões.
            tips = visual['query']['queryState'].setdefault('Tooltips', {'projections': []})['projections']
            if not any(p['field'].get('Measure', {}).get('Property') == 'Total Pago' for p in tips):
                tips.append(exact_projection('Total Pago', True, 'Valor pago exato'))
        elif kind == 'slicer':
            # Remove apenas a seleção salva do menu, para abrir no total geral.
            for entry in obj.get('general', []):
                entry.get('properties', {}).pop('filter', None)
            props(obj, 'items').update(fontColor=color(PALETTE['text']), background=color(PALETTE['card']), textSize=literal(11))
            props(obj, 'header').update(fontColor=color(PALETTE['text']), background=color(PALETTE['card']))
            props(obj, 'dropdown').update(borderColor=color(PALETTE['border']), iconColor=color(PALETTE['text']), accentBarColor=color(PALETTE['alternative']))

    template = next(v for v in visuals if v['visual']['visualType'] == 'card')
    detail = copy.deepcopy(template)
    detail['name'] = DETAIL_ID
    detail['position'] = {'x': 32, 'y': 942, 'width': 1536, 'height': 416, 'z': 12, 'tabOrder': 12}
    detail['visual']['visualType'] = 'tableEx'
    props(detail['visual']['visualContainerObjects'], 'title')['text'] = literal('Detalhamento dos registros | valores exatos em R$')
    fields = [('id_registro','Registro'), ('codigo_programa','Código do programa'), ('nome_programa','Programa'),
              ('codigo_acao','Código da ação'), ('nome_orgao_superior','Órgão superior'), ('nome_grupo_despesa','Grupo de despesa')]
    detail['visual']['query'] = {'queryState': {'Values': {'projections':
        [exact_projection(name, label=label) for name, label in fields] +
        [exact_projection(name, True) for name in ['Total Pago','Total Empenhado','Total Liquidado','Restos a Pagar Pagos']]}}}
    detail['visual']['objects'] = objects({
        'grid': {'gridHorizontal': literal(True), 'gridHorizontalColor': color(PALETTE['border']), 'rowPadding': literal(6)},
        'columnHeaders': {'fontColor': color(PALETTE['text']), 'backColor': color(PALETTE['header']), 'fontSize': literal(10), 'wordWrap': literal(False)},
        'values': {'fontColorPrimary': color(PALETTE['text']), 'fontColorSecondary': color(PALETTE['text']),
                   'backColorPrimary': color(PALETTE['card']), 'backColorSecondary': color(PALETTE['page']), 'fontSize': literal(10)},
        'total': {'totals': literal(True), 'label': literal('Total no contexto'), 'fontColor': color(PALETTE['money']), 'backColor': color(PALETTE['header'])},
        'columnFormatting': {'labelDisplayUnits': literal(1), 'labelPrecision': literal(2)},
    })
    visuals.append(detail)
    analytical = [v for v in visuals if v['visual']['visualType'] != 'textbox']
    interactions = []
    for source in analytical:
        kind = source['visual']['visualType']
        if kind not in ('slicer','clusteredBarChart','tableEx'):
            continue
        for target in analytical:
            if source['name'] == target['name']:
                continue
            # Barras filtram dados; não reescrevem os menus de seleção.
            mode = 'NoFilter' if kind == 'tableEx' or (kind == 'clusteredBarChart' and target['visual']['visualType'] == 'slicer') else 'DataFilter'
            interactions.append({'source': source['name'], 'target': target['name'], 'type': mode})
    page['visualInteractions'] = interactions
    return page, visuals


def main():
    folder = REPORT / 'definition/pages' / PAGE_ID
    page = json.loads((folder / 'page.json').read_text(encoding='utf-8'))
    visuals = [json.loads(p.read_text(encoding='utf-8')) for p in sorted(folder.glob('visuals/*/visual.json'))]
    backup = ROOT / 'data/processed/backups' / ('dark_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
    backup.mkdir(parents=True)
    shutil.copytree(REPORT, backup / REPORT.name)
    protected = [p for root in [ROOT/'sql', ROOT/'powerbi/Brasil_em_Dados.SemanticModel', ROOT/'data/raw'] for p in root.rglob('*') if p.is_file()]
    protected += list((ROOT/'data/processed').glob('*.csv')) + list((ROOT/'data').glob('*.duckdb'))
    write(backup/'protected_hashes.json', {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in protected})
    page, visuals = refine(page, visuals)
    # Propriedades específicas precisam existir no catálogo instalado.
    theme = json.loads((SCHEMAS/'theme.json').read_text(encoding='utf-8'))
    for v in visuals:
        allowed = {}
        for part in theme['definitions']['visual-' + v['visual']['visualType']]['allOf']:
            allowed.update(part.get('properties', {}))
        for group, entries in v['visual'].get('objects', {}).items():
            assert group in allowed, group
            for entry in entries:
                assert set(entry['properties']) <= set(allowed[group]['items']['properties']), group
        write(STAGE/PAGE_ID/'visuals'/v['name']/'visual.json', v)
    write(STAGE/PAGE_ID/'page.json', page)
    write(STAGE/'manifest.json', {'backup':str(backup), 'page':PAGE_ID, 'visuals':len(visuals)})
    print(json.dumps({'backup':str(backup), 'candidate':str(STAGE), 'visuals':len(visuals)},ensure_ascii=False))


if __name__ == '__main__':
    main()
