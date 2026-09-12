document.addEventListener('DOMContentLoaded', () => {
    // If already logged in, redirect to main dashboard page
    if (localStorage.getItem('auth_token')) {
        window.location.href = '/index.html';
    }

    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    
    if (loginForm) {
        loginForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const user = document.getElementById('login_username').value.trim();
            const pass = document.getElementById('login_password').value.trim();
            const errorEl = document.getElementById('loginError');
            const successEl = document.getElementById('loginSuccess');
            
            if (errorEl) errorEl.style.display = 'none';
            if (successEl) successEl.style.display = 'none';

            if (user === '' || pass === '') {
                if (errorEl) {
                    errorEl.textContent = 'Please enter both username and password.';
                    errorEl.style.display = 'block';
                }
                return;
            }

            const btn = loginForm.querySelector('.login-btn');
            const originalText = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Authenticating...';
            btn.style.pointerEvents = 'none';

            try {
                const response = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username: user, password: pass })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    localStorage.setItem('auth_token', data.token);
                    window.location.href = '/index.html';
                } else {
                    if (errorEl) {
                        errorEl.textContent = data.message || 'Login failed.';
                        errorEl.style.display = 'block';
                    }
                    btn.innerHTML = originalText;
                    btn.style.pointerEvents = 'auto';
                }
            } catch (err) {
                if (errorEl) {
                    errorEl.textContent = 'Network error. Please try again later.';
                    errorEl.style.display = 'block';
                }
                btn.innerHTML = originalText;
                btn.style.pointerEvents = 'auto';
            }
        });
    }

    if (registerForm) {
        registerForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const user = document.getElementById('register_username').value.trim();
            const pass = document.getElementById('register_password').value.trim();
            const passConfirm = document.getElementById('register_password_confirm').value.trim();
            const email = document.getElementById('register_email').value.trim();
            const fullName = document.getElementById('register_fullname').value.trim();
            
            const errorEl = document.getElementById('registerError');
            const successEl = document.getElementById('registerSuccess');
            
            if (errorEl) errorEl.style.display = 'none';
            if (successEl) successEl.style.display = 'none';

            if (pass !== passConfirm) {
                if (errorEl) {
                    errorEl.textContent = 'Passwords do not match.';
                    errorEl.style.display = 'block';
                }
                return;
            }

            const btn = registerForm.querySelector('.login-btn');
            const originalText = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating Account...';
            btn.style.pointerEvents = 'none';

            try {
                const response = await fetch('/api/auth/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        username: user, 
                        password: pass,
                        email: email || undefined,
                        full_name: fullName || undefined
                    })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    if (successEl) {
                        successEl.textContent = 'Account created successfully! You can now log in.';
                        successEl.style.display = 'block';
                    }
                    registerForm.reset();
                    
                    // Switch to login tab after 2 seconds
                    setTimeout(() => {
                        const loginTab = document.querySelector('[data-tab="login"]');
                        if (loginTab) loginTab.click();
                    }, 2000);
                } else {
                    if (errorEl) {
                        errorEl.textContent = data.message || 'Registration failed.';
                        errorEl.style.display = 'block';
                    }
                }
            } catch (err) {
                if (errorEl) {
                    errorEl.textContent = 'Network error. Please try again later.';
                    errorEl.style.display = 'block';
                }
            } finally {
                btn.innerHTML = originalText;
                btn.style.pointerEvents = 'auto';
            }
        });
    }
});
