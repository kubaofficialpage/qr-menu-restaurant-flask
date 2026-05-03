import {
    IMAGE_PLACEHOLDER,
    escapeHtml,
    formatShortText,
    getMenuImageSrc,
    isMenuItemAvailable,
    renderMenuImageMarkup,
    renderQuantityControl,
    renderUnavailableOverlay,
    setText,
} from './menu-ui.js';
import { syncMenuImageElement } from './image.js';
import { state } from './state.js';
import { t } from './i18n.js';
import { getById } from './dom.js';
import { logError } from './logger.js';

export { IMAGE_PLACEHOLDER, escapeHtml, isMenuItemAvailable };

const MENU_ITEM_STAGGER_MS = 45;
const MENU_ITEM_MAX_DELAY_MS = 450;
const MENU_CHUNK_SIZE = 24;
const MENU_LAZY_RENDER_THRESHOLD = 60;

export function renderCategories() {
    const categories = [
        renderCategoryButton({ id: "all", name: t("category_all"), isActive: state.activeCat === "all" }),
        ...state.categories.map(category => renderCategoryButton({
            id: category.id,
            name: category.name,
            isActive: String(state.activeCat) === String(category.id),
        })),
    ];

    const container = getById("categories");
    if (container) {
        container.innerHTML = categories.join("");
    }
}

export function renderCategoriesSkeleton(count = 6) {
    const container = getById("categories");
    if (!container) return;
    if (container.dataset.skeleton === "true") return;

    const pills = Array.from({ length: count }).map(() => {
        const w = 64 + Math.floor(Math.random() * 48);
        return `
            <div
                data-menu-skeleton
                class="h-10 rounded-[24px] bg-white border overflow-hidden relative"
                style="width:${w}px">
                <div class="h-full w-full bg-gray-200 animate-pulse"></div>
            </div>
        `.trim();
    });

    container.dataset.skeleton = "true";
    container.innerHTML = pills.join("");
}

export function renderMenu(data = [], options = {}) {
    const menu = getById("menu");
    if (!menu) return;

    if (menu.dataset.skeleton === "true") {
        menu.innerHTML = "";
        delete menu.dataset.skeleton;
    }

    const items = Array.isArray(data) ? data : [];
    const groupByCategory = Boolean(options.groupByCategory);
    const visibleIds = new Set(items.map(item => String(item.id)));
    const availableIds = new Set(state.menuData.map(item => String(item.id)));
    const cards = new Map();

    menu.querySelectorAll("[data-menu-category-title]").forEach(title => title.remove());

    menu.querySelectorAll("[data-menu-item-id]").forEach(card => {
        if (!availableIds.has(card.dataset.menuItemId)) {
            card.remove();
            return;
        }

        card.classList.toggle("hidden", !visibleIds.has(card.dataset.menuItemId));
        cards.set(card.dataset.menuItemId, card);
    });

    toggleMenuEmptyState(menu, items.length === 0);
    if (items.length === 0) return;

    const groups = getMenuRenderGroups(items, groupByCategory);
    const renderToken = ++state.renderToken;

    if (items.length >= MENU_LAZY_RENDER_THRESHOLD) {
        renderMenuInChunks(menu, groups, cards, renderToken, groupByCategory);
        return;
    }

    const result = buildMenuFragment(groups, cards, groupByCategory);
    menu.appendChild(result.fragment);
}

export function renderMenuSkeleton(count = 12) {
    const menu = getById("menu");
    if (!menu) return;
    if (menu.dataset.skeleton === "true") return;

    const cards = Array.from({ length: count }).map(() => {
        const nameW = 72 + Math.floor(Math.random() * 72);
        const amountW = 52 + Math.floor(Math.random() * 90);
        return `
            <article data-menu-skeleton class="bg-white p-0">
                <div class="bg-slate-50 rounded-[18px] overflow-hidden">
                    <div class="w-full h-40 bg-gray-200 animate-pulse"></div>
                </div>
                <div class="px-1 pt-2 space-y-2">
                    <div class="h-5 w-16 bg-gray-200 rounded animate-pulse"></div>
                    <div class="h-4 bg-gray-200 rounded animate-pulse" style="width:${nameW}px"></div>
                    <div class="h-3 bg-gray-200 rounded animate-pulse" style="width:${amountW}px"></div>
                </div>
            </article>
        `.trim();
    });

    menu.dataset.skeleton = "true";
    menu.innerHTML = cards.join("");
}

