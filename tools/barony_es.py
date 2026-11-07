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
from pathlib import Path

COMPONENTS = ('lang', 'textos', 'libros')
BOOK_NAMES = 'lang/book_names.json'
ROOT = Path(__file__).resolve().parent.parent


# --- Catálogos PO -------------------------------------------------------------

def _quote(text):
    """Las cadenas de varias líneas empiezan con "" y se parten tras cada \\n, como msgcat."""
    escaped = [
        '"' + re.sub(r'[\\"\n\t\r]', lambda m: {'\n': r'\n', '\t': r'\t', '\r': r'\r'}.get(m[0], '\\' + m[0]), line) + '"'
        for line in re.findall(r'[^\n]*\n|[^\n]+', text)
    ]
    if not escaped:
        return '""'
    return escaped[0] if len(escaped) == 1 else '""\n' + '\n'.join(escaped)


def _unquote(quoted):
    body = re.search(r'"(.*)"', quoted)[1]
    return re.sub(r'\\(.)', lambda m: {'n': '\n', 't': '\t', 'r': '\r'}.get(m[1], m[1]), body)


def parse_po(text):
    """Entradas de un PO. Un mismo contexto puede aparecer con varios textos en inglés, uno por
    cada versión del juego en que cambió, así que la clave es (msgctxt, msgid)."""
    entries, language = [], None
    fields, notes, fuzzy, field = {}, [], False, None
    for line in text.splitlines() + ['']:
        if 'msgstr' in fields and (not line or line.startswith(('#', 'msg'))):
            if 'msgctxt' in fields:
                entries.append({
                    'context': fields['msgctxt'], 'source': fields['msgid'], 'target': fields['msgstr'],
                    'fuzzy': fuzzy, 'previous': fields.get('#|msgid', ''), 'notes': '\n'.join(notes),
                })
            elif fields['msgid'] == '':
                found = re.search(r'^Language: *(\S+)$', fields['msgstr'], re.M)
                language = found and found[1]
            fields, notes, fuzzy, field = {}, [], False, None
        prefix, body = ('#|', line[3:]) if line.startswith('#| ') else ('', line)
        if body.startswith('#.'):
            notes.append(body[2:].strip())
        elif body.startswith('#,'):
            fuzzy = 'fuzzy' in (flag.strip() for flag in body[2:].split(','))
        elif body.startswith('"') and field:
            fields[field] += _unquote(body)
        elif body.startswith('msg'):
            name, _, value = body.partition(' ')
            field = prefix + name
            fields[field] = _unquote(value)
    return language, entries


def format_po(language, entries):
    header = ['msgid ""', 'msgstr ""', r'"Project-Id-Version: Barony\n"']
    if language:
        header.append(rf'"Language: {language}\n"')
    header += [r'"MIME-Version: 1.0\n"', r'"Content-Type: text/plain; charset=UTF-8\n"',
               r'"Content-Transfer-Encoding: 8bit\n"']
    blocks = [header]
    for entry in entries:
        block = [f'#. {note}' for note in entry['notes'].split('\n') if entry['notes']]
        if entry['fuzzy']:
            block.append('#, fuzzy')
            if entry['previous']:
                block += [f'#| {line}' for line in f'msgid {_quote(entry["previous"])}'.split('\n')]
        block += [f'msgctxt {_quote(entry["context"])}', f'msgid {_quote(entry["source"])}',
                  f'msgstr {_quote(entry["target"])}']
        blocks.append(block)
    return '\n'.join('\n'.join(block) + '\n' for block in blocks)


def catalog_path(component, language=None):
    return ROOT / 'po' / component / (f'{language}.po' if language else f'{component}.pot')


# --- Formatos del juego -------------------------------------------------------

def _glob(pattern):
    return re.compile('^' + '[^/]*'.join(map(re.escape, pattern.split('*'))) + '$')


