// dzpokerV3/static/mall.js - 商城页：分类与商品列表

(function () {
    const productGrid = document.getElementById('product-grid');
    const categoryBtns = document.querySelectorAll('#mall-categories .cat-btn');

    var allProducts = [];
    var currentCat = 'all';

    var mockProducts = [
        { id: 't1', name: '经典绿绒', category: 'table_theme', price: 0, icon: '🃏', desc: '默认牌桌' },
        { id: 't2', name: '深蓝丝绒', category: 'table_theme', price: 500, icon: '🃏', desc: '深邃蓝调' },
        { id: 't3', name: '玫瑰金桌', category: 'table_theme', price: 1200, icon: '🃏', desc: '奢华质感' },
        { id: 'c1', name: '标准红背', category: 'card_back', price: 0, icon: '🂠', desc: '默认卡背' },
        { id: 'c2', name: '龙纹卡背', category: 'card_back', price: 300, icon: '🂠', desc: '中国风' },
        { id: 'c3', name: '星空卡背', category: 'card_back', price: 600, icon: '🂠', desc: '深邃星空' },
        { id: 'c4', name: '金箔卡背', category: 'card_back', price: 1000, icon: '🂠', desc: '尊贵金箔' },
        { id: 'e1', name: '基础表情', category: 'emote', price: 0, icon: '😊', desc: '默认表情' },
        { id: 'e2', name: '豪华表情包', category: 'emote', price: 200, icon: '🎭', desc: '更多表情' },
        { id: 'e3', name: '节日限定', category: 'emote', price: 500, icon: '🎄', desc: '节日专属' }
    ];

    function renderProducts() {
        var list = currentCat === 'all'
            ? allProducts
            : allProducts.filter(function (p) { return p.category === currentCat; });
        if (!productGrid) return;
        productGrid.innerHTML = list.map(function (p) {
            var priceText = p.price === 0 ? '免费' : p.price + ' 金币';
            return (
                '<div class="product-card" data-product-id="' + p.id + '">' +
                '<div class="product-img">' + p.icon + '</div>' +
                '<div class="product-info">' +
                '<div class="product-name">' + escapeHtml(p.name) + '</div>' +
                '<div class="product-price">' + priceText + '</div>' +
                '<button type="button" class="btn btn-amber product-buy" data-id="' + p.id + '">' +
                (p.price === 0 ? '使用' : '购买') +
                '</button>' +
                '</div></div>'
            );
        }).join('');

        productGrid.querySelectorAll('.product-buy').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var id = btn.getAttribute('data-id');
                var p = allProducts.find(function (x) { return x.id === id; });
                if (p) {
                    if (p.price === 0) {
                        alert('已切换为：' + p.name);
                    } else {
                        alert('购买「' + p.name + '」需要 ' + p.price + ' 金币。（当前为演示，未扣费）');
                    }
                }
            });
        });
    }

    function escapeHtml(s) {
        var div = document.createElement('div');
        div.textContent = s;
        return div.innerHTML;
    }

    function loadProducts() {
        var url = (window.DZPOKER && window.DZPOKER.apiUrl) ? window.DZPOKER.apiUrl('/api/mall/products') : '/api/mall/products';
        fetch(url)
            .then(function (res) { return res.json(); })
            .then(function (data) {
                allProducts = (data.products || data || []).length ? (data.products || data) : mockProducts;
                renderProducts();
            })
            .catch(function () {
                allProducts = mockProducts;
                renderProducts();
            });
    }

    categoryBtns.forEach(function (btn) {
        btn.addEventListener('click', function () {
            categoryBtns.forEach(function (b) { b.classList.remove('active'); });
            btn.classList.add('active');
            currentCat = btn.getAttribute('data-cat') || 'all';
            renderProducts();
        });
    });

    loadProducts();
})();
