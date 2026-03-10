// dzpokerV3/static/script.js - 支持多人在线：table + token，WebSocket 实时同步
// 客户端仅监控当前单桌；服务端监管所有牌桌。

let lastState = null;
let tableId = null;
let token = null;
let mySeat = 0;
let socket = null;

function apiUrl(path) {
    return (window.DZPOKER && window.DZPOKER.apiUrl) ? window.DZPOKER.apiUrl(path) : path;
}
function wsUrl() {
    return (window.DZPOKER && window.DZPOKER.wsUrl) ? window.DZPOKER.wsUrl() : "";
}

function getUrlParams() {
    const params = {};
    const q = window.location.search.slice(1).split('&');
    q.forEach(function (p) {
        const kv = p.split('=');
        if (kv[0]) params[kv[0]] = decodeURIComponent(kv[1] || '');
    });
    return params;
}

function ensureToken() {
    var t = (typeof window.authGetToken === 'function' && window.authGetToken()) || localStorage.getItem('token') || '';
    if (t) return Promise.resolve(t);
    return fetch(apiUrl('/api/login'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: '游客_' + Date.now() })
    })
        .then(function (r) { return r.json(); })
        .then(function (data) {
            if (data.token) {
                localStorage.setItem('token', data.token);
                if (data.username) localStorage.setItem('dzpoker_username', data.username);
                return data.token;
            }
            throw new Error('获取游客身份失败');
        });
}

document.addEventListener('DOMContentLoaded', () => {
    const params = getUrlParams();
    tableId = params.table ? parseInt(params.table, 10) : null;
    token = params.token || (typeof window.authGetToken === 'function' && window.authGetToken()) || localStorage.getItem('token') || '';

    const noTableMsg = document.getElementById('no-table-msg');
    const gameArea = document.querySelector('.game-area');

    if (!tableId) {
        if (noTableMsg) noTableMsg.style.display = 'block';
        if (gameArea) gameArea.style.display = 'none';
        return;
    }
    if (noTableMsg) noTableMsg.style.display = 'none';
    if (gameArea) gameArea.style.display = '';

    if (!token) {
        ensureToken().then(function (t) {
            token = t;
            if (history.replaceState) {
                var url = new URL(window.location.href);
                url.searchParams.set('token', token);
                history.replaceState(null, '', url.toString());
            }
            loadTableAndGame();
        }).catch(function () {
            if (noTableMsg) {
                noTableMsg.innerHTML = '<p>无法获取游客身份，请<a href="/lobby">从大厅进入</a>。</p>';
                noTableMsg.style.display = 'block';
            }
            if (gameArea) gameArea.style.display = 'none';
        });
        return;
    }

    mySeat = 0;

    const startGameBtn = document.getElementById('start-game-btn');
    const foldBtn = document.getElementById('fold-btn');
    const checkBtn = document.getElementById('check-btn');
    const callBtn = document.getElementById('call-btn');
    const betBtn = document.getElementById('bet-btn');
    const allInBtn = document.getElementById('all-in-btn');
    const betAmountInput = document.getElementById('bet-amount');
    const betSlider = document.getElementById('bet-slider');

    startGameBtn.addEventListener('click', startGame);
    const leaveSeatBtn = document.getElementById('leave-seat-btn');
    if (leaveSeatBtn) {
        leaveSeatBtn.addEventListener('click', function () {
            if (!tableId || !token) return;
            leaveSeatBtn.disabled = true;
            leaveSeatBtn.textContent = '离开中…';
            fetch(apiUrl('/api/tables/' + tableId + '/leave'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token: token })
            })
                .then(function (r) { return r.json().then(function (body) { return { ok: r.ok, body: body }; }); })
                .then(function (res) {
                    if (!res.ok && res.body && res.body.error) {
                        alert(res.body.error);
                    }
                    leaveSeatBtn.disabled = false;
                    leaveSeatBtn.textContent = '离开座位';
                    loadTableAndGame();
                })
                .catch(function () {
                    leaveSeatBtn.disabled = false;
                    leaveSeatBtn.textContent = '离开座位';
                    alert('操作失败，请重试');
                });
        });
    }
    foldBtn.addEventListener('click', () => sendAction('fold'));
    if (checkBtn) checkBtn.addEventListener('click', () => sendAction('check'));
    if (callBtn) callBtn.addEventListener('click', () => sendAction('call'));
    allInBtn.addEventListener('click', () => sendAction('all_in'));
    betBtn.addEventListener('click', () => {
        const amount = betAmountInput.value ? parseInt(betAmountInput.value, 10) : (betSlider ? parseInt(betSlider.value, 10) : 0);
        if (amount > 0) {
            sendAction('bet', amount);
        } else {
            alert('请输入有效的下注金额');
        }
    });
    if (betSlider) {
        betSlider.addEventListener('input', () => {
            betAmountInput.value = betSlider.value;
        });
    }
    document.querySelectorAll('.emote-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const emote = btn.getAttribute('data-emote');
            if (emote) sendEmote(emote);
        });
    });

    const presetMin = document.getElementById('preset-min');
    const presetHalf = document.getElementById('preset-half');
    const preset3q = document.getElementById('preset-3q');
    const presetPot = document.getElementById('preset-pot');
    function setBetTo(value) {
        if (!lastState || !betAmountInput || !betSlider) return;
        const me = lastState.players[mySeat];
        const myChips = me ? me.chips : 0;
        const myCurrentBet = me ? me.current_bet : 0;
        const minRaiseTo = lastState.min_raise_to || 0;
        const maxTo = myCurrentBet + myChips;
        const capped = Math.min(Math.max(value, minRaiseTo), maxTo);
        betAmountInput.value = capped;
        betSlider.value = capped;
    }
    if (presetMin) presetMin.addEventListener('click', () => setBetTo(lastState ? lastState.min_raise_to : 0));
    if (presetHalf) presetHalf.addEventListener('click', () => {
        if (!lastState) return;
        const pot = lastState.pot || 0;
        const myBet = lastState.players[mySeat] ? lastState.players[mySeat].current_bet : 0;
        setBetTo(myBet + Math.floor(pot / 2));
    });
    if (preset3q) preset3q.addEventListener('click', () => {
        if (!lastState) return;
        const pot = lastState.pot || 0;
        const myBet = lastState.players[mySeat] ? lastState.players[mySeat].current_bet : 0;
        setBetTo(myBet + Math.floor(pot * 3 / 4));
    });
    if (presetPot) presetPot.addEventListener('click', () => {
        if (!lastState) return;
        const pot = lastState.pot || 0;
        const myBet = lastState.players[mySeat] ? lastState.players[mySeat].current_bet : 0;
        setBetTo(myBet + pot);
    });

    const dealNextBtn = document.getElementById('deal-next-btn');
    if (dealNextBtn) dealNextBtn.addEventListener('click', dealNextStreet);

    const insuranceBuyBtn = document.getElementById('insurance-buy-btn');
    const insuranceDeclineBtn = document.getElementById('insurance-decline-btn');
    const insuranceAmountInput = document.getElementById('insurance-amount');
    if (insuranceBuyBtn && insuranceAmountInput) {
        insuranceBuyBtn.addEventListener('click', function () {
            const amount = parseInt(insuranceAmountInput.value, 10) || 0;
            if (amount <= 0) {
                alert('请输入有效保费（大于 0）');
                return;
            }
            if (socket && socket.connected) {
                socket.emit('insurance', { token: token, amount: amount });
                return;
            }
            fetch(apiUrl('/api/tables/' + tableId + '/insurance'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token: token, amount: amount })
            }).then(function (r) { return r.json(); }).then(function (s) {
                if (s && s.error) alert(s.error);
                else if (s && !s.error) updateUI(s);
            });
        });
    }
    if (insuranceDeclineBtn) {
        insuranceDeclineBtn.addEventListener('click', function () {
            dealNextStreet();
        });
    }

    loadTableAndGame();
});

