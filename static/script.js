// dzpokerV3/static/script.js - 支持多人在线：table + token，WebSocket 实时同步
// 客户端仅监控当前单桌；服务端监管所有牌桌。

let lastState = null;
let tableId = null;
let token = null;
let mySeat = 0;
let socket = null;
/** 上次收到状态更新的时间（用于检测 WebSocket 漏推时轮询拉取） */
var lastStateUpdateTime = 0;
/** 自动开始下一局的定时器 ID，避免重复调度 */
var autoNextHandTimeout = null;
/** 已展示的获胜信息，避免同一局多次触发弹窗动画 */
var lastShownWinnerInfo = null;

/** 多套表情包：key 为包名，value 为 [ emoji, label ] 或 emoji 字符串 */
const EMOTE_PACKS = {
    default: { name: '默认', emotes: ['👍', '😂', '😎', '🙏', '😤', '🎉', '👋', '❤️'] },
    funny: { name: '搞笑', emotes: ['🤣', '😭', '🤔', '😏', '🙄', '😈', '💀', '🤡'] },
    poker: { name: '扑克脸', emotes: ['😐', '😑', '😶', '🃏', '🎴', '💰', '🔥', '⚡'] },
    festival: { name: '节日', emotes: ['🎄', '🎃', '🎆', '🧧', '🎁', '🌸', '🌟', '✨'] },
    vip: { name: 'VIP', emotes: ['👑', '💎', '🏆', '🥇', '🎖️', '💵', '🛡️', '⚔️'] }
};
const EMOTE_PACK_IDS = Object.keys(EMOTE_PACKS);
const EMOTE_STORAGE_KEY = 'dzpoker_emote_pack';
/** 表情显示时长（毫秒），到点后自动消失，且同一表情不会因轮到己方而重复弹出 */
const EMOTE_DISPLAY_TTL_MS = 3000;
/** 已展示过的表情：realSeat -> emote 字符串，避免每次 state 更新都重新弹出 */
var emoteShownForSeat = {};

/** 按玩家名/ID 取稳定头像编号 1–8，同一玩家始终同款 */
function avatarIndexForPlayer(nameOrId) {
    var s = String(nameOrId || '').trim() || '?';
    var h = 0;
    for (var i = 0; i < s.length; i++) h = ((h << 5) - h) + s.charCodeAt(i) | 0;
    return (Math.abs(h) % 8) + 1;
}

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

/** 面额与颜色：紫500/黑100/绿25/蓝10/红5/白1，对应 /static 下 chip-*.png */
var CHIP_DENOMS = [500, 100, 25, 10, 5, 1];
var CHIP_COLORS = ['purple', 'black', 'green', 'blue', 'red', 'white'];

/** 按面额拆分金额，返回筹码颜色列表，最多 maxChips 枚 */
function amountToChipClasses(amount, maxChips) {
    amount = Math.max(0, Math.floor(Number(amount) || 0));
    if (amount === 0 || maxChips < 1) return [];
    var list = [];
    var rest = amount;
    for (var d = 0; d < CHIP_DENOMS.length && list.length < maxChips; d++) {
        while (rest >= CHIP_DENOMS[d] && list.length < maxChips) {
            list.push(CHIP_COLORS[d]);
            rest -= CHIP_DENOMS[d];
        }
    }
    if (list.length === 0) list.push('red');
    return list;
}

/** 展示用：优先多种颜色（紫/黑/绿/蓝/红/白），再从剩余金额填满至 maxChips；小金额也从低面额起各取一枚以增加颜色 */
function chipClassesForDisplay(amount, maxChips) {
    amount = Math.max(0, Math.floor(Number(amount) || 0));
    if (amount === 0 || maxChips < 1) return [];
    var list = [];
    var rest = amount;
    /* 从低面额到高面额各取一枚（能取就取），这样小金额也能出现多色 */
    var lowToHigh = [1, 5, 10, 25, 100, 500];
    var lowToHighColors = ['white', 'red', 'blue', 'green', 'black', 'purple'];
    for (var i = 0; i < lowToHigh.length && list.length < maxChips && rest >= lowToHigh[i]; i++) {
        list.push(lowToHighColors[i]);
        rest -= lowToHigh[i];
    }
    /* 剩余金额用高面额贪心填满到 maxChips */
    for (var d = CHIP_DENOMS.length - 1; d >= 0 && list.length < maxChips; d--) {
        while (rest >= CHIP_DENOMS[d] && list.length < maxChips) {
            list.push(CHIP_COLORS[d]);
            rest -= CHIP_DENOMS[d];
        }
    }
    if (list.length === 0) list.push('red');
    return list;
}

/** 按筹码量决定牌桌上显示的枚数上限：少则少显示，多则多显示，便于区分 */
function maxChipsForSeatDisplay(amount) {
    amount = Math.max(0, Math.floor(Number(amount) || 0));
    if (amount === 0) return 0;
    if (amount < 50) return 2;
    if (amount < 200) return 4;
    if (amount < 800) return 6;
    return 8;
}

/** 牌桌中心底池：多色筹码（紫/黑/绿/蓝/红/白）随机摞几堆，使用 /static 下 chip-*.png */
function updatePotChips(potNum) {
    var el = document.getElementById('pot-chips');
    if (!el) return;
    var classes = chipClassesForDisplay(potNum, 8);
    if (classes.length === 0) {
        el.innerHTML = '';
        return;
    }
    var seed = potNum % 97;
    var numPiles = 2 + (seed % 2);
    var piles = [];
    for (var p = 0; p < numPiles; p++) {
        piles.push([]);
    }
    for (var i = 0; i < classes.length; i++) {
        piles[i % numPiles].push(classes[i]);
    }
    var html = '';
    for (var j = 0; j < piles.length; j++) {
        if (piles[j].length === 0) continue;
        html += '<span class="pot-pile">';
        for (var k = 0; k < piles[j].length; k++) {
            html += '<span class="chip chip-pot chip-' + piles[j][k] + '" aria-hidden="true"></span>';
        }
        html += '</span>';
    }
    el.innerHTML = html;
}

