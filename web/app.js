(() => {
  const $ = (id) => document.getElementById(id);

  const setText = (id, value) => {
    const node = $(id);
    if (node) node.textContent = value;
  };

  const statusClass = (status) => status === "ready" ? "ready" : "pending";

  function render(data) {
    const stats = data.stats || {};
    setText("groups", stats.verified_groups ?? 0);
    setText("candidates", stats.candidates ?? 0);
    setText("evidence", stats.evidence_records ?? 0);
    setText("sources", stats.observed_sources ?? 0);

    setText("engine-status", data.engine?.status || "unknown");
    setText("engine-mode", data.engine?.mode || "unknown");
    setText("last-update", data.generated_at ? new Date(data.generated_at).toLocaleString() : "No discovery run yet");

    const channels = data.channels || {};
    ["clearweb", "forums", "onion", "onion_index"].forEach((key) => {
      const node = document.querySelector(`[data-channel="${key}"] .channel-status`);
      if (!node) return;
      const status = channels[key] || "unknown";
      node.textContent = status.toUpperCase();
      node.className = `channel-status ${statusClass(status)}`;
    });

    const list = $("observations");
    const empty = $("observations-empty");
    list.querySelectorAll(".observation").forEach((node) => node.remove());

    const observations = Array.isArray(data.observations) ? data.observations : [];
    if (!observations.length) {
      empty.hidden = false;
      return;
    }

    empty.hidden = true;
    observations.slice(0, 20).forEach((item) => {
      const article = document.createElement("article");
      article.className = "observation";
      const signals = Array.isArray(item.signals) && item.signals.length ? item.signals.join(" · ") : "No matching signals";
      article.innerHTML = `
        <div class="observation-main">
          <b>${escapeHtml(item.title || "Untitled observation")}</b>
          <span>${escapeHtml(item.channel || "unknown")} · ${escapeHtml(item.source_name || "unknown source")}</span>
          <small>${escapeHtml(item.masked_url || "")}</small>
          <small>${escapeHtml(signals)}</small>
        </div>
        <div class="observation-meta">
          <strong>${escapeHtml(item.status || "unverified")}</strong>
          <span>${escapeHtml(item.confidence || "unknown")} · score ${escapeHtml(item.score ?? 0)}</span>
        </div>`;
      list.appendChild(article);
    });
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>'"]/g, (char) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", "\"": "&quot;"
    }[char]));
  }

  fetch("./data.json", { cache: "no-store" })
    .then((response) => {
      if (!response.ok) throw new Error(`data.json: ${response.status}`);
      return response.json();
    })
    .then(render)
    .catch((error) => {
      setText("engine-status", "data unavailable");
      setText("last-update", error.message);
    });
})();
