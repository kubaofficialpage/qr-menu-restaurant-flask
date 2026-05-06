import { showToast } from "../modules/toast.js";

const state = {
    phone: "",
    step: "phone",
    stubCode: "000000",
};

document.addEventListener("DOMContentLoaded", () => {
    const openBtn = document.getElementById("profileOpenAuthBtn");
    const modal = document.getElementById("profileAuthModal");
    if (!openBtn || !modal) return;

    openBtn.addEventListener("click", (event) => {
        event.preventDefault();
        openModal();
    });

    document.getElementById("profileAuthCloseBtn")?.addEventListener("click", closeModal);
    modal.addEventListener("click", (event) => {
        if (event.target === modal) closeModal();
    });

    document.getElementById("profileAuthNextBtn")?.addEventListener("click", requestOtp);
    document.getElementById("profileAuthVerifyBtn")?.addEventListener("click", verifyOtp);

    document.querySelectorAll("[data-profile-otp-digit]").forEach((input, index, inputs) => {
        input.addEventListener("input", () => {
            input.value = input.value.replace(/\D/g, "").slice(0, 1);
            if (input.value && index < inputs.length - 1) {
                inputs[index + 1].focus();
            }
        });

        input.addEventListener("keydown", (event) => {
            if (event.key === "Backspace" && !input.value && index > 0) {
                inputs[index - 1].focus();
            }
        });

        input.addEventListener("paste", (event) => {
            event.preventDefault();
            const digits = String(event.clipboardData?.getData("text") || "")
                .replace(/\D/g, "")
                .slice(0, inputs.length);

            digits.split("").forEach((digit, digitIndex) => {
                if (inputs[digitIndex]) {
                    inputs[digitIndex].value = digit;
                }
            });

            const targetIndex = Math.min(digits.length, inputs.length - 1);
            inputs[targetIndex]?.focus();
        });
    });
});

function openModal() {
    const modal = document.getElementById("profileAuthModal");
    if (!modal) return;
    modal.classList.remove("hidden");
    resetModal();
    document.getElementById("profileAuthPhone")?.focus();
}

function closeModal() {
    document.getElementById("profileAuthModal")?.classList.add("hidden");
}

function resetModal() {
    state.step = "phone";
    hideError();

    document.getElementById("profileAuthStepPhone")?.classList.remove("hidden");
    document.getElementById("profileAuthStepCode")?.classList.add("hidden");

    const phoneInput = document.getElementById("profileAuthPhone");
    if (phoneInput) {
        phoneInput.value = state.phone || "";
    }

    document.querySelectorAll("[data-profile-otp-digit]").forEach((input) => {
        input.value = "";
    });

    const stub = document.getElementById("profileOtpStubCode");
    if (stub) stub.textContent = state.stubCode;
}

async function requestOtp() {
    hideError();
    const phone = document.getElementById("profileAuthPhone")?.value.trim() || "";
    if (!phone) {
        showError("Введите номер WhatsApp.");
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

    state.phone = phone;
    state.stubCode = data.code || "000000";

    const stub = document.getElementById("profileOtpStubCode");
    if (stub) stub.textContent = state.stubCode;

    showToast(data.message || "Код отправлен.", "success");

    document.getElementById("profileAuthStepPhone")?.classList.add("hidden");
    document.getElementById("profileAuthStepCode")?.classList.remove("hidden");
    document.querySelector("[data-profile-otp-digit]")?.focus();
}

async function verifyOtp() {
    hideError();

    const phone = document.getElementById("profileAuthPhone")?.value.trim() || state.phone || "";
    const code = getOtpCode();

    if (!phone) {
        showError("Введите номер WhatsApp.");
        return;
    }

    if (code.length !== 6) {
        showError("Введите код из 6 цифр.");
        return;
    }

    const response = await fetch("/api/customer/verify-otp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone, code, fullName: "", address: "" }),
    });

    const data = await response.json();
    if (!response.ok || !data.ok) {
        showError(data.message || "Не удалось подтвердить номер.");
        return;
    }

    showToast("Вы успешно авторизованы.", "success");
    window.location.reload();
}

function getOtpCode() {
    return Array.from(document.querySelectorAll("[data-profile-otp-digit]"))
        .map((input) => input.value.trim())
        .join("");
}

function showError(message) {
    const box = document.getElementById("profileAuthError");
    if (!box) return;
    box.textContent = message;
    box.classList.remove("hidden");
}

function hideError() {
    document.getElementById("profileAuthError")?.classList.add("hidden");
}
