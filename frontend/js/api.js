/* ============================================================
   Trust Mesh API Client — js/api.js
   All API calls go through this module.
   BASE_URL can be overridden via localStorage.
   ============================================================ */

const BASE_URL = localStorage.getItem('agri_api_url') || 'http://localhost:8000';

const API = {
  // ---- Core fetch wrapper ------------------------------------
  async _fetch(path, options = {}) {
    try {
      const resp = await fetch(BASE_URL + path, {
        ...options,
        headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: resp.statusText }));
        throw new Error(err.detail || `HTTP ${resp.status}`);
      }
      return await resp.json();
    } catch (e) {
      console.error('[API]', path, e.message);
      throw e;
    }
  },

  // ---- Endpoints ----------------------------------------------
  async getStats()          { return this._fetch('/api/dashboard/stats'); },
  async getDevices()        { return this._fetch('/api/devices'); },

  async registerProduct(data) {
    return this._fetch('/api/register-product', { method: 'POST', body: JSON.stringify(data) });
  },
  async sendSensorData(data) {
    return this._fetch('/api/sensor-data', { method: 'POST', body: JSON.stringify(data) });
  },
  async addSupplyEvent(data) {
    return this._fetch('/api/supply-event', { method: 'POST', body: JSON.stringify(data) });
  },

  async getProduct(id)      { return this._fetch(`/api/product/${id}`); },
  async getSensorHistory(id, limit = 50) {
    return this._fetch(`/api/sensor-history/${id}?limit=${limit}`);
  },
  async getBlockchain(id)   { return this._fetch(`/api/blockchain/${id}`); },
  async verifyProduct(id)   { return this._fetch(`/api/verify/${id}`); },

  async tamperTest(data) {
    return this._fetch('/api/tamper-test', { method: 'POST', body: JSON.stringify(data) });
  },

  async startSimulation() {
    return this._fetch('/api/simulate/start', { method: 'POST' });
  },
  async stopSimulation() {
    return this._fetch('/api/simulate/stop', { method: 'POST' });
  },
};

// ---- Toast notifications ------------------------------------
function toast(msg, type = 'success') {
  let container = document.getElementById('toastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  const t = document.createElement('div');
  t.className = `toast toast-${type}`;
  t.textContent = msg;
  container.appendChild(t);
  setTimeout(() => t.remove(), 4000);
}

// ---- API status check ---------------------------------------
async function checkAPIStatus() {
  const dot    = document.getElementById('apiDot');
  const label  = document.getElementById('apiStatus');
  try {
    await API.getStats();
    if (dot)   dot.classList.add('ok');
    if (label) label.textContent = 'API Online';
  } catch {
    if (dot)   dot.classList.remove('ok');
    if (label) label.textContent = 'API Offline';
  }
}

// ---- Utility helpers ----------------------------------------
function shortHash(h = '') { return h ? `${h.slice(0,8)}...${h.slice(-8)}` : '—'; }
function formatDT(ts)      { return ts ? new Date(ts).toLocaleString('en-IN') : '—'; }
function formatNum(n, d=2)  { return n != null ? Number(n).toFixed(d) : '—'; }

function statusBadge(status) {
  const map = {
    registered: 'badge-blue',
    in_transit: 'badge-orange',
    warehouse:  'badge-purple',
    retail:     'badge-gold',
    delivered:  'badge-green',
    VALID:      'badge-green',
    TAMPERED:   'badge-red',
    CONNECTED:  'badge-green',
    OFFLINE:    'badge-red',
  };
  return `<span class="badge ${map[status] || 'badge-blue'}">${status}</span>`;
}

// ---- QR Code generator (client-side) ------------------------
// Uses qrcodejs CDN
function generateQRCanvas(text, canvasId) {
  const el = document.getElementById(canvasId);
  if (!el || typeof QRCode === 'undefined') return;
  el.innerHTML = '';
  new QRCode(el, {
    text,
    width: 200,
    height: 200,
    colorDark: '#4ade80',
    colorLight: '#0a0f0a',
    correctLevel: QRCode.CorrectLevel.H,
  });
}
