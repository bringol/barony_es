"""Catálogos gettext de la traducción de Barony para varias versiones del juego.

    python tools/barony_es.py extract --game 5.0.2=RUTA --game 4.3.2=RUTA --game 3.3.7=RUTA
    python tools/barony_es.py import 5.0.2 CARPETA_TRADUCIDA [--overwrite]
    python tools/barony_es.py build 5.0.2 [--out build/5.0.2] [--fuzzy]
    python tools/barony_es.py stats
"""

import argparse
import json
import re
import shutil
import sys
from dataclasses import dataclass, field, replace
from fnmatch import fnmatchcase
from functools import cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE, ASSETS = ROOT / 'source', ROOT / 'assets'
COMPONENTS = ('lang', 'textos', 'libros')
BOOK_NAMES = 'lang/book_names.json'
HEADER = 'Project-Id-Version: Barony\nMIME-Version: 1.0\nContent-Type: text/plain; charset=UTF-8\nContent-Transfer-Encoding: 8bit\n'
ESCAPES = {'\\': r'\\', '"': r'\"', '\n': r'\n', '\t': r'\t', '\r': r'\r'}
UNESCAPES = {escaped: char for char, escaped in ESCAPES.items()}
PRINTF = re.compile(r'%[-+0#]*\d*(?:\.\d+)?(?:ll|l|h)?[sdiuxXcf]')
NOTES = {
    'lines': 'Cada línea es un renglón en el juego; puedes agregar o quitar líneas para que no se desborde.',
    'layout': 'Maquetación en JSON: ajústala si la traducción cambia la posición de palabras o líneas.',
}


# --- Catálogos PO ---

@dataclass
class Entry:
    """Un contexto puede repetirse con varios textos en inglés, uno por cada redacción que tuvo entre versiones del juego, así que la clave es (contexto, inglés)."""

    context: str
    source: str
    target: str = ''
    fuzzy: bool = False
    previous: str = ''
    notes: tuple = ()
    comments: tuple = ()

    @property
    def key(self):
        return self.context, self.source


def _quote(text):
    """Un texto de varias líneas empieza con "" y sigue con una cadena por línea."""
    lines = ['"' + re.sub(r'[\\"\n\t\r]', lambda m: ESCAPES[m[0]], line) + '"' for line in re.findall(r'[^\n]*\n|[^\n]+', text)]
    return '\n'.join(lines if len(lines) == 1 else ['""', *lines])


def _unquote(quoted):
    return re.sub(r'\\.', lambda m: UNESCAPES.get(m[0], m[0][1]), re.search(r'"(.*)"', quoted)[1])


def parse_po(text):
    """Cabecera y entradas de un PO."""
    header, entries = HEADER, []
    fields, name, fuzzy, notes, comments = {}, None, False, [], []
    for line in [*text.splitlines(), '']:
        if 'msgstr' in fields and not line.startswith('"'):
            if 'msgctxt' in fields:
                entries.append(Entry(fields['msgctxt'], fields['msgid'], fields['msgstr'], fuzzy,
                                     fields.get('#| msgid', ''), tuple(notes), tuple(comments)))
            elif not fields['msgid']:
                header = fields['msgstr']
            fields, fuzzy, notes, comments = {}, False, [], []
        prefix, body = ('#| ', line[3:]) if line.startswith('#| ') else ('', line)
        if body.startswith('msg'):
            keyword, _, value = body.partition(' ')
            name = prefix + keyword
            fields[name] = _unquote(value)
        elif body.startswith('"'):
            fields[name] += _unquote(body)
        elif line.startswith('#,'):
            fuzzy = 'fuzzy' in line
        elif line.startswith('#.'):
            notes.append(line[2:].strip())
        elif line == '#' or line.startswith('# '):
            comments.append(line[2:])
    return header, entries


