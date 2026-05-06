document.addEventListener("DOMContentLoaded", () => {
    initTimers();
    initAccordions();
    initNewOrderAlert();
    initSocket();
});

function initTimers() {
    const tick = () => {
        document.querySelectorAll("[data-order-timer]").forEach(node => {
            const createdAt = node.dataset.createdAt;
            const stoppedAt = node.dataset.stoppedAt;
            if (!createdAt) return;
            const created = new Date(createdAt);
            const endTime = stoppedAt ? new Date(stoppedAt).getTime() : Date.now();
            const diffMs = Math.max(0, endTime - created.getTime());
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

function initNewOrderAlert() {
    const configElement = document.getElementById("operatorSocketConfig");
    if (!configElement) return;

    let config = {};
    try {
        config = JSON.parse(configElement.textContent || "{}");
    } catch {
        config = {};
    }

    if (!config.hasNewOrders) return;

    const audio = new Audio("/static/resource/sound/new_order.mp3");
    audio.loop = true;
    audio.preload = "auto";

    const tryPlay = () => {
        audio.play().then(() => {
            cleanupUnlockListeners();
        }).catch(() => {
            bindUnlockListeners();
        });
    };

    const bindUnlockListeners = () => {
        ["click", "touchstart", "keydown"].forEach(eventName => {
            window.addEventListener(eventName, tryPlay, { once: true });
        });
    };

    const cleanupUnlockListeners = () => {
        ["click", "touchstart", "keydown"].forEach(eventName => {
            window.removeEventListener(eventName, tryPlay);
        });
    };

    tryPlay();
}

function initAccordions() {
    document.querySelectorAll("[data-operator-accordion-button]").forEach(button => {
        const targetId = button.dataset.target;
        const body = targetId ? document.getElementById(targetId) : null;
        const icon = button.querySelector("[data-operator-accordion-icon]");
        if (!body) return;

        body.classList.add("hidden");
        icon?.classList.remove("rotate-180");

        button.addEventListener("click", () => {
            const isHidden = body.classList.contains("hidden");
            body.classList.toggle("hidden", !isHidden);
            icon?.classList.toggle("rotate-180", isHidden);
        });
    });
}
