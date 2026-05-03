import { fetchMenuData } from './api.js';
import { state, loadCartFromStorage, saveCartToStorage } from './state.js';
import {
    IMAGE_PLACEHOLDER,
    escapeHtml,
    formatShortText,
    getMenuImageSrc,
    getMenuItem,
    renderQuantityControl,
    renderUnavailableOverlay,
} from './menu-ui.js';
import { lockPageScroll, unlockPageScroll } from './scroll-lock.js';
import { showToast } from './toast.js';
import { initImageLoading } from './image.js';
import { applyTranslations, bindLangSwitcher, initI18n, t } from './i18n.js';

const CART_PAGE_TOUR_STORAGE_KEY = "qr_menu_cart_page_tour_seen";
const MENU_ITEM_STAGGER_MS = 45;
const MENU_ITEM_MAX_DELAY_MS = 450;
const CART_ITEM_EXIT_FALLBACK_MS = 320;
let cartTourStep = 0;

document.addEventListener('DOMContentLoaded', () => {
    initI18n("ru");
    applyTranslations();
    bindLangSwitcher();
    initImageLoading();
    loadCartFromStorage();
    bindCartPageActions();

    renderCartPageSkeleton();

    window.addEventListener("qrMenuLangChanged", () => {
        applyTranslations();
        refreshCartPage();
        renderMenuSuggestions();
    });

    fetchMenuData()
        .then(renderCartPage)
        .catch(error => {
            console.error('Error loading cart page data:', error);
            showToast(t("no_server_response"));
            renderCartPage();
        });
});

function renderCartPageSkeleton() {
    const itemsContainer = document.getElementById("cartPageItems");
    if (itemsContainer && itemsContainer.dataset.skeleton !== "true") {
        itemsContainer.dataset.skeleton = "true";
        itemsContainer.innerHTML = Array.from({ length: 3 }).map(() => {
            return `
                <div class="grid grid-cols-[72px_1fr_auto] items-center gap-3 bg-white">
                    <div class="h-[72px] w-[72px] shrink-0 rounded-[18px] bg-gray-200 animate-pulse"></div>
                    <div class="flex-1 space-y-2">
                        <div class="h-4 w-40 bg-gray-200 rounded animate-pulse"></div>
                        <div class="h-3 w-56 bg-gray-200 rounded animate-pulse"></div>
                    </div>
                    <div class="h-8 w-24 rounded-xl bg-gray-200 animate-pulse"></div>
                </div>
            `.trim();
        }).join("");
    }

    const menuContainer = document.getElementById("cartPageMenu");
    if (menuContainer && menuContainer.dataset.skeleton !== "true") {
        menuContainer.dataset.skeleton = "true";
        menuContainer.innerHTML = Array.from({ length: 6 }).map(() => {
            return `
                <article class="bg-white p-0">
                    <div class="bg-slate-50 rounded-[18px] overflow-hidden">
                        <div class="w-full h-40 bg-gray-200 animate-pulse"></div>
                    </div>
                    <div class="px-1 pt-2 space-y-2">
                        <div class="h-4 w-16 bg-gray-200 rounded animate-pulse"></div>
                        <div class="h-3 w-24 bg-gray-200 rounded animate-pulse"></div>
                    </div>
                </article>
            `.trim();
        }).join("");
    }
}

