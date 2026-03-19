/**
 * 俱乐部列表页：拉取列表、创建俱乐部
 */
(function() {
    function apiUrl(path) {
        return (window.DZPOKER && window.DZPOKER.apiUrl) ? window.DZPOKER.apiUrl(path) : path;
    }
    var token = (window.authGetToken && window.authGetToken()) || localStorage.getItem('token') || '';

    var listEl = document.getElementById('clubs-list');
    var loadingEl = document.getElementById('clubs-loading');
    var emptyEl = document.getElementById('clubs-empty');
    var createBtn = document.getElementById('create-club-btn');
    var createForm = document.getElementById('create-club-form');
    var createFrm = document.getElementById('create-club-frm');
    var cancelBtn = document.getElementById('cancel-create-btn');
    var msgEl = document.getElementById('create-club-msg');

    function renderClubs(clubs) {
        loadingEl.style.display = 'none';
        if (!clubs || clubs.length === 0) {
            emptyEl.style.display = 'block';
            listEl.innerHTML = '';
            return;
        }
        emptyEl.style.display = 'none';
        listEl.innerHTML = '';
        clubs.forEach(function(c) {
            var card = document.createElement('a');
            card.href = '/club/' + c.id;
            card.className = 'club-card';
            card.innerHTML =
                '<span class="club-card-name">' + (c.name || '未命名') + '</span>' +
                '<span class="club-card-desc">' + (c.description || '暂无简介') + '</span>' +
                '<span class="club-card-meta">ID: ' + c.id + '</span>';
            listEl.appendChild(card);
        });
    }

    function loadClubs() {
        loadingEl.style.display = 'block';
        emptyEl.style.display = 'none';
        listEl.innerHTML = '';
        fetch(apiUrl('/api/clubs'), { headers: token ? { 'Authorization': 'Bearer ' + token } : {} })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                var arr = data.clubs || [];
                renderClubs(arr);
            })
            .catch(function() {
                loadingEl.style.display = 'none';
                emptyEl.style.display = 'block';
                listEl.innerHTML = '<p class="form-msg error">加载失败</p>';
            });
    }

    if (createBtn && createForm) {
        createBtn.addEventListener('click', function() {
            if (!token) {
                if (msgEl) { msgEl.textContent = '请先登录'; msgEl.className = 'form-msg error'; }
                return;
            }
            createForm.style.display = 'block';
            if (msgEl) msgEl.textContent = '';
        });
    }
    if (cancelBtn && createForm) {
        cancelBtn.addEventListener('click', function() {
            createForm.style.display = 'none';
        });
    }
    if (createFrm) {
        createFrm.addEventListener('submit', function(e) {
            e.preventDefault();
            var name = document.getElementById('club-name').value.trim();
            var desc = document.getElementById('club-desc').value.trim();
            if (!name) {
                if (msgEl) { msgEl.textContent = '请填写名称'; msgEl.className = 'form-msg error'; }
                return;
            }
            if (!token) {
                if (msgEl) { msgEl.textContent = '请先登录'; msgEl.className = 'form-msg error'; }
                return;
            }
            if (msgEl) msgEl.textContent = '';
            fetch(apiUrl('/api/clubs'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
                body: JSON.stringify({ name: name, description: desc || undefined })
            })
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (data.error) {
                        if (msgEl) { msgEl.textContent = data.error; msgEl.className = 'form-msg error'; }
                        return;
                    }
                    if (msgEl) { msgEl.textContent = '创建成功'; msgEl.className = 'form-msg success'; }
                    createForm.style.display = 'none';
                    createFrm.reset();
                    loadClubs();
                })
                .catch(function() {
                    if (msgEl) { msgEl.textContent = '请求失败'; msgEl.className = 'form-msg error'; }
                });
        });
    }

    loadClubs();
})();