function loadTableAndGame() {
    if (!tableId || !token) return;
    const gameArea = document.querySelector('.game-area');
    const noTableMsg = document.getElementById('no-table-msg');
    const sitWrap = document.getElementById('sit-at-table-wrap');
    const pokerTable = document.querySelector('.poker-table');
    const actionsEl = document.querySelector('.game-area .actions');

    fetch(apiUrl('/api/tables/' + tableId + '?token=' + encodeURIComponent(token)))
        .then(function (res) { return res.json(); })
        .then(function (data) {
            if (data.error) {
                if (noTableMsg) {
                    noTableMsg.innerHTML = '<p>请先<a href="/lobby">登录并在大厅进入牌桌</a>，进入牌桌后再选择空位落座。</p>';
                    noTableMsg.style.display = 'block';
                }
                if (gameArea) gameArea.style.display = 'none';
                if (sitWrap) sitWrap.style.display = 'none';
                return;
            }
            mySeat = data.my_seat >= 0 ? data.my_seat : -1;

            if (mySeat < 0) {
                if (data.status === 'playing') {
                    if (noTableMsg) {
                        noTableMsg.innerHTML = '<p>对局已开始，您未在此桌。<a href="/lobby">返回大厅</a></p>';
                        noTableMsg.style.display = 'block';
                    }
                    if (gameArea) gameArea.style.display = 'none';
                    if (sitWrap) sitWrap.style.display = 'none';
                    return;
                }
                if (data.status === 'waiting') {
                    if (noTableMsg) noTableMsg.style.display = 'none';
                    if (gameArea) gameArea.style.display = '';
                    if (sitWrap) {
                        sitWrap.style.display = 'block';
                        document.getElementById('sit-at-table-title').textContent = (data.table_name || '牌桌') + ' · 选择座位';
                        renderSitSeats(data);
                    }
                    if (pokerTable) pokerTable.style.display = 'none';
                    if (actionsEl) actionsEl.style.display = 'none';
                    return;
                }
            }

            if (noTableMsg) noTableMsg.style.display = 'none';
            if (gameArea) gameArea.style.display = '';
            if (sitWrap) sitWrap.style.display = 'none';
            if (pokerTable) pokerTable.style.display = '';
            if (actionsEl) actionsEl.style.display = '';

            mySeat = data.my_seat >= 0 ? data.my_seat : 0;
            var leaveWrap = document.getElementById('leave-seat-wrap');
            if (data.status === 'waiting') {
                if (leaveWrap) leaveWrap.style.display = (mySeat >= 0 ? 'block' : 'none');
                if (data.can_start) {
                    document.getElementById('start-game-btn').style.display = 'block';
                    document.getElementById('start-game-btn').textContent = '开始对局';
                    document.getElementById('action-controls').style.display = 'none';
                    document.getElementById('deal-controls').style.display = 'none';
                    document.getElementById('stage-display').textContent = '等待开局（两人已就座，点击开始）';
                } else {
                    document.getElementById('start-game-btn').style.display = 'none';
                    document.getElementById('stage-display').textContent = '等待对手加入（当前 ' + (data.player_count || 0) + '/' + (data.max_players || 2) + ' 人）';
                    if (window._waitPoll) clearInterval(window._waitPoll);
                    window._waitPoll = setInterval(function () {
                        fetch(apiUrl('/api/tables/' + tableId + '?token=' + encodeURIComponent(token)))
                            .then(function (r) { return r.json(); })
                            .then(function (d) {
                                if (d.error) return;
                                if (d.status === 'playing' && d.game_state) {
                                    if (window._waitPoll) clearInterval(window._waitPoll);
                                    window._waitPoll = null;
                                    mySeat = d.my_seat >= 0 ? d.my_seat : 0;
                                    lastState = d.game_state;
                                    updateUI(d.game_state);
                                    connectSocket();
                                } else if (d.player_count !== undefined) {
                                    document.getElementById('stage-display').textContent = '等待对手加入（当前 ' + d.player_count + '/' + (d.max_players || 2) + ' 人）';
                                }
                                if (leaveWrap) leaveWrap.style.display = (d.my_seat >= 0 ? 'block' : 'none');
                            });
                    }, 2000);
                }
                var maxP = data.max_players || 6;
                var waitState = { max_players: maxP, players: [], stage: 'preflop', pot: 0, community_cards: [], dealer_idx: -1, sb_idx: -1, bb_idx: -1, current_player_idx: -1, is_running: false, last_action: '', emotes: {} };
                for (var wi = 0; wi < maxP; wi++) {
                    waitState.players[wi] = (data.seats && data.seats[wi]) ? { name: (data.seat_names && data.seat_names[wi]) || '玩家', chips: data.seats[wi].stack != null ? data.seats[wi].stack : 0, has_folded: false } : null;
                }
                updateUI(waitState);
                if (data.can_start) {
                    document.getElementById('stage-display').textContent = '等待开局（两人已就座，点击开始）';
                    document.getElementById('start-game-btn').style.display = 'block';
                } else {
                    document.getElementById('stage-display').textContent = '等待对手加入（当前 ' + (data.player_count || 0) + '/' + (data.max_players || 2) + ' 人）';
                    document.getElementById('start-game-btn').style.display = 'none';
                }
                return;
            }
            if (leaveWrap) leaveWrap.style.display = 'none';
            if (data.status === 'playing' && data.game_state) {
                lastState = data.game_state;
                updateUI(data.game_state);
                connectSocket();
            }
        })
        .catch(function () {
            var noMsg = document.getElementById('no-table-msg');
            var area = document.querySelector('.game-area');
            if (noMsg) noMsg.style.display = 'block';
            if (area) area.style.display = 'none';
        });
}