function bindCartPageActions() {
    document.addEventListener('click', (e) => {
        const action = e.target.closest('[data-cart-page-action]');
        if (!action) return;

        e.preventDefault();
        const id = action.dataset.param;
        const item = getMenuItem(id);
        if (!item?.is_available) return;

        if (action.dataset.cartPageAction === 'add') {
            state.cartQty[id] = (state.cartQty[id] || 0) + 1;
        }

        if (action.dataset.cartPageAction === 'remove') {
            if (!state.cartQty[id]) return;
            state.cartQty[id]--;
            if (state.cartQty[id] <= 0) {
                delete state.cartQty[id];
            }
        }

        saveCartToStorage();
        refreshCartPage();
    });

    document.getElementById("clearCartPageBtn")?.addEventListener('click', openClearModal);
    document.getElementById("cancelClearCartPageBtn")?.addEventListener('click', closeClearModal);
    document.getElementById("confirmClearCartPageBtn")?.addEventListener('click', confirmClearCart);

    document.getElementById("splitBillPageBtn")?.addEventListener('click', openSplitModal);
    document.getElementById("closeSplitPageBtn")?.addEventListener('click', closeSplitModal);
    document.getElementById("calculateSplitPageBtn")?.addEventListener('click', calculateSplit);
    document.getElementById("clearCartPageModal")?.addEventListener('click', closeModalOnBackdrop);
    document.getElementById("splitBillPageModal")?.addEventListener('click', closeModalOnBackdrop);
    document.getElementById("cartTourNextBtn")?.addEventListener('click', nextCartTourStep);
    document.getElementById("cartTourSkipBtn")?.addEventListener('click', completeCartTour);
    window.addEventListener('resize', positionCartTour);
    window.addEventListener('scroll', positionCartTour, { passive: true });

    document.getElementById("cartPageCheckout")?.addEventListener('click', (e) => {
        e.preventDefault();
        alert(t("checkout_not_connected"));
    });
}

function renderCartPage() {
    refreshCartPage();
    renderMenuSuggestions();
    maybeStartCartTour();
}

function refreshCartPage() {
    const cartItems = getCartItems();
    const total = cartItems.reduce((sum, item) => sum + item.price * item.qty, 0);

    document.getElementById("cartPageTotal").innerText = total;
    document.getElementById("splitPageTotal").innerText = total;
    setActionsDisabled(cartItems.length === 0);
    renderCartItems(cartItems);
    updateMenuSuggestionControls();
}

function renderCartItems(items) {
    const container = document.getElementById("cartPageItems");
    if (!container) return;

    if (container.dataset.skeleton === "true") {
        container.innerHTML = "";
        delete container.dataset.skeleton;
    }

    if (items.length === 0 && !container.querySelector("[data-cart-list-item-id]")) {
        container.innerHTML = `
            <div data-cart-empty class="text-center text-gray-500 py-8">
                ${t("cart_empty")}
            </div>
        `;
        return;
    }

    container.querySelector("[data-cart-empty]")?.remove();

    const rows = new Map(
        [...container.querySelectorAll("[data-cart-list-item-id]")]
            .map(row => [row.dataset.cartListItemId, row])
    );
    const activeIds = new Set(items.map(item => String(item.id)));

    rows.forEach((row, id) => {
        if (!activeIds.has(id)) {
            animateCartListItemExit(row, container);
        }
    });

    items.forEach(item => {
        const id = String(item.id);
        const row = rows.get(id);

        if (row) {
            row.classList.remove("is-leaving");
            updateCartListItem(row, item);
            return;
        }

        container.appendChild(createElementFromHtml(renderCartListItem(item)));
    });
}

function animateCartListItemExit(row, container) {
    if (row.classList.contains("is-leaving")) return;

    row.classList.add("is-leaving");

    const removeRow = () => {
        if (!row.classList.contains("is-leaving")) return;

        row.remove();
        if (!container.querySelector("[data-cart-list-item-id]")) {
            showCartEmptyState(container);
        }
    };

    row.addEventListener("animationend", removeRow, { once: true });
    setTimeout(() => {
        if (row.isConnected) removeRow();
    }, CART_ITEM_EXIT_FALLBACK_MS);
}

function showCartEmptyState(container) {
    if (container.querySelector("[data-cart-empty]")) return;

    container.innerHTML = `
        <div data-cart-empty class="text-center text-gray-500 py-8">
            ${t("cart_empty")}
        </div>
    `;
}

