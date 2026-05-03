import { showToast } from "../modules/toast.js";

const form = document.getElementById("menuGeneratorForm");
const clearButton = document.getElementById("clearMenuSeedBtn");
const generateButton = document.getElementById("generateMenuSeedBtn");
const preview = document.getElementById("menuGeneratorPreview");
const previewMeta = document.getElementById("menuGeneratorPreviewMeta");
const importForm = document.querySelector("[data-generator-import-form]");
const hiddenJson = document.querySelector("[data-generated-menu-json]");

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

function renderGeneratedMenu(data) {
    const categories = Array.isArray(data?.categories) ? data.categories : [];
    if (!categories.length) {
        preview.innerHTML = `
            <div class="rounded-lg border border-dashed border-slate-200 px-5 py-10 text-center text-sm text-slate-500">
                Генерация не вернула категории.
            </div>
        `;
        previewMeta.textContent = "Категории не найдены.";
        importForm?.classList.add("hidden");
        return;
    }

    const categoryCount = categories.length;
    const itemCount = categories.reduce((sum, category) => sum + (category.items?.length || 0), 0);
    previewMeta.textContent = `Категорий: ${categoryCount}. Блюд: ${itemCount}.`;

    preview.innerHTML = categories.map((category, categoryIndex) => `
        <section class="rounded-xl border border-slate-200">
            <div class="flex items-center justify-between gap-3 border-b border-slate-200 px-4 py-3">
                <div class="font-semibold text-slate-900">${escapeHtml(category.name)}</div>
                <div class="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
                    ${category.items.length} поз.
                </div>
            </div>
            <div class="divide-y divide-slate-200">
                ${category.items.map((item, itemIndex) => `
                    <article class="px-4 py-3">
                        <div class="flex items-start justify-between gap-4">
                            <div class="min-w-0">
                                <div class="text-sm font-semibold text-slate-900">
                                    ${categoryIndex + 1}.${itemIndex + 1} ${escapeHtml(item.name)}
                                </div>
                                <div class="mt-1 text-sm text-slate-600">${escapeHtml(item.description || "Без описания")}</div>
                                <div class="mt-2 text-xs text-slate-500">${escapeHtml(item.amount || "Порция не указана")}</div>
                            </div>
                            <div class="shrink-0 rounded-full bg-emerald-50 px-3 py-1 text-sm font-semibold text-emerald-700">
                                ${escapeHtml(item.price)} c
                            </div>
                        </div>
                    </article>
                `).join("")}
            </div>
        </section>
    `).join("");

    if (hiddenJson) {
        hiddenJson.value = JSON.stringify(data);
    }
    importForm?.classList.remove("hidden");
}

function resetPreview() {
    preview.innerHTML = `
        <div class="rounded-lg border border-dashed border-slate-200 px-5 py-10 text-center text-sm text-slate-500">
            Здесь появятся категории и блюда после генерации.
        </div>
    `;
    previewMeta.textContent = "Сначала выполните генерацию.";
    if (hiddenJson) hiddenJson.value = "";
    importForm?.classList.add("hidden");
}

async function handleGenerate(event) {
    event.preventDefault();
    if (!form) return;

    const apiUrl = form.dataset.menuGeneratorApiUrl || window.MENU_GENERATOR_API_URL;
    if (!apiUrl) {
        showToast("Не задан URL генератора меню.", "error");
        return;
    }

    const formData = new FormData(form);
    const payload = {
        cuisine: String(formData.get("cuisine") || "").trim(),
        concept: String(formData.get("concept") || "").trim(),
        language: String(formData.get("language") || "ru").trim(),
        category_count: Number(formData.get("category_count") || 5),
        items_per_category: Number(formData.get("items_per_category") || 6),
    };

    if (!payload.cuisine || !payload.concept) {
        showToast("Заполните кухню и концепцию.", "error");
        return;
    }

    generateButton.disabled = true;
    generateButton.textContent = "Генерация...";

    try {
        const response = await fetch(apiUrl, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            credentials: "same-origin",
            body: JSON.stringify(payload),
        });

        const data = await response.json();
        if (!response.ok || !data.ok) {
            throw new Error(data.message || "Не удалось сгенерировать меню");
        }

        renderGeneratedMenu(data.generated_menu);
        showToast("Черновик меню готов.", "success");
    } catch (error) {
        console.error(error);
        resetPreview();
        showToast(String(error.message || error), "error");
    } finally {
        generateButton.disabled = false;
        generateButton.textContent = "Сгенерировать";
    }
}

form?.addEventListener("submit", handleGenerate);
clearButton?.addEventListener("click", () => {
    form?.reset();
    resetPreview();
});