/** 牌桌音效：chip=下注/跟注/加注, fold=弃牌, win=获胜。受设置 soundEnabled / .sound-disabled 控制 */
function playGameSound(type) {
    if (document.body && document.body.classList.contains('sound-disabled')) return;
    try {
        var C = window.AudioContext || window.webkitAudioContext;
        if (!C) return;
        var ctx = window._gameAudioContext || (window._gameAudioContext = new C());
        if (ctx.state === 'suspended') ctx.resume();
        var now = ctx.currentTime;

        /** 下注/跟注：短促柔和的“叮”声（正弦波 + 快速衰减），替代原先白噪声 */
        function chipTick(when) {
            var sr = ctx.sampleRate;
            var dur = 0.038;
            var len = Math.floor(sr * dur);
            var buf = ctx.createBuffer(1, len, sr);
            var d = buf.getChannelData(0);
            var freq = 880;
            for (var i = 0; i < len; i++) {
                var t = i / sr;
                var env = Math.pow(1 - t / dur, 2);
                d[i] = 0.28 * Math.sin(2 * Math.PI * freq * t) * env;
            }
            var src = ctx.createBufferSource();
            src.buffer = buf;
            var g = ctx.createGain();
            g.gain.setValueAtTime(0.5, when);
            g.gain.exponentialRampToValueAtTime(0.001, when + dur);
            src.connect(g);
            g.connect(ctx.destination);
            src.start(when);
            src.stop(when + dur);
        }

        if (type === 'chip') {
            chipTick(now);
            chipTick(now + 0.048);
        } else if (type === 'fold') {
            /* 弃牌：低频纸张划过声 */
            var sr2 = ctx.sampleRate;
            var len2 = Math.floor(sr2 * 0.14);
            var buf2 = ctx.createBuffer(1, len2, sr2);
            var d2 = buf2.getChannelData(0);
            for (var i = 0; i < len2; i++) {
                d2[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len2, 2.2) * 0.6;
            }
            var src2 = ctx.createBufferSource();
            src2.buffer = buf2;
            var lp = ctx.createBiquadFilter();
            lp.type = 'lowpass'; lp.frequency.value = 900;
            var g2 = ctx.createGain();
            g2.gain.setValueAtTime(0.22, now);
            g2.gain.exponentialRampToValueAtTime(0.001, now + 0.13);
            src2.connect(lp); lp.connect(g2); g2.connect(ctx.destination);
            src2.start(now); src2.stop(now + 0.14);
        } else if (type === 'win') {
            /* 获胜：一串筹码雨（8 枚连续落桌，频率递增） */
            for (var k = 0; k < 8; k++) {
                (function(delay, freq) {
                    var sr3 = ctx.sampleRate;
                    var len3 = Math.floor(sr3 * 0.07);
                    var buf3 = ctx.createBuffer(1, len3, sr3);
                    var d3 = buf3.getChannelData(0);
                    for (var i = 0; i < len3; i++) {
                        d3[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len3, 4);
                    }
                    var src3 = ctx.createBufferSource();
                    src3.buffer = buf3;
                    var bp3 = ctx.createBiquadFilter();
                    bp3.type = 'bandpass'; bp3.frequency.value = freq; bp3.Q.value = 3.5;
                    var g3 = ctx.createGain();
                    g3.gain.setValueAtTime(0.35, now + delay);
                    g3.gain.exponentialRampToValueAtTime(0.001, now + delay + 0.07);
                    src3.connect(bp3); bp3.connect(g3); g3.connect(ctx.destination);
                    src3.start(now + delay); src3.stop(now + delay + 0.08);
                })(k * 0.065, 3200 + k * 280);
            }
        }
    } catch (e) { /* 静默忽略 */ }
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
    const fillBotsBtn = document.getElementById('fill-bots-btn');
    if (fillBotsBtn) {
        fillBotsBtn.addEventListener('click', function () {
            if (!tableId || !token) return;
            fillBotsBtn.disabled = true;
            fillBotsBtn.textContent = '拉取中…';
            fetch(apiUrl('/api/tables/' + tableId + '/fill_bots'), { method: 'POST' })
                .then(function (r) { return r.json().catch(function () { return {} }); })
                .then(function (body) {
                    fillBotsBtn.disabled = false;
                    fillBotsBtn.textContent = '拉机器人';
                    loadTableAndGame();
                })
                .catch(function () {
                    fillBotsBtn.disabled = false;
                    fillBotsBtn.textContent = '拉机器人';
                    loadTableAndGame();
                });
        });
    }
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
        const raw = betAmountInput.value != null && betAmountInput.value !== '' ? betAmountInput.value : (betSlider ? betSlider.value : '0');
        const totalToPut = parseInt(raw, 10);
        if (isNaN(totalToPut) || totalToPut <= 0) {
            alert('请输入有效的下注金额');
            return;
        }
        /* 有人已下注时后端要求发 raise（加注额=总投入-当前跟注额），否则发 bet */
        const amountToCall = (lastState && lastState.amount_to_call != null) ? lastState.amount_to_call : 0;
        const action = amountToCall > 0 ? 'raise' : 'bet';
        let sendAmount = action === 'raise' ? (totalToPut - amountToCall) : totalToPut;
        sendAmount = Math.max(0, Math.floor(sendAmount));
        if (action === 'raise' && sendAmount <= 0) {
            alert('加注额必须大于当前跟注额，请调整拉杆或输入金额');
            return;
        }
        sendAction(action, sendAmount);
    });
    if (betSlider) {
        betSlider.addEventListener('input', () => {
            betAmountInput.value = betSlider.value;
        });
    }
    var autoPilotBtn = document.getElementById('auto-pilot-btn');
    if (autoPilotBtn) {
        window._autoPilotEnabled = localStorage.getItem('dzpoker_auto_pilot') === '1';
        autoPilotBtn.classList.toggle('on', window._autoPilotEnabled);
        autoPilotBtn.addEventListener('click', function () {
            window._autoPilotEnabled = !window._autoPilotEnabled;
            localStorage.setItem('dzpoker_auto_pilot', window._autoPilotEnabled ? '1' : '0');
            autoPilotBtn.classList.toggle('on', window._autoPilotEnabled);
        });
    }
    (function initEmoteBar() {
        var packSelect = document.getElementById('emote-pack-select');
        var btnContainer = document.getElementById('emote-bar-btns');
        if (!packSelect || !btnContainer) return;
        function getCurrentPack() {
            var id = (typeof localStorage !== 'undefined' && localStorage.getItem(EMOTE_STORAGE_KEY)) || 'default';
            return EMOTE_PACK_IDS.indexOf(id) >= 0 ? id : 'default';
        }
        function setCurrentPack(id) {
            if (typeof localStorage !== 'undefined') localStorage.setItem(EMOTE_STORAGE_KEY, id);
        }
        function renderEmoteBar() {
            var packId = getCurrentPack();
            var pack = EMOTE_PACKS[packId];
            if (!pack) pack = EMOTE_PACKS.default;
            packSelect.innerHTML = EMOTE_PACK_IDS.map(function (id) {
                return '<option value="' + id + '"' + (id === packId ? ' selected' : '') + '>' + (EMOTE_PACKS[id].name) + '</option>';
            }).join('');
            btnContainer.innerHTML = (pack.emotes || []).map(function (e) {
                return '<button type="button" class="emote-btn" data-emote="' + String(e).replace(/"/g, '&quot;') + '" title="' + String(e) + '">' + e + '</button>';
            }).join('');
        }
        renderEmoteBar();
        packSelect.addEventListener('change', function () {
            setCurrentPack(this.value);
            renderEmoteBar();
        });
        btnContainer.addEventListener('click', function (e) {
            var btn = e.target && e.target.closest('.emote-btn');
            if (btn) {
                var emote = btn.getAttribute('data-emote');
                if (emote) sendEmote(emote);
            }
        });
    })();

    const chatToggleBtn = document.getElementById('chat-toggle-btn');
    const chatPanel = document.getElementById('chat-panel');
    const chatInput = document.getElementById('chat-input');
    const chatSendBtn = document.getElementById('chat-send-btn');
    const chatMessages = document.getElementById('chat-messages');
    if (chatToggleBtn && chatPanel) {
        chatToggleBtn.addEventListener('click', function () {
            const visible = chatPanel.style.display === 'block';
            chatPanel.style.display = visible ? 'none' : 'block';
            chatToggleBtn.setAttribute('aria-expanded', visible ? 'false' : 'true');
        });
    }
    function appendChatLine(seatLabel, text, isMe) {
        if (!chatMessages) return;
        const div = document.createElement('div');
        div.className = 'chat-line' + (isMe ? ' chat-line-me' : '');
        div.textContent = (seatLabel ? seatLabel + ': ' : '') + text;
        chatMessages.appendChild(div);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    window.appendChatMessage = function (seat, username, message) {
        const label = username || ('座位' + (seat != null ? seat + 1 : '?'));
        appendChatLine(label, message || '', false);
    };
    if (chatSendBtn && chatInput) {
        function sendChat() {
            const msg = (chatInput.value || '').trim();
            if (!msg) return;
            if (socket && socket.connected) {
                socket.emit('game:chat_message', { message: msg });
            }
            appendChatLine('我', msg, true);
            chatInput.value = '';
        }
        chatSendBtn.addEventListener('click', sendChat);
        chatInput.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') { e.preventDefault(); sendChat(); }
        });
    }

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

    // WebSocket 漏推时兜底：轮到机器人且超过 3 秒未收到状态更新则用 GET 拉取，避免界面一直停在「坚果成牌」等
    if (window._stateStalePoll) clearInterval(window._stateStalePoll);
    window._stateStalePoll = setInterval(function () {
        if (!tableId || !token || !lastState || !lastState.is_running) return;
        var mySeatNum = (typeof mySeat !== 'undefined') ? mySeat : -1;
        if (lastState.current_player_idx === mySeatNum) return;
        if (Date.now() - lastStateUpdateTime < 3000) return;
        loadTableAndGame();
    }, 2000);
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
            mySeat = data.my_seat >= 0 ? data.my_seat : 0;
            var myStack = (data.seats && data.seats[mySeat] && data.seats[mySeat].stack != null) ? data.seats[mySeat].stack : 0;
            if (actionsEl) actionsEl.style.display = (mySeat >= 0 && myStack > 0) ? '' : 'none';
            var leaveWrap = document.getElementById('leave-seat-wrap');
            if (data.status === 'waiting') {
                if (leaveWrap) leaveWrap.style.display = (mySeat >= 0 ? 'block' : 'none');
                var fillBotsEl = document.getElementById('fill-bots-btn');
                if (fillBotsEl) fillBotsEl.style.display = (mySeat >= 0 ? 'inline-block' : 'none');
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
                if (fillBotsEl) fillBotsEl.style.display = (mySeat >= 0 ? 'inline-block' : 'none');
                return;
            }
            if (document.getElementById('fill-bots-btn')) document.getElementById('fill-bots-btn').style.display = 'none';
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
    socket.on('game:deal_phase', function (payload) {
        if (payload && payload.phase) playDealPhaseAnimation(payload.phase, payload.cards || []);
    });
    socket.on('game:state_update', function (state) {
        lastStateUpdateTime = Date.now();
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
    socket.on('game:chat_message', function (data) {
        if (typeof window.appendChatMessage === 'function') {
            window.appendChatMessage(data.seat, data.username, data.message);
        }
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
    /* 轮到机器人时禁止发送，避免 400；若 lastState 未更新（如断线）也尽量不误发 */
    if (lastState && lastState.is_running && lastState.current_player_idx !== undefined && lastState.current_player_idx !== null) {
        var mySeatNum = (typeof mySeat !== 'undefined') ? mySeat : -1;
        if (lastState.current_player_idx !== mySeatNum) {
            if (typeof console !== 'undefined' && console.warn) console.warn('当前不是您的回合，请等待对方下注');
            return;
        }
    }
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
    }).then(function (r) {
        return r.json().then(function (s) {
            if (s && s.error) {
                alert(s.error);
                if (r.status === 400 && tableId && token && typeof loadTableAndGame === 'function') loadTableAndGame();
            }
            if (s && !s.error) updateUI(s);
        });
    }).catch(function () {
        if (tableId && token && typeof loadTableAndGame === 'function') loadTableAndGame();
    });
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

function showTableEmote(emoteChar) {
    var table = document.querySelector('.poker-table');
    if (!table || !emoteChar) return;
    var existing = document.getElementById('table-emote-center');
    if (!existing) {
        existing = document.createElement('div');
        existing.id = 'table-emote-center';
        existing.className = 'table-emote-center';
        table.appendChild(existing);
    }
    existing.innerHTML = '<span class="seat-emote-bubble emote-visible" aria-label="表情">' + emoteChar + '</span>';
    existing.style.display = 'block';
    setTimeout(function () {
        if (existing) existing.style.display = 'none';
    }, EMOTE_DISPLAY_TTL_MS);
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
    }).then(function (r) { return r.json(); }).then(function (s) {
        if (s && s.error) return;
        if (s && s.deal_phase) playDealPhaseAnimation(s.deal_phase, s.deal_cards || []);
        if (s && !s.error) updateUI(s);
    });
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
        has_folded: player.has_folded != null ? player.has_folded : !player.is_in_hand,
        is_all_in: player.is_all_in || false
    };
}

