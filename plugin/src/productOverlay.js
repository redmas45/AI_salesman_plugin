import { config } from "./config";

const PLACEHOLDER_IMAGE = "https://demo.vercel.store/placeholder.png";

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function normalizeProduct(raw) {
  if (!raw) return null;
  const id = String(raw.id || raw.product_id || "").trim();
  const name = String(raw.name || raw.title || "Untitled product").trim();
  const price = Number(raw.price || 0);
  if (!id || !name) return null;

  return {
    id,
    name,
    brand: raw.brand || raw.vendor || "Unknown Brand",
    category: raw.category || raw.category_name || "Products",
    description: raw.description || "",
    price: Number.isFinite(price) ? price : 0,
    imageUrl: raw.image_url || raw.image || raw.thumbnail || "",
  };
}

function ensureStyles() {
  if (document.getElementById("shopbot-product-overlay-styles")) return;

  const style = document.createElement("style");
  style.id = "shopbot-product-overlay-styles";
  style.textContent = `
    #shopbot-product-panel {
      position: fixed;
      left: 50%;
      bottom: 96px;
      z-index: 2147483638;
      width: min(calc(100vw - 32px), var(--shopbot-panel-width, 720px));
      max-height: min(72vh, var(--shopbot-panel-max-height, 560px));
      transform: translate(-50%, calc(100% + 32px));
      opacity: 0;
      pointer-events: none;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      border: 1px solid rgba(22, 22, 21, 0.12);
      border-radius: 8px;
      background: rgba(247, 247, 243, 0.97);
      box-shadow: 0 24px 70px rgba(22, 22, 21, 0.18);
      color: #161615;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      transition: transform 0.26s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.2s ease;
    }
    #shopbot-product-panel.active {
      transform: translate(-50%, 0);
      opacity: 1;
      pointer-events: auto;
    }
    #shopbot-product-panel.count-1 { --shopbot-panel-width: 360px; --shopbot-panel-max-height: 470px; }
    #shopbot-product-panel.count-2 { --shopbot-panel-width: 600px; --shopbot-panel-max-height: 500px; }
    #shopbot-product-panel.count-3 { --shopbot-panel-width: 860px; --shopbot-panel-max-height: 520px; }
    #shopbot-product-panel.count-many { --shopbot-panel-width: 980px; --shopbot-panel-max-height: 620px; }
    .shopbot-product-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
      padding: 14px 16px;
      border-bottom: 1px solid rgba(22, 22, 21, 0.1);
    }
    .shopbot-product-title {
      margin: 0;
      color: #161615;
      font-size: 15px;
      font-weight: 800;
      line-height: 1.25;
      letter-spacing: 0;
    }
    .shopbot-product-close {
      display: grid;
      place-items: center;
      width: 34px;
      height: 34px;
      flex: 0 0 auto;
      border: 1px solid rgba(22, 22, 21, 0.14);
      border-radius: 8px;
      background: #ffffff;
      color: #161615;
      cursor: pointer;
      font-size: 20px;
      line-height: 1;
    }
    .shopbot-product-grid {
      display: grid;
      grid-template-columns: repeat(var(--shopbot-card-count, 2), minmax(0, 1fr));
      gap: 12px;
      padding: 14px;
      overflow: auto;
      scrollbar-width: thin;
    }
    .shopbot-product-card {
      display: grid;
      grid-template-rows: auto auto auto 1fr;
      gap: 9px;
      min-width: 0;
      border: 1px solid rgba(22, 22, 21, 0.1);
      border-radius: 8px;
      background: #ffffff;
      padding: 12px;
    }
    .shopbot-product-image {
      width: 100%;
      height: clamp(132px, 18vw, 178px);
      object-fit: contain;
      border-radius: 8px;
      background: #f1f2ee;
      padding: 8px;
      mix-blend-mode: multiply;
    }
    .shopbot-product-name {
      margin: 0;
      min-height: 38px;
      color: #161615;
      font-size: 14px;
      font-weight: 760;
      line-height: 1.35;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    .shopbot-product-meta {
      margin: 0;
      color: #686660;
      font-size: 13px;
      line-height: 1.35;
      overflow-wrap: anywhere;
    }
    .shopbot-product-actions {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
      align-self: end;
      margin-top: 2px;
    }
    .shopbot-product-actions button {
      min-height: 36px;
      border: 1px solid rgba(22, 22, 21, 0.12);
      border-radius: 8px;
      background: #161615;
      color: #ffffff;
      cursor: pointer;
      font-size: 12px;
      font-weight: 760;
      line-height: 1;
    }
    .shopbot-product-actions button.secondary {
      background: #ffffff;
      color: #161615;
    }
    .shopbot-product-empty {
      margin: 0;
      padding: 14px;
      color: #686660;
      font-size: 14px;
    }
    @media (max-width: 720px) {
      #shopbot-product-panel {
        bottom: 86px;
        width: min(calc(100vw - 20px), 520px);
      }
      #shopbot-product-panel.count-2,
      #shopbot-product-panel.count-3,
      #shopbot-product-panel.count-many {
        --shopbot-card-count: 2;
      }
      .shopbot-product-grid {
        padding: 12px;
      }
      .shopbot-product-image {
        height: clamp(118px, 32vw, 150px);
      }
    }
    @media (max-width: 430px) {
      #shopbot-product-panel {
        bottom: 82px;
      }
      #shopbot-product-panel.count-1,
      #shopbot-product-panel.count-2,
      #shopbot-product-panel.count-3,
      #shopbot-product-panel.count-many {
        --shopbot-card-count: 1;
      }
    }
  `;
  document.head.appendChild(style);
}

