import { escapeHtml, renderCategories, renderMenu } from './render.js';
import { getById } from './dom.js';
import { logError } from './logger.js';
import { syncMenuImageElement } from './image.js';
import { getMenuImageSrc, renderMenuImageMarkup } from './menu-ui.js';
import { state } from './state.js';
import { t } from './i18n.js';

const SEARCH_DROPDOWN_LIMIT = 6;
const SEARCH_INPUT_DEBOUNCE_MS = 120;
let searchTimer = null;

export function filterCat(cat) {
    state.activeCat = cat;
    renderCategories();
    hideSearchDropdown();

    const title = getById("catTitle");
    if (cat === "all") {
        title.innerText = t("all_dishes");
        renderMenu(state.menuData, { groupByCategory: true });
        return;
    }

    const category = state.categoriesById.get(String(cat));
    if (!category) {
        state.activeCat = "all";
        title.innerText = t("all_dishes");
        renderCategories();
        renderMenu(state.menuData, { groupByCategory: true });
        return;
    }

    title.innerText = category.name;
    renderMenu(state.menuByCategory.get(String(cat)) || []);
}

export function searchItems(e) {
    const text = String(e.target.value || "").toLowerCase().trim();
    clearTimeout(searchTimer);
    searchTimer = window.setTimeout(() => applySearch(text), SEARCH_INPUT_DEBOUNCE_MS);
}

export function hideSearchDropdown() {
    getById("searchDropdown")?.classList.add("hidden");
}

function restoreActiveCategory(title) {
    hideSearchDropdown();

    if (state.activeCat === "all") {
        title.innerText = t("all_dishes");
        renderMenu(state.menuData, { groupByCategory: true });
        return;
    }

    const category = state.categoriesById.get(String(state.activeCat));
    if (!category) {
        state.activeCat = "all";
        title.innerText = t("all_dishes");
        renderCategories();
        renderMenu(state.menuData, { groupByCategory: true });
        return;
    }

    title.innerText = category.name;
    renderMenu(state.menuByCategory.get(String(state.activeCat)) || []);
}

function renderSearchDropdown(items) {
    const dropdown = getById("searchDropdown");
    if (!dropdown) return;

    const visibleItems = items.slice(0, SEARCH_DROPDOWN_LIMIT);
    toggleSearchEmptyState(dropdown, visibleItems.length === 0);
    syncSearchDropdownItems(dropdown, visibleItems);
    dropdown.classList.remove("hidden");
}

function syncSearchDropdownItems(dropdown, items) {
    const visibleIds = new Set(items.map(item => String(item.id)));
    const buttons = new Map();

    dropdown.querySelectorAll("[data-search-item-id]").forEach(button => {
        const isVisible = visibleIds.has(button.dataset.searchItemId);
        button.classList.toggle("hidden", !isVisible);
        if (isVisible) {
            buttons.set(button.dataset.searchItemId, button);
        }
    });

    const fragment = document.createDocumentFragment();
    items.forEach(item => {
        let button = buttons.get(String(item.id));

        if (!button) {
            button = createSearchDropdownItem(item);
        } else {
            updateSearchDropdownAvailability(button, item);
            button.querySelector("[data-search-item-name]").innerText = item.name;
            updateSearchDropdownImage(button, item);
        }

        fragment.appendChild(button);
    });

    dropdown.appendChild(fragment);
}

function createSearchDropdownItem(item) {
    const template = document.createElement("template");
    const imageSrc = getSearchImageSrc(item);
    const itemId = escapeHtml(item.id);
    const isAvailable = Boolean(item.is_available);

    template.innerHTML = `
        <button
            type="button"
            data-search-item-id="${itemId}"
            ${isAvailable ? `data-action="openItemModal" data-param="${itemId}"` : 'disabled aria-disabled="true"'}
            class="w-full flex items-center gap-3 px-3 py-2 text-left ${isAvailable ? "hover:bg-gray-50" : "cursor-not-allowed opacity-60"}"
            role="option">
            <div class="relative w-12 h-12 shrink-0 bg-gray-50 rounded-lg overflow-hidden">
                ${renderMenuImageMarkup({
                    src: imageSrc,
                    alt: item.name,
                    placeholderClass: "w-12 h-12 object-contain p-2",
                    spinnerClass: "image-spinner image-spinner-sm",
                    imageClass: "menu-image absolute inset-0 w-12 h-12 object-cover rounded-lg opacity-0",
                    dataAttributeName: "data-search-image-src",
                })}
            </div>
            <span class="min-w-0 flex-1">
                <span data-search-item-name class="block truncate font-medium text-gray-900">${escapeHtml(item.name)}</span>
                <span data-search-item-unavailable class="${isAvailable ? "hidden" : ""} text-xs font-medium text-amber-700">${escapeHtml(t("item_unavailable_soon"))}</span>
            </span>
        </button>
    `.trim();

    return template.content.firstElementChild;
}

function updateSearchDropdownAvailability(button, item) {
    const isAvailable = Boolean(item.is_available);

    button.disabled = !isAvailable;
    button.toggleAttribute("aria-disabled", !isAvailable);
    button.classList.toggle("cursor-not-allowed", !isAvailable);
    button.classList.toggle("opacity-60", !isAvailable);
    button.classList.toggle("hover:bg-gray-50", isAvailable);
    const unavailable = button.querySelector("[data-search-item-unavailable]");
    if (unavailable) {
        unavailable.classList.toggle("hidden", isAvailable);
        unavailable.innerText = t("item_unavailable_soon");
    }

    if (isAvailable) {
        button.dataset.action = "openItemModal";
        button.dataset.param = item.id;
    } else {
        delete button.dataset.action;
        delete button.dataset.param;
    }
}

function updateSearchDropdownImage(button, item) {
    const image = button.querySelector("[data-search-image-src]");
    if (!image) return;

    const imageSrc = getSearchImageSrc(item);
    syncMenuImageElement(image, imageSrc, item.name ?? "", "image-spinner image-spinner-sm");
}

function getSearchImageSrc(item) {
    return getMenuImageSrc(item);
}

function toggleSearchEmptyState(dropdown, isVisible) {
    let emptyState = getById("searchEmptyState");

    if (!emptyState) {
        emptyState = document.createElement("p");
        emptyState.id = "searchEmptyState";
        emptyState.className = "px-3 py-4 text-sm text-gray-500 text-center hidden";
        emptyState.innerText = t("search_nothing_found");
        dropdown.prepend(emptyState);
    }

    if (emptyState) {
        emptyState.innerText = t("search_nothing_found");
    }

    emptyState.classList.toggle("hidden", !isVisible);
}

function applySearch(text) {
    const title = getById("catTitle");
    if (!title) return;

    try {
        if (!text) {
            restoreActiveCategory(title);
            return;
        }

        const filtered = state.menuData.filter(item => String(item.name).toLowerCase().includes(text));
        title.innerText = t("search_result_title");
        renderMenu(filtered);
        renderSearchDropdown(filtered);
    } catch (error) {
        logError("menu:search", error, { text });
        restoreActiveCategory(title);
    }
}
