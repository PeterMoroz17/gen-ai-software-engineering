const express = require('express');
const transactionRoutes = require('./routes/transactions');
const accountRoutes = require('./routes/accounts');
const rateLimiter = require('./middleware/rateLimiter');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());
app.use(rateLimiter);

app.use('/transactions', transactionRoutes);
app.use('/accounts', accountRoutes);

// 404 handler
app.use((req, res) => {
  res.status(404).json({
    error: 'Not Found',
    message: `${req.method} ${req.path} is not a valid endpoint`,
  });
});

// Global error handler
app.use((err, req, res, _next) => {
  console.error(err.stack);
  res.status(500).json({ error: 'Internal Server Error', message: err.message });
});

app.listen(PORT, () => {
  console.log(`Banking Transactions API running on http://localhost:${PORT}`);
});

module.exports = app;
