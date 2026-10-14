/**
 * Shared utilities for the FinanzApp frontend.
 */

const App = {
    /**
     * Make an authenticated API request.
     */
    async fetch(url, options = {}) {
        const defaults = {
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
        };
        const config = { ...defaults, ...options };
        if (options.headers) {
            config.headers = { ...defaults.headers, ...options.headers };
        }

        const response = await fetch(url, config);

        // Handle session expiration
        if (response.status === 401) {
            const data = await response.json().catch(() => ({}));
            if (data.error && data.error.code === 'AUTH_SESSION_EXPIRED') {
                window.location.href = '/login';
                return null;
            }
        }

        return response;
    },

    /**
     * Format a number as currency.
     */
    formatMoney(amount) {
        const num = parseFloat(amount) || 0;
        return '$' + num.toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    },

    /**
     * Get today's date in YYYY-MM-DD format.
     */
    today() {
        return new Date().toISOString().split('T')[0];
    },

    /**
     * Get first day of current month in YYYY-MM-DD format.
     */
    firstOfMonth() {
        const now = new Date();
        return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-01`;
    },

    /**
     * Show an error message in an element.
     */
    showError(elementId, message) {
        const el = document.getElementById(elementId);
        if (el) {
            el.textContent = message;
            el.style.display = 'block';
        }
    },

    /**
     * Show a success message in an element.
     */
    showSuccess(elementId, message) {
        const el = document.getElementById(elementId);
        if (el) {
            el.textContent = message;
            el.style.display = 'block';
            setTimeout(() => { el.textContent = ''; }, 4000);
        }
    },

    /**
     * Clear error/success messages.
     */
    clearMessages(...ids) {
        ids.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.textContent = '';
        });
    },

    /**
     * Get heatmap emoji for a percentage value.
     */
    getIndicatorEmoji(percentage) {
        if (percentage === null || percentage === undefined) return '⚪';
        const pct = parseFloat(percentage);
        if (pct > 100) return '🚨';
        if (pct > 85) return '🔴';
        if (pct > 70) return '🟠';
        if (pct > 50) return '🟡';
        return '🟢';
    },

    /**
     * Get CSS color class for a percentage.
     */
    getIndicatorColor(percentage) {
        if (percentage === null || percentage === undefined) return '';
        const pct = parseFloat(percentage);
        if (pct > 100) return 'color: var(--critical)';
        if (pct > 85) return 'color: var(--red)';
        if (pct > 70) return 'color: var(--orange)';
        if (pct > 50) return 'color: var(--yellow)';
        return 'color: var(--green)';
    },

    /**
     * Load and display the active business name in the sidebar.
     */
    async loadActiveBusiness() {
        const nameEl = document.getElementById('activeBusinessName');
        if (!nameEl) return;

        try {
            const resp = await this.fetch('/api/businesses');
            if (!resp || !resp.ok) {
                nameEl.textContent = 'Sin negocio';
                return;
            }
            const data = await resp.json();
            const businesses = data.businesses || [];

            if (businesses.length === 0) {
                nameEl.textContent = 'Crear negocio →';
                return;
            }

            // Mostrar el negocio ACTIVO real de la sesión (no siempre el primero)
            const sessionResp = await this.fetch('/api/auth/session');
            if (sessionResp && sessionResp.ok) {
                const sdata = await sessionResp.json();
                const active = sdata.session && sdata.session.active_business;
                if (active) {
                    nameEl.textContent = active.name;
                    nameEl.dataset.businessId = active.id;
                } else {
                    // Autenticado pero sin negocio activo: invitar a seleccionar
                    nameEl.textContent = 'Seleccionar negocio →';
                }
            }
        } catch (e) {
            nameEl.textContent = 'Error';
        }
    }
};

// === Sidebar Toggle ===
document.addEventListener('DOMContentLoaded', () => {
    const sidebar = document.getElementById('sidebar');
    const hamburger = document.getElementById('hamburgerBtn');
    const sidebarToggle = document.getElementById('sidebarToggle');

    if (hamburger && sidebar) {
        hamburger.addEventListener('click', () => {
            sidebar.classList.add('open');
        });
    }
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', () => {
            sidebar.classList.remove('open');
        });
    }

    // Logout
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async () => {
            await App.fetch('/api/auth/logout', { method: 'POST' });
            window.location.href = '/login';
        });
    }

    // Business selector
    const sidebarBusiness = document.getElementById('sidebarBusiness');
    const businessModal = document.getElementById('businessModal');
    const closeBusinessModal = document.getElementById('closeBusinessModal');

    if (sidebarBusiness && businessModal) {
        sidebarBusiness.addEventListener('click', () => {
            businessModal.classList.add('show');
            loadBusinessList();
        });
    }
    if (closeBusinessModal && businessModal) {
        closeBusinessModal.addEventListener('click', () => {
            businessModal.classList.remove('show');
        });
    }

    // Pista según el tipo de negocio elegido
    const typeSelect = document.getElementById('newBusinessType');
    const typeHint = document.getElementById('businessTypeHint');
    const TYPE_HINTS = {
        comercio: 'Comercio: salarios, mercadería, 8 gastos variables y costos operativos completos.',
        hogar: 'Hogar: alquiler, servicios, supermercado, seguros, salud e impuestos. Sin salarios ni comisiones.',
        expansion: 'Expansión: set completo con foco en logística e inversión.',
        servicios: 'Servicios: honorarios, servicios, insumos e impuestos. Sin mercadería ni mermas.',
    };
    if (typeSelect && typeHint) {
        typeSelect.addEventListener('change', () => {
            typeHint.textContent = TYPE_HINTS[typeSelect.value] || '';
        });
    }

    // Create business
    const createBusinessBtn = document.getElementById('createBusinessBtn');
    if (createBusinessBtn) {
        createBusinessBtn.addEventListener('click', async () => {
            const nameInput = document.getElementById('newBusinessName');
            const name = nameInput.value.trim();
            if (!name) return;
            const businessType = typeSelect ? typeSelect.value : 'comercio';

            const resp = await App.fetch('/api/businesses', {
                method: 'POST',
                body: JSON.stringify({ name, business_type: businessType }),
            });
            if (resp && resp.ok) {
                const data = await resp.json();
                nameInput.value = '';
                // Select the new business
                await App.fetch(`/api/businesses/${data.business.id}/select`, { method: 'POST' });
                document.getElementById('activeBusinessName').textContent = data.business.name;
                businessModal.classList.remove('show');
                window.location.reload();
            }
        });
    }

    // Load active business on page load
    App.loadActiveBusiness();
});

async function loadBusinessList() {
    const list = document.getElementById('businessList');
    if (!list) return;

    list.innerHTML = '<p class="loading-text">Cargando...</p>';

    const resp = await App.fetch('/api/businesses');
    if (!resp || !resp.ok) {
        list.innerHTML = '<p>Error al cargar negocios</p>';
        return;
    }

    const data = await resp.json();
    const businesses = data.businesses || [];

    if (businesses.length === 0) {
        list.innerHTML = '<p class="loading-text">No hay negocios registrados</p>';
        return;
    }

    const TYPE_LABELS = {
        comercio: 'Comercio', hogar: 'Hogar', expansion: 'Expansión', servicios: 'Servicios',
    };
    const typeOptions = (sel) => Object.entries(TYPE_LABELS)
        .map(([v, l]) => `<option value="${v}" ${v === sel ? 'selected' : ''}>${l}</option>`).join('');

    list.innerHTML = businesses.map(b => `
        <div class="business-item" data-id="${b.id}">
            <div style="flex:1;min-width:0;">
                <span>${b.name} <small style="color:var(--text-muted)">(${TYPE_LABELS[b.business_type] || b.business_type || 'Comercio'})</small></span>
                <div class="edit-type-row" id="editType-${b.id}" style="display:none;margin-top:0.4rem;gap:0.4rem;align-items:center;">
                    <select class="input-field edit-type-select" style="padding:0.4rem;">${typeOptions(b.business_type)}</select>
                    <button class="btn btn-sm btn-primary" onclick="saveBusinessType(${b.id})">Guardar</button>
                </div>
            </div>
            <div style="display:flex;gap:0.4rem;">
                <button class="btn btn-sm btn-outline" onclick="toggleEditType(${b.id})" title="Cambiar tipo de negocio">⚙️</button>
                <button class="btn btn-sm btn-outline" onclick="selectBusiness(${b.id}, '${b.name.replace(/'/g, "\\'")}')">Seleccionar</button>
            </div>
        </div>
    `).join('');
}

function toggleEditType(id) {
    const row = document.getElementById(`editType-${id}`);
    if (row) row.style.display = row.style.display === 'none' ? 'flex' : 'none';
}

async function saveBusinessType(id) {
    const row = document.getElementById(`editType-${id}`);
    const select = row ? row.querySelector('.edit-type-select') : null;
    if (!select) return;
    const resp = await App.fetch(`/api/businesses/${id}`, {
        method: 'PUT',
        body: JSON.stringify({ business_type: select.value }),
    });
    if (resp && resp.ok) {
        await loadBusinessList();
        // Si es el negocio activo, recargar para refrescar categorías/semáforo
        window.location.reload();
    }
}

async function selectBusiness(id, name) {
    const resp = await App.fetch(`/api/businesses/${id}/select`, { method: 'POST' });
    if (resp && resp.ok) {
        document.getElementById('activeBusinessName').textContent = name;
        document.getElementById('businessModal').classList.remove('show');
        window.location.reload();
    }
}