function renderMenuSuggestions() {
    const container = document.getElementById("cartPageMenu");
    if (!container) return;

    if (container.dataset.skeleton === "true") {
        container.innerHTML = "";
        delete container.dataset.skeleton;
    }

    const items = state.menuData.slice(0, 12);
    if (items.length === 0) {
        container.innerHTML = `
            <div class="col-span-3 text-center text-gray-500 py-8">
                ${t("menu_unavailable")}
            </div>
        `;
        return;
    }

    if (container.dataset.rendered === "true") {
        updateMenuSuggestionControls();
        return;
    }

    container.innerHTML = items.map(renderMenuCard).join("");
    container.dataset.rendered = "true";
}

function getCartItems() {
    const items = [];

    Object.entries(state.cartQty).forEach(([id, qty]) => {
        const item = getMenuItem(id);
        if (!item || !item.is_available || qty <= 0) {
            delete state.cartQty[id];
            return;
        }

        items.push({ ...item, qty });
    });

    return items;
}

function renderCartListItem(item) {
    const imageSrc = getMenuImageSrc(item);
    const amount = formatAmount(item.amount);

    return `
        <article data-cart-list-item-id="${escapeHtml(item.id)}" class="cart-list-item grid grid-cols-[72px_1fr_auto] items-center gap-3 bg-white">
            <div class="relative h-[72px] w-[72px] shrink-0 overflow-hidden rounded-[20px] bg-slate-50">
                <img src="${IMAGE_PLACEHOLDER}" alt="" class="h-full w-full object-contain p-3" />
                <div class="image-spinner image-spinner-sm"></div>
                <img
                    src="${escapeHtml(imageSrc)}"
                    alt="${escapeHtml(item.name)}"
                    loading="lazy"
                    decoding="async"
                    class="menu-image absolute inset-0 h-full w-full object-cover opacity-0"
                />
            </div>
            <div class="min-w-0 flex-1 self-stretch flex flex-col justify-center">
                <div class="font-semibold text-sm leading-tight truncate">${escapeHtml(item.name)}</div>
                <div class="text-sm leading-tight mt-1">
                    <span data-cart-line-total class="font-semibold">${item.qty * item.price} c</span>
                    <span class="text-gray-400"> - </span>
                    <span class="text-gray-500">${escapeHtml(item.price)} c${amount}</span>
                </div>
            </div>
            <div class="cart-list-counter shrink-0 flex items-center rounded-xl bg-slate-50">
                <button data-cart-page-action="remove" data-param="${item.id}" class="w-9 h-8 flex items-center justify-center text-lg leading-none">-</button>
                <span data-cart-qty class="w-8 text-center text-sm font-semibold">${item.qty}</span>
                <button data-cart-page-action="add" data-param="${item.id}" class="w-9 h-8 flex items-center justify-center text-lg leading-none">+</button>
            </div>
        </article>
    `;
}

function updateCartListItem(row, item) {
    const qty = row.querySelector("[data-cart-qty]");
    const lineTotal = row.querySelector("[data-cart-line-total]");

    if (qty) qty.innerText = item.qty;
    if (lineTotal) lineTotal.innerText = `${item.qty * item.price} c`;
}