function renderSitSeats(data) {
    const container = document.getElementById('sit-at-table-seats');
    if (!container) return;
    const seats = Array.isArray(data.seats) ? data.seats : [];
    const names = Array.isArray(data.seat_names) ? data.seat_names : [];
    const maxPlayers = Math.max(2, parseInt(data.max_players, 10) || 6);
    const takenCount = seats.filter(function (s) { return s != null && s !== undefined; }).length;

    const titleEl = document.getElementById('sit-at-table-title');
    const hintEl = container.parentElement && container.parentElement.querySelector('.sit-at-table-hint');
    if (titleEl) titleEl.textContent = (data.table_name || '牌桌') + ' · 选择座位';
    if (hintEl) hintEl.textContent = '共 ' + maxPlayers + ' 个座位，' + takenCount + ' 个已占，' + (maxPlayers - takenCount) + ' 个空位可点击落座。';

    container.innerHTML = '';
    for (let i = 0; i < maxPlayers; i++) {
        const raw = i < seats.length ? seats[i] : undefined;
        const isEmpty = (raw === null || raw === undefined);
        const name = (!isEmpty && names[i] != null && names[i] !== '') ? String(names[i]) : '空位';
        if (isEmpty) {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'sit-seat-btn';
            btn.textContent = '座位 ' + (i + 1) + ' · 空位，点击落座';
            btn.setAttribute('data-seat', String(i));
            btn.addEventListener('click', function () {
                const seat = parseInt(this.getAttribute('data-seat'), 10);
                btn.disabled = true;
                btn.textContent = '落座中…';
                fetch(apiUrl('/api/tables/' + tableId + '/sit'), {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ token: token, seat: seat })
                })
                    .then(function (r) { return r.json().then(function (body) { return { ok: r.ok, body: body }; }); })
                    .then(function (res) {
                        if (!res.ok && res.body && res.body.error) {
                            alert(res.body.error);
                            btn.disabled = false;
                            btn.textContent = '座位 ' + (i + 1) + ' · 空位，点击落座';
                            return;
                        }
                        loadTableAndGame();
                    })
                    .catch(function () {
                        btn.disabled = false;
                        btn.textContent = '座位 ' + (i + 1) + ' · 空位，点击落座';
                        alert('落座失败，请重试');
                    });
            });
            container.appendChild(btn);
        } else {
            const span = document.createElement('span');
            span.className = 'sit-seat-taken';
            span.textContent = '座位 ' + (i + 1) + ' · 已占 · ' + name;
            container.appendChild(span);
        }
    }
}

