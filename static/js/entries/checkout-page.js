import { fetchMenuData } from "../modules/api.js";
import { applyTranslations, bindLangSwitcher, initI18n } from "../modules/i18n.js";
import { getRestaurantBranchPublicId, getRestaurantSlug, readJsonScript } from "../modules/page-context.js";
import { state, loadCartFromStorage, saveCartToStorage } from "../modules/state.js";

const checkoutState = {
    currentStep: 1,
    branch: null,
    customer: null,
    verified: false,
    isSubmitting: false,
    requestId: null,
    pendingAdvance: false,
    receiptPreviewUrl: null,
    receiptProgressTimer: null,
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
        // keep checkout page usable
    }

    renderCartSummary();
    syncAuthCard();
    updateBranchQr();
    updateTotals();
    updateStep();
});

function hydrateCheckoutState() {
    const pageData = readJsonScript("checkoutPageData") || {};
    checkoutState.branch = pageData.branch || null;
    checkoutState.customer = pageData.customer || null;
    checkoutState.verified = Boolean(pageData.customer);
    checkoutState.requestId = window.crypto?.randomUUID?.() || `checkout-${Date.now()}`;

    const otpStub = document.getElementById("checkoutOtpStubCode");
    if (otpStub) otpStub.textContent = pageData.otpStubCode || "000000";

    if (checkoutState.customer?.address) {
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
    document.getElementById("checkoutReceipt")?.addEventListener("change", updateReceiptPreview);

    document.querySelectorAll("[data-otp-digit]").forEach((input, index, inputs) => {
        input.addEventListener("input", () => {
            input.value = input.value.replace(/\D/g, "").slice(0, 1);
            if (input.value && index < inputs.length - 1) inputs[index + 1].focus();
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
            inputs[Math.min(digits.length, inputs.length - 1)]?.focus();
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

function getSubtotal() {
    return getCartItems().reduce((sum, item) => sum + Number(item.price || 0) * Number(item.qty || 0), 0);
}

function getDeliveryFee() {
    return Number(checkoutState.branch?.delivery_fee || 0);
}

function updateTotals() {
    const subtotal = getSubtotal();
    const delivery = getDeliveryFee();
    const total = subtotal + delivery;
    const subtotalEl = document.getElementById("checkoutSubtotalAmount");
    const deliveryEl = document.getElementById("checkoutDeliveryAmount");
    const grandEl = document.getElementById("checkoutGrandTotalAmount");
    if (subtotalEl) subtotalEl.textContent = `${subtotal} c`;
    if (deliveryEl) deliveryEl.textContent = `${delivery} c`;
    if (grandEl) grandEl.textContent = `${total} c`;
}

function renderCartSummary() {
    const items = getCartItems();
    const nextBtn = document.getElementById("checkoutNextBtn");
    const submitBtn = document.getElementById("checkoutSubmitBtn");
    if (!items.length) {
        nextBtn?.setAttribute("disabled", "disabled");
        submitBtn?.setAttribute("disabled", "disabled");
    } else {
        nextBtn?.removeAttribute("disabled");
        submitBtn?.removeAttribute("disabled");
    }
    updateTotals();
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
    const qrImage = document.getElementById("checkoutBranchQrImage");
    const qrEmpty = document.getElementById("checkoutBranchQrEmpty");
    if (!qrImage || !qrEmpty) return;

    if (checkoutState.branch?.qr_code_url) {
        qrImage.src = checkoutState.branch.qr_code_url;
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
    document.getElementById("checkoutNextBtn")?.classList.toggle("hidden", checkoutState.currentStep === 2);
    document.getElementById("checkoutSubmitBtn")?.classList.toggle("hidden", checkoutState.currentStep !== 2);

    const actionsRow = document.getElementById("checkoutActionsRow");
    if (actionsRow) {
        actionsRow.classList.toggle("checkout-actions--step1", checkoutState.currentStep === 1);
        actionsRow.classList.toggle("checkout-actions--split", checkoutState.currentStep !== 1);
    }
}

function onNextStep() {
    if (checkoutState.currentStep === 1 && !checkoutState.verified) {
        checkoutState.pendingAdvance = true;
        openAuthModal();
        return;
    }
    if (!validateStep(1)) return;
    checkoutState.currentStep = 2;
    updateStep();
}

function onBackStep() {
    checkoutState.currentStep = 1;
    updateStep();
}

function validateStep(step) {
    resetMessages();
    if (step === 1) {
        const address = document.getElementById("checkoutAddress")?.value.trim() || "";
        if (!address) return showError("Укажите адрес доставки.");
        if (!checkoutState.verified) return showError("Сначала авторизуйтесь по номеру телефона.");
    }
    if (step === 2) {
        const paymentType = document.querySelector('input[name="payment_type"]:checked')?.value || "online";
        const receipt = document.getElementById("checkoutReceipt")?.files?.[0];
        if (paymentType === "online" && !receipt) return showError("Загрузите чек оплаты.");
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
    document.getElementById("checkoutAuthStepPhone")?.classList.remove("hidden");
    document.getElementById("checkoutAuthStepCode")?.classList.add("hidden");
    document.getElementById("checkoutAuthError")?.classList.add("hidden");
    document.querySelectorAll("[data-otp-digit]").forEach(input => { input.value = ""; });
    const phoneInput = document.getElementById("checkoutAuthPhone");
    if (phoneInput && checkoutState.customer?.phone_whatsapp) {
        phoneInput.value = checkoutState.customer.phone_whatsapp;
    }
}

async function requestOtp() {
    hideAuthError();
    const phone = document.getElementById("checkoutAuthPhone")?.value.trim() || "";
    if (!phone) return showAuthError("Введите номер телефона.");

    const response = await fetch("/api/customer/request-otp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone }),
    });
    const data = await response.json();
    if (!response.ok || !data.ok) return showAuthError(data.message || "Не удалось отправить OTP.");

    document.getElementById("checkoutAuthStepPhone")?.classList.add("hidden");
    document.getElementById("checkoutAuthStepCode")?.classList.remove("hidden");
    document.querySelector("[data-otp-digit]")?.focus();
}

async function verifyOtp() {
    hideAuthError();
    const phone = document.getElementById("checkoutAuthPhone")?.value.trim() || "";
    const code = getOtpCode();
    if (!phone) return showAuthError("Введите номер телефона.");
    if (code.length !== 6) return showAuthError("Введите код из 6 цифр.");

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
    if (!response.ok || !data.ok) return showAuthError(data.message || "Не удалось подтвердить номер.");

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
    return Array.from(document.querySelectorAll("[data-otp-digit]")).map(input => input.value.trim()).join("");
}

async function submitOrder(event) {
    event.preventDefault();
    if (checkoutState.isSubmitting) return;
    if (!validateStep(2)) return;

    const slug = getRestaurantSlug();
    const branchPublicId = getRestaurantBranchPublicId();
    const items = getCartItems();
    if (!slug || !branchPublicId || !items.length) {
        showError("Корзина пуста.");
        return;
    }

    checkoutState.isSubmitting = true;
    resetMessages();
    toggleSubmitting(true);
    setReceiptProgress(100);

    const formData = new FormData();
    formData.set("full_name", checkoutState.customer?.full_name || "");
    formData.set("phone", checkoutState.customer?.phone_whatsapp || "");
    formData.set("address", document.getElementById("checkoutAddress")?.value.trim() || "");
    formData.set("comment", document.getElementById("checkoutComment")?.value.trim() || "");
    formData.set("otp_code", "");
    formData.set("payment_type", document.querySelector('input[name="payment_type"]:checked')?.value || "online");
    formData.set("branch_id", String(checkoutState.branch?.id || ""));
    formData.set("client_request_id", checkoutState.requestId);
    formData.set("cart", JSON.stringify(items.map(item => ({ id: item.id, qty: item.qty }))));

    const receiptFile = await getPreparedReceiptFile(document.getElementById("checkoutReceipt")?.files?.[0]);
    if (receiptFile) formData.set("receipt", receiptFile);

    try {
        const response = await fetch(`/api/${encodeURIComponent(slug)}/${encodeURIComponent(branchPublicId)}/orders`, {
            method: "POST",
            body: formData,
        });
        const data = await response.json();
        if (!response.ok || !data.ok) {
            throw new Error(data.message || "Не удалось оформить заказ.");
        }
        clearCart();
        showLoading();
        window.location.assign(data.order?.detail_url || `/${slug}/${branchPublicId}/orders`);
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

function updateReceiptPreview() {
    const input = document.getElementById("checkoutReceipt");
    const preview = document.getElementById("checkoutReceiptPreview");
    const meta = document.getElementById("checkoutReceiptMeta");
    const file = input?.files?.[0];
    if (!preview || !meta) return;

    if (checkoutState.receiptPreviewUrl) {
        URL.revokeObjectURL(checkoutState.receiptPreviewUrl);
        checkoutState.receiptPreviewUrl = null;
    }

    if (!file) {
        preview.src = "";
        preview.classList.add("hidden");
        meta.textContent = "PNG, JPG или WEBP";
        setReceiptProgress(0);
        return;
    }

    checkoutState.receiptPreviewUrl = URL.createObjectURL(file);
    preview.src = checkoutState.receiptPreviewUrl;
    preview.classList.remove("hidden");
    meta.textContent = `Файл: ${file.name} · ${formatFileSize(file.size)}`;
    animateReceiptProgress();
}

async function getPreparedReceiptFile(file) {
    if (!file || !file.type.startsWith("image/")) return file;
    try {
        return await compressImageToWebp(file);
    } catch {
        return file;
    }
}

function compressImageToWebp(file, options = {}) {
    const maxWidth = Number(options.maxWidth || 1280);
    const maxHeight = Number(options.maxHeight || 1280);
    const quality = Number(options.quality || 0.82);

    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onerror = () => reject(new Error("read-failed"));
        reader.onload = () => {
            const image = new Image();
            image.onerror = () => reject(new Error("image-load-failed"));
            image.onload = () => {
                let width = image.width;
                let height = image.height;
                const scale = Math.min(1, maxWidth / width, maxHeight / height);
                width = Math.max(1, Math.round(width * scale));
                height = Math.max(1, Math.round(height * scale));
                const canvas = document.createElement("canvas");
                canvas.width = width;
                canvas.height = height;
                const context = canvas.getContext("2d");
                if (!context) return reject(new Error("canvas-context-failed"));
                context.drawImage(image, 0, 0, width, height);
                canvas.toBlob(blob => {
                    if (!blob) return reject(new Error("blob-failed"));
                    const baseName = file.name.replace(/\.[^.]+$/, "") || "receipt";
                    resolve(new File([blob], `${baseName}.webp`, { type: "image/webp" }));
                }, "image/webp", quality);
            };
            image.src = String(reader.result);
        };
        reader.readAsDataURL(file);
    });
}

function toggleSubmitting(isSubmitting) {
    const submit = document.getElementById("checkoutSubmitBtn");
    const back = document.getElementById("checkoutBackBtn");
    const next = document.getElementById("checkoutNextBtn");
    [submit, back, next].forEach(button => {
        if (button) button.disabled = isSubmitting;
    });
    if (submit) {
        const label = submit.querySelector("span");
        if (label) label.textContent = isSubmitting ? "Оформляем..." : "Оформить заказ";
    }
}

function resetMessages() {
    document.getElementById("checkoutError")?.classList.add("hidden");
    document.getElementById("checkoutLoading")?.classList.add("hidden");
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

function formatFileSize(size) {
    const bytes = Number(size || 0);
    if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    if (bytes >= 1024) return `${Math.round(bytes / 1024)} KB`;
    return `${bytes} B`;
}

function setReceiptProgress(value) {
    const bar = document.getElementById("checkoutReceiptProgressBar");
    if (!bar) return;
    bar.style.width = `${Math.max(0, Math.min(100, Number(value) || 0))}%`;
}

function animateReceiptProgress() {
    if (checkoutState.receiptProgressTimer) window.clearInterval(checkoutState.receiptProgressTimer);
    let current = 0;
    setReceiptProgress(current);
    checkoutState.receiptProgressTimer = window.setInterval(() => {
        current += 20;
        setReceiptProgress(current);
        if (current >= 100) {
            window.clearInterval(checkoutState.receiptProgressTimer);
            checkoutState.receiptProgressTimer = null;
        }
    }, 90);
}
