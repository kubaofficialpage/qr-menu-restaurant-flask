import { fetchMenuData } from '../modules/api.js';
import { applyTranslations, bindLangSwitcher, initI18n } from '../modules/i18n.js';
import { readJsonScript, getRestaurantSlug } from '../modules/page-context.js';
import { state, loadCartFromStorage, saveCartToStorage } from '../modules/state.js';

const checkoutState = {
    currentStep: 1,
    branches: [],
    customer: null,
    verified: false,
    selectedBranchId: null,
    isSubmitting: false,
    requestId: null,
    pendingAdvance: false,
    authStep: "phone",
};

document.addEventListener("DOMContentLoaded", async () => {
    initI18n("ru");
    applyTranslations();
    bindLangSwitcher();
    loadCartFromStorage();
    hydrateCheckoutState();
    bindCheckoutActions();

    try {
        await fetchMenuData();
    } catch {
        // Keep checkout usable even if menu fetch fails.
    }

    renderCartSummary();
    renderBranches();
    syncAuthCard();
    updateStep();
});

function hydrateCheckoutState() {
    const pageData = readJsonScript("checkoutPageData") || {};
    checkoutState.branches = Array.isArray(pageData.branches) ? pageData.branches : [];
    checkoutState.customer = pageData.customer || null;
    checkoutState.verified = Boolean(pageData.customer);
    checkoutState.selectedBranchId = checkoutState.branches[0]?.id || null;
    checkoutState.requestId = window.crypto?.randomUUID?.() || `checkout-${Date.now()}-${Math.random().toString(16).slice(2)}`;

    const otpStub = document.getElementById("checkoutOtpStubCode");
    if (otpStub) otpStub.textContent = pageData.otpStubCode || "000000";

    if (checkoutState.customer) {
        document.getElementById("checkoutAddress").value = checkoutState.customer.address || "";
    }
}

function bindCheckoutActions() {
    document.getElementById("checkoutNextBtn")?.addEventListener("click", onNextStep);
    document.getElementById("checkoutBackBtn")?.addEventListener("click", onBackStep);
    document.getElementById("checkoutForm")?.addEventListener("submit", submitOrder);

    document.getElementById("checkoutOpenAuthBtn")?.addEventListener("click", openAuthModal);
    document.getElementById("checkoutAuthCloseBtn")?.addEventListener("click", closeAuthModal);
    document.getElementById("checkoutAuthModal")?.addEventListener("click", event => {
        if (event.target === event.currentTarget) closeAuthModal();
    });
    document.getElementById("checkoutAuthNextBtn")?.addEventListener("click", requestOtp);
    document.getElementById("checkoutAuthVerifyBtn")?.addEventListener("click", verifyOtp);

    document.querySelectorAll("[data-otp-digit]").forEach((input, index, inputs) => {
        input.addEventListener("input", () => {
            input.value = input.value.replace(/\D/g, "").slice(0, 1);
            if (input.value && index < inputs.length - 1) {
                inputs[index + 1].focus();
            }
        });
        input.addEventListener("keydown", event => {
            if (event.key === "Backspace" && !input.value && index > 0) {
                inputs[index - 1].focus();
            }
        });
        input.addEventListener("paste", event => {
            event.preventDefault();
            const digits = String(event.clipboardData?.getData("text") || "").replace(/\D/g, "").slice(0, inputs.length);
            digits.split("").forEach((digit, digitIndex) => {
                if (inputs[digitIndex]) inputs[digitIndex].value = digit;
            });
            const targetIndex = Math.min(digits.length, inputs.length - 1);
            inputs[targetIndex]?.focus();
        });
    });
}

function getCartItems() {
    const items = [];
    Object.entries(state.cartQty).forEach(([id, qty]) => {
        const menuItem = state.menuById.get(String(id));
        if (!menuItem || qty <= 0) return;
        items.push({ ...menuItem, qty });
    });
    return items;
}

