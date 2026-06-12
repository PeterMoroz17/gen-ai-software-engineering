const { v4: uuidv4 } = require('uuid');

const transactions = [];

function createTransaction(data) {
  const transaction = {
    id: uuidv4(),
    fromAccount: data.fromAccount ? data.fromAccount.toUpperCase() : null,
    toAccount: data.toAccount ? data.toAccount.toUpperCase() : null,
    amount: parseFloat(data.amount.toFixed(2)),
    currency: data.currency.toUpperCase(),
    type: data.type,
    timestamp: new Date().toISOString(),
    status: data.status || 'completed',
  };
  transactions.push(transaction);
  return transaction;
}

function getAllTransactions(filters = {}) {
  let result = [...transactions];

  if (filters.accountId) {
    const id = filters.accountId.toUpperCase();
    result = result.filter(t => t.fromAccount === id || t.toAccount === id);
  }

  if (filters.type) {
    result = result.filter(t => t.type === filters.type);
  }

  if (filters.from) {
    const fromDate = new Date(filters.from);
    result = result.filter(t => new Date(t.timestamp) >= fromDate);
  }

  if (filters.to) {
    const toDate = new Date(filters.to);
    toDate.setHours(23, 59, 59, 999);
    result = result.filter(t => new Date(t.timestamp) <= toDate);
  }

  return result;
}

function getTransactionById(id) {
  return transactions.find(t => t.id === id) || null;
}

function getAccountBalance(accountId) {
  const id = accountId.toUpperCase();
  const balances = {};

  for (const t of transactions) {
    if (t.status === 'failed') continue;
    const cur = t.currency;
    if (!balances[cur]) balances[cur] = 0;

    if (t.type === 'deposit' && t.toAccount === id) {
      balances[cur] += t.amount;
    } else if (t.type === 'withdrawal' && t.fromAccount === id) {
      balances[cur] -= t.amount;
    } else if (t.type === 'transfer') {
      if (t.toAccount === id) balances[cur] += t.amount;
      if (t.fromAccount === id) balances[cur] -= t.amount;
    }
  }

  for (const cur of Object.keys(balances)) {
    balances[cur] = parseFloat(balances[cur].toFixed(2));
  }

  return balances;
}

function getAccountSummary(accountId) {
  const id = accountId.toUpperCase();
  const accountTxns = transactions.filter(
    t => t.fromAccount === id || t.toAccount === id
  );

  const deposits = {};
  const withdrawals = {};
  let mostRecentDate = null;

  for (const t of accountTxns) {
    if (t.status === 'failed') continue;
    const cur = t.currency;
    if (!deposits[cur]) deposits[cur] = 0;
    if (!withdrawals[cur]) withdrawals[cur] = 0;

    const txDate = new Date(t.timestamp);
    if (!mostRecentDate || txDate > mostRecentDate) mostRecentDate = txDate;

    if (t.type === 'deposit' && t.toAccount === id) {
      deposits[cur] += t.amount;
    } else if (t.type === 'withdrawal' && t.fromAccount === id) {
      withdrawals[cur] += t.amount;
    } else if (t.type === 'transfer') {
      if (t.toAccount === id) deposits[cur] += t.amount;
      if (t.fromAccount === id) withdrawals[cur] += t.amount;
    }
  }

  for (const cur of Object.keys(deposits)) deposits[cur] = parseFloat(deposits[cur].toFixed(2));
  for (const cur of Object.keys(withdrawals)) withdrawals[cur] = parseFloat(withdrawals[cur].toFixed(2));

  return {
    accountId: id,
    totalDeposits: deposits,
    totalWithdrawals: withdrawals,
    numberOfTransactions: accountTxns.filter(t => t.status !== 'failed').length,
    mostRecentTransaction: mostRecentDate ? mostRecentDate.toISOString() : null,
  };
}

module.exports = {
  createTransaction,
  getAllTransactions,
  getTransactionById,
  getAccountBalance,
  getAccountSummary,
};
