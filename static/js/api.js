/**
 * Hotel OS - API Client and Formatting Utilities
 * Handles authenticated API calls, automatic 401 redirects, retry logic, and formatting.
 */

const API_BASE = '';

// High-speed in-memory client cache with Stale-While-Revalidate (SWR)
const _apiCache = new Map();
const CACHE_TTL_MS = 30000; // 30 seconds

const API = {
  clearCache() {
    _apiCache.clear();
  },

  getToken() {
    return localStorage.getItem('access_token');
  },

  setToken(token) {
    if (token) {
      localStorage.setItem('access_token', token);
      try { document.cookie = `access_token=${token}; path=/; max-age=604800; SameSite=Lax`; } catch (e) {}
    } else {
      localStorage.removeItem('access_token');
      try { document.cookie = 'access_token=; path=/; max-age=0; SameSite=Lax'; } catch (e) {}
    }
  },

  getUser() {
    const u = localStorage.getItem('current_user');
    return u ? JSON.parse(u) : null;
  },

  setUser(user) {
    if (user) {
      localStorage.setItem('current_user', JSON.stringify(user));
    } else {
      localStorage.removeItem('current_user');
    }
  },

  /**
   * Core request dispatcher with retry and error handling.
   */
  async request(endpoint, options = {}, isRetry = false) {
    const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;
    const token = this.getToken();

    const headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    };

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      // 401 Unauthorized handling: Hard redirect to login (except when attempting to login)
      if (response.status === 401) {
        if (endpoint === '/api/auth/login' || endpoint.includes('/auth/login')) {
          const errData = contentType.includes('application/json') ? await response.clone().json() : null;
          const msg = errData?.error?.message || errData?.detail || 'Invalid username/email or password';
          throw new Error(msg);
        }
        this.setToken(null);
        this.setUser(null);
        if (!window.location.pathname.includes('/login')) {
          sessionStorage.setItem('flash_toast', JSON.stringify({ type: 'warning', message: 'Session expired. Please sign in.' }));
          window.location.href = '/login';
        }
        throw new Error('Session expired');
      }

      // 402 Payment Required: If trial expired or subscription locked, redirect to /locked
      if (response.status === 402) {
        const errData = contentType.includes('application/json') ? await response.clone().json() : null;
        if (errData?.error?.code === 'trial_expired' || errData?.error?.code === 'subscription_locked') {
          window.location.href = '/locked';
          throw new Error(errData.error.message);
        }
      }

      // 5xx Server Error handling: Auto retry once after 3 seconds
      if (response.status >= 500 && !isRetry) {
        if (window.UI && window.UI.toast) {
          window.UI.toast('Something went wrong, retrying in 3s...', 'warning');
        }
        await new Promise(resolve => setTimeout(resolve, 3000));
        return this.request(endpoint, options, true);
      }

      const contentType = response.headers.get('content-type') || '';
      let data = null;
      if (contentType.includes('application/json')) {
        data = await response.json();
      }

      if (!response.ok) {
        const errorMsg = data?.error?.message || data?.detail || `Request failed with status ${response.status}`;
        const error = new Error(errorMsg);
        error.status = response.status;
        error.data = data;
        throw error;
      }

      return data;
    } catch (err) {
      if (err.name === 'TypeError' && !isRetry) {
        // Network failure retry
        if (window.UI && window.UI.toast) {
          window.UI.toast('Connection issue, retrying...', 'warning');
        }
        await new Promise(resolve => setTimeout(resolve, 3000));
        return this.request(endpoint, options, true);
      }
      throw err;
    }
  },

  get(endpoint, params = {}, forceFresh = false) {
    const query = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== null && v !== undefined && v !== '') {
        query.append(k, v);
      }
    }
    const qs = query.toString();
    const fullUrl = qs ? `${endpoint}?${qs}` : endpoint;
    const now = Date.now();

    // Check SWR memory cache
    if (!forceFresh && _apiCache.has(fullUrl)) {
      const entry = _apiCache.get(fullUrl);
      if (now - entry.timestamp < CACHE_TTL_MS) {
        // Return cached instantly (0ms) and refresh silently in background
        this.request(fullUrl, { method: 'GET' }).then(freshData => {
          _apiCache.set(fullUrl, { data: freshData, timestamp: Date.now() });
        }).catch(() => {});
        return Promise.resolve(JSON.parse(JSON.stringify(entry.data)));
      }
    }

    return this.request(fullUrl, { method: 'GET' }).then(data => {
      _apiCache.set(fullUrl, { data, timestamp: Date.now() });
      return data;
    });
  },

  post(endpoint, body = {}) {
    _apiCache.clear();
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(body),
    });
  },

  patch(endpoint, body = {}) {
    _apiCache.clear();
    return this.request(endpoint, {
      method: 'PATCH',
      body: JSON.stringify(body),
    });
  },

  put(endpoint, body = {}) {
    _apiCache.clear();
    return this.request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(body),
    });
  },

  delete(endpoint) {
    _apiCache.clear();
    return this.request(endpoint, { method: 'DELETE' });
  },

  // Auth Operations
  async login(username_or_email, password) {
    const res = await this.post('/api/auth/login', { username_or_email, password });
    this.setToken(res.access_token);
    this.setUser(res.user);
    return res;
  },

  async logout() {
    try {
      await this.post('/api/auth/logout');
    } catch (e) {
      // Ignore network errors on logout
    }
    this.setToken(null);
    this.setUser(null);
    window.location.href = '/login';
  },

  async me() {
    const user = await this.get('/api/auth/me');
    this.setUser(user);
    return user;
  },
};