function renderMenuCard(item, index = 0) {
    const imageSrc = getMenuImageSrc(item);
    const isAvailable = Boolean(item.is_available);
    const delay = Math.min(index * MENU_ITEM_STAGGER_MS, MENU_ITEM_MAX_DELAY_MS);

    return `
        <article class="cart-product-card menu-item is-entering bg-white p-0 ${isAvailable ? "" : "opacity-70"}" style="--menu-item-delay:${delay}ms">
            <div class="img-box relative overflow-hidden rounded-[20px] bg-slate-50">
                <img src="${IMAGE_PLACEHOLDER}" alt="" class="image-placeholder w-full h-40 object-contain p-8" />
                <div class="image-spinner"></div>
                <img
                    src="${escapeHtml(imageSrc)}"
                    alt="${escapeHtml(item.name)}"
                    loading="lazy"
                    decoding="async"
                    class="menu-image absolute inset-0 h-40 w-full object-cover opacity-0"
                />
                ${isAvailable ? "" : renderUnavailableOverlay()}
                <div data-cart-page-control-id="${escapeHtml(item.id)}" class="absolute bottom-2 right-2">
                    ${renderCartPageButton(item.id)}
                </div>
            </div>
            <div class="px-1 pt-2 pb-1">
                <h2 class="text-lg font-bold leading-none text-slate-900">${escapeHtml(item.price)} c</h2>
                <h4 class="mt-1 text-md text-slate-900">${escapeHtml(formatShortText(item.name, 15))}</h4>
                <h6 class="text-gray-500 text-sm">${escapeHtml(item.amount)}</h6>
            </div>
        </article>
    `;
}

function renderCartPageButton(id) {
    const item = getMenuItem(id);
    if (!item?.is_available) return "";

    return renderQuantityControl(id, state.cartQty[id] || 0, "cart-page");
}

function updateMenuSuggestionControls() {
    document.querySelectorAll("[data-cart-page-control-id]").forEach(control => {
        control.innerHTML = renderCartPageButton(control.dataset.cartPageControlId);
    });
}

function setActionsDisabled(isDisabled) {
    ["clearCartPageBtn", "splitBillPageBtn"].forEach(id => {
        const button = document.getElementById(id);
        if (!button) return;
        button.disabled = isDisabled;
        button.classList.toggle("opacity-40", isDisabled);
        button.classList.toggle("cursor-not-allowed", isDisabled);
    });
}

function openClearModal() {
    document.getElementById("clearCartPageModal").classList.remove("hidden");
    lockPageScroll("cart-clear-modal");
}

function closeClearModal() {
    document.getElementById("clearCartPageModal").classList.add("hidden");
    unlockPageScroll("cart-clear-modal");
}

function confirmClearCart() {
    Object.keys(state.cartQty).forEach(id => delete state.cartQty[id]);
    saveCartToStorage();
    closeClearModal();
    refreshCartPage();
}

function openSplitModal() {
    const total = document.getElementById("cartPageTotal").innerText;
    document.getElementById("splitPageTotal").innerText = total;
    document.getElementById("splitPageGuestsCount").value = "";
    document.getElementById("splitPageResult").classList.add("hidden");
    document.getElementById("splitBillPageModal").classList.remove("hidden");
    lockPageScroll("cart-split-modal");
}

function closeSplitModal() {
    document.getElementById("splitBillPageModal").classList.add("hidden");
    unlockPageScroll("cart-split-modal");
}

function closeModalOnBackdrop(e) {
    if (e.target !== e.currentTarget) return;

    if (e.currentTarget.id === "clearCartPageModal") {
        closeClearModal();
        return;
    }

    if (e.currentTarget.id === "splitBillPageModal") {
        closeSplitModal();
    }
}

function calculateSplit() {
    const total = Number(document.getElementById("splitPageTotal").innerText || 0);
    const guests = parseInt(document.getElementById("splitPageGuestsCount").value);
    const perPerson = guests > 0 ? Math.ceil(total / guests) : t("specify_guests");

    document.getElementById("splitPagePerPerson").innerText = perPerson;
    document.getElementById("splitPageResult").classList.remove("hidden");
}

function formatAmount(value) {
    const amount = String(value ?? "").trim();
    return amount ? ` / ${escapeHtml(amount)}` : "";
}

function createElementFromHtml(html) {
    const template = document.createElement("template");
    template.innerHTML = html.trim();
    return template.content.firstElementChild;
}

