import { showToast } from "./toast.js";

const modal = document.getElementById("adminModal");
const modalTitle = document.getElementById("adminModalTitle");
const modalBody = document.getElementById("adminModalBody");
const sidebar = document.getElementById("adminSidebar");
const sidebarOverlay = document.getElementById("adminSidebarOverlay");
const slugPattern = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const slugChecks = new WeakMap();

function openModal(title, html) {
    if (!modal || !modalTitle || !modalBody) return;
    if (!html) {
        showToast("Не удалось открыть форму.", "error");
        return;
    }

    modalTitle.textContent = title;
    modalBody.innerHTML = html;
    initFormEnhancements(modalBody);
    modal.classList.remove("hidden");
    modal.classList.add("flex");
    const firstInput = modalBody.querySelector("input, select, textarea, button");
    firstInput?.focus();
}

function showFlashMessages() {
    const messages = window.ADMIN_FLASH_MESSAGES || [];
    messages.forEach(([category, message]) => {
        showToast(message, category === "error" ? "error" : "success");
    });
}

function initDataTables() {
    if (!window.DataTable) return;

    document.querySelectorAll(".js-data-table").forEach((table) => {
        if (table.dataset.dataTableReady === "true") return;
        if (table.querySelector("[data-empty-row]")) return;

        const columnCount = table.querySelectorAll("thead th").length;
        const actionColumnIndex = columnCount > 0 ? columnCount - 1 : 0;

        new window.DataTable(table, {
            pageLength: 10,
            lengthMenu: [10, 25, 50, 100],
            order: [],
            columnDefs: [
                {
                    targets: actionColumnIndex,
                    orderable: false,
                    searchable: false,
                },
            ],
            language: {
                search: "Поиск:",
                lengthMenu: "Показывать _MENU_",
                info: "Показано _START_-_END_ из _TOTAL_",
                infoEmpty: "Нет записей",
                infoFiltered: "(отфильтровано из _MAX_)",
                zeroRecords: "Ничего не найдено",
                emptyTable: "Нет данных",
                paginate: {
                    first: "Первая",
                    previous: "Назад",
                    next: "Вперед",
                    last: "Последняя",
                },
            },
        });

        table.dataset.dataTableReady = "true";
    });
}

function closeModal() {
    if (!modal || !modalBody) return;
    modal.classList.add("hidden");
    modal.classList.remove("flex");
    modalBody.innerHTML = "";
}

function openSidebar() {
    sidebar?.classList.remove("-translate-x-full");
    sidebarOverlay?.classList.remove("hidden");
}

function closeSidebar() {
    sidebar?.classList.add("-translate-x-full");
    sidebarOverlay?.classList.add("hidden");
}

function templateHtml(id) {
    const template = document.getElementById(id);
    return template ? template.innerHTML.trim() : "";
}

function filterRestaurantPicker(input) {
    const picker = input.closest("[data-restaurant-picker]");
    if (!picker) return;

    const query = input.value.trim().toLowerCase();
    const options = picker.querySelectorAll("[data-restaurant-option]");
    const empty = picker.querySelector("[data-restaurant-empty]");
    let visibleCount = 0;

    options.forEach((option) => {
        const text = (option.dataset.searchText || option.textContent || "").toLowerCase();
        const isVisible = text.includes(query);
        option.classList.toggle("hidden", !isVisible);
        if (isVisible) visibleCount += 1;
    });

    empty?.classList.toggle("hidden", visibleCount > 0);
}

function imageUploadElements(input) {
    const dropzone = input.closest("[data-image-upload-dropzone]");
    return {
        dropzone,
        filename: dropzone?.querySelector("[data-image-upload-filename]"),
        placeholder: dropzone?.querySelector("[data-image-upload-placeholder]"),
        preview: dropzone?.querySelector("[data-image-upload-preview]"),
        progress: dropzone?.querySelector("[data-image-upload-progress]"),
        status: dropzone?.querySelector("[data-image-upload-status]"),
    };
}

function setImageUploadFile(input, file) {
    if (!file || !file.type.startsWith("image/")) return;

    const { filename, placeholder, preview, progress, status } = imageUploadElements(input);
    if (filename) filename.textContent = file.name;
    if (status) status.textContent = "Файл выбран";
    if (progress) progress.style.width = "35%";

    const reader = new FileReader();
    reader.addEventListener("load", () => {
        if (preview) {
            preview.src = reader.result;
            preview.classList.remove("hidden");
        }
        placeholder?.classList.add("hidden");
        if (progress) progress.style.width = "100%";
        if (status) status.textContent = "Готово к загрузке";
    });
    reader.readAsDataURL(file);
}

function setDroppedImageFiles(input, files) {
    if (!files.length) return;

    const dataTransfer = new DataTransfer();
    dataTransfer.items.add(files[0]);
    input.files = dataTransfer.files;
    setImageUploadFile(input, files[0]);
}

