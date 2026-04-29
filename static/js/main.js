import { loadMenuData } from './api.js';
import { addItem, removeItem, updateCart } from './cart.js';
import { initImageLoading } from './image.js';
import { openItemModal, closeItemModal, bgClose } from './modal.js';
import { filterCat, hideSearchDropdown, searchItems } from './search.js';
import { loadCartFromStorage } from './state.js';
import { applyTranslations, bindLangSwitcher, initI18n } from './i18n.js';
import { renderCategories, renderCategoriesSkeleton, renderMenu, renderMenuSkeleton } from './render.js';
import { state } from './state.js';
import { lockPageScroll, unlockPageScroll } from './scroll-lock.js';

document.addEventListener('DOMContentLoaded', () => {
    initI18n("ru");
    applyTranslations();
    bindLangSwitcher();
    initImageLoading();
    loadCartFromStorage();

    renderCategoriesSkeleton();
    renderMenuSkeleton();

    window.addEventListener("qrMenuLangChanged", () => {
        applyTranslations();
        renderCategories();
        if (state.activeCat === "all") {
            document.getElementById("catTitle") && (document.getElementById("catTitle").innerText = document.querySelector("[data-i18n='all_dishes']")?.innerText || document.getElementById("catTitle").innerText);
            renderMenu(state.menuData, { groupByCategory: true });
        }
    });

    loadMenuData().then(updateCart);

    document.getElementById("search")?.addEventListener("input", searchItems);
    document.getElementById("itemModal")?.addEventListener('click', bgClose);
    document.getElementById("restaurantInfoModal")?.addEventListener('click', bgCloseRestaurantInfo);

    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            closeRestaurantInfo();
        }
    });

    document.addEventListener('click', handleDocumentClick);
});

function handleDocumentClick(e) {
    if (!e.target.closest("#search") && !e.target.closest("#searchDropdown")) {
        hideSearchDropdown();
    }

    const action = e.target.closest('[data-action]');
    if (!action) return;

    if (action.tagName !== 'A') {
        e.preventDefault();
    }

    const { action: actionType, param } = action.dataset;

    switch (actionType) {
        case 'filterCat':
            filterCat(param === "all" ? "all" : Number(param));
            break;
        case 'addItem':
            addItem(param);
            break;
        case 'removeItem':
            removeItem(param);
            break;
        case 'openItemModal':
            hideSearchDropdown();
            openItemModal(param);
            break;
        case 'closeItemModal':
            closeItemModal();
            break;
        case 'bgClose':
            bgClose(e);
            break;
        case 'openRestaurantInfo':
            openRestaurantInfo();
            break;
        case 'closeRestaurantInfo':
            closeRestaurantInfo();
            break;
    }
}

function openRestaurantInfo() {
    const modal = document.getElementById("restaurantInfoModal");
    if (!modal) return;
    modal.classList.remove("hidden");
    modal.classList.add("flex");
    lockPageScroll("restaurant-info");
}

function closeRestaurantInfo() {
    const modal = document.getElementById("restaurantInfoModal");
    if (!modal) return;
    modal.classList.add("hidden");
    modal.classList.remove("flex");
    unlockPageScroll("restaurant-info");
}

function bgCloseRestaurantInfo(e) {
    if (e.target && e.target.id === "restaurantInfoModal") {
        closeRestaurantInfo();
    }
}
