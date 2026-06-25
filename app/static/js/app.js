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

    // --- Fav dot: click to hide ---
    var favDot = document.getElementById('favDot');
    var favLink = document.getElementById('favLink');
    if (favDot && favLink) {
        // hide if already viewed this session
        if (sessionStorage.getItem('favViewed') === '1') {
            favDot.style.display = 'none';
        }
        favLink.addEventListener('click', function () {
            sessionStorage.setItem('favViewed', '1');
            favDot.style.display = 'none';
        });
    }

    // --- Mobile navbar: collapse on navigation click, but keep dropdown toggles open ---
    document.querySelectorAll('#navbarNav .nav-link, #navbarNav .dropdown-item').forEach(function (link) {
        link.addEventListener('click', function (event) {
            var nav = document.getElementById('navbarNav');
            var isDropdownToggle = event.currentTarget.matches('[data-bs-toggle="dropdown"], .dropdown-toggle');

            if (isDropdownToggle) {
                return;
            }

            if (nav && nav.classList.contains('show')) {
                setTimeout(function () {
                    var bsCollapse = bootstrap.Collapse.getInstance(nav);
                    if (bsCollapse) {
                        bsCollapse.hide();
                    }
                }, 150);
            }
        });
    });

    // --- Bootstrap tooltips ---
    [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]')).forEach(function (el) {
        return new bootstrap.Tooltip(el);
    });
});
