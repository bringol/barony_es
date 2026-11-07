import json
import tempfile
import unittest
from pathlib import Path

from barony_es import (Rules, VersionStore, align, book_title, format_po, parse_po, translate_file, units)

SCRIPT = 'data/scripts/t1/script.json'
RULES = Rules({
    'lang': ['lang/en.txt'],
    'books': ['books/*.txt'],
    'json': {'data/story/*.json': ['/text/*']},
    'lines': {'data/scripts/*/script.json': ['/script_entries/*/sign']},
    'layout': {'data/scripts/*/script.json': ['/script_entries/*/attributes/word_highlights']},
})


class CatalogTest(unittest.TestCase):
    def test_round_trip_keeps_one_entry_per_source_of_a_context(self):
        entries = [
            {'context': 'lang/en.txt:10', 'source': 'Old "text"\nline', 'target': 'Viejo', 'fuzzy': False,
             'previous': '', 'notes': 'Versiones: 3.3.7'},
            {'context': 'lang/en.txt:10', 'source': 'New text', 'target': 'Viejo', 'fuzzy': True,
             'previous': 'Old text', 'notes': ''},
        ]
        self.assertEqual(parse_po(format_po('es', entries)), ('es', entries))


class FormatsTest(unittest.TestCase):
    def test_lang_keeps_comments_and_untranslated_entries(self):
        text = '# comment\n1 null#\n10 first\nline#\n# section\n11 DEPRECATED#\n12 second#\n'
        self.assertEqual([c for c, _ in units('lang/en.txt', text, RULES)], ['lang/en.txt:10', 'lang/en.txt:12'])
        translated = translate_file('lang/en.txt', text, RULES, lambda c, s: {'lang/en.txt:10': 'primera\nlínea'}.get(c))
        self.assertEqual(translated, '# comment\n1 null#\n10 primera\nlínea#\n# section\n11 DEPRECATED#\n12 second#\n')
        with self.assertRaises(ValueError):
            translate_file('lang/en.txt', text, RULES, lambda c, s: 'con # almohadilla')

    def test_signs_are_one_text_whose_lines_can_grow(self):
        english = json.dumps({'script_entries': {'a': {
            'sign': ['Use$ keys', '$', ''], 'attributes': {'word_highlights': [[0, 1]]}}}})
        self.assertEqual(units(SCRIPT, english, RULES), [
            (f'{SCRIPT}:/script_entries/a/sign', 'Use$ keys\n$\n'),
            (f'{SCRIPT}:/script_entries/a/attributes/word_highlights', '[[0,1]]'),
        ])
        spanish = json.dumps({'script_entries': {'a': {
            'sign': ['Usa las', 'teclas$', '$', ''], 'attributes': {'word_highlights': [[1, 0]]}}}})
        self.assertEqual(set(align(SCRIPT, english, spanish, RULES).values()), {'Usa las\nteclas$\n$\n', '[[1,0]]'})
        built = json.loads(translate_file(SCRIPT, english, RULES, lambda c, s: {
            'Use$ keys\n$\n': 'Usa las\nteclas$\n$\n', '[[0,1]]': '[[1,0]]'}.get(s)))
        self.assertEqual(built['script_entries']['a'], {
            'sign': ['Usa las', 'teclas$', '$', ''], 'attributes': {'word_highlights': [[1, 0]]}})

    def test_arrays_of_another_length_are_not_paired(self):
        english = json.dumps({'text': ['One', 'Two']})
        spanish = json.dumps({'text': ['Uno', 'Extra', 'Dos']})
        self.assertEqual(align('data/story/intro.json', english, spanish, RULES), {})

    def test_book_titles_come_from_file_names(self):
        self.assertEqual(book_title('books/On Giantism, Vol 1.txt'),
                         ('lang/book_names.json:/book_names/On Giantism, Vol 1', 'On Giantism, Vol 1'))


class VersionStoreTest(unittest.TestCase):
    def test_older_versions_keep_only_what_differs(self):
        contents = {
            '5.0.2': {'a.txt': b'new', 'b.txt': b'same', 'c.txt': b'only new'},
            '4.3.2': {'a.txt': b'old', 'b.txt': b'same'},
        }
        with tempfile.TemporaryDirectory() as root:
            store = VersionStore(root)
            store.write(contents)
            self.assertEqual(sorted(p.relative_to(root).as_posix() for p in Path(root).rglob('*') if p.is_file()),
                             ['4.3.2/.removed', '4.3.2/a.txt', '5.0.2/a.txt', '5.0.2/b.txt', '5.0.2/c.txt'])
            self.assertEqual(store.versions, ['5.0.2', '4.3.2'])
            self.assertEqual({v: store.read(v) for v in store.versions}, contents)


if __name__ == '__main__':
    unittest.main()
