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
      let response;
      try {
        // First, try to send a message to an already-injected content script.
        response = await chrome.tabs.sendMessage(tab.id, payload);
      } catch (err) {
        const msg = err && err.message ? err.message : String(err);
        // If there is no receiving end, the content script is likely not injected yet.
        if (msg.includes('Could not establish connection') || msg.includes('Receiving end does not exist')) {
          // Inject the content script once, then retry the message.
          await chrome.scripting.executeScript({
            target: { tabId: tab.id },
            files: ['content.js'],
          });
          response = await chrome.tabs.sendMessage(tab.id, payload);
        } else {
          // Re-throw any other kind of messaging error.
          throw err;
        }
      }
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
