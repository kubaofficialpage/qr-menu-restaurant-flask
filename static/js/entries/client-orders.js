import { getRestaurantBranchPublicId, getRestaurantSlug } from "../modules/page-context.js";

document.addEventListener("DOMContentLoaded", () => {
    const slug = getRestaurantSlug();
    const branchPublicId = getRestaurantBranchPublicId();
    if (!slug || !branchPublicId) return;

    loadOrders(slug, branchPublicId);
    initSocket(slug, branchPublicId);
});

function loadOrders(slug, branchPublicId) {
    fetch(`/api/${encodeURIComponent(slug)}/${encodeURIComponent(branchPublicId)}/orders/my`)
        .then(response => response.json())
        .then(data => renderOrders(data.orders || []))
        .catch(() => renderOrders([]));
}

function renderOrders(orders) {
    const container = document.getElementById("customerOrdersList");
    if (!container) return;

    if (!orders.length) {
        container.innerHTML = `
            <div class="rounded-[28px] border border-dashed border-slate-300 bg-white px-6 py-14 text-center">
                <div class="text-lg font-semibold text-slate-900">Заказов пока нет</div>
                <div class="mt-2 text-sm text-slate-500">Когда вы оформите доставку, статусы появятся здесь.</div>
            </div>
        `;
        return;
    }

    container.innerHTML = orders.map(order => `
        <a href="${escapeHtml(order.detail_url || "#")}" class="block rounded-[28px] bg-white p-5 shadow-[0_20px_60px_rgba(15,23,42,0.08)]">
            <div class="flex items-start justify-between gap-3">
                <div>
                    <div class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Заказ</div>
                    <div class="mt-1 text-xl font-extrabold text-slate-900">${escapeHtml(order.order_number)}</div>
                </div>
                <span class="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">${escapeHtml(order.status_label)}</span>
            </div>
            <div class="mt-4 grid gap-3 md:grid-cols-2">
                <div class="rounded-2xl bg-slate-50 px-4 py-3">
                    <div class="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">Филиал</div>
                    <div class="mt-1 font-semibold text-slate-900">${escapeHtml(order.branch?.name || "Не выбран")}</div>
                    <div class="text-sm text-slate-500">${escapeHtml(order.branch?.address || "")}</div>
                </div>
                <div class="rounded-2xl bg-slate-50 px-4 py-3">
                    <div class="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">Итого</div>
                    <div class="mt-1 font-semibold text-slate-900">${Number(order.total_amount || 0)} c</div>
                    <div class="mt-2 flex flex-wrap items-center gap-2">
                        <span class="inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${order.payment_status === "paid" ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"}">${escapeHtml(order.payment_status_label || "")}</span>
                    </div>
                    <div class="mt-2 text-sm text-slate-500">${escapeHtml(order.delivery_address || "")}</div>
                </div>
            </div>
        </a>
    `).join("");
}

function initSocket(slug, branchPublicId) {
    const configElement = document.getElementById("clientOrdersSocketConfig");
    if (!configElement || typeof io === "undefined") return;

    let config = {};
    try {
        config = JSON.parse(configElement.textContent || "{}");
    } catch {
        config = {};
    }

    const socket = io();
    socket.on("connect", () => {
        socket.emit("join_customer_room", { restaurantId: Number(config.restaurantId || 0) });
    });

    socket.on("customer_order_updated", () => {
        loadOrders(slug, branchPublicId);
    });
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}
