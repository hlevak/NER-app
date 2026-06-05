#!/usr/bin/env python3
"""Generate NER configuration artifacts from data/banks/ schemas.

CSV files are the single source of truth.
Entity metadata (label, name_ru, prompt_ru, color, regex_group) is generated
by LLM per bank and cached in config/banks/<BANK>/entity_meta.json.

Reads:
  data/banks/<BANK>/<KOD>.csv       -- DB field schemas per entity
  data/banks/<BANK>/vocab/<KOD>.csv -- vocabulary reference files

Generates (once, then cached):
  config/banks/<BANK>/entity_meta.json -- LLM-generated entity metadata per bank

Writes:
  config/entities.json             -- full NER entity config
  config/label_studio_config.xml   -- Label Studio XML
  config/entity_schema.json        -- JSON Schema for validation
  config/banks/<BANK>/vocab_index.json -- per-bank vocabulary index

Usage:
  python scripts/generate_input_schemas.py [--bank BANK] [--force] [--no-llm] [--dry-run]
  python scripts/generate_input_schemas.py --xml
  python scripts/generate_input_schemas.py --schema
  python scripts/generate_input_schemas.py --prompt
"""
import csv
import json
import sys
import argparse
import hashlib
from pathlib import Path

ROOT = Path(__file__).parent.parent
BANKS_DIR = ROOT / "data" / "banks"
OUT_ENTITIES = ROOT / "config" / "entities.json"
OUT_XML = ROOT / "config" / "label_studio_config.xml"
OUT_SCHEMA = ROOT / "config" / "entity_schema.json"
OUT_BANKS_DIR = ROOT / "config" / "banks"

# Default color palette for LLM to choose from (index-based fallback)
_COLOR_PALETTE = [
    "#FFA39E", "#D4380D", "#FFC069", "#95DE64", "#9254DE",
    "#1890FF", "#13C2C2", "#EB2F96", "#FA8C16", "#52C41A",
]

# Well-known entity type -> color mapping (used as hints in LLM prompt)
_KNOWN_COLORS = {
    "PER": "#FFA39E", "ORG": "#D4380D", "LOC": "#FFC069",
    "DATE": "#95DE64", "ES": "#9254DE",
}

# Well-known regex groups
_KNOWN_REGEX = {"DATE": "date", "ES": "es"}

# CSV column name candidates
FIELD_NAME_COLS = ("field_name", "column_name", "name", "поле", "колонка")
DATA_TYPE_COLS  = ("data_type", "type", "тип")
DESC_COLS       = ("description", "desc", "описание", "comment", "комментарий")
VOCAB_VAL_COLS  = ("value", "значение", "name", "имя")


# ---------------------------------------------------------------------------
# CSV helpers
# ---------------------------------------------------------------------------

def _find_col(header: list[str], candidates: tuple) -> int | None:
    lower = [h.lower().strip() for h in header]
    for c in candidates:
        if c in lower:
            return lower.index(c)
    return None


def read_schema_csv(path: Path) -> list[dict]:
    fields = []
    try:
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
    except Exception as exc:
        print(f"[WARN] Cannot read {path}: {exc}", file=sys.stderr)
    return fields


