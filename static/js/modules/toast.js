const TOAST_REMOVE_DELAY = 300;
const DEFAULT_TOAST_DURATION = 3500;

export function showToast(message, type = "error", duration = DEFAULT_TOAST_DURATION) {
    const container = getToastContainer();
    const toast = document.createElement("div");

    toast.className = `toast toast-${type}`;
    toast.setAttribute("role", "status");
    toast.innerText = message;

    container.appendChild(toast);

    requestAnimationFrame(() => {
        toast.classList.add("is-visible");
    });

    setTimeout(() => {
        toast.classList.remove("is-visible");
        setTimeout(() => toast.remove(), TOAST_REMOVE_DELAY);
    }, duration);
}

function getToastContainer() {
    let container = document.getElementById("toastContainer");
    if (container) return container;

    container = document.createElement("div");
    container.id = "toastContainer";
    container.className = "toast-container";
    document.body.appendChild(container);
    return container;
}
