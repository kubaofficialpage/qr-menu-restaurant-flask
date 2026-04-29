const activeLocks = new Set();

function blockReload(e) {
    e.preventDefault();
    e.returnValue = "";
}

export function lockPageScroll(lockId) {
    if (!lockId || activeLocks.has(lockId)) return;

    activeLocks.add(lockId);
    if (activeLocks.size > 1) return;

    document.documentElement.classList.add("modal-open");
    document.body.classList.add("modal-open");
    window.addEventListener("beforeunload", blockReload);
}

export function unlockPageScroll(lockId) {
    if (!lockId || !activeLocks.has(lockId)) return;

    activeLocks.delete(lockId);
    if (activeLocks.size > 0) return;

    document.documentElement.classList.remove("modal-open");
    document.body.classList.remove("modal-open");
    window.removeEventListener("beforeunload", blockReload);
}
