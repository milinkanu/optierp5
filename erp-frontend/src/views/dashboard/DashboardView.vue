<template>
  <div class="zoho-dashboard">
    <!-- Welcome Header -->
    <header class="dashboard-welcome">
      <div class="welcome-left">
        <div class="avatar-large">🏢</div>
        <div class="welcome-text">
          <h1>Hello, {{ user?.name || 'Sarfraj Khan' }}</h1>
          <p>Elivya</p>
        </div>
      </div>
      <div class="welcome-right">
        <div class="helpline">
          <span>Zoho Books India Helpline: <strong>18003093036</strong></span>
          <p>Mon - Fri • 9:00 AM - 7:00 PM • Toll Free</p>
        </div>
      </div>
    </header>

    <!-- Tabs -->
    <nav class="dashboard-tabs">
      <button class="tab active">Dashboard</button>
      <button class="tab">Fiscal Year-End Tasks</button>
      <button class="tab">Getting Started <span>▼</span></button>
    </nav>

    <!-- Summary Grid -->
    <div class="summary-grid">
      <div class="stat-card">
        <div class="card-header">
          <h3>Total Receivables</h3>
          <button class="new-btn">➕ New</button>
        </div>
        <div class="card-body">
          <div class="label">Total Unpaid Invoices</div>
          <div class="value">₹5.00</div>
          <div class="progress-bar">
            <div class="progress" style="width: 100%; background: #1e88e5;"></div>
          </div>
          <div class="breakdown">
            <span class="dot blue"></span> Current: ₹5.00
            <span class="dot orange"></span> Overdue: ₹0.00
          </div>
        </div>
      </div>

      <div class="stat-card">
        <div class="card-header">
          <h3>Total Payables</h3>
          <button class="new-btn">➕ New</button>
        </div>
        <div class="card-body">
          <div class="label">Total Unpaid Bills</div>
          <div class="value">₹0.00</div>
          <div class="progress-bar">
            <div class="progress" style="width: 0%; background: #fb8c00;"></div>
          </div>
          <div class="breakdown">
            <span class="dot blue"></span> Current: ₹0.00
            <span class="dot orange"></span> Overdue: ₹0.00
          </div>
        </div>
      </div>
    </div>

    <!-- Cash Flow Section -->
    <div class="chart-section">
      <div class="section-header">
        <h3>Cash Flow</h3>
        <select class="period-select">
          <option>This Fiscal Year</option>
        </select>
      </div>
      <div class="chart-placeholder">
        <div class="chart-y-axis">
          <span>5 K</span>
          <span>4 K</span>
          <span>3 K</span>
          <span>2 K</span>
          <span>1 K</span>
          <span>0</span>
        </div>
        <div class="chart-canvas">
          <svg width="100%" height="200" viewBox="0 0 800 200">
            <polyline
              fill="none"
              stroke="#1e88e5"
              stroke-width="2"
              points="0,180 100,180 200,180 300,180 400,180 500,180 600,180 700,180 800,180"
            />
            <line x1="0" y1="180" x2="800" y2="180" stroke="#eee" />
          </svg>
        </div>
        <div class="chart-legend">
          <div class="legend-item"><span class="dot grey"></span> Cash as on 01/04/2026: <strong>₹0.00</strong></div>
          <div class="legend-item"><span class="dot green"></span> Incoming: <strong>₹0.00 (+)</strong></div>
          <div class="legend-item"><span class="dot red"></span> Outgoing: <strong>₹0.00 (-)</strong></div>
          <div class="legend-item"><span class="dot light-blue"></span> Cash as on 31/03/2027: <strong>₹0.00 (=)</strong></div>
        </div>
      </div>
    </div>

    <!-- Bottom Grid -->
    <div class="bottom-grid">
      <div class="stat-card">
        <div class="section-header">
          <h3>Income and Expense</h3>
          <select class="period-select">
            <option>This Fiscal Year</option>
          </select>
        </div>
        <div class="income-chart-placeholder">
          <!-- Placeholder for bar chart -->
          <div class="no-data">No data available for the selected period</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="section-header">
          <h3>Top Expenses</h3>
          <select class="period-select">
            <option>This Fiscal Year</option>
          </select>
        </div>
        <div class="expenses-list">
          <div class="no-data">No data available for the selected period</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useAuthStore } from '../../stores/auth'