def format_po(header, entries):
    """Los textos con marcadores de printf llevan `c-format` para que los editores de PO comprueben que la traducción los conserva."""
    blocks = [f'msgid ""\nmsgstr {_quote(header)}\n']
    for entry in entries:
        lines = [*(f'# {comment}'.rstrip() for comment in entry.comments), *(f'#. {note}' for note in entry.notes)]
        if flags := [flag for flag, on in (('fuzzy', entry.fuzzy), ('c-format', PRINTF.search(entry.source))) if on]:
            lines.append('#, ' + ', '.join(flags))
        if entry.fuzzy and entry.previous:
            lines += [f'#| {line}' for line in f'msgid {_quote(entry.previous)}'.split('\n')]
        lines += [f'msgctxt {_quote(entry.context)}', f'msgid {_quote(entry.source)}', f'msgstr {_quote(entry.target)}']
        blocks.append('\n'.join(lines) + '\n')
    return '\n'.join(blocks)


def catalog_path(component, language=None):
    return ROOT / 'po' / component / (f'{language}.po' if language else f'{component}.pot')


def write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8', newline='\n')


# --- Formatos del juego ---

def matches(pattern, path):
    """`*` vale dentro de un solo segmento de la ruta."""
    wanted, actual = pattern.split('/'), path.split('/')
    return len(wanted) == len(actual) and all(map(fnmatchcase, actual, wanted))


@dataclass(eq=False)
class Rules:
    """Dónde están los textos: archivos de idioma, libros y, por cada JSON, los punteros de sus nodos traducibles; las claves de los objetos nunca se traducen. `json` son cadenas sueltas. `lines` son arreglos de líneas que se traducen como un solo texto, para poder agregar o quitar líneas. `layout` son datos que siguen a la redacción, como qué palabras resalta un letrero, y se traducen como JSON. `restore` son archivos que la traducción conserva en las versiones del juego que ya no los traen, como un libro eliminado."""

    lang: list
    books: list
    json: dict
    lines: dict = field(default_factory=dict)
    layout: dict = field(default_factory=dict)
    restore: list = field(default_factory=list)

    @cache
    def patterns(self, path):
        return {kind: [pointer for glob, pointers in getattr(self, kind).items() if matches(glob, path) for pointer in pointers]
                for kind in ('lines', 'layout', 'json')}

    def component(self, path):
        if any(matches(glob, path) for glob in self.lang):
            return 'lang'
        if any(matches(glob, path) for glob in self.books):
            return 'libros'
        if any(self.patterns(path).values()):
            return 'textos'

    def kind(self, path, pointer):
        """Cómo se traduce un nodo JSON (`lines`, `layout` o `json`), o None si no es texto."""
        return next((kind for kind, patterns in self.patterns(path).items() if any(matches(p, pointer) for p in patterns)), None)


def lang_spans(text):
    """Entradas `<id> <texto>#` de un archivo de idioma: el texto puede ocupar varias líneas y las líneas que empiezan con `#` entre entradas son comentarios."""
    spans, index = [], 0
    entry = re.compile(r'^(\d+) ', re.M)
    while (match := entry.search(text, index)) and (end := text.find('#', match.end())) >= 0:
        spans.append((match[1], match.end(), end))
        index = end + 1
    return spans


def worth(text):
    """Solo vale traducir textos con letras; el juego deja las entradas sin uso como `DEPRECATED` y la primera como `null`."""
    return text not in ('DEPRECATED', 'null') and re.search(r'[^\W\d_]', text) is not None


def escape(key):
    return str(key).replace('~', '~0').replace('/', '~1')


def json_nodes(node, pointer='', parent=None, key=None):
    """Todos los nodos de un JSON en orden, con su JSON pointer y su lugar en el nodo padre."""
    yield pointer, node, parent, key
    children = node.items() if isinstance(node, dict) else enumerate(node) if isinstance(node, list) else ()
    for child_key, child in children:
        yield from json_nodes(child, f'{pointer}/{escape(child_key)}', node, child_key)


def encode(kind, node):
    """Texto de catálogo de un nodo JSON, o None si el nodo no es del tipo esperado."""
    match kind, node:
        case 'json', str():
            return node
        case 'lines', list() if all(isinstance(line, str) for line in node):
            return '\n'.join(node)
        case 'layout', dict() | list():
            return json.dumps(node, ensure_ascii=False, separators=(',', ':'))