function renderCartSummary() {
    const items = getCartItems();
    const container = document.getElementById("checkoutCartItems");
    const emptyState = document.getElementById("checkoutCartEmpty");
    const count = document.getElementById("checkoutCartCount");
    const total = document.getElementById("checkoutTotalAmount");
    if (!container || !emptyState || !count || !total) return;

    const grandTotal = items.reduce((sum, item) => sum + Number(item.price || 0) * Number(item.qty || 0), 0);
    total.textContent = String(grandTotal);
    count.textContent = `${items.length} позиций`;

    if (!items.length) {
        container.innerHTML = "";
        emptyState.classList.remove("hidden");
        document.getElementById("checkoutNextBtn")?.setAttribute("disabled", "disabled");
        document.getElementById("checkoutSubmitBtn")?.setAttribute("disabled", "disabled");
        return;
    }

    emptyState.classList.add("hidden");
    document.getElementById("checkoutNextBtn")?.removeAttribute("disabled");
    document.getElementById("checkoutSubmitBtn")?.removeAttribute("disabled");
    container.innerHTML = items.map(item => `
        <div class="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
            <div class="min-w-0">
                <div class="truncate font-semibold text-slate-900">${escapeHtml(item.name)}</div>
                <div class="text-sm text-slate-500">${escapeHtml(item.amount || "")}</div>
            </div>
            <div class="text-right">
                <div class="font-semibold text-slate-900">${Number(item.qty) * Number(item.price)} c</div>
                <div class="text-sm text-slate-500">${Number(item.qty)} x ${Number(item.price)} c</div>
            </div>
        </div>
    `).join("");
}

function renderBranches() {
    const container = document.getElementById("checkoutBranches");
    if (!container) return;

    container.innerHTML = checkoutState.branches.map(branch => `
        <label class="checkout-branch-card">
            <input type="radio" name="branch_id" value="${branch.id}" ${Number(branch.id) === Number(checkoutState.selectedBranchId) ? "checked" : ""}>
            <span class="checkout-branch-card__body">
                <strong class="block text-slate-900">${escapeHtml(branch.name)}</strong>
                <span class="mt-1 block text-sm text-slate-500">${escapeHtml(branch.address || "")}</span>
            </span>
        </label>
    `).join("");

    container.querySelectorAll('input[name="branch_id"]').forEach(input => {
        input.addEventListener("change", () => {
            checkoutState.selectedBranchId = Number(input.value);
            updateBranchQr();
        });
    });

    updateBranchQr();
}

function syncAuthCard() {
    const title = document.getElementById("checkoutAuthTitle");
    const text = document.getElementById("checkoutAuthText");
    const button = document.getElementById("checkoutOpenAuthBtn");
    if (!title || !text || !button) return;

    if (checkoutState.verified) {
        title.textContent = "Авторизация подтверждена";
        text.textContent = "Номер телефона успешно подтвержден.";
        button.classList.add("hidden");
        return;
    }

    title.textContent = "Нужна авторизация";
    text.textContent = "Подтвердите номер телефона перед оформлением заказа.";
    button.classList.remove("hidden");
}

function updateBranchQr() {
    const branch = checkoutState.branches.find(item => Number(item.id) === Number(checkoutState.selectedBranchId));
    const qrImage = document.getElementById("checkoutBranchQrImage");
    const qrEmpty = document.getElementById("checkoutBranchQrEmpty");
    if (!qrImage || !qrEmpty) return;

    if (branch?.qr_code_url) {
        qrImage.src = branch.qr_code_url;
        qrImage.classList.remove("hidden");
        qrEmpty.classList.add("hidden");
        return;
    }

    qrImage.src = "";
    qrImage.classList.add("hidden");
    qrEmpty.classList.remove("hidden");
}

