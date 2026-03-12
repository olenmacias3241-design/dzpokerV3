/**
 * 钱包登录（spec 10）：ETH/BSC 用 MetaMask，SOL/Tron 占位提示
 * 后端未实现时显示「即将上线」
 */
(function() {
    var apiBase = (window.DZPOKER && window.DZPOKER.apiUrl) ? window.DZPOKER.apiUrl('') : '';
    var statusEl = document.getElementById('wallet-status');
    var msgEl = document.getElementById('wallet-msg');

    function setStatus(text, isError) {
        if (!statusEl) return;
        statusEl.textContent = text || '';
        statusEl.className = 'wallet-msg' + (isError ? ' error' : text ? ' success' : '');
    }

    function getEthereumAddress() {
        if (typeof window.ethereum === 'undefined') return Promise.reject(new Error('未检测到 MetaMask 或兼容钱包'));
        return window.ethereum.request({ method: 'eth_requestAccounts' }).then(function(accounts) {
            var addr = accounts && accounts[0];
            if (!addr) return Promise.reject(new Error('未获取到地址'));
            return addr;
        });
    }

    function signMessageEVM(message) {
        var selected = window.ethereum.selectedAddress;
        if (!selected) {
            return window.ethereum.request({ method: 'eth_requestAccounts' }).then(function(acc) {
                selected = acc && acc[0];
                return window.ethereum.request({ method: 'personal_sign', params: [message, selected] });
            });
        }
        return window.ethereum.request({ method: 'personal_sign', params: [message, selected] });
    }

    function tryWalletLogin(chain) {
        setStatus('正在连接…', false);
        var addressPromise;
        if (chain === 'ETH' || chain === 'BSC') {
            addressPromise = getEthereumAddress();
        } else if (chain === 'SOL') {
            setStatus('SOL 钱包登录即将上线，请先使用 Phantom 等钱包对接。', true);
            return;
        } else if (chain === 'Tron') {
            setStatus('Tron 钱包登录即将上线，请先使用 TronLink 等钱包对接。', true);
            return;
        } else {
            setStatus('不支持的链', true);
            return;
        }

        addressPromise.then(function(address) {
            setStatus('请求签名…', false);
            return fetch(apiBase + '/api/auth/wallet/challenge', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ chain: chain, address: address })
            }).then(function(r) {
                if (r.status === 404 || r.status === 501) {
                    setStatus('钱包登录接口即将上线，请暂时使用账号密码登录。', true);
                    return null;
                }
                return r.json();
            }).then(function(challengeData) {
                if (!challengeData || !challengeData.challenge) return null;
                return signMessageEVM(challengeData.challenge).then(function(signature) {
                    return { address: address, signature: signature, message: challengeData.challenge };
                });
            });
        }).then(function(payload) {
            if (!payload) return;
            return fetch(apiBase + '/api/auth/wallet/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    chain: chain,
                    address: payload.address,
                    signature: payload.signature,
                    message: payload.message
                })
            });
        }).then(function(r) {
            if (!r) return;
            if (r.status === 404 || r.status === 501) {
                setStatus('钱包登录即将上线。', true);
                return;
            }
            return r.json().then(function(data) {
                if (data.token) {
                    (window.authSetToken || function(t) { localStorage.setItem('token', t); })(data.token);
                    setStatus('登录成功，正在跳转…', false);
                    setTimeout(function() { window.location.href = '/lobby'; }, 600);
                } else {
                    setStatus(data.message || data.error || '登录失败', true);
                }
            });
        }).catch(function(e) {
            setStatus(e && e.message ? e.message : '连接失败', true);
        });
    }

    var btns = document.querySelectorAll('.wallet-chain button');
    for (var i = 0; i < btns.length; i++) {
        btns[i].addEventListener('click', function() {
            var chain = this.getAttribute('data-chain');
            tryWalletLogin(chain);
        });
    }
})();
