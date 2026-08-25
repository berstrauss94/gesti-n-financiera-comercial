/**
 * Expenses page logic: tabs + CRUD for salaries, withdrawals, variable expenses, operating costs.
 */
document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    initSalaryForm();
    initWithdrawalForm();
    initVariableForm();
    initOperatingForm();

    // Load initial data
    loadSalaries();
    loadWithdrawals();
    loadVariableExpenses();
    loadOperatingCosts();
});

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
        electricidad: 'Electricidad',
        monotributo: 'Monotributo',
        mercaderia: 'Mercadería',
        alquiler: 'Alquiler',
        contable: 'Contable',
    };
    return names[cat] || cat;
}
