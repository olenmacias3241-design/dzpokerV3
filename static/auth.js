/**
 * dzpokerV3/static/auth.js
 * 全局：从 localStorage 读取 token，请求 /api/auth/me 更新导航栏；退出清除 token。
 */
(function() {
    var TOKEN_KEY = 'token';

    function getToken() {
        return localStorage.getItem(TOKEN_KEY) || '';
    }

    function setToken(token) {
        if (token) localStorage.setItem(TOKEN_KEY, token);
        else localStorage.removeItem(TOKEN_KEY);
    }

    window.authGetToken = getToken;
    window.authSetToken = setToken;

    var navGuest = document.getElementById('nav-guest');
    var navUser = document.getElementById('nav-user');
    var navUsername = document.getElementById('nav-username');
    var navCoins = document.getElementById('nav-coins');
    var navLogout = document.getElementById('nav-logout');

    function showGuest() {
        if (navGuest) navGuest.style.display = '';
        if (navUser) navUser.style.display = 'none';
    }

    function showUser(profile) {
        if (navGuest) navGuest.style.display = 'none';
        if (navUser) navUser.style.display = '';
        if (navUsername) navUsername.textContent = profile.username || '用户';
        if (navCoins) navCoins.textContent = '筹码: ' + (profile.coinsBalance != null ? Number(profile.coinsBalance).toLocaleString() : '—');
    }

    function loadMe() {
        var token = getToken();
        if (!token) {
            showGuest();
            return;
        }
        var url = (window.DZPOKER && window.DZPOKER.apiUrl) ? window.DZPOKER.apiUrl('/api/auth/me') : '/api/auth/me';
        fetch(url, {
            headers: { 'Authorization': 'Bearer ' + token }
        })
        .then(function(r) {
            if (r.status === 401 || r.status === 500) {
                setToken('');
                showGuest();
                return null;
            }
            return r.json();
        })
        .then(function(data) {
            if (data == null) return;
            if (data.ok && data.userProfile) {
                showUser(data.userProfile);
                if (window.DZPokerUIConfig && window.DZPokerUIConfig.init) {
                    window.DZPokerUIConfig.init({ fetchServer: true });
                }
            } else {
                setToken('');
                showGuest();
            }
        })
        .catch(function() {
            setToken('');
            showGuest();
        });
    }

    if (navLogout) {
        navLogout.addEventListener('click', function(e) {
            e.preventDefault();
            setToken('');
            showGuest();
            if (window.location.pathname !== '/login' && window.location.pathname !== '/register') {
                window.location.reload();
            }
        });
    }

    loadMe();
})();
