/**
 * api.js — Couche API centralisée
 * Gestion des tokens JWT, requêtes fetch, rafraîchissement automatique
 */

/**
 * Effectue une requête API authentifiée
 * @param {string} method - GET, POST, PUT, DELETE
 * @param {string} endpoint - /api/...
 * @param {Object} body - corps de la requête (optionnel)
 * @returns {Promise<Object>} - données JSON
 */
async function API_CALL(method, endpoint, body = null) {
  const token = localStorage.getItem('access_token');

  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const options = { method, headers };
  if (body && method !== 'GET') {
    options.body = JSON.stringify(body);
  }

  const res = await fetch(endpoint, options);

  // Token expiré → redirection login
  if (res.status === 401) {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    window.location.href = '/';
    throw new Error('Session expirée');
  }

  const data = await res.json();

  if (!res.ok) {
    throw new Error(data.error || data.message || `Erreur ${res.status}`);
  }

  return data;
}

/**
 * Affiche un toast Bootstrap
 */
function TOAST(message, type = 'info', duration = 4000) {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const icons = {
    success: 'bi-check-circle-fill',
    danger: 'bi-exclamation-circle-fill',
    warning: 'bi-exclamation-triangle-fill',
    info: 'bi-info-circle-fill',
    secondary: 'bi-bell-fill',
  };

  const id = 'toast-' + Date.now();
  const html = `
    <div id="${id}" class="toast align-items-center text-bg-${type} border-0 shadow" role="alert" aria-live="assertive">
      <div class="d-flex">
        <div class="toast-body d-flex align-items-center gap-2">
          <i class="bi ${icons[type] || icons.info}"></i>
          ${message}
        </div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
      </div>
    </div>
  `;

  container.insertAdjacentHTML('beforeend', html);
  const toastEl = document.getElementById(id);
  const toast = new bootstrap.Toast(toastEl, { delay: duration });
  toast.show();
  toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
}
