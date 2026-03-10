/**
 * dzpokerV3/static/config.js
 * 客户端配置：服务端地址（前后端分离时指向 API/WS 服务器）
 * - 同源部署时无需设置，留空即可
 * - 分离部署时在页面加载前设置 window.DZPOKER_API_BASE 与 window.DZPOKER_WS_URL
 */
(function () {
    var base = (typeof window !== "undefined" && window.DZPOKER_API_BASE) || "";
    var ws = (typeof window !== "undefined" && window.DZPOKER_WS_URL) !== undefined
        ? window.DZPOKER_WS_URL
        : base;

    function apiBase() {
        return base || "";
    }
    function wsUrl() {
        return ws || "";
    }
    /** 拼完整 API 路径（path 以 / 开头，如 /api/...） */
    function apiUrl(path) {
        var p = (path || "").replace(/^\//, "");
        var b = apiBase().replace(/\/$/, "");
        return b ? b + "/" + p : "/" + p;
    }

    window.DZPOKER = {
        apiBase: apiBase,
        wsUrl: wsUrl,
        apiUrl: apiUrl
    };
})();