function updateUI(state) {
    lastStateUpdateTime = Date.now();
    var prevPot = lastState && lastState.pot != null ? lastState.pot : 0;
    var prevBets = (lastState && lastState.players) ? lastState.players.map(function (p) {
        return p && (p.current_bet != null ? p.current_bet : (p.bet_this_round != null ? p.bet_this_round : 0));
    }) : [];
    var prevStage = (lastState && lastState.stage != null) ? String(lastState.stage).toLowerCase() : '';
    lastState = state;
    var stage = (state.stage != null ? String(state.stage) : '').toLowerCase();
    var stageVal = stage;
    document.getElementById('stage-display').innerText = stageLabel(stageVal);
    const turnEl = document.getElementById('turn-display');
    if (window._turnCountdownInterval) {
        clearInterval(window._turnCountdownInterval);
        window._turnCountdownInterval = null;
    }
    if (turnEl) {
        var curIdx = state.current_player_idx;
        var hasCurrentPlayer = state.is_running && curIdx != null && curIdx !== undefined;
        /* 轮到任何人（含机器人）都显示「轮到 XXX 下注」；进度条改由各座位内 .seat-countdown 显示 */
        if (hasCurrentPlayer) {
            var whoName = (state.current_player_name && state.current_player_name.trim()) || (state.players && state.players[curIdx] && state.players[curIdx].name) || ('座位 ' + (curIdx + 1));
            turnEl.textContent = '轮到 ' + whoName + ' 下注';
            turnEl.style.display = 'block';
            if (curIdx !== window._countdownForSeat) {
                window._countdownForSeat = curIdx;
                window._countdownElapsed = 0;
                window._countdownTotalSec = 5;
                if (window._turnCountdownInterval) clearInterval(window._turnCountdownInterval);
                window._turnCountdownInterval = setInterval(function tick() {
                    if (window._countdownForSeat == null) return;
                    window._countdownElapsed = (window._countdownElapsed || 0) + 0.1;
                    var left = Math.max(0, (window._countdownTotalSec || 5) - window._countdownElapsed);
                    var pct = (left / (window._countdownTotalSec || 5)) * 100;
                    var seatEl = document.querySelector('.seat-countdown[data-seat-id="' + window._countdownForSeat + '"]');
                    if (seatEl) {
                        var bar = seatEl.querySelector('.turn-countdown-bar');
                        var text = seatEl.querySelector('.turn-countdown-text');
                        if (bar) bar.style.width = pct + '%';
                        if (text) text.textContent = Math.ceil(left);
                        seatEl.style.display = 'flex';
                    }
                    if (left <= 0) {
                        if (window._turnCountdownInterval) { clearInterval(window._turnCountdownInterval); window._turnCountdownInterval = null; }
                        if (seatEl) seatEl.style.display = 'none';
                        window._countdownForSeat = null;
                    }
                }, 100);
            }
        } else {
            window._countdownForSeat = null;
            if (window._turnCountdownInterval) { clearInterval(window._turnCountdownInterval); window._turnCountdownInterval = null; }
            if (state.street_label && stage !== 'showdown' && stage !== 'ended') {
                turnEl.textContent = state.street_label + ' · 等待下注';
                turnEl.style.display = 'block';
            } else {
                turnEl.textContent = '';
                turnEl.style.display = 'none';
            }
        }
    }
    document.getElementById('pot-display').innerText = state.pot != null ? state.pot : 0;
    var potNum = state.pot != null ? state.pot : 0;
    updatePotChips(potNum);
    if (potNum > prevPot) {
        var potWrap = document.getElementById('pot-display');
        if (potWrap && potWrap.parentElement) {
            potWrap.parentElement.classList.add('pot-bump');
            setTimeout(function () { potWrap.parentElement.classList.remove('pot-bump'); }, 500);
        }
    }
    const sidePotEl = document.getElementById('side-pots-display');
    if (sidePotEl) {
        var hasSidePots = state.side_pots && state.side_pots.length > 0;
        if (!hasSidePots) {
            sidePotEl.innerHTML = '';
            sidePotEl.style.display = 'none';
        } else {
            var parts = state.side_pots.map(function (p, i) {
                var amt = p.amount != null ? p.amount : p;
                return '边' + (i + 1) + ':' + amt;
            });
            sidePotEl.innerHTML = parts.map(function (s) { return '<span class="side-pot-item">' + s + '</span>'; }).join('');
            sidePotEl.style.display = 'block';
        }
    }
    var streetBetCallEl = document.getElementById('street-bet-call-display');
    if (streetBetCallEl && state.is_running) {
        var atc = state.amount_to_call != null ? state.amount_to_call : 0;
        var callAmt = state.call_amount != null ? state.call_amount : 0;
        if (atc > 0 || callAmt > 0) {
            streetBetCallEl.innerHTML = '本街最高下注 <strong>' + atc + '</strong> &nbsp; 需跟注 <strong>' + callAmt + '</strong>';
            streetBetCallEl.style.display = 'block';
        } else {
            streetBetCallEl.innerHTML = '';
            streetBetCallEl.style.display = 'none';
        }
    } else if (streetBetCallEl) {
        streetBetCallEl.innerHTML = '';
        streetBetCallEl.style.display = 'none';
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
        /* 牌型实时显示（后端翻牌后返回 my_hand_type） */
        var handTypeDisplayEl = document.getElementById('my-hand-type-display');
        if (handTypeDisplayEl) handTypeDisplayEl.textContent = state.my_hand_type || '—';
    } else {
        if (myStatsEl) myStatsEl.style.display = 'none';
        if (streetHintEl) streetHintEl.style.display = 'none';
        var handTypeDisplayEl = document.getElementById('my-hand-type-display');
        if (handTypeDisplayEl) handTypeDisplayEl.textContent = '—';
    }
    document.getElementById('last-action-display').innerText = state.last_action || '';
    if (state.last_action && state.last_action.indexOf('弃牌') >= 0) playGameSound('fold');

    const communityContainer = document.getElementById('community-cards-display');
    var communityCards = state.community_cards || [];

    /* 仅在新一局 preflop 且尚无公共牌时清空；ended 时保留公共牌显示 */
    if (stage === 'preflop' && communityCards.length === 0) {
        communityContainer.innerHTML = '';
    }
    animateCards(communityContainer, communityCards, stage);

    /* 牌型仅显示在己方控制台 #my-hand-type-display，不在桌面中央展示 */

    const playersContainer = document.getElementById('player-seats');
    /* 使用各座位内嵌的 .seat-countdown，不再移动全局 countdown 节点 */
    playersContainer.innerHTML = '';
    var maxSeats = state.max_players || (state.players && state.players.length) || 6;
    /* prevStage 用于己方手牌：仅在本局首次进入 preflop 时播发牌动画，避免每次 state 更新都闪 */
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

    /* 本局手牌发牌动画样式随机（1–9 多种搞笑款，每轮可不同） */
    var holeDealStyle = 'deal-hole-' + (1 + Math.floor(Math.random() * 9));

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
        if (p.has_folded) seatDiv.classList.add('player-seat-folded');
        /* 筹码为 0 的玩家不渲染（含己方）：按约定不显示在牌桌、不轮询、不显示控制台 */
        if ((p.chips != null ? p.chips : 0) === 0) continue;
        const isDealer = state.dealer_idx === realSeat;
        const isSB = state.sb_idx === realSeat;
        const isBB = state.bb_idx === realSeat;
        const isWinner = state.winner_idx === realSeat || (Array.isArray(state.winner_idxs) && state.winner_idxs.indexOf(realSeat) !== -1);
        /* 位置徽章 D/SB/BB 放在手牌上方；轮到你 保留在信息区 */
        const positionBadges = [];
        if (isDealer) positionBadges.push('<span class="badge dealer">D</span>');
        if (isSB) positionBadges.push('<span class="badge sb">SB</span>');
        if (isBB) positionBadges.push('<span class="badge bb">BB</span>');
        const turnBadge = (state.current_player_idx === realSeat && state.is_running)
            ? '<span class="badge active-turn" aria-live="polite">轮到你</span>' : '';
        var rawName = p.name || '玩家';
        var displayName = rawName.length > 10 ? rawName.substring(0, 10) + '...' : rawName;

        const emoteInfo = state.emotes && state.emotes[String(realSeat)];
        const emoteChar = emoteInfo && emoteInfo.emote ? String(emoteInfo.emote).replace(/</g, '&lt;') : '';
        const alreadyShown = emoteShownForSeat[realSeat] === (emoteInfo && emoteInfo.emote ? String(emoteInfo.emote) : '');
        const showEmote = emoteChar && !alreadyShown;
        if (showEmote) {
            emoteShownForSeat[realSeat] = emoteInfo.emote ? String(emoteInfo.emote) : '';
            setTimeout(function () { emoteShownForSeat[realSeat] = undefined; }, EMOTE_DISPLAY_TTL_MS);
            showTableEmote(emoteChar);
        }

        let handHtml = '';
        /* 仅自己或摊牌/结束阶段显示牌面；摊牌后未弃牌玩家的手牌对所有人可见 */
        const showCardFaces = (realSeat === mySeat || stage === 'showdown' || stage === 'ended') && p.hand && p.hand.length > 0;
        const isRed = (s) => s === '♥' || s === '♦';
        /* 发牌动画：preflop 且有两张底牌时，首次出现则播（己方：上一帧没有两张牌也播，避免后端先发 preflop 再发 hand 导致不播） */
        var prevHand = lastState && lastState.players && lastState.players[realSeat] && lastState.players[realSeat].hand;
        var prevHadTwo = Array.isArray(prevHand) && prevHand.length >= 2;
        const isPreflopDeal = stage === 'preflop' && !p.has_folded && (p.hand && p.hand.length === 2 || !showCardFaces) && (realSeat !== mySeat || prevStage !== 'preflop' || !prevHadTwo);
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
            /* 若后端未下发该座位的 hand 导致 handHtml 仍为空，仍显示 2 张牌背，避免最上/右下角等座位牌不显示 */
            if (!handHtml && !p.has_folded) {
                handHtml = '<div class="card-back"></div><div class="card-back"></div>';
            }
        } else {
            const count = p.has_folded ? 0 : 2;
            for (let k = 0; k < count; k++) {
                const delay = k === 0 ? holeDelay0 : holeDelay1;
                const dealStyle = isPreflopDeal ? ' style="animation-delay: ' + delay + 'ms"' : '';
                const dealClass = isPreflopDeal ? holeStyleClass : '';
                handHtml += '<div class="card-back' + dealClass + '"' + dealStyle + '></div>';
            }
        }
        /* 兜底：未弃牌但 hand 为空时仍显示 2 张牌背，避免顶部/右下角等座位牌不显示 */
        if (handHtml === '' && !p.has_folded) {
            handHtml = '<div class="card-back"></div><div class="card-back"></div>';
        }

        /* 每个座位内嵌倒计时条，轮到该座位时显示（含机器人），避免移动 DOM 导致不显示 */
        var seatCountdownHtml = '<div class="seat-countdown turn-countdown-wrap turn-countdown-under-seat" data-seat-id="' + realSeat + '" style="display:none;" aria-label="行动倒计时">' +
            '<div class="turn-countdown-track"><div class="turn-countdown-bar" style="width:100%"></div></div>' +
            '<span class="turn-countdown-text">5</span></div>';
        var stackAmt = p.chips != null ? p.chips : 0;
        seatDiv.setAttribute('data-seat-display', String(i));
        var maxChips = maxChipsForSeatDisplay(stackAmt);
        var stackClasses = maxChips > 0 ? chipClassesForDisplay(stackAmt, maxChips) : [];
        var numPiles = stackClasses.length > 0 ? (2 + ((realSeat + (p.name || '').length) % 2)) : 0;
        var seatPiles = [];
        for (var pp = 0; pp < numPiles; pp++) seatPiles.push([]);
        for (var sc = 0; sc < stackClasses.length; sc++) {
            seatPiles[sc % numPiles].push(stackClasses[sc]);
        }
        var pileHtml = '';
        for (var px = 0; px < seatPiles.length; px++) {
            pileHtml += '<span class="seat-chips-pile" aria-hidden="true">';
            for (var py = 0; py < seatPiles[px].length; py++) {
                pileHtml += '<span class="chip chip-stack chip-' + (seatPiles[px][py] || 'red') + '" aria-hidden="true"></span>';
            }
            if (seatPiles[px].length === 0 && stackClasses.length > 0) pileHtml += '<span class="chip chip-stack chip-red" aria-hidden="true"></span>';
            pileHtml += '</span>';
        }
        if (stackClasses.length > 0 && pileHtml.indexOf('chip chip-stack') === -1) {
            pileHtml = '<span class="seat-chips-pile" aria-hidden="true"><span class="chip chip-stack chip-red"></span></span><span class="seat-chips-pile" aria-hidden="true"><span class="chip chip-stack chip-red"></span></span>';
        }
        /* 座位角度（用于桌面上的筹码/下注定位，rx=40/ry=34 保证在毡面内） */
        var tableAngleRad = (90 - (i * 360 / maxSeats)) * Math.PI / 180;
        var seatHandTypes = state.seat_hand_types || {};
        var seatHandType = seatHandTypes.hasOwnProperty(realSeat) ? seatHandTypes[realSeat] : null;
        seatDiv.innerHTML =
            '<div class="seat-main">' +
            '<div class="player-hand-area">' +
            (positionBadges.length ? '<div class="player-hand-badges">' + positionBadges.join('') + '</div>' : '') +
            '<div class="player-hand-wrap"><div class="player-hand">' + handHtml + '</div></div>' +
            '</div>' +
            '<div class="player-info ' + (state.current_player_idx === realSeat && state.is_running ? 'active' : '') + ' ' + (p.has_folded ? 'folded' : '') + (isWinner ? ' winner' : '') + '">' +
            '<div class="player-meta">' +
            (function () {
                var initial = (rawName && rawName.length > 0) ? String(rawName).charAt(0) : '?';
                var avatarClass = 'avatar-' + avatarIndexForPlayer(p.name || p.player_id || realSeat);
                return '<div class="player-avatar ' + avatarClass + '" aria-hidden="true" title="' + (rawName.replace(/"/g, '&quot;')) + '"><span class="avatar-initial">' + (initial.replace(/</g, '&lt;').replace(/>/g, '&gt;')) + '</span></div>';
            }()) +
            (turnBadge ? '<div class="badges">' + turnBadge + '</div>' : '') +
            '<strong title="' + (rawName.replace(/"/g, '&quot;')) + '">' + (displayName.replace(/</g, '&lt;').replace(/>/g, '&gt;')) + '</strong>' +
            (state.winnings_by_seat && state.winnings_by_seat[realSeat] > 0 ? '<span class="win-amount">+' + state.winnings_by_seat[realSeat] + '</span>' : '') +
            '<div class="player-meta-footer">' +
            (p.is_all_in ? '<span class="all-in-tag">All-in</span>' : '') +
            (seatHandType ? '<span class="seat-hand-type">' + seatHandType + '</span>'
                : (realSeat === mySeat && state.my_hand_type ? '<span class="my-hand-type">' + state.my_hand_type + '</span>' : '')) +
            '</div>' +
            '</div></div></div>' +
            seatCountdownHtml;
        playersContainer.appendChild(seatDiv);
        /* 筹码组：总筹码与本街下注并排显示在桌面同一位置 */
        if (stackAmt > 0) {
            var chipRadiusX = 44;
            var chipRadiusY = 43;
            var betAmt = p.current_bet != null ? p.current_bet : 0;
            var betHtml = '';
            if (betAmt > 0) {
                var betClasses = amountToChipClasses(betAmt, 2);
                var betChipHtml = '';
                for (var bc = 0; bc < 2; bc++) {
                    betChipHtml += '<span class="chip chip-stack chip-' + (betClasses[bc] || 'red') + '" aria-hidden="true"></span>';
                }
                betHtml = '<div class="chips-bet-group" title="本街下注 ' + betAmt + '">' +
                    '<div class="bet-chips-row">' + betChipHtml + '</div>' +
                    '<span class="bet-on-table-value">' + betAmt + '</span>' +
                    '</div>';
            }
            var groupDiv = document.createElement('div');
            groupDiv.className = 'chips-on-table-group';
            groupDiv.setAttribute('data-seat', String(realSeat));
            groupDiv.style.left = (50 + chipRadiusX * Math.cos(tableAngleRad)).toFixed(2) + '%';
            groupDiv.style.top  = (50 + chipRadiusY * Math.sin(tableAngleRad)).toFixed(2) + '%';
            groupDiv.innerHTML =
                '<div class="chips-stack-group" title="筹码 ' + stackAmt + '">' +
                '<div class="seat-chips-piles-wrap">' + pileHtml + '</div>' +
                '<span class="seat-chips-amount">' + stackAmt + '</span>' +
                '</div>' +
                betHtml;
            playersContainer.appendChild(groupDiv);
        }
    }

    /* 下注动效与音效：任意座位（含机器人）本街下注增加时高亮 + 筹码声 */
    if (state.players && prevBets.length >= 0) {
        for (var sb = 0; sb < state.players.length; sb++) {
            var prevBet = prevBets[sb] != null ? prevBets[sb] : 0;
            var curP = state.players[sb];
            var curBet = curP && (curP.current_bet != null ? curP.current_bet : (curP.bet_this_round != null ? curP.bet_this_round : 0));
            if (curBet > prevBet) {
                playGameSound('chip');
                var seatEl = playersContainer.querySelector('.player-seat[data-seat="' + sb + '"]');
                if (seatEl) {
                    var infoEl = seatEl.querySelector('.player-info');
                    if (infoEl) {
                        infoEl.classList.add('bet-bump');
                        (function (el) {
                            setTimeout(function () { el.classList.remove('bet-bump'); }, 450);
                        })(infoEl);
                    }
                }
            }
        }
    }

    /* 显示当前行动座位的倒计时条（含机器人），其余隐藏 */
    document.querySelectorAll('.seat-countdown').forEach(function (el) { el.style.display = 'none'; });
    if (window._countdownForSeat != null) {
        var curSeatCd = document.querySelector('.seat-countdown[data-seat-id="' + window._countdownForSeat + '"]');
        if (curSeatCd) curSeatCd.style.display = 'flex';
    }

    /* 底牌发牌动画：约 0.8s 后为所有带 card-deal-hole 的牌加上 visible，触发收尾动画 */
    setTimeout(function () {
        var holeCards = document.querySelectorAll('.player-hand .card-deal-hole');
        holeCards.forEach(function (el) { el.classList.add('visible'); });
    }, 800);

    const isOurTurn = state.is_running && state.current_player_idx === mySeat;
    const callAmount = state.call_amount || 0;
    const minRaiseTo = state.min_raise_to || 0;
    const myChips = state.players[mySeat] ? state.players[mySeat].chips : 0;
    const pendingStreet = state.pending_street || null;

    /* 筹码为 0 或不在牌桌时不显示控制台（与“0 筹码不显示在牌桌、轮询跳过”一致） */
    var actionsContainer = document.querySelector('.game-area .actions');
    if (actionsContainer) actionsContainer.style.display = (mySeat >= 0 && myChips > 0) ? '' : 'none';

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
            /* 控制台始终显示：已落座且非保险/发牌阶段时一直展示，非自己回合显示等待文案 */
            var showActions = mySeat >= 0;
            var actionControlsEl = document.getElementById('action-controls');
            if (actionControlsEl) {
                actionControlsEl.style.display = showActions ? 'block' : 'none';
                var turnWaitEl = document.getElementById('turn-wait-msg');
                var actionsRow = actionControlsEl.querySelector('.actions-row');
                var myConsoleEl = document.getElementById('my-console');
                if (myConsoleEl && showActions) myConsoleEl.style.display = '';
                if (showActions && turnWaitEl && actionsRow) {
                    var betControlsEl = actionControlsEl.querySelector('.bet-controls');
                    if (state.is_running) {
                        if (isOurTurn) {
                            turnWaitEl.style.display = 'none';
                            actionsRow.style.display = 'flex';
                            if (betControlsEl) betControlsEl.style.display = '';
                            actionsRow.querySelectorAll('button').forEach(function (b) { b.disabled = false; });
                        } else {
                            var who = state.current_player_name || ('座位' + (state.current_player_idx != null ? state.current_player_idx + 1 : '?'));
                            turnWaitEl.textContent = '等待 ' + who + ' 下注';
                            turnWaitEl.style.display = 'block';
                            actionsRow.style.display = 'flex';
                            if (betControlsEl) betControlsEl.style.display = 'none';
                            actionsRow.querySelectorAll('button').forEach(function (b) { b.disabled = b.id === 'auto-pilot-btn' ? false : true; });
                        }
                    } else {
                        turnWaitEl.style.display = 'none';
                        actionsRow.style.display = 'flex';
                        if (betControlsEl) betControlsEl.style.display = 'none';
                        actionsRow.querySelectorAll('button').forEach(function (b) { b.disabled = b.id === 'auto-pilot-btn' ? false : true; });
                    }
                }
            }
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

    /* 托管：轮到己方且开启托管时，延迟后自动过牌/跟注/弃牌 */
    if (window._autoPilotTimeoutId) {
        clearTimeout(window._autoPilotTimeoutId);
        window._autoPilotTimeoutId = null;
    }
    if (isOurTurn && window._autoPilotEnabled && state.is_running && mySeat >= 0 && myChips > 0) {
        window._autoPilotTimeoutId = setTimeout(function () {
            window._autoPilotTimeoutId = null;
            if (callAmount === 0) {
                sendAction('check');
            } else if (callAmount > 0 && callAmount <= myChips) {
                sendAction('call');
            } else {
                sendAction('fold');
            }
        }, 450);
    }

    if (state.winner_info) {
        if (state.winner_info !== lastShownWinnerInfo) {
            lastShownWinnerInfo = state.winner_info;
            showWinnerAnimation(state.winner_info, state.winner_idx, state.players, state.winner_amount, state.winner_hand_type);
        }
        /* 本局已结束：延迟后自动开始下一局，无需点击「开始新一局」 */
        if (!state.is_running && !autoNextHandTimeout && tableId && token) {
            var seated = (state.players || []).filter(function (p) { return p && (p.name || p.user_id); }).length;
            if (seated >= 2) {
                autoNextHandTimeout = setTimeout(function () {
                    autoNextHandTimeout = null;
                    startGame();
                }, 2500);
            }
        }
    } else {
        lastShownWinnerInfo = null;
        hideWinnerOverlay();
        if (autoNextHandTimeout) {
            clearTimeout(autoNextHandTimeout);
            autoNextHandTimeout = null;
        }
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

function parseCardForDisplay(cardData) {
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
    if (suit.length === 1 && suit in { H: 1, D: 1, C: 1, S: 1 }) suit = { H: '♥', D: '♦', C: '♣', S: '♠' }[suit];
    return { suit: suit, rank: rank };
}

/**
 * 发牌阶段动画：根据 game:deal_phase 或 deal_next 返回的 phase/cards 播放对应动画。
 * 建议先播动画（每张 0.2–0.4s），随后 game:state_update 会更新牌面 DOM。
 */
function playDealPhaseAnimation(phase, cards) {
    var container = document.getElementById('community-cards-display');
    if (!container && phase !== 'hole_cards') return;

    function cardToDisplay(card) {
        if (!card) return { suit: '?', rank: '?' };
        var suit = card.suit != null ? card.suit : '?';
        var rank = card.rank != null ? card.rank : '?';
        if (typeof suit === 'string' && suit.length === 1) {
            suit = { H: '♥', D: '♦', C: '♣', S: '♠' }[suit.toUpperCase()] || suit;
        }
        return { suit: suit, rank: rank };
    }
    function isRed(s) { return s === '♥' || s === '♦'; }

    if (phase === 'hole_cards') {
        /* 底牌：无 cards 负载，由随后 state_update 渲染手牌并带 card-deal-hole 动画 */
        return;
    }

    if (phase === 'flop' && cards && cards.length >= 3) {
        var delayMs = 280;
        for (var i = 0; i < 3; i++) {
            var c = cardToDisplay(cards[i]);
            var suitClass = isRed(c.suit) ? 'red' : 'black';
            var variant = 1 + Math.floor(Math.random() * 9);
            var cardDiv = document.createElement('div');
            cardDiv.className = 'card ' + suitClass + ' deal-flop deal-flop-' + variant;
            cardDiv.innerText = c.suit + c.rank;
            container.appendChild(cardDiv);
            (function (el, idx) {
                var delay = 120 + idx * delayMs;
                requestAnimationFrame(function () {
                    requestAnimationFrame(function () {
                        void el.offsetHeight;
                        setTimeout(function () { el.classList.add('visible'); }, delay);
                    });
                });
            })(cardDiv, i);
        }
        return;
    }

    if ((phase === 'turn' || phase === 'river') && cards && cards.length >= 1) {
        var variant = 1 + Math.floor(Math.random() * 9);
        var dealClass = phase === 'turn' ? ('deal-turn deal-turn-' + variant) : ('deal-river deal-river-' + variant);
        var c = cardToDisplay(cards[0]);
        var suitClass = isRed(c.suit) ? 'red' : 'black';
        var cardDiv = document.createElement('div');
        cardDiv.className = 'card ' + suitClass + ' ' + dealClass;
        cardDiv.innerText = c.suit + c.rank;
        container.appendChild(cardDiv);
        requestAnimationFrame(function () {
            requestAnimationFrame(function () {
                void cardDiv.offsetHeight;
                setTimeout(function () { cardDiv.classList.add('visible'); }, 120);
            });
        });
    }
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
            var variantNum = 1 + Math.floor(Math.random() * 9);
            var variant = '';
            if (dealClass === 'deal-flop') variant = ' deal-flop-' + variantNum;
            else if (dealClass === 'deal-turn') variant = ' deal-turn-' + variantNum;
            else if (dealClass === 'deal-river') variant = ' deal-river-' + variantNum;
            cardDiv.className = 'card ' + suitClass + ' ' + dealClass + variant;
            cardDiv.innerText = suit + rank;
            container.appendChild(cardDiv);
            requestAnimationFrame(function () {
                requestAnimationFrame(function () {
                    void cardDiv.offsetHeight;
                    setTimeout(function () { cardDiv.classList.add('visible'); }, 220);
                });
            });
        }, index * delayMs);
    });
}

