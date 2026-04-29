import { state, saveCartToStorage } from './state.js';
import { isMenuItemAvailable, renderCartButton } from './render.js';

export function addItem(id) {
    if (!isMenuItemAvailable(id)) return;

    state.cartQty[id] = (state.cartQty[id] || 0) + 1;
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
    const cartCount = document.getElementById("cartCount");
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
