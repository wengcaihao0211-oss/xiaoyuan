// Toast notifications & alerts auto-dismiss
document.addEventListener('DOMContentLoaded', function () {
    // --- Toast auto-dismiss ---
    document.querySelectorAll('.toast-item').forEach(function (toast) {
        var delay = parseInt(toast.getAttribute('data-delay')) || 6000;
        setTimeout(function () {
            toast.style.transition = 'all 0.35s ease';
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(60px) scale(0.9)';
            setTimeout(function () { toast.remove(); }, 350);
        }, delay);
    });

    // --- Backward compat: old Bootstrap alerts ---
    document.querySelectorAll('.alert-dismissible').forEach(function (alert) {
        setTimeout(function () {
            try { var bsAlert = new bootstrap.Alert(alert); bsAlert.close(); } catch (e) {}
        }, 5000);
    });

    // --- Bootstrap tooltips ---
    [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]')).forEach(function (el) {
        return new bootstrap.Tooltip(el);
    });
});
