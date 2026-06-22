---
name: research-quality-measurement
description: Defines the rubric used to score the quality of a codebase research report (file:line accuracy, completeness, clarity) into one of four levels.
---

# Skill: Research Quality Measurement

Use this rubric whenever you assess a `codebase-research.md` (or similar research
artifact) and need to state its quality in a `verified-research.md` result file.

## Dimensions

1. **Reference Accuracy** — for every claim that cites a `file:line`, does the cited
   line actually exist and does the quoted snippet match the source exactly
   (whitespace-insensitive)?
2. **Completeness** — does the research address every symptom/question raised in
   the originating bug report or task, with a root cause identified for each?
3. **Clarity** — can a Bug Planner act on the research without re-reading the
   source code themselves (clear file paths, clear cause/effect explanation)?

## Levels

Compute `accuracy% = verified_references / total_references_checked`.

| Level | Accuracy | Completeness | Clarity | Meaning |
|---|---|---|---|---|
| **Excellent** | 100% | All symptoms addressed with root cause | Clear, actionable | Planner can proceed with no further investigation |
| **Good** | ≥ 90% | All symptoms addressed, minor gaps in detail | Mostly clear | Planner can proceed; note minor gaps |
| **Fair** | ≥ 70% | At least one symptom only partially addressed | Some ambiguity | Planner should re-verify flagged areas before proceeding |
| **Poor** | < 70% | One or more symptoms unaddressed, or root cause missing | Unclear or contradictory | Research must be redone before planning continues |

## Required output when applying this skill

In the result file, report:
- The computed accuracy percentage and the counts behind it (e.g. `9/10 references verified`).
- The chosen level and a one-paragraph justification tying the level explicitly to
  the table above (which dimension(s) drove the score).
- Whether the Bug Planner is cleared to proceed (Excellent/Good = yes, Fair = yes with
  caveats, Poor = no).