class Rules:
    """Dónde están los textos: archivos de idioma, libros y, por cada JSON, las rutas de sus hojas
    traducibles (`*` vale por una clave o índice). Las claves de los objetos nunca se traducen.
    `lines` son arreglos de líneas que se traducen como un solo texto, para poder agregar o quitar
    líneas. `layout` son datos que siguen a la redacción, como qué palabras resalta un letrero, y se
    traducen como JSON. `restore` son archivos que la traducción recupera de versiones anteriores
    aunque el juego ya no los traiga, como un libro eliminado."""

    def __init__(self, data):
        self.lang, self.books = data['lang'], data['books']
        self.sections = {'json': data['json'], 'lines': data.get('lines', {}), 'layout': data.get('layout', {})}
        self.restore = data.get('restore', [])

    def component(self, path):
        if any(_glob(g).match(path) for g in self.lang):
            return 'lang'
        if any(_glob(g).match(path) for g in self.books):
            return 'libros'
        if any(_glob(g).match(path) for section in self.sections.values() for g in section):
            return 'textos'
        return None

    def patterns(self, path, section='json'):
        return [p for g, ps in self.sections[section].items() if _glob(g).match(path) for p in ps]

    def kind(self, context):
        """Cómo se traduce un texto JSON: `json` (una cadena), `lines` o `layout`."""
        path, _, pointer = context.partition(':')
        return next((s for s in ('lines', 'layout') if any(_matches(p, pointer) for p in self.patterns(path, s))), 'json')


def lang_spans(text):
    """Entradas `<id> <texto>#` de un archivo de idioma: el texto puede ocupar varias líneas y las
    líneas que empiezan con `#` entre entradas son comentarios."""
    spans, index = [], 0
    entry = re.compile(r'^(\d+) ', re.M)
    while (match := entry.search(text, index)) and (end := text.find('#', match.end())) >= 0:
        spans.append((match[1], match.end(), end))
        index = end + 1
    return spans


def _escape(key):
    return str(key).replace('~', '~0').replace('/', '~1')


def _segments(pointer):
    return [s.replace('~1', '/').replace('~0', '~') for s in pointer.split('/')[1:]]


def json_nodes(node, pointer=''):
    """Todos los nodos de un JSON en orden, con su JSON pointer."""
    yield pointer, node
    if isinstance(node, dict):
        for key, value in node.items():
            yield from json_nodes(value, f'{pointer}/{_escape(key)}')
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from json_nodes(value, f'{pointer}/{index}')


def _matches(pattern, pointer):
    wanted, actual = pattern.split('/'), pointer.split('/')
    return len(wanted) == len(actual) and all(w in ('*', a) for w, a in zip(wanted, actual))


def _worth(text):
    """Solo vale traducir textos con letras; el juego deja las entradas sin uso como `DEPRECATED`
    y la primera como `null`."""
    return text not in ('DEPRECATED', 'null') and re.search(r'[^\W\d_]', text) is not None


def _compact(node):
    return json.dumps(node, ensure_ascii=False, separators=(',', ':'))


def is_book(path):
    return path.startswith('books/') and path.endswith('.txt')


def book_title(path):
    """Las versiones sin lang/book_names.json titulan los libros con el nombre del archivo: el título
    traducido renombra el archivo y el original se ignora."""
    title = path[len('books/'):-len('.txt')]
    return f'{BOOK_NAMES}:/book_names/{_escape(title)}', title


def untitled_books(files):
    """Libros sin entrada en lang/book_names.json; en las versiones sin ese archivo, todos."""
    if BOOK_NAMES not in files:
        return [path for path in files if is_book(path)]
    names = json.loads(read_text(files[BOOK_NAMES]))['book_names']
    return [path for path in files if is_book(path) and book_title(path)[1] not in names]


def units(path, text, rules):
    """(contexto, texto en inglés) de cada texto traducible del archivo, en orden."""
    kind = rules.component(path)
    if kind == 'lang':
        return [(f'{path}:{id}', text[start:end]) for id, start, end in lang_spans(text) if _worth(text[start:end])]
    if kind == 'libros':
        # Cada libro es un solo texto: los traductores mueven las líneas en blanco para que quepa en las páginas.
        return [(path, text)] if _worth(text) else []
    if kind == 'textos':
        found = []
        for pointer, node in json_nodes(json.loads(text)):
            context = f'{path}:{pointer}'
            if any(_matches(p, pointer) for p in rules.patterns(path, rules.kind(context))):
                source = _encode(rules.kind(context), node)
                if source is not None and (rules.kind(context) == 'layout' or _worth(source)):
                    found.append((context, source))
        return found
    return []


def _encode(kind, node):
    """Texto del catálogo para un nodo JSON, o None si el nodo no es de ese tipo."""
    if kind == 'layout':
        return _compact(node) if isinstance(node, (dict, list)) else None
    if kind == 'lines':
        return '\n'.join(node) if isinstance(node, list) and all(isinstance(x, str) for x in node) else None
    return node if isinstance(node, str) else None


def _decode(kind, text):
    return json.loads(text) if kind == 'layout' else text.split('\n') if kind == 'lines' else text


