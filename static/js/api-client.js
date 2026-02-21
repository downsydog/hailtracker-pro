/**
 * HailTracker Pro - API Client
 * Lightweight fetch wrapper used by server-rendered templates.
 */
const api = {
    async get(url) {
        const resp = await fetch(url, {
            headers: { 'Accept': 'application/json' },
            credentials: 'same-origin'
        });
        if (!resp.ok) {
            const err = new Error(`API ${resp.status}`);
            err.status = resp.status;
            throw err;
        }
        return resp.json();
    },

    async post(url, data) {
        const resp = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            credentials: 'same-origin',
            body: JSON.stringify(data)
        });
        if (!resp.ok) {
            const err = new Error(`API ${resp.status}`);
            err.status = resp.status;
            try { err.data = await resp.json(); } catch (_) {}
            throw err;
        }
        return resp.json();
    },

    showToast(message, type) {
        const container = document.getElementById('toast-container');
        if (!container) return;
        const colors = {
            success: 'bg-green-500',
            error: 'bg-red-500',
            warning: 'bg-yellow-500',
            info: 'bg-blue-500'
        };
        const el = document.createElement('div');
        el.className = `${colors[type] || colors.info} text-white px-4 py-2 rounded-lg shadow-lg text-sm transition-opacity duration-300`;
        el.textContent = message;
        container.appendChild(el);
        setTimeout(() => { el.style.opacity = '0'; setTimeout(() => el.remove(), 300); }, 3000);
    }
};
