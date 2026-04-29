// state.js - Глобальное состояние приложения
const CART_STORAGE_KEY = "qr_menu_cart";
const CART_TTL_MS = 1000 * 60 * 60; // 1 час

export const state = {
    menuData: [],           // список всех блюд
    categories: [],         // список категорий
    cart: [],               // корзина (резерв)
    cartQty: {},            // количество товаров в корзине {id: qty}
    activeCat: "all"        // активная категория
};

function getCartStorageKey() {
    return window.RESTAURANT_SLUG ? `${CART_STORAGE_KEY}:${window.RESTAURANT_SLUG}` : CART_STORAGE_KEY;
}

function isExpired(timestamp) {
    if (!timestamp) return true;
    return Date.now() - timestamp > CART_TTL_MS;
}

export function loadCartFromStorage() {
    try {
        const raw = localStorage.getItem(getCartStorageKey());
        if (!raw) return;
        const data = JSON.parse(raw);
        if (!data || isExpired(data.updatedAt)) {
            localStorage.removeItem(getCartStorageKey());
            return;
        }
        state.cartQty = data.cartQty || {};
    } catch (err) {
        console.warn("Failed to load cart from storage", err);
    }
}

export function saveCartToStorage() {
    try {
        const data = {
            cartQty: state.cartQty,
            updatedAt: Date.now(),
        };
        localStorage.setItem(getCartStorageKey(), JSON.stringify(data));
    } catch (err) {
        console.warn("Failed to save cart to storage", err);
    }
}