function ensurePanel() {
  ensureStyles();

  let panel = document.getElementById("shopbot-product-panel");
  if (panel) return panel;

  panel = document.createElement("div");
  panel.id = "shopbot-product-panel";
  panel.setAttribute("aria-live", "polite");
  panel.innerHTML = `
    <div class="shopbot-product-header">
      <h2 class="shopbot-product-title">Recommended products</h2>
      <button class="shopbot-product-close" type="button" aria-label="Close recommendations">&times;</button>
    </div>
    <div class="shopbot-product-grid"></div>
  `;
  panel.querySelector(".shopbot-product-close").addEventListener("click", () => {
    panel.classList.remove("active");
  });
  document.body.appendChild(panel);
  return panel;
}

async function fetchProductsByIds(productIds) {
  const ids = (Array.isArray(productIds) ? productIds : [])
    .map((id) => String(id || "").trim())
    .filter(Boolean);
  if (!ids.length) return [];

  const url = new URL("/v1/products/by-ids", config.apiUrl);
  url.searchParams.set("site_id", config.siteId);
  url.searchParams.set("ids", ids.join(","));

  const response = await fetch(url.toString(), { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error("Failed to fetch recommended products");

  const products = (await response.json()).map(normalizeProduct).filter(Boolean);
  const byId = new Map(products.map((product) => [String(product.id), product]));
  return ids.map((id) => byId.get(String(id))).filter(Boolean);
}

async function requestAddToCart(productId) {
  const cart = window.ShopCart;
  if (cart && typeof cart.addItem === "function") {
    await cart.addItem(productId, 1);
    if (typeof cart.open === "function") cart.open();
    return;
  }

  const detail = {
    action: "ADD_TO_CART",
    params: { product_id: productId, quantity: 1 },
    parameters: { product_id: productId, quantity: 1 },
  };
  window.dispatchEvent(new CustomEvent("shopbot:action", { detail }));
}

async function requestProductDetail(productId) {
  const cart = window.ShopCart;
  if (cart && typeof cart.showProductDetail === "function") {
    await cart.showProductDetail(productId);
    return;
  }

  const detail = {
    action: "SHOW_PRODUCT_DETAIL",
    params: { product_id: productId },
    parameters: { product_id: productId },
  };
  window.dispatchEvent(new CustomEvent("shopbot:action", { detail }));
}

function countClass(count) {
  if (count <= 1) return "count-1";
  if (count === 2) return "count-2";
  if (count === 3) return "count-3";
  return "count-many";
}

function cardCount(count) {
  if (count <= 1) return 1;
  if (count === 2) return 2;
  return 3;
}

function renderProducts(products, title) {
  const panel = ensurePanel();
  const grid = panel.querySelector(".shopbot-product-grid");
  const heading = panel.querySelector(".shopbot-product-title");
  const count = products.length;

  panel.classList.remove("count-1", "count-2", "count-3", "count-many");
  panel.classList.add(countClass(count));
  panel.style.setProperty("--shopbot-card-count", String(cardCount(count)));
  heading.textContent = title || "Recommended products";

  if (!count) {
    grid.innerHTML = `<p class="shopbot-product-empty">No matching products are currently available.</p>`;
    panel.classList.add("active");
    collapseVoiceBubble();
    return;
  }

  grid.innerHTML = products
    .map((product) => {
      const safeId = escapeHtml(product.id);
      return `
        <article class="shopbot-product-card" data-product-id="${safeId}">
          <img class="shopbot-product-image" src="${escapeHtml(product.imageUrl || PLACEHOLDER_IMAGE)}" alt="${escapeHtml(product.name)}">
          <h3 class="shopbot-product-name">${escapeHtml(product.name)}</h3>
          <p class="shopbot-product-meta">${escapeHtml(product.brand)} - $${Number(product.price || 0).toFixed(2)} USD</p>
          <div class="shopbot-product-actions">
            <button type="button" data-add="${safeId}">Add</button>
            <button type="button" class="secondary" data-view="${safeId}">View</button>
          </div>
        </article>
      `;
    })
    .join("");

  grid.querySelectorAll("[data-add]").forEach((button) => {
    button.addEventListener("click", async () => {
      await requestAddToCart(button.getAttribute("data-add"));
    });
  });
  grid.querySelectorAll("[data-view]").forEach((button) => {
    button.addEventListener("click", async () => {
      await requestProductDetail(button.getAttribute("data-view"));
    });
  });

  panel.classList.add("active");
  collapseVoiceBubble();
}

function collapseVoiceBubble() {
  window.setTimeout(() => {
    const chat = document.getElementById("shopbot-chat");
    const messages = document.getElementById("shopbot-msgs");
    if (messages) messages.innerHTML = "";
    if (chat) chat.classList.remove("visible");
  }, 180);
}

export async function showProductOverlay(productIds, title = "Recommended products") {
  try {
    const products = await fetchProductsByIds(productIds);
    renderProducts(products, title);
    return true;
  } catch (err) {
    console.warn("[ShopBot] Product overlay failed:", err);
    renderProducts([], title);
    return true;
  }
}
