"""Render the user-facing Markdown validation report.

Consumed by the CLI in Task 15. The format is designed to be scannable in
30 seconds — a clinician opening this file should immediately see what's
right (✅), what's over a limit (⚠️), and what audit-trail changes were
made (ℹ️).
"""


def _md_safe(s) -> str:
    """Wrap user-controlled strings in inline-code spans to neutralize
    Markdown formatting (links, images, emphasis). Replaces any embedded
    backticks with a Unicode-look-alike to keep the span unbroken."""
    text = str(s) if s is not None else ""
    # If the string itself contains backticks, escape them so the span
    # doesn't terminate early.
    if "`" in text:
        text = text.replace("`", "ʼ")  # modifier-letter apostrophe — visually similar
    return f"`{text}`"


def render_report(payload: dict) -> str:
    """Produce a Markdown report from a validation payload.

    Expected payload shape:
        {
            "manuscript_filename": str,
            "journal": {"abbreviation": str, ...},
            "validation": {
                "sections": [{canonical, original_heading, word_count,
                              limit, over_limit}, ...],
                "missing_required": [{canonical, display}, ...],
                "total_word_count": int,
                "total_word_limit": int|None,
                "total_over_limit": bool,
            },
            "heading_renames": [{from, to}, ...],
            "cover_letter_path": str|None,
        }
    """
    journal = payload["journal"]
    validation = payload["validation"]

    lines: list[str] = []
    lines.append(
        f"# {journal['abbreviation']} Submission Report — "
        f"{_md_safe(payload['manuscript_filename'])}"
    )
    lines.append("")

    # Required-section status (header)
    if validation["missing_required"]:
        names = ", ".join(m["canonical"] for m in validation["missing_required"])
        lines.append(f"⚠️ Missing required sections: {names}")
    else:
        lines.append("✅ All required sections present")
    lines.append("")

    # Per-section breakdown
    for s in validation["sections"]:
        label = s["canonical"] or _md_safe(s["original_heading"]) or "(unnamed)"
        wc = s["word_count"]
        limit = s["limit"]
        if limit is None:
            lines.append(f"✅ {label}: {wc} words")
        else:
            mark = "⚠️" if s["over_limit"] else "✅"
            over = f" — {wc - limit} over" if s["over_limit"] else ""
            lines.append(f"{mark} {label}: {wc} words (limit {limit}){over}")

    # Total
    total_limit = validation["total_word_limit"]
    if total_limit is not None:
        mark = "⚠️" if validation["total_over_limit"] else "✅"
        lines.append(
            f"{mark} Total: {validation['total_word_count']:,} words "
            f"(limit {total_limit:,})"
        )
    else:
        lines.append(f"ℹ️ Total: {validation['total_word_count']:,} words")

    # Heading-rename audit trail
    if payload.get("heading_renames"):
        lines.append("")
        lines.append("## Heading changes")
        for r in payload["heading_renames"]:
            lines.append(f"- ℹ️ {_md_safe(r['from'])} → {_md_safe(r['to'])}")

    # Cover letter section (only when generated)
    cover_path = payload.get("cover_letter_path")
    if cover_path:
        lines.append("")
        lines.append("## Cover letter")
        lines.append(f"- Generated: yes ({cover_path})")
        lines.append("- ⚠️ Fill the [NOVELTY] placeholder before sending")

    return "\n".join(lines) + "\n"
