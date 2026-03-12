/**
 * 锦标赛列表页：拉取赛事列表、按类型筛选
 * API: GET /api/tournaments（后端未实现时 404 显示「即将上线」）
 */
(function() {
    var apiBase = (window.DZPOKER && window.DZPOKER.apiUrl) ? window.DZPOKER.apiUrl('') : '';
    var token = (window.authGetToken && window.authGetToken()) || localStorage.getItem('token') || '';
    var currentFilter = 'all';
    var allTournaments = [];

    var loadingEl = document.getElementById('tournaments-loading');
    var emptyEl = document.getElementById('tournaments-empty');
    var errorEl = document.getElementById('tournaments-error');
    var listEl = document.getElementById('tournaments-list');
    var filterBtns = document.querySelectorAll('.tournaments-filters .filter-btn');

    function statusText(s) {
        var map = { Registration: '报名中', LateRegistration: '晚报名', Running: '进行中', Break: '休息中', Finished: '已结束' };
        return map[s] || s || '—';
    }

    function formatStarts(at) {
        if (!at) return '坐满即开';
        var d = new Date(at);
        return isNaN(d.getTime()) ? at : d.toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    }

    function renderList() {
        var list = currentFilter === 'all' ? allTournaments : allTournaments.filter(function(t) { return t.type === currentFilter; });
        listEl.innerHTML = '';
        if (list.length === 0) {
            emptyEl.style.display = 'block';
            emptyEl.textContent = currentFilter === 'all' ? '暂无赛事。锦标赛功能即将上线，敬请期待。' : '暂无该类型赛事。';
            return;
        }
        emptyEl.style.display = 'none';
        list.forEach(function(t) {
            var card = document.createElement('a');
            card.href = '/tournament/' + t.id;
            card.className = 'tournament-card';
            var reg = (t.registeredCount != null ? t.registeredCount : 0) + ' / ' + (t.maxPlayers != null ? t.maxPlayers : '?');
            card.innerHTML =
                '<span class="tournament-card-name">' + (t.name || '未命名') + '</span>' +
                '<span class="tournament-card-type">' + (t.type || '—') + '</span>' +
                '<span class="tournament-card-buyin">买入 ' + (t.buyIn != null ? t.buyIn.toLocaleString() : '—') + (t.fee ? ' + ' + t.fee : '') + '</span>' +
                '<span class="tournament-card-reg">' + reg + ' 人</span>' +
                '<span class="tournament-card-status">' + statusText(t.status) + '</span>' +
                '<span class="tournament-card-starts">' + formatStarts(t.startsAt) + '</span>';
            listEl.appendChild(card);
        });
    }

    function loadTournaments() {
        loadingEl.style.display = 'block';
        emptyEl.style.display = 'none';
        if (errorEl) errorEl.style.display = 'none';
        fetch(apiBase + '/api/tournaments', { headers: token ? { 'Authorization': 'Bearer ' + token } : {} })
            .then(function(r) {
                if (r.status === 404) {
                    allTournaments = [];
                    loadingEl.style.display = 'none';
                    emptyEl.style.display = 'block';
                    emptyEl.textContent = '锦标赛功能即将上线，敬请期待。';
                    return;
                }
                return r.json();
            })
            .then(function(data) {
                loadingEl.style.display = 'none';
                if (!data) return;
                if (data.error && errorEl) {
                    errorEl.textContent = data.error;
                    errorEl.style.display = 'block';
                    return;
                }
                allTournaments = data.tournaments || [];
                renderList();
            })
            .catch(function() {
                loadingEl.style.display = 'none';
                emptyEl.style.display = 'block';
                emptyEl.textContent = '加载失败，请稍后重试。';
            });
    }

    filterBtns.forEach(function(btn) {
        btn.addEventListener('click', function() {
            filterBtns.forEach(function(b) { b.classList.remove('active'); });
            this.classList.add('active');
            currentFilter = this.getAttribute('data-type') || 'all';
            renderList();
        });
    });

    loadTournaments();
})();