import { storeToRefs } from 'pinia'

const auth = useAuthStore()
const { user } = storeToRefs(auth)
</script>

<style scoped>
.zoho-dashboard {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* Welcome Header */
.dashboard-welcome {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 8px;
}

.welcome-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.avatar-large {
  width: 48px;
  height: 48px;
  background: white;
  border: 1px solid #ddd;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.welcome-text h1 {
  font-size: 1.25rem;
  margin: 0;
  color: #333;
}

.welcome-text p {
  margin: 4px 0 0;
  font-size: 0.85rem;
  color: #666;
}

.helpline {
  text-align: right;
  font-size: 0.75rem;
  color: #666;
}

.helpline strong {
  color: #333;
}

.helpline p {
  margin: 2px 0 0;
  opacity: 0.7;
}

/* Tabs */
.dashboard-tabs {
  display: flex;
  gap: 24px;
  border-bottom: 1px solid #ddd;
}

.tab {
  background: none;
  border: none;
  padding: 8px 0 12px;
  font-size: 0.9rem;
  color: #666;
  cursor: pointer;
  position: relative;
}

.tab.active {
  color: #333;
  font-weight: 600;
}

.tab.active::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  width: 100%;
  height: 2px;
  background: #1e88e5;
}

/* Grid Layouts */
.summary-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.stat-card {
  background: white;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.card-header h3 {
  font-size: 0.95rem;
  margin: 0;
  color: #444;
}

.new-btn {
  background: none;
  border: none;
  color: #1e88e5;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
}

.card-body .label {
  font-size: 0.8rem;
  color: #888;
  margin-bottom: 8px;
}

.card-body .value {
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 16px;
}

.progress-bar {
  height: 8px;
  background: #f0f0f0;
  border-radius: 4px;
  margin-bottom: 16px;
  overflow: hidden;
}

.progress {
  height: 100%;
}

.breakdown {
  font-size: 0.8rem;
  color: #666;
  display: flex;
  align-items: center;
  gap: 12px;
}

.dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.dot.blue { background: #1e88e5; }
.dot.orange { background: #fb8c00; }
.dot.grey { background: #999; }
.dot.green { background: #4caf50; }
.dot.red { background: #f44336; }
.dot.light-blue { background: #03a9f4; }

/* Chart Sections */
.chart-section {
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 20px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.section-header h3 {
  font-size: 0.95rem;
  margin: 0;
}

.period-select {
  border: 1px solid #ddd;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.8rem;
  color: #666;
}

.chart-placeholder {
  display: grid;
  grid-template-columns: 50px 1fr 200px;
  gap: 20px;
  height: 250px;
}

.chart-y-axis {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  font-size: 0.75rem;
  color: #999;
  padding-bottom: 20px;
}

.chart-canvas {
  position: relative;
  border-left: 1px solid #eee;
  border-bottom: 1px solid #eee;
}

.chart-legend {
  display: flex;
  flex-direction: column;
  gap: 12px;
  justify-content: center;
}

.legend-item {
  font-size: 0.8rem;
  color: #666;
}

.bottom-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.no-data {
  height: 150px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #999;
  font-size: 0.85rem;
  font-style: italic;
  background: #fafafa;
  border-radius: 4px;
}

@media (max-width: 1024px) {
  .summary-grid, .bottom-grid {
    grid-template-columns: 1fr;
  }
  .chart-placeholder {
    grid-template-columns: 50px 1fr;
    height: auto;
  }
  .chart-legend {
    grid-column: span 2;
    flex-direction: row;
    flex-wrap: wrap;
  }
}
</style>
