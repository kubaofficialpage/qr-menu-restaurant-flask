import { renderCategories, renderMenu } from './render.js';
import { state } from './state.js';
import { showToast } from './toast.js';
import { t } from './i18n.js';

const MENU_REQUEST_TIMEOUT_MS = 8000;

export function fetchMenuData() {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), MENU_REQUEST_TIMEOUT_MS);
    const slug = window.RESTAURANT_SLUG;
    const endpoint = slug ? `/api/${encodeURIComponent(slug)}/menu` : "/api/menu";

    return fetch(endpoint, { signal: controller.signal })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Menu API failed with status ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            state.menuData.length = 0;
            state.menuData.push(...(data.menu || []));
            state.categories.length = 0;
            state.categories.push(...(data.categories || []));
            return data;
        })
        .finally(() => clearTimeout(timeoutId));
}

export function loadMenuData() {
    return fetchMenuData()
        .then(data => {
            renderCategories();
            renderMenu(state.menuData, { groupByCategory: true });
            return data;
        })
        .catch(error => {
            console.error('Error loading menu data:', error);
            showToast(t("no_server_response"));
            renderMenuError();
        });
}

function renderMenuError() {
    const title = document.getElementById("catTitle");
    const menu = document.getElementById("menu");

    if (title) title.innerText = t("menu_load_error_title");
    if (!menu) return;

    menu.innerHTML = `
        <p class="col-span-full text-center text-red-500 py-10 text-lg">
            ${t("menu_load_error_text")}
        </p>
    `;
}
