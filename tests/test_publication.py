from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src import prepare_publication as publication


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def put(self, relative, text='exemplo'):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        return path

    def test_excludes_local_and_sensitive_artifacts(self):
        self.put('powerbi/model/.pbi/cache.abf')
        self.put('powerbi/model/.pbi/localSettings.json', '{}')
        shared = self.put('powerbi/model/.pbi/editorSettings.json', '{}')
        self.put('powerbi/secrets.json', '{}')
        self.put('powerbi/credentials/key.json', '{}')
        self.put('powerbi/backups/a.json', '{}')
        self.put('data/raw/a.csv')
        self.assertEqual(publication.candidates(self.root), [shared])

    def test_detects_personal_paths_and_token_patterns(self):
        self.put('src/example.py', 'token = ' + 'ghp_' + 'x'*30)
        self.put('powerbi/model.tmdl', 'source = ' + 'C:' + '\\Users\\' + 'Pessoa\\dados.csv')
        result = publication.audit(self.root)
        self.assertEqual({x['tipo'] for x in result['achados']}, {'possivel_segredo','caminho_pessoal'})
        self.assertNotIn('x'*30, str(result))

    def test_prepares_anonymous_copy_without_changing_original(self):
        rel = 'powerbi/Brasil_em_Dados.SemanticModel/definition/tables/despesas_bi.tmdl'
        source = self.put(rel, 'table despesas_bi\n source = File.Contents("' + 'C:' + '\\Users\\' + 'Pessoa\\despesas_bi.csv")\n')
        before = source.read_bytes()
        self.put('README.md', '# Exemplo')
        self.put('.gitignore', 'data/**\n')
        destination = self.root/'data/processed/publicacao_teste'
        with patch.object(publication, 'ROOT', self.root):
            result = publication.prepare(destination)
            self.assertEqual(result['achados'], [])
            with self.assertRaises(ValueError):
                publication.prepare(destination)
        self.assertEqual(source.read_bytes(), before)
        self.assertIn('CONFIGURAR_CAMINHO', (destination/rel).read_text())
        self.assertFalse((destination/'.git').exists())


if __name__ == '__main__':
    unittest.main()
