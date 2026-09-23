"""Prepara uma página PBIR em área de revisão, sem modificar o projeto original.

Usa esquemas extraídos da instalação local do Power BI; nenhum acesso à rede.
Execute validate_pbir.ps1 antes de copiar a página candidata para o relatório.
"""
import ast
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
from urllib.parse import urljoin, urldefrag

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / 'powerbi/Brasil_em_Dados.Report'
PAGE_ID = 'b6d202601000000000001'
SCHEMAS = ROOT / 'data/processed/pbir_local_schemas'
STAGE = ROOT / 'data/processed/pbir_overview_candidate'
BASE = 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/'
MONEY_FORMAT = '"R$" #,0,,,.00" bi";-"R$" #,0,,,.00" bi";"R$" #,0,,,.00" bi"'
NAVY, GREEN, TEXT, MUTED = '#13324F', '#087F6D', '#223B53', '#586C80'


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def local_schemas(pbi_install=None):
    installations = [pbi_install] if pbi_install else sorted(Path('C:/Program Files/WindowsApps').glob('Microsoft.MicrosoftPowerBIDesktop_*_x64__*'))
    if not installations:
        raise RuntimeError('Instalação local do Power BI não localizada.')
    scripts = installations[-1] / 'bin/WebView2Resources/minerva/scripts'
    SCHEMAS.mkdir(parents=True, exist_ok=True)
    sources = list(scripts.glob('desktop.schema.json.*.min.js')) + [scripts / 'desktop.reportThemeSchema.json.min.js']
    inventory = []
    schema_map = {}
    for source in sources:
        for match in re.finditer(r"JSON\.parse\(('(?:\\.|[^'\\])*')\)", source.read_text(encoding='utf-8')):
            schema = json.loads(ast.literal_eval(match.group(1)))
            if '$id' not in schema and 'ThemeSchema' not in source.name:
                continue
            filename = 'theme.json' if 'ThemeSchema' in source.name else source.stem + '.json'
            (SCHEMAS / filename).write_text(json.dumps(schema, ensure_ascii=True), encoding='utf-8')
            if '$id' in schema:
                schema_map[schema['$id']] = schema
            inventory.append({'arquivo': filename, 'origem_local': str(source),
                              'sha256': hashlib.sha256(source.read_bytes()).hexdigest()})
    write(SCHEMAS / 'origens.json', inventory)
    # Agrupa referências em namespaces separados. Evita colisões de nomes
    # (ex.: SortDirection) no validador .NET instalado, sem mudar os esquemas.
    bundled = SCHEMAS / 'bundled'
    bundled.mkdir(exist_ok=True)
    for target in ('page/2.1.0', 'visualContainer/2.12.0', 'pagesMetadata/1.1.0'):
        root_uri = BASE + target + '/schema.json'
        definitions, keys = {}, {}

        def include(uri):
            if uri in keys:
                return keys[uri]
            key = 'document_' + str(len(keys))
            keys[uri] = key

            def rewrite(value):
                if isinstance(value, list):
                    return [rewrite(item) for item in value]
                if not isinstance(value, dict):
                    return value
                result = {}
                for prop, content in value.items():
                    if prop in ('$id', '$schema') and isinstance(content, str):
                        continue
                    if prop == '$ref' and isinstance(content, str):
                        doc, fragment = urldefrag(urljoin(uri, content))
                        ref_key = include(doc)
                        result[prop] = '#/definitions/' + ref_key + fragment
                    else:
                        result[prop] = rewrite(content)
                return result

            definitions[key] = rewrite(schema_map[uri])
            return key

        root_key = include(root_uri)
        bundle = {'$schema': 'http://json-schema.org/draft-07/schema#', '$id': root_uri,
                  'allOf': [{'$ref': '#/definitions/' + root_key}], 'definitions': definitions}
        (bundled / (target.replace('/', '_') + '.json')).write_text(json.dumps(bundle, ensure_ascii=True), encoding='utf-8')
    return json.loads((SCHEMAS / 'theme.json').read_text(encoding='utf-8'))


def literal(value):
    if isinstance(value, bool):
        encoded = str(value).lower()
    elif isinstance(value, (int, float)):
        encoded = str(value) + 'D'
    else:
        encoded = "'" + value.replace("'", "''") + "'"
    return {'expr': {'Literal': {'Value': encoded}}}


def color(value):
    return {'solid': {'color': literal(value)}}


def objects(groups):
    return {group: [{'properties': props}] for group, props in groups.items()}


def field(name, measure=False):
    return {'Measure' if measure else 'Column': {
        'Expression': {'SourceRef': {'Entity': 'despesas_bi'}}, 'Property': name}}


def projection(name, measure=False):
    result = {'field': field(name, measure), 'queryRef': f'despesas_bi.{name}', 'nativeQueryRef': name}
    if measure:
        result['format'] = MONEY_FORMAT
    return result


