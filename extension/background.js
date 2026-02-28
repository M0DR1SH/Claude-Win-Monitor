const APP_URL = 'http://localhost:27182/session-key';
const RETRY_DELAY_MS = 5000;
const MAX_RETRIES = 10;

async function getSessionKey() {
  const cookie = await chrome.cookies.get({ url: 'https://claude.ai', name: 'sessionKey' });
  return cookie?.value ?? null;
}

async function sendSessionKey(retries = MAX_RETRIES) {
  const key = await getSessionKey();
  if (!key) return;

  for (let i = 0; i < retries; i++) {
    try {
      const res = await fetch(APP_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_key: key })
      });
      if (res.ok) return; // succès, on arrête
    } catch (e) {
      // App non active — on attend avant de réessayer
    }
    await new Promise(r => setTimeout(r, RETRY_DELAY_MS));
  }
}

// Au démarrage du navigateur ou à l'installation/réactivation
chrome.runtime.onInstalled.addListener(() => sendSessionKey());
chrome.runtime.onStartup.addListener(() => sendSessionKey());

// Dès que le cookie sessionKey change (refresh automatique par Claude)
chrome.cookies.onChanged.addListener((changeInfo) => {
  if (
    changeInfo.cookie.domain.includes('claude.ai') &&
    changeInfo.cookie.name === 'sessionKey' &&
    !changeInfo.removed
  ) {
    sendSessionKey(3); // moins de retries pour un changement de cookie
  }
});

// Quand un onglet claude.ai finit de charger
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' && tab.url?.includes('claude.ai')) {
    sendSessionKey(3);
  }
});

// Surveiller le démarrage de l'app : dès qu'elle répond au ping, envoyer la clé
async function watchForApp() {
  while (true) {
    try {
      const res = await fetch('http://localhost:27182/ping', { method: 'GET' });
      if (res.ok) {
        await sendSessionKey(1); // app dispo, un seul essai suffit
      }
    } catch (e) {
      // App pas encore lancée
    }
    await new Promise(r => setTimeout(r, 10000)); // vérifier toutes les 10s
  }
}

watchForApp();
