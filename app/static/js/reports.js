/**
 * Reports page logic.
 */
document.addEventListener('DOMContentLoaded', () => {
    // Set default dates
    document.getElementById('reportFrom').value = App.firstOfMonth();
    document.getElementById('reportTo').value = App.today();

    // Report form
    document.getElementById('reportForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        await generateReport();
    });

    // Compare form
    document.getElementById('compareForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        await comparePeriods();
    });

    // Export buttons
    document.getElementById('exportCsvBtn').addEventListener('click', () => exportReport('csv'));
    document.getElementById('exportPdfBtn').addEventListener('click', () => exportReport('pdf'));
});

async function generateReport() {
    const granularity = document.getElementById('reportGranularity').value;
    const from = document.getElementById('reportFrom').value;
    const to = document.getElementById('reportTo').value;
    const filter = document.getElementById('reportFilter').value.trim();

    if (!from || !to) return;

    let url = `/api/reports?granularity=${granularity}&from=${from}&to=${to}`;
    if (filter) url += `&filter=${encodeURIComponent(filter)}`;

    try {
        const resp = await App.fetch(url);

        if (!resp || resp.status === 403) {
            alert('Seleccione un negocio primero');
            return;
        }
        if (!resp.ok) {
            const data = await resp.json();
            alert(data.error?.message || 'Error al generar reporte');
            return;
        }

        const data = await resp.json();
        const report = data.report || {};

        // Show results section
        document.getElementById('reportResults').style.display = 'block';

        // Summary
        const summary = report.summary || {};
        document.getElementById('rptIncome').textContent = App.formatMoney(summary.total_income);
        document.getElementById('rptExpenses').textContent = App.formatMoney(summary.total_expenses);
        document.getElementById('rptProfit').textContent = App.formatMoney(summary.net_profit);

        // Style profit
        const profitEl = document.getElementById('rptProfit');
        profitEl.style.color = summary.net_profit >= 0 ? 'var(--green)' : 'var(--red)';

        // Trend
        const trendMap = { up: '📈 Subiendo', down: '📉 Bajando', stable: '➡️ Estable' };
        document.getElementById('rptTrend').textContent = trendMap[report.trend] || '—';

        // Groups table
        const tbody = document.getElementById('reportTableBody');
        const groups = report.groups || [];

        if (groups.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="loading-text">Sin datos para este período</td></tr>';
        } else {
            tbody.innerHTML = groups.map(g => `
                <tr>
                    <td>${g.period}</td>
                    <td>${App.formatMoney(g.income)}</td>
                    <td>${App.formatMoney(g.total_expenses)}</td>
                    <td style="color: ${g.net_profit >= 0 ? 'var(--green)' : 'var(--red)'}">${App.formatMoney(g.net_profit)}</td>
                </tr>
            `).join('');
        }
    } catch (e) {
        console.error('Error generating report:', e);
    }
}

async function comparePeriods() {
    const p1From = document.getElementById('p1From').value;
    const p1To = document.getElementById('p1To').value;
    const p2From = document.getElementById('p2From').value;
    const p2To = document.getElementById('p2To').value;

    if (!p1From || !p1To || !p2From || !p2To) {
        alert('Complete todas las fechas');
        return;
    }

    const url = `/api/reports/compare?period1_from=${p1From}&period1_to=${p1To}&period2_from=${p2From}&period2_to=${p2To}`;

    try {
        const resp = await App.fetch(url);

        if (!resp || resp.status === 403) {
            alert('Seleccione un negocio primero');
            return;
        }
        if (!resp.ok) {
            const data = await resp.json();
            alert(data.error?.message || 'Error al comparar');
            return;
        }

        const data = await resp.json();
        const comparison = data.comparison || {};
        const metrics = comparison.metrics || {};

        // Show results
        document.getElementById('compareResults').style.display = 'block';

        const tbody = document.getElementById('compareTableBody');
        const labels = {
            total_income: 'Ingreso Total',
            total_salaries: 'Salarios',
            total_withdrawals: 'Retiros',
            total_variable_expenses: 'Gastos Variables',
            total_operating_costs: 'Costos Operativos',
            total_expenses: 'Total Gastos',
            net_profit: 'Ganancia Neta',
        };

        let html = '';
        for (const [key, values] of Object.entries(metrics)) {
            const label = labels[key] || key;
            const diffColor = values.absolute_diff >= 0 ? 'var(--green)' : 'var(--red)';
            const pctText = values.percentage_diff !== null ? `${values.percentage_diff > 0 ? '+' : ''}${values.percentage_diff}%` : 'N/A';

            html += `
                <tr>
                    <td>${label}</td>
                    <td>${App.formatMoney(values.period1)}</td>
                    <td>${App.formatMoney(values.period2)}</td>
                    <td style="color: ${diffColor}">${values.absolute_diff >= 0 ? '+' : ''}${App.formatMoney(values.absolute_diff)}</td>
                    <td style="color: ${diffColor}">${pctText}</td>
                </tr>
            `;
        }
        tbody.innerHTML = html;
    } catch (e) {
        console.error('Error comparing periods:', e);
    }
}

function exportReport(format) {
    const from = document.getElementById('reportFrom').value;
    const to = document.getElementById('reportTo').value;

    if (!from || !to) {
        alert('Seleccione un rango de fechas primero');
        return;
    }

    // Trigger download via direct navigation
    window.location.href = `/api/reports/export?format=${format}&from=${from}&to=${to}`;
}
