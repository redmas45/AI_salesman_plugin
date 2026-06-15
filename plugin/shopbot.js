(()=>{function K(){let t=document.createElement("style");t.textContent=`
    #shopbot-widget {
      position: fixed;
      bottom: 20px;
      left: 50%;
      transform: translateX(-50%);
      z-index: 2147483647;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: #161615;
      letter-spacing: 0;
    }
    #shopbot-btn {
      width: 62px;
      height: 62px;
      border-radius: 50%;
      border: 1px solid rgba(22, 22, 21, 0.12);
      background: #161615;
      box-shadow: 0 18px 38px rgba(22, 22, 21, 0.22), inset 0 1px 0 rgba(255, 255, 255, 0.16);
      color: #fff;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: transform 0.22s ease, box-shadow 0.22s ease, background 0.22s ease;
      outline: none;
    }
    #shopbot-btn:hover {
      transform: translateY(-3px);
      box-shadow: 0 22px 46px rgba(22, 22, 21, 0.28), 0 0 0 6px rgba(21, 93, 252, 0.1);
      background: #242421;
    }
    #shopbot-btn.recording {
      background: #a76335;
      animation: shopbotPulse 1.5s infinite cubic-bezier(0.66, 0, 0, 1);
    }
    #shopbot-chat {
      position: absolute;
      bottom: 82px;
      left: 50%;
      transform: translateX(-50%);
      width: min(380px, calc(100vw - 28px));
      max-height: min(520px, calc(100vh - 120px));
      background: rgba(247, 247, 243, 0.96);
      backdrop-filter: blur(18px);
      -webkit-backdrop-filter: blur(18px);
      border: 1px solid rgba(22, 22, 21, 0.12);
      border-radius: 8px;
      box-shadow: 0 24px 72px rgba(22, 22, 21, 0.2);
      padding: 14px;
      display: none;
      flex-direction: column;
      gap: 12px;
      color: #161615;
    }
    #shopbot-chat.visible { display: flex; }
    .shopbot-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding-bottom: 12px;
      border-bottom: 1px solid rgba(22, 22, 21, 0.1);
    }
    .shopbot-header strong {
      display: block;
      color: #161615;
      font-size: 14px;
      line-height: 1.2;
    }
    .shopbot-kicker {
      display: block;
      margin-bottom: 2px;
      color: #a76335;
      font-size: 11px;
      font-weight: 760;
      line-height: 1;
    }
    .shopbot-live-dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: #155dfc;
      box-shadow: 0 0 0 5px rgba(21, 93, 252, 0.12);
      flex: 0 0 auto;
    }
    #shopbot-msgs {
      padding-right: 2px;
      scrollbar-width: none;
      -ms-overflow-style: none;
    }
    #shopbot-msgs::-webkit-scrollbar {
      width: 0;
      height: 0;
      display: none;
    }
    #shopbot-chat:not(.visible) #shopbot-msgs {
      overflow: hidden !important;
    }
    .shopbot-msg {
      max-width: 88%;
      padding: 11px 13px;
      border-radius: 8px;
      font-size: 14px;
      line-height: 1.5;
      overflow-wrap: anywhere;
    }
    .shopbot-msg.user {
      background: #161615;
      color: #fff;
      align-self: flex-end;
      border: 1px solid rgba(22, 22, 21, 0.12);
    }
    .shopbot-msg.ai {
      background: #ffffff;
      color: #161615;
      align-self: flex-start;
      border: 1px solid rgba(22, 22, 21, 0.1);
      box-shadow: 0 8px 20px rgba(22, 22, 21, 0.06);
    }
    #shopbot-status {
      font-size: 12px;
      color: #686660;
      text-align: center;
      min-height: 18px;
      margin-top: 2px;
      transition: color 0.2s ease;
      font-weight: 650;
    }
    #shopbot-status.listening {
      color: #a76335;
      animation: shopbotTextPulse 1.5s infinite ease-in-out;
    }
    #shopbot-status.processing {
      color: #155dfc;
      animation: shopbotTextPulse 1.5s infinite ease-in-out;
    }
    #shopbot-status.ready {
      color: #596652;
    }
    #shopbot-status.error {
      color: #a76335;
    }
    @keyframes shopbotTextPulse {
      0%, 100% { opacity: 0.68; }
      50% { opacity: 1; }
    }
    @keyframes shopbotPulse {
      to { box-shadow: 0 0 0 20px rgba(167, 99, 53, 0); }
    }
    @media (max-width: 520px) {
      #shopbot-widget {
        bottom: 14px;
      }
      #shopbot-btn {
        width: 58px;
        height: 58px;
      }
      #shopbot-chat {
        bottom: 76px;
      }
    }
  `,document.head.appendChild(t)}function X(){let t=document.createElement("div");return t.id="shopbot-widget",t.innerHTML=`
    <div id="shopbot-chat">
      <div class="shopbot-header">
        <div>
          <span class="shopbot-kicker">AI-KART</span>
          <strong>Shopping Assistant</strong>
        </div>
        <span class="shopbot-live-dot" aria-hidden="true"></span>
      </div>
      <div id="shopbot-msgs" style="max-height: 300px; overflow-y: auto; display: flex; flex-direction: column; gap: 8px;"></div>
      <div id="shopbot-status">Ready</div>
    </div>
    <button id="shopbot-btn" aria-label="Voice Assistant">
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
        <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
        <line x1="12" x2="12" y1="19" y2="22"/>
      </svg>
    </button>
  `,document.body.appendChild(t),{btn:document.getElementById("shopbot-btn"),chat:document.getElementById("shopbot-chat"),msgs:document.getElementById("shopbot-msgs"),status:document.getElementById("shopbot-status")}}function y(t,e,o){t.chat.classList.add("visible");let n=document.createElement("div");return n.className=`shopbot-msg ${o}`,n.innerText=e,t.msgs.appendChild(n),t.msgs.scrollTop=t.msgs.scrollHeight,n}function v(t,e,o){e&&(e.innerText=o,t.msgs.scrollTop=t.msgs.scrollHeight)}var i=Object.freeze({ADD_TO_CART:"ADD_TO_CART",CHECKOUT:"CHECKOUT",CLEAR_CART:"CLEAR_CART",FILTER_PRODUCTS:"FILTER_PRODUCTS",NAVIGATE_TO:"NAVIGATE_TO",REMOVE_FROM_CART:"REMOVE_FROM_CART",SHOW_COMPARISON:"SHOW_COMPARISON",SHOW_PRODUCT_DETAIL:"SHOW_PRODUCT_DETAIL",SHOW_PRODUCTS:"SHOW_PRODUCTS",UPDATE_CART_QUANTITY:"UPDATE_CART_QUANTITY"}),a=Object.freeze({PAGE:"page",PRODUCT_ID:"product_id",PRODUCT_IDS:"product_ids",QUANTITY:"quantity",SEARCH_QUERY:"search_query"}),I=new Set(["cart","/cart"]),_="Recommended products",R=Object.freeze({PRODUCTS_BY_IDS:"/v1/products/by-ids",SHOP:"/v1/shop",SHOP_WS:"/v1/ws/shop"}),O=Object.freeze({DATA_WAV_PREFIX:"data:audio/wav;base64,",WEBM_FILENAME:"audio.webm",WEBM_MIME_TYPE:"audio/webm"}),J=Object.freeze({POST:"POST"}),p=Object.freeze({ERROR:"error",PROCESSING:"processing",READY:"ready",RECORDING:"recording"}),L=12,Z=2400,tt=900,et=4200,D=1,ot=180,S=Object.freeze({SHOPBOT_ACTION:"shopbot:action"}),nt=2500,f=Object.freeze({AUDIO_CHUNK:"audio_chunk",AUDIO_END:"audio_end",CONFIG:"config",DONE:"done",ERROR:"error",TEXT_CHUNK:"text_chunk",TRANSCRIPT:"transcript"});function rt(t,e){let o=null,n=[],r=!1;async function c(){try{let w=await navigator.mediaDevices.getUserMedia({audio:!0});o=new MediaRecorder(w),n=[],o.ondataavailable=x=>{x.data.size>0&&n.push(x.data)},o.onstop=async()=>{let x=new Blob(n,{type:O.WEBM_MIME_TYPE});w.getTracks().forEach(u=>u.stop()),await t(x)},o.start(),r=!0,e(p.RECORDING)}catch(w){console.error("Microphone access denied",w),e(p.ERROR)}}function s(){o&&o.state!=="inactive"&&o.stop(),r=!1,e(p.PROCESSING)}function T(){r?s():c()}return{toggle:T}}var E=document.currentScript,st="__AI_PUBLIC_API_URL__",it="__AI_DEFAULT_SITE_ID__";function b(t){return String(t||"").trim()}function _t(){let t=b(E?.getAttribute("src"));if(!t)return null;try{return new URL(t,window.location.href)}catch{return null}}function At(t){return b(E?.getAttribute("data-site-id"))||b(t?.searchParams.get("site"))||b(t?.searchParams.get("site_id"))||b(t?.searchParams.get("shop"))||(it.startsWith("__AI_")?"":it)||"site_1"}function wt(t){let e=b(E?.getAttribute("data-api-url"));return e?e.replace(/\/+$/,""):t?.origin?t.origin.replace(/\/+$/,""):st.startsWith("__AI_")?window.location.origin.replace(/\/+$/,""):st.replace(/\/+$/,"")}var at=_t(),l={siteId:At(at),apiUrl:wt(at),useWebSocket:b(E?.getAttribute("data-use-websocket")).toLowerCase()!=="false",autoGreet:b(E?.getAttribute("data-auto-greet")).toLowerCase()!=="false",brandName:b(E?.getAttribute("data-brand"))||"AI-KART"};var xt=Object.freeze(["/api/products.json","/products.json","/collections/all/products.json"]),Ot=Object.freeze(["products","data","items","results"]),ut=Object.freeze(["id","product_id","handle","sku"]),pt=Object.freeze(["name","title"]),Et=Object.freeze(["url","href","permalink","product_url"]),yt=Object.freeze(["image_url","image","thumbnail","featured_image"]),Rt=Object.freeze(["brand","vendor"]),St=Object.freeze(["category","category_name","product_type"]),Ct=Object.freeze(["description","summary","body_html"]),It="Unknown Brand",Dt="Products",Pt="/product/",Ut="/products/",vt="/",Lt=/^[a-z0-9][a-z0-9-]*$/i,N=null;function m(t){return t==null||typeof t=="object"?"":String(t||"").trim()}function Nt(t){return m(t).toLowerCase().replace(/[^a-z0-9]+/g," ").trim()}function M(t,e){return e.map(o=>m(t?.[o])).filter(Boolean)}function A(t,e){return M(t,e)[0]||""}function Mt(t){let e=A(t,yt);if(e)return e;let o=t?.image||t?.featured_image;return o&&typeof o=="object"?m(o.src||o.url):Array.isArray(t?.images)?m(t.images[0]?.src||t.images[0]?.url||t.images[0]):""}function kt(t){let e=m(t);if(!e)return"";try{let o=new URL(e,window.location.origin);return o.origin!==window.location.origin?"":`${o.pathname}${o.search}${o.hash}`}catch{return""}}function Ht(t){return t==="/products.json"||t.includes("/collections/")?Ut:Pt}function Ft(t,e,o){let n=kt(A(t,Et));return n||(!Lt.test(e)||!/[a-z]/i.test(e)?"":`${Ht(o)}${encodeURIComponent(e)}${vt}`)}function dt(t,e=""){if(!t)return null;let o=A(t,ut),n=m(t.handle||t.slug||t.product_handle),r=A(t,pt),c=Number(t.price||t.amount||t.cost||0);return!o&&!n?null:{id:o,handle:n,name:r,title:m(t.title||r),brand:A(t,Rt)||It,category:A(t,St)||Dt,description:A(t,Ct),price:Number.isFinite(c)?c:0,imageUrl:Mt(t),url:Ft(t,n||o,e)}}function Bt(t){return M(t,ut)}function ct(t){return M(t,pt).map(Nt)}function Gt(t,e){let o=m(e);return!!(o&&Bt(t).includes(o))}function Wt(t,e){let o=new Set(ct(e));return ct(t).some(n=>o.has(n))}function zt(t,e){return!!(t?.imageUrl&&t.imageUrl===e?.imageUrl)}function Yt(t){if(Array.isArray(t))return t;for(let e of Ot){let o=t?.[e];if(Array.isArray(o))return o}return[]}async function jt(t){try{let e=await fetch(new URL(t,window.location.origin),{headers:{Accept:"application/json"}});if(!e.ok)return[];let o=await e.json();return Yt(o).map(n=>dt(n,t)).filter(Boolean)}catch(e){return console.warn(`[ShopBot] Catalog endpoint lookup failed for ${t}:`,e),[]}}async function Vt(){return N||(N=Promise.all(xt.map(jt)).then(t=>t.flat())),N}async function k(t){let e=(Array.isArray(t)?t:[]).map(m).filter(Boolean);if(!e.length)return[];let o=new URL(R.PRODUCTS_BY_IDS,l.apiUrl);o.searchParams.set("site_id",l.siteId),o.searchParams.set("ids",e.join(","));let n=await fetch(o.toString(),{headers:{Accept:"application/json"}});if(!n.ok)throw new Error("Failed to fetch products from ShopBot API");let r=(await n.json()).map(s=>dt(s)).filter(Boolean),c=new Map(r.map(s=>[String(s.id),s]));return e.map(s=>c.get(s)).filter(Boolean)}async function P(t){let e=m(t);if(!e)return"";let[o]=await k([e]);if(o?.url)return o.url;let n=await Vt(),r=n.find(s=>Gt(s,e));return r?.url?r.url:o&&n.find(s=>Wt(s,o)||zt(s,o))?.url||""}var $t="https://demo.vercel.store/placeholder.png";function C(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}function Qt(){if(document.getElementById("shopbot-product-overlay-styles"))return;let t=document.createElement("style");t.id="shopbot-product-overlay-styles",t.textContent=`
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
  `,document.head.appendChild(t)}function qt(){Qt();let t=document.getElementById("shopbot-product-panel");return t||(t=document.createElement("div"),t.id="shopbot-product-panel",t.setAttribute("aria-live","polite"),t.innerHTML=`
    <div class="shopbot-product-header">
      <h2 class="shopbot-product-title">${_}</h2>
      <button class="shopbot-product-close" type="button" aria-label="Close recommendations">&times;</button>
    </div>
    <div class="shopbot-product-grid"></div>
  `,t.querySelector(".shopbot-product-close").addEventListener("click",()=>{t.classList.remove("active")}),document.body.appendChild(t),t)}async function Kt(t){return k(t)}async function Xt(t){let e=window.ShopCart;if(e&&typeof e.addItem=="function"){await e.addItem(t,D),typeof e.open=="function"&&e.open();return}let o={action:i.ADD_TO_CART,params:{[a.PRODUCT_ID]:t,[a.QUANTITY]:D},parameters:{[a.PRODUCT_ID]:t,[a.QUANTITY]:D}};window.dispatchEvent(new CustomEvent(S.SHOPBOT_ACTION,{detail:o}))}async function Jt(t){try{let n=await P(t);if(n){window.location.href=n;return}}catch(n){console.warn("[ShopBot] Product detail URL lookup failed:",n)}let e=window.ShopCart;if(e&&typeof e.showProductDetail=="function"){await e.showProductDetail(t);return}let o={action:i.SHOW_PRODUCT_DETAIL,params:{[a.PRODUCT_ID]:t},parameters:{[a.PRODUCT_ID]:t}};window.dispatchEvent(new CustomEvent(S.SHOPBOT_ACTION,{detail:o}))}function Zt(t){return t<=1?"count-1":t===2?"count-2":t===3?"count-3":"count-many"}function te(t){return t<=1?1:t===2?2:3}function lt(t,e){let o=qt(),n=o.querySelector(".shopbot-product-grid"),r=o.querySelector(".shopbot-product-title"),c=t.length;if(o.classList.remove("count-1","count-2","count-3","count-many"),o.classList.add(Zt(c)),o.style.setProperty("--shopbot-card-count",String(te(c))),r.textContent=e||_,!c){n.innerHTML='<p class="shopbot-product-empty">No matching products are currently available.</p>',o.classList.add("active"),ht();return}n.innerHTML=t.map(s=>{let T=C(s.id);return`
        <article class="shopbot-product-card" data-product-id="${T}">
          <img class="shopbot-product-image" src="${C(s.imageUrl||$t)}" alt="${C(s.name)}">
          <h3 class="shopbot-product-name">${C(s.name)}</h3>
          <p class="shopbot-product-meta">${C(s.brand)} - $${Number(s.price||0).toFixed(2)} USD</p>
          <div class="shopbot-product-actions">
            <button type="button" data-add="${T}">Add</button>
            <button type="button" class="secondary" data-view="${T}">View</button>
          </div>
        </article>
      `}).join(""),n.querySelectorAll("[data-add]").forEach(s=>{s.addEventListener("click",async()=>{await Xt(s.getAttribute("data-add"))})}),n.querySelectorAll("[data-view]").forEach(s=>{s.addEventListener("click",async()=>{await Jt(s.getAttribute("data-view"))})}),o.classList.add("active"),ht()}function ht(){window.setTimeout(()=>{let t=document.getElementById("shopbot-chat"),e=document.getElementById("shopbot-msgs");e&&(e.innerHTML=""),t&&t.classList.remove("visible")},ot)}async function ft(t,e=_){try{let o=await Kt(t);return lt(o,e),!0}catch(o){return console.warn("[ShopBot] Product overlay failed:",o),lt([],e),!0}}function ee(t){let e=t?.params||t?.parameters||{};return{...t||{},params:e,parameters:e}}function mt(t){let e=String(t||"").trim();if(!e||/^https?:\/\//i.test(e))return"";if(e==="home"||e==="/")return"/";let o=e.replace(/^\/+|\/+$/g,"");return o?`/${o}/`:"/"}var H=class{canHandle(e){return e.action===i.SHOW_PRODUCTS}async handle(e){let o=e.parameters||{};return await ft(o[a.PRODUCT_IDS]||[],o[a.SEARCH_QUERY]||_),!0}},F=class{canHandle(e){return e.action===i.SHOW_PRODUCT_DETAIL}async handle(e){let o="";try{let n=e.parameters?.[a.PRODUCT_ID];o=await P(n)}catch(n){return console.warn("[ShopBot] Product detail URL lookup failed:",n),!1}return o?(window.location.href=o,!0):!1}},B=class{canHandle(e){let o=window.ShopBotConfig;if(!o)return!1;if(e.action===i.ADD_TO_CART)return typeof o.onAddToCart=="function";if(e.action===i.FILTER_PRODUCTS)return typeof o.onFilter=="function";if(e.action===i.CHECKOUT)return typeof o.onCheckout=="function";if(e.action===i.NAVIGATE_TO){let n=e.parameters?.[a.PAGE];return I.has(n)&&typeof o.onOpenCart=="function"?!0:typeof o.onNavigate=="function"}return!1}async handle(e){let o=window.ShopBotConfig;if(e.action===i.ADD_TO_CART)return await o.onAddToCart(e.parameters?.[a.PRODUCT_ID],e.parameters?.[a.QUANTITY]),!0;if(e.action===i.FILTER_PRODUCTS)return await o.onFilter(e.parameters),!0;if(e.action===i.CHECKOUT)return await o.onCheckout(e.parameters),!0;if(e.action===i.NAVIGATE_TO){let n=e.parameters?.[a.PAGE];return I.has(n)&&typeof o.onOpenCart=="function"?(await o.onOpenCart(e.parameters),!0):(await o.onNavigate(n,e.parameters),!0)}return!1}},G=class{canHandle(e){let o=window.ShopCart;if(!o)return!1;let n=e.parameters?.[a.PAGE];return e.action===i.ADD_TO_CART&&typeof o.addItem=="function"||e.action===i.CLEAR_CART&&typeof o.clear=="function"||e.action===i.NAVIGATE_TO&&I.has(n)&&typeof o.open=="function"||e.action===i.CHECKOUT&&typeof o.checkout=="function"||e.action===i.SHOW_PRODUCTS&&typeof o.showProducts=="function"||e.action===i.SHOW_COMPARISON&&typeof o.showComparison=="function"||e.action===i.FILTER_PRODUCTS&&typeof o.filterProducts=="function"||e.action===i.SHOW_PRODUCT_DETAIL&&typeof o.showProductDetail=="function"||e.action===i.REMOVE_FROM_CART&&typeof o.removeItem=="function"||e.action===i.UPDATE_CART_QUANTITY&&typeof o.updateQuantity=="function"}async handle(e){let o=window.ShopCart,n=e.parameters||{};return e.action===i.ADD_TO_CART?(await o.addItem(n[a.PRODUCT_ID],n[a.QUANTITY]||1),!0):e.action===i.CLEAR_CART?(o.clear(),!0):e.action===i.NAVIGATE_TO?(o.open(),!0):e.action===i.CHECKOUT?(await o.checkout(n),!0):e.action===i.SHOW_PRODUCTS?(await o.showProducts(n[a.PRODUCT_IDS]||[],n[a.SEARCH_QUERY]||_),!0):e.action===i.SHOW_COMPARISON?(await o.showComparison(n[a.PRODUCT_IDS]||[]),!0):e.action===i.FILTER_PRODUCTS?(await o.filterProducts(n),!0):e.action===i.SHOW_PRODUCT_DETAIL?(await o.showProductDetail(n[a.PRODUCT_ID]),!0):e.action===i.REMOVE_FROM_CART?(await o.removeItem(n[a.PRODUCT_ID]),!0):e.action===i.UPDATE_CART_QUANTITY?(await o.updateQuantity(n[a.PRODUCT_ID],Number(n[a.QUANTITY])||0),!0):!1}},W=class{canHandle(e){return e.action===i.NAVIGATE_TO&&!!mt(e.parameters?.[a.PAGE])}handle(e){return window.location.href=mt(e.parameters?.[a.PAGE]),!0}},z=class{canHandle(){return!0}handle(e){return window.dispatchEvent(new CustomEvent(S.SHOPBOT_ACTION,{detail:e})),!0}},Y=class{constructor(e){this.adapters=e}async execute(e){for(let o of e||[]){let n=ee(o);if(n.action)for(let r of this.adapters){if(!r.canHandle(n))continue;if(await r.handle(n))break}}}},oe=new Y([new H,new F,new B,new G,new W,new z]);function j(t){return oe.execute(t)}var ne=3;function re(t,e){let o=new URL(R.SHOP_WS,t);return o.protocol=o.protocol==="https:"?"wss:":"ws:",o.searchParams.set("site_id",e),o.toString()}function se(t){return new Promise((e,o)=>{let n=new FileReader;n.onloadend=()=>{let r=String(n.result||"");e(r.includes(",")?r.split(",").pop():r)},n.onerror=()=>o(n.error||new Error("Failed to read audio blob")),n.readAsDataURL(t)})}var V=class{constructor(){this.queue=[],this.playing=!1}push(e){e&&(this.queue.push(e),this.playNext())}playNext(){if(this.playing||this.queue.length===0)return;this.playing=!0;let e=new Audio(O.DATA_WAV_PREFIX+this.queue.shift());e.onended=()=>{this.playing=!1,this.playNext()},e.onerror=()=>{this.playing=!1,this.playNext()},e.play().catch(o=>{console.error("Audio playback failed",o),this.playing=!1,this.playNext()})}},$=class{async sendAudio(e,o,n=[]){let r=new FormData;r.append("audio",e,O.WEBM_FILENAME),r.append("site_id",l.siteId),n&&n.length>0&&r.append("conversation_history",JSON.stringify(n));let c=await fetch(`${l.apiUrl}${R.SHOP}`,{method:J.POST,body:r});if(!c.ok)throw new Error("ShopBot API request failed");let s=await c.json();s.transcript&&o.onUserMessage?.(s.transcript),s.response_text&&o.onAssistantMessage?.(s.response_text,s.ui_actions||[]),o.onStatusChange?.(p.READY),s.audio_b64&&ce(s.audio_b64),s.ui_actions&&s.ui_actions.length>0&&await j(s.ui_actions),o.onComplete?.(s)}},Q=class{constructor(){this.ws=null,this.connected=!1,this.connecting=null,this.failed=!1,this.retries=0,this.audioQueue=new V,this.callbacks=null,this.turnText=""}async ensureConnected(e=[]){return this.failed||!l.useWebSocket||!("WebSocket"in window)?!1:this.connected&&this.ws?.readyState===WebSocket.OPEN?!0:this.connecting?this.connecting:(this.connecting=new Promise(o=>{let n=new WebSocket(re(l.apiUrl,l.siteId));this.ws=n;let r=()=>{this.connected=!1,this.connecting=null,this.retries+=1,this.retries>=ne&&(this.failed=!0),o(!1)},c=window.setTimeout(r,nt);n.onopen=()=>{window.clearTimeout(c),this.connected=!0,this.connecting=null,this.retries=0,this.sendJson({type:f.CONFIG,history:e||[]}),o(!0)},n.onmessage=s=>this.handleMessage(s),n.onerror=r,n.onclose=()=>{this.connected=!1}}),this.connecting)}sendJson(e){return!this.ws||this.ws.readyState!==WebSocket.OPEN?!1:(this.ws.send(JSON.stringify(e)),!0)}async sendAudio(e,o,n=[]){if(!await this.ensureConnected(n))return!1;this.callbacks=o,this.turnText="",this.sendJson({type:f.CONFIG,history:n||[]});let c=await se(e);return this.sendJson({type:f.AUDIO_CHUNK,data:c}),this.sendJson({type:f.AUDIO_END}),!0}async handleMessage(e){let o=this.callbacks;if(!o)return;let n={};try{n=JSON.parse(e.data)}catch{o.onComplete?.({error:"Invalid WebSocket message"});return}if(n.type===f.TRANSCRIPT){o.onUserMessage?.(n.text||"");return}if(n.type===f.TEXT_CHUNK){this.turnText+=n.text||"",o.onAssistantChunk?.(n.text||"",this.turnText);return}if(n.type===f.AUDIO_CHUNK){this.audioQueue.push(n.audio_b64);return}if(n.type===f.DONE){let r=n.response_text||this.turnText;o.onAssistantMessage?.(r,n.ui_actions||[],{streamed:!0}),o.onStatusChange?.(p.READY),n.ui_actions&&n.ui_actions.length>0&&await j(n.ui_actions),o.onComplete?.(n),this.callbacks=null;return}n.type===f.ERROR&&(o.onStatusChange?.(p.ERROR),o.onComplete?.({error:n.message||"WebSocket error"}),this.callbacks=null)}},ie=new $,ae=new Q;async function bt(t,e,o,n=[]){try{if(l.useWebSocket&&await ae.sendAudio(t,o,n))return;await ie.sendAudio(t,o,n)}catch(r){console.error(r),o.onStatusChange?.(p.ERROR),o.onComplete?.({error:String(r)})}}function ce(t){let e=O.DATA_WAV_PREFIX+t;new Audio(e).play().catch(n=>console.error("Audio playback failed",n))}window.__shopbot_identifier="voice-orb";function gt(){if(window.__shopbotBooted||document.getElementById("shopbot-widget"))return;window.__shopbotBooted=!0,K();let t=X(),e=null;function o(u=Z){e&&window.clearTimeout(e),e=window.setTimeout(()=>{t.msgs.innerHTML="",t.chat.classList.remove("visible"),e=null},u)}function n(u){t.status.className="",u===p.RECORDING?(e&&(window.clearTimeout(e),e=null),t.msgs.innerHTML="",t.btn.classList.add("recording"),t.chat.classList.add("visible"),t.status.innerText="Listening...",t.status.classList.add("listening")):u===p.PROCESSING?(t.btn.classList.remove("recording"),t.chat.classList.add("visible"),t.status.innerText="Analyzing...",t.status.classList.add("processing")):u===p.READY?(t.status.innerText="Ready",t.status.classList.add("ready")):u===p.ERROR&&(t.status.innerText="Error",t.status.classList.add("error"),t.btn.classList.remove("recording"))}let r=[],c=null,s="";function T(u,d){let h=[];for(let U of d||[]){let g=U.params||{};if(g[a.PRODUCT_IDS]&&Array.isArray(g[a.PRODUCT_IDS]))for(let q of g[a.PRODUCT_IDS])h.includes(q)||h.push(q);g[a.PRODUCT_ID]&&!h.includes(g[a.PRODUCT_ID])&&h.push(g[a.PRODUCT_ID])}return h.length>0?u+` [PRODUCT_IDS: ${h.join(",")}]`:u}async function w(u){c=null,s="",await bt(u,t,{onUserMessage:d=>{y(t,d,"user"),r.push({role:"user",content:d}),r.length>L&&r.shift()},onAssistantChunk:(d,h)=>{s=h,c||(c=y(t,"","ai")),v(t,c,s)},onAssistantMessage:(d,h,U={})=>{U.streamed&&c?v(t,c,d):y(t,d,"ai");let g=T(d,h);r.push({role:"assistant",content:g}),r.length>L&&r.shift(),c=null,s=""},onStatusChange:n,onComplete:()=>o()},r)}let x=rt(w,n);t.btn.addEventListener("click",()=>{x.toggle()}),ue()&&(pe(),window.setTimeout(()=>{if(r.length>0)return;let u=`Welcome to ${l.brandName}. How can I help you today?`;y(t,u,"ai"),n(p.READY),o(et);try{if("speechSynthesis"in window){let d=new SpeechSynthesisUtterance(u);d.rate=1,d.pitch=1,window.speechSynthesis.speak(d)}}catch{}},tt))}function ue(){if(!l.autoGreet||!de())return!1;try{return window.sessionStorage.getItem(Tt())!=="1"}catch{return!window.__shopbotAutoGreeted}}function pe(){window.__shopbotAutoGreeted=!0;try{window.sessionStorage.setItem(Tt(),"1")}catch{}}function Tt(){return`shopbot:auto-greeted:${l.siteId}`}function de(){let t=window.location.pathname.replace(/\/+$/,"")||"/";return t==="/"||t.endsWith("/index.html")}document.readyState==="loading"?document.addEventListener("DOMContentLoaded",gt):gt();})();