function connectSocket() {
    if (socket || typeof io === 'undefined') return;
    socket = io(wsUrl() || undefined);
    socket.on('connect', function () {
        socket.emit('join_table', { table_id: tableId, token: token });
    });
    socket.on('game:state_update', function (state) {
        lastState = state;
        updateUI(state);
    });
    socket.on('table:state', function (state) {
        if (state.my_seat !== undefined) mySeat = state.my_seat >= 0 ? state.my_seat : -1;
        if (state.status === 'playing' && state.game_state) {
            lastState = state.game_state;
            updateUI(state.game_state);
        } else if (state.status === 'waiting') {
            var stageEl = document.getElementById('stage-display');
            if (stageEl && state.player_count !== undefined)
                stageEl.textContent = '等待对手加入（当前 ' + state.player_count + '/' + (state.max_players || 6) + ' 人）';
            var leaveWrap = document.getElementById('leave-seat-wrap');
            if (leaveWrap) leaveWrap.style.display = (mySeat >= 0 ? 'block' : 'none');
            if (mySeat < 0 && state.seats && document.getElementById('sit-at-table-seats')) {
                var sitWrap = document.getElementById('sit-at-table-wrap');
                if (sitWrap && sitWrap.style.display !== 'none') {
                    renderSitSeats(state);
                }
            }
        }
    });
    socket.on('error', function (data) {
        if (data && data.message) alert(data.message);
    });
}

async function startGame() {
    if (!tableId || !token) return;
    const isStartNewRound = lastState && lastState.winner_info;
    if (isStartNewRound && socket) {
        socket.emit('start_round', {});
        return;
    }
    const response = await fetch(apiUrl('/api/tables/' + tableId + '/start'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: token })
    });
    const data = await response.json();
    if (data.error) {
        alert(data.error);
        return;
    }
    mySeat = data.my_seat >= 0 ? data.my_seat : 0;
    if (data.game_state) {
        lastState = data.game_state;
        updateUI(data.game_state);
        connectSocket();
    }
}

async function sendAction(action, amount = 0) {
    if (socket && socket.connected) {
        const payload = { action: action };
        if (amount > 0) payload.amount = amount;
        socket.emit('game:action', payload);
        return;
    }
    const payload = { token: token, action: action };
    if (amount > 0) payload.amount = amount;
    fetch(apiUrl('/api/tables/' + tableId + '/action'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    }).then(function (r) { return r.json(); }).then(function (s) { if (s && !s.error) updateUI(s); });
}

async function sendEmote(emote) {
    if (socket && socket.connected) {
        socket.emit('game:emote', { emote: emote });
        return;
    }
    fetch(apiUrl('/api/tables/' + tableId + '/emote'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: token, emote: emote })
    }).then(function (r) { return r.json(); }).then(function (s) { if (s && !s.error) updateUI(s); });
}

function dealNextStreet() {
    if (socket && socket.connected) {
        socket.emit('deal_next_street', { token: token });
        return;
    }
    fetch(apiUrl('/api/tables/' + tableId + '/deal_next'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: token })
    }).then(function (r) { return r.json(); }).then(function (s) { if (s && !s.error) updateUI(s); });
}

function normalizePlayer(player, seatIndex) {
    if (!player) return { name: '', chips: 0, current_bet: 0, hand: [], has_folded: true, is_all_in: false };
    var hand = player.hand || player.hole_cards;
    if (Array.isArray(hand) && hand.length > 0 && (typeof hand[0] === 'string')) {
        hand = hand.map(function (str) {
            if (typeof str !== 'string' || str.length < 2) return { suit: '?', rank: '?' };
            var rank = str[0];
            var suitChar = str[1];
            var suit = { H: '♥', D: '♦', C: '♣', S: '♠' }[suitChar] || '?';
            return { suit: suit, rank: rank };
        });
    }
    return {
        name: player.name || ('玩家' + (seatIndex + 1)),
        chips: player.chips != null ? player.chips : player.stack,
        current_bet: player.current_bet != null ? player.current_bet : player.bet_this_round,
        hand: hand || [],
        has_folded: player.has_folded != null ? player.has_folded : (!player.is_in_hand || !player.is_active),
        is_all_in: player.is_all_in || false
    };
}

