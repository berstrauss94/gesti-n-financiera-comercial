/**
 * Dashboard page logic.
 */
document.addEventListener('DOMContentLoaded', () => {
    initDashboard();
});

async function initDashboard() {
    // 1) ¿Hay un negocio activo en la sesión?
    let hasActiveBusiness = false;
    try {
        const sresp = await App.fetch('/api/auth/session');
        if (sresp && sresp.ok) {
            const sdata = await sresp.json();
            hasActiveBusiness = !!(sdata.session && sdata.session.active_business);
        }
    } catch (e) { /* ignore */ }

    if (hasActiveBusiness) {
        // Caso normal: cargar datos sin interrumpir
        loadDashboardData();
        loadDashboardHeatmap();
        return;
    }

    // 2) No hay negocio activo. ¿El usuario tiene negocios creados?
    let businesses = [];
    try {
        const bresp = await App.fetch('/api/businesses');
        if (bresp && bresp.ok) {
            businesses = (await bresp.json()).businesses || [];
        }
    } catch (e) { /* ignore */ }

    if (businesses.length > 0) {
        // Tiene negocios pero ninguno activo: auto-seleccionar el primero
        // en silencio (no abrir el modal) y cargar el dashboard.
        try {
            await App.fetch(`/api/businesses/${businesses[0].id}/select`, { method: 'POST' });
            const nameEl = document.getElementById('activeBusinessName');
            if (nameEl) nameEl.textContent = businesses[0].name;
        } catch (e) { /* ignore */ }
        loadDashboardData();
        loadDashboardHeatmap();
        return;
    }

    // 3) Usuario sin ningún negocio: aquí sí tiene sentido abrir el modal
    //    para que cree el primero.
    const modal = document.getElementById('businessModal');
    if (modal) modal.classList.add('show');
}

async function loadDashboardData() {
    const fromDate = App.firstOfMonth();
    const toDate = App.today();

    try {
        const resp = await App.fetch(`/api/reports?granularity=monthly&from=${fromDate}&to=${toDate}`);

        if (!resp || !resp.ok) return;

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
        // La respuesta trae {date, gross_income, indicators:{...}}.
        // Solo las categorías dentro de "indicators" son indicadores del semáforo.
        const indicators = heatmap.indicators || {};

        let html = '';
        for (const [key, value] of Object.entries(indicators)) {
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
                    <span class="tooltip">${label}: ${pctText} del ingreso bruto del día</span>
                </div>
            `;
        }

        container.innerHTML = html || '<p class="loading-text">Sin movimientos cargados para hoy. Registra un ingreso y gastos para ver el semáforo.</p>';
    } catch (e) {
        container.innerHTML = '<p class="loading-text">Error al cargar heatmap</p>';
    }
}

function formatCategoryLabel(key) {
    const labels = {
        salarios: 'Salarios',
        retiros: 'Retiros',
        retiros_dueno: 'Retiros del Dueño',
        comisiones: 'Comisiones',
        mermas: 'Mermas',
        servicios: 'Servicios',
        insumos: 'Insumos',
        mantenimiento: 'Mantenimiento',
        impuestos_municipales: 'Imp. Municipales',
        seguros: 'Seguros',
        logistica: 'Logística',
        electricidad: 'Electricidad',
        agua: 'Agua',
        internet: 'Internet',
        monotributo: 'Monotributo',
        mercaderia: 'Mercadería',
        alquiler: 'Alquiler',
        contable: 'Contable',
        emergencia: 'Fondo de Emergencia',
        inversion: 'Inversión',
    };
    return labels[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}
