#!/usr/bin/env python3
"""Lectura unica de .project.yml y del frontmatter YAML, sin dependencias externas.

Admite el subconjunto YAML que usa el template: mapas indentados con espacios,
escalares sin comillas o con comillas simples/dobles, comentarios, listas
inline (``[a, "b"]``), mapas inline vacios o simples (``{}``, ``{a: 1}``) y
listas de guiones (de escalares o de mapas). En el frontmatter tambien se
admiten los bloques ``|`` y ``>`` (con chomping ``-``/``+``); en ``.project.yml``
se rechazan. Cualquier otra construccion (tabuladores, anclas, claves
complejas) produce ``ConfigError`` con el numero de linea en lugar de
interpretarse a medias.
"""
from __future__ import annotations

import json
import os
import re
import stat
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath

MINIMUM_PYTHON = (3, 9)
if sys.version_info < MINIMUM_PYTHON:
    raise SystemExit("ProjectTraceKit requiere Python 3.9 o superior")

POWERSHELL_EXTENSIONS = frozenset({".ps1", ".psm1", ".psd1", ".ps1xml"})
UNRESOLVED_VALUES = frozenset({"", "pending", "[CONFIGURAR]", "[PENDIENTE]"})
GENERATED_REQUIREMENTS_FILES = frozenset({"epics-consolidated.md"})
NON_EPIC_FILES = frozenset({"readme.md", "index.md", *GENERATED_REQUIREMENTS_FILES})

# Tabla unica de valores por defecto. Todas las herramientas la usan.
DEFAULTS = {
    "project.language": "es",
    "requirements.mode": "same_repository",
    "requirements.local_root": ".",
    "requirements.repository.local_path": ".",
    "paths.requirements": ".",
    "paths.sources": "sources",
    "paths.epics": "epics",
    "paths.templates": "templates",
    "paths.decisions": "decisions",
    "paths.requirement_sources": "requirement-sources",
    "paths.domain_model": "domain-model.md",
    "paths.glossary": "domain-model/glossary.md",
    "paths.requirements_index": "epics/index.md",
    "paths.traceability_matrix": "traceability-matrix.md",
    "paths.plans": "plans",
    "paths.tasks": "tasks",
    "identifiers.epic.prefix": "EPIC",
    "identifiers.feature.prefix": "FEAT",
    "identifiers.scenario.prefix": "ESC",
    "validation.unresolved_marker": "[CONFIGURAR]",
}

# Prefijos de identificador: una palabra sin guiones (el guion separa los numeros).
_IDENTIFIER_PREFIX = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")

# Rutas que se unen a una raiz: nunca pueden ser absolutas ni contener "..".
CONTAINED_PATH_KEYS = (
    "requirements.local_root",
    "paths.requirements",
    "paths.sources",
    "paths.epics",
    "paths.templates",
    "paths.decisions",
    "paths.requirement_sources",
    "paths.domain_model",
    "paths.glossary",
    "paths.requirements_index",
    "paths.traceability_matrix",
    "paths.plans",
    "paths.tasks",
    "integrations.codebase_memory.evidence_path",
)

# Carpeta del paquete locale -> clave paths.* que la reubica.
REQUIREMENTS_FOLDER_KEYS = {
    "sources": "paths.sources",
    "epics": "paths.epics",
    "templates": "paths.templates",
    "decisions": "paths.decisions",
    "requirement-sources": "paths.requirement_sources",
}


class ConfigError(ValueError):
    """Configuracion o frontmatter con una estructura no soportada."""


