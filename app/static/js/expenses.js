/**
 * Expenses page logic: tabs + CRUD for salaries, withdrawals, variable expenses, operating costs.
 */
document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    initSalaryForm();
    initWithdrawalForm();
    initVariableForm();
    initOperatingForm();

    // Poblar categorías activas según el perfil del negocio + conceptos extra
    loadCategories();

    // Ahorros y umbrales (agente)
    initSavingsForm();
    initThresholdsAgent();

    // Load initial data
    loadSalaries();
    loadWithdrawals();
    loadVariableExpenses();
    loadOperatingCosts();
    loadSavings();
    loadThresholds();
});

// === Categorías dinámicas por perfil ===
async function loadCategories() {
    try {
        const resp = await App.fetch('/api/categories');
        if (!resp || !resp.ok) return;
        const data = await resp.json();
        const active = data.active || [];
        const available = data.available || [];
        const activeKeys = new Set(active.map(c => c.key));

        // Mostrar/ocultar las pestañas de Salarios y Retiros según estén activas
        toggleTab('salarios', activeKeys.has('salarios'));
        toggleTab('retiros', activeKeys.has('retiros_dueno'));

        // Rellenar los selects de categoría con las activas de cada grupo
        fillCategorySelect('varCategory', active.filter(c => c.group === 'variable'));
        fillCategorySelect('opCategory', active.filter(c => c.group === 'operativo'));

        // Paneles para agregar/quitar conceptos
        renderConceptManager('conceptManagerVariable', 'variable', active, available);
        renderConceptManager('conceptManagerOperating', 'operativo', active, available);
        renderSpecialConceptControls(activeKeys, available);
    } catch (e) {
        // silencioso: si falla, quedan las opciones por defecto del HTML
    }
}

// Muestra u oculta una pestaña (y su contenido) por data-tab
function toggleTab(tabName, show) {
    const tabBtn = document.querySelector(`.tab[data-tab="${tabName}"]`);
    const tabContent = document.getElementById('tab-' + tabName);
    const display = show ? '' : 'none';
    if (tabBtn) tabBtn.style.display = display;
    if (tabContent && !show) tabContent.classList.remove('active');
}

function fillCategorySelect(selectId, categories) {
    const select = document.getElementById(selectId);
    if (!select) return;
    const current = select.value;
    let html = '<option value="">Seleccionar...</option>';
    categories.forEach(c => {
        html += `<option value="${c.key}">${c.label}</option>`;
    });
    select.innerHTML = html;
    if (current) select.value = current;
}

// Gestor de conceptos de un grupo: lista las activas con botón "quitar"
// y un selector para agregar las disponibles.
function renderConceptManager(containerId, group, active, available) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const activeGroup = active.filter(c => c.group === group);
    const availGroup = available.filter(c => c.group === group);

    let html = '<div class="concept-manager">';

    // Chips de categorías activas con botón quitar
    html += '<div class="concept-chips">';
    if (activeGroup.length === 0) {
        html += '<small class="form-hint">No hay conceptos activos en este grupo.</small>';
    } else {
        activeGroup.forEach(c => {
            html += `<span class="concept-chip">${c.label}`
                + `<button class="concept-remove" type="button" data-cat="${c.key}" title="Quitar concepto">✕</button></span>`;
        });
    }
    html += '</div>';

    // Selector para agregar
    if (availGroup.length > 0) {
        html += '<div class="add-concept-row" style="margin-top:0.6rem;">'
            + '<select class="input-field add-concept-select"><option value="">+ Agregar concepto...</option>';
        availGroup.forEach(c => { html += `<option value="${c.key}">${c.label}</option>`; });
        html += '</select><button class="btn btn-outline btn-sm add-concept-btn" type="button">Agregar</button></div>';
    }
    html += '</div>';
    container.innerHTML = html;

    // Handlers de quitar
    container.querySelectorAll('.concept-remove').forEach(btn => {
        btn.addEventListener('click', () => removeConcept(btn.dataset.cat));
    });
    // Handler de agregar
    const addBtn = container.querySelector('.add-concept-btn');
    if (addBtn) {
        addBtn.addEventListener('click', () => {
            const sel = container.querySelector('.add-concept-select');
            if (sel && sel.value) addConcept(sel.value);
        });
    }
}