def json_texts(path, document, rules):
    """(puntero, tipo, inglés, padre, clave) de cada nodo traducible de un JSON."""
    for pointer, node, parent, key in json_nodes(document):
        kind = rules.kind(path, pointer)
        if kind and (source := encode(kind, node)) is not None and (kind == 'layout' or worth(source)):
            yield pointer, kind, source, parent, key


def is_book(path):
    return path.startswith('books/') and path.endswith('.txt')


def book_title(path):
    """Las versiones sin lang/book_names.json titulan los libros con el nombre del archivo: el título traducido renombra el archivo y el original se ignora."""
    title = path[len('books/'):-len('.txt')]
    return f'{BOOK_NAMES}:/book_names/{escape(title)}', title


def untitled_books(files):
    """Libros sin entrada en lang/book_names.json; en las versiones sin ese archivo, todos."""
    names = json.loads(files[BOOK_NAMES])['book_names'] if BOOK_NAMES in files else {}
    return [path for path in files if is_book(path) and book_title(path)[1] not in names]


def units(path, text, rules):
    """(contexto, inglés) de cada texto traducible del archivo, en orden."""
    match rules.component(path):
        case 'lang':
            return [(f'{path}:{number}', text[start:end]) for number, start, end in lang_spans(text) if worth(text[start:end])]
        case 'libros':
            # Cada libro es un solo texto: la traducción mueve las líneas en blanco para que quepa en las páginas.
            return [(path, text)] if worth(text) else []
        case 'textos':
            return [(f'{path}:{pointer}', source) for pointer, _, source, _, _ in json_texts(path, json.loads(text), rules)]
    return []


def align(path, english, translated, rules):
    """Traducciones de los textos de `english` que hay en `translated`, un archivo traducido con la misma estructura."""
    match rules.component(path):
        case 'lang':
            targets = {number: translated[start:end] for number, start, end in lang_spans(translated)}
            return {(context, source): targets[number] for context, source in units(path, english, rules)
                    if (number := context.rpartition(':')[2]) in targets}
        case 'libros':
            return {key: translated for key in units(path, english, rules)}
        case 'textos':
            document, found = json.loads(english), {}
            for pointer, kind, source, _, _ in json_texts(path, document, rules):
                node, twin = document, json.loads(translated)
                for segment in pointer.split('/')[1:]:
                    segment = segment.replace('~1', '/').replace('~0', '~')
                    # Si un arreglo cambió de largo sus índices se desplazan y no hay forma fiable de emparejarlos.
                    match node, twin:
                        case dict(), dict():
                            node, twin = node.get(segment), twin.get(segment)
                        case list(), list() if len(node) == len(twin):
                            node, twin = node[int(segment)], twin[int(segment)]
                        case _:
                            break
                else:
                    if (target := encode(kind, twin)) is not None:
                        found[f'{path}:{pointer}', source] = target
            return found
    return {}


def translate_file(path, text, rules, translate):
    """`text` con cada texto reemplazado por `translate(contexto, inglés)`; None conserva el inglés."""
    match rules.component(path):
        case 'lang':
            parts, last = [], 0
            for number, start, end in lang_spans(text):
                target = translate(f'{path}:{number}', text[start:end]) if worth(text[start:end]) else None
                if target is not None:
                    if '#' in target or len(f'{number} {target}'.encode()) > 1023:
                        raise ValueError(f'{path}:{number}: el juego corta la entrada en el primer «#» y solo lee 1023 bytes: {target!r}')
                    parts += [text[last:start], target]
                    last = end
            return ''.join(parts) + text[last:]
        case 'libros':
            return (translate(path, text) if worth(text) else None) or text
        case 'textos':
            document = json.loads(text)
            for pointer, kind, source, parent, key in [*json_texts(path, document, rules)]:
                target = translate(f'{path}:{pointer}', source)
                if target is not None:
                    try:
                        parent[key] = json.loads(target) if kind == 'layout' else target.split('\n') if kind == 'lines' else target
                    except ValueError as error:
                        error.add_note(f'{path}:{pointer}: la maquetación no es JSON válido: {target!r}')
                        raise
            return json.dumps(document, ensure_ascii=False, indent='\t') + '\n'
    return text


# --- Versiones ---

def version_key(version):
    return tuple(int(part) for part in version.split('.'))