def _find(source, target, segments):
    """Nodo de `target` en `segments`, recorriendo `source` a la par: si un arreglo cambió de largo,
    todos sus índices se desplazan y no hay forma fiable de emparejarlos."""
    for segment in segments:
        if isinstance(source, dict) and isinstance(target, dict):
            source, target = source.get(segment), target.get(segment)
        elif isinstance(source, list) and isinstance(target, list) and len(source) == len(target):
            source, target = source[int(segment)], target[int(segment)]
        else:
            return None
    return target


def align(path, english, translated, rules):
    """Traducciones de los textos de `english` que hay en `translated`, un archivo traducido con la
    misma estructura."""
    found = units(path, english, rules)
    kind = rules.component(path)
    if kind == 'lang':
        ids = {id: translated[start:end] for id, start, end in lang_spans(translated)}
        return {(c, s): ids[c.rsplit(':', 1)[1]] for c, s in found if c.rsplit(':', 1)[1] in ids}
    if kind == 'libros':
        return {key: translated for key in found}
    if kind == 'textos':
        source, target, result = json.loads(english), json.loads(translated), {}
        for context, text in found:
            node = _encode(rules.kind(context), _find(source, target, _segments(context[len(path) + 1:])))
            if node is not None:
                result[context, text] = node
        return result
    return {}


def _set(node, segments, value):
    for segment in segments[:-1]:
        node = node[int(segment)] if isinstance(node, list) else node[segment]
    if isinstance(node, list):
        node[int(segments[-1])] = value
    else:
        node[segments[-1]] = value


def translate_file(path, text, rules, translate):
    """`text` con cada texto reemplazado por `translate(contexto, inglés)` (None conserva el inglés)."""
    kind = rules.component(path)
    if kind == 'lang':
        parts, last = [], 0
        for id, start, end in lang_spans(text):
            source = text[start:end]
            target = translate(f'{path}:{id}', source) if _worth(source) else None
            if target is not None and '#' in target:
                raise ValueError(f'{path}:{id}: «#» termina una entrada del archivo de idioma: {target!r}')
            parts += [text[last:start], source if target is None else target]
            last = end
        return ''.join(parts) + text[last:]
    if kind == 'libros':
        return (translate(path, text) if _worth(text) else None) or text
    if kind == 'textos':
        document = json.loads(text)
        for context, source in units(path, text, rules):
            target = translate(context, source)
            if target is not None:
                _set(document, _segments(context[len(path) + 1:]), _decode(rules.kind(context), target))
        return json.dumps(document, ensure_ascii=False, indent='\t') + '\n'
    return text


# --- Archivos por versión -----------------------------------------------------

def version_key(version):
    return tuple(int(part) for part in version.split('.'))


class VersionStore:
    """Archivos de varias versiones guardados una sola vez: la versión más nueva completa y cada
    versión anterior solo con lo que difiere de la siguiente, más `.removed`, la lista de archivos
    de la siguiente que no tiene."""

    def __init__(self, root):
        self.root = Path(root)

    @property
    def versions(self):
        if not self.root.is_dir():
            return []
        return sorted((d.name for d in self.root.iterdir() if d.is_dir()), key=version_key, reverse=True)

    def read(self, version):
        files = {}
        for current in self.versions:
            directory = self.root / current
            removed = directory / '.removed'
            for path in removed.read_text(encoding='utf-8').splitlines() if removed.exists() else []:
                files.pop(path, None)
            for file in directory.rglob('*'):
                if file.is_file() and file.name != '.removed':
                    files[file.relative_to(directory).as_posix()] = file.read_bytes()
            if current == version:
                return files
        raise KeyError(f'{version} no está en {self.root}')

    def write(self, contents):
        if self.root.exists():
            shutil.rmtree(self.root)
        newer = None
        for version in sorted(contents, key=version_key, reverse=True):
            files = contents[version]
            for path, data in files.items():
                if newer is None or newer.get(path) != data:
                    target = self.root / version / path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
            if newer is not None:
                # Las versiones anteriores siempre llevan `.removed`, aunque esté vacío, para que git conserve la carpeta.
                (self.root / version).mkdir(parents=True, exist_ok=True)
                (self.root / version / '.removed').write_text(
                    ''.join(f'{path}\n' for path in sorted(newer) if path not in files), encoding='utf-8', newline='\n')
            newer = files


def read_text(data):
    """Los textos se guardan con \\n y sin BOM, así las versiones que solo difieren en saltos de línea
    comparten el archivo."""
    return data.decode('utf-8').removeprefix('﻿').replace('\r\n', '\n')


def write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8', newline='\n')


