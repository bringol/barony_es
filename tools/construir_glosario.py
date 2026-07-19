"""Construye un termbase inglés-español a partir de los JSON del proyecto, con tokenización avanzada."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

ENGLISH_DIR = PROJECT_ROOT / "1-ENG-VERSION"
SPANISH_DIR = PROJECT_ROOT / "v5.0.2"
POLISH_DIR = PROJECT_ROOT / "2-POLISH"

BASE_GLOSSARY = SCRIPT_DIR / "glosario_base.txt"
OUTPUT_GLOSSARY = SCRIPT_DIR / "glosario_completo.txt"
PLURAL_DERIVED_TERMS: set[str] = set()

# Expresiones regulares para limpieza avanzada
FORMAT_VARIABLE_RE = re.compile(
    r"%%|%(?:\d+\$)?[-+#0']*(?:\d+|\*)?(?:\.(?:\d+|\*))?"
    r"(?:hh|h|ll|l|L|j|z|t)?[diuoxXfFeEgGaAcspnhmt]"
)
POSSESSIVE_RE = re.compile(r"\b([A-Za-z]+)'s\b")
DIGIT_RE = re.compile(r"\d")
# Elimina toda la puntuación y símbolos extraños típicos de las interfaces (dejamos letras y números)
SYMBOLS_RE = re.compile(r"[!¡\?¿\"'()*^&$#@\[\]{}<>;:.,/\\|~`_+=\-]")
WHITESPACE_RE = re.compile(r"\s+")

# Elimina artículos y preposiciones al inicio de la frase para dejar solo el sustantivo/término
EN_ARTICLES_RE = re.compile(r"^(a|an|the|this|that|these|those)\s+", re.IGNORECASE)
ES_ARTICLES_RE = re.compile(r"^(el|la|los|las|un|una|unos|unas|este|esta|estos|estas|ese|esa)\s+", re.IGNORECASE)

EFFECT_PREFIX_RE = re.compile(
    r"^(?:"
    r"inflicts?|applies?|grants?|cures?|causes?|summons?|conjures?|casts?|"
    r"spawns?|restores?|reveals?|detects?|deals?|absorbs?|destroys?|"
    r"dismantles?|repairs?|prevents?|slows?|teleports?|retaliates?|"
    r"allows?|increases?|decreases?|removes?|provides?|adds?|transmutes?|"
    r"turns?|gives?"
    r")\s+"
)
ES_EFFECT_PREFIX_RE = re.compile(
    r"^(?:"
    r"inflige|aplica|brinda|concede|cura|causa|invoca|canaliza|lanza|"
    r"genera|restaura|recupera|revela|detecta|infligir|absorbe|destruye|"
    r"repara|previene|ralentiza|teletransporta|aumenta|reduce|remueve|"
    r"elimina|provee|proporciona|otorga|transmuta|convierte"
    r")\s+"
)

PROTECTED_ACRONYMS = {
    "ac", "atk", "cha", "chr", "con", "dex", "dmg", "en", "hp", "ht",
    "int", "mp", "per", "pts", "pwr", "res", "rgn", "spd", "str", "wgt",
    "xp",
}
MATH_VARIABLE_TOKENS = {"f", "g", "s", "x", "y", "z"}
TRAILING_FRAGMENT_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "but", "by",
    "broken", "can", "claimed", "could", "did", "do", "does", "for", "found",
    "from", "gained", "had", "has", "have", "if", "in", "into", "is", "kill",
    "may", "must", "of", "on", "once", "opened", "or", "read", "shall",
    "should", "sold", "than", "that", "the", "then", "through", "to", "upon",
    "used", "when", "while", "will", "with", "without", "would",
}
MID_FRAGMENT_PREPOSITIONS = {
    "a", "about", "an", "as", "at", "before", "by", "for", "from", "if",
    "in", "into", "near", "of", "on", "than", "the", "through", "to", "upon",
    "when", "while", "with", "without",
}
INTERNAL_AUXILIARY_WORDS = {
    "are", "be", "been", "being", "can", "cannot", "could", "did", "do",
    "does", "had", "has", "have", "is", "may", "must", "shall", "should",
    "will", "would",
}
INTERNAL_VERB_WORDS = {
    "assassinate", "consumes", "dealt", "degrade", "destroyed", "disarmed",
    "dropped", "earned", "eaten", "enscribed", "fashioned", "fired", "forged",
    "gained", "given", "gives", "hit", "killed", "lost", "opened", "provide",
    "pulled", "repaired", "restored", "salvaged", "sold", "spent", "tapped",
    "thrown", "touched", "trained", "used",
}
FRAGMENT_START_WORDS = {
    "able", "access", "activate", "active", "adds", "adopting", "allowing",
    "alights", "all", "allows", "appraise", "approaching", "are", "attempting",
    "augments", "avoid", "avoiding", "be", "being", "beware", "bottom",
    "bring", "buy", "can", "cannot", "choose", "collect", "come", "comes",
    "compared", "complete", "concerning",
    "consider", "continue", "could", "default",
    "depends", "destroy", "discard", "drink", "drinking", "drop", "enable",
    "ensure", "equip", "every", "fight", "find", "finding", "follow", "for",
    "from", "gain", "gaining", "get", "getting", "give", "go", "has", "have",
    "having", "help", "helps", "higher", "hold", "holding", "how", "if",
    "improve", "improves", "improving", "in", "increase", "increased",
    "increases", "interact", "keep", "keeping", "kill", "know", "knowing",
    "learn", "leave", "left", "less", "lies", "like", "low", "make",
    "making", "may", "mix",
    "more", "most", "move", "moving", "must", "need", "needs", "not",
    "observe", "once", "only", "open", "opened", "opening", "or", "point",
    "press", "pressing", "prioritize", "proceed", "pull", "read", "recruit",
    "regularly", "remember", "removable", "remove", "removed", "requires", "return", "select",
    "selecting", "some", "start", "staying", "take", "taking", "then",
    "there", "they", "this", "throw", "through", "to", "unlocked", "use",
    "used", "using", "view", "walking", "watch", "when", "where", "which",
    "while", "will", "with", "without", "you", "your",
}
FRAGMENT_PRONOUNS = {
    "he", "her", "him", "his", "it", "its", "our", "she", "their", "them",
    "they", "us", "we", "you", "your", "yourself",
}

UNIVERSAL_SINGLE_WORDS = {
    "abilities", "ability", "accordingly", "actions", "adventure", "area",
    "action", "all", "apple", "assistance", "average", "avoid", "bad",
    "base", "basic", "benefit", "benefits", "best", "better", "beware",
    "book", "books", "bottle", "bottles", "box", "boxes", "bread", "briefly",
    "bring", "broken", "bubble", "bubbly", "button", "buttons", "buzz",
    "cancel", "categories", "category", "caution", "cheese", "chest",
    "chests", "class", "classes", "collect", "commands", "complex",
    "considerably", "containers", "corner", "difference", "door", "doors",
    "effect", "effects", "equipment", "excellent", "face", "fighting", "fish",
    "food", "found", "games", "good", "grapes", "help", "here", "highest",
    "items", "key", "keys", "least", "left", "level", "levels", "locations",
    "meals", "meat", "name", "needs", "none", "normal", "notice", "objects",
    "options", "other", "out", "piece", "pieces", "plain", "point",
    "potential", "press", "profile", "rank", "reduced", "return", "side",
    "simple", "slot", "stats", "successes", "thanks", "time", "times",
    "together", "tools", "traps", "unknown", "useful", "water", "weapon",
    "weaponry", "weapons", "wood", "work",
}

ALLOWED_OF_PREFIXES = {
    "amulet", "book", "circlet", "cloak", "focus", "icon", "potion", "quiver",
    "ring", "scroll", "spell", "spellbook", "symbol", "tablet",
}
DOMAIN_KEYWORDS = PROTECTED_ACRONYMS | {
    "acid", "alchemy", "alchemist", "alembic", "amulet", "arcana", "arcane",
    "arcanist", "armor", "assassin", "automaton", "axe", "bard", "barbarian",
    "baphomet", "baron", "blackiron", "blocking", "bloodletting", "boots",
    "bow", "bracer", "breastpiece", "bronze", "burning", "castle", "cha",
    "chakram", "charisma", "cleric", "cloak", "cold", "constitution",
    "crossbow", "crystal", "curse", "cursed", "damage", "demon", "dexterity",
    "dracula", "drunk", "dungeon", "dwarf", "effect", "enchant", "fire",
    "fist", "flame", "food", "forge", "fountain", "gharbard", "gharbad",
    "ghost", "ghoul", "glaive", "glove", "gnome", "goatman", "goblin",
    "gold", "golem", "guild", "gyrobot", "halberd", "helm", "herx", "hood",
    "human", "hunter", "ice", "incubus", "insectoid", "intelligence", "iron",
    "jester", "jewel", "kobold", "lance", "lantern", "leadership", "leather",
    "levitation", "lich", "lore", "magic", "magicstaff", "mace", "magician",
    "mana", "mechanist", "merchant", "minotaur", "monk", "monster",
    "mysticism", "necromancy", "orb", "paladin", "perception", "pickaxe",
    "poison", "polearm", "polymorph", "potion", "pwr", "quiver", "ranged",
    "regen", "regeneration", "resistance", "ring", "rogue", "sapper", "scroll",
    "scutum", "shield", "shopkeeper", "skeleton", "skill", "slime", "sorcery",
    "spell", "spellbook", "spider", "staff", "stat", "stealth", "steel",
    "strength", "succubus", "sword", "thaumaturgy", "thumpus", "tinkering",
    "trading", "trap", "troll", "unarmed", "undead", "vampire", "warrior",
    "waterbreathing", "waterwalking", "wizard",
}
DOMAIN_SUFFIXES = {
    "ammo", "armor", "atk", "bonus", "bow", "class", "cloak", "curse",
    "damage", "effect", "form", "guild", "hat", "helm", "hood", "key", "lair",
    "magic", "maze", "potion", "power", "regen", "resistance", "skill", "spell",
    "staff", "stat", "status", "trap", "weapon",
}
MATERIAL_WORDS = {
    "blackiron", "bone", "bronze", "chain", "crystal", "iron", "leather",
    "quilted", "silver", "steel", "wooden",
}
EQUIPMENT_LIST_WORDS = {
    "ammo", "arm", "armor", "arrow", "axe", "beartrap", "boot", "bow",
    "bracer", "breastpiece", "chakram", "cloak", "crossbow", "dart", "flail",
    "gauntlet", "glaive", "glove", "halberd", "helm", "hood", "knuckle",
    "mace", "magicstaff", "plumbata", "polearm", "quiver", "shield",
    "shuriken", "spear", "staff", "sword", "tomahawk", "trap", "trident",
    "visor",
}
CREATURE_LIST_WORDS = {
    "automaton", "bat", "beast", "bugbear", "cockatrice", "crab", "demon",
    "dryad", "ghoul", "gnome", "goatman", "goblin", "golem", "human",
    "imp", "incubus", "insectoid", "kobold", "minotaur", "rat", "scarab",
    "scorpion", "skeleton", "slime", "spider", "succubus", "troll", "vampire",
}
ALLOWED_EXACT_TERMS = {
    "armor class", "attribute bonus", "base spell", "blood vial", "cast speed",
    "critical strike", "free action", "magic mapping", "magic missile",
    "magic reflection", "magic resistance", "melee attack", "poison resistance",
    "ranged attack", "slow digestion", "spell power", "status effect",
    "thrown weapon",
}

STATUS_ALIASES = {
    "asleep": "sleep",
    "bleed": "bleeding",
    "blinded": "blindness",
    "blind": "blindness",
    "burned": "burning",
    "burns": "burning",
    "confuse": "confusion",
    "confused": "confusion",
    "drunkenness": "drunk",
    "grease": "greasy",
    "invisible": "invisibility",
    "levitating": "levitation",
    "numbing": "numb",
    "paralyze": "paralysis",
    "paralyzed": "paralysis",
    "poisoned": "poison",
    "polymorphed": "polymorph",
    "root": "rooted",
    "roots": "rooted",
    "slowed": "slow",
    "strangled": "strangulation",
    "web": "webbed",
}
CANONICAL_SPANISH = {
    "bleeding": "sangrado",
    "blindness": "ceguera",
    "burning": "quemadura",
    "confusion": "confusión",
    "cowardice": "cobardía",
    "disarm": "desarme",
    "drunk": "ebriedad",
    "evasion": "evasión",
    "free action": "acción libre",
    "greasy": "grasiento",
    "incoherence": "incoherencia",
    "invisibility": "invisibilidad",
    "knockback": "empuje",
    "levitation": "levitación",
    "magic reflection": "reflejo mágico",
    "nausea resistance": "resistencia a náuseas",
    "numb": "adormecimiento",
    "paralysis": "parálisis",
    "poison": "veneno",
    "polymorph": "polimorfia",
    "retaliation": "represalia",
    "rooted": "arraigo",
    "sex change": "cambiar sexo",
    "sleep": "sueño",
    "slow": "lentitud",
    "speed": "velocidad",
    "stability": "estabilidad",
    "strangulation": "estrangulamiento",
    "telepathy": "telepatía",
    "warning": "advertencia",
    "waterbreathing": "respiración acuática",
    "waterwalking": "paso acuático",
    "webbed": "enmarañado",
    "weakness": "debilidad",
}
SUMMONED_BASES = {
    "deep shade", "earth sprite", "fire sprite", "flame cloak",
    "flame elemental", "hologram", "light", "portal", "revenant skeleton",
    "revenant skull", "spirit weapon",
}
EFFECT_BASES = set(CANONICAL_SPANISH) | set(STATUS_ALIASES) | SUMMONED_BASES
NON_PLURAL_WORDS = {
    "anonymous", "boisterous", "bonus", "cautious", "curious", "dangerous",
    "devious", "famous", "generous", "hideous", "jealous", "nervous",
    "obvious", "previous", "righteous", "serious", "various",
}
IRREGULAR_SINGULARS = {
    "axes": "axe",
    "bonuses": "bonus",
    "classes": "class",
    "goatmen": "goatman",
    "incubi": "incubus",
    "knives": "knife",
    "leaves": "leaf",
    "lives": "life",
    "selves": "self",
    "staves": "staff",
    "staffs": "staff",
    "succubi": "succubus",
    "teeth": "tooth",
    "thieves": "thief",
}

@dataclass
class Stats:
    files_processed: int = 0
    candidates: int = 0
    ids_discarded: int = 0
    dialogue_discarded: int = 0
    length_discarded: int = 0
    numeric_discarded: int = 0
    fragment_discarded: int = 0
    universal_discarded: int = 0
    domain_discarded: int = 0
    empty_discarded: int = 0
    effects_condensed: int = 0
    plurals_merged: int = 0
    duplicates: int = 0
    added_translated: int = 0
    added_pending: int = 0
    incompatible_nodes: int = 0

def clean_text(text: str, is_spanish: bool = False) -> str:
    """Aplica una limpieza agresiva para extraer solo el núcleo del término."""
    text = POSSESSIVE_RE.sub(r"\1", text)
    # 1. Quitar variables de formato (%d, %s, \n)
    text = FORMAT_VARIABLE_RE.sub("", text)
    # 2. Reemplazar símbolos y puntuación por espacios
    text = SYMBOLS_RE.sub(" ", text)
    # 3. Normalizar espacios y pasar a minúsculas
    text = WHITESPACE_RE.sub(" ", text).strip().lower()
    
    # 4. Eliminar artículos iniciales según el idioma
    if is_spanish:
        text = ES_ARTICLES_RE.sub("", text)
    else:
        text = EN_ARTICLES_RE.sub("", text)
        
    return text.strip()

def normalize_status(term: str) -> str:
    """Convierte variantes de un estado al nombre base del termbase."""
    return STATUS_ALIASES.get(term, term)

def singularize_word(word: str) -> str:
    """Reduce plurales ingleses comunes al singular para evitar duplicados."""
    if word in PROTECTED_ACRONYMS:
        return word
    if word in NON_PLURAL_WORDS:
        return word
    if word in IRREGULAR_SINGULARS:
        return IRREGULAR_SINGULARS[word]
    if len(word) <= 3 or not word.endswith("s") or word.endswith("ss"):
        return word
    if word.endswith("ies") and len(word) > 4:
        return f"{word[:-3]}y"
    if word.endswith("ves") and len(word) > 4:
        if word[:-3].endswith("i"):
            return f"{word[:-3]}fe"
        return f"{word[:-3]}f"
    if word.endswith(("ches", "shes", "sses", "xes", "zes", "oes")):
        return word[:-2]
    return word[:-1]

def singularize_term(term: str) -> str:
    words = term.split()
    if not words:
        return term

    return " ".join(singularize_word(word) for word in words)

def has_numeric_or_format_noise(original_text: str) -> bool:
    """Descarta placeholders, porcentajes y cualquier texto con digitos."""
    return "%" in original_text or DIGIT_RE.search(original_text) is not None

def has_math_variable_noise(term: str) -> bool:
    words = term.split()
    return any(word in MATH_VARIABLE_TOKENS for word in words)

def strip_effect_spanish(spanish: str) -> str:
    return ES_EFFECT_PREFIX_RE.sub("", spanish, count=1).strip()

def first_effect_base(remainder: str) -> str | None:
    words = [word for word in remainder.split() if word not in {"a", "an", "the"}]
    for size in range(min(3, len(words)), 0, -1):
        candidate = normalize_status(" ".join(words[:size]))
        if candidate in EFFECT_BASES:
            return candidate
    return None

def normalize_effect_term(english: str, spanish: str) -> tuple[str, str, bool]:
    """Condensa frases tipo 'inflicts burning' al estado o efecto base."""
    if not EFFECT_PREFIX_RE.match(english):
        return english, spanish, False

    remainder = EFFECT_PREFIX_RE.sub("", english, count=1).strip()
    effect_base = first_effect_base(remainder)
    if effect_base:
        return effect_base, CANONICAL_SPANISH.get(effect_base, strip_effect_spanish(spanish)), True

    spanish_base = strip_effect_spanish(spanish)
    if remainder in ALLOWED_EXACT_TERMS or remainder in SUMMONED_BASES:
        return remainder, spanish_base, True

    return english, spanish, False

def is_allowed_of_phrase(words: list[str]) -> bool:
    return len(words) >= 3 and words[0] in ALLOWED_OF_PREFIXES and words[1] == "of"

def is_list_fragment(words: list[str]) -> bool:
    if is_allowed_of_phrase(words):
        return False

    material_count = sum(word in MATERIAL_WORDS for word in words)
    equipment_count = sum(word in EQUIPMENT_LIST_WORDS for word in words)
    creature_count = sum(word in CREATURE_LIST_WORDS for word in words)
    if len(words) > 2 and material_count > 1:
        return True
    if equipment_count > 1:
        return True
    return creature_count > 1

def is_fragment(term: str) -> bool:
    words = term.split()
    if not words:
        return True
    if EFFECT_PREFIX_RE.match(term):
        return True
    if words[-1] in TRAILING_FRAGMENT_WORDS:
        return True
    if len(words) == 1:
        return False
    if words[0] in FRAGMENT_START_WORDS:
        return True
    if any(word in INTERNAL_AUXILIARY_WORDS for word in words):
        return True
    if any(word in INTERNAL_VERB_WORDS for word in words):
        return True
    if any(word in FRAGMENT_PRONOUNS for word in words):
        return True
    if is_list_fragment(words):
        return True
    if any(word in MID_FRAGMENT_PREPOSITIONS for word in words) and not is_allowed_of_phrase(words):
        return True
    if "and" in words or "or" in words:
        return True
    return False

def is_universal_term(term: str) -> bool:
    words = term.split()
    return len(words) == 1 and words[0] in UNIVERSAL_SINGLE_WORDS

def is_domain_term(term: str) -> bool:
    words = term.split()
    if not words:
        return False
    if len(words) == 1:
        return True
    if term in ALLOWED_EXACT_TERMS or is_allowed_of_phrase(words):
        return True
    if words[-1] in DOMAIN_SUFFIXES:
        return True
    return any(word in DOMAIN_KEYWORDS for word in words)

def prepare_term(english: str, spanish: str) -> tuple[str, str, str | None, bool, bool]:
    """Normaliza un candidato y devuelve el motivo si debe descartarse."""
    if has_numeric_or_format_noise(english):
        return "", "", "numeric", False, False

    clean_english = clean_text(english, is_spanish=False)
    clean_spanish = clean_text(spanish, is_spanish=True)

    if not clean_english or not clean_spanish:
        return "", "", "empty", False, False

    clean_english, clean_spanish, condensed_effect = normalize_effect_term(
        clean_english, clean_spanish
    )
    clean_english = normalize_status(clean_english)
    if clean_english in CANONICAL_SPANISH:
        clean_spanish = CANONICAL_SPANISH[clean_english]

    if has_math_variable_noise(clean_english):
        return "", "", "numeric", condensed_effect, False

    singular_english = singularize_term(clean_english)
    plural_merged = singular_english != clean_english
    clean_english = singular_english

    word_count = len(clean_english.split())
    if not 1 <= word_count <= 4:
        return "", "", "length", condensed_effect, plural_merged

    if is_fragment(clean_english):
        return "", "", "fragment", condensed_effect, plural_merged

    if is_universal_term(clean_english):
        return "", "", "universal", condensed_effect, plural_merged

    if not is_domain_term(clean_english):
        return "", "", "domain", condensed_effect, plural_merged

    return clean_english, clean_spanish, None, condensed_effect, plural_merged

def is_dialogue_or_sentence(original_text: str) -> bool:
    """Filtra frases que claramente son diálogos u oraciones descriptivas."""
    text_lower = original_text.lower()
    dialogue_markers = ["!", "?", "...", "i'll", "i'm", "don't", "there's", "this is", "let's"]
    if any(marker in text_lower for marker in dialogue_markers):
        return True
    
    # Si termina en un punto final (y no es un número/acrónimo), suele ser una oración
    if original_text.strip().endswith(".") and len(original_text.split()) > 2:
        return True
        
    return False

def load_base_glossary(path: Path) -> dict[str, str]:
    """Lee la base; la primera definición de cada término siempre prevalece."""
    glossary: dict[str, str] = {}

    if not path.is_file():
        # Si no existe, no rompemos el script, solo empezamos con uno vacío
        print(f"No se encontró glosario base en {path}. Se creará uno nuevo.")
        return glossary

    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8-sig").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            fields = next(csv.reader([line], delimiter=";"))
        except csv.Error as error:
            print(f"Advertencia: se omitió {path.name}:{line_number} ({error}).")
            continue
        if len(fields) != 2:
            continue

        english, spanish = (part.strip() for part in fields)
        normalized_english, normalized_spanish, reason, _, _ = prepare_term(
            english, spanish
        )
        if reason:
            continue

        glossary.setdefault(normalized_english, normalized_spanish)

    return glossary

def normalized_relative_path(file_path: Path, root: Path, suffix: str) -> Path:
    """Quita el sufijo de idioma del nombre y conserva la ruta relativa."""
    relative = file_path.relative_to(root)
    stem = relative.stem
    if suffix and stem.endswith(suffix):
        stem = stem[: -len(suffix)]
    return relative.with_name(f"{stem}{relative.suffix}")

def index_json_files(root: Path, suffix: str) -> dict[Path, Path]:
    """Indexa recursivamente los JSON por su ruta sin sufijo de idioma."""
    index: dict[Path, Path] = {}
    for file_path in sorted(root.rglob("*.json")):
        key = normalized_relative_path(file_path, root, suffix)
        index[key] = file_path
    return index

def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as file:
        return json.load(file)

def map_keys(source: dict[Any, Any], target: dict[Any, Any]) -> dict[Any, Any]:
    """Relaciona claves aunque las etiquetas visibles hayan sido traducidas."""
    mapping: dict[Any, Any] = {}
    unused_target_keys = list(target)

    for source_key in source:
        if source_key in target:
            mapping[source_key] = source_key
            unused_target_keys.remove(source_key)

    for source_key in source:
        if source_key in mapping:
            continue
        equal_value_keys = [
            target_key for target_key in unused_target_keys
            if source[source_key] == target[target_key]
        ]
        if len(equal_value_keys) == 1:
            target_key = equal_value_keys[0]
            mapping[source_key] = target_key
            unused_target_keys.remove(target_key)

    remaining_source_keys = [key for key in source if key not in mapping]
    for source_key, target_key in zip(remaining_source_keys, unused_target_keys):
        mapping[source_key] = target_key

    return mapping

def add_term(
    english: str,
    spanish: str,
    polish: str,
    glossary: dict[str, str],
    stats: Stats,
) -> None:
    """Aplica los filtros estrictos y agrega un término si es nuevo."""
    stats.candidates += 1

    # Filtro de Polaco (Evita IDs)
    if english == polish:
        stats.ids_discarded += 1
        return

    # Bloqueador de diálogos (Exclamaciones, oraciones largas)
    if is_dialogue_or_sentence(english):
        stats.dialogue_discarded += 1
        return

    clean_english, clean_spanish, reason, condensed_effect, plural_merged = prepare_term(
        english, spanish
    )
    if condensed_effect:
        stats.effects_condensed += 1
    if plural_merged:
        stats.plurals_merged += 1

    if reason == "empty":
        stats.empty_discarded += 1
        return
    if reason == "numeric":
        stats.numeric_discarded += 1
        return
    if reason == "length":
        stats.length_discarded += 1
        return
    if reason == "fragment":
        stats.fragment_discarded += 1
        return
    if reason == "universal":
        stats.universal_discarded += 1
        return
    if reason == "domain":
        stats.domain_discarded += 1
        return

    if clean_english in glossary:
        if clean_english in PLURAL_DERIVED_TERMS and not plural_merged:
            glossary[clean_english] = (
                "[PENDIENTE]" if english == spanish else clean_spanish
            )
            PLURAL_DERIVED_TERMS.discard(clean_english)
            if english == spanish:
                stats.added_pending += 1
            else:
                stats.added_translated += 1
            return

        stats.duplicates += 1
        return

    # Si la versión original (inglés) y tu traducción (español) son idénticas, falta traducir
    if english == spanish:
        glossary[clean_english] = "[PENDIENTE]"
        stats.added_pending += 1
    else:
        glossary[clean_english] = clean_spanish
        stats.added_translated += 1
    if plural_merged:
        PLURAL_DERIVED_TERMS.add(clean_english)

def extract_terms(
    english: Any,
    spanish: Any,
    polish: Any,
    glossary: dict[str, str],
    stats: Stats,
) -> None:
    """Recorre simultáneamente tres árboles JSON, incluyendo claves de texto."""
    if isinstance(english, dict):
        if not isinstance(spanish, dict) or not isinstance(polish, dict):
            stats.incompatible_nodes += 1
            return

        spanish_keys = map_keys(english, spanish)
        polish_keys = map_keys(english, polish)
        for english_key in english:
            if english_key not in spanish_keys or english_key not in polish_keys:
                stats.incompatible_nodes += 1
                continue

            spanish_key = spanish_keys[english_key]
            polish_key = polish_keys[english_key]
            if all(isinstance(key, str) for key in (english_key, spanish_key, polish_key)):
                add_term(english_key, spanish_key, polish_key, glossary, stats)

            extract_terms(
                english[english_key],
                spanish[spanish_key],
                polish[polish_key],
                glossary,
                stats,
            )
        return

    if isinstance(english, list):
        if not isinstance(spanish, list) or not isinstance(polish, list):
            stats.incompatible_nodes += 1
            return
        for english_item, spanish_item, polish_item in zip(english, spanish, polish):
            extract_terms(english_item, spanish_item, polish_item, glossary, stats)
        return

    if all(isinstance(value, str) for value in (english, spanish, polish)):
        add_term(english, spanish, polish, glossary, stats)
    elif type(english) is not type(spanish) or type(english) is not type(polish):
        stats.incompatible_nodes += 1

def write_glossary(path: Path, glossary: dict[str, str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file, delimiter=";", lineterminator="\n")
        for english in sorted(glossary, key=str.casefold):
            writer.writerow((english, glossary[english]))

def main() -> None:
    PLURAL_DERIVED_TERMS.clear()
    glossary = load_base_glossary(BASE_GLOSSARY)
    base_term_count = len(glossary)
    stats = Stats()

    english_files = index_json_files(ENGLISH_DIR, "_en")
    spanish_files = index_json_files(SPANISH_DIR, "")
    polish_files = index_json_files(POLISH_DIR, "_pl")
    common_paths = sorted(english_files.keys() & spanish_files.keys() & polish_files.keys())

    for relative_path in common_paths:
        try:
            english = load_json(english_files[relative_path])
            spanish = load_json(spanish_files[relative_path])
            polish = load_json(polish_files[relative_path])
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            print(f"Error al leer {relative_path}: {error}")
            continue

        extract_terms(english, spanish, polish, glossary, stats)
        stats.files_processed += 1

    write_glossary(OUTPUT_GLOSSARY, glossary)

    print(f"\n========================================")
    print(f"📊 REPORTE DE CREACIÓN DE GLOSARIO 📊")
    print(f"========================================")
    print(f"Archivos JSON comparados  : {stats.files_processed}")
    print(f"Términos del glosario base: {base_term_count}")
    print(f"Nuevos términos agregados : {stats.added_translated}")
    print(f"Nuevos [PENDIENTE] añadidos: {stats.added_pending}")
    print(f"----------------------------------------")
    print(f"Filtros de Limpieza (Descartados):")
    print(f"- Eran IDs / Códigos      : {stats.ids_discarded}")
    print(f"- Eran Diálogos/Oraciones : {stats.dialogue_discarded}")
    print(f"- Números/variables       : {stats.numeric_discarded}")
    print(f"- Fragmentos gramaticales : {stats.fragment_discarded}")
    print(f"- Vocabulario universal   : {stats.universal_discarded}")
    print(f"- Fuera del dominio       : {stats.domain_discarded}")
    print(f"- Vacíos tras limpiar     : {stats.empty_discarded}")
    print(f"- Excedían las 4 palabras : {stats.length_discarded}")
    print(f"- Ya existían (Duplicados): {stats.duplicates}")
    print(f"----------------------------------------")
    print(f"Efectos condensados       : {stats.effects_condensed}")
    print(f"Plurales unificados       : {stats.plurals_merged}")
    if stats.incompatible_nodes:
        print(f"Nodos incompatibles omitidos: {stats.incompatible_nodes}")
    print(f"========================================\n")
    print(f"✅ Glosario generado con éxito en: {OUTPUT_GLOSSARY.name}\n")

if __name__ == "__main__":
    main()
