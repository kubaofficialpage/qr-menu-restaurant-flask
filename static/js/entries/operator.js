document.addEventListener("DOMContentLoaded", () => {
    initTimers();
    initSocket();
});

function initTimers() {
    const tick = () => {
        document.querySelectorAll("[data-order-timer]").forEach(node => {
            const createdAt = node.dataset.createdAt;
            if (!createdAt) return;
            const created = new Date(createdAt);
            const diffMs = Math.max(0, Date.now() - created.getTime());
            const totalMinutes = Math.floor(diffMs / 60000);
            const hours = String(Math.floor(totalMinutes / 60)).padStart(2, "0");
            const minutes = String(totalMinutes % 60).padStart(2, "0");
            node.textContent = `${hours}:${minutes}`;
        });
    };
    tick();
    setInterval(tick, 30000);
}

function initSocket() {
    const configElement = document.getElementById("operatorSocketConfig");
    if (!configElement || typeof io === "undefined") return;

    let config = {};
    try {
        config = JSON.parse(configElement.textContent || "{}");
    } catch {
        config = {};
    }

    const socket = io();
    socket.on("connect", () => {
        socket.emit("join_operator_room", { branchId: Number(config.branchId || 0) });
    });

    let reloadQueued = false;
    socket.on("operator_orders_changed", () => {
        if (reloadQueued) return;
        reloadQueued = true;
        setTimeout(() => window.location.reload(), 500);
    });
}