// Controles para Salarios y Retiros (que no son categorías de gasto variable/operativo)
function renderSpecialConceptControls(activeKeys, available) {
    const container = document.getElementById('specialConcepts');
    if (!container) return;

    const specials = [
        { key: 'salarios', label: 'Salarios de empleados' },
        { key: 'retiros_dueno', label: 'Retiros del dueño' },
    ];

    let html = '<div class="concept-chips">';
    specials.forEach(s => {
        if (activeKeys.has(s.key)) {
            html += `<span class="concept-chip">${s.label}`
                + `<button class="concept-remove" type="button" data-cat="${s.key}" title="Quitar">✕</button></span>`;
        } else {
            html += `<button class="btn btn-outline btn-sm" type="button" data-add="${s.key}" style="margin-right:0.4rem;">+ ${s.label}</button>`;
        }
    });
    html += '</div>';
    container.innerHTML = html;

    container.querySelectorAll('.concept-remove').forEach(btn => {
        btn.addEventListener('click', () => removeConcept(btn.dataset.cat));
    });
    container.querySelectorAll('[data-add]').forEach(btn => {
        btn.addEventListener('click', () => addConcept(btn.dataset.add));
    });
}

async function addConcept(category) {
    if (!category) return;
    const resp = await App.fetch('/api/categories', {
        method: 'POST',
        body: JSON.stringify({ category }),
    });
    if (resp && (resp.ok || resp.status === 200)) {
        loadCategories();
    }
}

async function removeConcept(category) {
    if (!category) return;
    const resp = await App.fetch(`/api/categories/${category}`, { method: 'DELETE' });
    if (resp && resp.ok) {
        loadCategories();
    }
}

// === Tabs ===
function initTabs() {
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

            tab.classList.add('active');
            const target = document.getElementById('tab-' + tab.dataset.tab);
            if (target) target.classList.add('active');
        });
    });
}

// === Salaries ===
function initSalaryForm() {
    document.getElementById('salaryForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        App.clearMessages('salaryError', 'salarySuccess');

        const body = {
            employee_name: document.getElementById('salEmployeeName').value.trim(),
            amount: parseFloat(document.getElementById('salAmount').value),
            period_start: document.getElementById('salPeriodStart').value,
            period_end: document.getElementById('salPeriodEnd').value,
        };

        if (!body.employee_name || !body.amount || !body.period_start || !body.period_end) {
            App.showError('salaryError', 'Complete todos los campos');
            return;
        }

        try {
            const resp = await App.fetch('/api/salaries', {
                method: 'POST',
                body: JSON.stringify(body),
            });
            if (!resp) return;
            const data = await resp.json();

            if (resp.ok) {
                App.showSuccess('salarySuccess', '✓ Salario registrado');
                document.getElementById('salaryForm').reset();
                loadSalaries();
            } else {
                App.showError('salaryError', data.error?.message || 'Error');
            }
        } catch (err) {
            App.showError('salaryError', 'Error de conexión');
        }
    });
}

async function loadSalaries() {
    const tbody = document.getElementById('salaryTableBody');
    try {
        const resp = await App.fetch('/api/salaries');
        if (!resp || resp.status === 403) {
            tbody.innerHTML = '<tr><td colspan="3" class="loading-text">Seleccione un negocio</td></tr>';
            return;
        }
        if (!resp.ok) { tbody.innerHTML = '<tr><td colspan="3" class="loading-text">Error</td></tr>'; return; }

        const data = await resp.json();
        const items = data.salaries || [];

        if (items.length === 0) {
            tbody.innerHTML = '<tr><td colspan="3" class="loading-text">Sin salarios registrados</td></tr>';
            return;
        }

        tbody.innerHTML = items.map(s => `
            <tr>
                <td>${s.employee_name}</td>
                <td>${App.formatMoney(s.amount)}</td>
                <td>${s.period_start} → ${s.period_end}</td>
            </tr>
        `).join('');
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="3" class="loading-text">Error de conexión</td></tr>';
    }
}

