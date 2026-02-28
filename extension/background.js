// ================================================================
// CLAUDE-WIN-MONITOR — Claude Session Helper v1.0
// Extension navigateur (Chrome / Edge — Manifest V3)
// Transmission automatique de la sessionKey à l'application
//
// Auteur  : 🅻🅶 @ IA Mastery
// Date    : 28/02/2026
// ================================================================
//
// Principe de fonctionnement :
//   1. Lit le cookie "sessionKey" du domaine claude.ai
//   2. L'envoie à l'app via POST http://localhost:27182/session-key
//   3. Surveille les changements de cookie (renouvellement auto par Claude)
//   4. Détecte le démarrage de l'app via GET /ping (toutes les 10s)
//   5. Retry automatique si l'app n'est pas encore lancée (10 × 5s)
//
// Déclencheurs :
//   - Installation ou réactivation de l'extension
//   - Démarrage du navigateur
//   - Chargement d'un onglet claude.ai
//   - Renouvellement du cookie par Claude
//
// Usage :
//   L'extension peut être désactivée après le premier envoi réussi.
//   La réactiver uniquement en cas de changement de session Claude.
// ================================================================

const APP_URL        = 'http://localhost:27182/session-key';
const PING_URL       = 'http://localhost:27182/ping';
const RETRY_DELAY_MS = 5000;   // délai entre tentatives (ms)
const MAX_RETRIES    = 10;     // nb max de tentatives au démarrage
const POLL_DELAY_MS  = 10000;  // intervalle de surveillance de l'app (ms)

// ── Lecture du cookie sessionKey depuis le store Chrome ──────────
async function getSessionKey() {
  const cookie = await chrome.cookies.get({ url: 'https://claude.ai', name: 'sessionKey' });
  return cookie?.value ?? null;
}

// ── Envoi de la sessionKey vers l'app avec retry ─────────────────
async function sendSessionKey(retries = MAX_RETRIES) {
  const key = await getSessionKey();
  if (!key) return; // non connecté sur claude.ai

  for (let i = 0; i < retries; i++) {
    try {
      const res = await fetch(APP_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_key: key })
      });
      if (res.ok) return; // succès
    } catch (e) {
      // App non active — on attend avant de réessayer
    }
    await new Promise(r => setTimeout(r, RETRY_DELAY_MS));
  }
}

// ── Surveillance du démarrage de l'app (polling /ping) ───────────
async function watchForApp() {
  while (true) {
    try {
      const res = await fetch(PING_URL, { method: 'GET' });
      if (res.ok) {
        await sendSessionKey(1); // app dispo, un seul essai suffit
      }
    } catch (e) {
      // App pas encore lancée — on ignore
    }
    await new Promise(r => setTimeout(r, POLL_DELAY_MS));
  }
}

// ── Déclencheurs ─────────────────────────────────────────────────

// Installation ou réactivation de l'extension
chrome.runtime.onInstalled.addListener(() => sendSessionKey());

// Démarrage du navigateur
chrome.runtime.onStartup.addListener(() => sendSessionKey());

// Cookie sessionKey renouvelé automatiquement par Claude
chrome.cookies.onChanged.addListener((changeInfo) => {
  if (
    changeInfo.cookie.domain.includes('claude.ai') &&
    changeInfo.cookie.name === 'sessionKey' &&
    !changeInfo.removed
  ) {
    sendSessionKey(3);
  }
});

// Onglet claude.ai chargé (cookie existant, pas forcément changé)
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' && tab.url?.includes('claude.ai')) {
    sendSessionKey(3);
  }
});

// Démarrage de la surveillance de l'app
watchForApp();
