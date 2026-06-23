const WINDOW_MS = 60 * 1000;
const MAX_REQUESTS = 100;

const requestCounts = new Map();

function rateLimiter(req, res, next) {
  const ip = req.ip || req.connection.remoteAddress || 'unknown';
  const now = Date.now();

  const record = requestCounts.get(ip);

  if (!record || now > record.resetAt) {
    requestCounts.set(ip, { count: 1, resetAt: now + WINDOW_MS });
    return next();
  }

  record.count += 1;

  if (record.count > MAX_REQUESTS) {
    const retryAfter = Math.ceil((record.resetAt - now) / 1000);
    res.set('Retry-After', retryAfter);
    return res.status(429).json({
      error: 'Too Many Requests',
      message: `Maximum ${MAX_REQUESTS} requests per minute exceeded`,
      retryAfter,
    });
  }

  next();
}

module.exports = rateLimiter;
