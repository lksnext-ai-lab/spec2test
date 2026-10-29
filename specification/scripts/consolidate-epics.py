#!/usr/bin/env python3
"""Consolida las epicas configuradas en un unico documento Markdown."""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import project_config as pc  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_NAME = "epics-consolidated.md"
MESSAGES = {
    "es": {
        "title": "# Documento consolidado de épicas",
        "note": "_Este documento se genera automáticamente a partir de las épicas de la ruta configurada._",
        "updated": "**Última actualización:**",
        "toc": "## Tabla de contenidos",
        "written": "Consolidado actualizado: {path}",
        "unchanged": "Consolidado sin cambios: {path}",
        "stale": "Consolidado desactualizado: {path}. Ejecuta consolidate-epics.py",
        "empty": "Sin épicas que consolidar; {path} no es necesario",
    },
    "en": {
        "title": "# Consolidated epics document",
        "note": "_This document is generated automatically from the epics in the configured path._",
        "updated": "**Last updated:**",
        "toc": "## Table of contents",
        "written": "Consolidated document updated: {path}",
        "unchanged": "Consolidated document unchanged: {path}",
        "stale": "Consolidated document out of date: {path}. Run consolidate-epics.py",
        "empty": "No epics to consolidate; {path} is not required",
    },
}


def slug(text):
    normalized = unicodedata.normalize("NFD", text)
    value = "".join(char for char in normalized if unicodedata.category(char) != "Mn").lower()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9\s-]", "", value).replace(" ", "-")).strip("-")


def epic_files(epics_root, config=None):
    # Listado y orden compartidos con idx.py (project_config.epic_files).
    return pc.epic_files(epics_root, config)


def rewrite_feature_index_item(line, feature_slugs, linked_feature, plain_feature, prefix):
    linked_match = linked_feature.match(line)
    if linked_match:
        feature_id, title = linked_match.groups()
    else:
        plain_match = plain_feature.match(line)
        if not plain_match:
            return line
        feature_id, title = plain_match.group(1), line[plain_match.end():]
    if feature_id not in feature_slugs:
        return line
    anchor, _ = feature_slugs[feature_id]
    return f"- [{prefix}-{feature_id}: {title.strip()}](#{anchor})"


def rewrite_feature_index(lines, feature_slugs, ids):
    prefix = re.escape(ids.feature_prefix)
    linked_feature = re.compile(rf"^\s*-\s*\[{prefix}[-\s]+(\d+-\d+): ([^\]]+)\]\(#.*\)", re.IGNORECASE)
    plain_feature = re.compile(rf"^\s*-\s*{prefix}[-\s]+(\d+-\d+):", re.IGNORECASE)
    for index, line in enumerate(lines):
        # Acepta "Feature Index", "Indice de features" e "Índice de Features".
        if not pc.FEATURE_INDEX_HEADING.match(line):
            continue
        item = index + 1
        while item < len(lines) and (not lines[item].strip() or lines[item].lstrip().startswith("-")):
            if lines[item].strip():
                lines[item] = rewrite_feature_index_item(
                    lines[item], feature_slugs, linked_feature, plain_feature, ids.feature_prefix
                )
            item += 1


def render_epic(lines, used_slugs, entries, ids=None):
    ids = ids or pc.identifiers()
    title = re.sub(r"^#\s+", "", lines[0]).strip()
    base = slug(title)
    count = used_slugs.get(base, -1) + 1
    used_slugs[base] = count
    anchor = base if count == 0 else f"{base}-{count}"
    entries.append((title, anchor))

    feature_heading = re.compile(rf"^##\s*{re.escape(ids.feature_prefix)}[-\s]+(\d+-\d+):\s*(.*)", re.IGNORECASE)
    feature_slugs = {}
    for number, line in enumerate(lines):
        match = feature_heading.match(line)
        if match:
            feature_id, feature_title = match.groups()
            feature_slugs[feature_id] = (slug(f"{ids.feature_prefix} {feature_id}: {feature_title.strip()}"), number)
    rewrite_feature_index(lines, feature_slugs, ids)
    # Siempre "\n": no se mezcla os.linesep con LF.
    lines[0] = f'<a id="{anchor}"></a>\n# {title}'
    for feature_id, (feature_anchor, number) in feature_slugs.items():
        feature_title = lines[number].split(":", 1)[1].strip()
        lines[number] = f'<a id="{feature_anchor}"></a>\n## {ids.feature_prefix}-{feature_id}: {feature_title}'
    return "\n".join(line.rstrip() for line in lines)


def default_output(config):
    requirements = pc.requirements_root(ROOT, config)
    if not requirements.is_dir():
        # Sin raiz de requisitos no se adivina otra ubicacion para el consolidado.
        raise SystemExit(
            f"No existe la raiz de requisitos configurada ({requirements}). "
            "Crea la raiz configurada en .project.yml o indica el archivo de salida con --output"
        )
    return pc.epics_root(ROOT, config) / OUTPUT_NAME


def without_timestamp(content, text):
    return [line for line in content.splitlines() if not line.startswith(text["updated"])]


def consolidate(config, output=None, epics_root=None, check=False):
    text = MESSAGES[pc.language(config) or "es"]
    ids = pc.identifiers(config)
    epics_root = epics_root or pc.epics_root(ROOT, config)
    output = output or default_output(config)
    entries = []
    used_slugs = {}
    rendered = []
    for path in epic_files(epics_root, config):
        lines = pc.read_text(path).splitlines()
        if not lines:
            continue
        if not re.match(r"^#\s+", lines[0]):
            rendered.append("\n".join(line.rstrip() for line in lines))
            continue
        rendered.append(render_epic(lines, used_slugs, entries, ids))

    output_lines = [
        text["title"],
        text["note"],
        "",
        f"{text['updated']} {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        text["toc"],
        "",
        *[f"- [{title}](#{anchor})" for title, anchor in entries],
        "",
        "---",
        "",
    ]
    for epic in rendered:
        output_lines.extend([epic.rstrip(), "", "---", ""])
    content = "\n".join(output_lines).rstrip("\n") + "\n"
    if check and not entries and not rendered and not output.exists():
        # Destino recien instalado: sin epicas no hay nada que consolidar ni versionar.
        print(text["empty"].format(path=output))
        return 0
    # Sin cambios en las epicas no se reescribe: la fecha no genera diffs y
    # --check puede comparar el consolidado versionado sin escribirlo.
    if output.is_file() and without_timestamp(pc.read_text(output), text) == without_timestamp(content, text):
        print(text["unchanged"].format(path=output))
        return 0
    if check:
        print(text["stale"].format(path=output), file=sys.stderr)
        return 1
    output.parent.mkdir(parents=True, exist_ok=True)
    # UTF-8 sin BOM y LF, como el resto de scripts.
    output.write_text(content, encoding="utf-8", newline="\n")
    print(text["written"].format(path=output))
    return 0


def main(argv=None):
    pc.configure_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        help=f"Archivo de salida (por defecto <paths.epics>/{OUTPUT_NAME} bajo la raiz de requisitos)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="No escribe; falla si el consolidado no esta al dia (ignora solo la fecha)",
    )
    args = parser.parse_args(argv)
    try:
        config = pc.load_config(ROOT)
        pc.validate_contained_paths(config)
        pc.identifiers(config)
    except pc.ConfigError as error:
        raise SystemExit(f"Configuracion no valida: {error}") from error
    return consolidate(config, args.output.resolve() if args.output else None, check=args.check)


if __name__ == "__main__":
    sys.exit(main())