function updateUI(state) {
    lastState = state;
    var stage = (state.stage != null ? String(state.stage) : '').toLowerCase();
    var stageVal = stage;
    document.getElementById('stage-display').innerText = stageLabel(stageVal);
    const turnEl = document.getElementById('turn-display');
    if (turnEl) {
        if (state.is_running && state.current_player_name != null && state.current_player_name !== '') {
            turnEl.textContent = '轮到 ' + state.current_player_name + ' 下注';
            turnEl.style.display = 'block';
        } else if (state.street_label && stage !== 'showdown' && stage !== 'ended') {
            turnEl.textContent = state.street_label + ' · 等待下注';
            turnEl.style.display = 'block';
        } else {
            turnEl.textContent = '';
            turnEl.style.display = 'none';
        }
    }
    document.getElementById('pot-display').innerText = state.pot != null ? state.pot : 0;
    const sidePotEl = document.getElementById('side-pots-display');
    if (sidePotEl) {
        if (state.side_pots && state.side_pots.length > 0) {
            sidePotEl.textContent = '边池: ' + state.side_pots.map(function (p) { return p.amount != null ? p.amount : p; }).join(', ');
            sidePotEl.style.display = 'block';
        } else {
            sidePotEl.style.display = 'none';
        }
    }
    /* 我的筹码 / 本街下注 / 本街跟注额：固定显示在牌桌中央 */
    var myStatsEl = document.getElementById('my-stats');
    var myChipsDisplayEl = document.getElementById('my-chips-display');
    var myBetDisplayEl = document.getElementById('my-bet-display');
    var callAmountDisplayEl = document.getElementById('call-amount-display');
    var streetHintEl = document.getElementById('street-hint');
    if (mySeat >= 0 && state.players && state.players[mySeat]) {
        var me = state.players[mySeat];
        if (myStatsEl) myStatsEl.style.display = 'block';
        if (myChipsDisplayEl) myChipsDisplayEl.textContent = me.chips != null ? me.chips : 0;
        if (myBetDisplayEl) myBetDisplayEl.textContent = me.current_bet != null ? me.current_bet : 0;
        if (callAmountDisplayEl) callAmountDisplayEl.textContent = state.call_amount != null ? state.call_amount : 0;
        if (streetHintEl) {
            streetHintEl.style.display = (state.pending_street && state.stage !== 'ended') ? 'block' : 'none';
        }
    } else {
        if (myStatsEl) myStatsEl.style.display = 'none';
        if (streetHintEl) streetHintEl.style.display = 'none';
    }
    document.getElementById('last-action-display').innerText = state.last_action || '';

    const communityContainer = document.getElementById('community-cards-display');
    var communityCards = state.community_cards || [];

    /* 仅在新一局 preflop 且尚无公共牌时清空；ended 时保留公共牌显示 */
    if (stage === 'preflop' && communityCards.length === 0) {
        communityContainer.innerHTML = '';
    }
    animateCards(communityContainer, communityCards, stage);

    const playersContainer = document.getElementById('player-seats');
    playersContainer.innerHTML = '';
    var maxSeats = state.max_players || (state.players && state.players.length) || 6;
    var slots = [];
    for (var si = 0; si < maxSeats; si++) {
        slots.push(state.players && state.players[si] != null ? state.players[si] : null);
    }
    /* 围绕椭圆牌桌均匀分布：圆心 50%,50%，椭圆 rx>ry 与牌桌比例一致，座位贴桌缘外 */
    function seatPositionAroundTable(seatIndex, totalSeats) {
        var angleDeg = 90 - (seatIndex * 360 / totalSeats);
        var angleRad = angleDeg * Math.PI / 180;
        var rx = 54;
        var ry = 48;
        var cx = 50;
        var cy = 50;
        var leftPct = cx + rx * Math.cos(angleRad);
        var topPct = cy + ry * Math.sin(angleRad);
        var out = { top: topPct + '%', left: leftPct + '%', transform: '' };
        if (Math.abs(Math.cos(angleRad)) > 0.7) {
            out.transform = 'translate(-50%, ' + (topPct > 50 ? '0' : '-100%') + ')';
        } else if (leftPct > 65) {
            out.transform = 'translate(12px, -50%)';
        } else if (leftPct < 35) {
            out.transform = 'translate(calc(-100% - 12px), -50%)';
        } else {
            out.transform = 'translate(-50%, ' + (topPct > 50 ? '0' : '-100%') + ')';
        }
        return out;
    }
    var seatLayout6 = [];
    for (var s = 0; s < 6; s++) {
        seatLayout6.push(seatPositionAroundTable(s, 6));
    }
    var seatLayout8 = seatLayout6.slice();
    for (var s = 6; s < 8; s++) {
        seatLayout8.push(seatPositionAroundTable(s, 8));
    }
    var positions = maxSeats <= 6 ? seatLayout6 : seatLayout8;

    /* 本局手牌发牌动画样式随机（每轮可不同） */
    var holeDealStyle = 'deal-hole-' + (1 + Math.floor(Math.random() * 6));

    /* 当前玩家始终显示在牌桌底部：positions[0] 对应椭圆 90° 在屏幕下方，故底部索引为 0 */
    var bottomIdx = 0;
    var focusSeat = mySeat >= 0 ? mySeat : 0;
    function realSeatForDisplay(displayIndex) {
        return (displayIndex + focusSeat - bottomIdx + maxSeats) % maxSeats;
    }

    for (var i = 0; i < maxSeats; i++) {
        var realSeat = realSeatForDisplay(i);
        var player = slots[realSeat];
        var pos = positions[i] || seatLayout6[0];
        var seatDiv = document.createElement('div');
        seatDiv.className = 'player-seat';
        seatDiv.setAttribute('data-seat', String(realSeat));
        seatDiv.style.top = pos.top;
        seatDiv.style.left = pos.left;
        seatDiv.style.transform = pos.transform;

        if (player == null) {
            seatDiv.classList.add('player-seat-empty');
            seatDiv.innerHTML = '<div class="player-info player-info-empty">' +
                '<div class="empty-seat-label">空位</div>' +
                '<span class="empty-seat-hint">座位 ' + (realSeat + 1) + '</span></div>';
            playersContainer.appendChild(seatDiv);
            continue;
        }

        var p = normalizePlayer(player, realSeat);
        const isDealer = state.dealer_idx === realSeat;
        const isSB = state.sb_idx === realSeat;
        const isBB = state.bb_idx === realSeat;
        const isWinner = state.winner_idx === realSeat;
        const badges = [];
        if (isDealer) badges.push('<span class="badge dealer">D</span>');
        if (isSB) badges.push('<span class="badge sb">SB</span>');
        if (isBB) badges.push('<span class="badge bb">BB</span>');

        const emoteInfo = state.emotes && state.emotes[String(realSeat)];
        const emoteHtml = emoteInfo && emoteInfo.emote
            ? '<div class="player-emote">' + emoteInfo.emote + '</div>'
            : '<div class="player-emote"></div>';

        let handHtml = '';
        /* 仅自己或摊牌/结束阶段显示牌面；摊牌后未弃牌玩家的手牌对所有人可见 */
        const showCardFaces = (realSeat === mySeat || stage === 'showdown' || stage === 'ended') && p.hand && p.hand.length > 0;
        const isRed = (s) => s === '♥' || s === '♦';
        const isPreflopDeal = stage === 'preflop' && !p.has_folded && (p.hand && p.hand.length === 2 || !showCardFaces);
        const holeDelay0 = realSeat * 130;
        const holeDelay1 = realSeat * 130 + 180;
        const holeStyleClass = isPreflopDeal ? ' card-deal-hole ' + holeDealStyle : '';

        if (showCardFaces) {
            p.hand.forEach(function (card, cardIdx) {
                const suit = (card && card.suit) != null ? card.suit : '?';
                const rank = (card && card.rank) != null ? card.rank : '?';
                const delay = cardIdx === 0 ? holeDelay0 : holeDelay1;
                const dealStyle = isPreflopDeal ? ' style="animation-delay: ' + delay + 'ms"' : '';
                const dealClass = isPreflopDeal ? holeStyleClass : '';
                const visClass = isPreflopDeal ? '' : ' visible';
                if (suit === '?' && rank === '?') {
                    handHtml += '<div class="card-back' + dealClass + '"' + dealStyle + '></div>';
                } else {
                    const suitClass = isRed(suit) ? 'red' : 'black';
                    handHtml += '<div class="card ' + suitClass + visClass + dealClass + '"' + dealStyle + '>' + suit + rank + '</div>';
                }
            });
        } else {
            const count = p.has_folded ? 0 : 2;
            for (let k = 0; k < count; k++) {
                const delay = k === 0 ? holeDelay0 : holeDelay1;
                const dealStyle = isPreflopDeal ? ' style="animation-delay: ' + delay + 'ms"' : '';
                const dealClass = isPreflopDeal ? holeStyleClass : '';
                handHtml += '<div class="card-back' + dealClass + '"' + dealStyle + '></div>';
            }
        }

        seatDiv.innerHTML =
            '<div class="player-info ' + (state.current_player_idx === realSeat && state.is_running ? 'active' : '') + ' ' + (p.has_folded ? 'folded' : '') + (isWinner ? ' winner' : '') + '">' +
            '<div class="player-hand-wrap">' +
            '<div class="player-hand">' + handHtml + '</div></div>' +
            '<div class="player-meta">' +
            emoteHtml +
            '<div class="badges">' + badges.join('') + '</div>' +
            '<strong>' + (p.name || '玩家') + '</strong>' +
            '<span class="chips-line">筹码 ' + (p.chips != null ? p.chips : 0) + '</span>' +
            (state.winnings_by_seat && state.winnings_by_seat[realSeat] > 0 ? '<span class="win-amount">+' + state.winnings_by_seat[realSeat] + '</span>' : '') +
            '<span class="bet-line">本街下注: ' + (p.current_bet != null ? p.current_bet : 0) + '</span>' +
            (p.is_all_in ? '<span class="all-in-tag">All-in</span>' : '') +
            (realSeat === mySeat && state.my_hand_type ? '<div class="my-hand-type">' + state.my_hand_type + '</div>' : '') +
            '</div></div>';
        playersContainer.appendChild(seatDiv);
    }

    /* 底牌发牌动画可能因第二局等未触发，1.5s 后强制显示所有手牌 */
    setTimeout(function () {
        var holeCards = document.querySelectorAll('.player-hand .card-deal-hole');
        holeCards.forEach(function (el) { el.classList.add('visible'); });
    }, 1500);

    const isOurTurn = state.is_running && state.current_player_idx === mySeat;
    const callAmount = state.call_amount || 0;
    const minRaiseTo = state.min_raise_to || 0;
    const myChips = state.players[mySeat] ? state.players[mySeat].chips : 0;
    const pendingStreet = state.pending_street || null;

    const dealControls = document.getElementById('deal-controls');
    const dealNextBtn = document.getElementById('deal-next-btn');
    const insuranceControls = document.getElementById('insurance-controls');
    const insuranceMessage = document.getElementById('insurance-message');
    const insuranceForm = document.getElementById('insurance-form');
    const insuranceDeclineBtn = document.getElementById('insurance-decline-btn');

    if (state.insurance_offer) {
        if (dealControls) dealControls.style.display = 'none';
        document.getElementById('action-controls').style.display = 'none';
        document.getElementById('start-game-btn').style.display = 'none';
        if (insuranceControls) insuranceControls.style.display = 'block';
        const offer = state.insurance_offer;
        const pct = (offer.equity * 100).toFixed(1);
        if (insuranceMessage) insuranceMessage.textContent = '你是领先玩家，当前胜率 ' + pct + '%。买保险：输时可按赔率获赔，减少波动。';
        if (mySeat === offer.leading_idx) {
            if (insuranceForm) insuranceForm.style.display = 'flex';
            if (insuranceDeclineBtn) insuranceDeclineBtn.style.display = 'inline-block';
        } else {
            if (insuranceMessage) insuranceMessage.textContent = '等待 ' + (offer.leading_name || '领先玩家') + ' 决定是否买保险。';
            if (insuranceForm) insuranceForm.style.display = 'none';
            if (insuranceDeclineBtn) insuranceDeclineBtn.style.display = 'none';
        }
    } else {
        if (insuranceControls) insuranceControls.style.display = 'none';
        if (pendingStreet) {
            if (dealControls) dealControls.style.display = 'block';
            if (dealNextBtn) {
                var label = { flop: '发翻牌', turn: '发转牌', river: '发河牌', showdown: '比牌' }[pendingStreet] || '发牌';
                dealNextBtn.textContent = label;
            }
            document.getElementById('action-controls').style.display = 'none';
            document.getElementById('start-game-btn').style.display = 'none';
        } else {
            if (dealControls) dealControls.style.display = 'none';
            document.getElementById('action-controls').style.display = isOurTurn ? 'block' : 'none';
            document.getElementById('start-game-btn').style.display = (state.is_running ? 'none' : 'block');
            var startBtn = document.getElementById('start-game-btn');
            if (startBtn) startBtn.textContent = state.winner_info ? '开始新一局' : '开始对局';
        }
    }

    const checkBtn = document.getElementById('check-btn');
    if (checkBtn) checkBtn.style.display = callAmount === 0 ? 'inline-block' : 'none';
    const callBtn = document.getElementById('call-btn');
    if (callBtn) {
        callBtn.style.display = callAmount > 0 ? 'inline-block' : 'none';
        callBtn.textContent = callAmount > 0 ? '跟注 (' + callAmount + ')' : '跟注';
        callBtn.disabled = callAmount > myChips;
    }
    const betBtnEl = document.getElementById('bet-btn');
    if (betBtnEl) betBtnEl.textContent = minRaiseTo > 0 ? '加注' : '下注';
    const allInBtnEl = document.getElementById('all-in-btn');
    if (allInBtnEl) allInBtnEl.disabled = myChips <= 0;
    const betAmountInputEl = document.getElementById('bet-amount');
    if (betAmountInputEl) {
        betAmountInputEl.placeholder = minRaiseTo > 0 ? '最小 ' + minRaiseTo : '金额';
        betAmountInputEl.min = minRaiseTo;
        betAmountInputEl.max = myChips;
    }
    const betSliderEl = document.getElementById('bet-slider');
    if (betSliderEl) {
        betSliderEl.min = minRaiseTo || 0;
        betSliderEl.max = myChips;
        const val = Math.min(Math.max(minRaiseTo, parseInt(betSliderEl.value, 10) || 0), myChips);
        betSliderEl.value = val;
        if (betAmountInputEl) betAmountInputEl.value = val;
    }

    if (state.winner_info) {
        showWinnerAnimation(state.winner_info, state.winner_idx, state.players, state.winner_amount);
    } else {
        hideWinnerOverlay();
    }
}