function formatKgPhone(value) {
    let digits = value.replace(/\D/g, "");
    if (digits.startsWith("996")) {
        digits = digits.slice(3);
    }
    if (digits.startsWith("0")) {
        digits = digits.slice(1);
    }
    digits = digits.slice(0, 9);

    const parts = [];
    if (digits.length > 0) parts.push(digits.slice(0, 3));
    if (digits.length > 3) parts.push(digits.slice(3, 5));
    if (digits.length > 5) parts.push(digits.slice(5, 7));
    if (digits.length > 7) parts.push(digits.slice(7, 9));

    return parts.length ? `+996 ${parts.join(" ")}` : "";
}

function slugElements(input) {
    const field = input.closest("div");
    const container = field?.parentElement;
    return {
        spinner: field?.querySelector("[data-slug-spinner]"),
        check: field?.querySelector("[data-slug-check]"),
        status: container?.querySelector("[data-slug-status]"),
        publicLink: container?.querySelector("[data-slug-public-link]"),
    };
}

function setSlugState(input, state, message = "") {
    const { spinner, check, status } = slugElements(input);

    spinner?.classList.toggle("hidden", state !== "checking");
    check?.classList.toggle("hidden", state !== "available");

    input.classList.remove(
        "border-emerald-500",
        "ring-2",
        "ring-emerald-100",
        "border-red-500",
        "ring-red-100",
        "border-blue-500",
        "ring-blue-100",
    );

    if (status) {
        status.textContent = message;
        status.className = "mt-1 text-xs";
        status.classList.toggle("hidden", !message);
    }

    if (state === "checking") {
        input.classList.add("border-blue-500", "ring-2", "ring-blue-100");
        status?.classList.add("text-blue-600");
        input.setCustomValidity("");
    } else if (state === "available") {
        input.classList.add("border-emerald-500", "ring-2", "ring-emerald-100");
        status?.classList.add("text-emerald-600");
        input.setCustomValidity("");
    } else if (state === "unavailable" || state === "invalid") {
        input.classList.add("border-red-500", "ring-2", "ring-red-100");
        status?.classList.add("text-red-600");
        input.setCustomValidity(message || "Slug недоступен.");
    } else {
        status?.classList.add("text-slate-500");
        input.setCustomValidity("");
    }
}

function updateSlugPublicLink(input) {
    const { publicLink } = slugElements(input);
    if (!publicLink) return;

    const slug = input.value.trim().toLowerCase() || "restaurant-name";
    publicLink.href = `/${slug}`;
    publicLink.textContent = `/${slug}`;
}

function scheduleSlugCheck(input) {
    updateSlugPublicLink(input);

    const previous = slugChecks.get(input);
    if (previous) {
        clearTimeout(previous.timer);
        previous.controller?.abort();
    }

    const slug = input.value.trim().toLowerCase();
    input.value = slug;

    if (!slug) {
        setSlugState(input, "idle", "");
        slugChecks.delete(input);
        return;
    }

    if (!slugPattern.test(slug)) {
        setSlugState(input, "invalid", "Только латиница, цифры и дефисы.");
        slugChecks.delete(input);
        return;
    }

    setSlugState(input, "checking", "Проверяем slug...");

    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
        try {
            const url = new URL(input.dataset.slugCheckUrl, window.location.origin);
            url.searchParams.set("slug", slug);
            if (input.dataset.slugCurrentId) {
                url.searchParams.set("exclude_id", input.dataset.slugCurrentId);
            }

            const response = await fetch(url, {
                headers: { Accept: "application/json" },
                signal: controller.signal,
            });
            if (!response.ok) throw new Error("Slug check failed");

            const result = await response.json();
            if (result.available) {
                setSlugState(input, "available", result.message || "Slug свободен.");
            } else {
                setSlugState(input, result.valid ? "unavailable" : "invalid", result.message || "Slug уже занят.");
            }
        } catch (error) {
            if (error.name === "AbortError") return;
            setSlugState(input, "idle", "Не удалось проверить slug.");
        }
    }, 350);

    slugChecks.set(input, { timer, controller });
}

function serializeWorkSchedule(schedule) {
    const hidden = schedule.parentElement.querySelector("[data-work-hours-value]");
    if (!hidden) return;

    const dayRows = schedule.querySelectorAll("[data-work-open]");
    const labels = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];
    const lines = [];

    dayRows.forEach((openInput, index) => {
        const row = openInput.closest(".grid");
        const closeInput = row.querySelector("[data-work-close]");
        const closedInput = row.querySelector("[data-work-closed]");
        if (!closeInput || !closedInput) return;

        if (closedInput.checked) {
            lines.push(`${labels[index]} выходной`);
        } else {
            lines.push(`${labels[index]} ${openInput.value}-${closeInput.value}`);
        }
    });

    hidden.value = lines.join("; ");
}