/**
 * Currency Formatter (INR Indian Rupee default)
 */
/**
 * Active Currency Resolver & Formatter
 * Dynamically resolves hotel operating currency from workstation preference or organization settings.
 */
function getActiveCurrency() {
  return localStorage.getItem('checkinos_currency') ||
         (window.currentUser && window.currentUser.organization && window.currentUser.organization.currency) ||
         (window.currentOrg && window.currentOrg.currency) ||
         'INR';
}

function getCurrencySymbol(curr = null) {
  const c = (curr || getActiveCurrency()).toUpperCase();
  const map = {
    INR: '₹',
    USD: '$',
    EUR: '€',
    GBP: '£',
    AED: 'AED ',
    JPY: '¥',
    AUD: 'A$',
    CAD: 'C$',
    SGD: 'S$',
  };
  return map[c] || `${c} `;
}

function getCurrencyLocale(curr) {
  switch (curr) {
    case 'USD': return 'en-US';
    case 'EUR': return 'de-DE';
    case 'GBP': return 'en-GB';
    case 'AED': return 'ar-AE';
    case 'JPY': return 'ja-JP';
    case 'AUD': return 'en-AU';
    case 'CAD': return 'en-CA';
    case 'SGD': return 'en-SG';
    case 'INR':
    default: return 'en-IN';
  }
}

function formatCurrency(amount, currency = null) {
  const activeCurr = (currency || getActiveCurrency()).toUpperCase();
  const num = typeof amount === 'string' ? parseFloat(amount) : (amount || 0);
  const locale = getCurrencyLocale(activeCurr);
  try {
    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency: activeCurr,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(num);
  } catch (e) {
    return `${getCurrencySymbol(activeCurr)}${Number(num).toFixed(2)}`;
  }
}

/**
 * Human-Friendly Date Formatter ("Mon, 24 Nov" — never raw ISO)
 */
function formatDate(dateStr, options = { weekday: 'short', day: 'numeric', month: 'short' }) {
  if (!dateStr) return '—';
  // If YYYY-MM-DD, parse as local calendar date without timezone shift
  let d;
  if (typeof dateStr === 'string' && dateStr.length === 10 && dateStr.includes('-')) {
    const [y, m, day] = dateStr.split('-').map(Number);
    d = new Date(y, m - 1, day);
  } else {
    d = new Date(dateStr);
  }
  if (isNaN(d.getTime())) return dateStr;
  return new Intl.DateTimeFormat('en-US', options).format(d);
}

/**
 * Relative Timestamp Formatter ("2m ago", "1h ago", "yesterday")
 */
function formatRelativeTime(dateStr) {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  const now = new Date();
  const diffInSeconds = Math.round((date - now) / 1000);

  const rtf = new Intl.RelativeTimeFormat('en', { numeric: 'auto' });

  const absSec = Math.abs(diffInSeconds);
  if (absSec < 60) return 'just now';
  const diffInMinutes = Math.round(diffInSeconds / 60);
  if (Math.abs(diffInMinutes) < 60) return rtf.format(diffInMinutes, 'minute');
  const diffInHours = Math.round(diffInMinutes / 60);
  if (Math.abs(diffInHours) < 24) return rtf.format(diffInHours, 'hour');
  const diffInDays = Math.round(diffInHours / 24);
  if (Math.abs(diffInDays) < 30) return rtf.format(diffInDays, 'day');
  return formatDate(dateStr);
}

// Ensure cookie is in sync with localStorage on script load
try {
  const curToken = API.getToken();
  if (curToken && !document.cookie.includes('access_token=')) {
    document.cookie = `access_token=${curToken}; path=/; max-age=604800; SameSite=Lax`;
  }
} catch (e) {}

window.API = API;
window.getActiveCurrency = getActiveCurrency;
window.getCurrencySymbol = getCurrencySymbol;
window.formatCurrency = formatCurrency;
window.formatDate = formatDate;
window.formatRelativeTime = formatRelativeTime;
