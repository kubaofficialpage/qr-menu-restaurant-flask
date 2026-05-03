export function readJsonScript(id) {
    const el = document.getElementById(id);
    if (!el || !el.textContent) return null;

    try {
        return JSON.parse(el.textContent);
    } catch {
        return null;
    }
}

export function getRestaurantSlug() {
    const fromScript = readJsonScript("restaurantSlug");
    if (typeof fromScript === "string" || fromScript === null) return fromScript;

    if (typeof window.RESTAURANT_SLUG === "string" || window.RESTAURANT_SLUG === null) {
        return window.RESTAURANT_SLUG;
    }

    return null;
}