function stageLabel(s) {
    const map = {
        preflop: '底牌圈 · 请下注',
        preflop_done: '底牌圈下注结束',
        flop: '翻牌圈 · 请下注',
        flop_done: '翻牌圈下注结束',
        turn: '转牌圈 · 请下注',
        turn_done: '转牌圈下注结束',
        river: '河牌圈 · 请下注',
        river_done: '河牌圈下注结束',
        showdown: '比牌'
    };
    return map[s] || s || '等待开始';
}

function animateCards(container, cards, stage) {
    if (!container) return;
    var list = cards || [];

    /* showdown/ended 时：直接同步显示全部公共牌（不跳过、不依赖之前动画） */
    if (stage === 'showdown' || stage === 'ended') {
        container.innerHTML = '';
        var delayMs = 0;
        list.forEach(function (cardData, index) {
            var suit, rank;
            if (cardData && typeof cardData === 'object' && ('suit' in cardData || 'rank' in cardData)) {
                suit = cardData.suit != null ? cardData.suit : '?';
                rank = cardData.rank != null ? cardData.rank : '?';
            } else if (typeof cardData === 'string' && cardData.length >= 2) {
                rank = cardData[0];
                var sc = cardData[1];
                suit = { H: '♥', D: '♦', C: '♣', S: '♠' }[sc] || '?';
            } else {
                suit = '?';
                rank = '?';
            }
            var suitClass = (suit === '♥' || suit === '♦') ? 'red' : 'black';
            var cardDiv = document.createElement('div');
            cardDiv.className = 'card ' + suitClass + ' deal-community visible';
            cardDiv.innerText = suit + rank;
            container.appendChild(cardDiv);
        });
        return;
    }

    if (list.length === 0) return;

    /* 严格按德州规则：只追加本街新发的牌。翻牌 3 张、转牌 1 张、河牌 1 张，绝不一次多张 */
    var existingCount = container.querySelectorAll('.card').length;
    var newCards = list.slice(existingCount);
    /* 前端强制规则：一次最多只画 3 张（翻牌）或 1 张（转/河） */
    if (existingCount === 0 && newCards.length > 3) newCards = newCards.slice(0, 3);
    if (existingCount === 3 && newCards.length > 1) newCards = newCards.slice(0, 1);
    if (existingCount === 4 && newCards.length > 1) newCards = newCards.slice(0, 1);
    if (newCards.length === 0) return;

    var delayMs = 200;
    var dealClass = 'deal-community';
    if (newCards.length === 3 && existingCount === 0) {
        delayMs = 220;
        dealClass = 'deal-flop';
    } else if (newCards.length === 1 && existingCount === 3) {
        delayMs = 0;
        dealClass = 'deal-turn';
    } else if (newCards.length === 1 && existingCount === 4) {
        delayMs = 0;
        dealClass = 'deal-river';
    } else {
        delayMs = 200;
        dealClass = 'deal-community';
    }

    const isRed = (s) => s === '♥' || s === '♦';
    newCards.forEach(function (cardData, index) {
        setTimeout(function () {
            const cardDiv = document.createElement('div');
            var suit, rank;
            if (cardData && typeof cardData === 'object' && ('suit' in cardData || 'rank' in cardData)) {
                suit = cardData.suit != null ? cardData.suit : '?';
                rank = cardData.rank != null ? cardData.rank : '?';
            } else if (typeof cardData === 'string' && cardData.length >= 2) {
                rank = cardData[0];
                var sc = cardData[1];
                suit = { H: '♥', D: '♦', C: '♣', S: '♠' }[sc] || '?';
            } else {
                suit = '?';
                rank = '?';
            }
            const suitClass = isRed(suit) ? 'red' : 'black';
            cardDiv.className = 'card ' + suitClass + ' ' + dealClass;
            cardDiv.innerText = suit + rank;
            container.appendChild(cardDiv);
            setTimeout(function () { cardDiv.classList.add('visible'); }, 50);
        }, index * delayMs);
    });
}