function getMenuCard(item, cards, animationIndex) {
    const itemId = String(item.id);
    let card = cards.get(itemId);

    if (!card) {
        card = createMenuItem(item, animationIndex);
    } else {
        updateMenuItem(card, item);
        card.classList.remove("hidden");
        queueMenuItemEntry(card, animationIndex);
    }

    return card;
}

function getMenuRenderGroups(items, groupByCategory) {
    if (!groupByCategory) {
        return [{ name: "", items }];
    }

    const itemsByCategory = new Map();
    items.forEach(item => {
        const categoryId = String(item.category_id ?? "");
        const categoryItems = itemsByCategory.get(categoryId) || [];
        categoryItems.push(item);
        itemsByCategory.set(categoryId, categoryItems);
    });

    const groups = state.categories
        .map(category => ({
            name: category.name,
            items: itemsByCategory.get(String(category.id)) || [],
        }))
        .filter(group => group.items.length > 0);

    const uncategorizedItems = items.filter(item => !state.categories.some(category => String(category.id) === String(item.category_id)));
    if (uncategorizedItems.length > 0) {
        groups.push({ name: t("category_other"), items: uncategorizedItems });
    }

    return groups;
}

function createCategoryTitle(name) {
    const title = document.createElement("h2");
    title.dataset.menuCategoryTitle = "";
    title.className = "col-span-full mt-2 text-xl font-bold text-gray-900 first:mt-0";
    title.innerText = name;
    return title;
}

export function renderCartButton(id) {
    if (!isMenuItemAvailable(id)) {
        return "";
    }

    return renderQuantityControl(id, state.cartQty[id] || 0);
}

function renderCategoryButton({ id, name, isActive }) {
    return `
        <button type="button" data-action="filterCat" data-param="${escapeHtml(id)}" class="px-4 py-2 rounded-[24px] whitespace-nowrap ${isActive ? "bg-black text-white" : "bg-white border"}">
            ${escapeHtml(name)}
        </button>
    `;
}

function createMenuItem(item, index = 0) {
    const template = document.createElement("template");
    template.innerHTML = renderMenuItemHtml(item, index).trim();
    return template.content.firstElementChild;
}

function renderMenuItemHtml(item, index = 0) {
    const imageSrc = getMenuImageSrc(item);
    const itemId = escapeHtml(item.id);
    const isAvailable = Boolean(item.is_available);
    const delay = getMenuItemDelay(index);

    return `
        <article class="menu-item is-entering bg-white p-0 ${isAvailable ? "cursor-pointer" : "opacity-70 cursor-not-allowed"}" style="--menu-item-delay:${delay}ms" data-menu-item-id="${itemId}" ${isAvailable ? `data-action="openItemModal" data-param="${itemId}"` : 'aria-disabled="true"'}>
            <div class="img-box relative overflow-hidden rounded-[20px] bg-slate-50">
                ${renderMenuImageMarkup({
                    src: imageSrc,
                    alt: item.name,
                    placeholderClass: "image-placeholder w-full h-40 object-contain p-8",
                    spinnerClass: "image-spinner",
                    imageClass: "menu-image absolute inset-0 h-40 w-full object-cover opacity-0",
                    dataAttributeName: "data-menu-image-src",
                })}
                ${isAvailable ? "" : renderUnavailableOverlay()}
                <div data-cart-control-id="${itemId}" class="absolute bottom-2 right-2">
                    ${renderCartButton(item.id)}
                </div>
            </div>
            <div class="px-1 pt-2 pb-1">
                <h2 data-menu-price class="text-lg font-bold leading-none text-slate-900">${escapeHtml(item.price)} c</h2>
                <h3 data-menu-name class="mt-1 text-md text-slate-900">${escapeHtml(formatShortText(item.name, 15, ".."))}</h3>
                <p data-menu-amount class="text-gray-500 text-sm">${escapeHtml(item.amount)}</p>
            </div>
        </article>
    `;
}

function queueMenuItemEntry(card, index) {
    card.style.setProperty("--menu-item-delay", `${getMenuItemDelay(index)}ms`);
    card.classList.remove("is-entering");
    void card.offsetWidth;
    card.classList.add("is-entering");
}

function getMenuItemDelay(index) {
    return Math.min(index * MENU_ITEM_STAGGER_MS, MENU_ITEM_MAX_DELAY_MS);
}

