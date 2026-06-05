#!/usr/bin/env python3
"""Generate NER configuration artifacts from data/banks/ schemas.

Reads:
  config/entity_meta.json          — manual metadata (label, color, prompt_ru, …)
  data/banks/<BANK>/<КОД>.csv      — DB field schemas per entity per bank
  data/banks/<BANK>/vocab/<КОД>.csv — vocabulary reference files

Writes:
  config/entities.json             — full NER entity config (runtime + manual editing)
  config/label_studio_config.xml   — Label Studio labeling interface XML
  config/entity_schema.json        — JSON Schema for entity object validation
  config/banks/<BANK>/vocab_index.json — per-bank vocabulary index

Usage:
  python scripts/generate_input_schemas.py [--xml] [--schema] [--prompt] [--dry-run]
  (no flags = generate all)
"""
import csv
import json
import argparse
from pathlib import Path

ROOT = Path(__file__).parent.parent
META_PATH = ROOT / "config" / "entity_meta.json"
BANKS_DIR = ROOT / "data" / "banks"
OUT_ENTITIES = ROOT / "config" / "entities.json"
OUT_XML = ROOT / "config" / "label_studio_config.xml"
OUT_SCHEMA = ROOT / "config" / "entity_schema.json"
OUT_BANKS_DIR = ROOT / "config" / "banks"

# Expected CSV column names (case-insensitive fallback)
FIELD_NAME_COLS = ("field_name", "column_name", "name", "поле", "колонка")
DATA_TYPE_COLS = ("data_type", "type", "тип")
DESC_COLS = ("description", "desc", "описание", "comment")
VOCAB_VALUE_COLS = ("value", "значение", "name", "имя")


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_meta() -> dict:
    """Return {code_or_label: {label, name_ru, prompt_ru, color, regex_group, fields}}."""
    with open(META_PATH, encoding="utf-8") as f:
        return json.load(f)


def _find_col(header: list[str], candidates: tuple) -> int | None:
    lower = [h.lower().strip() for h in header]
    for c in candidates:
        if c in lower:
            return lower.index(c)
    return None


def read_schema_csv(path: Path) -> list[dict]:
    """Read a schema CSV -> list of {name, data_type, description}."""
    fields = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if not header:
            return fields
        fi = _find_col(header, FIELD_NAME_COLS)
        ti = _find_col(header, DATA_TYPE_COLS)
        di = _find_col(header, DESC_COLS)
        if fi is None:
            return fields
        for row in reader:
            if not row or not row[fi].strip():
                continue
            fields.append({
                "name": row[fi].strip().upper(),
                "data_type": row[ti].strip() if ti is not None and ti < len(row) else None,
                "description": row[di].strip() if di is not None and di < len(row) else None,
            })
    return fields


