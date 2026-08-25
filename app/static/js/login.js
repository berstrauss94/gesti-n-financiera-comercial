/**
 * Login page logic.
 */
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('loginForm');
    const errorEl = document.getElementById('loginError');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        errorEl.textContent = '';

        const username = document.getElementById('username').value.trim();
        const password = document.getElementById('password').value;

        if (!username || !password) {
            errorEl.textContent = 'Complete todos los campos';
            return;
        }

        const btn = document.getElementById('loginBtn');
        btn.disabled = true;
        btn.textContent = 'Ingresando...';

        try {
            const resp = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({ username, password }),
            });

            const data = await resp.json();

            if (resp.ok) {
                window.location.href = '/dashboard';
            } else {
                const error = data.error || {};
                if (error.code === 'AUTH_ACCOUNT_LOCKED') {
                    errorEl.textContent = '🔒 Cuenta bloqueada temporalmente. Intente más tarde.';
                } else {
                    errorEl.textContent = 'Usuario o contraseña incorrectos';
                }
            }
        } catch (err) {
            errorEl.textContent = 'Error de conexión. Intente nuevamente.';
        } finally {
            btn.disabled = false;
            btn.textContent = 'Iniciar Sesión';
        }
    });
});