def configure_stdio() -> None:
    """Fuerza UTF-8 en stdout/stderr para que la salida JSON no falle en cp1252."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except (ValueError, OSError):
                pass


# --------------------------------------------------------------------------
# Parser YAML-subset
# --------------------------------------------------------------------------

_KEY_PATTERN = re.compile(r"^([A-Za-z_][A-Za-z0-9_.-]*|\"[^\"]+\"|'[^']+')\s*:(?:\s+|$)(.*)$")
_INT_PATTERN = re.compile(r"^[-+]?\d+$")


def _strip_comment(text: str) -> str:
    """Elimina un comentario final respetando las comillas."""
    quote = None
    index = 0
    while index < len(text):
        char = text[index]
        if quote:
            if char == "\\" and quote == '"':
                index += 2
                continue
            if char == quote:
                if quote == "'" and text[index + 1:index + 2] == "'":
                    index += 2
                    continue
                quote = None
        elif char in "\"'" and (index == 0 or text[index - 1] in " \t[{,:"):
            quote = char
        elif char == "#" and (index == 0 or text[index - 1] in " \t"):
            return text[:index].rstrip()
        index += 1
    return text.rstrip()


def _split_flow(text: str, line_number: int) -> list[str]:
    items: list[str] = []
    depth = 0
    quote = None
    current = ""
    index = 0
    while index < len(text):
        char = text[index]
        if quote:
            current += char
            if char == "\\" and quote == '"' and index + 1 < len(text):
                current += text[index + 1]
                index += 2
                continue
            if char == quote:
                quote = None
        elif char in "\"'":
            quote = char
            current += char
        elif char in "[{":
            depth += 1
            current += char
        elif char in "]}":
            depth -= 1
            current += char
        elif char == "," and depth == 0:
            items.append(current.strip())
            current = ""
        else:
            current += char
        index += 1
    if quote or depth:
        raise ConfigError(f"Linea {line_number}: coleccion inline sin cerrar")
    if current.strip():
        items.append(current.strip())
    elif items:
        raise ConfigError(f"Linea {line_number}: elemento vacio en coleccion inline")
    return items


def parse_scalar(text: str, line_number: int = 0):
    """Convierte un escalar YAML del subconjunto soportado."""
    value = text.strip()
    if not value:
        return None
    if value.startswith('"'):
        if len(value) < 2 or not value.endswith('"'):
            raise ConfigError(f"Linea {line_number}: cadena con comillas dobles sin cerrar")
        try:
            return json.loads(value)
        except json.JSONDecodeError as error:
            raise ConfigError(f"Linea {line_number}: escape no valido en cadena: {error.msg}") from error
    if value.startswith("'"):
        if len(value) < 2 or not value.endswith("'"):
            raise ConfigError(f"Linea {line_number}: cadena con comillas simples sin cerrar")
        return value[1:-1].replace("''", "'")
    if value.startswith("["):
        if not value.endswith("]"):
            raise ConfigError(f"Linea {line_number}: lista inline sin cerrar")
        return [parse_scalar(item, line_number) for item in _split_flow(value[1:-1], line_number)]
    if value.startswith("{"):
        if not value.endswith("}"):
            raise ConfigError(f"Linea {line_number}: mapa inline sin cerrar")
        result = {}
        for item in _split_flow(value[1:-1], line_number):
            match = _KEY_PATTERN.match(item)
            if not match:
                raise ConfigError(f"Linea {line_number}: entrada no valida en mapa inline: {item}")
            result[_unquote_key(match.group(1))] = parse_scalar(match.group(2), line_number)
        return result
    if value[0] in "&*!|>%@`":
        raise ConfigError(f"Linea {line_number}: construccion YAML no soportada: {value[:20]}")
    if re.search(r":(?:\s|$)", value):
        raise ConfigError(
            f"Linea {line_number}: un escalar sin comillas no puede contener ': '; usa comillas"
        )
    lowered = value.casefold()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "~"}:
        return None
    if _INT_PATTERN.match(value):
        return int(value)
    return value


def _unquote_key(key: str) -> str:
    return key[1:-1] if key[:1] in "\"'" else key


_BLOCK_HEADER = re.compile(r"^([|>])(?:([+-])([1-9])?|([1-9])([+-])?)?$")


def _block_key_column(indent: int, content: str) -> tuple[int, str]:
    """Columna de la clave y resto de la linea, saltando los guiones de lista."""
    column = indent
    rest = content.strip()
    while rest.startswith("- "):
        after = rest[2:]
        column += 2 + len(after) - len(after.lstrip(" "))
        rest = after.lstrip(" ")
    return column, rest


def _fold_block(lines: list[str]) -> str:
    """Plegado ``>``: une lineas normales con espacio; las vacias y las mas indentadas conservan el salto."""
    def normal(line: str) -> bool:
        return line != "" and not line.startswith((" ", "\t"))

    result = lines[0] if lines else ""
    for index in range(1, len(lines)):
        previous, current = lines[index - 1], lines[index]
        if normal(previous) and normal(current):
            result += " " + current
            continue
        if normal(previous) and current == "":
            following = next((line for line in lines[index:] if line != ""), "")
            if normal(following):
                # El salto tras la linea normal se descarta: cada linea vacia aporta uno.
                result += current
                continue
        result += "\n" + current
    return result


def _parse_block_scalar(header: str, body: list[str], key_column: int, number: int) -> str:
    """Contenido de un bloque ``|``/``>`` leido de las lineas originales (conserva ``#`` y lineas vacias)."""
    match = _BLOCK_HEADER.match(header)
    style = match.group(1)
    chomping = match.group(2) or match.group(5) or ""
    explicit = match.group(3) or match.group(4)
    if explicit:
        content_indent = key_column + int(explicit)
    else:
        first = next((line for line in body if line.strip()), None)
        content_indent = len(first) - len(first.lstrip(" ")) if first is not None else key_column + 1
    lines: list[str] = []
    for offset, raw in enumerate(body, 1):
        if not raw.strip():
            lines.append(raw[content_indent:] if len(raw) > content_indent else "")
            continue
        if len(raw) - len(raw.lstrip(" ")) < content_indent:
            raise ConfigError(f"Linea {number + offset}: indentacion inconsistente en el bloque '{style}'")
        lines.append(raw[content_indent:])
    trailing = 0
    while lines and lines[-1] == "":
        lines.pop()
        trailing += 1
    text = "\n".join(lines) if style == "|" else _fold_block(lines)
    if not lines:
        return "\n" * trailing if chomping == "+" else ""
    if chomping == "-":
        return text
    if chomping == "+":
        return text + "\n" + "\n" * trailing
    return text + "\n"


def parse_yaml(text: str, *, block_scalars: bool = False) -> dict:
    """Parsea el subconjunto YAML del template y devuelve un dict.

    ``block_scalars`` admite los bloques ``|``/``>`` (frontmatter de agentes y
    skills); ``.project.yml`` los rechaza para mantener un formato editable por
    el instalador linea a linea.
    """
    if text.startswith("\ufeff"):
        text = text[1:]
    raw_lines = text.splitlines()
    blocks: dict[int, str] = {}
    lines: list[tuple[int, int, str, str]] = []
    block_until = 0
    for number, raw in enumerate(raw_lines, 1):
        if number <= block_until:
            continue
        if "\t" in raw[: len(raw) - len(raw.lstrip(" \t"))]:
            raise ConfigError(f"Linea {number}: los tabuladores no se admiten para indentar")
        content = _strip_comment(raw)
        if not content.strip() or content.strip() in {"---", "..."}:
            continue
        indent = len(content) - len(content.lstrip(" "))
        lines.append((number, indent, content.strip(), raw))
        if block_scalars:
            key_column, rest = _block_key_column(indent, content)
            key_match = _KEY_PATTERN.match(rest)
            header = key_match.group(2).strip() if key_match else ""
            if key_match and _BLOCK_HEADER.match(header):
                # Las lineas del bloque se leen en crudo: vacias, con "#" o con mas indentacion.
                end = number
                while end < len(raw_lines) and (
                    not raw_lines[end].strip()
                    or len(raw_lines[end]) - len(raw_lines[end].lstrip(" ")) > key_column
                ):
                    end += 1
                while end > number and not raw_lines[end - 1].strip():
                    end -= 1
                body = raw_lines[number:end]
                # Las lineas vacias finales solo cuentan con chomping "+".
                tail = number + len(body)
                while tail < len(raw_lines) and not raw_lines[tail].strip():
                    tail += 1
                blocks[number] = _parse_block_scalar(
                    header, raw_lines[number:tail] if "+" in header else body, key_column, number
                )
                block_until = end

    position = 0

    def parse_block(indent: int, compact: bool = False):
        nonlocal position
        if position >= len(lines):
            return None
        is_list = lines[position][2].startswith("- ") or lines[position][2] == "-"
        container: dict | list = [] if is_list else {}
        while position < len(lines):
            number, current_indent, content, _ = lines[position]
            if current_indent < indent:
                break
            if current_indent > indent:
                raise ConfigError(f"Linea {number}: indentacion inesperada")
            if is_list:
                if not (content.startswith("- ") or content == "-"):
                    if compact:
                        break
                    raise ConfigError(f"Linea {number}: se esperaba un elemento de lista")
                item = content[1:].strip()
                position += 1
                if not item:
                    container.append(parse_child(number, indent))
                    continue
                key_match = _KEY_PATTERN.match(item)
                if key_match and not item.startswith(("\"", "'", "[", "{")):
                    # Elemento de lista que es un mapa: "- key: value" + claves alineadas.
                    item_indent = indent + (len(content) - len(item))
                    mapping = {}
                    _assign(mapping, key_match, number, item_indent)
                    if position < len(lines) and lines[position][1] == item_indent:
                        rest = parse_block(item_indent)
                        if not isinstance(rest, dict):
                            raise ConfigError(f"Linea {number}: mezcla de lista y mapa")
                        for key, value in rest.items():
                            if key in mapping:
                                raise ConfigError(f"Linea {number}: clave duplicada {key}")
                            mapping[key] = value
                    container.append(mapping)
                else:
                    container.append(parse_scalar(item, number))
            else:
                if content.startswith("- "):
                    raise ConfigError(f"Linea {number}: elemento de lista dentro de un mapa")
                key_match = _KEY_PATTERN.match(content)
                if not key_match:
                    raise ConfigError(f"Linea {number}: se esperaba 'clave: valor'")
                position += 1
                _assign(container, key_match, number, indent)
        return container

    def parse_child(number: int, indent: int):
        if position < len(lines) and lines[position][1] > indent:
            return parse_block(lines[position][1])
        return None

    def _assign(mapping: dict, key_match, number: int, indent: int) -> None:
        key = _unquote_key(key_match.group(1))
        if key in mapping:
            raise ConfigError(f"Linea {number}: clave duplicada {key}")
        raw_value = key_match.group(2).strip()
        if number in blocks:
            mapping[key] = blocks[number]
            return
        if re.fullmatch(r"[|>][+-]?\d?|[|>]\d[+-]?", raw_value):
            # En .project.yml los bloques no se admiten: el instalador edita la
            # configuracion linea a linea. En el frontmatter si se interpretan.
            raise ConfigError(f"Linea {number}: los bloques '|' y '>' no se admiten en {key}; usa una cadena entre comillas")
        if raw_value:
            mapping[key] = parse_scalar(raw_value, number)
            if position < len(lines) and lines[position][1] > indent:
                raise ConfigError(f"Linea {lines[position][0]}: indentacion inesperada tras {key}")
            return
        child_indent = lines[position][1] if position < len(lines) else -1
        if child_indent > indent:
            mapping[key] = parse_block(child_indent)
        elif (
            position < len(lines)
            and child_indent == indent
            and lines[position][2].startswith("- ")
        ):
            # Lista de guiones alineada con la clave padre (estilo YAML compacto).
            mapping[key] = parse_block(indent, compact=True)
        else:
            mapping[key] = None

    result = parse_block(lines[0][1]) if lines else {}
    if position < len(lines):
        raise ConfigError(f"Linea {lines[position][0]}: indentacion inconsistente")
    if not isinstance(result, dict):
        raise ConfigError("El documento YAML debe ser un mapa en la raiz")
    return result


def split_frontmatter(text: str) -> tuple[str | None, str]:
    """Devuelve (frontmatter, cuerpo). El frontmatter debe abrir en la linea 1."""
    if text.startswith("﻿"):
        text = text[1:]
    match = re.match(r"^---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|$)", text, re.DOTALL)
    if not match:
        return None, text
    return match.group(1), text[match.end():]


def parse_frontmatter(text: str) -> dict | None:
    frontmatter, _ = split_frontmatter(text)
    if frontmatter is None:
        return None
    return parse_yaml(frontmatter, block_scalars=True)


# --------------------------------------------------------------------------
# Acceso a la configuracion
# --------------------------------------------------------------------------

def read_text(path: Path) -> str:
    """Lee texto UTF-8 aceptando BOM."""
    return path.read_text(encoding="utf-8-sig")


def load_config_text(text: str) -> dict:
    return parse_yaml(text)


def load_config(root: Path) -> dict:
    path = Path(root) / ".project.yml"
    if not path.is_file():
        raise ConfigError(f"No existe {path}")
    return parse_yaml(read_text(path))


def get(config: dict, dotted: str, default=None):
    """Lee una clave por ruta (``paths.plans``). Usa DEFAULTS si falta."""
    current = config
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            return DEFAULTS.get(dotted, default) if default is None else default
        current = current[part]
    if current is None:
        return DEFAULTS.get(dotted, default) if default is None else default
    return current


def get_str(config: dict, dotted: str, default: str | None = None) -> str:
    value = get(config, dotted, default)
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def get_list(config: dict, dotted: str) -> list:
    value = get(config, dotted, [])
    if value is None:
        return []
    if not isinstance(value, list):
        raise ConfigError(f"{dotted} debe ser una lista")
    return value


def get_bool(config: dict, dotted: str):
    """Devuelve True/False, o None si falta o no es booleano."""
    value = get(config, dotted, None)
    return value if isinstance(value, bool) else None


def unresolved_markers(config: dict | None = None) -> set[str]:
    """Marcadores literales de valor sin configurar (sin "" ni "pending")."""
    markers = {value for value in UNRESOLVED_VALUES if value and value != "pending"}
    if config is not None:
        configured = get_str(config, "validation.unresolved_marker").strip()
        if configured:
            markers.add(configured)
    return markers


def is_unresolved(value, config: dict | None = None) -> bool:
    """True si el valor falta, esta vacio, es un marcador o es literalmente pending."""
    if value is None:
        return True
    text = str(value).strip()
    return not text or text in unresolved_markers(config) or text.casefold() == "pending"


def is_placeholder(value, config: dict | None = None) -> bool:
    """Como ``is_unresolved`` pero acepta el valor explicito ``pending``."""
    if value is not None and str(value).strip().casefold() == "pending":
        return False
    return is_unresolved(value, config)


def consolidate_epics_enabled(config: dict) -> bool:
    """El consolidador se instala y exige salvo que se desactive explicitamente."""
    return (
        get_bool(config, "modules.consolidate_epics") is not False
        and get_bool(config, "features.consolidate_epics.enabled") is not False
    )


class Identifiers:
    """Prefijos configurados (``identifiers.*.prefix``) y sus expresiones regulares.

    ``epic``, ``feature`` y ``scenario`` son fragmentos sin grupos ni anclas
    (``EPIC-\\d+``); ``*_numbers`` capturan cada numero por separado.
    """

    def __init__(self, epic: str = "EPIC", feature: str = "FEAT", scenario: str = "ESC") -> None:
        self.epic_prefix = epic
        self.feature_prefix = feature
        self.scenario_prefix = scenario
        e, f, s = (re.escape(value) for value in (epic, feature, scenario))
        self.epic = rf"{e}-\d+"
        self.feature = rf"{f}-\d+-\d+"
        self.scenario = rf"{s}-\d+-\d+-\d+"
        self.epic_numbers = rf"{e}-(\d+)"
        self.feature_numbers = rf"{f}-(\d+)-(\d+)"
        self.scenario_numbers = rf"{s}-(\d+)-(\d+)-(\d+)"

    def epic_id(self, number) -> str:
        return f"{self.epic_prefix}-{number}"

    def feature_id(self, epic, feature) -> str:
        return f"{self.feature_prefix}-{epic}-{feature}"

    def scenario_id(self, epic, feature, scenario) -> str:
        return f"{self.scenario_prefix}-{epic}-{feature}-{scenario}"


def identifiers(config: dict | None = None) -> Identifiers:
    """Lee ``identifiers.{epic,feature,scenario}.prefix`` (por defecto EPIC/FEAT/ESC)."""
    values = []
    for kind in ("epic", "feature", "scenario"):
        key = f"identifiers.{kind}.prefix"
        value = get_str(config or {}, key).strip()
        if not _IDENTIFIER_PREFIX.match(value):
            raise ConfigError(f"{key} debe ser una palabra alfanumerica sin guiones: {value!r}")
        values.append(value)
    if len({value.casefold() for value in values}) != len(values):
        raise ConfigError("identifiers.*.prefix deben ser distintos entre si")
    return Identifiers(*values)


# Patrones del kit que incrustan un prefijo de identificador:
# clave -> (clave del prefijo, prefijo por defecto, patron por defecto).
# identifiers.epic.file_pattern ("epic-NN-name.md") no incrusta el prefijo.
PREFIX_PATTERN_DEFAULTS = {
    "identifiers.epic.pattern": ("identifiers.epic.prefix", "EPIC", "EPIC-N"),
    "identifiers.feature.pattern": ("identifiers.feature.prefix", "FEAT", "FEAT-N-M"),
    "identifiers.scenario.pattern": ("identifiers.scenario.prefix", "ESC", "ESC-N-M-K"),
    "identifiers.task.pattern": ("identifiers.task.prefix", "TASK", "TASK-N"),
    "features.e2e.tag_pattern": ("identifiers.scenario.prefix", "ESC", "@ESC-N-M-K"),
    "github_projects.fields.Epic.pattern": ("identifiers.epic.prefix", "EPIC", "EPIC-N"),
}


def prefix_pattern(config: dict, key: str) -> str:
    """Patron efectivo de ``key``: el configurado si es propio; si falta o conserva
    el valor por defecto del kit, el derivado del prefijo configurado."""
    prefix_key, default_prefix, default_pattern = PREFIX_PATTERN_DEFAULTS[key]
    configured = get(config, key, None)
    if configured is not None and configured != default_pattern:
        return get_str(config, key)
    prefix = get_str(config, prefix_key, default_prefix).strip()
    if not _IDENTIFIER_PREFIX.match(prefix):
        return default_pattern if configured is not None else ""
    return default_pattern.replace(default_prefix, prefix, 1)


def derived_prefix_patterns(config: dict) -> dict[str, str]:
    """Claves presentes que conservan el patron por defecto aunque su prefijo cambio,
    con el valor derivado del prefijo configurado (``EPIC-N`` -> ``EP-N``)."""
    updates: dict[str, str] = {}
    for key, (_prefix_key, _default_prefix, default_pattern) in PREFIX_PATTERN_DEFAULTS.items():
        if get(config, key, None) != default_pattern:
            continue
        derived = prefix_pattern(config, key)
        if derived and derived != default_pattern:
            updates[key] = derived
    return updates


def language(config: dict) -> str:
    value = get_str(config, "project.language").strip().casefold()
    return value if value in {"es", "en"} else ""


# --------------------------------------------------------------------------
# Rutas
# --------------------------------------------------------------------------

def safe_relative(value, field: str) -> Path:
    """Valida una ruta configurada relativa y contenida."""
    if not isinstance(value, str):
        raise ConfigError(f"{field} debe ser una ruta de texto")
    text = value.strip()
    if "\x00" in text:
        raise ConfigError(f"{field} contiene caracteres NUL")
    windows = PureWindowsPath(text)
    posix = PurePosixPath(text.replace("\\", "/"))
    if (
        windows.is_absolute()
        or windows.drive
        or windows.root
        or posix.is_absolute()
        or text.startswith("~")
    ):
        raise ConfigError(f"{field} debe ser una ruta relativa sin unidad: {value}")
    if ".." in posix.parts:
        raise ConfigError(f"{field} no puede contener '..': {value}")
    return Path(*posix.parts) if posix.parts and posix.parts != (".",) else Path(".")


def validate_contained_paths(config: dict) -> None:
    for key in CONTAINED_PATH_KEYS:
        safe_relative(get_str(config, key), key)


def ensure_within(path: Path, root: Path, field: str = "ruta") -> Path:
    """Comprueba que ``path`` (resuelto) queda dentro de ``root`` (resuelto)."""
    resolved = Path(path).resolve()
    base = Path(root).resolve()
    if resolved != base and base not in resolved.parents:
        raise ConfigError(f"{field} queda fuera de la raiz permitida: {path}")
    return resolved


def requirements_relative(config: dict) -> Path:
    return safe_relative(get_str(config, "requirements.local_root"), "requirements.local_root") / safe_relative(
        get_str(config, "paths.requirements"), "paths.requirements"
    )


def requirements_file_relative(relative: Path, config: dict) -> Path:
    """Traduce una ruta del paquete locale ``requirements/`` a la configurada."""
    posix = Path(relative).as_posix()
    if posix == "epics/index.md":
        return safe_relative(get_str(config, "paths.requirements_index"), "paths.requirements_index")
    if posix == "traceability-matrix.md":
        return safe_relative(get_str(config, "paths.traceability_matrix"), "paths.traceability_matrix")
    if posix == "domain-model.md":
        return safe_relative(get_str(config, "paths.domain_model"), "paths.domain_model")
    if posix == "domain-model/glossary.md":
        return safe_relative(get_str(config, "paths.glossary"), "paths.glossary")
    parts = Path(relative).parts
    if parts and parts[0] in REQUIREMENTS_FOLDER_KEYS:
        key = REQUIREMENTS_FOLDER_KEYS[parts[0]]
        return safe_relative(get_str(config, key), key).joinpath(*parts[1:])
    return Path(relative)


def external_local_path(config: dict) -> str:
    return get_str(config, "requirements.repository.local_path").strip()


def requirements_root(root: Path, config: dict) -> Path:
    """Raiz de requisitos resuelta (mismo repositorio o repositorio externo)."""
    base = Path(root)
    if get_str(config, "requirements.mode") == "external_repository":
        base = base / external_local_path(config)
    return (base / requirements_relative(config)).resolve()


def epics_root(root: Path, config: dict) -> Path:
    return requirements_root(root, config) / requirements_file_relative(Path("epics"), config)


def display_path(path: Path, root: Path) -> str:
    """Ruta legible relativa a ``root`` incluso fuera de el o en otra unidad."""
    try:
        return Path(path).resolve().relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        try:
            return Path(os.path.relpath(Path(path).resolve(), Path(root).resolve())).as_posix()
        except ValueError:
            return Path(path).resolve().as_posix()


def non_epic_names(config: dict | None = None) -> frozenset[str]:
    """Nombres que nunca son epicas: los fijos y el indice y la matriz configurados."""
    if config is None:
        return NON_EPIC_FILES
    configured = (get_str(config, key) for key in ("paths.requirements_index", "paths.traceability_matrix"))
    return NON_EPIC_FILES | {Path(value).name.casefold() for value in configured if value}


def is_epic_file(path: Path, config: dict | None = None) -> bool:
    return (
        path.is_file()
        and path.suffix.casefold() == ".md"
        and path.name.casefold() not in non_epic_names(config)
    )


def is_hidden(path: Path) -> bool:
    """Archivo oculto: nombre con punto inicial (POSIX) o atributo oculto (Windows)."""
    if path.name.startswith("."):
        return True
    try:
        attributes = getattr(path.stat(), "st_file_attributes", 0)
    except OSError:
        return False
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_HIDDEN", 2))


def epic_number(path: Path, config: dict | None = None) -> int | None:
    """Numero de la epica leido del encabezado ``# <prefijo>-N`` de la primera linea."""
    ids = identifiers(config)
    lines = read_text(path).splitlines()
    match = re.match(rf"^#\s+{ids.epic_numbers}\b", lines[0], re.IGNORECASE) if lines else None
    return int(match.group(1)) if match else None


def epic_files(directory: Path, config: dict | None = None) -> list[Path]:
    """Epicas de ``directory`` ordenadas igual en idx.py y consolidate-epics.py.

    Excluye indice, matriz, consolidado, archivos vacios y ocultos. Orden: numero
    de epica ascendente; las epicas sin numero van al final, por nombre.
    """
    if not Path(directory).is_dir():
        return []
    files = [
        path for path in Path(directory).glob("*.md")
        if is_epic_file(path, config) and not is_hidden(path) and path.stat().st_size > 0
    ]

    def sort_key(path: Path):
        number = epic_number(path, config)
        return (number if number is not None else sys.maxsize, path.name.casefold())

    return sorted(files, key=sort_key)


# --------------------------------------------------------------------------
# Estructura de las epicas (compartida por validador, idx y consolidador)
# --------------------------------------------------------------------------

SCENARIOS_HEADING = re.compile(r"^###\s+(?:Scenarios|Escenarios)\s*$", re.IGNORECASE)
E2E_HEADING = re.compile(r"^###\s+(?:E2E Verification|Verificaci[oó]n E2E)\s*$", re.IGNORECASE)
FEATURE_INDEX_HEADING = re.compile(r"^##\s+(?:Feature Index|[IÍ]ndice de features)\s*$", re.IGNORECASE)
STATUS_LINE = re.compile(r"^\*\*(?:Status|Estado):\*\*\s*(.+?)\s*$")
PRIORITY_LINE = re.compile(r"^\*\*(?:Priority|Prioridad):\*\*\s*(.+?)\s*$")


def split_table_row(line: str) -> list[str]:
    """Parte una fila Markdown respetando ``\\|``."""
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|") and not stripped.endswith("\\|"):
        stripped = stripped[:-1]
    return [cell.strip().replace("\\|", "|") for cell in re.split(r"(?<!\\)\|", stripped)]
