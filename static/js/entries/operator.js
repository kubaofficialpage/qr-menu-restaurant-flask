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
            const totalSeconds = Math.floor(diffMs / 1000);
            const hoursValue = Math.floor(totalSeconds / 3600);
            const minutesValue = Math.floor((totalSeconds % 3600) / 60);
            const secondsValue = totalSeconds % 60;

            const hours = String(hoursValue).padStart(2, "0");
            const minutes = String(minutesValue).padStart(2, "0");
            const seconds = String(secondsValue).padStart(2, "0");

            node.textContent = hoursValue > 0 ? `${hours}:${minutes}:${seconds}` : `${minutes}:${seconds}`;
        });
    };
    tick();
    setInterval(tick, 1000);
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
