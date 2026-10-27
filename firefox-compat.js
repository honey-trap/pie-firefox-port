/* Compatibility layer for the local, unofficial Firefox port of Pie 1.33.9. */
(() => {
  "use strict";
  let offscreenReady;
  let offscreenFrame;

  async function createOffscreen({ url }) {
    if (offscreenReady) return offscreenReady;
    const expected = browser.runtime.getURL("offscreen.html");
    if (url !== expected && url !== "offscreen.html") {
      throw new Error("Only Pie's bundled offscreen document is supported");
    }
    offscreenReady = new Promise((resolve, reject) => {
      offscreenFrame = document.createElement("iframe");
      offscreenFrame.hidden = true;
      offscreenFrame.src = expected;
      offscreenFrame.onload = () => resolve();
      offscreenFrame.onerror = () => {
        offscreenFrame.remove();
        offscreenFrame = null;
        offscreenReady = null;
        reject(new Error("Could not load the offscreen document"));
      };
      document.documentElement.append(offscreenFrame);
    });
    return offscreenReady;
  }

  for (const api of new Set([browser, chrome])) {
    if (!api.offscreen) api.offscreen = { createDocument: createOffscreen };
    {
      const nativeGetContexts = api.runtime.getContexts?.bind(api.runtime);
      api.runtime.getContexts = async (filter = {}) => {
        const { contextTypes, documentUrls } = filter;
        if (offscreenReady) await offscreenReady;
        const url = browser.runtime.getURL("offscreen.html");
        const nativeTypes = contextTypes?.filter((type) => !["OFFSCREEN_DOCUMENT", "SIDE_PANEL"].includes(type));
        const contexts = nativeGetContexts && (!contextTypes || nativeTypes.length)
          ? await nativeGetContexts({ ...filter, ...(contextTypes && { contextTypes: nativeTypes }) })
          : [];
        return offscreenFrame?.isConnected &&
          (!contextTypes || contextTypes.includes("OFFSCREEN_DOCUMENT")) &&
          (!documentUrls || documentUrls.includes(url))
          ? [...contexts, { contextType: "OFFSCREEN_DOCUMENT", documentUrl: url }]
          : contexts;
      };
    }
    // Firefox has no equivalent for querying whether a button is pinned.
    // This only affects Pie's pin-button prompts and toolbar analytics.
    if (!api.action.getUserSettings) {
      api.action.getUserSettings = async () => ({ isOnToolbar: false });
    }
  }

  const dnr = browser.declarativeNetRequest;
  // Remote filter refreshes must not reject the entire batch because of a
  // Chrome-only condition. Omit the whole rule, never just its condition.
  for (const method of ["updateDynamicRules", "updateSessionRules"]) {
    const update = dnr[method].bind(dnr);
    dnr[method] = (options) => {
      const unsupported = (options.addRules || []).filter((rule) =>
        rule.condition.responseHeaders || rule.condition.excludedResponseHeaders);
      if (!unsupported.length) return update(options);
      console.warn("Pie Firefox: skipped unsupported response-header rules", unsupported.map((rule) => rule.id));
      return update({
        ...options,
        addRules: options.addRules.filter((rule) => !unsupported.includes(rule)),
        removeRuleIds: [...new Set([...(options.removeRuleIds || []), ...unsupported.map((rule) => rule.id)])],
      });
    };
  }
})();
