import { state } from './state.js';

export const IMAGE_PLACEHOLDER = "/static/resource/img/placeholder-dish.svg";

export function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

export function getMenuItem(id) {
    return state.menuData.find(item => String(item.id) === String(id));
}

export function isMenuItemAvailable(id) {
    return Boolean(getMenuItem(id)?.is_available);
}

export function getMenuImageSrc(item) {
    return item.image ? `/static/resource/${item.image}` : "/static/resource/img/default_food_png.png";
}

export function renderMenuImageMarkup({
    src,
    alt = "",
    placeholderClass = "image-placeholder w-full h-40 object-contain p-8",
    spinnerClass = "image-spinner",
    imageClass = "menu-image absolute inset-0 w-full h-40 object-cover rounded-[16px] p-1 opacity-0",
    dataAttributeName = "data-menu-image-src",
}) {
    return `
        <img src="${IMAGE_PLACEHOLDER}" alt="" class="${placeholderClass}">
        <div class="${spinnerClass}"></div>
        <img
            src="${escapeHtml(src)}"
            ${dataAttributeName}="${escapeHtml(src)}"
            alt="${escapeHtml(alt)}"
            loading="lazy"
            decoding="async"
            class="${imageClass}"
        >
    `;
}

export function formatShortText(value, maxLength, suffix = "...") {
    const text = String(value ?? "");
    return text.length > maxLength ? text.slice(0, maxLength) + suffix : text;
}

export function renderUnavailableOverlay() {
    return `
        <div data-availability-overlay class="absolute inset-1 flex items-center justify-center rounded-[16px] bg-white/70 backdrop-blur-[1px]">
            ${renderUnavailableBadge()}
        </div>
    `;
}

export function renderUnavailableBadge() {
    return `
        <span class="rounded-full bg-amber-100 px-3 py-2 text-xs font-bold text-amber-700 shadow">
            Будет позже
        </span>
    `;
}

export function renderQuantityControl(id, qty, mode = "menu") {
    const isCartPage = mode === "cart-page";
    const addAction = isCartPage ? "add" : "addItem";
    const removeAction = isCartPage ? "remove" : "removeItem";
    const actionAttr = isCartPage ? "data-cart-page-action" : "data-action";
    const safeId = escapeHtml(id);

    if (qty === 0) {
        return `
            <button type="button" ${actionAttr}="${addAction}" data-param="${safeId}" class="w-9 h-9 bg-white rounded-full shadow flex items-center justify-center text-xl font-bold" aria-label="Добавить в корзину">
                +
            </button>
        `;
    }

    return `
        <div class="flex items-center bg-white rounded-full shadow" aria-label="Количество в корзине">
            <button type="button" ${actionAttr}="${removeAction}" data-param="${safeId}" class="w-8 h-8 flex items-center justify-center text-lg" aria-label="Уменьшить количество">
                -
            </button>
            <span class="px-2 text-sm font-bold">${qty}</span>
            <button type="button" ${actionAttr}="${addAction}" data-param="${safeId}" class="w-8 h-8 flex items-center justify-center text-lg" aria-label="Увеличить количество">
                +
            </button>
        </div>
    `;
}

export function setText(element, value) {
    if (!element) return;

    const text = String(value ?? "");
    if (element.innerText !== text) {
        element.innerText = text;
    }
}
