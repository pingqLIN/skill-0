/* Video-Full service worker (Manifest V3 background) */
// Minimal service worker – all logic lives in content.js.
chrome.runtime.onInstalled.addListener(() => {
  console.log('[Video-Full] Extension installed.');
});
