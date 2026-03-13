/**
 * dzpokerV3/static/nav-ui.js
 * 导航栏主题/UI 快捷切换下拉
 */
(function() {
    var switcher = document.getElementById('nav-ui-switcher');
    var btn = document.getElementById('nav-theme-btn');
    var dropdown = document.getElementById('nav-ui-dropdown');
    var cfg = window.DZPokerUIConfig;

    function open() {
        if (dropdown) {
            dropdown.setAttribute('aria-hidden', 'false');
            dropdown.classList.add('is-open');
        }
    }
    function close() {
        if (dropdown) {
            dropdown.setAttribute('aria-hidden', 'true');
            dropdown.classList.remove('is-open');
        }
    }
    function toggle() {
        if (dropdown && dropdown.classList.contains('is-open')) close();
        else open();
    }

    if (btn) btn.addEventListener('click', function(e) { e.stopPropagation(); toggle(); });
    if (switcher && switcher !== btn) {
        switcher.addEventListener('click', function(e) {
            if (e.target === btn || btn.contains(e.target)) return;
            e.stopPropagation();
            toggle();
        });
    }

    if (dropdown && cfg) {
        dropdown.querySelectorAll('[data-theme]').forEach(function(b) {
            b.addEventListener('click', function() {
                cfg.set({ theme: this.getAttribute('data-theme') }, { syncToServer: true });
                close();
            });
        });
        dropdown.querySelectorAll('[data-ui]').forEach(function(b) {
            b.addEventListener('click', function() {
                cfg.set({ uiVersion: this.getAttribute('data-ui') }, { syncToServer: true });
                close();
            });
        });
        var skinBtns = document.getElementById('nav-ui-skin-btns');
        if (skinBtns && cfg.SKIN_IDS && cfg.SKIN_LABELS) {
            cfg.SKIN_IDS.forEach(function(id) {
                var label = cfg.SKIN_LABELS[id] || id;
                var b = document.createElement('button');
                b.type = 'button';
                b.setAttribute('data-skin', id);
                b.textContent = label;
                b.addEventListener('click', function() {
                    cfg.set({ skin: id }, { syncToServer: true });
                    close();
                });
                skinBtns.appendChild(b);
            });
        }
    }

    document.addEventListener('click', function() { close(); });
    if (switcher) switcher.addEventListener('click', function(e) { e.stopPropagation(); });
})();
