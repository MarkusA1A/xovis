// Xovis Dashboard - Frontend JavaScript

const API_BASE = '';
const MAX_OCCUPANCY = 50; // Maximale Gebäudebelegung für Ring-Anzeige

// Chart.js Instanzen
let chartToday = null;
let chartWeek = null;
let chartMonth = null;

// Farben
const COLORS = {
    in: 'rgb(45, 198, 83)',
    inBorder: 'rgb(34, 160, 65)',
    inBg: 'rgba(45, 198, 83, 0.12)',
    out: 'rgb(230, 57, 70)',
    outBorder: 'rgb(190, 40, 52)',
    outBg: 'rgba(230, 57, 70, 0.12)',
    occupancy: 'rgb(0, 119, 182)',
    occupancyBorder: 'rgb(0, 95, 150)',
    occupancyBg: 'rgba(0, 119, 182, 0.08)'
};

// Dark Mode erkennen
function isDarkMode() {
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
}

function getGridColor() {
    return isDarkMode() ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)';
}

function getTickColor() {
    return isDarkMode() ? '#5A6D87' : '#94A3B8';
}

// ==================== Uhr ====================

function updateClock() {
    const el = document.getElementById('clock');
    if (el) {
        el.textContent = new Date().toLocaleTimeString('de-DE', {
            hour: '2-digit', minute: '2-digit'
        });
    }
}

// ==================== API ====================

async function fetchAPI(endpoint) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error(`API Fehler (${endpoint}):`, error);
        return null;
    }
}

// ==================== Ring-Anzeige ====================

function updateOccupancyRing(value) {
    const ring = document.getElementById('occupancy-ring');
    if (!ring) return;

    const circumference = 2 * Math.PI * 52; // r=52
    const percent = Math.min(value / MAX_OCCUPANCY, 1);
    const offset = circumference * (1 - percent);
    ring.setAttribute('stroke-dashoffset', offset);
}

// ==================== Value Animation ====================

function animateValue(elementId, newValue) {
    const element = document.getElementById(elementId);
    if (!element) return;

    const oldText = element.textContent;
    const newText = newValue != null ? String(newValue) : '--';
    element.textContent = newText;

    if (oldText !== '--' && oldText !== newText) {
        element.classList.add('updated');
        setTimeout(() => element.classList.remove('updated'), 500);
    }
}

// ==================== Live-Daten ====================

async function updateLiveData() {
    const data = await fetchAPI('/api/live');
    if (!data) return;

    const current = data.current || {};

    animateValue('current-occupancy', current.occupancy);
    animateValue('count-in', current.count_in);
    animateValue('count-out', current.count_out);

    updateOccupancyRing(current.occupancy || 0);

    const timestamp = new Date(data.timestamp);
    document.getElementById('last-update').textContent = timestamp.toLocaleTimeString('de-DE');
}

async function updateStatus() {
    const data = await fetchAPI('/api/status');
    if (!data) return;

    const statusDot = document.querySelector('.status-dot');
    const statusText = document.querySelector('.status-text');
    const sensorIp = document.getElementById('sensor-ip');

    if (data.sensor_connected) {
        statusDot.className = 'status-dot connected';
        statusText.textContent = 'Sensor verbunden';
    } else {
        statusDot.className = 'status-dot disconnected';
        statusText.textContent = 'Sensor nicht erreichbar';
    }

    sensorIp.textContent = data.sensor_ip || '--';
}

// ==================== Chart Summary ====================

