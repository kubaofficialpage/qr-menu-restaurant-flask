const idCache = new Map();

export function getById(id) {
    const cached = idCache.get(id);
    if (!cached) {
        const current = document.getElementById(id);
        if (current) {
            idCache.set(id, current);
        }
        return current;
    }
    return cached;
}

export function resetById(id) {
    idCache.delete(id);
}
