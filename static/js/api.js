import { renderCategories, renderMenu } from './render.js';
import { getById } from './dom.js';
import { logError } from './logger.js';
import { state } from './state.js';
import { setMenuData } from './state.js';
import { showToast } from './toast.js';
import { t } from './i18n.js';

const MENU_REQUEST_TIMEOUT_MS = 8000;
const MENU_CACHE_KEY = window.RESTAURANT_SLUG ? `qr_menu_cache:${window.RESTAURANT_SLUG}` : "qr_menu_cache:default";

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
            state.restaurant = data.restaurant || null;
            setMenuData(data.menu || [], data.categories || []);
            saveMenuCache(data);
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
            logError("menu:load", error, { slug: window.RESTAURANT_SLUG || null });
            const cached = loadMenuCache();
            if (cached) {
                state.restaurant = cached.restaurant || null;
                setMenuData(cached.menu || [], cached.categories || []);
                renderCategories();
                renderMenu(state.menuData, { groupByCategory: true });
                showToast(t("no_server_response"));
                return cached;
            }
            showToast(t("no_server_response"));
            renderMenuError();
        });
}

function renderMenuError() {
    const title = getById("catTitle");
    const menu = getById("menu");

    if (title) title.innerText = t("menu_load_error_title");
    if (!menu) return;

    menu.innerHTML = `
        <p class="col-span-full text-center text-red-500 py-10 text-lg">
            ${t("menu_load_error_text")}
        </p>
    `;
}

function saveMenuCache(data) {
    try {
        sessionStorage.setItem(MENU_CACHE_KEY, JSON.stringify(data));
    } catch (error) {
        logError("menu:cache-save", error);
    }
}

function loadMenuCache() {
    try {
        const raw = sessionStorage.getItem(MENU_CACHE_KEY);
        return raw ? JSON.parse(raw) : null;
    } catch (error) {
        logError("menu:cache-load", error);
        return null;
    }
}
