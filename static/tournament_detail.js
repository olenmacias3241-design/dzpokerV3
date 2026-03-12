/**
 * 锦标赛详情页：详情、报名/取消报名、盲注/奖励展示
 * API: GET /api/tournaments/<id>, POST register, POST unregister
 */
(function() {
    var tournamentId = window.TOURNAMENT_ID || 0;
    var apiBase = (window.DZPOKER && window.DZPOKER.apiUrl) ? window.DZPOKER.apiUrl('') : '';
    var token = (window.authGetToken && window.authGetToken()) || localStorage.getItem('token') || '';

    var loadingEl = document.getElementById('tournament-loading');
    var errorEl = document.getElementById('tournament-error');
    var contentEl = document.getElementById('tournament-content');
    var errorTextEl = document.getElementById('tournament-error-text');
    var registerBtn = document.getElementById('register-btn');
    var unregisterBtn = document.getElementById('unregister-btn');
    var enterLobbyLink = document.getElementById('enter-lobby-link');
    var msgEl = document.getElementById('tournament-msg');

    var match = /\/tournament\/(\d+)/.exec(window.location.pathname);
    if (match) tournamentId = parseInt(match[1], 10);

    function statusText(s) {
        var map = { Registration: '报名中', LateRegistration: '晚报名', Running: '进行中', Break: '休息中', Finished: '已结束' };
        return map[s] || s || '—';
    }

    function formatStarts(at) {
        if (!at) return '坐满即开';
        var d = new Date(at);
        return isNaN(d.getTime()) ? at : d.toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    }

    function showContent(data) {
        loadingEl.style.display = 'none';
        contentEl.style.display = 'block';
        document.getElementById('tournament-name').textContent = data.name || '未命名';
        document.getElementById('tournament-type-badge').textContent = data.type || '—';
        document.getElementById('tournament-type-badge').className = 'tournament-type-badge type-' + (data.type || '').toLowerCase();
        document.getElementById('tournament-status-badge').textContent = statusText(data.status);
        document.getElementById('tournament-status-badge').className = 'tournament-status-badge status-' + (data.status || '').toLowerCase();
        document.getElementById('tournament-buyin').textContent = (data.buyIn != null ? data.buyIn.toLocaleString() : '—') + (data.fee ? ' + ' + data.fee + ' 报名费' : '');
        document.getElementById('tournament-stack').textContent = data.startingStack != null ? data.startingStack.toLocaleString() : '—';
        document.getElementById('tournament-players').textContent = (data.minPlayersToStart != null ? data.minPlayersToStart : '?') + '–' + (data.maxPlayers != null ? data.maxPlayers : '?') + ' 人';
        document.getElementById('tournament-starts').textContent = formatStarts(data.startsAt);
        document.getElementById('tournament-latereg').textContent = data.lateRegMinutes != null ? data.lateRegMinutes + ' 分钟' : '—';

        if (registerBtn && unregisterBtn && enterLobbyLink) {
            registerBtn.style.display = 'none';
            unregisterBtn.style.display = 'none';
            enterLobbyLink.style.display = 'none';
            if (data.status === 'Registration' || data.status === 'LateRegistration') {
                if (data.myRegistration) {
                    unregisterBtn.style.display = 'inline-block';
                    if (data.status === 'Running' || data.status === 'LateRegistration') enterLobbyLink.href = '/tournament/' + tournamentId + '/lobby';
                    if (data.status === 'Running') enterLobbyLink.style.display = 'inline-block';
                } else {
                    registerBtn.style.display = 'inline-block';
                }
            } else if (data.status === 'Running' || data.status === 'Break') {
                if (data.myRegistration) {
                    enterLobbyLink.href = '/tournament/' + tournamentId + '/lobby';
                    enterLobbyLink.style.display = 'inline-block';
                }
            }
        }

        var blindsSection = document.getElementById('tournament-blinds-section');
        var blindsList = document.getElementById('tournament-blinds-list');
        var blinds = data.blindStructure || data.blind_structure_json;
        if (blinds && (Array.isArray(blinds) ? blinds.length : 1)) {
            blindsSection.style.display = 'block';
            blindsList.innerHTML = '';
            var arr = Array.isArray(blinds) ? blinds : (typeof blinds === 'string' ? (function() { try { return JSON.parse(blinds); } catch(e) { return []; } })() : []);
            (arr.length ? arr : [{ smallBlind: 10, bigBlind: 20, ante: 0, durationMinutes: 5 }]).forEach(function(level, i) {
                var row = document.createElement('div');
                row.className = 'blind-level-row';
                row.textContent = (i + 1) + '. SB ' + (level.smallBlind != null ? level.smallBlind : level.small_blind) + ' / BB ' + (level.bigBlind != null ? level.bigBlind : level.big_blind) + (level.ante ? ' Ante ' + level.ante : '') + ' · ' + (level.durationMinutes != null ? level.durationMinutes : level.duration_minutes) + ' 分钟';
                blindsList.appendChild(row);
            });
        } else {
            blindsSection.style.display = 'none';
        }

        var payoutsSection = document.getElementById('tournament-payouts-section');
        var payoutsList = document.getElementById('tournament-payouts-list');
        var payouts = data.payoutStructure || data.payout_structure_json;
        if (payouts && (Array.isArray(payouts) ? payouts.length : 1)) {
            payoutsSection.style.display = 'block';
            payoutsList.innerHTML = '';
            var arr = Array.isArray(payouts) ? payouts : (typeof payouts === 'string' ? (function() { try { return JSON.parse(payouts); } catch(e) { return []; } })() : []);
            (arr.length ? arr : [{ rankFrom: 1, rankTo: 1, percent: 50 }, { rankFrom: 2, rankTo: 2, percent: 30 }, { rankFrom: 3, rankTo: 3, percent: 20 }]).forEach(function(p) {
                var rf = p.rankFrom != null ? p.rankFrom : p.rank_from;
                var rt = p.rankTo != null ? p.rankTo : p.rank_to;
                var pc = p.percent != null ? p.percent : p.percent_value;
                var row = document.createElement('div');
                row.className = 'payout-row';
                row.textContent = '第 ' + rf + (rf !== rt ? '–' + rt : '') + ' 名：' + pc + '%';
                payoutsList.appendChild(row);
            });
        } else {
            payoutsSection.style.display = 'none';
        }
    }

    function showError(msg) {
        loadingEl.style.display = 'none';
        contentEl.style.display = 'none';
        errorEl.style.display = 'block';
        errorTextEl.textContent = msg || '加载失败';
    }

    function setMsg(text, isError) {
        if (!msgEl) return;
        msgEl.textContent = text || '';
        msgEl.className = 'form-msg' + (isError ? ' error' : ' success');
    }

    fetch(apiBase + '/api/tournaments/' + tournamentId, { headers: token ? { 'Authorization': 'Bearer ' + token } : {} })
        .then(function(r) {
            if (r.status === 404) {
                showError('赛事不存在或锦标赛接口即将上线。');
                return null;
            }
            return r.json();
        })
        .then(function(data) {
            if (!data) return;
            if (data.error) {
                showError(data.error);
                return;
            }
            showContent(data);
        })
        .catch(function() {
            showError('网络错误');
        });

    if (registerBtn) {
        registerBtn.addEventListener('click', function() {
            if (!token) { setMsg('请先登录', true); return; }
            setMsg('');
            registerBtn.disabled = true;
            fetch(apiBase + '/api/tournaments/' + tournamentId + '/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token }
            })
                .then(function(r) { return r.json().catch(function() { return {}; }); })
                .then(function(data) {
                    registerBtn.disabled = false;
                    if (data.error) { setMsg(data.error, true); return; }
                    setMsg('报名成功', false);
                    if (unregisterBtn) unregisterBtn.style.display = 'inline-block';
                    registerBtn.style.display = 'none';
                })
                .catch(function() {
                    registerBtn.disabled = false;
                    setMsg('请求失败', true);
                });
        });
    }

    if (unregisterBtn) {
        unregisterBtn.addEventListener('click', function() {
            if (!token) return;
            setMsg('');
            unregisterBtn.disabled = true;
            fetch(apiBase + '/api/tournaments/' + tournamentId + '/unregister', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token }
            })
                .then(function(r) { return r.json().catch(function() { return {}; }); })
                .then(function(data) {
                    unregisterBtn.disabled = false;
                    if (data.error) { setMsg(data.error, true); return; }
                    setMsg('已取消报名', false);
                    unregisterBtn.style.display = 'none';
                    if (registerBtn) registerBtn.style.display = 'inline-block';
                })
                .catch(function() {
                    unregisterBtn.disabled = false;
                    setMsg('请求失败', true);
                });
        });
    }
})();
