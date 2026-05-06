import { getRestaurantSlug } from './page-context.js';
import { lockPageScroll, unlockPageScroll } from './scroll-lock.js';
import { showToast } from './toast.js';

let checkoutState = {
    step: 1,
    branches: [],
    selectedBranchId: null,
    verified: false,
    customer: null,
};

export function initCheckoutFlow({ getCartItems, clearCart }) {
    const checkoutButton = document.getElementById("cartPageCheckout");
    const modal = document.getElementById("checkoutModal");
    if (!checkoutButton || !modal) return;

    checkoutButton.addEventListener("click", async (event) => {
        event.preventDefault();
        if (!getCartItems().length) return;
        await openCheckoutModal();
    });

    document.getElementById("closeCheckoutModalBtn")?.addEventListener("click", closeCheckoutModal);
    modal.addEventListener("click", (event) => {
        if (event.target === modal) closeCheckoutModal();
    });

    document.getElementById("checkoutNextBtn")?.addEventListener("click", () => handleNextStep(getCartItems));
    document.getElementById("checkoutBackBtn")?.addEventListener("click", handlePreviousStep);
    document.getElementById("checkoutRequestOtpBtn")?.addEventListener("click", requestOtp);
    document.getElementById("checkoutVerifyOtpBtn")?.addEventListener("click", verifyOtp);
    document.getElementById("checkoutBranches")?.addEventListener("change", onBranchSelected);
    document.getElementById("checkoutForm")?.addEventListener("submit", (event) => submitOrder(event, getCartItems, clearCart));
}

async function openCheckoutModal() {
    resetMessages();
    setCheckoutStep(1);
    document.getElementById("checkoutModal")?.classList.remove("hidden");
    lockPageScroll("checkout-modal");
    await loadCheckoutOptions();
}

function closeCheckoutModal() {
    document.getElementById("checkoutModal")?.classList.add("hidden");
    unlockPageScroll("checkout-modal");
}

async function loadCheckoutOptions() {
    const slug = getRestaurantSlug();
    if (!slug) return;

    const response = await fetch(`/api/${encodeURIComponent(slug)}/checkout/options`);
    const data = await response.json();
    if (!data.ok) {
        showError(data.message || "Не удалось загрузить данные оформления.");
        return;
    }

    checkoutState.branches = data.branches || [];
    checkoutState.selectedBranchId = checkoutState.branches[0]?.id || null;
    checkoutState.customer = data.customer || null;
    checkoutState.verified = Boolean(data.customer?.id);

    fillCustomerData(data.customer);
    syncKnownCustomerState();
    renderBranches();
    renderBranchQr();
    updateAuthStatus();
}

function fillCustomerData(customer) {
    if (!customer) return;
    setInputValue("checkoutFullName", customer.full_name || "");
    setInputValue("checkoutPhone", customer.phone_whatsapp || "");
    setInputValue("checkoutAddress", customer.address || "");
}

function setInputValue(id, value) {
    const input = document.getElementById(id);
    if (input) input.value = value;
}

function syncKnownCustomerState() {
    const isKnown = Boolean(checkoutState.customer?.id) && checkoutState.verified;
    const knownCard = document.getElementById("checkoutKnownCustomerCard");
    const knownText = document.getElementById("checkoutKnownCustomerText");
    const otpBlock = document.getElementById("checkoutOtpBlock");
    const identityFields = document.getElementById("checkoutIdentityFields");
    const fullNameInput = document.getElementById("checkoutFullName");
    const phoneInput = document.getElementById("checkoutPhone");
    const otpInput = document.getElementById("checkoutOtpCode");

    knownCard?.classList.toggle("hidden", !isKnown);
    otpBlock?.classList.toggle("hidden", isKnown);
    identityFields?.classList.toggle("hidden", isKnown);

    if (knownText) {
        knownText.textContent = isKnown
            ? `${checkoutState.customer.full_name || ""} - ${checkoutState.customer.phone_whatsapp || ""}`
            : "";
    }

    if (fullNameInput) fullNameInput.readOnly = isKnown;
    if (phoneInput) phoneInput.readOnly = isKnown;
    if (otpInput && isKnown) otpInput.value = "";
}

