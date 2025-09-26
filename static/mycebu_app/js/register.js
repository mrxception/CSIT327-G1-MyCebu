(function () {
    const password = document.getElementById('password');
    const toggleBtn = document.getElementById('togglePassword');
    const eye = document.getElementById('eye');
    const eyeOff = document.getElementById('eyeOff');

    const confirmPassword = document.getElementById('confirmPassword');
    const toggleConfirmBtn = document.getElementById('toggleConfirmPassword');
    const eye2 = document.getElementById('eye2');
    const eyeOff2 = document.getElementById('eyeOff2');

    toggleBtn.addEventListener('click', () => {
        const showing = password.type === 'text';
        password.type = showing ? 'password' : 'text';
        eye.style.display = showing ? '' : 'none';
        eyeOff.style.display = showing ? 'none' : '';
    });

    toggleConfirmBtn.addEventListener('click', () => {
        const showing = confirmPassword.type === 'text';
        confirmPassword.type = showing ? 'password' : 'text';
        eye2.style.display = showing ? '' : 'none';
        eyeOff2.style.display = showing ? 'none' : '';
    });

    document.getElementById('login-form').addEventListener('submit', function () {
        var btn = document.getElementById('submitBtn');
        btn.disabled = true;
        btn.textContent = 'Signing in...';
    });
})();