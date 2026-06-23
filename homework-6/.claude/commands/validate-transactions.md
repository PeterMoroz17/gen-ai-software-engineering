Validate all transactions in `sample-transactions.json` without processing them.

Steps:
1. Run the validator in dry-run mode: `python agents/transaction_validator.py --dry-run`.
2. Report: total count, valid count, invalid count, reasons for rejection (these are printed directly by the command).
3. Show a table of results (transaction_id | valid/invalid | reason).