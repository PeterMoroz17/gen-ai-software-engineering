const express = require('express');
const router = express.Router();
const { getAccountBalance, getAccountSummary } = require('../models/transaction');
const { validateAccountId } = require('../validators/transactionValidator');

function checkAccountId(req, res) {
  if (!validateAccountId(req.params.accountId)) {
    res.status(400).json({
      error: 'Invalid account ID',
      message: 'Account ID must follow format ACC-XXXXX (5 alphanumeric characters)',
    });
    return false;
  }
  return true;
}

// GET /accounts/:accountId/balance
router.get('/:accountId/balance', (req, res) => {
  if (!checkAccountId(req, res)) return;
  const balances = getAccountBalance(req.params.accountId);
  res.json({ accountId: req.params.accountId.toUpperCase(), balances });
});

// GET /accounts/:accountId/summary
router.get('/:accountId/summary', (req, res) => {
  if (!checkAccountId(req, res)) return;
  const summary = getAccountSummary(req.params.accountId);
  res.json(summary);
});

// GET /accounts/:accountId/interest?rate=0.05&days=30&currency=USD
router.get('/:accountId/interest', (req, res) => {
  if (!checkAccountId(req, res)) return;

  const rate = parseFloat(req.query.rate);
  const days = parseFloat(req.query.days);
  const currency = req.query.currency ? req.query.currency.toUpperCase() : undefined;

  if (req.query.rate === undefined || isNaN(rate) || rate < 0 || rate > 1) {
    return res.status(400).json({
      error: 'Invalid rate',
      message: 'rate must be a number between 0 and 1 (e.g. 0.05 for 5%)',
    });
  }

  if (req.query.days === undefined || isNaN(days) || days <= 0) {
    return res.status(400).json({
      error: 'Invalid days',
      message: 'days must be a positive number',
    });
  }

  if (!currency) {
    return res.status(400).json({
      error: 'Missing currency',
      message: 'currency is required (e.g. ?currency=USD)',
    });
  }

  const balances = getAccountBalance(req.params.accountId);
  const principal = balances[currency] || 0;
  const interest = principal * rate * (days / 365);

  res.json({
    accountId: req.params.accountId.toUpperCase(),
    currency,
    principal: parseFloat(principal.toFixed(2)),
    annualRate: rate,
    days,
    interest: parseFloat(interest.toFixed(2)),
    projectedBalance: parseFloat((principal + interest).toFixed(2)),
  });
});

module.exports = router;
