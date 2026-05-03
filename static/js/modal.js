import { escapeHtml, renderCartButton } from './render.js';
import { getById } from './dom.js';
import { getMenuImageSrc, renderMenuImageMarkup } from './menu-ui.js';
import { lockPageScroll, unlockPageScroll } from './scroll-lock.js';
import { state } from './state.js';

function parseIngredients(value) {
    return String(value || "")
        .split(",")
        .map((x) => x.trim().replace(/\s+/g, " "))
        .filter(Boolean);
}

function renderIngredientsTags(value) {
    const tags = parseIngredients(value);
    if (!tags.length) return "";

    return `
        <div class="mt-4">
            <div class="text-xs font-semibold text-gray-500 mb-2">Состав</div>
            <div class="flex flex-wrap gap-2">
                ${tags
                    .map(
                        (tag) =>
                            `<span class="inline-flex items-center rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700">${escapeHtml(tag)}</span>`,
                    )
                    .join("")}
            </div>
        </div>
    `;
}

export function openItemModal(id) {
    const item = state.menuById.get(String(id));
    if (!item || !item.is_available) return;

    getById("itemModalContent").innerHTML = renderItemModalContent(item);
    getById("modalSheet").style.maxHeight = "80vh";

    const modal = getById("itemModal");
    modal.classList.remove("hidden");
    lockPageScroll("item-modal");
    requestAnimationFrame(() => modal.classList.add("is-open"));
}

export function closeItemModal() {
    const modal = getById("itemModal");
    modal.classList.add("hidden");
    modal.classList.remove("is-open");
    unlockPageScroll("item-modal");
}

export function bgClose(e) {
    if (e.target.id === "itemModal") {
        closeItemModal();
    }
}

function renderItemModalContent(item) {
    const imageSrc = getMenuImageSrc(item);
    const description = String(item.description || "").trim();

    return `
        <div class="relative bg-gray-50 rounded-xl overflow-hidden mb-3">
            ${renderMenuImageMarkup({
                src: imageSrc,
                alt: item.name,
                placeholderClass: "w-full h-56 object-contain p-10",
                spinnerClass: "image-spinner",
                imageClass: "menu-image absolute inset-0 w-full h-56 object-cover rounded-xl opacity-0",
                dataAttributeName: "data-modal-image-src",
            })}
            <div data-cart-control-id="${escapeHtml(item.id)}" class="absolute bottom-3 right-3">
                ${renderCartButton(item.id)}
            </div>
        </div>
        <h2 id="itemModalTitle" class="text-xl font-bold mb-1">${escapeHtml(item.name)}</h2>
        <p class="text-gray-500 mb-3">${escapeHtml(item.amount)}</p>
        <div class="text-lg font-bold mb-2">${escapeHtml(item.price)} c</div>
        ${description ? `<div class="text-sm text-gray-700 whitespace-pre-line">${escapeHtml(description)}</div>` : ""}
        ${renderIngredientsTags(item.ingredients)}
    `;
}
