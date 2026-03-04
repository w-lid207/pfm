/**
 * app.js — Initialisation globale
 * Auth guard, dark mode, WebSocket, mise à jour navbar
 */

// ── Guard d'authentification ──
(function authGuard() {
  // La page login n'a pas de navbar, on ne vérifie pas
  if (window.location.pathname === '/') return;

  const token = localStorage.getItem('access_token');
  if (!token) {
    window.location.href = '/';
    return;
  }

  // Mettre à jour navbar avec infos utilisateur
  const user = JSON.parse(localStorage.getItem('user') || '{}');
  if (user.username) {
    const elUser = document.getElementById('usernameBadge');
    const elRole = document.getElementById('userRoleBadge');
    if (elUser) elUser.textContent = user.username;
    if (elRole) {
      elRole.textContent = user.role === 'admin' ? '👑 Admin' : '🔧 Opérateur';
    }

    // Afficher logs admin
    if (user.role === 'admin') {
      const navLogs = document.getElementById('navLogs');
      if (navLogs) navLogs.style.display = '';
    }
  }
})();

// ── Déconnexion ──
function logout() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('user');
  window.location.href = '/';
}

// ── Dark Mode ──
(function initDarkMode() {
  const saved = localStorage.getItem('darkMode');
  if (saved === 'true') {
    document.documentElement.setAttribute('data-theme', 'dark');
  }
})();

document.addEventListener('DOMContentLoaded', () => {
  const btn = document.getElementById('darkModeBtn');
  if (!btn) return;

  const isDark = () => document.documentElement.getAttribute('data-theme') === 'dark';

  // Sync icon
  function updateIcon() {
    const icon = btn.querySelector('i');
    if (icon) {
      icon.className = isDark() ? 'bi bi-sun-fill' : 'bi bi-moon-stars';
    }
  }
  updateIcon();

  btn.addEventListener('click', () => {
    const newTheme = isDark() ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('darkMode', newTheme === 'dark');
    updateIcon();
  });

  // ── Badge alertes non lues ──
  async function refreshAlertBadge() {
    try {
      const data = await API_CALL('GET', '/api/alertes?non_lues=true');
      const badge = document.getElementById('alertBadge');
      if (badge) {
        const count = data.non_lues || 0;
        badge.textContent = count;
        badge.classList.toggle('d-none', count === 0);
      }
    } catch (e) {}
  }
  refreshAlertBadge();
  setInterval(refreshAlertBadge, 60000);
});

// ── WebSocket ──
let socket = null;
(function initSocketIO() {
  if (window.location.pathname === '/') return;
  if (typeof io === 'undefined') return;

  try {
    socket = io({ transports: ['websocket', 'polling'] });

    socket.on('connect', () => {
      const badge = document.getElementById('wsStatus');
      if (badge) {
        badge.className = 'badge bg-success';
        badge.innerHTML = '<i class="bi bi-wifi me-1"></i>Live';
      }
    });

    socket.on('disconnect', () => {
      const badge = document.getElementById('wsStatus');
      if (badge) {
        badge.className = 'badge bg-secondary';
        badge.innerHTML = '<i class="bi bi-wifi-off me-1"></i>Offline';
      }
    });

    socket.on('alert_received', (data) => {
      TOAST(`🔔 ${data.titre || 'Nouvelle alerte'}`, 'warning', 6000);
    });
  } catch (e) {
    console.warn('WebSocket non disponible:', e);
  }
})();