// === Withdrawals ===
function initWithdrawalForm() {
    document.getElementById('withdrawalForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        App.clearMessages('withdrawalError', 'withdrawalSuccess');

        const body = {
            date: document.getElementById('wdDate').value,
            amount: parseFloat(document.getElementById('wdAmount').value),
        };
        const desc = document.getElementById('wdDescription').value.trim();
        if (desc) body.description = desc;

        if (!body.date || !body.amount) {
            App.showError('withdrawalError', 'La fecha y monto son requeridos');
            return;
        }

        try {
            const resp = await App.fetch('/api/withdrawals', {
                method: 'POST',
                body: JSON.stringify(body),
            });
            if (!resp) return;
            const data = await resp.json();

            if (resp.ok) {
                App.showSuccess('withdrawalSuccess', '✓ Retiro registrado');
                document.getElementById('withdrawalForm').reset();
                loadWithdrawals();
            } else {
                App.showError('withdrawalError', data.error?.message || 'Error');
            }
        } catch (err) {
            App.showError('withdrawalError', 'Error de conexión');
        }
    });
}

async function loadWithdrawals() {
    const tbody = document.getElementById('withdrawalTableBody');
    try {
        const resp = await App.fetch('/api/withdrawals');
        if (!resp || resp.status === 403) {
            tbody.innerHTML = '<tr><td colspan="3" class="loading-text">Seleccione un negocio</td></tr>';
            return;
        }
        if (!resp.ok) { tbody.innerHTML = '<tr><td colspan="3" class="loading-text">Error</td></tr>'; return; }

        const data = await resp.json();
        const items = data.withdrawals || [];

        if (items.length === 0) {
            tbody.innerHTML = '<tr><td colspan="3" class="loading-text">Sin retiros registrados</td></tr>';
            return;
        }

        tbody.innerHTML = items.map(w => `
            <tr>
                <td>${w.date}</td>
                <td>${App.formatMoney(w.amount)}</td>
                <td>${w.description || '—'}</td>
            </tr>
        `).join('');
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="3" class="loading-text">Error de conexión</td></tr>';
    }
}

// === Variable Expenses ===
function initVariableForm() {
    document.getElementById('variableForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        App.clearMessages('variableError', 'variableSuccess');

        const body = {
            category: document.getElementById('varCategory').value,
            amount: parseFloat(document.getElementById('varAmount').value),
            date: document.getElementById('varDate').value,
        };
        const desc = document.getElementById('varDescription').value.trim();
        if (desc) body.description = desc;

        if (!body.category || !body.amount || !body.date) {
            App.showError('variableError', 'Complete categoría, monto y fecha');
            return;
        }

        try {
            const resp = await App.fetch('/api/variable-expenses', {
                method: 'POST',
                body: JSON.stringify(body),
            });
            if (!resp) return;
            const data = await resp.json();

            if (resp.ok) {
                App.showSuccess('variableSuccess', '✓ Gasto variable registrado');
                document.getElementById('variableForm').reset();
                loadVariableExpenses();
            } else {
                App.showError('variableError', data.error?.message || 'Error');
            }
        } catch (err) {
            App.showError('variableError', 'Error de conexión');
        }
    });
}

async function loadVariableExpenses() {
    const tbody = document.getElementById('variableTableBody');
    try {
        const resp = await App.fetch('/api/variable-expenses');
        if (!resp || resp.status === 403) {
            tbody.innerHTML = '<tr><td colspan="4" class="loading-text">Seleccione un negocio</td></tr>';
            return;
        }
        if (!resp.ok) { tbody.innerHTML = '<tr><td colspan="4" class="loading-text">Error</td></tr>'; return; }

        const data = await resp.json();
        const items = data.variable_expenses || [];

        if (items.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="loading-text">Sin gastos variables</td></tr>';
            return;
        }

        tbody.innerHTML = items.map(v => `
            <tr>
                <td>${v.date}</td>
                <td>${formatCategoryName(v.category)}</td>
                <td>${App.formatMoney(v.amount)}</td>
                <td>${v.description || '—'}</td>
            </tr>
        `).join('');
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="4" class="loading-text">Error de conexión</td></tr>';
    }
}