def versions():
    """Versiones con textos en inglés en source/, de la más nueva a la más antigua."""
    return sorted((folder.name for folder in SOURCE.iterdir() if folder.is_dir()), key=version_key, reverse=True)


def read_files(folder):
    """Textos de una carpeta por ruta relativa, con \\n y sin BOM."""
    return {file.relative_to(folder).as_posix(): file.read_text(encoding='utf-8-sig')
            for file in folder.rglob('*') if file.is_file()}


# --- Comandos ---

def extract(args, rules):
    for version, game in (game.split('=', 1) for game in args.game):
        shutil.rmtree(SOURCE / version, ignore_errors=True)
        for file in Path(game).rglob('*'):
            path = file.relative_to(game).as_posix()
            if rules.component(path) and file.is_file():
                write_text(SOURCE / version / path, file.read_text(encoding='utf-8-sig'))
    english = {version: read_files(SOURCE / version) for version in versions()}
    for path in rules.restore:
        origin = next((files[path] for files in english.values() if path in files), None)
        for version, files in english.items():
            if origin is not None and path not in files:
                files[path] = origin
                write_text(SOURCE / version / path, origin)

    for component in COMPONENTS:
        found = {}
        for path in sorted({path for files in english.values() for path in files if rules.component(path) == component}):
            for version, files in english.items():
                for key in units(path, files[path], rules) if path in files else ():
                    found.setdefault(key, []).append(version)
        if component == 'textos':
            for version, files in english.items():
                for path in untitled_books(files):
                    found.setdefault(book_title(path), []).append(version)
        template = []
        for (context, source), present in found.items():
            notes = [NOTES[kind]] if (kind := rules.kind(*context.partition(':')[::2])) in NOTES else []
            if len(present) < len(english):
                notes.append('Versiones: ' + ', '.join(sorted(present, key=version_key)))
            template.append(Entry(context, source, notes=tuple(notes)))
        write_text(catalog_path(component), format_po(HEADER, template))

        for po in catalog_path(component).parent.glob('*.po'):
            header, old = parse_po(po.read_text(encoding='utf-8'))
            kept = {entry.key: entry for entry in old}
            # Un texto cuyo inglés cambió queda en borrador con la traducción de su redacción anterior.
            drafts = {entry.context: entry for entry in reversed(old) if entry.target and not entry.fuzzy}
            merged = []
            for entry in template:
                if before := kept.get(entry.key):
                    entry = replace(before, notes=entry.notes)
                elif before := drafts.get(entry.context):
                    entry = replace(entry, target=before.target, fuzzy=True, previous=before.source)
                merged.append(entry)
            write_text(po, format_po(header, merged))
        print(f'{component}: {len(template)} textos')


def import_folder(args, rules):
    folder, english = Path(args.folder), read_files(SOURCE / args.version)
    found, unpaired = {}, []
    for path, text in english.items():
        if (translated := folder / path).is_file():
            aligned = align(path, text, translated.read_text(encoding='utf-8-sig'), rules)
            if not aligned and units(path, text, rules):
                unpaired.append(path)
            # Un texto que la traducción dejó vacío a propósito se guarda como un espacio.
            found |= {key: target if target.strip() else ' ' for key, target in aligned.items()}
    if (names := folder / BOOK_NAMES).is_file():
        titles = json.loads(names.read_text(encoding='utf-8-sig'))['book_names']
        found |= {book_title(path): titles[book_title(path)[1]] for path in untitled_books(english) if book_title(path)[1] in titles}
    for component in COMPONENTS:
        po = catalog_path(component, args.language)
        header, entries = parse_po(po.read_text(encoding='utf-8'))
        imported = 0
        for entry in entries:
            target = found.get(entry.key)
            if target is not None and (not entry.target or (args.overwrite and entry.target != target)):
                entry.target, entry.fuzzy, entry.previous = target, False, ''
                imported += 1
        write_text(po, format_po(header, entries))
        print(f'{component}: {imported} traducciones importadas')
    if unpaired:
        print('Sin emparejar (estructura distinta):', ', '.join(unpaired))

    # Los binarios (fuentes, imágenes, mapas) reemplazan los recursos de la versión; los archivos sueltos en la raíz de la carpeta, como la vista previa del Workshop, no son del juego.
    binaries = [file for file in folder.rglob('*') if file.is_file() and file.parent != folder and file.suffix not in ('.txt', '.json')]
    if binaries:
        shutil.rmtree(ASSETS / args.version, ignore_errors=True)
        for file in binaries:
            target = ASSETS / args.version / file.relative_to(folder)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(file, target)
        print(f'recursos de {args.version}: {len(binaries)} archivos')


