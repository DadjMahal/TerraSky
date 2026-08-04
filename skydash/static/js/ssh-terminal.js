/* ============================================================================
   SkyDash — #16 Built-in SSH terminal (xterm.js + Socket.IO)
   Connects to the /ssh namespace; only the Hermes instance is SSH-enabled.
   ============================================================================ */
(function () {
    "use strict";
    let term = null, socket = null, fitAddon = null, inited = false;

    function init(slug) {
        const host = document.getElementById("ssh-host");
        if (!host) return;
        if (inited) { return; }
        inited = true;

        if (typeof Terminal === "undefined" || typeof io === "undefined") {
            host.innerHTML = '<div class="ssh-banner">Loading terminal libraries…</div>';
            const s1 = document.createElement("script");
            s1.src = "https://cdn.jsdelivr.net/npm/@xterm/xterm@5.5.0/lib/xterm.min.js";
            s1.onload = () => {
                const fit = document.createElement("script");
                fit.src = "https://cdn.jsdelivr.net/npm/@xterm/addon-fit@0.10.0/lib/addon-fit.min.js";
                fit.onload = () => start(slug);
                document.head.appendChild(fit);
            };
            const css = document.createElement("link");
            css.rel = "stylesheet";
            css.href = "https://cdn.jsdelivr.net/npm/@xterm/xterm@5.5.0/css/xterm.css";
            document.head.appendChild(css);
            const sio = document.createElement("script");
            sio.src = "https://cdn.jsdelivr.net/npm/socket.io@4.7.5/client-dist/socket.io.min.js";
            sio.onload = () => {};
            document.head.appendChild(sio);
            s1.onload = () => {
                if (window.io) start(slug);
                else { const w = setInterval(() => { if (window.io && window.Terminal) { clearInterval(w); start(slug); } }, 100); }
            };
            return;
        }
        start(slug);
    }

    function start(slug) {
        const host = document.getElementById("ssh-host");
        if (!host || typeof Terminal === "undefined" || typeof io === "undefined") return;
        host.innerHTML = '<div id="ssh-terminal"></div>';
        const target = document.getElementById("ssh-terminal");
        if (!target) return;

        term = new Terminal({ cursorBlink: true, fontSize: 13, theme: { background: "#000000", foreground: "#00ff00" } });
        if (window.FitAddon) { fitAddon = new FitAddon.FitAddon(); term.loadAddon(fitAddon); }
        term.open(target);
        if (fitAddon) fitAddon.fit();
        term.writeln("Connecting to SSH session…");

        socket = io("/ssh", { transports: ["websocket", "polling"] });
        socket.emit("ssh_open", { slug });
        socket.on("ssh_status", (d) => {
            if (d.ok) term.writeln(`\x1b[32mConnected to ${d.host}\x1b[0m`);
            else term.writeln(`\x1b[31m${d.error || "Disconnected"}\x1b[0m`);
        });
        socket.on("ssh_output", (d) => term.write(d.data || ""));
        term.onData((data) => socket.emit("ssh_input", { data }));
        term.onResize(({ cols, rows }) => socket.emit("ssh_resize", { cols, rows }));
        window.addEventListener("resize", () => { if (fitAddon) fitAddon.fit(); });
    }

    window.SkyDashSSHTerminal = { init };
})();