// === Operating Costs ===
function initOperatingForm() {
    document.getElementById('operatingForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        App.clearMessages('operatingError', 'operatingSuccess');

        const body = {
            category: document.getElementById('opCategory').value,
            amount: parseFloat(document.getElementById('opAmount').value),
            month: document.getElementById('opMonth').value,
        };
        const desc = document.getElementById('opDescription').value.trim();
        if (desc) body.description = desc;

        if (!body.category || !body.amount || !body.month) {
            App.showError('operatingError', 'Complete categoría, monto y mes');
            return;
        }

        try {
            const resp = await App.fetch('/api/operating-costs', {
                method: 'POST',
                body: JSON.stringify(body),
            });
            if (!resp) return;
            const data = await resp.json();

            if (resp.ok) {
                App.showSuccess('operatingSuccess', '✓ Costo operativo registrado');
                document.getElementById('operatingForm').reset();
                loadOperatingCosts();
            } else {
                App.showError('operatingError', data.error?.message || 'Error');
            }
        } catch (err) {
            App.showError('operatingError', 'Error de conexión');
        }
    });
}

async function loadOperatingCosts() {
    const tbody = document.getElementById('operatingTableBody');
    try {
        const resp = await App.fetch('/api/operating-costs');
        if (!resp || resp.status === 403) {
            tbody.innerHTML = '<tr><td colspan="4" class="loading-text">Seleccione un negocio</td></tr>';
            return;
        }
        if (!resp.ok) { tbody.innerHTML = '<tr><td colspan="4" class="loading-text">Error</td></tr>'; return; }

        const data = await resp.json();
        const items = data.operating_costs || [];

        if (items.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="loading-text">Sin costos operativos</td></tr>';
            return;
        }

        tbody.innerHTML = items.map(o => `
            <tr>
                <td>${o.month}</td>
                <td>${formatCategoryName(o.category)}</td>
                <td>${App.formatMoney(o.amount)}</td>
                <td>${o.description || '—'}</td>
            </tr>
        `).join('');
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="4" class="loading-text">Error de conexión</td></tr>';
    }
}

// === Ahorros (emergencia / inversión) ===
function initSavingsForm() {
    const form = document.getElementById('savingsForm');
    if (!form) return;
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        App.clearMessages('savingsError', 'savingsSuccess');
        const body = {
            kind: document.getElementById('savKind').value,
            amount: parseFloat(document.getElementById('savAmount').value),
            date: document.getElementById('savDate').value,
        };
        const desc = document.getElementById('savDescription').value.trim();
        if (desc) body.description = desc;
        if (!body.kind || !body.amount || !body.date) {
            App.showError('savingsError', 'Complete tipo, monto y fecha');
            return;
        }
        try {
            const resp = await App.fetch('/api/savings', { method: 'POST', body: JSON.stringify(body) });
            if (!resp) return;
            const data = await resp.json();
            if (resp.ok) {
                App.showSuccess('savingsSuccess', '✓ Ahorro registrado');
                form.reset();
                loadSavings();
            } else {
                App.showError('savingsError', data.error?.message || 'Error');
            }
        } catch (err) {
            App.showError('savingsError', 'Error de conexión');
        }
    });
}

async function loadSavings() {
    const tbody = document.getElementById('savingsTableBody');
    if (!tbody) return;
    try {
        const resp = await App.fetch('/api/savings');
        if (!resp || resp.status === 403) {
            tbody.innerHTML = '<tr><td colspan="4" class="loading-text">Seleccione un negocio</td></tr>';
            return;
        }
        if (!resp.ok) { tbody.innerHTML = '<tr><td colspan="4" class="loading-text">Error</td></tr>'; return; }
        const data = await resp.json();
        const items = data.savings || [];
        if (items.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="loading-text">Sin ahorros registrados</td></tr>';
            return;
        }
        const kindLabel = { emergencia: 'Fondo de Emergencia', inversion: 'Inversión' };
        tbody.innerHTML = items.map(s => `
            <tr>
                <td>${s.date}</td>
                <td>${kindLabel[s.kind] || s.kind}</td>
                <td>${App.formatMoney(s.amount)}</td>
                <td>${s.description || '—'}</td>
            </tr>
        `).join('');
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="4" class="loading-text">Error de conexión</td></tr>';
    }
}