def read_vocab_csv(path: Path) -> int:
    """Return row count of a vocab CSV (excluding header)."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        next(reader, None)
        return sum(1 for row in reader if any(cell.strip() for cell in row))


def resolve_label(code: str, meta: dict) -> tuple[str, dict | None]:
    """Map a CSV filename code to a label and its meta entry."""
    if code in meta:
        return meta[code]["label"], meta[code]
    # Try Latin codes used directly (PER, ORG, ES, …)
    upper = code.upper()
    for key, entry in meta.items():
        if entry["label"] == upper:
            return upper, entry
    # Fallback: treat code itself as label (no meta)
    return upper, None


# ---------------------------------------------------------------------------
# Scanners
# ---------------------------------------------------------------------------

def scan_banks() -> list[str]:
    if not BANKS_DIR.exists():
        return []
    return sorted(
        d.name for d in BANKS_DIR.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )


def scan_schemas(bank: str, meta: dict) -> dict[str, list[dict]]:
    """label -> list of field dicts."""
    result: dict[str, list[dict]] = {}
    bank_dir = BANKS_DIR / bank
    for csv_file in sorted(bank_dir.glob("*.csv")):
        code = csv_file.stem
        label, _ = resolve_label(code, meta)
        result[label] = read_schema_csv(csv_file)
    return result


def scan_vocab(bank: str, meta: dict) -> dict[str, dict]:
    """label -> {path, count}."""
    result: dict[str, dict] = {}
    vocab_dir = BANKS_DIR / bank / "vocab"
    if not vocab_dir.exists():
        return result
    for csv_file in sorted(vocab_dir.glob("*.csv")):
        code = csv_file.stem
        label, _ = resolve_label(code, meta)
        result[label] = {
            "path": str(csv_file.relative_to(ROOT)),
            "count": read_vocab_csv(csv_file),
        }
    return result


# ---------------------------------------------------------------------------
# Merge
# ---------------------------------------------------------------------------

def merge(meta: dict, banks: list[str]) -> list[dict]:
    """Build the full entity list merging meta + all banks."""
    # Collect per-bank schemas and vocab
    bank_schemas: dict[str, dict[str, list[dict]]] = {}
    bank_vocabs: dict[str, dict[str, dict]] = {}
    for bank in banks:
        bank_schemas[bank] = scan_schemas(bank, meta)
        bank_vocabs[bank] = scan_vocab(bank, meta)

    # Determine all labels: from meta + from banks
    all_labels_ordered: list[str] = []
    seen: set[str] = set()
    for entry in meta.values():
        lbl = entry["label"]
        if lbl not in seen:
            all_labels_ordered.append(lbl)
            seen.add(lbl)
    for bank in banks:
        for lbl in bank_schemas[bank]:
            if lbl not in seen:
                all_labels_ordered.append(lbl)
                seen.add(lbl)

    # Build entity objects
    entities = []
    # Build reverse map: label -> (code_ru, meta_entry)
    label_to_meta: dict[str, tuple[str, dict]] = {}
    for code, entry in meta.items():
        lbl = entry["label"]
        if lbl not in label_to_meta:
            label_to_meta[lbl] = (code, entry)

    for label in all_labels_ordered:
        code_ru, meta_entry = label_to_meta.get(label, (label, None))

        # Union of fields across all banks, preserving first-seen order
        union_fields: list[dict] = []
        seen_field_names: set[str] = set()
        # Start with fields defined in entity_meta (e.g. ES logical fields)
        if meta_entry and meta_entry.get("fields"):
            for f in meta_entry["fields"]:
                fn = f["name"].upper() if f.get("data_type") is None else f["name"]
                if fn not in seen_field_names:
                    union_fields.append(f)
                    seen_field_names.add(fn)
        # Then add fields from bank CSVs
        for bank in banks:
            for f in bank_schemas[bank].get(label, []):
                if f["name"] not in seen_field_names:
                    union_fields.append(f)
                    seen_field_names.add(f["name"])

        # Per-bank summary
        banks_entry: dict[str, dict] = {}
        for bank in banks:
            b_fields = [f["name"] for f in bank_schemas[bank].get(label, [])]
            b_vocab = bank_vocabs[bank].get(label)
            if b_fields or b_vocab:
                banks_entry[bank] = {
                    "fields": b_fields,
                    "vocab": b_vocab["path"] if b_vocab else None,
                    "vocab_count": b_vocab["count"] if b_vocab else 0,
                }

        entity: dict = {
            "label": label,
            "code_ru": code_ru,
            "name_ru": meta_entry["name_ru"] if meta_entry else label,
            "prompt_ru": meta_entry["prompt_ru"] if meta_entry else "",
            "color": meta_entry["color"] if meta_entry else "#AAAAAA",
            "regex_group": meta_entry.get("regex_group") if meta_entry else None,
            "fields": union_fields,
            "banks": banks_entry,
        }
        entities.append(entity)

    return entities


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------

def write_entities(entities: list[dict], dry_run: bool) -> None:
    data = {
        "_generated_from": "data/banks/",
        "_note": "auto-generated — safe to edit manually for prompt tuning; regenerating will overwrite",
        "entities": entities,
    }
    if dry_run:
        print("[entities.json]\n" + json.dumps(data, ensure_ascii=False, indent=2))
        return
    OUT_ENTITIES.parent.mkdir(parents=True, exist_ok=True)
    OUT_ENTITIES.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] entities.json   -> {OUT_ENTITIES}")


def write_xml(entities: list[dict], dry_run: bool) -> None:
    lines = ['<View>', '  <Labels name="label" toName="text">']
    for e in entities:
        lines.append(f'    <Label value="{e["label"]}" background="{e["color"]}"/>')
    lines += ['  </Labels>', '  <Text name="text" value="$text"/>', '</View>']
    xml = "\n".join(lines)
    if dry_run:
        print("\n[label_studio_config.xml]\n" + xml)
        return
    OUT_XML.parent.mkdir(parents=True, exist_ok=True)
    OUT_XML.write_text(xml, encoding="utf-8")
    print(f"[OK] XML config      -> {OUT_XML}")
    print(xml)


def write_schema(entities: list[dict], dry_run: bool) -> None:
    all_field_names: set[str] = set()
    for e in entities:
        for f in e.get("fields", []):
            all_field_names.add(f["name"])
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "NEREntity",
        "type": "object",
        "required": ["start", "end", "label", "text"],
        "properties": {
            "start":  {"type": "integer"},
            "end":    {"type": "integer"},
            "label":  {"type": "string", "enum": [e["label"] for e in entities]},
            "text":   {"type": "string"},
            "score":  {"type": "number"},
            "source": {"type": "string"},
            "meta":   {
                "type": "object",
                "properties": {name: {"type": "string"} for name in sorted(all_field_names)},
                "additionalProperties": False,
            },
        },
    }
    if dry_run:
        print("\n[entity_schema.json]\n" + json.dumps(schema, ensure_ascii=False, indent=2))
        return
    OUT_SCHEMA.parent.mkdir(parents=True, exist_ok=True)
    OUT_SCHEMA.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] JSON schema     -> {OUT_SCHEMA}")


def write_vocab_index(entities: list[dict], banks: list[str], dry_run: bool) -> None:
    for bank in banks:
        index = {}
        for e in entities:
            b = e["banks"].get(bank)
            if b and b.get("vocab"):
                index[e["label"]] = {
                    "code_ru": e["code_ru"],
                    "path": b["vocab"],
                    "count": b.get("vocab_count", 0),
                }
        if not index:
            continue
        out = OUT_BANKS_DIR / bank / "vocab_index.json"
        if dry_run:
            print(f"\n[vocab_index {bank}]\n" + json.dumps(index, ensure_ascii=False, indent=2))
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[OK] vocab index     -> {out}")


def print_prompt(entities: list[dict]) -> None:
    print("\n[NER system prompt — entity list]\n")
    for e in entities:
        print(f"- {e['label']} ({e['name_ru']}) — {e['prompt_ru']}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--xml",     action="store_true", help="Generate Label Studio XML only")
    p.add_argument("--schema",  action="store_true", help="Generate JSON Schema only")
    p.add_argument("--prompt",  action="store_true", help="Print NER prompt snippet only")
    p.add_argument("--dry-run", action="store_true", help="Print to stdout, do not write files")
    args = p.parse_args()
    all_mode = not (args.xml or args.schema or args.prompt)

    if not META_PATH.exists():
        raise FileNotFoundError(f"entity_meta.json not found: {META_PATH}")

    meta = load_meta()
    banks = scan_banks()

    if not banks:
        print(f"[WARN] No banks found in {BANKS_DIR}. Creating empty entities from meta only.")

    entities = merge(meta, banks)

    if all_mode or not (args.xml or args.schema or args.prompt):
        write_entities(entities, args.dry_run)
        write_xml(entities, args.dry_run)
        write_schema(entities, args.dry_run)
        write_vocab_index(entities, banks, args.dry_run)
        print_prompt(entities)
    else:
        if args.xml:
            write_xml(entities, args.dry_run)
        if args.schema:
            write_schema(entities, args.dry_run)
        if args.prompt:
            print_prompt(entities)


if __name__ == "__main__":
    main()
