// Xovis Dashboard - Frontend JavaScript

const API_BASE = '';  // Relativ zur aktuellen Domain

// Chart.js Instanzen
let chartToday = null;
let chartWeek = null;
let chartMonth = null;

// Farben für Charts
const COLORS = {
    in: 'rgb(34, 197, 94)',             // Grün
    inBorder: 'rgb(22, 163, 74)',
    inBg: 'rgba(34, 197, 94, 0.15)',
    out: 'rgb(239, 68, 68)',            // Rot
    outBorder: 'rgb(220, 38, 38)',
    outBg: 'rgba(239, 68, 68, 0.15)',
    occupancy: 'rgb(37, 99, 235)',      // Blau
    occupancyBorder: 'rgb(29, 78, 216)',
    occupancyBg: 'rgba(37, 99, 235, 0.1)'
};

// ==================== API Calls ====================

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

// ==================== Live-Daten ====================

// Letzte bekannte Werte für Animation
let lastValues = { occupancy: null, count_in: null, count_out: null };

function animateValue(elementId, newValue) {
    const element = document.getElementById(elementId);
    const oldValue = element.textContent;
    element.textContent = newValue ?? '--';

    // Animation bei Wertänderung
    if (oldValue !== '--' && oldValue !== String(newValue)) {
        element.classList.add('updated');
        setTimeout(() => element.classList.remove('updated'), 300);
    }
}

async function updateLiveData() {
    const data = await fetchAPI('/api/live');
    if (!data) return;

    const current = data.current || {};

    // Werte mit Animation aktualisieren
    animateValue('current-occupancy', current.occupancy);
    animateValue('count-in', current.count_in);
    animateValue('count-out', current.count_out);

    // Zeitstempel
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
        statusText.textContent = 'Sensor nicht erreichbar (Testmodus)';
    }

    // Sensor IP anzeigen
    sensorIp.textContent = data.sensor_ip || '--';
}

// ==================== Charts ====================

function createChart(ctx, type, labels, datasets, options = {}) {
    return new Chart(ctx, {
        type: type,
        data: { labels, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 15
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    padding: 12,
                    titleFont: { size: 14 },
                    bodyFont: { size: 13 },
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: ${context.parsed.y} Personen`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            },
            ...options
        }
    });
}

async function updateTodayChart() {
    const data = await fetchAPI('/api/stats/today');
    if (!data || !data.hours) return;

    const labels = [];
    const dataIn = [];
    const dataOut = [];
    const dataOccupancy = [];

    // Alle 24 Stunden vorbereiten
    for (let h = 0; h < 24; h++) {
        labels.push(`${h.toString().padStart(2, '0')}:00`);
        const hourData = data.hours.find(d => parseInt(d.hour) === h);
        dataIn.push(hourData?.total_in || 0);
        dataOut.push(hourData?.total_out || 0);
        dataOccupancy.push(hourData?.max_occupancy || 0);
    }

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
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointRadius: 3,
                pointHoverRadius: 6
            },
            {
                label: 'Austritte',
                data: dataOut,
                borderColor: COLORS.out,
                backgroundColor: COLORS.outBg,
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointRadius: 3,
                pointHoverRadius: 6
            },
            {
                label: 'Max. Belegung',
                data: dataOccupancy,
                borderColor: COLORS.occupancy,
                backgroundColor: COLORS.occupancyBg,
                borderWidth: 2,
                fill: false,
                tension: 0.4,
                borderDash: [6, 4],
                pointRadius: 3,
                pointHoverRadius: 6
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
                borderColor: COLORS.inBorder,
                borderWidth: 1,
                borderRadius: 4
            },
            {
                label: 'Austritte',
                data: dataOut,
                backgroundColor: COLORS.out,
                borderColor: COLORS.outBorder,
                borderWidth: 1,
                borderRadius: 4
            }
        ]);
    }
}

async function updateMonthChart() {
    const data = await fetchAPI('/api/stats/month');
    if (!data || !data.days) return;

    const labels = data.days.map(d => {
        const date = new Date(d.date);
        return date.getDate().toString();
    });

    const dataIn = data.days.map(d => d.total_in || 0);
    const dataOut = data.days.map(d => d.total_out || 0);

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
                borderColor: COLORS.inBorder,
                borderWidth: 1,
                borderRadius: 4
            },
            {
                label: 'Austritte',
                data: dataOut,
                backgroundColor: COLORS.out,
                borderColor: COLORS.outBorder,
                borderWidth: 1,
                borderRadius: 4
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
            // Alle deaktivieren
            tabs.forEach(t => t.classList.remove('active'));
            contents.forEach(c => c.classList.remove('active'));

            // Aktiven Tab setzen
            tab.classList.add('active');
            const tabId = `tab-${tab.dataset.tab}`;
            document.getElementById(tabId).classList.add('active');

            // Chart aktualisieren
            switch(tab.dataset.tab) {
                case 'today':
                    updateTodayChart();
                    break;
                case 'week':
                    updateWeekChart();
                    break;
                case 'month':
                    updateMonthChart();
                    break;
            }
        });
    });
}

// ==================== Initialisierung ====================

async function init() {
    console.log('Xovis Dashboard wird initialisiert...');

    // Tabs einrichten
    setupTabs();

    // Erste Daten laden
    await updateStatus();
    await updateLiveData();
    await updateTodayChart();

    // Automatische Updates
    setInterval(updateLiveData, 10000);      // Alle 10 Sekunden
    setInterval(updateStatus, 60000);        // Jede Minute
    setInterval(updateTodayChart, 60000);    // Jede Minute

    console.log('Dashboard bereit!');
}

// Start
document.addEventListener('DOMContentLoaded', init);
