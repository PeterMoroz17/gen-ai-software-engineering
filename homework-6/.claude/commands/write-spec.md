Generate or refresh `specification.md` for the banking pipeline, following the banking template in `../homework-3/specification-TEMPLATE-example.md`.

Steps:
1. Read `TASKS.md` and `sample-transactions.json` in this folder to ground every objective in real data.
2. Read `../homework-3/specification-TEMPLATE-example.md` for the structural skeleton (Banking-Specific Specification Template section).
3. Write `specification.md` with exactly 5 sections in this order:
   - **High-Level Objective** — one sentence.
   - **Mid-Level Objectives** — 4-5 concrete, testable requirements (reference real thresholds/fields from `sample-transactions.json`).
   - **Implementation Notes** — Decimal-only money, ISO 4217 currency, ISO 8601 audit logging, PII masking, file-based agent communication.
   - **Context** — Beginning context (what exists today) and Ending context (what will exist when done).
   - **Low-Level Tasks** — one entry per pipeline agent (`transaction_validator`, `fraud_detector`, `compliance_checker`, `integrator`), each with `Task / Prompt / File to CREATE / Function to CREATE / Details`.
4. Update `agents.md` if any meta-agent or pipeline-agent responsibility changed.
5. Report a short diff summary of what changed versus the previous `specification.md`, if one existed.