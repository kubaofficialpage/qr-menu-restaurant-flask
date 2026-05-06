// state.js - Глобальное состояние приложения
import { getRestaurantBranchPublicId, getRestaurantSlug } from "./page-context.js";

const CART_STORAGE_KEY = "qr_menu_cart";
const CART_TTL_MS = 1000 * 60 * 60; // 1 час

export const state = {
    restaurant: null,
    branch: null,
    menuData: [],           // список всех блюд
    menuById: new Map(),
    menuByCategory: new Map(),
    categories: [],         // список категорий
    categoriesById: new Map(),
    cart: [],               // корзина (резерв)
    cartQty: {},            // количество товаров в корзине {id: qty}
    activeCat: "all",       // активная категория
    renderToken: 0,
};

export function setMenuData(menuItems = [], categories = []) {
    state.menuData.length = 0;
    state.menuData.push(...menuItems);
    state.categories.length = 0;
    state.categories.push(...categories);

    state.menuById.clear();
    state.menuByCategory.clear();
    state.categoriesById.clear();

    state.menuData.forEach((item) => {
        const itemId = String(item.id);
        state.menuById.set(itemId, item);

        const categoryId = String(item.category_id ?? "");
        const categoryItems = state.menuByCategory.get(categoryId) || [];
        categoryItems.push(item);
        state.menuByCategory.set(categoryId, categoryItems);
    });

    state.categories.forEach((category) => {
        state.categoriesById.set(String(category.id), category);
    });

    state.renderToken += 1;
}

function getCartStorageKey() {
    const slug = getRestaurantSlug();
    const branchPublicId = getRestaurantBranchPublicId();
    return slug ? `${CART_STORAGE_KEY}:${slug}:${branchPublicId || "root"}` : CART_STORAGE_KEY;
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