function renderSummary(containerId, data, type) {
    const el = document.getElementById(containerId);
    if (!el || !data) return;

    let html = '';

    if (type === 'today') {
        const totalIn = data.reduce((s, h) => s + (h.total_in || 0), 0);
        const totalOut = data.reduce((s, h) => s + (h.total_out || 0), 0);
        const peakHour = data.reduce((max, h) =>
            (h.total_in || 0) > (max.total_in || 0) ? h : max, data[0] || {});
        html = `
            <span class="stat">Eintritte: <span class="stat-value">${totalIn}</span></span>
            <span class="stat">Austritte: <span class="stat-value">${totalOut}</span></span>
            ${peakHour?.hour ? `<span class="stat">Peak: <span class="stat-value">${peakHour.hour}:00</span></span>` : ''}
        `;
    } else {
        const totalIn = data.reduce((s, d) => s + (d.total_in || 0), 0);
        const avgIn = data.length ? Math.round(totalIn / data.length) : 0;
        html = `
            <span class="stat">Gesamt: <span class="stat-value">${totalIn}</span></span>
            <span class="stat">Durchschnitt/Tag: <span class="stat-value">${avgIn}</span></span>
        `;
    }

    el.innerHTML = html;
}

// ==================== Charts ====================

function chartDefaults() {
    return {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { intersect: false, mode: 'index' },
        plugins: {
            legend: {
                position: 'top',
                align: 'end',
                labels: {
                    usePointStyle: true,
                    pointStyle: 'circle',
                    padding: 16,
                    font: { family: "'Outfit', sans-serif", size: 12, weight: '500' },
                    color: getTickColor()
                }
            },
            tooltip: {
                backgroundColor: isDarkMode() ? '#1C2840' : '#1B2A4A',
                titleColor: '#E8EDF5',
                bodyColor: '#C0CDE0',
                borderColor: isDarkMode() ? '#304060' : 'transparent',
                borderWidth: isDarkMode() ? 1 : 0,
                padding: 12,
                cornerRadius: 10,
                titleFont: { family: "'Outfit', sans-serif", size: 13, weight: '600' },
                bodyFont: { family: "'Outfit', sans-serif", size: 12 },
                callbacks: {
                    label: function(ctx) {
                        return ` ${ctx.dataset.label}: ${ctx.parsed.y} Personen`;
                    }
                }
            }
        },
        scales: {
            y: {
                beginAtZero: true,
                ticks: {
                    precision: 0,
                    font: { family: "'JetBrains Mono', monospace", size: 11 },
                    color: getTickColor()
                },
                grid: { color: getGridColor() },
                border: { display: false }
            },
            x: {
                ticks: {
                    font: { family: "'Outfit', sans-serif", size: 11 },
                    color: getTickColor()
                },
                grid: { display: false },
                border: { display: false }
            }
        }
    };
}

function createChart(ctx, type, labels, datasets, extraOpts = {}) {
    const opts = chartDefaults();
    Object.assign(opts, extraOpts);
    return new Chart(ctx, { type, data: { labels, datasets }, options: opts });
}

async function updateTodayChart() {
    const data = await fetchAPI('/api/stats/today');
    if (!data || !data.hours) return;

    const labels = [];
    const dataIn = [];
    const dataOut = [];
    const dataOccupancy = [];

    for (let h = 6; h <= 20; h++) {
        labels.push(`${h.toString().padStart(2, '0')}:00`);
        const hourData = data.hours.find(d => parseInt(d.hour) === h);
        dataIn.push(hourData?.total_in || 0);
        dataOut.push(hourData?.total_out || 0);
        dataOccupancy.push(hourData?.max_occupancy || 0);
    }

    renderSummary('today-summary', data.hours, 'today');

    const ctx = document.getElementById('chart-today');

    if (chartToday) {
        chartToday.data.labels = labels;
        chartToday.data.datasets[0].data = dataIn;
        chartToday.data.datasets[1].data = dataOut;
        chartToday.data.datasets[2].data = dataOccupancy;
        chartToday.update();
    } else {
        chartToday = createChart(ctx, 'line', labels, [
            {
                label: 'Eintritte',
                data: dataIn,
                borderColor: COLORS.in,
                backgroundColor: COLORS.inBg,
                borderWidth: 2.5,
                fill: true,
                tension: 0.35,
                pointRadius: 0,
                pointHoverRadius: 5,
                pointHoverBackgroundColor: COLORS.in
            },
            {
                label: 'Austritte',
                data: dataOut,
                borderColor: COLORS.out,
                backgroundColor: COLORS.outBg,
                borderWidth: 2.5,
                fill: true,
                tension: 0.35,
                pointRadius: 0,
                pointHoverRadius: 5,
                pointHoverBackgroundColor: COLORS.out
            },
            {
                label: 'Belegung',
                data: dataOccupancy,
                borderColor: COLORS.occupancy,
                backgroundColor: COLORS.occupancyBg,
                borderWidth: 2,
                fill: false,
                tension: 0.35,
                borderDash: [6, 4],
                pointRadius: 0,
                pointHoverRadius: 5,
                pointHoverBackgroundColor: COLORS.occupancy
            }
        ]);
    }
}

