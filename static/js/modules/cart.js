import { getById } from './dom.js';
import { getMenuItem } from './menu-ui.js';
import { state, saveCartToStorage } from './state.js';
import { isMenuItemAvailable, renderCartButton } from './render.js';

export function addItem(id) {
    if (!isMenuItemAvailable(id)) return;

    state.cartQty[id] = (state.cartQty[id] || 0) + 1;
    trackCartAdd(id);
    persistCartChange(id);
}

export function removeItem(id) {
    if (!state.cartQty[id]) return;

    state.cartQty[id] -= 1;
    if (state.cartQty[id] <= 0) {
        delete state.cartQty[id];
    }

    persistCartChange(id);
}

export function updateCart() {
    removeUnavailableItems();
    updateCartCount();
    updateAllCartControls();
    saveCartToStorage();
}

export function updateItemUI(id) {
    document.querySelectorAll(`[data-cart-control-id="${CSS.escape(String(id))}"]`).forEach(control => {
        control.innerHTML = renderCartButton(id);
    });
}

function persistCartChange(id) {
    updateItemUI(id);
    updateCartCount();
    saveCartToStorage();
}

function updateAllCartControls() {
    document.querySelectorAll("[data-cart-control-id]").forEach(control => {
        control.innerHTML = renderCartButton(control.dataset.cartControlId);
    });
}

function updateCartCount() {
    const cartCount = getById("cartCount");
    if (!cartCount) return;

    cartCount.innerText = Object.values(state.cartQty)
        .reduce((sum, qty) => sum + Number(qty || 0), 0);
}

function removeUnavailableItems() {
    const availableIds = new Set(
        state.menuData
            .filter(item => item.is_available)
            .map(item => String(item.id))
    );

    Object.keys(state.cartQty).forEach(id => {
        if (!availableIds.has(String(id)) || state.cartQty[id] <= 0) {
            delete state.cartQty[id];
        }
    });
}

function trackCartAdd(id) {
    const restaurantId = state.restaurant?.id;
    if (!restaurantId) return;
    if (!getMenuItem(id)) return;

    const payload = JSON.stringify({
        restaurantId,
        menuItemId: Number(id),
        quantityDelta: 1,
    });

    if (navigator.sendBeacon) {
        const blob = new Blob([payload], { type: "application/json" });
        navigator.sendBeacon("/api/analytics/cart-add", blob);
        return;
    }

    fetch("/api/analytics/cart-add", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: payload,
        keepalive: true,
    }).catch(() => {});
}
