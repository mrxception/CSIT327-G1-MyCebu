(function () {
    const password = document.getElementById('password');
    const toggleBtn = document.getElementById('togglePassword');
    const eye = document.getElementById('eye');
    const eyeOff = document.getElementById('eyeOff');
    toggleBtn.addEventListener('click', () => {
        const showing = password.type === 'text';
        password.type = showing ? 'password' : 'text';
        eye.style.display = showing ? '' : 'none';
        eyeOff.style.display = showing ? 'none' : '';
    });

    document.getElementById('login-form').addEventListener('submit', function () {
        var btn = document.getElementById('submitBtn');
        btn.disabled = true;
        btn.textContent = 'Signing in...';
    });
})();