function updateStep() {
    document.querySelectorAll("[data-checkout-step]").forEach(section => {
        section.classList.toggle("hidden", Number(section.dataset.checkoutStep) !== checkoutState.currentStep);
    });

    document.querySelectorAll("[data-checkout-step-indicator]").forEach(item => {
        item.classList.toggle("is-active", Number(item.dataset.checkoutStepIndicator) <= checkoutState.currentStep);
    });

    document.getElementById("checkoutBackBtn")?.classList.toggle("hidden", checkoutState.currentStep === 1);
    document.getElementById("checkoutNextBtn")?.classList.toggle("hidden", checkoutState.currentStep === 3);
    document.getElementById("checkoutSubmitBtn")?.classList.toggle("hidden", checkoutState.currentStep !== 3);
}

function onNextStep() {
    if (checkoutState.currentStep === 1 && !checkoutState.verified) {
        checkoutState.pendingAdvance = true;
        openAuthModal();
        return;
    }
    if (!validateStep(checkoutState.currentStep)) return;
    checkoutState.currentStep = Math.min(3, checkoutState.currentStep + 1);
    updateStep();
}

function onBackStep() {
    checkoutState.currentStep = Math.max(1, checkoutState.currentStep - 1);
    updateStep();
}

function validateStep(step) {
    resetMessages();

    if (step === 1) {
        const address = document.getElementById("checkoutAddress")?.value.trim() || "";
        if (!address) return showError("Укажите адрес доставки.");
        if (!checkoutState.verified) return showError("Сначала авторизуйтесь по номеру телефона.");
    }

    if (step === 2 && !checkoutState.selectedBranchId) {
        return showError("Выберите филиал.");
    }

    if (step === 3) {
        const paymentType = document.querySelector('input[name="payment_type"]:checked')?.value || "online";
        const receipt = document.getElementById("checkoutReceipt")?.files?.[0];
        if (paymentType === "online" && !receipt) {
            return showError("Загрузите чек оплаты.");
        }
    }

    return true;
}

function openAuthModal() {
    document.getElementById("checkoutAuthModal")?.classList.remove("hidden");
    resetAuthModal();
    document.getElementById("checkoutAuthPhone")?.focus();
}

function closeAuthModal() {
    document.getElementById("checkoutAuthModal")?.classList.add("hidden");
    checkoutState.pendingAdvance = false;
}

function resetAuthModal() {
    checkoutState.authStep = "phone";
    document.getElementById("checkoutAuthStepPhone")?.classList.remove("hidden");
    document.getElementById("checkoutAuthStepCode")?.classList.add("hidden");
    document.getElementById("checkoutAuthError")?.classList.add("hidden");
    document.querySelectorAll("[data-otp-digit]").forEach(input => {
        input.value = "";
    });

    const phoneInput = document.getElementById("checkoutAuthPhone");
    if (phoneInput && checkoutState.customer?.phone_whatsapp) {
        phoneInput.value = checkoutState.customer.phone_whatsapp;
    }
}

async function requestOtp() {
    hideAuthError();
    const phone = document.getElementById("checkoutAuthPhone")?.value.trim() || "";
    if (!phone) {
        showAuthError("Введите номер телефона.");
        return;
    }

    const response = await fetch("/api/customer/request-otp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone }),
    });
    const data = await response.json();
    if (!response.ok || !data.ok) {
        showAuthError(data.message || "Не удалось отправить OTP.");
        return;
    }

    checkoutState.authStep = "code";
    document.getElementById("checkoutAuthStepPhone")?.classList.add("hidden");
    document.getElementById("checkoutAuthStepCode")?.classList.remove("hidden");
    document.querySelector("[data-otp-digit]")?.focus();
}

async function verifyOtp() {
    hideAuthError();
    const phone = document.getElementById("checkoutAuthPhone")?.value.trim() || "";
    const code = getOtpCode();

    if (!phone) {
        showAuthError("Введите номер телефона.");
        return;
    }
    if (code.length !== 6) {
        showAuthError("Введите код из 6 цифр.");
        return;
    }

    const response = await fetch("/api/customer/verify-otp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            phone,
            code,
            address: document.getElementById("checkoutAddress")?.value.trim() || "",
        }),
    });
    const data = await response.json();
    if (!response.ok || !data.ok) {
        showAuthError(data.message || "Не удалось подтвердить номер.");
        return;
    }

    checkoutState.customer = data.customer || null;
    checkoutState.verified = true;
    if (checkoutState.customer?.address && !document.getElementById("checkoutAddress")?.value.trim()) {
        document.getElementById("checkoutAddress").value = checkoutState.customer.address;
    }
    syncAuthCard();
    document.getElementById("checkoutAuthModal")?.classList.add("hidden");

    if (checkoutState.pendingAdvance && validateStep(1)) {
        checkoutState.pendingAdvance = false;
        checkoutState.currentStep = 2;
        updateStep();
    }
}

