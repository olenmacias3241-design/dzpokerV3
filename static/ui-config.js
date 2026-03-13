/**
 * dzpokerV3/static/ui-config.js
 * 多 UI 切换：主题、UI 版本、字体、动画、音效等
 * 优先级：URL 参数(仅当次) > 服务端用户配置 > localStorage > 默认值
 */
(function () {
    var STORAGE_KEY = 'dzpoker_ui_config';
    var SKIN_IDS = ['classic', 'blue-casino', 'burgundy-velvet', 'midnight-black-gold', 'forest-green', 'violet-vip', 'warm-lamp', 'high-contrast-arena', 'light-minimal', 'cyber-neon'];
    var SKIN_LABELS = {
        'classic': '经典绿金',
        'blue-casino': '深蓝赌场',
        'burgundy-velvet': '酒红丝绒',
        'midnight-black-gold': '午夜黑金',
        'forest-green': '森林绿',
        'violet-vip': '紫罗兰 VIP',
        'warm-lamp': '暖黄灯光',
        'high-contrast-arena': '高对比竞技',
        'light-minimal': '极简浅色',
        'cyber-neon': '赛博霓虹'
    };
    var DEFAULTS = {
        theme: 'system',
        uiVersion: 'default',
        fontSize: 'medium',
        skin: 'classic',
        animationEnabled: true,
        soundEnabled: true,
        reducedMotion: false
    };

    var current = {};
    var urlOverrides = {}; // 仅当次生效，不写入存储

    function parseUrlParams() {
        var q = typeof window !== 'undefined' && window.location && window.location.search;
        if (!q) return {};
        var out = {};
        q.slice(1).split('&').forEach(function (pair) {
            var i = pair.indexOf('=');
            var k = i >= 0 ? decodeURIComponent(pair.slice(0, i)).trim() : decodeURIComponent(pair).trim();
            var v = i >= 0 ? decodeURIComponent(pair.slice(i + 1)).trim() : '';
            if (k) out[k] = v;
        });
        return out;
    }

    function parseBool(val) {
        if (val === true || val === false) return val;
        if (val === '1' || val === 'true' || val === 'yes') return true;
        if (val === '0' || val === 'false' || val === 'no') return false;
        return undefined;
    }

    function mergeConfig(base, override) {
        var next = {};
        ['theme', 'uiVersion', 'fontSize', 'skin', 'animationEnabled', 'soundEnabled', 'reducedMotion'].forEach(function (k) {
            if (override && override[k] !== undefined) {
                if (k === 'animationEnabled' || k === 'soundEnabled' || k === 'reducedMotion') {
                    var b = parseBool(override[k]);
                    if (b !== undefined) next[k] = b;
                    else next[k] = base[k];
                } else if (k === 'theme' && ['light', 'dark', 'system'].indexOf(override[k]) >= 0) {
                    next[k] = override[k];
                } else if (k === 'uiVersion' && ['default', 'compact', 'classic'].indexOf(override[k]) >= 0) {
                    next[k] = override[k];
                } else if (k === 'fontSize' && ['small', 'medium', 'large'].indexOf(override[k]) >= 0) {
                    next[k] = override[k];
                } else if (k === 'skin' && SKIN_IDS.indexOf(override[k]) >= 0) {
                    next[k] = override[k];
                } else {
                    next[k] = base[k];
                }
            } else {
                next[k] = base[k];
            }
        });
        return next;
    }

    function loadFromStorage() {
        try {
            var raw = localStorage.getItem(STORAGE_KEY);
            if (raw) {
                var parsed = JSON.parse(raw);
                return mergeConfig(DEFAULTS, parsed);
            }
        } catch (e) {}
        return Object.assign({}, DEFAULTS);
    }

    function saveToStorage(config) {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
        } catch (e) {}
    }

    function getEffectiveTheme() {
        var theme = current.theme || 'system';
        if (theme === 'light' || theme === 'dark') return theme;
        if (typeof window !== 'undefined' && window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            return 'dark';
        }
        return 'light';
    }

    function applyToDom() {
        var doc = typeof document !== 'undefined' && document.documentElement;
        if (!doc) return;

        var theme = getEffectiveTheme();
        doc.setAttribute('data-theme', theme);
        doc.setAttribute('data-ui-version', current.uiVersion || 'default');
        doc.setAttribute('data-font-size', current.fontSize || 'medium');
        var skin = current.skin && SKIN_IDS.indexOf(current.skin) >= 0 ? current.skin : 'classic';
        doc.setAttribute('data-ui-skin', skin);
        doc.classList.toggle('no-animation', !current.animationEnabled);
        doc.classList.toggle('reduced-motion', !!current.reducedMotion);
        doc.classList.toggle('sound-disabled', !current.soundEnabled);
    }

    function loadFromUrl() {
        var q = parseUrlParams();
        var overrides = {};
        if (q.theme && ['light', 'dark', 'system'].indexOf(q.theme) >= 0) overrides.theme = q.theme;
        if (q.ui || q.uiVersion) {
            var v = q.ui || q.uiVersion;
            if (['default', 'compact', 'classic'].indexOf(v) >= 0) overrides.uiVersion = v;
        }
        if (q.fontSize && ['small', 'medium', 'large'].indexOf(q.fontSize) >= 0) overrides.fontSize = q.fontSize;
        if (q.skin && SKIN_IDS.indexOf(q.skin) >= 0) overrides.skin = q.skin;
        if (q.animation !== undefined) { var a = parseBool(q.animation); if (a !== undefined) overrides.animationEnabled = a; }
        if (q.sound !== undefined) { var s = parseBool(q.sound); if (s !== undefined) overrides.soundEnabled = s; }
        urlOverrides = overrides;
    }

    function resolveConfig() {
        var base = Object.assign({}, DEFAULTS);
        var local = loadFromStorage();
        base = mergeConfig(base, local);
        base = mergeConfig(base, urlOverrides);
        current = base;
    }

    function get() {
        return Object.assign({}, current);
    }

    function set(partial, options) {
        options = options || {};
        current = mergeConfig(current, partial);
        applyToDom();
        if (!options.skipSave && Object.keys(urlOverrides).length === 0) {
            saveToStorage(current);
            if (options.syncToServer !== false && window.authGetToken && window.authGetToken()) {
                syncToServer(current);
            }
        }
        if (window.DZPokerUIConfig && typeof window.DZPokerUIConfig.onChange === 'function') {
            window.DZPokerUIConfig.onChange(current);
        }
        return current;
    }

    function getToken() {
        return (window.authGetToken && window.authGetToken()) || '';
    }

    function syncToServer(config) {
        var token = getToken();
        if (!token) return Promise.resolve();
        var url = (window.DZPOKER && window.DZPOKER.apiUrl) ? window.DZPOKER.apiUrl('/api/users/me/ui-config') : '/api/users/me/ui-config';
        return fetch(url, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
            },
            body: JSON.stringify(config)
        }).then(function (r) {
            if (!r.ok) return Promise.reject(new Error('sync failed'));
            return r.json ? r.json() : {};
        }).catch(function () {
            if (typeof window !== 'undefined' && window.console && window.console.warn) {
                window.console.warn('UI config sync to server failed; local settings applied.');
            }
        });
    }

    function fetchServerConfig() {
        var token = getToken();
        if (!token) return Promise.resolve(null);
        var url = (window.DZPOKER && window.DZPOKER.apiUrl) ? window.DZPOKER.apiUrl('/api/users/me/ui-config') : '/api/users/me/ui-config';
        return fetch(url, { headers: { 'Authorization': 'Bearer ' + token } })
            .then(function (r) {
                if (r.status === 204 || !r.ok) return null;
                return r.json();
            })
            .then(function (data) {
                if (data && typeof data === 'object') return mergeConfig(DEFAULTS, data);
                return null;
            })
            .catch(function () { return null; });
    }

    function init(opts) {
        opts = opts || {};
        loadFromUrl();
        resolveConfig();
        if (opts.serverConfig) {
            current = mergeConfig(mergeConfig(loadFromStorage(), opts.serverConfig), urlOverrides);
        } else if (opts.fetchServer && getToken()) {
            return fetchServerConfig().then(function (server) {
                if (server) current = mergeConfig(server, urlOverrides);
                else resolveConfig();
                applyToDom();
                saveToStorage(current);
                return current;
            });
        }
        applyToDom();
        if (typeof window !== 'undefined' && window.matchMedia) {
            window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function () {
                if (current.theme === 'system') applyToDom();
            });
        }
        return Promise.resolve(current);
    }

    window.DZPokerUIConfig = {
        get: get,
        set: set,
        apply: applyToDom,
        getEffectiveTheme: getEffectiveTheme,
        init: init,
        DEFAULTS: Object.assign({}, DEFAULTS),
        STORAGE_KEY: STORAGE_KEY,
        SKIN_IDS: SKIN_IDS.slice(),
        SKIN_LABELS: Object.assign({}, SKIN_LABELS),
        onChange: null
    };

    // 首屏同步应用（URL + localStorage），避免闪烁
    loadFromUrl();
    resolveConfig();
    applyToDom();
})();