function updateMenuItem(card, item) {
    const isAvailable = Boolean(item.is_available);

    card.classList.toggle("opacity-70", !isAvailable);
    card.classList.toggle("cursor-not-allowed", !isAvailable);
    card.classList.toggle("cursor-pointer", isAvailable);
    card.toggleAttribute("aria-disabled", !isAvailable);

    if (isAvailable) {
        card.dataset.action = "openItemModal";
        card.dataset.param = item.id;
    } else {
        delete card.dataset.action;
        delete card.dataset.param;
    }

    setText(card.querySelector("[data-menu-price]"), `${item.price} c`);
    setText(card.querySelector("[data-menu-name]"), formatShortText(item.name, 15, ".."));
    setText(card.querySelector("[data-menu-amount]"), item.amount);
    updateAvailabilityOverlay(card, isAvailable);
    updateMenuImage(card, item);
}

function updateAvailabilityOverlay(card, isAvailable) {
    const imageBox = card.querySelector(".img-box");
    if (!imageBox) return;

    const existing = imageBox.querySelector("[data-availability-overlay]");
    if (isAvailable) {
        existing?.remove();
        return;
    }

    if (existing) return;

    const template = document.createElement("template");
    template.innerHTML = renderUnavailableOverlay().trim();
    const overlay = template.content.firstElementChild;
    imageBox.insertBefore(overlay, imageBox.querySelector("[data-cart-control-id]"));
}

function updateMenuImage(card, item) {
    const image = card.querySelector("[data-menu-image-src]");
    if (!image) return;

    const imageSrc = getMenuImageSrc(item);
    syncMenuImageElement(image, imageSrc, item.name ?? "", "image-spinner");
}

function toggleMenuEmptyState(menu, isVisible) {
    let emptyState = document.getElementById("menuEmptyState");

    if (!emptyState) {
        emptyState = document.createElement("p");
        emptyState.id = "menuEmptyState";
        emptyState.className = "col-span-full text-center text-gray-500 py-10 text-lg hidden";
        emptyState.innerText = "Ничего не найдено";
        menu.prepend(emptyState);
    }

    emptyState.classList.toggle("hidden", !isVisible);
}

function buildMenuFragment(groups, cards, groupByCategory, startIndex = 0, maxItems = Number.POSITIVE_INFINITY) {
    const fragment = document.createDocumentFragment();
    let animationIndex = startIndex;
    let renderedItems = 0;

    for (const group of groups) {
        let titleRendered = false;

        for (const item of group.items) {
            if (renderedItems >= maxItems) {
                return { fragment, renderedItems, animationIndex };
            }

            if (groupByCategory && !titleRendered) {
                fragment.appendChild(createCategoryTitle(group.name));
                titleRendered = true;
            }

            const card = getMenuCard(item, cards, animationIndex);
            fragment.appendChild(card);
            animationIndex++;
            renderedItems++;
        }
    }

    return { fragment, renderedItems, animationIndex };
}

function renderMenuInChunks(menu, groups, cards, renderToken, groupByCategory) {
    let animationIndex = 0;
    let groupIndex = 0;
    let itemIndexInGroup = 0;

    const step = () => {
        if (renderToken !== state.renderToken) return;

        const fragment = document.createDocumentFragment();
        let rendered = 0;

        while (groupIndex < groups.length && rendered < MENU_CHUNK_SIZE) {
            const group = groups[groupIndex];

            if (groupByCategory && itemIndexInGroup === 0) {
                fragment.appendChild(createCategoryTitle(group.name));
            }

            while (itemIndexInGroup < group.items.length && rendered < MENU_CHUNK_SIZE) {
                const item = group.items[itemIndexInGroup];
                const card = getMenuCard(item, cards, animationIndex);
                fragment.appendChild(card);
                itemIndexInGroup++;
                animationIndex++;
                rendered++;
            }

            if (itemIndexInGroup >= group.items.length) {
                groupIndex++;
                itemIndexInGroup = 0;
            }
        }

        menu.appendChild(fragment);

        if (groupIndex < groups.length) {
            requestAnimationFrame(step);
        }
    };

    try {
        requestAnimationFrame(step);
    } catch (error) {
        logError("menu:chunk-render", error, { groups: groups.length });
        const result = buildMenuFragment(groups, cards, groupByCategory);
        menu.appendChild(result.fragment);
    }
}