def translations(language, fuzzy=False):
    """Traducción de cada (contexto, inglés). Un msgstr vacío significa «sin traducir», así que un texto vacío a propósito se escribe como un espacio."""
    return {entry.key: '' if entry.target.isspace() else entry.target
            for component in COMPONENTS
            for entry in parse_po(catalog_path(component, language).read_text(encoding='utf-8'))[1]
            if entry.target and (fuzzy or not entry.fuzzy)}


def build(args, rules):
    out = Path(args.out or ROOT / 'build' / args.version)
    shutil.rmtree(out, ignore_errors=True)
    done = translations(args.language, args.fuzzy)
    files = read_files(SOURCE / args.version)
    ignored = []
    for path, english in files.items():
        translated = translate_file(path, english, rules, lambda context, source: done.get((context, source)))
        title = done.get(book_title(path)) if BOOK_NAMES not in files and is_book(path) else None
        if title:
            ignored.append(path[len('books/'):])
            write_text(out / f'books/{title}.txt', translated)
        elif translated != english:
            write_text(out / path, translated)
    if ignored:
        write_text(out / 'books/ignored_books.json', json.dumps({'ignored_books': sorted(ignored)}, ensure_ascii=False, indent='\t') + '\n')
    if BOOK_NAMES in files and (untitled := untitled_books(files)):
        names = out / BOOK_NAMES
        document = json.loads(names.read_text(encoding='utf-8') if names.exists() else files[BOOK_NAMES])
        for path in untitled:
            document['book_names'][book_title(path)[1]] = done.get(book_title(path), book_title(path)[1])
        write_text(names, json.dumps(document, ensure_ascii=False, indent='\t') + '\n')
    if (ASSETS / args.version).is_dir():
        shutil.copytree(ASSETS / args.version, out, dirs_exist_ok=True)
    print(f'{args.version}: {sum(file.is_file() for file in out.rglob("*"))} archivos en {out}')


def stats(args, rules):
    done = translations(args.language)
    print('| Versión | ' + ' | '.join(COMPONENTS) + ' |\n|---|' + '---|' * len(COMPONENTS))
    for version in versions():
        files, cells = read_files(SOURCE / version), []
        for component in COMPONENTS:
            keys = [key for path, text in files.items() if rules.component(path) == component for key in units(path, text, rules)]
            cells.append(f'{sum(key in done for key in keys)}/{len(keys)}')
        print(f'| {version} | ' + ' | '.join(cells) + ' |')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--language', '-l', default='es', help='idioma del catálogo')
    commands = parser.add_subparsers(required=True)
    command = commands.add_parser('extract', help='lee los textos en inglés de cada versión del juego y actualiza los catálogos')
    command.add_argument('--game', '-g', action='append', default=[], metavar='VERSIÓN=CARPETA')
    command.set_defaults(run=extract)
    command = commands.add_parser('import', help='importa una carpeta traducida con la estructura del juego')
    command.add_argument('version', choices=versions())
    command.add_argument('folder')
    command.add_argument('--overwrite', action='store_true', help='reemplaza las traducciones existentes')
    command.set_defaults(run=import_folder)
    command = commands.add_parser('build', help='genera la carpeta traducida de una versión')
    command.add_argument('version', choices=versions())
    command.add_argument('--out', '-o')
    command.add_argument('--fuzzy', action='store_true', help='incluye las traducciones en borrador')
    command.set_defaults(run=build)
    commands.add_parser('stats', help='progreso por versión y catálogo').set_defaults(run=stats)
    args = parser.parse_args()
    args.run(args, Rules(**json.loads((ROOT / 'rules.json').read_text(encoding='utf-8'))))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