function renderBranches() {
    const container = document.getElementById("checkoutBranches");
    if (!container) return;

    if (!checkoutState.branches.length) {
        container.innerHTML = `
            <div class="rounded-3xl border border-dashed border-slate-300 px-5 py-8 text-center text-sm text-slate-500">
                У ресторана пока нет активных филиалов для доставки.
            </div>
        `;
        return;
    }

    container.innerHTML = checkoutState.branches.map(branch => `
        <label class="checkout-branch-card relative block">
            <input type="radio" name="branch_id" value="${branch.id}" ${Number(branch.id) === Number(checkoutState.selectedBranchId) ? "checked" : ""}>
            <span class="checkout-branch-card__body">
                <span class="block text-base font-semibold text-slate-900">${escapeHtml(branch.name)}</span>
                <span class="mt-1 block text-sm text-slate-500">${escapeHtml(branch.address)}</span>
            </span>
        </label>
    `).join("");
}

function onBranchSelected(event) {
    const input = event.target.closest("input[name='branch_id']");
    if (!input) return;
    checkoutState.selectedBranchId = Number(input.value);
    renderBranchQr();
}

function renderBranchQr() {
    const image = document.getElementById("checkoutBranchQrImage");
    const empty = document.getElementById("checkoutBranchQrEmpty");
    if (!image || !empty) return;

    const branch = checkoutState.branches.find(item => Number(item.id) === Number(checkoutState.selectedBranchId));
    if (branch?.qr_code_url) {
        image.src = branch.qr_code_url;
        image.classList.remove("hidden");
        empty.classList.add("hidden");
    } else {
        image.src = "";
        image.classList.add("hidden");
        empty.classList.remove("hidden");
    }
}

async function requestOtp() {
    resetMessages();
    const phone = document.getElementById("checkoutPhone")?.value.trim();
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
    if (!data.ok) {
        showError(data.message || "Не удалось запросить OTP.");
        return;
    }

    showToast(data.message || "Код отправлен.");
    const status = document.getElementById("checkoutAuthStatus");
    if (status) {
        status.textContent = data.existingCustomer
            ? "Клиент найден. Подтвердите номер кодом 0000."
            : "Новый клиент. После подтверждения профиль будет создан автоматически.";
    }
}

async function verifyOtp() {
    resetMessages();
    const payload = {
        phone: document.getElementById("checkoutPhone")?.value.trim(),
        code: document.getElementById("checkoutOtpCode")?.value.trim(),
        fullName: document.getElementById("checkoutFullName")?.value.trim(),
        address: document.getElementById("checkoutAddress")?.value.trim(),
    };

    const response = await fetch("/api/customer/verify-otp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!data.ok) {
        showError(data.message || "OTP не подтвержден.");
        checkoutState.verified = false;
        updateAuthStatus();
        return;
    }

    checkoutState.verified = true;
    checkoutState.customer = data.customer || null;
    fillCustomerData(data.customer);
    syncKnownCustomerState();
    updateAuthStatus("Номер подтвержден. Можно продолжать оформление.");
}

function updateAuthStatus(customMessage) {
    const status = document.getElementById("checkoutAuthStatus");
    if (!status) return;
    status.textContent = customMessage || (checkoutState.verified ? "Клиент авторизован." : "Подтвердите номер через OTP перед оформлением.");
    status.className = `mt-2 text-xs ${checkoutState.verified ? "text-emerald-700" : "text-slate-500"}`;
}

function handleNextStep(getCartItems) {
    resetMessages();
    if (checkoutState.step === 1 && !validateStepOne()) return;
    if (checkoutState.step === 2 && !validateStepTwo()) return;
    if (checkoutState.step === 1 && !getCartItems().length) {
        showError("Корзина пуста.");
        return;
    }
    setCheckoutStep(Math.min(3, checkoutState.step + 1));
}

function handlePreviousStep() {
    resetMessages();
    setCheckoutStep(Math.max(1, checkoutState.step - 1));
}

function validateStepOne() {
    const fullName = document.getElementById("checkoutFullName")?.value.trim();
    const phone = document.getElementById("checkoutPhone")?.value.trim();
    const address = document.getElementById("checkoutAddress")?.value.trim();
    if (!fullName || !phone || !address) {
        showError("Заполните ФИО, номер WhatsApp и адрес.");
        return false;
    }
    if (!checkoutState.verified) {
        showError("Подтвердите номер OTP-кодом 0000.");
        return false;
    }
    return true;
}