# --- Comandos -----------------------------------------------------------------

def load_catalogs(language):
    catalogs = {}
    for component in COMPONENTS:
        po = catalog_path(component, language)
        catalogs[component] = parse_po((po if po.exists() else catalog_path(component)).read_text(encoding='utf-8'))
    return catalogs


def extract(args, rules, sources):
    games = dict(game.split('=', 1) for game in args.game)
    roots = {glob.split('/')[0] for glob in [*rules.lang, *rules.books, *(g for s in rules.sections.values() for g in s)]}
    english = {version: sources.read(version) for version in sources.versions if version not in games}
    for version, folder in games.items():
        folder, files = Path(folder), {}
        for root in roots:
            for file in (folder / root).rglob('*') if (folder / root).is_dir() else []:
                path = file.relative_to(folder).as_posix()
                if file.is_file() and rules.component(path):
                    files[path] = read_text(file.read_bytes()).encode('utf-8')
        english[version] = files
    # Libros que la traducción recupera de versiones anteriores, aunque el juego ya no los traiga.
    for path in rules.restore:
        origin = next((english[v][path] for v in sorted(english, key=version_key, reverse=True) if path in english[v]), None)
        for files in english.values() if origin else []:
            files.setdefault(path, origin)
    sources.write(english)

    versions = sorted(english, key=version_key, reverse=True)
    paths = sorted({path for files in english.values() for path in files})
    for component in COMPONENTS:
        found = {}
        for path in (path for path in paths if rules.component(path) == component):
            for version in versions:
                if path in english[version]:
                    for key in units(path, read_text(english[version][path]), rules):
                        found.setdefault(key, set()).add(version)
        if component == 'textos':
            for version in versions:
                for path in untitled_books(english[version]):
                    found.setdefault(book_title(path), set()).add(version)
        template = []
        for (context, source), present in found.items():
            notes = []
            if rules.kind(context) == 'layout':
                notes.append('Maquetación en JSON: ajústala si la traducción cambia la posición de palabras o líneas.')
            elif rules.kind(context) == 'lines':
                notes.append('Cada línea es un renglón en el juego; puedes agregar o quitar líneas para que no se desborde.')
            if len(present) < len(versions):
                notes.append('Versiones: ' + ', '.join(sorted(present, key=version_key)))
            template.append({'context': context, 'source': source, 'target': '', 'fuzzy': False,
                             'previous': '', 'notes': '\n'.join(notes)})
        write_text(catalog_path(component), format_po(None, template))

        # Se actualiza como msgmerge: la traducción de un texto que cambió queda en borrador con su texto anterior.
        for po in catalog_path(component).parent.glob('*.po'):
            language, old = parse_po(po.read_text(encoding='utf-8'))
            kept = {(e['context'], e['source']): e for e in old}
            changed = {e['context']: e for e in old if e['target'] and (e['context'], e['source']) not in found}
            merged = []
            for entry in template:
                key = entry['context'], entry['source']
                if key in kept:
                    entry = {**entry, **{k: kept[key][k] for k in ('target', 'fuzzy', 'previous')}}
                elif entry['context'] in changed:
                    before = changed[entry['context']]
                    entry = {**entry, 'target': before['target'], 'fuzzy': True, 'previous': before['source']}
                merged.append(entry)
            write_text(po, format_po(language, merged))
        print(f'{component}: {len(template)} textos')


def import_folder(args, rules, sources, assets):
    folder, english = Path(args.folder), sources.read(args.version)
    found, unpaired = {}, []
    for path, data in english.items():
        translated = folder / path
        if translated.is_file():
            aligned = align(path, read_text(data), read_text(translated.read_bytes()), rules)
            if not aligned and units(path, read_text(data), rules):
                unpaired.append(path)
            found.update({key: target if target.strip() else ' ' for key, target in aligned.items()})
    if (folder / BOOK_NAMES).is_file():
        names = json.loads(read_text((folder / BOOK_NAMES).read_bytes()))['book_names']
        found.update({book_title(path): names[book_title(path)[1]]
                      for path in untitled_books(english) if book_title(path)[1] in names})
    for component, (language, entries) in load_catalogs(args.language).items():
        imported = 0
        for entry in entries:
            target = found.get((entry['context'], entry['source']))
            if target is not None and (not entry['target'] or (args.overwrite and entry['target'] != target)):
                entry.update(target=target, fuzzy=False, previous='')
                imported += 1
        write_text(catalog_path(component, args.language), format_po(language or args.language, entries))
        print(f'{component}: {imported} traducciones importadas')
    if unpaired:
        print('Sin emparejar (estructura distinta):', ', '.join(unpaired))

    # Los binarios (fuentes, imágenes, mapas) reemplazan los recursos de la versión; los archivos
    # sueltos en la raíz de la carpeta, como la vista previa del Workshop, no son del juego.
    binaries = {file.relative_to(folder).as_posix(): file.read_bytes() for file in folder.rglob('*')
                if file.is_file() and '/' in file.relative_to(folder).as_posix() and file.suffix not in ('.txt', '.json')}
    if binaries:
        assets.write({v: binaries if v == args.version else assets.read(v) for v in {*assets.versions, args.version}})
        print(f'recursos de {args.version}: {len(binaries)} archivos')


