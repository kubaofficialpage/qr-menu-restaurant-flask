const STORAGE_KEY = "qr_menu_lang";

function flagSvg(lang) {
    const safe = String(lang || "").toLowerCase();
    if (!LANG_META[safe]) return "";
    return `
        <img
            src="/static/flags/${safe}.svg"
            alt=""
            class="w-6 h-4 rounded-sm"
            loading="lazy"
            decoding="async"
        />
    `.trim();
}

const LANG_META = {
    ru: { name: "RU" },
    en: { name: "EN" },
    ky: { name: "KG" },
};

const DICT = {
    ru: {
        lang_label: "RU",
        category_all: "Все",
        category_other: "Другое",
        search_placeholder: "Поиск блюд...",
        search_aria: "Поиск блюд",
        search_result_title: "Результат",
        search_nothing_found: "Ничего не найдено",
        item_unavailable_soon: "Будет позже",
        cart_open_aria: "Открыть корзину",
        all_dishes: "Все блюда",
        cart_title: "Корзина",
        cart_empty: "Корзина пуста",
        similar: "Похожее",
        total: "Итого",
        checkout: "Оформить заказ",
        menu_unavailable: "Меню пока недоступно",
        no_server_response: "Нет ответа от сервера. Попробуйте обновить страницу.",
        menu_load_error_title: "Ошибка загрузки",
        menu_load_error_text: "Не удалось загрузить меню. Обновите страницу или попробуйте позже.",
        checkout_not_connected: "Оформление заказа пока не подключено.",
        confirm_title: "Подтверждение",
        clear_cart_confirm_text: "Вы уверены, что хотите очистить корзину?",
        yes: "Да",
        cancel: "Отмена",
        split_bill_title: "Разделить счет",
        split_bill_total: "Общая сумма",
        guests_count_placeholder: "Количество гостей",
        calculate: "Рассчитать",
        per_person: "На человека",
        close: "Закрыть",
        restaurant_info_btn_aria: "Информация о ресторане",
        restaurant_info_title: "Информация о ресторане",
        restaurant_info_contacts: "Контакты",
        restaurant_info_about: "О ресторане",
        restaurant_info_map: "Открыть на карте",
        specify_guests: "Укажите количество гостей",
        cart_tour_skip: "Пропустить",
        cart_tour_next: "Далее",
        cart_tour_done: "Готово",
        cart_tour_items_title: "Список блюд",
        cart_tour_items_text: "Здесь видны добавленные позиции, количество и сумма по каждому блюду.",
        cart_tour_menu_title: "Добавить еще",
        cart_tour_menu_text: "В блоке похожих блюд можно быстро добавить или убрать позиции кнопками плюс и минус.",
        cart_tour_split_title: "Разделить счет",
        cart_tour_split_text: "Эта кнопка считает сумму на каждого гостя.",
        cart_tour_clear_title: "Очистить корзину",
        cart_tour_clear_text: "Удаляет все блюда после подтверждения.",
        cart_tour_checkout_title: "Оформить заказ",
        cart_tour_checkout_text: "Финальная кнопка всегда закреплена снизу, чтобы быстро перейти к заказу.",
    },
    en: {
        lang_label: "EN",
        category_all: "All",
        category_other: "Other",
        search_placeholder: "Search dishes...",
        search_aria: "Search dishes",
        search_result_title: "Results",
        search_nothing_found: "Nothing found",
        item_unavailable_soon: "Coming soon",
        cart_open_aria: "Open cart",
        all_dishes: "All dishes",
        cart_title: "Cart",
        cart_empty: "Cart is empty",
        similar: "Similar",
        total: "Total",
        checkout: "Checkout",
        menu_unavailable: "Menu is not available yet",
        no_server_response: "No response from server. Please refresh the page.",
        menu_load_error_title: "Load error",
        menu_load_error_text: "Could not load the menu. Refresh the page or try again later.",
        checkout_not_connected: "Checkout is not connected yet.",
        confirm_title: "Confirmation",
        clear_cart_confirm_text: "Are you sure you want to clear the cart?",
        yes: "Yes",
        cancel: "Cancel",
        split_bill_title: "Split bill",
        split_bill_total: "Total",
        guests_count_placeholder: "Number of guests",
        calculate: "Calculate",
        per_person: "Per person",
        close: "Close",
        restaurant_info_btn_aria: "Restaurant information",
        restaurant_info_title: "Restaurant information",
        restaurant_info_contacts: "Contacts",
        restaurant_info_about: "About",
        restaurant_info_map: "Open on map",
        specify_guests: "Enter number of guests",
        cart_tour_skip: "Skip",
        cart_tour_next: "Next",
        cart_tour_done: "Done",
        cart_tour_items_title: "Items",
        cart_tour_items_text: "Here you can see added items, quantity, and subtotal for each dish.",
        cart_tour_menu_title: "Add more",
        cart_tour_menu_text: "In the suggestions block you can quickly add or remove items using plus/minus.",
        cart_tour_split_title: "Split bill",
        cart_tour_split_text: "This button calculates the amount per guest.",
        cart_tour_clear_title: "Clear cart",
        cart_tour_clear_text: "Removes all items after confirmation.",
        cart_tour_checkout_title: "Checkout",
        cart_tour_checkout_text: "The final button is pinned to the bottom for quick access.",
    },
    ky: {
        lang_label: "KY",
        category_all: "Баары",
        category_other: "Башка",
        search_placeholder: "Тамак издөө...",
        search_aria: "Тамак издөө",
        search_result_title: "Натыйжа",
        search_nothing_found: "Эч нерсе табылган жок",
        item_unavailable_soon: "Кийин чыгат",
        cart_open_aria: "Себетти ачуу",
        all_dishes: "Бардык тамактар",
        cart_title: "Себет",
        cart_empty: "Себет бош",
        similar: "Окшош",
        total: "Жалпы",
        checkout: "Заказ берүү",
        menu_unavailable: "Меню азырынча жеткиликсиз",
        no_server_response: "Сервер жооп берген жок. Баракты жаңылаңыз.",
        menu_load_error_title: "Жүктөө катасы",
        menu_load_error_text: "Меню жүктөлгөн жок. Баракты жаңылаңыз же кийинчерээк аракет кылыңыз.",
        checkout_not_connected: "Заказ берүү азырынча туташкан жок.",
        confirm_title: "Ырастоо",
        clear_cart_confirm_text: "Себетти тазалоону каалайсызбы?",
        yes: "Ооба",
        cancel: "Жок",
        split_bill_title: "Эсеп бөлүү",
        split_bill_total: "Жалпы сумма",
        guests_count_placeholder: "Коноктор саны",
        calculate: "Эсептөө",
        per_person: "Ар бирине",
        close: "Жабуу",
        restaurant_info_btn_aria: "Ресторан тууралуу маалымат",
        restaurant_info_title: "Ресторан тууралуу маалымат",
        restaurant_info_contacts: "Байланыш",
        restaurant_info_about: "Ресторан жөнүндө",
        restaurant_info_map: "Картадан ачуу",
        specify_guests: "Коноктор санын жазыңыз",
        cart_tour_skip: "Өткөрүү",
        cart_tour_next: "Кийинки",
        cart_tour_done: "Даяр",
        cart_tour_items_title: "Тизмек",
        cart_tour_items_text: "Бул жерде кошулган тамактар, саны жана ар биринин суммасы көрүнөт.",
        cart_tour_menu_title: "Дагы кошуу",
        cart_tour_menu_text: "Окшош тамактар бөлүмүнөн плюс/минус аркылуу тез кошуп же азайта аласыз.",
        cart_tour_split_title: "Эсеп бөлүү",
        cart_tour_split_text: "Бул баскыч ар бир конокко туура келген сумманы эсептейт.",
        cart_tour_clear_title: "Себетти тазалоо",
        cart_tour_clear_text: "Ырастоодон кийин бардык тамактарды өчүрөт.",
        cart_tour_checkout_title: "Заказ берүү",
        cart_tour_checkout_text: "Акыркы баскыч ылдыйда бекитилген — заказга тез өтүү үчүн.",
    },
};

