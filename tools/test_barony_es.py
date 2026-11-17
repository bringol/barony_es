import json
import unittest

from barony_es import HEADER, Entry, Rules, align, book_title, format_po, parse_po, translate_file, units

SCRIPT = 'data/scripts/t1/script.json'
RULES = Rules(
    lang=['lang/en.txt'],
    books=['books/*.txt'],
    json={'data/story/*.json': ['/text/*']},
    lines={'data/scripts/*/script.json': ['/script_entries/*/sign']},
    layout={'data/scripts/*/script.json': ['/script_entries/*/attributes/word_highlights']},
)


class CatalogTest(unittest.TestCase):
    def test_round_trip_keeps_one_entry_per_source_of_a_context(self):
        header = HEADER + 'Language: es\n'
        entries = [
            Entry('lang/en.txt:10', 'Old "text"\nline', 'Viejo', notes=('Versiones: 3.3.7',), comments=('revisar',)),
            Entry('lang/en.txt:10', 'New %s text', 'Viejo', fuzzy=True, previous='Old text'),
        ]
        text = format_po(header, entries)
        self.assertIn('#, fuzzy, c-format\n#| msgid "Old text"\n', text)
        self.assertEqual(parse_po(text), (header, entries))

    def test_wrapped_strings_and_foreign_comments_are_read(self):
        text = '#: lang/en.txt\n#, c-format, fuzzy\nmsgctxt "a"\nmsgid ""\n"One "\n"two\\n"\nmsgstr "Uno"\n\n#~ msgid "gone"\n#~ msgstr "ido"\n'
        self.assertEqual(parse_po(text), (HEADER, [Entry('a', 'One two\n', 'Uno', fuzzy=True)]))


class FormatsTest(unittest.TestCase):
    def test_lang_keeps_comments_and_untranslated_entries(self):
        text = '# comment\n1 null#\n10 first\nline#\n# section\n11 DEPRECATED#\n12 second#\n'
        self.assertEqual([context for context, _ in units('lang/en.txt', text, RULES)], ['lang/en.txt:10', 'lang/en.txt:12'])
        translated = translate_file('lang/en.txt', text, RULES, lambda context, _: {'lang/en.txt:10': 'primera\nlínea'}.get(context))
        self.assertEqual(translated, '# comment\n1 null#\n10 primera\nlínea#\n# section\n11 DEPRECATED#\n12 second#\n')

    def test_lang_rejects_what_the_game_cannot_read(self):
        for target in ('con # almohadilla', 'ñ' * 511):
            with self.assertRaises(ValueError):
                translate_file('lang/en.txt', '10 first#\n', RULES, lambda *_: target)

    def test_signs_are_one_text_whose_lines_can_grow(self):
        english = json.dumps({'script_entries': {'a': {
            'sign': ['Use$ keys', '$', ''], 'attributes': {'word_highlights': [[0, 1]]}}}})
        self.assertEqual(units(SCRIPT, english, RULES), [
            (f'{SCRIPT}:/script_entries/a/sign', 'Use$ keys\n$\n'),
            (f'{SCRIPT}:/script_entries/a/attributes/word_highlights', '[[0,1]]'),
        ])
        spanish = {'sign': ['Usa las', 'teclas$', '$', ''], 'attributes': {'word_highlights': [[1, 0]]}}
        targets = {'Use$ keys\n$\n': 'Usa las\nteclas$\n$\n', '[[0,1]]': '[[1,0]]'}
        self.assertEqual(set(align(SCRIPT, english, json.dumps({'script_entries': {'a': spanish}}), RULES).values()), set(targets.values()))
        built = json.loads(translate_file(SCRIPT, english, RULES, lambda _, source: targets.get(source)))
        self.assertEqual(built['script_entries']['a'], spanish)

    def test_arrays_of_another_length_are_not_paired(self):
        english = json.dumps({'text': ['One', 'Two']})
        spanish = json.dumps({'text': ['Uno', 'Extra', 'Dos']})
        self.assertEqual(align('data/story/intro.json', english, spanish, RULES), {})

    def test_book_titles_come_from_file_names(self):
        self.assertEqual(book_title('books/On Giantism, Vol 1.txt'),
                         ('lang/book_names.json:/book_names/On Giantism, Vol 1', 'On Giantism, Vol 1'))


if __name__ == '__main__':
    unittest.main()
