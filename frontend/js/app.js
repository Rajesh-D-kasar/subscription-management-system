// State Management
const state = {
  token: localStorage.getItem("token") || null,
  user: JSON.parse(localStorage.getItem("user") || "null"),
  currentRoute: "dashboard",
  productsCache: [],
  plansCache: [],
  customersCache: []
};

const API_BASE = "/api/v1";

// Toast Notifications
function showToast(msg, type = "success") {
  const container = document.getElementById("toastContainer");
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${type === "success" ? "✓" : "⚠"}</span> <span>${msg}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.remove();
  }, 4000);
}

// API Fetch Helper
async function api(endpoint, options = {}) {
  const headers = options.headers || {};
  if (state.token) {
    headers["Authorization"] = `Bearer ${state.token}`;
  }
  if (!headers["Content-Type"] && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers
  });

  if (res.status === 401) {
    handleLogout();
    throw new Error("Session expired. Please log in again.");
  }

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: "Request failed" }));
    const errorMsg = errorData.detail || "An error occurred";
    showToast(errorMsg, "error");
    throw new Error(errorMsg);
  }

  // If response is a blob/file download
  const contentType = res.headers.get("content-type");
  if (contentType && contentType.includes("application/pdf")) {
    return res.blob();
  }

  return res.json();
}

// Auth Tabs
function switchAuthTab(tab) {
  document.getElementById("tabLogin").classList.remove("active");
  document.getElementById("tabRegister").classList.remove("active");
  document.getElementById("tabForgot").classList.remove("active");

  document.getElementById("formLogin").style.display = "none";
  document.getElementById("formRegister").style.display = "none";
  document.getElementById("formForgot").style.display = "none";

  if (tab === "login") {
    document.getElementById("tabLogin").classList.add("active");
    document.getElementById("formLogin").style.display = "block";
  } else if (tab === "register") {
    document.getElementById("tabRegister").classList.add("active");
    document.getElementById("formRegister").style.display = "block";
  } else {
    document.getElementById("tabForgot").classList.add("active");
    document.getElementById("formForgot").style.display = "block";
  }
}

async function handleLogin(e) {
  e.preventDefault();
  const email = document.getElementById("loginEmail").value;
  const password = document.getElementById("loginPassword").value;

  try {
    const data = await api("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password })
    });
    setSession(data);
    showToast("Signed in successfully!");
  } catch (err) {
    console.error(err);
  }
}

async function handleRegister(e) {
  e.preventDefault();
  const full_name = document.getElementById("regName").value;
  const email = document.getElementById("regEmail").value;
  const company = document.getElementById("regCompany").value;
  const password = document.getElementById("regPassword").value;

  try {
    const data = await api("/auth/register", {
      method: "POST",
      body: JSON.stringify({ full_name, email, company, password })
    });
    setSession(data);
    showToast("Account created successfully!");
  } catch (err) {
    console.error(err);
  }
}

async function handleForgotPassword(e) {
  e.preventDefault();
  const email = document.getElementById("resetEmail").value;
  try {
    const res = await api("/auth/password-reset-request", {
      method: "POST",
      body: JSON.stringify({ email })
    });
    const box = document.getElementById("resetTokenResult");
    box.style.display = "block";
    box.innerHTML = `<strong>Reset Token:</strong><br/>${res.reset_token || "Token issued in logs."}`;
    showToast(res.message);
  } catch (err) {
    console.error(err);
  }
}

function setSession(data) {
  state.token = data.access_token;
  state.user = {
    id: data.user_id,
    email: data.email,
    name: data.full_name,
    role: data.role,
    customerId: data.customer_id
  };
  localStorage.setItem("token", state.token);
  localStorage.setItem("user", JSON.stringify(state.user));
  initApp();
}

function handleLogout() {
  state.token = null;
  state.user = null;
  localStorage.removeItem("token");
  localStorage.removeItem("user");
  document.getElementById("authView").style.display = "flex";
  document.getElementById("appView").style.display = "none";
}

// Modal Helpers
function openModal(title, bodyHtml, footerHtml) {
  document.getElementById("modalTitle").innerText = title;
  document.getElementById("modalBody").innerHTML = bodyHtml;
  document.getElementById("modalFooter").innerHTML = footerHtml;
  document.getElementById("modalOverlay").classList.add("open");
}

function closeModal() {
  document.getElementById("modalOverlay").classList.remove("open");
}

// Navigation & Role Guards
function navigate(route) {
  state.currentRoute = route;

  // Active nav item
  document.querySelectorAll(".sidebar-nav .nav-item").forEach(item => {
    item.classList.remove("active");
  });
  const currentNav = document.getElementById(`nav-${route}`);
  if (currentNav) currentNav.classList.add("active");

  const topbarActions = document.getElementById("topbarActions");
  topbarActions.innerHTML = "";

  if (route === "dashboard") renderDashboard();
  else if (route === "subscriptions") renderSubscriptions();
  else if (route === "invoices") renderInvoices();
  else if (route === "payments") renderPayments();
  else if (route === "products") renderProducts();
  else if (route === "plans") renderPlans();
  else if (route === "discounts") renderDiscounts();
  else if (route === "customers") renderCustomers();
}

function updateRoleUI() {
  const role = state.user?.role || "customer";
  document.getElementById("currentUserName").innerText = state.user?.name || "User";
  document.getElementById("currentUserRole").innerText = role.toUpperCase();
  document.getElementById("currentUserInitial").innerText = (state.user?.name || "U")[0].toUpperCase();

  document.querySelectorAll(".admin-only").forEach(el => {
    el.style.display = (role === "admin") ? "flex" : "none";
  });

  document.querySelectorAll(".staff-or-admin").forEach(el => {
    el.style.display = (role === "admin" || role === "staff") ? "flex" : "none";
  });
}