def container(title=None):
    result = {
        'background': {'show': literal(True), 'color': color('#FFFFFF'), 'transparency': literal(0)},
        'border': {'show': literal(True), 'color': color('#DFE7EE'), 'radius': literal(10)},
        'visualHeader': {'show': literal(False)},
        'padding': {key: literal(16) for key in ('left', 'right', 'top', 'bottom')},
    }
    if title:
        result['title'] = {'show': literal(True), 'text': literal(title), 'fontColor': color(NAVY),
                           'fontSize': literal(13), 'fontFamily': literal('Segoe UI'), 'bold': literal(True)}
    return objects(result)


def visual(number, kind, x, y, width, height, title=None):
    return {'$schema': BASE + 'visualContainer/2.12.0/schema.json',
            'name': f'b6d202601{number:011d}',
            'position': {'x': x, 'y': y, 'width': width, 'height': height, 'z': number, 'tabOrder': number},
            'visual': {'visualType': kind, 'visualContainerObjects': container(title), 'drillFilterOtherVisuals': True}}


def textbox(number, x, y, width, height, lines, dark=False):
    result = visual(number, 'textbox', x, y, width, height)
    result['visual']['objects'] = objects({'general': {'paragraphs': [
        {'textRuns': [{'value': text, 'textStyle': {'fontFamily': 'Segoe UI', 'fontSize': f'{size}pt',
          'fontWeight': 'bold' if bold else 'normal', 'color': shade}}]}
        for text, size, bold, shade in lines]}})
    result['visual']['visualContainerObjects'] = objects({
        'background': {'show': literal(True), 'color': color(NAVY if dark else '#F3F6FA'), 'transparency': literal(0)},
        'border': {'show': literal(False)}, 'visualHeader': {'show': literal(False)},
        'title': {'show': literal(False)},
        'padding': {key: literal(12 if dark else 0) for key in ('left', 'right', 'top', 'bottom')},
    })
    return result