let currentLang = "ru";

export function getLang() {
    return currentLang;
}

export function setLang(lang) {
    if (!DICT[lang]) {
        lang = "ru";
    }
    currentLang = lang;
    try {
        localStorage.setItem(STORAGE_KEY, lang);
    } catch {
        // ignore
    }

    document.documentElement.lang = lang;

    window.dispatchEvent(
        new CustomEvent("qrMenuLangChanged", {
            detail: { lang },
        })
    );
}

export function initI18n(defaultLang = "ru") {
    let lang = defaultLang;
    try {
        lang = localStorage.getItem(STORAGE_KEY) || defaultLang;
    } catch {
        lang = defaultLang;
    }
    setLang(lang);
}

export function t(key) {
    return DICT[currentLang]?.[key] ?? DICT.ru?.[key] ?? key;
}

export function applyTranslations(root = document) {
    root.querySelectorAll("[data-i18n]").forEach(el => {
        el.textContent = t(el.dataset.i18n);
    });

    root.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
        el.setAttribute("placeholder", t(el.dataset.i18nPlaceholder));
    });

    root.querySelectorAll("[data-i18n-aria-label]").forEach(el => {
        el.setAttribute("aria-label", t(el.dataset.i18nAriaLabel));
    });
}

export function bindLangSwitcher() {
    const btn = document.getElementById("langSwitcherBtn");
    const menu = document.getElementById("langSwitcherMenu");
    if (!btn || !menu) return;

    const setButtonText = () => {
        const meta = LANG_META[currentLang] || LANG_META.ru;
        btn.innerHTML = flagSvg(currentLang);
        btn.setAttribute("aria-label", meta.name);
    };

    setButtonText();

    const closeMenu = () => {
        menu.classList.add("hidden");
        btn.setAttribute("aria-expanded", "false");
    };

    btn.addEventListener("click", (e) => {
        e.preventDefault();
        const isHidden = menu.classList.contains("hidden");
        if (isHidden) {
            menu.classList.remove("hidden");
            btn.setAttribute("aria-expanded", "true");
        } else {
            closeMenu();
        }
    });

    document.addEventListener("click", (e) => {
        if (e.target.closest("#langSwitcher")) return;
        closeMenu();
    });

    menu.querySelectorAll("[data-lang]").forEach(item => {
        const lang = item.dataset.lang;
        const meta = LANG_META[lang];
        if (meta) {
            item.innerHTML = `
                ${flagSvg(lang)}
                <span>${meta.name}</span>
            `.trim();
        }
        item.addEventListener("click", (e) => {
            e.preventDefault();
            const lang = item.dataset.lang;
            setLang(lang);
            setButtonText();
            applyTranslations();
            closeMenu();
        });
    });
}
