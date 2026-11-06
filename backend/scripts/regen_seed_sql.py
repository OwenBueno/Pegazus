"""Regenerate supabase/seed.sql from algebra_p0lite.json (incl. primer_md)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SEED_JSON = next(
    (
        p
        for p in (
            Path("/supabase/seed/algebra_p0lite.json"),
            ROOT / "supabase" / "seed" / "algebra_p0lite.json",
            Path("/app/seed/algebra_p0lite.json"),
        )
        if p.is_file()
    ),
    ROOT / "supabase" / "seed" / "algebra_p0lite.json",
)
OUT_CANDIDATES = [
    Path("/app/seed/seed.sql"),
    Path("/supabase/seed.sql"),
    ROOT / "supabase" / "seed.sql",
]


def esc(s: str) -> str:
    return s.replace("'", "''")


def main() -> None:
    seed = json.loads(SEED_JSON.read_text(encoding="utf-8"))
    lines: list[str] = [
        "-- Idempotent Algebra seed (mirrors supabase/seed/algebra_p0lite.json)",
        "",
        "INSERT INTO public.knowledge_nodes "
        "(id, domain, slug, title, description, node_type, canonical_equation_latex, "
        "source_license, source_attribution, primer_md)",
        "VALUES",
    ]
    node_rows = []
    for n in seed["nodes"]:
        primer = esc(n.get("primer_md") or "")
        node_rows.append(
            f"  ('{n['id']}', 'MATHEMATICS', '{n['slug']}', '{esc(n['title'])}',\n"
            f"   '{esc(n['description'])}', '{n['node_type']}', "
            f"'{esc(n['canonical_equation_latex'])}', 'CC-BY-4.0', 'Pegazus seed',\n"
            f"   '{primer}')"
        )
    lines.append(",\n".join(node_rows))
    lines.extend(
        [
            "ON CONFLICT (id) DO UPDATE SET",
            "  title = EXCLUDED.title,",
            "  description = EXCLUDED.description,",
            "  canonical_equation_latex = EXCLUDED.canonical_equation_latex,",
            "  primer_md = EXCLUDED.primer_md;",
            "",
            "INSERT INTO public.knowledge_edges (parent_id, child_id, edge_type, weight)",
            "VALUES",
        ]
    )
    edge_rows = [
        f"  ('{e['parent_id']}', '{e['child_id']}', '{e['edge_type']}', {float(e['weight']):.2f})"
        for e in seed["edges"]
    ]
    lines.append(",\n".join(edge_rows))
    lines.extend(
        [
            "ON CONFLICT (parent_id, child_id, edge_type) DO UPDATE SET weight = EXCLUDED.weight;",
            "",
            "INSERT INTO public.items (id, node_id, statement_latex, steps, difficulty_estimate, status, source)",
            "VALUES",
        ]
    )
    item_rows = []
    for it in seed["items"]:
        steps_json = json.dumps(it["steps"], separators=(",", ":")).replace("'", "''")
        item_rows.append(
            f"  ('{it['id']}', '{it['node_id']}', '{esc(it['statement_latex'])}',\n"
            f"   '{steps_json}'::jsonb,\n"
            f"   {float(it['difficulty_estimate']):.2f}, '{it['status']}', '{it['source']}')"
        )
    lines.append(",\n".join(item_rows))
    lines.extend(
        [
            "ON CONFLICT (id) DO UPDATE SET",
            "  statement_latex = EXCLUDED.statement_latex,",
            "  steps = EXCLUDED.steps,",
            "  difficulty_estimate = EXCLUDED.difficulty_estimate,",
            "  status = EXCLUDED.status,",
            "  source = EXCLUDED.source;",
            "",
        ]
    )
    out = Path("/app/seed/seed.sql")
    out.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(lines)
    out.write_text(text, encoding="utf-8")
    for cand in (Path("/supabase/seed.sql"), ROOT / "supabase" / "seed.sql"):
        try:
            cand.write_text(text, encoding="utf-8")
            print(f"also wrote {cand}")
        except OSError:
            pass
    print(f"Wrote {out} ({len(seed['nodes'])} nodes, {len(seed['items'])} items)")


if __name__ == "__main__":
    main()
