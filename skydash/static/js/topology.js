/* ============================================================================
   SkyDash — #14 Network topology map
   SVG diagram: Internet -> Public IP -> Instance -> Private IP / DNS.
   Uses instance data already rendered in the page (window.SKYDASH_INST).
   ============================================================================ */
(function () {
    "use strict";
    function render() {
        const host = document.getElementById("topology-host");
        if (!host) return;
        const inst = window.SKYDASH_INST || {};
        const pub = inst.public_ip || "—";
        const priv = inst.private_ip || "—";
        const pdns = inst.public_dns || "—";
        host.innerHTML = `
        <svg class="topology-svg" viewBox="0 0 640 220">
          <line class="link" x1="80" y1="110" x2="220" y2="110"/>
          <line class="link" x1="420" y1="110" x2="560" y2="60"/>
          <line class="link" x1="420" y1="110" x2="560" y2="160"/>
          <circle class="node" cx="50" cy="110" r="34"/>
          <text class="node-label node-label-title" x="50" y="115" text-anchor="middle">INTERNET</text>
          <circle class="node node-primary" cx="320" cy="110" r="44"/>
          <text class="node-label node-label-title" x="320" y="106" text-anchor="middle">${(inst.name || "").slice(0,14)}</text>
          <text class="node-label" x="320" y="122" text-anchor="middle">${inst.provider || ""}</text>
          <circle class="node" cx="590" cy="60" r="30"/>
          <text class="node-label node-label-title" x="590" y="64" text-anchor="middle">PRIVATE</text>
          <circle class="node" cx="590" cy="160" r="30"/>
          <text class="node-label node-label-title" x="590" y="164" text-anchor="middle">DNS</text>
          <text class="node-label node-label-ip" x="150" y="100" text-anchor="middle">${pub}</text>
          <text class="node-label node-label-ip" x="490" y="55" text-anchor="middle">${priv}</text>
          <text class="node-label node-label-ip" x="490" y="155" text-anchor="middle">${pdns}</text>
        </svg>
        <div class="small text-faint mt-2">Security groups rendered below.</div>`;
    }
    window.SkyDashTopology = { render };
})();