function validateStepTwo() {
    if (!checkoutState.selectedBranchId) {
        showError("Выберите филиал.");
        return false;
    }
    return true;
}

function setCheckoutStep(step) {
    checkoutState.step = step;
    document.querySelectorAll("[data-checkout-step]").forEach(node => {
        node.classList.toggle("hidden", Number(node.dataset.checkoutStep) !== step);
    });
    document.querySelectorAll("[data-checkout-step-indicator]").forEach(node => {
        node.classList.toggle("is-active", Number(node.dataset.checkoutStepIndicator) === step);
    });
    document.getElementById("checkoutBackBtn")?.classList.toggle("hidden", step === 1);
    document.getElementById("checkoutNextBtn")?.classList.toggle("hidden", step === 3);
    document.getElementById("checkoutSubmitBtn")?.classList.toggle("hidden", step !== 3);
}

async function submitOrder(event, getCartItems, clearCart) {
    event.preventDefault();
    resetMessages();
    if (!validateStepOne() || !validateStepTwo()) return;

    const slug = getRestaurantSlug();
    if (!slug) return;

    const formData = new FormData();
    formData.set("full_name", document.getElementById("checkoutFullName")?.value.trim() || "");
    formData.set("phone", document.getElementById("checkoutPhone")?.value.trim() || "");
    formData.set("otp_code", document.getElementById("checkoutOtpCode")?.value.trim() || "");
    formData.set("address", document.getElementById("checkoutAddress")?.value.trim() || "");
    formData.set("comment", document.getElementById("checkoutComment")?.value.trim() || "");
    formData.set("payment_type", document.querySelector("input[name='payment_type']:checked")?.value || "online");
    formData.set("branch_id", String(checkoutState.selectedBranchId || ""));
    formData.set("cart", JSON.stringify(getCartItems().map(item => ({ id: item.id, qty: item.qty }))));

    const receipt = document.getElementById("checkoutReceipt")?.files?.[0];
    if (receipt) {
        formData.set("receipt", receipt);
    }

    const submitButton = document.getElementById("checkoutSubmitBtn");
    const nextButton = document.getElementById("checkoutNextBtn");
    const backButton = document.getElementById("checkoutBackBtn");
    const closeButton = document.getElementById("closeCheckoutModalBtn");
    const loadingNode = document.getElementById("checkoutLoading");

    if (submitButton) {
        submitButton.disabled = true;
        submitButton.textContent = "Оформляем...";
    }
    if (nextButton) nextButton.disabled = true;
    if (backButton) backButton.disabled = true;
    if (closeButton) closeButton.disabled = true;
    loadingNode?.classList.remove("hidden");

    try {
        const response = await fetch(`/api/${encodeURIComponent(slug)}/orders`, {
            method: "POST",
            body: formData,
        });
        const data = await response.json();
        if (!data.ok) {
            showError(data.message || "Не удалось оформить заказ.");
            return;
        }

        clearCart();
        showSuccess(`Заказ ${data.order.order_number} оформлен.`);
        showToast("Заказ отправлен оператору.");
        setTimeout(() => {
            closeCheckoutModal();
            window.location.href = data.order?.detail_url || `/${slug}/orders`;
        }, 900);
    } finally {
        if (submitButton) {
            submitButton.disabled = false;
            submitButton.textContent = "Оформить заказ";
        }
        if (nextButton) nextButton.disabled = false;
        if (backButton) backButton.disabled = false;
        if (closeButton) closeButton.disabled = false;
        loadingNode?.classList.add("hidden");
    }
}

function showError(message) {
    const node = document.getElementById("checkoutError");
    if (!node) return;
    node.textContent = message;
    node.classList.remove("hidden");
}

function showSuccess(message) {
    const node = document.getElementById("checkoutSuccess");
    if (!node) return;
    node.textContent = message;
    node.classList.remove("hidden");
}

function resetMessages() {
    document.getElementById("checkoutError")?.classList.add("hidden");
    document.getElementById("checkoutSuccess")?.classList.add("hidden");
    document.getElementById("checkoutLoading")?.classList.add("hidden");
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}