function initFormEnhancements(root = document) {
    root.querySelectorAll("[data-phone-mask]").forEach((input) => {
        input.value = formatKgPhone(input.value);
    });

    root.querySelectorAll("[data-work-schedule]").forEach((schedule) => {
        if (schedule.dataset.ready === "true") return;
        schedule.dataset.ready = "true";
        const hidden = schedule.parentElement.querySelector("[data-work-hours-value]");
        if (hidden && !hidden.value.trim()) {
            serializeWorkSchedule(schedule);
        }
    });

    root.querySelectorAll("[data-slug-input]").forEach((input) => {
        if (input.dataset.slugReady === "true") return;
        input.dataset.slugReady = "true";
        updateSlugPublicLink(input);
    });
}

document.addEventListener("click", (event) => {
    const openButton = event.target.closest("[data-modal-template]");
    if (openButton) {
        const title = openButton.dataset.modalTitle || "";
        const html = templateHtml(openButton.dataset.modalTemplate);
        openModal(title, html);
        return;
    }

    const deleteButton = event.target.closest("[data-delete-action]");
    if (deleteButton) {
        const title = deleteButton.dataset.modalTitle || "Подтверждение удаления";
        const message = deleteButton.dataset.deleteMessage || "Удалить этот элемент?";
        const action = deleteButton.dataset.deleteAction;
        openModal(title, `
            <form method="POST" action="${action}" class="space-y-5">
                <p class="text-sm text-slate-600">${message}</p>
                <div class="flex justify-end gap-2">
                    <button type="button" data-modal-close class="rounded-md border border-slate-200 px-4 py-2 text-sm hover:bg-slate-50">Отмена</button>
                    <button type="submit" class="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700">Удалить</button>
                </div>
            </form>
        `);
        return;
    }

    if (event.target.closest("[data-modal-close]") || event.target === modal) {
        closeModal();
        return;
    }

    if (event.target.closest("[data-admin-open-sidebar]")) {
        openSidebar();
        return;
    }

    if (event.target.closest("[data-admin-close-sidebar]")) {
        closeSidebar();
    }
});

document.addEventListener("input", (event) => {
    const restaurantSearch = event.target.closest("[data-restaurant-search]");
    if (restaurantSearch) {
        filterRestaurantPicker(restaurantSearch);
    }

    const phoneInput = event.target.closest("[data-phone-mask]");
    if (phoneInput) {
        phoneInput.value = formatKgPhone(phoneInput.value);
    }

    const slugInput = event.target.closest("[data-slug-input]");
    if (slugInput) {
        scheduleSlugCheck(slugInput);
    }
});

document.addEventListener("change", (event) => {
    const imageInput = event.target.closest("[data-image-upload-input]");
    if (imageInput && imageInput.files.length) {
        setImageUploadFile(imageInput, imageInput.files[0]);
    }

    const schedule = event.target.closest("[data-work-schedule]");
    if (schedule) {
        schedule.dataset.dirty = "true";
        serializeWorkSchedule(schedule);
    }
});

document.addEventListener("dragover", (event) => {
    const dropzone = event.target.closest("[data-image-upload-dropzone]");
    if (!dropzone) return;
    event.preventDefault();
    dropzone.classList.add("border-blue-400", "bg-blue-50");
});

document.addEventListener("dragleave", (event) => {
    const dropzone = event.target.closest("[data-image-upload-dropzone]");
    if (!dropzone || dropzone.contains(event.relatedTarget)) return;
    dropzone.classList.remove("border-blue-400", "bg-blue-50");
});

document.addEventListener("drop", (event) => {
    const dropzone = event.target.closest("[data-image-upload-dropzone]");
    if (!dropzone) return;
    event.preventDefault();
    dropzone.classList.remove("border-blue-400", "bg-blue-50");

    const input = dropzone.querySelector("[data-image-upload-input]");
    setDroppedImageFiles(input, event.dataTransfer.files);
});

document.addEventListener("submit", (event) => {
    const form = event.target;
    form.querySelectorAll("[data-work-schedule]").forEach((schedule) => {
        const hidden = schedule.parentElement.querySelector("[data-work-hours-value]");
        if (schedule.dataset.dirty === "true" || !hidden.value.trim()) {
            serializeWorkSchedule(schedule);
        }
    });

    const imageInput = form.querySelector("[data-image-upload-input]");
    if (!imageInput || !imageInput.files.length) return;

    const { progress, status } = imageUploadElements(imageInput);
    if (progress) progress.style.width = "100%";
    if (status) status.textContent = "Загружается...";
});

document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
        closeModal();
        closeSidebar();
    }
});

showFlashMessages();
initDataTables();
initFormEnhancements();
