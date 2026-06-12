const express = require('express');
const router = express.Router();
const {
  createTransaction,
  getAllTransactions,
  getTransactionById,
  getAccountBalance,
} = require('../models/transaction');
const { validateTransaction } = require('../validators/transactionValidator');

// POST /transactions
router.post('/', (req, res) => {
  const errors = validateTransaction(req.body);
  if (errors.length > 0) {
    return res.status(400).json({ error: 'Validation failed', details: errors });
  }

  const { type, fromAccount, amount, currency } = req.body;
  if (type === 'withdrawal' || type === 'transfer') {
    const balances = getAccountBalance(fromAccount);
    const available = balances[currency.toUpperCase()] || 0;
    if (available < amount) {
      return res.status(400).json({
        error: 'Insufficient funds',
        message: `Account ${fromAccount.toUpperCase()} has ${available} ${currency.toUpperCase()}, but ${amount} is required`,
      });
    }
  }

  const transaction = createTransaction(req.body);
  res.status(201).json(transaction);
});

// GET /transactions/export?format=csv  (must come before /:id)
router.get('/export', (req, res) => {
  const { format = 'csv' } = req.query;

  if (format !== 'csv') {
    return res.status(400).json({ error: 'Unsupported format', message: 'Only format=csv is supported' });
  }

  const all = getAllTransactions();
  const headers = ['id', 'fromAccount', 'toAccount', 'amount', 'currency', 'type', 'timestamp', 'status'];

  const csvRows = all.map(t =>
    headers.map(h => {
      const val = t[h] == null ? '' : String(t[h]);
      return `"${val.replace(/"/g, '""')}"`;
    }).join(',')
  );

  const csv = [headers.join(','), ...csvRows].join('\r\n');

  res.setHeader('Content-Type', 'text/csv');
  res.setHeader('Content-Disposition', 'attachment; filename="transactions.csv"');
  res.send(csv);
});

// GET /transactions?accountId=&type=&from=&to=
router.get('/', (req, res) => {
  const { accountId, type, from, to } = req.query;
  const filters = {};
  if (accountId) filters.accountId = accountId;
  if (type) filters.type = type;
  if (from) filters.from = from;
  if (to) filters.to = to;

  const result = getAllTransactions(filters);
  res.json(result);
});

// GET /transactions/:id
router.get('/:id', (req, res) => {
  const transaction = getTransactionById(req.params.id);
  if (!transaction) {
    return res.status(404).json({
      error: 'Not Found',
      message: `Transaction with id '${req.params.id}' not found`,
    });
  }
  res.json(transaction);
});

module.exports = router;