// === Umbrales (agente de recomendación + edición manual) ===
function initThresholdsAgent() {
    const btn = document.getElementById('applyRecommendBtn');
    if (!btn) return;
    btn.addEventListener('click', async () => {
        const resp = await App.fetch('/api/savings/recommend/apply', { method: 'POST', body: JSON.stringify({}) });
        if (resp && resp.ok) {
            const data = await resp.json();
            App.showSuccess('recommendSuccess', `✓ ${data.message}`);
            loadThresholds();
        }
    });
}

async function loadThresholds() {
    const tbody = document.getElementById('thresholdsTableBody');
    if (!tbody) return;
    try {
        const resp = await App.fetch('/api/savings/thresholds');
        if (!resp || resp.status === 403) {
            tbody.innerHTML = '<tr><td colspan="7" class="loading-text">Seleccione un negocio</td></tr>';
            return;
        }
        if (!resp.ok) { tbody.innerHTML = '<tr><td colspan="7" class="loading-text">Error</td></tr>'; return; }
        const data = await resp.json();
        const items = (data.thresholds || []).filter(t => t.category !== 'ganancia_neta');
        if (items.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="loading-text">Sin umbrales</td></tr>';
            return;
        }
        tbody.innerHTML = items.map(t => `
            <tr data-cat="${t.category}">
                <td>${t.label}${t.inverted ? ' 🔼' : ''}${t.is_custom ? ' <small style="color:var(--accent-blue)">(custom)</small>' : ''}</td>
                <td><input type="number" step="0.01" class="th-input" data-f="green" value="${t.green_max}" style="width:70px"></td>
                <td><input type="number" step="0.01" class="th-input" data-f="yellow" value="${t.yellow_max}" style="width:70px"></td>
                <td><input type="number" step="0.01" class="th-input" data-f="orange" value="${t.orange_max}" style="width:70px"></td>
                <td><input type="number" step="0.01" class="th-input" data-f="red" value="${t.red_max}" style="width:70px"></td>
                <td>${t.has_recommendation === false ? '—' : '✓'}</td>
                <td><button class="btn btn-outline btn-sm th-save" type="button">Guardar</button></td>
            </tr>
        `).join('');

        tbody.querySelectorAll('.th-save').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const row = e.target.closest('tr');
                const cat = row.dataset.cat;
                const vals = {};
                row.querySelectorAll('.th-input').forEach(inp => {
                    vals[inp.dataset.f + '_max'] = parseFloat(inp.value);
                });
                const resp = await App.fetch(`/api/savings/thresholds/${cat}`, {
                    method: 'PUT', body: JSON.stringify(vals),
                });
                if (resp && resp.ok) loadThresholds();
            });
        });
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="7" class="loading-text">Error de conexión</td></tr>';
    }
}

// === Helpers ===
function formatCategoryName(cat) {
    const names = {
        comisiones: 'Comisiones',
        mermas: 'Mermas',
        servicios: 'Servicios',
        insumos: 'Insumos',
        mantenimiento: 'Mantenimiento',
        impuestos_municipales: 'Imp. Municipales',
        seguros: 'Seguros',
        logistica: 'Logística',
        emergencia: 'Fondo de Emergencia',
        inversion: 'Inversión',
        electricidad: 'Electricidad',
        agua: 'Agua',
        internet: 'Internet',
        monotributo: 'Monotributo',
        mercaderia: 'Mercadería',
        alquiler: 'Alquiler',
        contable: 'Contable',
    };
    return names[cat] || cat;
}