def build(pbi_install=None):
    theme = local_schemas(pbi_install)
    tmdl = (ROOT / 'powerbi/Brasil_em_Dados.SemanticModel/definition/tables/despesas_bi.tmdl').read_text(encoding='utf-8')
    pages_file = REPORT / 'definition/pages/pages.json'
    pages = json.loads(pages_file.read_text(encoding='utf-8'))
    if PAGE_ID in pages['pageOrder'] or (REPORT / 'definition/pages' / PAGE_ID).exists():
        raise RuntimeError('Página já existe; não sobrescrever sem revisão e novo backup.')
    backup = ROOT / 'data/processed' / ('report_backup_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
    backup.mkdir()
    shutil.copytree(REPORT, backup / REPORT.name)
    protected = [ROOT / 'powerbi/Brasil_em_Dados.SemanticModel', ROOT / 'sql', ROOT / 'data/raw']
    files = [p for folder in protected for p in folder.rglob('*') if p.is_file()]
    files += list((ROOT / 'data/processed').glob('*.csv'))
    files += [ROOT / 'powerbi/Brasil_em_Dados.pbip', ROOT / '.gitignore']
    write(backup / 'protected_hashes.json', {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
    visuals = [textbox(1, 32, 24, 1536, 102, [
        ('Brasil em Dados | Gastos Públicos', 27, True, '#FFFFFF'),
        ('Execução da despesa federal — Janeiro de 2026', 14, False, '#C8DFE9')], dark=True)]
    slicers = []
    for i, (name, title) in enumerate([
        ('nome_orgao_superior', 'Órgão superior'), ('codigo_programa', 'Programa (código)'), ('nome_grupo_despesa', 'Grupo de despesa')]):
        v = visual(i + 2, 'slicer', 32 + i * 520, 146, 496, 96, title)
        v['visual']['query'] = {'queryState': {'Values': {'projections': [projection(name)]}}}
        v['visual']['objects'] = objects({
            'data': {'mode': literal('Dropdown')},
            'selection': {'singleSelect': literal(False), 'selectAllCheckboxEnabled': literal(True)},
            'header': {'show': literal(False)},
            'items': {'fontColor': color(TEXT), 'textSize': literal(11)},
        })
        visuals.append(v); slicers.append(v['name'])
    for i, name in enumerate(['Total Pago', 'Total Empenhado', 'Total Liquidado', 'Restos a Pagar Pagos']):
        v = visual(i + 5, 'card', 32 + i * 390, 266, 366, 140, name)
        v['visual']['query'] = {'queryState': {'Values': {'projections': [projection(name, True)]}}}
        v['visual']['objects'] = objects({
            'general': {'formatString': literal(MONEY_FORMAT)},
            'labels': {'color': color(GREEN if i in (0, 3) else NAVY), 'fontSize': literal(29),
                       'labelDisplayUnits': literal(1), 'labelPrecision': literal(2), 'fontFamily': literal('Segoe UI')},
            'categoryLabels': {'show': literal(False)},
        })
        visuals.append(v)
    for i, (name, title) in enumerate([
        ('nome_orgao_superior', 'Valor pago por órgão superior'), ('codigo_programa', 'Valor pago por programa')]):
        v = visual(i + 9, 'clusteredBarChart', 32 + i * 780, 430, 756, 488, title)
        v['visual']['query'] = {'queryState': {
            'Category': {'projections': [projection(name)]},
            'Y': {'projections': [projection('Total Pago', True)]}},
            'sortDefinition': {'sort': [{'field': field('Total Pago', True), 'direction': 'Descending'}], 'isDefaultSort': True}}
        if i == 1:
            # MIN de texto retorna o nome único do código, sem criar medida DAX.
            v['visual']['query']['queryState']['Tooltips'] = {'projections': [{
                'field': {'Aggregation': {'Expression': field('nome_programa'), 'Function': 3}},
                'queryRef': 'Min(despesas_bi.nome_programa)', 'nativeQueryRef': 'Nome do programa',
                'displayName': 'Nome do programa'}]}
            v['visual']['visualContainerObjects']['subTitle'] = [{'properties': {
                'show': literal(True), 'text': literal('Código no eixo • nome ao passar o cursor'),
                'fontColor': color(MUTED), 'fontSize': literal(10)}}]
        v['visual']['objects'] = objects({
            'legend': {'show': literal(False)},
            'dataPoint': {'defaultColor': color(NAVY if i == 0 else GREEN)},
            'categoryAxis': {'show': literal(True), 'showAxisTitle': literal(False), 'fontSize': literal(10),
                             'labelColor': color(TEXT), 'maxMarginFactor': literal(48), 'preferredCategoryWidth': literal(32)},
            'valueAxis': {'show': literal(True), 'showAxisTitle': literal(False), 'fontSize': literal(10),
                          'labelDisplayUnits': literal(1), 'labelPrecision': literal(2), 'gridlineShow': literal(True)},
            'labels': {'show': literal(True), 'color': color(TEXT), 'fontSize': literal(10),
                       'labelDisplayUnits': literal(1), 'labelPrecision': literal(2)},
        })
        visuals.append(v)
    visuals.append(textbox(11, 32, 942, 1536, 38, [
        ('Valores em R$ bilhões (bi). Role os gráficos para ver todas as categorias. Restos pagos são apresentados separadamente.', 11, False, MUTED)]))
    page = {'$schema': BASE + 'page/2.1.0/schema.json', 'name': PAGE_ID, 'displayName': 'Visão Geral',
            'displayOption': 'FitToPage', 'height': 1000, 'width': 1600,
            'objects': objects({'background': {'color': color('#F3F6FA'), 'transparency': literal(0)}}),
            'visualInteractions': [{'source': source, 'target': v['name'], 'type': 'DataFilter'}
                                   for source in slicers for v in visuals if v['visual']['visualType'] != 'textbox' and v['name'] != source]}
    # Confronta cada propriedade específica com o catálogo oficial local de visuais.
    for v in visuals:
        kind = v['visual']['visualType']
        definition = theme['definitions']['visual-' + kind]
        allowed = {}
        for part in definition.get('allOf', [definition]):
            allowed.update(part.get('properties', {}))
        for group, instances in v['visual'].get('objects', {}).items():
            assert group in allowed, (kind, group)
            allowed_props = allowed[group]['items']['properties']
            for instance in instances:
                assert set(instance['properties']) <= set(allowed_props), (kind, group)
        for role in v['visual'].get('query', {}).get('queryState', {}).values():
            for proj in role['projections']:
                typ, data = next(iter(proj['field'].items()))
                if typ == 'Aggregation':
                    typ, data = next(iter(data['Expression'].items()))
                ref = data['Property']
                assert (f"\tmeasure '{ref}' =" if typ == 'Measure' else f'\tcolumn {ref}\n') in tmdl, ref
        pos = v['position']
        assert 0 <= pos['x'] and pos['x'] + pos['width'] <= page['width']
        assert 0 <= pos['y'] and pos['y'] + pos['height'] <= page['height']
    assert len({v['name'] for v in visuals}) == len(visuals) == 11
    for i, a in enumerate(visuals):
        a = a['position']
        for b in visuals[i+1:]:
            b = b['position']
            assert a['x']+a['width'] <= b['x'] or b['x']+b['width'] <= a['x'] or a['y']+a['height'] <= b['y'] or b['y']+b['height'] <= a['y']
    write(STAGE / PAGE_ID / 'page.json', page)
    for v in visuals:
        write(STAGE / PAGE_ID / 'visuals' / v['name'] / 'visual.json', v)
    pages['pageOrder'].append(PAGE_ID)
    pages['activePageName'] = PAGE_ID
    write(STAGE / 'pages.json', pages)
    write(STAGE / 'build_manifest.json', {'backup': str(backup), 'page': PAGE_ID, 'visuals': len(visuals),
                                        'format': MONEY_FORMAT, 'status': 'candidato; requer validação de esquema antes de instalar'})
    print(json.dumps({'backup': str(backup), 'candidate': str(STAGE), 'visuals': len(visuals)}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pbi-install', type=Path)
    build(parser.parse_args().pbi_install)
