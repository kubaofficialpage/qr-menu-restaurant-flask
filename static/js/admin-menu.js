function initAdminMenuPage() {
    const categoryList = document.querySelector("[data-category-list]");
    const categoryActionsMenu = document.querySelector("[data-category-actions-menu]");
    const selectedCategoryTitle = document.getElementById("selectedCategoryTitle");
    const selectedCategoryActions = document.getElementById("selectedCategoryActions");
    const adminMenuRows = document.querySelectorAll(".menu-item-row");
    let draggedCategory = null;
    let wasCategoryDragged = false;

    if (!categoryList && !adminMenuRows.length) return;

    function closeCategoryActionsMenu() {
        categoryActionsMenu?.classList.add("hidden");
    }

    function setActiveCategoryButton(catId, categoryName) {
        document.querySelectorAll('[data-action="adminFilterCat"]').forEach((button) => {
            const isActive = button.dataset.param === String(catId);
            button.classList.toggle("border-slate-900", isActive);
            button.classList.toggle("bg-slate-900", isActive);
            button.classList.toggle("text-white", isActive);
            button.classList.toggle("border-slate-200", !isActive);
            button.classList.toggle("bg-white", !isActive);
            button.classList.toggle("text-slate-700", !isActive);
            button.classList.toggle("hover:bg-slate-50", !isActive);
        });

        if (selectedCategoryTitle) {
            selectedCategoryTitle.textContent = categoryName || "Все блюда";
        }

        selectedCategoryActions?.classList.toggle("hidden", catId === "all");
        document.querySelectorAll("[data-category-action-item]").forEach((item) => {
            item.classList.toggle("hidden", item.dataset.categoryActionItem !== String(catId));
        });
        closeCategoryActionsMenu();
    }

    function saveCategoryOrder() {
        if (!categoryList) return;

        const categoryIds = [...categoryList.querySelectorAll("[data-category-sort-id]")].map((button) =>
            Number(button.dataset.categorySortId),
        );

        if (!categoryIds.length) return;

        fetch(categoryList.dataset.reorderUrl, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Accept: "application/json",
            },
            credentials: "same-origin",
            body: JSON.stringify({ category_ids: categoryIds }),
        })
            .then((response) => {
                if (!response.ok) {
                    throw new Error("Category reorder failed");
                }
                return response.json();
            })
            .then((data) => {
                if (!data.ok) {
                    throw new Error(data.message || "Category reorder failed");
                }
            })
            .catch((error) => {
                console.error(error);
                window.location.reload();
            });
    }

    document.addEventListener("click", (event) => {
        const actionsToggle = event.target.closest("[data-category-actions-toggle]");
        if (actionsToggle) {
            categoryActionsMenu?.classList.toggle("hidden");
            return;
        }

        const target = event.target.closest('[data-action="adminFilterCat"]');
        if (target) {
            if (wasCategoryDragged) {
                event.preventDefault();
                wasCategoryDragged = false;
                return;
            }

            const category = target.dataset.param;
            setActiveCategoryButton(category, target.dataset.categoryName);
            adminMenuRows.forEach((row) => {
                row.classList.toggle(
                    "hidden",
                    category !== "all" && String(row.dataset.categoryId) !== String(category),
                );
            });
            return;
        }

        if (!event.target.closest("[data-category-actions-menu]")) {
            closeCategoryActionsMenu();
        }
    });

    document.addEventListener("click", (event) => {
        const btn = event.target.closest("[data-generate-description]");
        if (!btn) return;

        const url = btn.dataset.generateDescriptionUrl;
        if (!url) return;

        const form = btn.closest("form");
        if (!form) return;

        const nameInput = form.querySelector('input[name="name"]');
        const descriptionEl = form.querySelector('textarea[name="description"]');
        if (!nameInput || !descriptionEl) return;

        const dishName = (nameInput.value || "").trim();
        if (!dishName) {
            alert("Введите название блюда");
            return;
        }

        btn.disabled = true;
        const originalText = btn.textContent;
        btn.textContent = "Генерация...";

        fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Accept: "application/json",
            },
            credentials: "same-origin",
            body: JSON.stringify({ name: dishName, language: "ru" }),
        })
            .then((response) => response.json().then((data) => ({ ok: response.ok, data })))
            .then(({ ok, data }) => {
                if (!ok || !data.ok) {
                    throw new Error(data.message || "Ошибка генерации");
                }
                descriptionEl.value = data.description || "";
            })
            .catch((error) => {
                console.error(error);
                alert(String(error.message || error));
            })
            .finally(() => {
                btn.disabled = false;
                btn.textContent = originalText;
            });
    });

    categoryList?.addEventListener("dragstart", (event) => {
        draggedCategory = event.target.closest("[data-category-sort-id]");
        if (!draggedCategory) return;

        wasCategoryDragged = true;
        draggedCategory.classList.add("opacity-50");
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", draggedCategory.dataset.categorySortId);
    });

    categoryList?.addEventListener("dragover", (event) => {
        if (!draggedCategory) return;

        event.preventDefault();
        const target = event.target.closest("[data-category-sort-id]");
        if (!target || target === draggedCategory) return;

        const rect = target.getBoundingClientRect();
        const shouldInsertAfter = event.clientY > rect.top + rect.height / 2;
        categoryList.insertBefore(draggedCategory, shouldInsertAfter ? target.nextSibling : target);
    });

    categoryList?.addEventListener("dragend", () => {
        if (!draggedCategory) return;

        draggedCategory.classList.remove("opacity-50");
        draggedCategory = null;
        saveCategoryOrder();
        setTimeout(() => {
            wasCategoryDragged = false;
        }, 150);
    });
}

initAdminMenuPage();
