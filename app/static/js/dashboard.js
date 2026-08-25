/**
 * Dashboard page logic.
 */
document.addEventListener('DOMContentLoaded', () => {
    loadDashboardData();
    loadDashboardHeatmap();
});

async function loadDashboardData() {
    const fromDate = App.firstOfMonth();
    const toDate = App.today();

    try {
        const resp = await App.fetch(`/api/reports?granularity=monthly&from=${fromDate}&to=${toDate}`);

        if (!resp || resp.status === 403) {
            // No business selected - show modal
            const modal = document.getElementById('businessModal');
            if (modal) modal.classList.add('show');
            return;
        }

        if (!resp.ok) return;

        const data = await resp.json();
        const summary = data.report?.summary || {};

        document.getElementById('totalIncome').textContent = App.formatMoney(summary.total_income);
        document.getElementById('netProfit').textContent = App.formatMoney(summary.net_profit);
        document.getElementById('totalExpenses').textContent = App.formatMoney(summary.total_expenses);

        // Color the net profit based on positive/negative
        const profitEl = document.getElementById('netProfit');
        if (summary.net_profit < 0) {
            profitEl.style.color = 'var(--red)';
        } else {
            profitEl.style.color = 'var(--green)';
        }
    } catch (e) {
        console.error('Error loading dashboard data:', e);
    }
}

async function loadDashboardHeatmap() {
    const container = document.getElementById('dashboardHeatmap');
    if (!container) return;

    try {
        const resp = await App.fetch(`/api/heatmap/daily?date=${App.today()}`);

        if (!resp || resp.status === 403) {
            container.innerHTML = '<p class="loading-text">Seleccione un negocio primero</p>';
            return;
        }

        if (!resp.ok) {
            container.innerHTML = '<p class="loading-text">Sin datos para hoy</p>';
            return;
        }

        const data = await resp.json();
        const heatmap = data.heatmap || {};

        let html = '';
        for (const [key, value] of Object.entries(heatmap)) {
            if (key === 'net_profit') continue;
            const pct = value?.percentage;
            const emoji = App.getIndicatorEmoji(pct);
            const label = formatCategoryLabel(key);
            const pctText = pct !== null && pct !== undefined ? `${parseFloat(pct).toFixed(1)}%` : 'N/A';

            html += `
                <div class="heatmap-item">
                    <span class="indicator-emoji">${emoji}</span>
                    <div>
                        <p class="indicator-name">${label}</p>
                        <p class="indicator-pct" style="${App.getIndicatorColor(pct)}">${pctText}</p>
                    </div>
                    <span class="tooltip">${label}: ${pctText} del ingreso</span>
                </div>
            `;
        }

        container.innerHTML = html || '<p class="loading-text">Sin indicadores disponibles</p>';
    } catch (e) {
        container.innerHTML = '<p class="loading-text">Error al cargar heatmap</p>';
    }
}

function formatCategoryLabel(key) {
    const labels = {
        salarios: 'Salarios',
        retiros: 'Retiros',
        comisiones: 'Comisiones',
        mermas: 'Mermas',
        servicios: 'Servicios',
        insumos: 'Insumos',
        mantenimiento: 'Mantenimiento',
        impuestos_municipales: 'Imp. Municipales',
        seguros: 'Seguros',
        logistica: 'Logística',
        electricidad: 'Electricidad',
        monotributo: 'Monotributo',
        mercaderia: 'Mercadería',
        alquiler: 'Alquiler',
        contable: 'Contable',
    };
    return labels[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}