def read_vocab_sample(path: Path, n: int = 5) -> list[str]:
    samples = []
    try:
        with open(path, encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                val = next((c.strip() for c in row if c.strip()), None)
                if val:
                    samples.append(val)
                if len(samples) >= n:
                    break
    except Exception:
        pass
    return samples


def read_vocab_count(path: Path) -> int:
    try:
        with open(path, encoding="utf-8-sig", newline="") as f:
            return sum(1 for _ in csv.reader(f)) - 1
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# LLM metadata generation
# ---------------------------------------------------------------------------

_LLM_URL = "http://localhost:1234/v1/chat/completions"
_LLM_TIMEOUT = 120

_META_SYSTEM_PROMPT = """\
Ты - эксперт по распознаванию именованных сущностей (NER) в банковских базах данных.
Проанализируй таблицу БД и определи тип NER-сущности.

Правила выбора label:
- PER — таблица содержит ФИО, имена, фамилии людей
- ORG — организации, компании, юридические лица
- LOC или ADDR — адреса, города, регионы, страны
- DATE — даты рождения, события, периоды
- ES — электронные идентификаторы: телефоны, email, URL, IP, номера карт/счетов, кошельки
- DOC — документы: паспорт, ИНН, СНИЛС, серии документов
- Другой латинский код — если ни один из выше не подходит

Отвечай СТРОГО в формате JSON без пояснений.
"""


def _build_meta_prompt(bank: str, kod: str, fields: list[dict], vocab_samples: list[str]) -> str:
    field_lines = "\n".join(
        f"  - {f['name']} ({f['data_type'] or '?'})"
        + (f": {f['description']}" if f.get("description") else "")
        for f in fields[:20]
    )
    vocab_str = ", ".join(f'"{v}"' for v in vocab_samples[:5])
    color_hints = ", ".join(f"{k}={v}" for k, v in _KNOWN_COLORS.items())

    return f"""\
Банк: {bank}, файл: {kod}.csv
Колонки:
{field_lines or "  (нет колонок)"}
{f"Примеры из словаря: {vocab_str}" if vocab_samples else ""}

Ответь ТОЛЬКО в JSON:
{{
  "label": "<PER/ORG/LOC/DATE/ES/DOC/ADDR или другой, макс 6 латинских букв>",
  "name_ru": "<русское название, 2-4 слова>",
  "prompt_ru": "<описание для NER на русском, 1 предложение>",
  "color": "<hex-цвет: PER=#FFA39E ORG=#D4380D LOC=#FFC069 DATE=#95DE64 ES=#9254DE или новый>",
  "regex_group": <null, или "date" для дат, или "es" для электронных следов>
}}
"""


def _call_llm_for_meta(bank: str, kod: str, fields: list[dict], vocab_samples: list[str]) -> dict | None:
    try:
        import httpx
    except ImportError:
        return None

    prompt = _build_meta_prompt(bank, kod, fields, vocab_samples)
    payload = {
        "messages": [
            {"role": "system", "content": _META_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 256,
    }
    try:
        resp = httpx.post(_LLM_URL, json=payload, timeout=_LLM_TIMEOUT)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()
        # Extract JSON from possible markdown wrapper
        if "```" in content:
            content = content.split("```")[1].lstrip("json").strip()
        return json.loads(content)
    except Exception as exc:
        print(f"[WARN] LLM call failed for {bank}/{kod}: {exc}", file=sys.stderr)
        return None


def _default_meta(kod: str, idx: int) -> dict:
    """Fallback metadata when LLM is unavailable."""
    upper = kod.upper()
    return {
        "label": upper[:6],
        "name_ru": kod,
        "prompt_ru": f"сущности типа {kod}",
        "color": _COLOR_PALETTE[idx % len(_COLOR_PALETTE)],
        "regex_group": _KNOWN_REGEX.get(upper),
    }


def ensure_bank_meta(bank: str, schema_map: dict[str, list[dict]],
                     vocab_map: dict[str, list[str]], use_llm: bool, force: bool) -> dict:
    """Load or generate entity metadata for a bank. Returns {kod -> meta_dict}."""
    meta_path = OUT_BANKS_DIR / bank / "entity_meta.json"
    cached: dict = {}
    if meta_path.exists() and not force:
        try:
            cached = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            cached = {}

    changed = False
    idx = len(cached)
    for kod, fields in schema_map.items():
        if kod in cached:
            continue
        print(f"  [meta] {bank}/{kod} -> ", end="", flush=True)
        meta = None
        if use_llm:
            meta = _call_llm_for_meta(bank, kod, fields, vocab_map.get(kod, []))
        if meta:
            # Normalise
            meta.setdefault("label", kod.upper()[:6])
            meta.setdefault("name_ru", kod)
            meta.setdefault("prompt_ru", f"сущности типа {kod}")
            meta.setdefault("color", _KNOWN_COLORS.get(meta["label"], _COLOR_PALETTE[idx % len(_COLOR_PALETTE)]))
            meta.setdefault("regex_group", _KNOWN_REGEX.get(meta["label"]))
            print(f"LLM -> {meta['label']}")
        else:
            meta = _default_meta(kod, idx)
            print(f"default -> {meta['label']}")
        cached[kod] = meta
        idx += 1
        changed = True

    if changed:
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(json.dumps(cached, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  [saved] {meta_path}")

    return cached


# ---------------------------------------------------------------------------
# Scanners
# ---------------------------------------------------------------------------

def scan_banks(bank_filter: str | None = None) -> list[str]:
    if not BANKS_DIR.exists():
        return []
    banks = sorted(
        d.name for d in BANKS_DIR.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )
    return [b for b in banks if bank_filter is None or b == bank_filter]


def scan_schemas(bank: str) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {}
    for csv_file in sorted((BANKS_DIR / bank).glob("*.csv")):
        result[csv_file.stem] = read_schema_csv(csv_file)
    return result


def scan_vocab(bank: str) -> tuple[dict[str, list[str]], dict[str, dict]]:
    """Returns (samples_map, index_map)."""
    samples: dict[str, list[str]] = {}
    index: dict[str, dict] = {}
    vocab_dir = BANKS_DIR / bank / "vocab"
    if not vocab_dir.exists():
        return samples, index
    for csv_file in sorted(vocab_dir.glob("*.csv")):
        kod = csv_file.stem
        samples[kod] = read_vocab_sample(csv_file)
        index[kod] = {
            "path": str(csv_file.relative_to(ROOT)),
            "count": read_vocab_count(csv_file),
        }
    return samples, index


# ---------------------------------------------------------------------------
# Merge
# ---------------------------------------------------------------------------

def merge_all(banks: list[str], bank_metas: dict[str, dict],
              bank_schemas: dict[str, dict[str, list[dict]]],
              bank_vocab_idx: dict[str, dict[str, dict]]) -> list[dict]:
    """Build unified entity list across all banks."""
    # label -> entity dict (union of fields, union of banks)
    entity_map: dict[str, dict] = {}
    # Track insertion order
    label_order: list[str] = []

    for bank in banks:
        meta_dict = bank_metas[bank]   # {kod -> meta}
        for kod, fields in bank_schemas[bank].items():
            meta = meta_dict.get(kod, _default_meta(kod, 0))
            label = meta["label"]

            if label not in entity_map:
                label_order.append(label)
                entity_map[label] = {
                    "label": label,
                    "code_ru": kod,
                    "name_ru": meta["name_ru"],
                    "prompt_ru": meta["prompt_ru"],
                    "color": meta["color"],
                    "regex_group": meta.get("regex_group"),
                    "fields": [],
                    "banks": {},
                }
            ent = entity_map[label]

            # Union fields
            seen = {f["name"] for f in ent["fields"]}
            for f in fields:
                if f["name"] not in seen:
                    ent["fields"].append(f)
                    seen.add(f["name"])

            # Per-bank entry
            vi = bank_vocab_idx[bank].get(kod)
            ent["banks"][bank] = {
                "fields": [f["name"] for f in fields],
                "vocab": vi["path"] if vi else None,
                "vocab_count": vi["count"] if vi else 0,
            }

    return [entity_map[lbl] for lbl in label_order]


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------

def write_entities(entities: list[dict], dry_run: bool) -> None:
    data = {
        "_generated_from": "data/banks/",
        "_note": "auto-generated from CSV + LLM metadata; safe to edit prompt_ru manually",
        "entities": entities,
    }
    if dry_run:
        print("\n[entities.json]\n" + json.dumps(data, ensure_ascii=False, indent=2))
        return
    OUT_ENTITIES.parent.mkdir(parents=True, exist_ok=True)
    OUT_ENTITIES.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] entities.json      -> {OUT_ENTITIES}")


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
    print(f"[OK] label_studio_config.xml -> {OUT_XML}")
    print(xml)


def write_schema(entities: list[dict], dry_run: bool) -> None:
    all_fields: set[str] = set()
    for e in entities:
        all_fields.update(f["name"] for f in e.get("fields", []))
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
                "properties": {n: {"type": "string"} for n in sorted(all_fields)},
                "additionalProperties": False,
            },
        },
    }
    if dry_run:
        print("\n[entity_schema.json]\n" + json.dumps(schema, ensure_ascii=False, indent=2))
        return
    OUT_SCHEMA.parent.mkdir(parents=True, exist_ok=True)
    OUT_SCHEMA.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] entity_schema.json -> {OUT_SCHEMA}")


