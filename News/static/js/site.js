// Мобильное меню в шапке.
(function () {
    const header = document.querySelector('[data-header]');
    const toggle = document.querySelector('[data-menu-toggle]');

    if (!header || !toggle) {
        return;
    }

    toggle.addEventListener('click', function () {
        const isOpen = header.classList.toggle('is-open');
        toggle.setAttribute('aria-expanded', String(isOpen));
    });

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && header.classList.contains('is-open')) {
            header.classList.remove('is-open');
            toggle.setAttribute('aria-expanded', 'false');
            toggle.focus();
        }
    });
})();
