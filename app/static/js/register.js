/**
 * Register page logic with client-side validation hints.
 */
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('registerForm');
    const errorEl = document.getElementById('registerError');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        errorEl.textContent = '';

        const username = document.getElementById('username').value.trim();
        const email = document.getElementById('email').value.trim();
        const password = document.getElementById('password').value;
        const phone = document.getElementById('phone').value.trim();

        // Client-side validation
        if (username.length < 8) {
            errorEl.textContent = 'El usuario debe tener mínimo 8 caracteres';
            return;
        }
        if (!/[A-Z]/.test(username)) {
            errorEl.textContent = 'El usuario debe contener al menos una mayúscula';
            return;
        }
        if (!email || !email.includes('@')) {
            errorEl.textContent = 'Ingrese un email válido';
            return;
        }
        if (password.length < 8) {
            errorEl.textContent = 'La contraseña debe tener mínimo 8 caracteres';
            return;
        }
        if (!/[A-Z]/.test(password)) {
            errorEl.textContent = 'La contraseña debe contener al menos una mayúscula';
            return;
        }
        if (!/[0-9]/.test(password)) {
            errorEl.textContent = 'La contraseña debe contener al menos un número';
            return;
        }
        if (phone && (phone.length < 7 || phone.length > 15 || !/^\d+$/.test(phone))) {
            errorEl.textContent = 'El teléfono debe tener entre 7 y 15 dígitos';
            return;
        }

        const btn = document.getElementById('registerBtn');
        btn.disabled = true;
        btn.textContent = 'Creando cuenta...';

        try {
            const body = { username, email, password };
            if (phone) body.phone = phone;

            const resp = await fetch('/api/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify(body),
            });

            const data = await resp.json();

            if (resp.ok) {
                // Auto-login after registration
                const loginResp = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'same-origin',
                    body: JSON.stringify({ username, password }),
                });

                if (loginResp.ok) {
                    window.location.href = '/dashboard';
                } else {
                    window.location.href = '/login';
                }
            } else {
                const error = data.error || {};
                if (error.code === 'DUPLICATE_USERNAME') {
                    errorEl.textContent = 'El nombre de usuario ya está en uso';
                } else if (error.code === 'DUPLICATE_EMAIL') {
                    errorEl.textContent = 'El email ya está registrado';
                } else {
                    errorEl.textContent = error.message || 'Error al registrar';
                }
            }
        } catch (err) {
            errorEl.textContent = 'Error de conexión. Intente nuevamente.';
        } finally {
            btn.disabled = false;
            btn.textContent = 'Crear Cuenta';
        }
    });
});
