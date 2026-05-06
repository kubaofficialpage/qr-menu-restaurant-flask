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
        // Summary can still render partially from cart state, but menu data is preferred.
    }

    renderCartSummary();
    renderBranches();
    syncKnownCustomerState();
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
    if (otpStub) otpStub.textContent = pageData.otpStubCode || "0000";

    if (checkoutState.customer) {
        document.getElementById("checkoutFullName").value = checkoutState.customer.full_name || "";
        document.getElementById("checkoutPhone").value = checkoutState.customer.phone_whatsapp || "";
        document.getElementById("checkoutAddress").value = checkoutState.customer.address || "";
    }
}

function bindCheckoutActions() {
    document.getElementById("checkoutNextBtn")?.addEventListener("click", onNextStep);
    document.getElementById("checkoutBackBtn")?.addEventListener("click", onBackStep);
    document.getElementById("checkoutRequestOtpBtn")?.addEventListener("click", requestOtp);
    document.getElementById("checkoutVerifyOtpBtn")?.addEventListener("click", verifyOtp);
    document.getElementById("checkoutForm")?.addEventListener("submit", submitOrder);
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

function syncKnownCustomerState() {
    const knownCard = document.getElementById("checkoutKnownCustomerCard");
    const knownText = document.getElementById("checkoutKnownCustomerText");
    const identityFields = document.getElementById("checkoutIdentityFields");
    const otpBlock = document.getElementById("checkoutOtpBlock");
    const status = document.getElementById("checkoutAuthStatus");
    if (!knownCard || !knownText || !identityFields || !otpBlock) return;

    if (!checkoutState.customer || !checkoutState.verified) {
        knownCard.classList.add("hidden");
        identityFields.classList.remove("hidden");
        otpBlock.classList.remove("hidden");
        return;
    }

    knownText.textContent = `${checkoutState.customer.full_name || ""} - ${checkoutState.customer.phone_whatsapp || ""}`;
    knownCard.classList.remove("hidden");
    identityFields.classList.add("hidden");
    otpBlock.classList.add("hidden");
    if (status) {
        status.textContent = "Номер подтвержден.";
    }
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
        const fullName = document.getElementById("checkoutFullName")?.value.trim() || checkoutState.customer?.full_name || "";
        const phone = document.getElementById("checkoutPhone")?.value.trim() || checkoutState.customer?.phone_whatsapp || "";
        const address = document.getElementById("checkoutAddress")?.value.trim() || "";

        if (!fullName) return showError("Укажите ФИО.");
        if (!phone) return showError("Укажите номер WhatsApp.");
        if (!address) return showError("Укажите адрес доставки.");
        if (!checkoutState.verified) return showError("Подтвердите номер через OTP.");
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

async function requestOtp() {
    resetMessages();
    const phone = document.getElementById("checkoutPhone")?.value.trim() || "";
    if (!phone) {
        showError("Сначала укажите номер WhatsApp.");
        return;
    }

    const response = await fetch("/api/customer/request-otp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone }),
    });
    const data = await response.json();
    if (!response.ok || !data.ok) {
        showError(data.message || "Не удалось отправить OTP.");
        return;
    }

    const status = document.getElementById("checkoutAuthStatus");
    if (status) {
        status.textContent = data.message || "Код отправлен.";
    }
}

async function verifyOtp() {
    resetMessages();
    const phone = document.getElementById("checkoutPhone")?.value.trim() || "";
    const fullName = document.getElementById("checkoutFullName")?.value.trim() || "";
    const address = document.getElementById("checkoutAddress")?.value.trim() || "";
    const code = document.getElementById("checkoutOtpCode")?.value.trim() || "";

    if (!phone || !fullName) {
        showError("Сначала заполните ФИО и номер WhatsApp.");
        return;
    }
    if (!code) {
        showError("Введите OTP код.");
        return;
    }

    const response = await fetch("/api/customer/verify-otp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone, code, fullName, address }),
    });
    const data = await response.json();
    if (!response.ok || !data.ok) {
        showError(data.message || "Не удалось подтвердить номер.");
        return;
    }

    checkoutState.customer = data.customer || null;
    checkoutState.verified = true;
    syncKnownCustomerState();
    showSuccess("Номер подтвержден.");
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
    const fullNameInput = document.getElementById("checkoutFullName");
    const phoneInput = document.getElementById("checkoutPhone");
    const addressInput = document.getElementById("checkoutAddress");
    const commentInput = document.getElementById("checkoutComment");
    const otpInput = document.getElementById("checkoutOtpCode");
    const receiptInput = document.getElementById("checkoutReceipt");
    const paymentType = document.querySelector('input[name="payment_type"]:checked')?.value || "online";

    formData.set("full_name", fullNameInput?.value.trim() || checkoutState.customer?.full_name || "");
    formData.set("phone", phoneInput?.value.trim() || checkoutState.customer?.phone_whatsapp || "");
    formData.set("address", addressInput?.value.trim() || "");
    formData.set("comment", commentInput?.value.trim() || "");
    formData.set("otp_code", checkoutState.customer ? "" : (otpInput?.value.trim() || ""));
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
    ["checkoutError", "checkoutSuccess", "checkoutLoading"].forEach(id => {
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

function showSuccess(message) {
    const box = document.getElementById("checkoutSuccess");
    if (!box) return;
    box.textContent = message;
    box.classList.remove("hidden");
}

function showLoading() {
    document.getElementById("checkoutLoading")?.classList.remove("hidden");
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}
