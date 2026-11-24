const express = require('express');
const path = require('path');
const fs = require('fs');
const cors = require('cors');
const cookieParser = require('cookie-parser');
const apiRouter = require('../server/routes/api');

const app = express();

app.use(cors());
app.use(cookieParser());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Serve static assets with caching headers
const staticDir = path.join(__dirname, '..', 'static');
app.use('/static', express.static(staticDir, { maxAge: '1h' }));

// Helper to render HTML templates with basic variable substitution
const templateDir = path.join(__dirname, '..', 'templates');
const renderTemplate = (filename, vars = {}) => {
  const filePath = path.join(templateDir, filename);
  let html = fs.readFileSync(filePath, 'utf8');
  const defaults = {
    hotel_name: "The Grand Pavilion & Palace Hotel",
    currency: "INR",
    ...vars
  };
  for (const [key, val] of Object.entries(defaults)) {
    const regex = new RegExp(`{{\\s*${key}\\s*}}`, 'g');
    html = html.replace(regex, String(val));
  }
  return html;
};

// Health probe
app.get('/healthz', (req, res) => {
  res.json({ status: "healthy", engine: "nodejs", timestamp: new Date().toISOString() });
});

// API Routes
app.use('/api', apiRouter);

// Page Routes
app.get('/', (req, res) => {
  try {
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    res.send(renderTemplate('landing.html'));
  } catch (e) {
    res.status(500).send("Error rendering landing page: " + e.message);
  }
});

app.get('/login', (req, res) => {
  try {
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    res.send(renderTemplate('login.html'));
  } catch (e) {
    res.status(500).send("Error rendering login page: " + e.message);
  }
});

app.get('/demo', (req, res) => {
  try {
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    res.send(renderTemplate('demo.html'));
  } catch (e) {
    res.status(500).send("Error rendering demo page: " + e.message);
  }
});

app.get('/pricing', (req, res) => {
  try {
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    res.send(renderTemplate('pricing.html'));
  } catch (e) {
    res.status(500).send("Error rendering pricing page: " + e.message);
  }
});

app.get('/security', (req, res) => {
  try {
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    res.send(renderTemplate('security.html'));
  } catch (e) {
    res.status(500).send("Error rendering security page: " + e.message);
  }
});

app.get('/status', (req, res) => {
  try {
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    res.send(renderTemplate('status.html'));
  } catch (e) {
    res.status(500).send("Error rendering status page: " + e.message);
  }
});

app.get('/changelog', (req, res) => {
  try {
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    res.send(renderTemplate('changelog.html'));
  } catch (e) {
    res.status(500).send("Error rendering changelog page: " + e.message);
  }
});

// PMS App Console Routes (All load app.html shell)
const appRoutes = [
  '/app',
  '/bookings',
  '/rooms',
  '/rate-calendar',
  '/timeline',
  '/tasks',
  '/housekeeping',
  '/night-audit',
  '/analytics',
  '/channels',
  '/property',
  '/policies',
  '/settings',
  '/billing',
  '/guests'
];

appRoutes.forEach(route => {
  app.get(route, (req, res) => {
    try {
      res.setHeader('Content-Type', 'text/html; charset=utf-8');
      res.send(renderTemplate('app.html'));
    } catch (e) {
      res.status(500).send("Error rendering app shell: " + e.message);
    }
  });
});

// Local Development Server
if (require.main === module) {
  const PORT = process.env.PORT || 8000;
  app.listen(PORT, () => {
    console.log(`[CheckinOS Node.js Engine] Running at http://localhost:${PORT}`);
  });
}

module.exports = app;