function getOtpCode() {
    return Array.from(document.querySelectorAll("[data-otp-digit]"))
        .map(input => input.value.trim())
        .join("");
}

async function submitOrder(event) {
    event.preventDefault();
    if (checkoutState.isSubmitting) return;
    if (!validateStep(3)) return;

    const slug = getRestaurantSlug();
    const items = getCartItems();
    if (!slug || !items.length) {
        showError("Корзина пуста.");
        return;
    }

    checkoutState.isSubmitting = true;
    resetMessages();
    toggleSubmitting(true);

    const formData = new FormData();
    const addressInput = document.getElementById("checkoutAddress");
    const commentInput = document.getElementById("checkoutComment");
    const receiptInput = document.getElementById("checkoutReceipt");
    const paymentType = document.querySelector('input[name="payment_type"]:checked')?.value || "online";

    formData.set("full_name", checkoutState.customer?.full_name || "");
    formData.set("phone", checkoutState.customer?.phone_whatsapp || "");
    formData.set("address", addressInput?.value.trim() || "");
    formData.set("comment", commentInput?.value.trim() || "");
    formData.set("otp_code", "");
    formData.set("payment_type", paymentType);
    formData.set("branch_id", String(checkoutState.selectedBranchId || ""));
    formData.set("client_request_id", checkoutState.requestId);
    formData.set("cart", JSON.stringify(items.map(item => ({ id: item.id, qty: item.qty }))));

    const receiptFile = receiptInput?.files?.[0];
    if (receiptFile) {
        formData.set("receipt", receiptFile);
    }

    try {
        const response = await fetch(`/api/${encodeURIComponent(slug)}/orders`, {
            method: "POST",
            body: formData,
        });
        const data = await response.json();
        if (!response.ok || !data.ok) {
            throw new Error(data.message || "Не удалось оформить заказ.");
        }

        clearCart();
        showLoading();
        window.location.assign(data.order?.detail_url || `/${slug}/orders`);
    } catch (error) {
        checkoutState.isSubmitting = false;
        toggleSubmitting(false);
        showError(error.message || "Не удалось оформить заказ.");
    }
}

function clearCart() {
    Object.keys(state.cartQty).forEach(id => delete state.cartQty[id]);
    saveCartToStorage();
}

function toggleSubmitting(isSubmitting) {
    const submit = document.getElementById("checkoutSubmitBtn");
    const back = document.getElementById("checkoutBackBtn");
    const next = document.getElementById("checkoutNextBtn");

    [submit, back, next].forEach(button => {
        if (!button) return;
        button.disabled = isSubmitting;
    });

    if (submit) {
        submit.textContent = isSubmitting ? "Оформляем..." : "Оформить заказ";
    }
}

function resetMessages() {
    ["checkoutError", "checkoutLoading"].forEach(id => {
        document.getElementById(id)?.classList.add("hidden");
    });
}

function showError(message) {
    const box = document.getElementById("checkoutError");
    if (!box) return false;
    box.textContent = message;
    box.classList.remove("hidden");
    return false;
}

function showLoading() {
    document.getElementById("checkoutLoading")?.classList.remove("hidden");
}

function showAuthError(message) {
    const box = document.getElementById("checkoutAuthError");
    if (!box) return;
    box.textContent = message;
    box.classList.remove("hidden");
}

function hideAuthError() {
    document.getElementById("checkoutAuthError")?.classList.add("hidden");
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}
