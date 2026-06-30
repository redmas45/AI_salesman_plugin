import { fetchHubProductsByIds, resolveProductDetailUrl } from "./productResolver";
import { executeWithAIHubAdapter, hasAIHubAdapter } from "./adapterBridge";
import {
  ACTION_PARAMS,
  ACTIONS,
  DEFAULT_CART_QUANTITY,
  DEFAULT_RECOMMENDATION_TITLE,
  EVENTS,
  OVERLAY_COLLAPSE_DELAY_MS,
} from "./constants";

const PLACEHOLDER_IMAGE = [
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='320' height='240' viewBox='0 0 320 240'%3E",
  "%3Crect width='320' height='240' fill='%23f1f2ee'/%3E",
  "%3Cpath d='M98 156h124l-31-40-25 30-17-22-51 32Z' fill='%23c8c3ba'/%3E",
  "%3Ccircle cx='117' cy='95' r='17' fill='%23d8d3ca'/%3E",
  "%3Ctext x='160' y='198' text-anchor='middle' fill='%23686660' font-family='Arial,sans-serif' font-size='16'%3EImage pending%3C/text%3E",
  "%3C/svg%3E",
].join("");
let currentProducts = [];
let currentTitle = DEFAULT_RECOMMENDATION_TITLE;

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
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
      <h2 class="shopbot-product-title">${DEFAULT_RECOMMENDATION_TITLE}</h2>
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
  return fetchHubProductsByIds(productIds);
}

async function requestAddToCart(productId) {
  const detail = {
    action: ACTIONS.ADD_TO_CART,
    params: {
      [ACTION_PARAMS.PRODUCT_ID]: productId,
      [ACTION_PARAMS.QUANTITY]: DEFAULT_CART_QUANTITY,
    },
    parameters: {
      [ACTION_PARAMS.PRODUCT_ID]: productId,
      [ACTION_PARAMS.QUANTITY]: DEFAULT_CART_QUANTITY,
    },
  };

  if (hasAIHubAdapter() && (await executeWithAIHubAdapter(detail))) {
    return;
  }

  window.dispatchEvent(new CustomEvent(EVENTS.SHOPBOT_ACTION, { detail }));
}

async function requestProductDetail(productId) {
  try {
    const productUrl = await resolveProductDetailUrl(productId);
    if (productUrl) {
      window.location.href = productUrl;
      return;
    }
  } catch (error) {
    console.warn("[AI Hub Widget] Product detail URL lookup failed:", error);
  }

  const detail = {
    action: ACTIONS.SHOW_PRODUCT_DETAIL,
    params: { [ACTION_PARAMS.PRODUCT_ID]: productId },
    parameters: { [ACTION_PARAMS.PRODUCT_ID]: productId },
  };
  if (hasAIHubAdapter() && (await executeWithAIHubAdapter(detail))) {
    return;
  }

  window.dispatchEvent(new CustomEvent(EVENTS.SHOPBOT_ACTION, { detail }));
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
  currentProducts = Array.isArray(products) ? [...products] : [];
  currentTitle = title || DEFAULT_RECOMMENDATION_TITLE;

  panel.classList.remove("count-1", "count-2", "count-3", "count-many");
  panel.classList.add(countClass(count));
  panel.style.setProperty("--shopbot-card-count", String(cardCount(count)));
  heading.textContent = currentTitle;

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
  }, OVERLAY_COLLAPSE_DELAY_MS);
}

export async function showProductOverlay(productIds, title = DEFAULT_RECOMMENDATION_TITLE) {
  try {
    const products = await fetchProductsByIds(productIds);
    renderProducts(products, title);
    return true;
  } catch (err) {
    console.warn("[AI Hub Widget] Product overlay failed:", err);
    renderProducts([], title);
    return true;
  }
}

export function sortProductOverlay(params = {}) {
  if (!currentProducts.length) return false;

  const sortBy = String(params.sort_by || params.sortBy || "price_asc").trim().toLowerCase();
  const sorted = [...currentProducts].sort((left, right) => compareProducts(left, right, sortBy));
  renderProducts(sorted, sortedTitle(currentTitle, sortBy));
  return true;
}

function compareProducts(left, right, sortBy) {
  if (sortBy === "price_desc") {
    return numericValue(right.price, Number.NEGATIVE_INFINITY) - numericValue(left.price, Number.NEGATIVE_INFINITY);
  }
  if (sortBy === "rating") {
    return numericValue(right.rating || right.review_rating, Number.NEGATIVE_INFINITY) - numericValue(left.rating || left.review_rating, Number.NEGATIVE_INFINITY);
  }
  if (sortBy === "newest") {
    return productTime(right) - productTime(left);
  }
  return numericValue(left.price, Number.POSITIVE_INFINITY) - numericValue(right.price, Number.POSITIVE_INFINITY);
}

function numericValue(value, fallback) {
  const match = String(value ?? "").replace(/,/g, "").match(/-?\d+(?:\.\d+)?/);
  if (!match) return fallback;
  const number = Number(match[0]);
  return Number.isFinite(number) ? number : fallback;
}

function productTime(product) {
  const raw = product?.updated_at || product?.created_at || product?.date || "";
  const time = Date.parse(String(raw || ""));
  return Number.isFinite(time) ? time : 0;
}

function sortedTitle(title, sortBy) {
  const suffixes = {
    price_asc: "sorted low to high",
    price_desc: "sorted high to low",
    rating: "sorted by rating",
    newest: "newest first",
  };
  const cleanTitle = String(title || DEFAULT_RECOMMENDATION_TITLE).replace(/\s+-\s+sorted.*$/i, "");
  return `${cleanTitle} - ${suffixes[sortBy] || suffixes.price_asc}`;
}
