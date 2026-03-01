/* Video-Full content script */
(function () {
  'use strict';

  // ------------------------------------------------------------------
  // State
  // ------------------------------------------------------------------
  const OVERLAY_ID = 'vf-overlay';

  // Tracks original DOM state for each moved player so we can restore them.
  // Each entry: { el, parent, nextSibling, origStyle }
  const movedPlayers = [];

  // ------------------------------------------------------------------
  // Helpers
  // ------------------------------------------------------------------

  /**
   * Returns true if the iframe src belongs to a supported video host.
   * Uses URL parsing to validate the exact hostname, preventing substring
   * spoofing (e.g. evil.com/player.vimeo.com).
   */
  function isVideoIframe(iframe) {
    const rawSrc = iframe.src || iframe.getAttribute('data-src') || '';
    if (!rawSrc) return false;
    let parsed;
    try {
      parsed = new URL(rawSrc, location.href);
    } catch (_) {
      return false;
    }
    const host = parsed.hostname.toLowerCase();
    // YouTube embed
    if (host === 'www.youtube.com' || host === 'youtube.com' || host === 'youtu.be') {
      return true;
    }
    // Vimeo player
    if (host === 'player.vimeo.com') {
      return true;
    }
    // Bilibili player
    if (host === 'player.bilibili.com') {
      return true;
    }
    return false;
  }

  /**
   * Collect all video players visible in the document:
   * native <video> elements + supported video iframes.
   * Excludes tiny/hidden elements and elements already inside the overlay.
   */
  function collectPlayers() {
    const overlay = document.getElementById(OVERLAY_ID);
    const players = [];

    document.querySelectorAll('video').forEach((v) => {
      if (overlay && overlay.contains(v)) return;
      const rect = v.getBoundingClientRect();
      if (rect.width < 10 || rect.height < 10) return;
      players.push(v);
    });

    document.querySelectorAll('iframe').forEach((f) => {
      if (!isVideoIframe(f)) return;
      if (overlay && overlay.contains(f)) return;
      const rect = f.getBoundingClientRect();
      if (rect.width < 10 || rect.height < 10) return;
      players.push(f);
    });

    return players;
  }

  // ------------------------------------------------------------------
  // Split
  // ------------------------------------------------------------------

  function applySplit(cols) {
    // Validate cols is a positive integer
    if (!Number.isInteger(cols) || cols < 1) {
      return { count: 0 };
    }

    // Remove any existing overlay first, restoring moved players before
    // we re-collect.
    destroyOverlay();

    const players = collectPlayers();
    if (players.length === 0) {
      return { count: 0 };
    }

    // Number of tiles = min(requested split size, players.length), but at least 1.
    const tileCount = Math.min(cols, players.length);

    // Derive effective grid columns from the requested split and the actual
    // tile count. This ensures:
    // - 2 Split → up to 1x2
    // - 4 Split → up to 2x2
    // - 6 Split → up to 3x2
    // - 9 Split → up to 3x3
    // - For other values, fall back to cols as the max column count.
    let gridCols;
    if (cols === 4) {
      gridCols = Math.min(2, tileCount);
    } else if (cols === 6) {
      gridCols = Math.min(3, tileCount);
    } else if (cols === 9) {
      gridCols = Math.min(3, tileCount);
    } else {
      gridCols = Math.min(cols, tileCount);
    }

    const gridRows = Math.ceil(tileCount / gridCols);

    // Build overlay
    const overlay = document.createElement('div');
    overlay.id = OVERLAY_ID;
    overlay.style.gridTemplateColumns = `repeat(${gridCols}, 1fr)`;
    overlay.style.gridTemplateRows = `repeat(${gridRows}, 1fr)`;

    for (let i = 0; i < tileCount; i++) {
      const player = players[i];
      const tile = document.createElement('div');
      tile.className = 'vf-tile';

      // Save original placement & style before moving.
      // Use hasAttribute to correctly distinguish "no style attr" from style="".
      movedPlayers.push({
        el: player,
        parent: player.parentNode,
        nextSibling: player.nextSibling,
        hadStyle: player.hasAttribute('style'),
        origStyle: player.getAttribute('style'),
      });

      // Move player into tile
      tile.appendChild(player);

      // Override inline dimensions so CSS can take over
      player.style.width = '100%';
      player.style.height = '100%';

      // Attempt muted autoplay for native videos
      if (player.tagName === 'VIDEO') {
        player.muted = true;
        player.play().catch((e) => { console.debug('[Video-Full] autoplay blocked:', e.message); });
      }

      overlay.appendChild(tile);
    }

    document.body.appendChild(overlay);
    return { count: tileCount };
  }

  // ------------------------------------------------------------------
  // Reset / restore
  // ------------------------------------------------------------------

  function destroyOverlay() {
    // Restore all moved players to their original DOM positions
    while (movedPlayers.length > 0) {
      const { el, parent, nextSibling, hadStyle, origStyle } = movedPlayers.pop();
      if (!parent) continue;

      // Restore original inline style exactly:
      // - had no style attr → remove it entirely
      // - had style="" or non-empty → restore that value
      if (!hadStyle) {
        el.removeAttribute('style');
      } else {
        el.setAttribute('style', origStyle);
      }

      // Re-insert at original position.
      // isConnected check ensures nextSibling is still in the DOM.
      if (nextSibling && nextSibling.isConnected && nextSibling.parentNode === parent) {
        parent.insertBefore(el, nextSibling);
      } else {
        parent.appendChild(el);
      }
    }

    // Remove overlay element
    const overlay = document.getElementById(OVERLAY_ID);
    if (overlay) overlay.remove();
  }

  function applyReset() {
    destroyOverlay();
    return { status: 'reset' };
  }

  // ------------------------------------------------------------------
  // Message listener
  // ------------------------------------------------------------------

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message.action === 'split') {
      const result = applySplit(message.cols);
      sendResponse(result);
    } else if (message.action === 'reset') {
      const result = applyReset();
      sendResponse(result);
    } else {
      // Respond with an error for unsupported actions to avoid hanging the port
      sendResponse({
        status: 'error',
        message: 'Unknown action',
        action: message && message.action,
      });
    }
    // Return false because all responses are sent synchronously
    return false;
  });
})();