async function updateWeekChart() {
    const data = await fetchAPI('/api/stats/week');
    if (!data || !data.days) return;

    const labels = data.days.map(d => {
        const date = new Date(d.date);
        return date.toLocaleDateString('de-DE', { weekday: 'short', day: 'numeric' });
    });
    const dataIn = data.days.map(d => d.total_in || 0);
    const dataOut = data.days.map(d => d.total_out || 0);

    renderSummary('week-summary', data.days, 'week');

    const ctx = document.getElementById('chart-week');

    if (chartWeek) {
        chartWeek.data.labels = labels;
        chartWeek.data.datasets[0].data = dataIn;
        chartWeek.data.datasets[1].data = dataOut;
        chartWeek.update();
    } else {
        chartWeek = createChart(ctx, 'bar', labels, [
            {
                label: 'Eintritte',
                data: dataIn,
                backgroundColor: COLORS.in,
                borderColor: 'transparent',
                borderWidth: 0,
                borderRadius: 6,
                borderSkipped: false
            },
            {
                label: 'Austritte',
                data: dataOut,
                backgroundColor: COLORS.out,
                borderColor: 'transparent',
                borderWidth: 0,
                borderRadius: 6,
                borderSkipped: false
            }
        ]);
    }
}

async function updateMonthChart() {
    const data = await fetchAPI('/api/stats/month');
    if (!data || !data.days) return;

    const labels = data.days.map(d => new Date(d.date).getDate().toString());
    const dataIn = data.days.map(d => d.total_in || 0);
    const dataOut = data.days.map(d => d.total_out || 0);

    renderSummary('month-summary', data.days, 'month');

    const ctx = document.getElementById('chart-month');

    if (chartMonth) {
        chartMonth.data.labels = labels;
        chartMonth.data.datasets[0].data = dataIn;
        chartMonth.data.datasets[1].data = dataOut;
        chartMonth.update();
    } else {
        chartMonth = createChart(ctx, 'bar', labels, [
            {
                label: 'Eintritte',
                data: dataIn,
                backgroundColor: COLORS.in,
                borderColor: 'transparent',
                borderWidth: 0,
                borderRadius: 4,
                borderSkipped: false
            },
            {
                label: 'Austritte',
                data: dataOut,
                backgroundColor: COLORS.out,
                borderColor: 'transparent',
                borderWidth: 0,
                borderRadius: 4,
                borderSkipped: false
            }
        ]);
    }
}

// ==================== Tab Navigation ====================

function setupTabs() {
    const tabs = document.querySelectorAll('.tab');
    const contents = document.querySelectorAll('.tab-content');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            contents.forEach(c => c.classList.remove('active'));

            tab.classList.add('active');
            const tabId = `tab-${tab.dataset.tab}`;
            document.getElementById(tabId).classList.add('active');

            switch (tab.dataset.tab) {
                case 'today': updateTodayChart(); break;
                case 'week': updateWeekChart(); break;
                case 'month': updateMonthChart(); break;
            }
        });
    });
}

// ==================== Init ====================

async function init() {
    setupTabs();
    updateClock();
    setInterval(updateClock, 30000);

    await updateStatus();
    await updateLiveData();
    await updateTodayChart();

    setInterval(updateLiveData, 10000);
    setInterval(updateStatus, 60000);
    setInterval(updateTodayChart, 60000);
}

document.addEventListener('DOMContentLoaded', init);