def write_vocab_indexes(entities: list[dict], banks: list[str], dry_run: bool) -> None:
    for bank in banks:
        index = {
            e["label"]: {"code_ru": e["code_ru"], **e["banks"][bank]}
            for e in entities
            if bank in e["banks"] and e["banks"][bank].get("vocab")
        }
        if not index:
            continue
        out = OUT_BANKS_DIR / bank / "vocab_index.json"
        if dry_run:
            print(f"\n[vocab_index {bank}]\n" + json.dumps(index, ensure_ascii=False, indent=2))
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[OK] vocab_index {bank}  -> {out}")


def print_prompt(entities: list[dict]) -> None:
    print("\n[NER system prompt -- entity list]")
    for e in entities:
        print(f"- {e['label']} ({e['name_ru']}) -- {e['prompt_ru']}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--bank",    help="Process only this bank")
    p.add_argument("--force",   action="store_true", help="Re-generate LLM metadata even if cached")
    p.add_argument("--no-llm",  action="store_true", help="Skip LLM, use default metadata")
    p.add_argument("--dry-run", action="store_true", help="Print outputs, do not write files")
    p.add_argument("--xml",     action="store_true", help="Generate Label Studio XML only")
    p.add_argument("--schema",  action="store_true", help="Generate JSON Schema only")
    p.add_argument("--prompt",  action="store_true", help="Print NER prompt snippet")
    args = p.parse_args()

    all_mode = not (args.xml or args.schema or args.prompt)
    use_llm = not args.no_llm

    banks = scan_banks(args.bank)
    if not banks:
        print(f"[WARN] No banks found in {BANKS_DIR}. Add CSV files to data/banks/<BANK>/")
        banks = []

    bank_schemas: dict[str, dict[str, list[dict]]] = {}
    bank_vocab_samples: dict[str, dict[str, list[str]]] = {}
    bank_vocab_idx: dict[str, dict[str, dict]] = {}
    bank_metas: dict[str, dict] = {}

    for bank in banks:
        print(f"\n[bank] {bank}")
        bank_schemas[bank] = scan_schemas(bank)
        bank_vocab_samples[bank], bank_vocab_idx[bank] = scan_vocab(bank)
        bank_metas[bank] = ensure_bank_meta(
            bank, bank_schemas[bank], bank_vocab_samples[bank],
            use_llm=use_llm, force=args.force,
        )

    entities = merge_all(banks, bank_metas, bank_schemas, bank_vocab_idx)

    if not entities and not banks:
        print("[INFO] No entities found. Nothing to generate.")
        return

    if all_mode:
        write_entities(entities, args.dry_run)
        write_xml(entities, args.dry_run)
        write_schema(entities, args.dry_run)
        write_vocab_indexes(entities, banks, args.dry_run)
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