function maybeStartCartTour() {
    if (localStorage.getItem(CART_PAGE_TOUR_STORAGE_KEY) === "1") return;
    const popover = document.getElementById("cartTourPopover");
    const overlay = document.getElementById("cartTourOverlay");
    if (!popover || !overlay) return;

    cartTourStep = 0;
    renderCartTourStep();
}

function nextCartTourStep() {
    const steps = getCartTourSteps();
    if (cartTourStep >= steps.length - 1) {
        completeCartTour();
        return;
    }

    clearCartTourTarget();
    cartTourStep++;
    renderCartTourStep();
}

function completeCartTour() {
    localStorage.setItem(CART_PAGE_TOUR_STORAGE_KEY, "1");
    clearCartTourTarget();
    document.getElementById("cartTourOverlay")?.classList.add("hidden");
    document.getElementById("cartTourPopover")?.classList.add("hidden");
}

function renderCartTourStep() {
    const steps = getCartTourSteps();
    const step = steps[cartTourStep];
    const target = document.querySelector(step.selector);
    const popover = document.getElementById("cartTourPopover");
    const overlay = document.getElementById("cartTourOverlay");
    if (!target || !popover || !overlay) return;

    document.getElementById("cartTourStep").innerText = `${cartTourStep + 1}/${steps.length}`;
    document.getElementById("cartTourTitle").innerText = step.title;
    document.getElementById("cartTourText").innerText = step.text;
    const nextBtn = document.getElementById("cartTourNextBtn");
    if (nextBtn) {
        nextBtn.innerText = cartTourStep === steps.length - 1 ? t("cart_tour_done") : t("cart_tour_next");
    }

    overlay.classList.remove("hidden");
    popover.classList.remove("hidden");
    clearCartTourTarget();
    target.classList.add("cart-tour-target");
    target.closest(".cart-page-top, .cart-page-bottom")?.classList.add("cart-tour-parent");
    target.scrollIntoView({ block: "center", behavior: "smooth" });
    setTimeout(positionCartTour, 220);
}

function positionCartTour() {
    const steps = getCartTourSteps();
    const step = steps[cartTourStep];
    const target = step ? document.querySelector(step.selector) : null;
    const popover = document.getElementById("cartTourPopover");
    if (!target || !popover || popover.classList.contains("hidden")) return;

    const gap = 12;
    const margin = 16;
    const rect = target.getBoundingClientRect();
    const popoverRect = popover.getBoundingClientRect();
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    let left = rect.left + (rect.width - popoverRect.width) / 2;
    let top = rect.bottom + gap;

    if (top + popoverRect.height > viewportHeight - margin) {
        top = rect.top - popoverRect.height - gap;
    }

    if (top < margin) {
        top = margin;
    }

    left = Math.max(margin, Math.min(left, viewportWidth - popoverRect.width - margin));
    popover.style.transform = `translate(${Math.round(left)}px, ${Math.round(top)}px)`;
}

function clearCartTourTarget() {
    document.querySelectorAll(".cart-tour-target").forEach(element => {
        element.classList.remove("cart-tour-target");
    });
    document.querySelectorAll(".cart-tour-parent").forEach(element => {
        element.classList.remove("cart-tour-parent");
    });
}

function getCartTourSteps() {
    return [
        {
            selector: '[data-cart-tour="items"]',
            title: t("cart_tour_items_title"),
            text: t("cart_tour_items_text"),
        },
        {
            selector: '[data-cart-tour="menu"]',
            title: t("cart_tour_menu_title"),
            text: t("cart_tour_menu_text"),
        },
        {
            selector: '[data-cart-tour="split"]',
            title: t("cart_tour_split_title"),
            text: t("cart_tour_split_text"),
        },
        {
            selector: '[data-cart-tour="clear"]',
            title: t("cart_tour_clear_title"),
            text: t("cart_tour_clear_text"),
        },
        {
            selector: '[data-cart-tour="checkout"]',
            title: t("cart_tour_checkout_title"),
            text: t("cart_tour_checkout_text"),
        },
    ];
}
