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
        <div class="relative overflow-hidden rounded-t-[28px] bg-gray-50">
            ${renderMenuImageMarkup({
                src: imageSrc,
                alt: item.name,
                placeholderClass: "h-64 w-full object-contain p-10",
                spinnerClass: "image-spinner",
                imageClass: "menu-image absolute inset-0 h-64 w-full object-cover opacity-0",
                dataAttributeName: "data-modal-image-src",
            })}
            <button
                type="button"
                data-action="closeItemModal"
                class="absolute right-3 top-3 z-10 flex h-10 w-10 items-center justify-center rounded-full bg-white/92 text-slate-900 shadow-sm backdrop-blur hover:bg-white"
                aria-label="Закрыть">
                <i class="fa-solid fa-xmark" aria-hidden="true"></i>
            </button>
            <div data-cart-control-id="${escapeHtml(item.id)}" class="absolute bottom-3 right-3">
                ${renderCartButton(item.id)}
            </div>
        </div>
        <div class="px-4 pb-5 pt-4">
            <h2 id="itemModalTitle" class="mb-1 text-xl font-bold text-slate-900">${escapeHtml(item.name)}</h2>
            <p class="mb-3 text-gray-500">${escapeHtml(item.amount)}</p>
            <div class="mb-2 text-lg font-bold text-slate-900">${escapeHtml(item.price)} c</div>
            ${description ? `<div class="text-sm text-gray-700 whitespace-pre-line">${escapeHtml(description)}</div>` : ""}
            ${renderIngredientsTags(item.ingredients)}
        </div>
    `;
}
