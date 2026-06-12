const VALID_CURRENCIES = new Set([
  'AED','AFN','ALL','AMD','ANG','AOA','ARS','AUD','AWG','AZN',
  'BAM','BBD','BDT','BGN','BHD','BIF','BMD','BND','BOB','BRL',
  'BSD','BTN','BWP','BYN','BZD','CAD','CDF','CHF','CLP','CNY',
  'COP','CRC','CUP','CVE','CZK','DJF','DKK','DOP','DZD','EGP',
  'ERN','ETB','EUR','FJD','FKP','GBP','GEL','GHS','GIP','GMD',
  'GNF','GTQ','GYD','HKD','HNL','HRK','HTG','HUF','IDR','ILS',
  'INR','IQD','IRR','ISK','JMD','JOD','JPY','KES','KGS','KHR',
  'KMF','KPW','KRW','KWD','KYD','KZT','LAK','LBP','LKR','LRD',
  'LSL','LYD','MAD','MDL','MGA','MKD','MMK','MNT','MOP','MRU',
  'MUR','MVR','MWK','MXN','MYR','MZN','NAD','NGN','NIO','NOK',
  'NPR','NZD','OMR','PAB','PEN','PGK','PHP','PKR','PLN','PYG',
  'QAR','RON','RSD','RUB','RWF','SAR','SBD','SCR','SDG','SEK',
  'SGD','SHP','SLE','SOS','SRD','STN','SYP','SZL','THB','TJS',
  'TMT','TND','TOP','TRY','TTD','TWD','TZS','UAH','UGX','USD',
  'UYU','UZS','VES','VND','VUV','WST','XAF','XCD','XOF','XPF',
  'YER','ZAR','ZMW','ZWL',
]);

const ACCOUNT_REGEX = /^ACC-[A-Z0-9]{5}$/;
const VALID_TYPES = ['deposit', 'withdrawal', 'transfer'];
const VALID_STATUSES = ['pending', 'completed', 'failed'];

function hasAtMostTwoDecimals(amount) {
  const rounded = parseFloat(amount.toFixed(2));
  return Math.abs(rounded - amount) < 1e-10;
}

function isValidAccount(value) {
  return typeof value === 'string' && ACCOUNT_REGEX.test(value.toUpperCase());
}

function validateTransaction(data) {
  const errors = [];

  // amount
  if (data.amount === undefined || data.amount === null) {
    errors.push({ field: 'amount', message: 'Amount is required' });
  } else if (typeof data.amount !== 'number' || isNaN(data.amount)) {
    errors.push({ field: 'amount', message: 'Amount must be a number' });
  } else if (data.amount <= 0) {
    errors.push({ field: 'amount', message: 'Amount must be a positive number' });
  } else if (!hasAtMostTwoDecimals(data.amount)) {
    errors.push({ field: 'amount', message: 'Amount must have at most 2 decimal places' });
  }

  // currency
  if (!data.currency) {
    errors.push({ field: 'currency', message: 'Currency is required' });
  } else if (!VALID_CURRENCIES.has(data.currency.toUpperCase())) {
    errors.push({ field: 'currency', message: `Invalid currency code: ${data.currency}` });
  }

  // type
  if (!data.type) {
    errors.push({ field: 'type', message: 'Transaction type is required' });
  } else if (!VALID_TYPES.includes(data.type)) {
    errors.push({ field: 'type', message: `Type must be one of: ${VALID_TYPES.join(', ')}` });
  } else {
    // account requirements per type
    if (data.type === 'deposit') {
      if (!data.toAccount) {
        errors.push({ field: 'toAccount', message: 'toAccount is required for deposits' });
      } else if (!isValidAccount(data.toAccount)) {
        errors.push({ field: 'toAccount', message: 'Account must follow format ACC-XXXXX (alphanumeric)' });
      }
    } else if (data.type === 'withdrawal') {
      if (!data.fromAccount) {
        errors.push({ field: 'fromAccount', message: 'fromAccount is required for withdrawals' });
      } else if (!isValidAccount(data.fromAccount)) {
        errors.push({ field: 'fromAccount', message: 'Account must follow format ACC-XXXXX (alphanumeric)' });
      }
    } else if (data.type === 'transfer') {
      if (!data.fromAccount) {
        errors.push({ field: 'fromAccount', message: 'fromAccount is required for transfers' });
      } else if (!isValidAccount(data.fromAccount)) {
        errors.push({ field: 'fromAccount', message: 'Account must follow format ACC-XXXXX (alphanumeric)' });
      }
      if (!data.toAccount) {
        errors.push({ field: 'toAccount', message: 'toAccount is required for transfers' });
      } else if (!isValidAccount(data.toAccount)) {
        errors.push({ field: 'toAccount', message: 'Account must follow format ACC-XXXXX (alphanumeric)' });
      }
      if (
        data.fromAccount && data.toAccount &&
        data.fromAccount.toUpperCase() === data.toAccount.toUpperCase()
      ) {
        errors.push({ field: 'toAccount', message: 'fromAccount and toAccount must be different' });
      }
    }
  }

  // status (optional field)
  if (data.status !== undefined && !VALID_STATUSES.includes(data.status)) {
    errors.push({ field: 'status', message: `Status must be one of: ${VALID_STATUSES.join(', ')}` });
  }

  return errors;
}

function validateAccountId(accountId) {
  return isValidAccount(accountId);
}

module.exports = { validateTransaction, validateAccountId };