// VIEW 1: DASHBOARD
async function renderDashboard() {
  document.getElementById("pageTitle").innerText = "Dashboard & Key Metrics";
  const container = document.getElementById("mainContainer");
  container.innerHTML = `<div class="empty-state"><div class="empty-title">Loading live business intelligence...</div></div>`;

  try {
    if (state.user.role === "customer") {
      // Customer Portal Specific Dashboard
      const subs = await api("/subscriptions");
      const invs = await api("/invoices");
      const pays = await api("/payments");

      const activeSubs = subs.filter(s => s.status === "active").length;
      const unpaidInvs = invs.filter(i => i.amount_due > 0).length;

      container.innerHTML = `
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-card-header"><span class="stat-title">Active Subscriptions</span><div class="stat-icon primary">⚡</div></div>
            <div class="stat-value">${activeSubs}</div>
            <div class="stat-footer">${subs.length} total subscriptions</div>
          </div>
          <div class="stat-card">
            <div class="stat-card-header"><span class="stat-title">Pending Invoices</span><div class="stat-icon warning">🧾</div></div>
            <div class="stat-value">${unpaidInvs}</div>
            <div class="stat-footer">Awaiting payment settlement</div>
          </div>
          <div class="stat-card">
            <div class="stat-card-header"><span class="stat-title">Completed Payments</span><div class="stat-icon success">💳</div></div>
            <div class="stat-value">${pays.length}</div>
            <div class="stat-footer">Transaction receipts recorded</div>
          </div>
        </div>

        <div class="card" style="margin-bottom: 24px;">
          <div class="card-header">
            <h3 class="card-title">My Recent Subscriptions</h3>
            <button class="btn btn-primary btn-sm" onclick="openCreateSubscriptionModal()">+ New Subscription</button>
          </div>
          <div class="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Sub #</th>
                  <th>Plan</th>
                  <th>Status</th>
                  <th>Expiry Date</th>
                  <th>Total</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                ${subs.length === 0 ? '<tr><td colspan="6" style="text-align:center;">No subscriptions yet.</td></tr>' : 
                  subs.map(s => `
                    <tr>
                      <td><strong>${s.subscription_number}</strong></td>
                      <td>${s.plan_name}</td>
                      <td><span class="badge badge-${s.status}">${s.status}</span></td>
                      <td>${s.expiry_date}</td>
                      <td>₹${s.total_amount.toFixed(2)}</td>
                      <td>
                        <button class="btn btn-secondary btn-sm" onclick="renewSubscription(${s.id})">Renew</button>
                        ${s.status === 'active' ? `<button class="btn btn-danger btn-sm" onclick="closeSubscription(${s.id})">Cancel</button>` : ''}
                      </td>
                    </tr>
                  `).join('')}
              </tbody>
            </table>
          </div>
        </div>
      `;
      return;
    }

    // Admin & Staff Dashboard with live metrics
    const data = await api("/dashboard/analytics");
    const s = data.stats;

    container.innerHTML = `
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-card-header"><span class="stat-title">Revenue Collected</span><div class="stat-icon success">₹</div></div>
          <div class="stat-value">₹${s.total_revenue_collected.toLocaleString()}</div>
          <div class="stat-footer">Total payments recorded in DB</div>
        </div>
        <div class="stat-card">
          <div class="stat-card-header"><span class="stat-title">Active Subscriptions</span><div class="stat-icon primary">⚡</div></div>
          <div class="stat-value">${s.active_subscriptions}</div>
          <div class="stat-footer">Customers currently on active plans</div>
        </div>
        <div class="stat-card">
          <div class="stat-card-header"><span class="stat-title">Outstanding Payments</span><div class="stat-icon warning">⌛</div></div>
          <div class="stat-value">₹${s.outstanding_payments.toLocaleString()}</div>
          <div class="stat-footer">Pending invoice balances</div>
        </div>
        <div class="stat-card">
          <div class="stat-card-header"><span class="stat-title">Overdue Invoices</span><div class="stat-icon danger">🚨</div></div>
          <div class="stat-value">${s.overdue_invoices_count}</div>
          <div class="stat-footer">Requires immediate follow-up</div>
        </div>
      </div>

      <div class="dashboard-grid">
        <!-- Monthly Revenue Chart Representation -->
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">Monthly Revenue Performance</h3>
            <span class="badge badge-active">Actual DB Analytics</span>
          </div>
          <div style="display: flex; align-items: flex-end; gap: 24px; height: 180px; padding: 20px 0; border-bottom: 1px solid var(--border);">
            ${data.monthly_revenue.map(m => `
              <div style="flex:1; display:flex; flex-direction:column; align-items:center; gap:8px;">
                <div style="font-size:11px; font-weight:600; color:var(--text-muted);">₹${m.revenue.toFixed(0)}</div>
                <div style="width:100%; max-width:44px; height:${Math.min(130, Math.max(20, m.revenue / 25))}px; background:linear-gradient(180deg, #4f46e5, #818cf8); border-radius:6px;"></div>
                <div style="font-size:12px; font-weight:600;">${m.month}</div>
              </div>
            `).join('')}
          </div>
        </div>

        <!-- Subscription Breakdown -->
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">Lifecycle Breakdown</h3>
          </div>
          <div style="display:flex; flex-direction:column; gap:12px;">
            ${data.subscription_status_breakdown.map(b => `
              <div style="display:flex; justify-content:space-between; align-items:center; padding: 6px 0; border-bottom: 1px dashed var(--border);">
                <span class="badge badge-${b.status}">${b.status}</span>
                <strong style="font-size:14px;">${b.count}</strong>
              </div>
            `).join('')}
          </div>
        </div>
      </div>

      <!-- Overdue Invoices Alert Table -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title" style="color:var(--danger);">Urgent Overdue Invoices</h3>
          <span class="badge badge-closed">Due Date Passed</span>
        </div>
        <div class="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Invoice #</th>
                <th>Customer</th>
                <th>Due Date</th>
                <th>Total</th>
                <th>Amount Due</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              ${data.overdue_invoices.length === 0 ? '<tr><td colspan="6" style="text-align:center; padding:16px;">Zero overdue invoices! High financial health.</td></tr>' :
                data.overdue_invoices.map(i => `
                  <tr>
                    <td><strong>${i.invoice_number}</strong></td>
                    <td>${i.customer_name}</td>
                    <td style="color:var(--danger); font-weight:600;">${i.due_date}</td>
                    <td>₹${i.total_amount.toFixed(2)}</td>
                    <td style="color:var(--danger); font-weight:700;">₹${i.amount_due.toFixed(2)}</td>
                    <td>
                      <button class="btn btn-primary btn-sm" onclick="openPaymentModal(${i.id}, ${i.amount_due})">Record Pay</button>
                    </td>
                  </tr>
                `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;
  } catch (err) {
    console.error(err);
  }
}

// VIEW 2: SUBSCRIPTIONS
async function renderSubscriptions() {
  document.getElementById("pageTitle").innerText = "Subscriptions Management";
  const actions = document.getElementById("topbarActions");
  actions.innerHTML = `<button class="btn btn-primary" onclick="openCreateSubscriptionModal()">+ New Subscription</button>`;

  const container = document.getElementById("mainContainer");
  container.innerHTML = `<div class="empty-state"><div class="empty-title">Fetching subscriptions...</div></div>`;

  try {
    const subs = await api("/subscriptions");
    container.innerHTML = `
      <div class="table-wrapper">
        <div class="table-toolbar">
          <input type="text" id="subSearch" class="search-input" placeholder="Search by ID, customer..." oninput="filterSubscriptionsTable()">
          <select id="subStatusFilter" class="filter-select" onchange="filterSubscriptionsTable()">
            <option value="">All Statuses</option>
            <option value="draft">Draft</option>
            <option value="quotation">Quotation</option>
            <option value="confirmed">Confirmed</option>
            <option value="active">Active</option>
            <option value="paused">Paused</option>
            <option value="closed">Closed</option>
          </select>
        </div>
        <table>
          <thead>
            <tr>
              <th>Sub Number</th>
              <th>Customer</th>
              <th>Plan</th>
              <th>Lifecycle</th>
              <th>Dates</th>
              <th>Grand Total</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody id="subscriptionsTbody">
            ${subs.map(s => renderSubscriptionRow(s)).join('')}
          </tbody>
        </table>
      </div>
    `;
    window.allSubsCache = subs;
  } catch (err) {
    console.error(err);
  }
}

function renderSubscriptionRow(s) {
  return `
    <tr data-num="${s.subscription_number.toLowerCase()}" data-cust="${(s.customer_name || '').toLowerCase()}" data-status="${s.status}">
      <td><strong>${s.subscription_number}</strong></td>
      <td>
        <div>${s.customer_name}</div>
        <small style="color:var(--text-muted);">${s.customer_email}</small>
      </td>
      <td>
        <strong>${s.plan_name}</strong>
        <div style="font-size:11px; color:var(--text-muted);">${s.plan_recurrence.toUpperCase()}</div>
      </td>
      <td><span class="badge badge-${s.status}">${s.status}</span></td>
      <td>
        <small>Start: ${s.start_date}</small><br/>
        <small>Exp: <b>${s.expiry_date}</b></small>
      </td>
      <td><strong>₹${s.total_amount.toFixed(2)}</strong></td>
      <td>
        <div style="display:flex; gap:6px;">
          ${(state.user.role !== 'customer' && s.status === 'confirmed') ? 
            `<button class="btn btn-primary btn-sm" onclick="generateInvoiceFromSub(${s.id})">Generate Invoice</button>` : ''}
          ${(s.status === 'active') ? 
            `<button class="btn btn-secondary btn-sm" onclick="pauseSubscription(${s.id})">Pause</button>` : ''}
          ${(s.status === 'paused') ? 
            `<button class="btn btn-success btn-sm" onclick="resumeSubscription(${s.id})">Resume</button>` : ''}
          <button class="btn btn-secondary btn-sm" onclick="renewSubscription(${s.id})">Renew</button>
          ${s.status !== 'closed' ? 
            `<button class="btn btn-danger btn-sm" onclick="closeSubscription(${s.id})">Close</button>` : ''}
        </div>
      </td>
    </tr>
  `;
}

function filterSubscriptionsTable() {
  const query = document.getElementById("subSearch").value.toLowerCase();
  const filter = document.getElementById("subStatusFilter").value;
  const rows = document.querySelectorAll("#subscriptionsTbody tr");
  rows.forEach(r => {
    const num = r.getAttribute("data-num");
    const cust = r.getAttribute("data-cust");
    const st = r.getAttribute("data-status");
    const matchQuery = !query || num.includes(query) || cust.includes(query);
    const matchStatus = !filter || st === filter;
    r.style.display = (matchQuery && matchStatus) ? "" : "none";
  });
}

// Subscription Actions
async function generateInvoiceFromSub(subId) {
  try {
    const inv = await api("/invoices/generate", {
      method: "POST",
      body: JSON.stringify({ subscription_id: subId })
    });
    showToast(`Invoice ${inv.invoice_number} generated!`);
    navigate("invoices");
  } catch (err) {
    console.error(err);
  }
}

async function pauseSubscription(subId) {
  try {
    await api(`/subscriptions/${subId}/status?new_status=paused`, { method: "PUT" });
    showToast("Subscription paused.");
    renderSubscriptions();
  } catch (err) {
    console.error(err);
  }
}

async function resumeSubscription(subId) {
  try {
    await api(`/subscriptions/${subId}/status?new_status=active`, { method: "PUT" });
    showToast("Subscription resumed.");
    renderSubscriptions();
  } catch (err) {
    console.error(err);
  }
}

async function renewSubscription(subId) {
  try {
    const res = await api(`/subscriptions/${subId}/renew`, { method: "POST" });
    showToast(res.message);
    if (state.currentRoute === "subscriptions") renderSubscriptions();
    else renderDashboard();
  } catch (err) {
    console.error(err);
  }
}

async function closeSubscription(subId) {
  if (!confirm("Are you sure you want to close this subscription?")) return;
  try {
    await api(`/subscriptions/${subId}/status?new_status=closed&reason=User requested closure`, { method: "PUT" });
    showToast("Subscription closed.");
    if (state.currentRoute === "subscriptions") renderSubscriptions();
    else renderDashboard();
  } catch (err) {
    console.error(err);
  }
}

// Modal: Create Subscription with Product Variants & Auto Price Adjustment
async function openCreateSubscriptionModal() {
  const [plans, products, customers] = await Promise.all([
    api("/plans"),
    api("/products"),
    state.user.role === "customer" ? [] : api("/customers")
  ]);

  state.productsCache = products;

  const custSelectHtml = state.user.role === "customer" ? `
    <input type="hidden" id="modalCustId" value="${state.user.customerId}">
    <div class="form-group"><label>Customer Account</label><input class="form-control" value="${state.user.name}" disabled></div>
  ` : `
    <div class="form-group">
      <label>Customer</label>
      <select id="modalCustId" class="form-control" required>
        ${customers.map(c => `<option value="${c.id}">${c.name} (${c.email})</option>`).join('')}
      </select>
    </div>
  `;

  const bodyHtml = `
    ${custSelectHtml}
    <div class="form-group">
      <label>Billing Plan</label>
      <select id="modalPlanId" class="form-control">
        ${plans.map(p => `<option value="${p.id}">${p.name} - ₹${p.price} (${p.recurrence})</option>`).join('')}
      </select>
    </div>
    <div class="form-group">
      <label>Select Product</label>
      <select id="modalProdId" class="form-control" onchange="onModalProductChange()">
        ${products.map(pr => `<option value="${pr.id}">${pr.name} (Base: ₹${pr.sales_price})</option>`).join('')}
      </select>
    </div>
    <div class="form-group">
      <label>Product Variant (e.g. Brand: Odoo +₹560)</label>
      <select id="modalVariantId" class="form-control" onchange="updateModalPricePreview()">
        <!-- Filled dynamically -->
      </select>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Quantity</label>
        <input type="number" id="modalQty" class="form-control" min="1" value="1" oninput="updateModalPricePreview()">
      </div>
      <div class="form-group">
        <label>Promo Discount Code</label>
        <input type="text" id="modalDiscountCode" class="form-control" placeholder="e.g. FLUX10">
      </div>
    </div>
    <div style="background:#f8fafc; padding:12px; border-radius:8px; border:1px solid var(--border);">
      <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
        <span>Unit Price (Base + Variant):</span>
        <strong id="previewUnitPrice">₹0.00</strong>
      </div>
      <div style="display:flex; justify-content:space-between;">
        <span>Estimated Total (incl. 18% GST):</span>
        <strong id="previewEstTotal" style="color:var(--primary); font-size:15px;">₹0.00</strong>
      </div>
    </div>
  `;

  const footerHtml = `
    <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
    <button class="btn btn-primary" onclick="submitCreateSubscription()">Create Subscription</button>
  `;

  openModal("Create New Subscription", bodyHtml, footerHtml);
  onModalProductChange();
}

function onModalProductChange() {
  const prodId = parseInt(document.getElementById("modalProdId").value);
  const prod = state.productsCache.find(p => p.id === prodId);
  const variantSelect = document.getElementById("modalVariantId");

  if (!prod || !prod.variants || prod.variants.length === 0) {
    variantSelect.innerHTML = `<option value="">Standard (No additional variant)</option>`;
  } else {
    variantSelect.innerHTML = `
      <option value="">Standard (No additional variant)</option>
      ${prod.variants.map(v => `
        <option value="${v.id}" data-add="${v.additional_price}">
          ${v.attribute_name}: ${v.attribute_value} (+₹${v.additional_price})
        </option>
      `).join('')}
    `;
  }
  updateModalPricePreview();
}

function updateModalPricePreview() {
  const prodId = parseInt(document.getElementById("modalProdId").value);
  const prod = state.productsCache.find(p => p.id === prodId);
  if (!prod) return;

  const variantSelect = document.getElementById("modalVariantId");
  const selectedOpt = variantSelect.options[variantSelect.selectedIndex];
  const addPrice = selectedOpt ? parseFloat(selectedOpt.getAttribute("data-add") || 0) : 0;
  const qty = parseInt(document.getElementById("modalQty").value || 1);

  const unitTotal = prod.sales_price + addPrice;
  const subtotal = unitTotal * qty;
  const tax = subtotal * 0.18;
  const estGrandTotal = subtotal + tax;

  document.getElementById("previewUnitPrice").innerText = `₹${unitTotal.toFixed(2)}`;
  document.getElementById("previewEstTotal").innerText = `₹${estGrandTotal.toFixed(2)}`;
}

async function submitCreateSubscription() {
  const customer_id = parseInt(document.getElementById("modalCustId").value);
  const plan_id = parseInt(document.getElementById("modalPlanId").value);
  const product_id = parseInt(document.getElementById("modalProdId").value);
  const variant_id = document.getElementById("modalVariantId").value ? parseInt(document.getElementById("modalVariantId").value) : null;
  const quantity = parseInt(document.getElementById("modalQty").value);
  const discount_code = document.getElementById("modalDiscountCode").value.trim() || null;

  try {
    const newSub = await api("/subscriptions", {
      method: "POST",
      body: JSON.stringify({
        customer_id,
        plan_id,
        discount_code,
        lines: [{
          product_id,
          variant_id,
          quantity
        }]
      })
    });
    showToast(`Subscription ${newSub.subscription_number} created successfully!`);
    closeModal();
    if (state.currentRoute === "subscriptions") renderSubscriptions();
    else renderDashboard();
  } catch (err) {
    console.error(err);
  }
}

// VIEW 3: INVOICES & BILLING
async function renderInvoices() {
  document.getElementById("pageTitle").innerText = "Invoices & Billing Management";
  const container = document.getElementById("mainContainer");
  container.innerHTML = `<div class="empty-state"><div class="empty-title">Fetching invoices...</div></div>`;

  try {
    const invs = await api("/invoices");
    container.innerHTML = `
      <div class="table-wrapper">
        <div class="table-toolbar">
          <input type="text" id="invSearch" class="search-input" placeholder="Search invoices..." oninput="filterInvoicesTable()">
          <select id="invStatusFilter" class="filter-select" onchange="filterInvoicesTable()">
            <option value="">All Invoices</option>
            <option value="draft">Draft</option>
            <option value="confirmed">Confirmed</option>
            <option value="paid">Paid</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>
        <table>
          <thead>
            <tr>
              <th>Invoice #</th>
              <th>Customer</th>
              <th>Status</th>
              <th>Due Date</th>
              <th>Grand Total</th>
              <th>Amount Due</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody id="invoicesTbody">
            ${invs.map(i => `
              <tr data-num="${i.invoice_number.toLowerCase()}" data-cust="${(i.customer_name || '').toLowerCase()}" data-status="${i.status}">
                <td><strong>${i.invoice_number}</strong></td>
                <td>
                  <div>${i.customer_name}</div>
                  <small style="color:var(--text-muted);">${i.customer_email}</small>
                </td>
                <td><span class="badge badge-${i.status}">${i.status}</span></td>
                <td>${i.due_date}</td>
                <td>₹${i.total_amount.toFixed(2)}</td>
                <td style="font-weight:700; color:${i.amount_due > 0 ? 'var(--danger)' : 'var(--success)'};">
                  ₹${i.amount_due.toFixed(2)}
                </td>
                <td>
                  <div style="display:flex; gap:6px;">
                    <button class="btn btn-secondary btn-sm" onclick="downloadInvoicePdf(${i.id}, '${i.invoice_number}')">PDF</button>
                    ${i.amount_due > 0 && i.status !== 'cancelled' ? `
                      <button class="btn btn-primary btn-sm" onclick="openPaymentModal(${i.id}, ${i.amount_due})">Pay</button>
                    ` : ''}
                    ${(state.user.role !== 'customer' && i.status === 'draft') ? `
                      <button class="btn btn-success btn-sm" onclick="confirmInvoice(${i.id})">Confirm</button>
                    ` : ''}
                    ${(state.user.role !== 'customer' && i.status !== 'cancelled' && i.amount_paid === 0) ? `
                      <button class="btn btn-danger btn-sm" onclick="cancelInvoice(${i.id})">Cancel</button>
                    ` : ''}
                  </div>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
  } catch (err) {
    console.error(err);
  }
}

function filterInvoicesTable() {
  const query = document.getElementById("invSearch").value.toLowerCase();
  const filter = document.getElementById("invStatusFilter").value;
  const rows = document.querySelectorAll("#invoicesTbody tr");
  rows.forEach(r => {
    const num = r.getAttribute("data-num");
    const cust = r.getAttribute("data-cust");
    const st = r.getAttribute("data-status");
    r.style.display = ((!query || num.includes(query) || cust.includes(query)) && (!filter || st === filter)) ? "" : "none";
  });
}

async function downloadInvoicePdf(invId, invNumber) {
  try {
    const blob = await api(`/invoices/${invId}/pdf`);
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Invoice_${invNumber}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    showToast("Invoice PDF downloaded!");
  } catch (err) {
    console.error(err);
  }
}

async function confirmInvoice(invId) {
  try {
    await api(`/invoices/${invId}/confirm`, { method: "PUT" });
    showToast("Invoice confirmed!");
    renderInvoices();
  } catch (err) {
    console.error(err);
  }
}

async function cancelInvoice(invId) {
  if (!confirm("Are you sure you want to cancel this invoice?")) return;
  try {
    await api(`/invoices/${invId}/cancel`, { method: "PUT" });
    showToast("Invoice cancelled.");
    renderInvoices();
  } catch (err) {
    console.error(err);
  }
}

// VIEW 4: PAYMENTS
async function renderPayments() {
  document.getElementById("pageTitle").innerText = "Payments & Transactions";
  const container = document.getElementById("mainContainer");
  container.innerHTML = `<div class="empty-state"><div class="empty-title">Loading payments...</div></div>`;

  try {
    const payments = await api("/payments");
    container.innerHTML = `
      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Reference</th>
              <th>Invoice #</th>
              <th>Customer</th>
              <th>Method</th>
              <th>Amount</th>
              <th>Date</th>
            </tr>
          </thead>
          <tbody>
            ${payments.length === 0 ? '<tr><td colspan="6" style="text-align:center;">No payment records found.</td></tr>' :
              payments.map(p => `
                <tr>
                  <td><strong>${p.payment_reference}</strong></td>
                  <td>${p.invoice_number || 'N/A'}</td>
                  <td>${p.customer_name}</td>
                  <td><span class="badge badge-draft">${p.payment_method.toUpperCase()}</span></td>
                  <td><strong>₹${p.amount.toFixed(2)}</strong></td>
                  <td>${new Date(p.payment_date).toLocaleString()}</td>
                </tr>
              `).join('')}
          </tbody>
        </table>
      </div>
    `;
  } catch (err) {
    console.error(err);
  }
}

// Modal: Payment Recording with Overpayment Guard
function openPaymentModal(invoiceId, amountDue) {
  const bodyHtml = `
    <input type="hidden" id="payInvId" value="${invoiceId}">
    <div class="form-group">
      <label>Outstanding Balance</label>
      <input class="form-control" value="₹${amountDue.toFixed(2)}" disabled>
    </div>
    <div class="form-group">
      <label>Payment Method</label>
      <select id="payMethod" class="form-control">
        <option value="upi">UPI</option>
        <option value="card">Card</option>
        <option value="bank_transfer">Bank Transfer</option>
        <option value="cash">Cash</option>
      </select>
    </div>
    <div class="form-group">
      <label>Amount to Pay (Partial allowed, Overpayment blocked)</label>
      <input type="number" step="0.01" id="payAmount" class="form-control" max="${amountDue}" value="${amountDue}">
    </div>
    <div class="form-group">
      <label>Notes / Transaction Reference</label>
      <input type="text" id="payNotes" class="form-control" placeholder="Bank ref, UTR or approval note">
    </div>
  `;

  const footerHtml = `
    <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
    <button class="btn btn-primary" onclick="submitRecordPayment(${amountDue})">Confirm & Settle</button>
  `;

  openModal("Record Payment", bodyHtml, footerHtml);
}

async function submitRecordPayment(maxDue) {
  const invoice_id = parseInt(document.getElementById("payInvId").value);
  const payment_method = document.getElementById("payMethod").value;
  const amount = parseFloat(document.getElementById("payAmount").value);
  const notes = document.getElementById("payNotes").value;

  if (amount > maxDue) {
    showToast(`Payment exceeds due balance of ₹${maxDue.toFixed(2)}!`, "error");
    return;
  }

  try {
    const res = await api("/payments", {
      method: "POST",
      body: JSON.stringify({ invoice_id, payment_method, amount, notes })
    });
    showToast(`Payment ${res.payment_reference} recorded successfully!`);
    closeModal();
    if (state.currentRoute === "invoices") renderInvoices();
    else if (state.currentRoute === "dashboard") renderDashboard();
    else renderPayments();
  } catch (err) {
    console.error(err);
  }
}

// VIEW 5: PRODUCTS & VARIANTS
async function renderProducts() {
  document.getElementById("pageTitle").innerText = "Products & Catalog";
  const actions = document.getElementById("topbarActions");
  actions.innerHTML = `<button class="btn btn-primary" onclick="openCreateProductModal()">+ Add Product</button>`;

  const container = document.getElementById("mainContainer");
  container.innerHTML = `<div class="empty-state"><div class="empty-title">Loading catalog...</div></div>`;

  try {
    const products = await api("/products");
    container.innerHTML = `
      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Product Name</th>
              <th>Type</th>
              <th>Base Price</th>
              <th>Cost</th>
              <th>Configured Variants</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            ${products.map(p => `
              <tr>
                <td><strong>${p.name}</strong></td>
                <td><span class="badge badge-draft">${p.product_type}</span></td>
                <td><strong>₹${p.sales_price.toFixed(2)}</strong></td>
                <td>₹${p.cost_price.toFixed(2)}</td>
                <td>
                  ${p.variants.length === 0 ? '<span style="color:var(--text-muted); font-size:12px;">Standard only</span>' :
                    p.variants.map(v => `<span class="badge badge-quotation" style="margin-right:4px;">${v.attribute_name}: ${v.attribute_value} (+₹${v.additional_price})</span>`).join('')}
                </td>
                <td>
                  <button class="btn btn-secondary btn-sm" onclick="openAddVariantModal(${p.id}, '${p.name}')">+ Variant</button>
                  <button class="btn btn-danger btn-sm" onclick="deleteProduct(${p.id})">Delete</button>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
  } catch (err) {
    console.error(err);
  }
}

function openCreateProductModal() {
  const bodyHtml = `
    <div class="form-group">
      <label>Product Name</label>
      <input type="text" id="newProdName" class="form-control" required placeholder="Enterprise Software Suite">
    </div>
    <div class="form-group">
      <label>Type</label>
      <select id="newProdType" class="form-control">
        <option value="Software">Software</option>
        <option value="Service">Service</option>
        <option value="Infrastructure">Infrastructure</option>
      </select>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Sales Price (₹)</label>
        <input type="number" id="newProdSalesPrice" class="form-control" step="0.01" required value="1000">
      </div>
      <div class="form-group">
        <label>Cost Price (₹)</label>
        <input type="number" id="newProdCostPrice" class="form-control" step="0.01" value="400">
      </div>
    </div>
    <div class="form-group">
      <label>Notes</label>
      <textarea id="newProdNotes" class="form-control" rows="2"></textarea>
    </div>
  `;

  const footerHtml = `
    <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
    <button class="btn btn-primary" onclick="submitCreateProduct()">Save Product</button>
  `;

  openModal("Add New Product", bodyHtml, footerHtml);
}

async function submitCreateProduct() {
  const name = document.getElementById("newProdName").value;
  const product_type = document.getElementById("newProdType").value;
  const sales_price = parseFloat(document.getElementById("newProdSalesPrice").value);
  const cost_price = parseFloat(document.getElementById("newProdCostPrice").value);
  const notes = document.getElementById("newProdNotes").value;

  try {
    await api("/products", {
      method: "POST",
      body: JSON.stringify({ name, product_type, sales_price, cost_price, notes, variants: [] })
    });
    showToast("Product created!");
    closeModal();
    renderProducts();
  } catch (err) {
    console.error(err);
  }
}

function openAddVariantModal(productId, productName) {
  const bodyHtml = `
    <p style="font-size:13px; color:var(--text-muted); margin-bottom:12px;">Add variant for: <strong>${productName}</strong></p>
    <div class="form-group">
      <label>Attribute Name (e.g. Brand, Tier, Storage)</label>
      <input type="text" id="varAttrName" class="form-control" placeholder="Brand" value="Brand">
    </div>
    <div class="form-group">
      <label>Attribute Value (e.g. Odoo, Pro, 500GB)</label>
      <input type="text" id="varAttrVal" class="form-control" placeholder="Odoo" value="Odoo">
    </div>
    <div class="form-group">
      <label>Additional Price (₹) (e.g. 560 for Odoo)</label>
      <input type="number" step="0.01" id="varAddPrice" class="form-control" placeholder="560" value="560">
    </div>
  `;

  const footerHtml = `
    <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
    <button class="btn btn-primary" onclick="submitAddVariant(${productId})">Attach Variant</button>
  `;

  openModal("Add Product Variant", bodyHtml, footerHtml);
}

async function submitAddVariant(productId) {
  const attribute_name = document.getElementById("varAttrName").value;
  const attribute_value = document.getElementById("varAttrVal").value;
  const additional_price = parseFloat(document.getElementById("varAddPrice").value || 0);

  try {
    await api(`/products/${productId}/variants`, {
      method: "POST",
      body: JSON.stringify({ attribute_name, attribute_value, additional_price })
    });
    showToast("Variant added successfully!");
    closeModal();
    renderProducts();
  } catch (err) {
    console.error(err);
  }
}

async function deleteProduct(productId) {
  if (!confirm("Are you sure you want to delete or deactivate this product?")) return;
  try {
    const res = await api(`/products/${productId}`, { method: "DELETE" });
    showToast(res.message);
    renderProducts();
  } catch (err) {
    console.error(err);
  }
}

// VIEW 6: PLANS
async function renderPlans() {
  document.getElementById("pageTitle").innerText = "Subscription Plans";
  const actions = document.getElementById("topbarActions");
  actions.innerHTML = `<button class="btn btn-primary" onclick="openCreatePlanModal()">+ New Plan</button>`;

  const container = document.getElementById("mainContainer");
  container.innerHTML = `<div class="empty-state"><div class="empty-title">Loading plans...</div></div>`;

  try {
    const plans = await api("/plans");
    container.innerHTML = `
      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Plan Name</th>
              <th>Code</th>
              <th>Recurrence</th>
              <th>Base Price</th>
              <th>Interval</th>
              <th>Lifecycle Rules</th>
            </tr>
          </thead>
          <tbody>
            ${plans.map(p => `
              <tr>
                <td><strong>${p.name}</strong></td>
                <td><code>${p.code}</code></td>
                <td><span class="badge badge-quotation">${p.recurrence.toUpperCase()}</span></td>
                <td><strong>₹${p.price.toFixed(2)}</strong></td>
                <td>${p.billing_interval_days} days</td>
                <td>
                  <div style="font-size:12px;">
                    ${p.allow_pause ? '✓ Pause ' : '✕ No-Pause '}
                    ${p.allow_renewal ? '✓ Renewal ' : '✕ No-Renewal '}
                    ${p.allow_early_closure ? '✓ Early Closure' : '✕ Fixed Term'}
                  </div>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
  } catch (err) {
    console.error(err);
  }
}

function openCreatePlanModal() {
  const bodyHtml = `
    <div class="form-group">
      <label>Plan Name</label>
      <input type="text" id="planName" class="form-control" required placeholder="Growth Monthly Plan">
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Plan Code</label>
        <input type="text" id="planCode" class="form-control" required placeholder="PLAN-GROWTH">
      </div>
      <div class="form-group">
        <label>Recurrence</label>
        <select id="planRecurrence" class="form-control">
          <option value="daily">Daily</option>
          <option value="weekly">Weekly</option>
          <option value="monthly" selected>Monthly</option>
          <option value="yearly">Yearly</option>
        </select>
      </div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Plan Price (₹)</label>
        <input type="number" id="planPrice" class="form-control" value="2500">
      </div>
      <div class="form-group">
        <label>Billing Interval (Days)</label>
        <input type="number" id="planInterval" class="form-control" value="30">
      </div>
    </div>
  `;

  const footerHtml = `
    <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
    <button class="btn btn-primary" onclick="submitCreatePlan()">Create Plan</button>
  `;

  openModal("Create Subscription Plan", bodyHtml, footerHtml);
}

async function submitCreatePlan() {
  const name = document.getElementById("planName").value;
  const code = document.getElementById("planCode").value;
  const recurrence = document.getElementById("planRecurrence").value;
  const price = parseFloat(document.getElementById("planPrice").value);
  const billing_interval_days = parseInt(document.getElementById("planInterval").value);

  try {
    await api("/plans", {
      method: "POST",
      body: JSON.stringify({ name, code, recurrence, price, billing_interval_days })
    });
    showToast("Plan created successfully!");
    closeModal();
    renderPlans();
  } catch (err) {
    console.error(err);
  }
}

// VIEW 7: DISCOUNTS
async function renderDiscounts() {
  document.getElementById("pageTitle").innerText = "Discounts & Promotional Rules";
  const actions = document.getElementById("topbarActions");
  actions.innerHTML = `<button class="btn btn-primary" onclick="openCreateDiscountModal()">+ New Discount</button>`;

  const container = document.getElementById("mainContainer");
  container.innerHTML = `<div class="empty-state"><div class="empty-title">Loading discounts...</div></div>`;

  try {
    const discounts = await api("/discounts");
    container.innerHTML = `
      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Promo Code</th>
              <th>Description</th>
              <th>Type & Value</th>
              <th>Min Spend</th>
              <th>Usage Count</th>
              <th>Active</th>
            </tr>
          </thead>
          <tbody>
            ${discounts.map(d => `
              <tr>
                <td><strong><code>${d.code}</code></strong></td>
                <td>${d.description || 'Promotional Discount'}</td>
                <td>
                  <span class="badge badge-active">
                    ${d.discount_type === 'percentage' ? `${d.value}% Off` : `₹${d.value} Flat`}
                  </span>
                </td>
                <td>₹${d.min_purchase_amount}</td>
                <td>${d.times_used} ${d.max_usage_limit ? `/ ${d.max_usage_limit}` : ''}</td>
                <td>${d.is_active ? '✓ Active' : '✕ Disabled'}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
  } catch (err) {
    console.error(err);
  }
}

function openCreateDiscountModal() {
  const bodyHtml = `
    <div class="form-row">
      <div class="form-group">
        <label>Discount Code</label>
        <input type="text" id="discCode" class="form-control" placeholder="FLUX20" required>
      </div>
      <div class="form-group">
        <label>Type</label>
        <select id="discType" class="form-control">
          <option value="percentage">Percentage (%)</option>
          <option value="fixed">Fixed Amount (₹)</option>
        </select>
      </div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Discount Value</label>
        <input type="number" id="discVal" class="form-control" value="20" required>
      </div>
      <div class="form-group">
        <label>Minimum Purchase Amount (₹)</label>
        <input type="number" id="discMinSpend" class="form-control" value="1000">
      </div>
    </div>
    <div class="form-group">
      <label>Description</label>
      <input type="text" id="discDesc" class="form-control" placeholder="Seasonal festival offer">
    </div>
  `;

  const footerHtml = `
    <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
    <button class="btn btn-primary" onclick="submitCreateDiscount()">Save Discount</button>
  `;

  openModal("Add Promotional Discount", bodyHtml, footerHtml);
}

async function submitCreateDiscount() {
  const code = document.getElementById("discCode").value;
  const discount_type = document.getElementById("discType").value;
  const value = parseFloat(document.getElementById("discVal").value);
  const min_purchase_amount = parseFloat(document.getElementById("discMinSpend").value);
  const description = document.getElementById("discDesc").value;

  try {
    await api("/discounts", {
      method: "POST",
      body: JSON.stringify({ code, discount_type, value, min_purchase_amount, description })
    });
    showToast("Discount created!");
    closeModal();
    renderDiscounts();
  } catch (err) {
    console.error(err);
  }
}

// VIEW 8: CUSTOMERS DIRECTORY
async function renderCustomers() {
  document.getElementById("pageTitle").innerText = "Customers Directory";
  const actions = document.getElementById("topbarActions");
  actions.innerHTML = `<button class="btn btn-primary" onclick="openCreateCustomerModal()">+ New Customer</button>`;

  const container = document.getElementById("mainContainer");
  container.innerHTML = `<div class="empty-state"><div class="empty-title">Loading customers...</div></div>`;

  try {
    const customers = await api("/customers");
    container.innerHTML = `
      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Company</th>
              <th>Phone</th>
              <th>GST / Tax ID</th>
            </tr>
          </thead>
          <tbody>
            ${customers.map(c => `
              <tr>
                <td><strong>${c.name}</strong></td>
                <td>${c.email}</td>
                <td>${c.company || 'Individual'}</td>
                <td>${c.phone || 'N/A'}</td>
                <td><code>${c.tax_number || 'N/A'}</code></td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
  } catch (err) {
    console.error(err);
  }
}

function openCreateCustomerModal() {
  const bodyHtml = `
    <div class="form-group">
      <label>Customer Name</label>
      <input type="text" id="cName" class="form-control" required placeholder="Anita Desai">
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Email Address</label>
        <input type="email" id="cEmail" class="form-control" required placeholder="anita@company.com">
      </div>
      <div class="form-group">
        <label>Phone</label>
        <input type="text" id="cPhone" class="form-control" placeholder="+91 99999 88888">
      </div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Company</label>
        <input type="text" id="cCompany" class="form-control" placeholder="Desai Logistics">
      </div>
      <div class="form-group">
        <label>Tax / GST Number</label>
        <input type="text" id="cTax" class="form-control" placeholder="09ABCDE1234F1Z5">
      </div>
    </div>
  `;

  const footerHtml = `
    <button class="btn btn-secondary" onclick="closeModal()">Cancel</button>
    <button class="btn btn-primary" onclick="submitCreateCustomer()">Create Customer</button>
  `;

  openModal("Add Customer", bodyHtml, footerHtml);
}

async function submitCreateCustomer() {
  const name = document.getElementById("cName").value;
  const email = document.getElementById("cEmail").value;
  const phone = document.getElementById("cPhone").value;
  const company = document.getElementById("cCompany").value;
  const tax_number = document.getElementById("cTax").value;

  try {
    await api("/customers", {
      method: "POST",
      body: JSON.stringify({ name, email, phone, company, tax_number })
    });
    showToast("Customer created successfully!");
    closeModal();
    renderCustomers();
  } catch (err) {
    console.error(err);
  }
}

// Initializer
function initApp() {
  if (state.token && state.user) {
    document.getElementById("authView").style.display = "none";
    document.getElementById("appView").style.display = "flex";
    updateRoleUI();
    navigate("dashboard");
  } else {
    document.getElementById("authView").style.display = "flex";
    document.getElementById("appView").style.display = "none";
  }
}

// Start app on DOM load
document.addEventListener("DOMContentLoaded", initApp);
