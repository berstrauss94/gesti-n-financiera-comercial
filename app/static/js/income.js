/**
 * Income page logic.
 */
document.addEventListener('DOMContentLoaded', () => {
    // Set default date to today
    document.getElementById('incomeDate').value = App.today();

    // Load existing incomes
    loadIncomes();

    // Form submit
    document.getElementById('incomeForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        App.clearMessages('incomeError', 'incomeSuccess');

        const date = document.getElementById('incomeDate').value;
        const amount = document.getElementById('incomeAmount').value;
        const notes = document.getElementById('incomeNotes').value.trim();

        if (!date || !amount) {
            App.showError('incomeError', 'La fecha y el monto son requeridos');
            return;
        }

        const body = { date, amount: parseFloat(amount) };
        if (notes) body.notes = notes;

        try {
            const resp = await App.fetch('/api/income', {
                method: 'POST',
                body: JSON.stringify(body),
            });

            if (!resp) return;

            const data = await resp.json();

            if (resp.ok) {
                App.showSuccess('incomeSuccess', '✓ Ingreso registrado exitosamente');
                document.getElementById('incomeAmount').value = '';
                document.getElementById('incomeNotes').value = '';
                loadIncomes();
            } else {
                const error = data.error || {};
                if (error.code === 'INCOME_DUPLICATE_DATE') {
                    App.showError('incomeError', '⚠️ Ya existe un ingreso para esta fecha. Cambie la fecha o edite el existente.');
                } else if (error.code === 'BUSINESS_NOT_SELECTED') {
                    App.showError('incomeError', 'Debe seleccionar un negocio primero');
                } else {
                    App.showError('incomeError', error.message || 'Error al registrar');
                }
            }
        } catch (err) {
            App.showError('incomeError', 'Error de conexión');
        }
    });
});

async function loadIncomes() {
    const tbody = document.getElementById('incomeTableBody');

    try {
        const resp = await App.fetch('/api/income');
        if (!resp || resp.status === 403) {
            tbody.innerHTML = '<tr><td colspan="3" class="loading-text">Seleccione un negocio primero</td></tr>';
            return;
        }
        if (!resp.ok) {
            tbody.innerHTML = '<tr><td colspan="3" class="loading-text">Error al cargar</td></tr>';
            return;
        }

        const data = await resp.json();
        const incomes = data.incomes || [];

        if (incomes.length === 0) {
            tbody.innerHTML = '<tr><td colspan="3" class="loading-text">No hay ingresos registrados</td></tr>';
            return;
        }

        tbody.innerHTML = incomes.map(i => `
            <tr>
                <td>${i.date}</td>
                <td>${App.formatMoney(i.amount)}</td>
                <td>${i.notes || '—'}</td>
            </tr>
        `).join('');
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="3" class="loading-text">Error de conexión</td></tr>';
    }
}