def translations(language, fuzzy):
    """Un msgstr vacío significa «sin traducir», así que un texto vacío a propósito se escribe como un espacio."""
    return {(e['context'], e['source']): e['target'].strip() and e['target'] for _, entries in load_catalogs(language).values()
            for e in entries if e['target'] and (fuzzy or not e['fuzzy'])}


def build(args, rules, sources, assets):
    out = Path(args.out or ROOT / 'build' / args.version)
    if out.exists():
        shutil.rmtree(out)
    done = translations(args.language, args.fuzzy)
    files = sources.read(args.version)
    titled = BOOK_NAMES not in files
    missing = [] if titled else untitled_books(files)
    written, ignored = 0, []
    for path, data in files.items():
        english = read_text(data)
        translated = translate_file(path, english, rules, lambda c, s: done.get((c, s)))
        title = done.get(book_title(path)) if titled and is_book(path) else None
        if translated == english and title is None:
            continue
        if title:
            ignored.append(path[len('books/'):])
        write_text(out / (f'books/{title}.txt' if title else path), translated)
        written += 1
    if ignored:
        write_text(out / 'books' / 'ignored_books.json',
                   json.dumps({'ignored_books': sorted(ignored)}, ensure_ascii=False, indent='\t') + '\n')
    if missing:
        names = out / BOOK_NAMES
        document = json.loads(names.read_text(encoding='utf-8') if names.exists() else read_text(files[BOOK_NAMES]))
        for path in missing:
            document['book_names'][book_title(path)[1]] = done.get(book_title(path), book_title(path)[1])
        write_text(names, json.dumps(document, ensure_ascii=False, indent='\t') + '\n')
    if args.version in assets.versions:
        for path, data in assets.read(args.version).items():
            (out / path).parent.mkdir(parents=True, exist_ok=True)
            (out / path).write_bytes(data)
            written += 1
    print(f'{args.version}: {written} archivos en {out}')


def stats(args, rules, sources):
    done = translations(args.language, False)
    print('| Versión | ' + ' | '.join(COMPONENTS) + ' |\n|---|' + '---|' * len(COMPONENTS))
    for version in sources.versions:
        files, cells = sources.read(version), []
        for component in COMPONENTS:
            keys = [key for path, data in files.items() if rules.component(path) == component
                    for key in units(path, read_text(data), rules)]
            cells.append(f'{sum(key in done for key in keys)}/{len(keys)}')
        print(f'| {version} | ' + ' | '.join(cells) + ' |')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--language', '-l', default='es', help='idioma del catálogo')
    commands = parser.add_subparsers(dest='command', required=True)
    command = commands.add_parser('extract', help='lee los textos en inglés de cada versión del juego')
    command.add_argument('--game', '-g', action='append', default=[], metavar='VERSIÓN=CARPETA')
    command = commands.add_parser('import', help='importa una carpeta traducida con la estructura del juego')
    command.add_argument('version')
    command.add_argument('folder')
    command.add_argument('--overwrite', action='store_true', help='reemplaza las traducciones existentes')
    command = commands.add_parser('build', help='genera la carpeta traducida de una versión')
    command.add_argument('version')
    command.add_argument('--out', '-o')
    command.add_argument('--fuzzy', action='store_true', help='incluye las traducciones en borrador')
    commands.add_parser('stats', help='progreso por versión y catálogo')
    args = parser.parse_args()

    rules = Rules(json.loads((ROOT / 'rules.json').read_text(encoding='utf-8')))
    sources, assets = VersionStore(ROOT / 'source'), VersionStore(ROOT / 'assets')
    match args.command:
        case 'extract':
            extract(args, rules, sources)
        case 'import':
            import_folder(args, rules, sources, assets)
        case 'build':
            build(args, rules, sources, assets)
        case 'stats':
            stats(args, rules, sources)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
