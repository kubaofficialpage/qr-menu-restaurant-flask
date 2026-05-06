const SOUND_STORAGE_KEY = "operator_sound_enabled";

let operatorSocketConfig = {};
let newOrderAudio = null;

document.addEventListener("DOMContentLoaded", () => {
    operatorSocketConfig = readOperatorConfig();
    initTimers();
    initAccordions();
    initOperatorMenus();
    initSoundSettings();
    initNewOrderAlert();
    initSocket();
});

function readOperatorConfig() {
    const configElement = document.getElementById("operatorSocketConfig");
    if (!configElement) return {};

    try {
        return JSON.parse(configElement.textContent || "{}");
    } catch {
        return {};
    }
}

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
    if (typeof io === "undefined") return;

    const socket = io();
    socket.on("connect", () => {
        socket.emit("join_operator_room", { branchId: Number(operatorSocketConfig.branchId || 0) });
    });

    let reloadQueued = false;
    socket.on("operator_orders_changed", () => {
        if (reloadQueued) return;
        reloadQueued = true;
        setTimeout(() => window.location.reload(), 500);
    });
}

function initNewOrderAlert() {
    if (!operatorSocketConfig.hasNewOrders) return;

    newOrderAudio = new Audio("/static/resource/sound/new_order.mp3");
    newOrderAudio.loop = true;
    newOrderAudio.preload = "auto";

    playNewOrderAlertIfEnabled();
}

function initSoundSettings() {
    updateSoundToggleButtons();

    document.querySelectorAll("[data-operator-sound-toggle]").forEach(button => {
        button.addEventListener("click", event => {
            event.preventDefault();
            const nextValue = !isSoundEnabled();
            setSoundEnabled(nextValue);
            updateSoundToggleButtons();

            if (nextValue) {
                playNewOrderAlertIfEnabled();
            } else {
                stopNewOrderAlert();
            }
        });
    });
}

function playNewOrderAlertIfEnabled() {
    if (!newOrderAudio || !isSoundEnabled()) return;

    const tryPlay = () => {
        newOrderAudio.play().then(() => {
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

function stopNewOrderAlert() {
    if (!newOrderAudio) return;
    newOrderAudio.pause();
    newOrderAudio.currentTime = 0;
}

function isSoundEnabled() {
    const storedValue = window.localStorage.getItem(SOUND_STORAGE_KEY);
    return storedValue !== "off";
}

function setSoundEnabled(enabled) {
    window.localStorage.setItem(SOUND_STORAGE_KEY, enabled ? "on" : "off");
}

function updateSoundToggleButtons() {
    const enabled = isSoundEnabled();

    document.querySelectorAll("[data-operator-sound-toggle]").forEach(button => {
        const textNode = button.querySelector("[data-operator-sound-toggle-text]");
        const iconNode = button.querySelector("[data-operator-sound-toggle-icon]");

        if (textNode) {
            textNode.textContent = enabled ? "Off sound" : "On sound";
        }

        if (iconNode) {
            iconNode.className = enabled
                ? "fa-solid fa-volume-high"
                : "fa-solid fa-volume-xmark";
            iconNode.setAttribute("aria-hidden", "true");
        }
    });
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

function initOperatorMenus() {
    const menus = Array.from(document.querySelectorAll("[data-operator-menu]"));
    if (!menus.length) return;

    document.addEventListener("click", event => {
        menus.forEach(menu => {
            if (menu.contains(event.target)) return;
            menu.removeAttribute("open");
        });
    });

    document.addEventListener("keydown", event => {
        if (event.key !== "Escape") return;
        menus.forEach(menu => menu.removeAttribute("open"));
    });
}