function showWinnerAnimation(winnerInfo, winnerIdx, players, winnerAmount) {
    const overlay = document.getElementById('winner-overlay');
    const textEl = document.getElementById('winner-text');
    const amountEl = document.getElementById('winner-amount');
    if (!overlay || !textEl) return;
    const winnerName = players && players[winnerIdx] ? players[winnerIdx].name : '';
    textEl.textContent = winnerName ? winnerName + ' 获胜！' : (winnerInfo || '比牌结束');
    if (amountEl) {
        if (winnerAmount != null && winnerAmount > 0) {
            amountEl.textContent = '赢得 ' + winnerAmount + ' 筹码';
            amountEl.style.display = 'block';
        } else {
            amountEl.textContent = '';
            amountEl.style.display = 'none';
        }
    }
    overlay.classList.remove('hidden');
    overlay.setAttribute('aria-hidden', 'false');
    runConfetti();
    setTimeout(function () {
        overlay.classList.add('visible');
    }, 50);
    setTimeout(function () {
        overlay.classList.remove('visible');
        setTimeout(function () {
            overlay.classList.add('hidden');
            overlay.setAttribute('aria-hidden', 'true');
            stopConfetti();
        }, 600);
    }, 4000);
}

function hideWinnerOverlay() {
    const overlay = document.getElementById('winner-overlay');
    if (overlay) {
        overlay.classList.add('hidden');
        overlay.classList.remove('visible');
        overlay.setAttribute('aria-hidden', 'true');
        stopConfetti();
    }
}

function runConfetti() {
    const container = document.getElementById('confetti-container');
    if (!container) return;
    container.innerHTML = '';
    const colors = ['#ffd700', '#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#ffeaa7'];
    for (var i = 0; i < 60; i++) {
        var p = document.createElement('div');
        p.className = 'confetti-piece';
        p.style.left = Math.random() * 100 + '%';
        p.style.animationDelay = Math.random() * 0.5 + 's';
        p.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
        p.style.transform = 'rotate(' + (Math.random() * 360) + 'deg)';
        container.appendChild(p);
    }
}

function stopConfetti() {
    const container = document.getElementById('confetti-container');
    if (container) container.innerHTML = '';
}
