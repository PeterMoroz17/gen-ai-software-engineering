Run the multi-agent banking pipeline end-to-end.

Steps:
1. Check that `sample-transactions.json` exists in this folder.
2. Clear the `shared/` directories (the integrator does this automatically on each run).
3. Run the pipeline: `python integrator.py`.
4. Show a summary of results from `shared/results/` (read `shared/results/summary.json`).
5. Report any transactions that were rejected and why (read each `shared/results/<transaction_id>.json` where `status == "rejected"` and print its `reason`).