/* ============================================================
   Trust Mesh App Logic — js/app.js
   Shared utilities, live polling, sim mode control
   ============================================================ */

// ---- Page init (called by each page) -------------------------
function initPage() {
  highlightCurrentNav();
  checkAPIStatus();
  setInterval(checkAPIStatus, 15000);
}

function highlightCurrentNav() {
  const page = window.location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav-links a').forEach(a => {
    const href = a.getAttribute('href');
    if (href === page || (page === '' && href === 'index.html')) {
      a.classList.add('active');
    } else {
      a.classList.remove('active');
    }
  });
}

// ---- Simulation Banner helper --------------------------------
function updateSimBanner(isActive) {
  const banner = document.getElementById('simBanner');
  if (!banner) return;
  banner.style.display = isActive ? 'flex' : 'none';
}

// ---- Live polling for sensor data ----------------------------
class LivePoller {
  constructor(productId, onData, intervalMs = 5000) {
    this.productId  = productId;
    this.onData     = onData;
    this.intervalMs = intervalMs;
    this._timer     = null;
    this._lastCount = 0;
  }
  start() {
    this._tick();
    this._timer = setInterval(() => this._tick(), this.intervalMs);
  }
  stop() { clearInterval(this._timer); }

  async _tick() {
    try {
      const res = await API.getSensorHistory(this.productId, 100);
      if (res.count !== this._lastCount) {
        this._lastCount = res.count;
        this.onData(res.data);
      }
    } catch (e) { /* silent */ }
  }
}

// ---- Chart helpers -------------------------------------------
function buildSensorChart(ctxId, labels, tempData, humData) {
  const ctx = document.getElementById(ctxId).getContext('2d');
  return new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Temperature (°C)',
          data: tempData,
          borderColor: '#fb923c',
          backgroundColor: 'rgba(251,146,60,.1)',
          borderWidth: 2,
          pointRadius: 3,
          tension: 0.4,
          yAxisID: 'yTemp',
        },
        {
          label: 'Humidity (%)',
          data: humData,
          borderColor: '#60a5fa',
          backgroundColor: 'rgba(96,165,250,.1)',
          borderWidth: 2,
          pointRadius: 3,
          tension: 0.4,
          yAxisID: 'yHum',
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 300 },
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { labels: { color: '#7d9b82', font: { family: 'Inter', size: 12 } } },
        tooltip: {
          backgroundColor: '#111811',
          borderColor: '#4ade8033',
          borderWidth: 1,
          titleColor: '#e2ffe8',
          bodyColor: '#7d9b82',
        },
      },
      scales: {
        x: { ticks: { color: '#7d9b82', font: { size: 10 } }, grid: { color: '#1a281a' } },
        yTemp: {
          type: 'linear', position: 'left',
          ticks: { color: '#fb923c', font: { size: 10 } },
          grid: { color: '#1a281a' },
          title: { display: true, text: '°C', color: '#fb923c' },
        },
        yHum: {
          type: 'linear', position: 'right',
          ticks: { color: '#60a5fa', font: { size: 10 } },
          grid: { drawOnChartArea: false },
          title: { display: true, text: '%', color: '#60a5fa' },
        },
      },
    },
  });
}

function updateSensorChart(chart, sensorHistory) {
  const sorted = [...sensorHistory].reverse();
  chart.data.labels             = sorted.map(r => formatDT(r.received_at).split(',')[1]?.trim() || '');
  chart.data.datasets[0].data   = sorted.map(r => r.temperature);
  chart.data.datasets[1].data   = sorted.map(r => r.humidity);
  chart.update('none');
}

// ---- GPS / Location helper ----------------------------------
const LOCATION_CACHE = {
  '20.0059,73.7897': 'Nashik, Maharashtra',
  '18.5204,73.8567': 'Pune, Maharashtra',
  '19.0760,72.8777': 'Mumbai, Maharashtra',
  '17.3850,78.4867': 'Hyderabad, Telangana',
};

function coordsToCity(lat, lon) {
  if (!lat || !lon) return 'Unknown';
  const key = `${parseFloat(lat).toFixed(4)},${parseFloat(lon).toFixed(4)}`;
  return LOCATION_CACHE[key] || `${parseFloat(lat).toFixed(4)}°N, ${parseFloat(lon).toFixed(4)}°E`;
}

// ---- SIH Demo Mode ------------------------------------------
const DEMO_STEPS = [
  { id: 1, label: 'Connect ESP32',         desc: 'Physical device (DEVICE-001) connected via Wi-Fi' },
  { id: 2, label: 'Show Device Connected', desc: 'OLED shows IP address, sensor values' },
  { id: 3, label: 'Register AGRI-001',     desc: 'Farmer registers Organic Tomatoes, 500 kg, Nashik' },
  { id: 4, label: 'Generate QR Code',      desc: 'Unique QR linked to /verify/AGRI-001' },
  { id: 5, label: 'Start Sensor Monitoring',desc: 'Live temperature and humidity graph activated' },
  { id: 6, label: 'Send Sensor Data',      desc: 'ESP32 POSTs to /api/sensor-data every 10s' },
  { id: 7, label: 'Display Live Values',   desc: 'Dashboard shows 25.4°C, 67%, GPS: Nashik' },
  { id: 8, label: 'Record Supply Event',   desc: 'FARM_HARVESTED event added to blockchain' },
  { id: 9, label: 'Generate Block Hash',   desc: 'SHA-256 block mined and persisted to DB' },
  { id: 10,label: 'Verify Product',        desc: 'Consumer scans QR → PRODUCT VERIFIED ✓' },
  { id: 11,label: 'Run Tamper Test',       desc: 'Admin mutates sensor_data_hash in memory' },
  { id: 12,label: 'Show DATA TAMPERED',    desc: 'Chain verification detects mismatch → ALERT' },
];

window.DEMO_STEPS = DEMO_STEPS;

// Run on every page
initPage();
