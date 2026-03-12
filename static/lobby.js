// dzpokerV3/static/lobby.js - 大厅：登录、创建牌桌、加入牌桌（客户端只请求服务端，不监管牌桌）

(function () {
    const TOKEN_KEY = "token";
    function apiUrl(path) {
        return (window.DZPOKER && window.DZPOKER.apiUrl) ? window.DZPOKER.apiUrl(path) : path;
    }
    function parseJsonRes(res, url) {
        var ct = (res.headers.get("Content-Type") || "").toLowerCase();
        return res.text().then(function (text) {
            if (ct.indexOf("application/json") !== -1) return text ? JSON.parse(text) : {};
            if (text && (text.trim().toLowerCase().indexOf("<!doctype") === 0 || text.trim().indexOf("<!DOCTYPE") === 0))
                throw new Error("服务端返回了网页而非数据，请确认 API 地址正确。当前请求: " + (url || res.url || ""));
            try { return text ? JSON.parse(text) : {}; } catch (e) {
                throw new Error("响应不是有效 JSON，请确认 API 地址正确。当前请求: " + (url || res.url || ""));
            }
        });
    }

    function getToken() {
        return (typeof window.authGetToken === "function" && window.authGetToken()) || localStorage.getItem(TOKEN_KEY) || "";
    }
    function setToken(token, username) {
        localStorage.setItem(TOKEN_KEY, token || "");
        if (username) localStorage.setItem("dzpoker_username", username);
    }
    function clearToken() {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem("dzpoker_username");
    }
    /** 无登录时自动以游客身份获取 token（登录已注释，默认走此逻辑） */
    function ensureToken() {
        var t = getToken();
        if (t) return Promise.resolve(t);
        return fetch(apiUrl("/api/login"), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username: "游客_" + Date.now() })
        })
            .then(function (res) { return parseJsonRes(res, apiUrl("/api/login")); })
            .then(function (data) {
                if (data.token) {
                    setToken(data.token, data.username);
                    return data.token;
                }
                throw new Error("获取游客身份失败");
            });
    }

    const tableListEl = document.getElementById("table-list");
    const quickStartBtn = document.getElementById("quick-start-btn");
    const createTableBtn = document.getElementById("create-table-btn");
    const quickStartMsg = document.getElementById("quick-start-msg");
    const filterBlinds = document.getElementById("filter-blinds");
    const filterPlayers = document.getElementById("filter-players");
    const filterApply = document.getElementById("filter-apply");
    const loginPanel = document.getElementById("login-panel");
    const loggedPanel = document.getElementById("logged-panel");
    const loginUsername = document.getElementById("login-username");
    const loginBtn = document.getElementById("login-btn");
    const loginMsg = document.getElementById("login-msg");
    const loggedUsername = document.getElementById("logged-username");
    const logoutBtn = document.getElementById("logout-btn");

    function updateLoginUI() {
        var token = getToken();
        if (token) {
            if (loggedUsername) loggedUsername.textContent = localStorage.getItem("dzpoker_username") || "玩家";
            if (loginPanel) loginPanel.style.display = "none";
            if (loggedPanel) loggedPanel.style.display = "block";
        } else {
            if (loginPanel) loginPanel.style.display = "block";
            if (loggedPanel) loggedPanel.style.display = "none";
        }
    }

    if (loginBtn) {
        loginBtn.addEventListener("click", function () {
            var name = (loginUsername && loginUsername.value) || "玩家";
            fetch(apiUrl("/api/login"), {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username: name })
            })
                .then(function (res) { return parseJsonRes(res, apiUrl("/api/login")); })
                .then(function (data) {
                    setToken(data.token, data.username);
                    updateLoginUI();
                    if (loginMsg) loginMsg.textContent = "登录成功";
                    loadTables();
                })
                .catch(function () {
                    if (loginMsg) loginMsg.textContent = "登录失败";
                });
        });
    }
    if (logoutBtn) {
        logoutBtn.addEventListener("click", function () {
            clearToken();
            updateLoginUI();
            if (loginMsg) loginMsg.textContent = "";
        });
    }

    updateLoginUI();

    /** 大厅顶部显示筹码余额（与导航栏一致，来自 /api/auth/me） */
    function updateBalanceDisplay() {
        var token = getToken();
        if (!token || !document.getElementById("balance-display")) return;
        fetch(apiUrl("/api/auth/me"), { headers: { "Authorization": "Bearer " + token } })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                if (data.ok && data.userProfile && data.userProfile.coinsBalance != null) {
                    document.getElementById("balance-display").textContent = Number(data.userProfile.coinsBalance).toLocaleString();
                } else {
                    document.getElementById("balance-display").textContent = "—";
                }
            })
            .catch(function () {
                if (document.getElementById("balance-display")) document.getElementById("balance-display").textContent = "—";
            });
    }
    updateBalanceDisplay();

    function escapeHtml(s) {
        var div = document.createElement("div");
        div.textContent = s;
        return div.innerHTML;
    }

    /** 无牌桌时显示的占位卡片（扑克大厅用语） */
    function seatDotsHtml(seated, maxP) {
        var html = '<span class="seat-dots">';
        for (var i = 0; i < maxP; i++) {
            html += '<span class="' + (i < seated ? 'filled' : 'empty') + '">●</span>';
        }
        html += '</span>';
        return html;
    }
    var STATIC_CARDS_HTML =
        '<div class="table-card">' +
        '<div class="card-header"><span class="card-blinds-label">盲注</span><span class="card-blinds-value">5/10</span><span class="card-buyin">买入 100–1000</span></div>' +
        '<div class="card-body"><div class="card-row"><span>人数</span><span class="value">' + seatDotsHtml(2, 6) + ' 2/6</span></div><div class="card-row"><span>状态</span><span class="value check">等待中</span></div></div>' +
        '<div class="card-actions"><span class="table-status playing">对局中</span></div></div>' +
        '<div class="table-card active">' +
        '<div class="card-header"><span class="card-blinds-label">盲注</span><span class="card-blinds-value">10/20</span><span class="card-buyin">买入 200–2000</span></div>' +
        '<div class="card-body"><div class="card-row"><span>人数</span><span class="value">' + seatDotsHtml(4, 6) + ' 4/6</span></div><div class="card-row"><span>状态</span><span class="value check">等待中</span></div></div>' +
        '<div class="card-actions"><button type="button" class="join-btn">入座</button></div></div>' +
        '<div class="table-card">' +
        '<div class="card-header"><span class="card-blinds-label">盲注</span><span class="card-blinds-value">25/50</span><span class="card-buyin">买入 500–5000</span></div>' +
        '<div class="card-body"><div class="card-row"><span>人数</span><span class="value">' + seatDotsHtml(6, 6) + ' 6/6</span></div><div class="card-row"><span>状态</span><span class="value">对局中</span></div></div>' +
        '<div class="card-actions"><span class="table-status playing">对局中</span></div></div>';

    function renderTables(tablesData) {
        if (!tableListEl) return;
        if (!tablesData || tablesData.length === 0) {
            tableListEl.innerHTML = STATIC_CARDS_HTML;
            return;
        }
        tableListEl.innerHTML = tablesData.map(function (t, idx) {
            var sb = (t.blinds && t.blinds.sb != null) ? t.blinds.sb : 0;
            var bb = (t.blinds && t.blinds.bb != null) ? t.blinds.bb : 0;
            var blindsText = (sb >= 1e6 ? (sb / 1e6) + "M" : sb) + "/" + (bb >= 1e6 ? (bb / 1e6) + "M" : bb);
            var minBuy = (t.minBuyIn != null) ? (t.minBuyIn >= 1e6 ? (t.minBuyIn / 1e6) + "M" : t.minBuyIn) : "?";
            var maxBuy = (t.maxBuyIn != null) ? (t.maxBuyIn >= 1e6 ? (t.maxBuyIn / 1e6) + "M" : t.maxBuyIn) : "?";
            var buyInText = "买入 " + minBuy + "–" + maxBuy;
            var isActive = idx === 0;
            var statusClass = t.status === "waiting" ? "waiting" : "playing";
            var statusText = t.status === "waiting" ? "等待中" : "对局中";
            var seated = t.seatedPlayers != null ? t.seatedPlayers : (t.playerCount != null ? t.playerCount : 0);
            var maxP = t.maxPlayers != null ? t.maxPlayers : 6;
            var canJoin = t.status === "waiting" && seated < maxP;
            var joinBtn = canJoin
                ? "<button type='button' class='btn btn-amber join-btn' data-table-id='" + t.tableId + "'>入座</button>"
                : "<span class='table-status " + statusClass + "'>" + statusText + "</span>";
            var dotsHtml = seatDotsHtml(seated, maxP);
            return (
                "<div class='table-card" + (isActive ? " active" : "") + "' data-table-id='" + t.tableId + "'>" +
                "<div class='card-header'>" +
                "<span class='card-blinds-label'>盲注</span>" +
                "<span class='card-blinds-value'>" + escapeHtml(blindsText) + "</span>" +
                "<span class='card-buyin'>" + escapeHtml(buyInText) + "</span>" +
                "</div>" +
                "<div class='card-body'>" +
                "<div class='card-row'><span>人数</span><span class='value'>" + dotsHtml + " " + seated + "/" + maxP + "</span></div>" +
                "<div class='card-row'><span>状态</span><span class='value" + (t.status === "waiting" ? " check" : "") + "'>" + statusText + "</span></div>" +
                "</div>" +
                "<div class='card-actions'>" + joinBtn + "</div>" +
                "</div>"
            );
        }).join("");

        tableListEl.querySelectorAll(".join-btn").forEach(function (btn) {
            btn.addEventListener("click", function () {
                var tableId = this.getAttribute("data-table-id");
                if (!tableId) return;
                ensureToken().then(function (token) {
                    if (quickStartMsg) quickStartMsg.textContent = "正在加入…";
                    var tableUrl = apiUrl("/api/tables/" + tableId);
                    var tableUrlWithToken = tableUrl + (tableUrl.indexOf("?") >= 0 ? "&" : "?") + "token=" + encodeURIComponent(token);
                    fetch(tableUrlWithToken)
                        .then(function (res) { return parseJsonRes(res, tableUrlWithToken); })
                        .then(function (state) {
                            if (state && state.error) {
                                if (quickStartMsg) quickStartMsg.textContent = state.error;
                                return;
                            }
                            if (!state || !Array.isArray(state.seats)) {
                                if (quickStartMsg) quickStartMsg.textContent = "无法获取座位信息";
                                return;
                            }
                            var seat = -1;
                            for (var i = 0; i < state.seats.length; i++) {
                                var s = state.seats[i];
                                if (s == null || s === undefined || (typeof s === "object" && s.userId == null)) {
                                    seat = i;
                                    break;
                                }
                            }
                            if (seat < 0) {
                                if (quickStartMsg) quickStartMsg.textContent = "该桌已满";
                                return;
                            }
                            return fetch(apiUrl("/api/tables/" + tableId + "/sit"), {
                                method: "POST",
                                headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({ token: token, seat: seat })
                            }).then(function (r) {
                                if (!r.ok) {
                                    return parseJsonRes(r, apiUrl("/api/tables/" + tableId + "/sit")).then(function (d) {
                                        throw new Error(d.error || d.message || "加入失败");
                                    });
                                }
                                return r.json();
                            }).then(function () {
                                window.location.href = "/?table=" + tableId + "&token=" + encodeURIComponent(token);
                            });
                        })
                        .catch(function (err) {
                            if (quickStartMsg) quickStartMsg.textContent = (err && err.message) ? err.message : "加入失败";
                        });
                });
            });
        });
    }

    function loadTables() {
        if (!tableListEl) return;
        var blinds = filterBlinds ? filterBlinds.value : "";
        var players = filterPlayers ? filterPlayers.value : "";
        var url = apiUrl("/api/lobby/tables");
        if (blinds) url += "?blinds=" + encodeURIComponent(blinds);
        if (players) url += (url.indexOf("?") >= 0 ? "&" : "?") + "players=" + encodeURIComponent(players);
        tableListEl.innerHTML = "<p class='lobby-loading'>加载中…</p>";
        fetch(url)
            .then(function (res) { return parseJsonRes(res, url); })
            .then(function (data) {
                renderTables(data.tables || []);
            })
            .catch(function () {
                tableListEl.innerHTML = STATIC_CARDS_HTML;
            });
    }

    if (quickStartBtn) {
        quickStartBtn.addEventListener("click", function () {
            ensureToken().then(function (token) {
                quickStartMsg.textContent = "匹配中…";
                fetch(apiUrl("/api/lobby/quick-start"), {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ token: token })
            })
                .then(function (res) { return parseJsonRes(res, apiUrl("/api/lobby/quick-start")); })
                .then(function (data) {
                    if (data.tableId != null) {
                        quickStartMsg.textContent = "正在进入牌桌…";
                        window.location.href = "/?table=" + data.tableId + "&token=" + encodeURIComponent(token);
                    } else {
                        quickStartMsg.textContent = data.message || "暂无空位";
                    }
                })
                .catch(function () {
                    quickStartMsg.textContent = "请求失败";
                });
            });
        });
    }

    if (createTableBtn) {
        var createPanel = document.getElementById("create-table-panel");
        var createForm = document.getElementById("create-table-form");
        var createMsg = document.getElementById("create-table-msg");
        var createCancel = document.getElementById("create-table-cancel");

        createTableBtn.addEventListener("click", function () {
            ensureToken().then(function () {
                if (createPanel) createPanel.style.display = "block";
                if (createMsg) createMsg.textContent = "";
            });
        });

        if (createCancel) {
            createCancel.addEventListener("click", function () {
                if (createPanel) createPanel.style.display = "none";
            });
        }

        document.querySelectorAll("#blind-presets .preset-btn").forEach(function (btn) {
            var sb = parseInt(btn.getAttribute("data-sb"), 10);
            var bb = parseInt(btn.getAttribute("data-bb"), 10);
            if (!sb || !bb) return;
            btn.addEventListener("click", function () {
                var sbEl = document.getElementById("ct-sb");
                var bbEl = document.getElementById("ct-bb");
                if (sbEl) sbEl.value = sb;
                if (bbEl) bbEl.value = bb;
                var minEl = document.getElementById("ct-min-buy");
                var maxEl = document.getElementById("ct-max-buy");
                if (minEl) minEl.value = Math.max(100, bb * 10);
                if (maxEl) maxEl.value = Math.max(10000, bb * 200);
            });
        });

        if (createForm) {
            createForm.addEventListener("submit", function (e) {
                e.preventDefault();
                ensureToken().then(function (token) {
                    var nameEl = document.getElementById("ct-name");
                    var sbEl = document.getElementById("ct-sb");
                    var bbEl = document.getElementById("ct-bb");
                    var playersEl = document.getElementById("ct-players");
                    var sb = parseInt(sbEl && sbEl.value, 10) || 5;
                    var bb = parseInt(bbEl && bbEl.value, 10) || 10;
                    var payload = {
                        tableName: (nameEl && nameEl.value ? nameEl.value.trim() : "") || undefined,
                        sb: sb,
                        bb: bb,
                        maxPlayers: parseInt(playersEl && playersEl.value, 10) || 6
                    };

                    if (createMsg) createMsg.textContent = "创建中…";
                    var createUrl = apiUrl("/api/lobby/tables");
                    fetch(createUrl, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(payload)
                    })
                        .then(function (res) { return parseJsonRes(res, createUrl); })
                        .then(function (data) {
                            if (data.tableId == null) {
                                if (createMsg) createMsg.textContent = (data.error || "创建失败");
                                return;
                            }
                            if (createPanel) createPanel.style.display = "none";
                            if (quickStartMsg) quickStartMsg.textContent = "已创建牌桌，正在进入…";
                            window.location.href = "/?table=" + data.tableId + "&token=" + encodeURIComponent(token);
                        })
                        .catch(function (err) {
                            if (createMsg) createMsg.textContent = (err && err.message) || "创建失败";
                        });
                });
            });
        }
    }

    if (filterApply) filterApply.addEventListener("click", loadTables);

    var loadTablesTimer = null;
    function loadTablesDebounced() {
        if (loadTablesTimer) clearTimeout(loadTablesTimer);
        loadTablesTimer = setTimeout(loadTables, 300);
    }

    ensureToken().then(function () { loadTablesDebounced(); updateBalanceDisplay(); }).catch(function () {
        if (tableListEl) tableListEl.innerHTML = "<p style='color: var(--text-muted);'>无法连接，请刷新重试。</p>";
    });
})();
