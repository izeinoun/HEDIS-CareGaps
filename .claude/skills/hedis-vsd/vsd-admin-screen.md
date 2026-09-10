# UI direction — Value Set Directory (read-only)

How an application surfaces a value-set pack. **Read-only**, like the Rules admin: a pack is
*built* from the licensed NCQA directory and re-built when a new year is published — never
hand-edited (that would break traceability to the licensed source).

## Purpose

A quality/compliance user browses the codes behind the rules pack's value sets: which codes
define "Dialysis" for MY2027, which value sets contain a given code, and the effective year.
It answers *"what does this value-set name actually mean in codes, for this year?"* — the code
lists the spec PDF referenced only by name.

## Layout

1. **Header (version + effective banner).** From `source`: `measurement_year` (the version;
   offer a **year selector** if several are loaded), the `effective` date range, `loaded_at`,
   `directory_title`, `publisher`, and the standing **license** note (keep visible — licensed
   internal content). `vsd_version` is the (secondary) contract version.
2. **Value-set list.** One row per entry in `value_sets`: name, `oid`, code count. Expands to
   the code table (`system`, `code`, `description`).
3. **Search.** Across value-set names, codes, and descriptions — the common lookups are
   "codes for value set X" and "which value sets contain code Y" (reverse lookup via
   `find_value_sets_for_code`).

## Upload → build (admin only)

The directory is *loaded*, not authored: give an admin an **upload** control (gated to the
`manage_vsd` / Administrator role):
1. Admin uploads the NCQA VSD export (`.csv` / `.xlsx`).
2. The app runs `build_vsd_pack.py` (deterministic — no LLM) and its validator.
3. Store the pack keyed by `measurement_year`; display via this screen; report coverage
   (value-set and code counts) and any validator warnings honestly.

Never merge years — a new year's upload is a new pack, selectable via the year selector.

## Cross-links & guardrails

- **Rules-admin cross-link.** Each `value_sets` name on the Rules screen links here, resolving
  name → codes and closing the "names only" gap.
- **Reviewer.** Surface a value set's codes as **reference** on an exclusion/credential finding,
  and **validate** a code a reviewer captures via `contains_code`. Never auto-select a code.
- **Never export the codes.** Reviewer/plan exports stay value-set-*names* only; the licensed
  code lists do not leave the system.
