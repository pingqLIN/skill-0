/* Video-Full popup script */
(function () {
  const statusEl = document.getElementById('status');

  function showStatus(msg) {
    statusEl.textContent = msg;
  }

  async function sendMessage(payload) {
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tab || !tab.id) {
        showStatus('No active tab found.');
        return;
      }
      // Ensure content script is injected (handles cases where extension was
      // just installed and the page hasn't reloaded yet).
      // Errors on restricted pages (e.g. chrome://) are surfaced to the user.
      await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        files: ['content.js'],
      }).catch((err) => {
        // Ignore "already injected" errors; surface genuine failures.
        if (!err.message.includes('already been injected')) {
          throw err;
        }
      });

      const response = await chrome.tabs.sendMessage(tab.id, payload);
      if (response && response.count !== undefined) {
        showStatus(`Applied to ${response.count} player(s).`);
      } else if (response && response.status) {
        showStatus(response.status);
      }
    } catch (err) {
      showStatus('Error: ' + (err.message || err));
    }
  }

  document.querySelectorAll('.split-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      const cols = parseInt(btn.dataset.cols, 10);
      showStatus('Applying...');
      sendMessage({ action: 'split', cols });
    });
  });

  document.getElementById('reset-btn').addEventListener('click', () => {
    showStatus('Resetting...');
    sendMessage({ action: 'reset' });
  });
})();