function showWinnerAnimation(winnerInfo, winnerIdx, players, winnerAmount, winnerHandType) {
    playGameSound('win');
    const overlay = document.getElementById('winner-overlay');
    const textEl = document.getElementById('winner-text');
    const amountEl = document.getElementById('winner-amount');
    const handTypeEl = document.getElementById('winner-hand-type');
    const contentEl = overlay ? overlay.querySelector('.winner-content') : null;
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
    if (handTypeEl) {
        var handType = winnerHandType;
        if (!handType && winnerInfo && typeof winnerInfo === 'string') {
            var m = winnerInfo.match(/以\s*([^获]+)\s*获胜/);
            if (m) handType = m[1].trim();
            else { m = winnerInfo.match(/牌型[：:]\s*([^，。]+)/); if (m) handType = m[1].trim(); }
        }
        if (handType) {
            handTypeEl.textContent = '以 ' + handType + ' 获胜';
            handTypeEl.style.display = 'block';
        } else {
            handTypeEl.textContent = '';
            handTypeEl.style.display = 'none';
        }
    }
    if (contentEl) contentEl.classList.remove('winner-content--animate');
    overlay.classList.remove('hidden');
    overlay.setAttribute('aria-hidden', 'false');
    runConfetti();
    setTimeout(function () {
        overlay.classList.add('visible');
        if (contentEl) contentEl.classList.add('winner-content--animate');
    }, 50);
    /* 展示 6 秒，方便看清谁获胜 */
    setTimeout(function () {
        overlay.classList.remove('visible');
        setTimeout(function () {
            overlay.classList.add('hidden');
            overlay.setAttribute('aria-hidden', 'true');
            if (contentEl) contentEl.classList.remove('winner-content--animate');
            stopConfetti();
        }, 600);
    }, 6000);
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
