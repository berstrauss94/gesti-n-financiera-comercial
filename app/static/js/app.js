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

            // Try to check if we have an active business by making a test call
            const sessionResp = await this.fetch('/api/auth/session');
            if (sessionResp && sessionResp.ok) {
                // We're authenticated. The active business is in session server-side.
                // Show the first business or try to get current from a heatmap call
                nameEl.textContent = businesses[0].name;
                nameEl.dataset.businessId = businesses[0].id;
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

    // Create business
    const createBusinessBtn = document.getElementById('createBusinessBtn');
    if (createBusinessBtn) {
        createBusinessBtn.addEventListener('click', async () => {
            const nameInput = document.getElementById('newBusinessName');
            const name = nameInput.value.trim();
            if (!name) return;

            const resp = await App.fetch('/api/businesses', {
                method: 'POST',
                body: JSON.stringify({ name }),
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

    list.innerHTML = businesses.map(b => `
        <div class="business-item" data-id="${b.id}">
            <span>${b.name}</span>
            <button class="btn btn-sm btn-outline" onclick="selectBusiness(${b.id}, '${b.name}')">Seleccionar</button>
        </div>
    `).join('');
}

async function selectBusiness(id, name) {
    const resp = await App.fetch(`/api/businesses/${id}/select`, { method: 'POST' });
    if (resp && resp.ok) {
        document.getElementById('activeBusinessName').textContent = name;
        document.getElementById('businessModal').classList.remove('show');
        window.location.reload();
    }
}
