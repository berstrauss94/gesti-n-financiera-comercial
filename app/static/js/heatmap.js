/**
 * Heatmap page logic.
 */
document.addEventListener('DOMContentLoaded', () => {
    // Set default date to today
    document.getElementById('heatmapDate').value = App.today();

    // Load button
    document.getElementById('loadHeatmapBtn').addEventListener('click', loadHeatmap);

    // Auto-load on page open
    loadHeatmap();
});

async function loadHeatmap() {
    const date = document.getElementById('heatmapDate').value;
    if (!date) return;

    const grid = document.getElementById('heatmapGrid');
    grid.innerHTML = '<p class="loading-text">Cargando...</p>';

    try {
        const resp = await App.fetch(`/api/heatmap/daily?date=${date}`);

        if (!resp || resp.status === 403) {
            grid.innerHTML = '<p class="loading-text">Seleccione un negocio primero</p>';
            return;
        }
        if (!resp.ok) {
            grid.innerHTML = '<p class="loading-text">Sin datos para esta fecha</p>';
            return;
        }

        const data = await resp.json();
        const heatmap = data.heatmap || {};

        // Render net profit master indicator
        renderMasterIndicator(heatmap.net_profit);

        // Render category indicators
        let html = '';
        for (const [key, value] of Object.entries(heatmap)) {
            if (key === 'net_profit') continue;

            const pct = value?.percentage;
            const emoji = App.getIndicatorEmoji(pct);
            const label = formatLabel(key);
            const pctText = pct !== null && pct !== undefined ? `${parseFloat(pct).toFixed(1)}%` : 'N/A';
            const amount = value?.amount ? App.formatMoney(value.amount) : '';

            html += `
                <div class="heatmap-item">
                    <span class="indicator-emoji">${emoji}</span>
                    <div>
                        <p class="indicator-name">${label}</p>
                        <p class="indicator-pct" style="${App.getIndicatorColor(pct)}">${pctText}</p>
                    </div>
                    <span class="tooltip">${label}: ${pctText} del ingreso bruto${amount ? ' (' + amount + ')' : ''}</span>
                </div>
            `;
        }

        grid.innerHTML = html || '<p class="loading-text">Sin indicadores disponibles</p>';
    } catch (e) {
        grid.innerHTML = '<p class="loading-text">Error al cargar el heatmap</p>';
    }
}

function renderMasterIndicator(netProfit) {
    const circle = document.getElementById('masterCircle');
    const value = document.getElementById('masterValue');
    const percent = document.getElementById('masterPercent');

    if (!netProfit || netProfit.percentage === null || netProfit.percentage === undefined) {
        circle.textContent = '⚪';
        value.textContent = 'Sin datos';
        percent.textContent = '';
        return;
    }

    const pct = parseFloat(netProfit.percentage);
    // For net profit, the logic is inverted: higher profit percentage = better
    // But using the same semaphore: if expenses consume >X% of income
    circle.textContent = App.getIndicatorEmoji(100 - pct);
    value.textContent = netProfit.amount ? App.formatMoney(netProfit.amount) : '—';
    percent.textContent = `Margen: ${pct.toFixed(1)}% del ingreso`;
    percent.style = App.getIndicatorColor(100 - pct);
}

function formatLabel(key) {
    const labels = {
        salarios: 'Salarios',
        retiros: 'Retiros del Dueño',
        comisiones: 'Comisiones',
        mermas: 'Mermas',
        servicios: 'Servicios',
        insumos: 'Insumos',
        mantenimiento: 'Mantenimiento',
        impuestos_municipales: 'Impuestos Municipales',
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
