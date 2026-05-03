import { renderCategories, renderMenu } from './render.js';
import { getById } from './dom.js';
import { logError } from './logger.js';
import { getRestaurantSlug } from './page-context.js';
import { state, setMenuData } from './state.js';
import { showToast } from './toast.js';
import { t } from './i18n.js';

const MENU_REQUEST_TIMEOUT_MS = 8000;

export function fetchMenuData() {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), MENU_REQUEST_TIMEOUT_MS);
    const slug = getRestaurantSlug();
    const menuCacheKey = slug ? `qr_menu_cache:${slug}` : "qr_menu_cache:default";
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
            saveMenuCache(menuCacheKey, data);
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
            const slug = getRestaurantSlug();
            const menuCacheKey = slug ? `qr_menu_cache:${slug}` : "qr_menu_cache:default";
            logError("menu:load", error, { slug });
            const cached = loadMenuCache(menuCacheKey);
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

function saveMenuCache(key, data) {
    try {
        sessionStorage.setItem(key, JSON.stringify(data));
    } catch (error) {
        logError("menu:cache-save", error);
    }
}

function loadMenuCache(key) {
    try {
        const raw = sessionStorage.getItem(key);
        return raw ? JSON.parse(raw) : null;
    } catch (error) {
        logError("menu:cache-load", error);
        return null;
    }
}
