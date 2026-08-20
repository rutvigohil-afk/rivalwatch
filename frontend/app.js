const API = "http://127.0.0.1:5000";


// ===============================
// PAGE NAVIGATION
// ===============================

const navItems = document.querySelectorAll(".nav-item");
const pages = document.querySelectorAll(".page");
const pageTitle = document.getElementById("page-title");

navItems.forEach(button => {
    button.addEventListener("click", () => {

        const pageName = button.dataset.page;

        navItems.forEach(item => item.classList.remove("active"));
        button.classList.add("active");

        pages.forEach(page => {
            page.classList.remove("active-page");
        });

        document.getElementById(pageName).classList.add("active-page");

        pageTitle.textContent =
            pageName.charAt(0).toUpperCase() + pageName.slice(1);

        if (pageName === "products") {
            loadProducts();
        }

        if (pageName === "changes") {
            loadChanges();
        }

        if (pageName === "health") {
            loadHealth();
        }
    });
});


// ===============================
// EXTRA PAGE BUTTONS
// ===============================

document.querySelectorAll("[data-page-link]").forEach(button => {

    button.addEventListener("click", () => {

        const pageName = button.dataset.pageLink;

        document.querySelector(
            `.nav-item[data-page="${pageName}"]`
        ).click();

    });

});


// ===============================
// LOAD DASHBOARD
// ===============================

async function loadDashboard() {

    try {

        const response = await fetch(`${API}/api/dashboard`);

        if (!response.ok) {
            throw new Error("Dashboard API failed");
        }

        const data = await response.json();

        document.getElementById("productCount").textContent =
            data.product_count;

        document.getElementById("changeCount").textContent =
            data.change_count;

        displayRecentChanges(data.recent_changes);

    } catch (error) {

        console.error("Dashboard error:", error);

    }
}


// ===============================
// PRODUCTS
// ===============================

async function loadProducts() {

    try {

        const response = await fetch(`${API}/api/products`);

        if (!response.ok) {
            throw new Error("Products API failed");
        }

        const products = await response.json();

        const table = document.getElementById("productsTable");

        table.innerHTML = "";

        products.forEach(product => {

            const row = document.createElement("tr");

            row.innerHTML = `
                <td>
                    <strong>${escapeHTML(product.name)}</strong>
                    <br>
                    <small>${escapeHTML(product.description || "")}</small>
                </td>

                <td>
                    ${product.currency || "INR"}
                    ${Number(product.price || 0).toLocaleString("en-IN")}
                </td>

                <td>
                    ⭐ ${product.rating ?? "N/A"}
                </td>

                <td>
                    ${product.currency || "INR"}
                </td>

                <td>
                    <span class="status-badge healthy-badge">
                        Available
                    </span>
                </td>
            `;

            table.appendChild(row);
        });

    } catch (error) {

        console.error("Products error:", error);

    }
}


// ===============================
// CHANGES
// ===============================

async function loadChanges() {

    try {

        const response = await fetch(`${API}/api/changes`);

        if (!response.ok) {
            throw new Error("Changes API failed");
        }

        const changes = await response.json();

        displayChanges(changes);

    } catch (error) {

        console.error("Changes error:", error);

    }
}


function displayChanges(changes) {

    const container = document.getElementById("changesList");

    container.innerHTML = "";

    if (!changes.length) {

        container.innerHTML = `
            <div class="empty-state">
                No changes detected yet.
            </div>
        `;

        return;
    }

    changes.forEach(change => {

        const item = document.createElement("div");

        item.className = "change-item";

        item.innerHTML = `
            <h3>${escapeHTML(change.change_type)}</h3>

            <p>
                Product:
                <strong>${escapeHTML(change.product_id)}</strong>
            </p>

            <p>
                Old:
                ${escapeHTML(change.old_value || "N/A")}
            </p>

            <p>
                New:
                ${escapeHTML(change.new_value || "N/A")}
            </p>
        `;

        container.appendChild(item);

    });
}


function displayRecentChanges(changes) {

    const container = document.getElementById("recentChanges");

    container.innerHTML = "";

    if (!changes || !changes.length) {

        container.innerHTML = `
            <p>No recent changes detected.</p>
        `;

        return;
    }

    changes.slice(0, 5).forEach(change => {

        const item = document.createElement("div");

        item.className = "change-item";

        item.innerHTML = `
            <strong>${escapeHTML(change.change_type)}</strong>

            <p>
                Product:
                ${escapeHTML(change.product_id)}
            </p>
        `;

        container.appendChild(item);

    });
}


// ===============================
// HEALTH
// ===============================

async function loadHealth() {

    try {

        const response = await fetch(`${API}/health`);

        const data = await response.json();

        console.log("Scraper health:", data);

    } catch (error) {

        console.error("Health error:", error);

    }
}


// ===============================
// RUN SCRAPER
// ===============================

const scrapeButton = document.getElementById("scrapeBtn");

scrapeButton.addEventListener("click", async () => {

    scrapeButton.disabled = true;

    scrapeButton.textContent = "↻ Running...";

    try {

        const response = await fetch(`${API}/api/scrape`, {
            method: "POST"
        });

        const data = await response.json();

        if (data.success) {

            alert(
                `Scraping completed!\nProducts found: ${data.products_found}`
            );

            await loadDashboard();

        } else {

            alert("Scraper failed.");

        }

    } catch (error) {

        console.error(error);

        alert(
            "Could not connect to backend.\nMake sure Flask is running."
        );

    }

    scrapeButton.disabled = false;

    scrapeButton.textContent = "↻ Run Scraper";

});


// ===============================
// SECURITY HELPER
// ===============================

function escapeHTML(value) {

    if (value === null || value === undefined) {
        return "";
    }

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


// ===============================
// START
// ===============================

loadDashboard();