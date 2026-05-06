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

export function getRestaurantBranchPublicId() {
    const fromScript = readJsonScript("restaurantBranchPublicId");
    if (typeof fromScript === "string" || fromScript === null) return fromScript;

    if (typeof window.RESTAURANT_BRANCH_PUBLIC_ID === "string" || window.RESTAURANT_BRANCH_PUBLIC_ID === null) {
        return window.RESTAURANT_BRANCH_PUBLIC_ID;
    }

    return null;
}
