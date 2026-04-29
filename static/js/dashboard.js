const dashboardData = window.DASHBOARD_DATA || {};

if (window.Chart && dashboardData.selected_restaurant) {
    Chart.defaults.font.family = "Montserrat, system-ui, sans-serif";
    Chart.defaults.color = "#64748b";
    Chart.defaults.plugins.legend.labels.usePointStyle = true;
    Chart.defaults.plugins.legend.labels.boxWidth = 8;

    initDailyAnalyticsChart();
    initTopDishesChart();
    initRestaurantsChart();
}

function initDailyAnalyticsChart() {
    const canvas = document.getElementById("dailyAnalyticsChart");
    if (!canvas) return;

    const context = canvas.getContext("2d");
    const visitsGradient = context.createLinearGradient(0, 0, 0, canvas.height || 320);
    visitsGradient.addColorStop(0, "rgba(59, 130, 246, 0.35)");
    visitsGradient.addColorStop(1, "rgba(59, 130, 246, 0.02)");

    const cartGradient = context.createLinearGradient(0, 0, 0, canvas.height || 320);
    cartGradient.addColorStop(0, "rgba(16, 185, 129, 0.3)");
    cartGradient.addColorStop(1, "rgba(16, 185, 129, 0.02)");

    new Chart(context, {
        type: "line",
        data: {
            labels: dashboardData.daily_labels || [],
            datasets: [
                {
                    label: "Визиты",
                    data: dashboardData.daily_visits || [],
                    borderColor: "#3b82f6",
                    backgroundColor: visitsGradient,
                    fill: true,
                    borderWidth: 3,
                    tension: 0.35,
                    pointRadius: 3,
                    pointHoverRadius: 5,
                },
                {
                    label: "Добавления в корзину",
                    data: dashboardData.daily_cart_adds || [],
                    borderColor: "#10b981",
                    backgroundColor: cartGradient,
                    fill: true,
                    borderWidth: 3,
                    tension: 0.35,
                    pointRadius: 3,
                    pointHoverRadius: 5,
                },
            ],
        },
        options: buildBaseOptions({
            interaction: { mode: "index", intersect: false },
            scales: {
                x: buildAxisOptions(),
                y: buildAxisOptions({ beginAtZero: true, ticksPrecision: 0 }),
            },
        }),
    });
}

function initTopDishesChart() {
    const canvas = document.getElementById("topDishesChart");
    if (!canvas) return;

    const topDishes = dashboardData.top_dishes || [];
    const labels = topDishes.map(item => item.name);
    const values = topDishes.map(item => item.total);

    new Chart(canvas, {
        type: "bar",
        data: {
            labels,
            datasets: [
                {
                    label: "Добавления",
                    data: values,
                    borderRadius: 14,
                    backgroundColor: [
                        "#0f172a",
                        "#1d4ed8",
                        "#0891b2",
                        "#0f766e",
                        "#65a30d",
                        "#d97706",
                        "#dc2626",
                    ],
                    maxBarThickness: 36,
                },
            ],
        },
        options: buildBaseOptions({
            indexAxis: "y",
            plugins: {
                legend: { display: false },
            },
            scales: {
                x: buildAxisOptions({ beginAtZero: true, ticksPrecision: 0 }),
                y: buildAxisOptions(),
            },
        }),
    });
}

function initRestaurantsChart() {
    const canvas = document.getElementById("restaurantsChart");
    if (!canvas) return;

    const restaurantStats = dashboardData.restaurant_stats || [];

    new Chart(canvas, {
        type: "bar",
        data: {
            labels: restaurantStats.map(item => item.name),
            datasets: [
                {
                    label: "Визиты",
                    data: restaurantStats.map(item => item.visits),
                    backgroundColor: "#3b82f6",
                    borderRadius: 10,
                },
                {
                    label: "Сессии",
                    data: restaurantStats.map(item => item.sessions),
                    backgroundColor: "#8b5cf6",
                    borderRadius: 10,
                },
                {
                    label: "Добавления",
                    data: restaurantStats.map(item => item.cart_adds),
                    backgroundColor: "#10b981",
                    borderRadius: 10,
                },
            ],
        },
        options: buildBaseOptions({
            scales: {
                x: buildAxisOptions(),
                y: buildAxisOptions({ beginAtZero: true, ticksPrecision: 0 }),
            },
        }),
    });
}

function buildBaseOptions(overrides = {}) {
    const { plugins: overridePlugins = {}, scales: overrideScales = {}, ...restOverrides } = overrides;

    return {
        responsive: true,
        maintainAspectRatio: false,
        animation: {
            duration: 700,
            easing: "easeOutQuart",
        },
        plugins: {
            legend: {
                position: "top",
                align: "start",
            },
            tooltip: {
                backgroundColor: "#0f172a",
                titleColor: "#f8fafc",
                bodyColor: "#e2e8f0",
                padding: 12,
                cornerRadius: 12,
                displayColors: true,
            },
            ...overridePlugins,
        },
        scales: {
            ...overrideScales,
        },
        ...restOverrides,
    };
}

function buildAxisOptions(options = {}) {
    const { beginAtZero, ticksPrecision, ...rest } = options;

    return {
        beginAtZero: Boolean(beginAtZero),
        border: { display: false },
        grid: {
            color: "rgba(148, 163, 184, 0.16)",
            drawTicks: false,
        },
        ticks: {
            color: "#64748b",
            padding: 10,
            precision: typeof ticksPrecision === "number" ? ticksPrecision : undefined,
        },
        ...rest,
    };
}
