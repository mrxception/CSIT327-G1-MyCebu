(function () {
    const form = document.getElementById('login-form');
    const email = document.getElementById('email');
    const password = document.getElementById('password');
    const emailErr = document.getElementById('email-error');
    const passErr = document.getElementById('password-error');
    const submitBtn = document.getElementById('submitBtn');

    const toggleBtn = document.getElementById('togglePassword');
    const eye = document.getElementById('eye');
    const eyeOff = document.getElementById('eyeOff');
    toggleBtn.addEventListener('click', () => {
        const showing = password.type === 'text';
        password.type = showing ? 'password' : 'text';
        eye.style.display = showing ? '' : 'none';
        eyeOff.style.display = showing ? 'none' : '';
    });

    function validate() {
        let ok = true;
        if (!email.value || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value)) {
            emailErr.hidden = false; ok = false;
        } else emailErr.hidden = true;


        if (!password.value) {
            passErr.hidden = false; ok = false;
        } else passErr.hidden = true;
        return ok;
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!validate()) return;
        const original = submitBtn.textContent;
        submitBtn.textContent = 'Signing in...';
        submitBtn.disabled = true;


        try {
            await new Promise(r => setTimeout(r, 1200));
            window.location.href = '/dashboard';
        } catch (err) {
            alert('Something went wrong.');
        } finally {
            submitBtn.textContent = original;
            submitBtn.disabled = false;
        }
    });
})();