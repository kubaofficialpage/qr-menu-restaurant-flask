import { escapeHtml, renderCartButton } from './render.js';
import { getMenuImageSrc, renderMenuImageMarkup } from './menu-ui.js';
import { lockPageScroll, unlockPageScroll } from './scroll-lock.js';
import { state } from './state.js';

export function openItemModal(id) {
    const item = state.menuData.find(menuItem => String(menuItem.id) === String(id));
    if (!item || !item.is_available) return;

    document.getElementById("itemModalContent").innerHTML = renderItemModalContent(item);
    document.getElementById("modalSheet").style.maxHeight = "80vh";

    const modal = document.getElementById("itemModal");
    modal.classList.remove("hidden");
    lockPageScroll("item-modal");
    requestAnimationFrame(() => modal.classList.add("is-open"));
}

export function closeItemModal() {
    const modal = document.getElementById("itemModal");
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
    `;
}
