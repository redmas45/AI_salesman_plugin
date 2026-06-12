(()=>{function P(){let t=document.createElement("style");t.textContent=`
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
  `,document.head.appendChild(t)}function L(){let t=document.createElement("div");return t.id="shopbot-widget",t.innerHTML=`
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
  `,document.body.appendChild(t),{btn:document.getElementById("shopbot-btn"),chat:document.getElementById("shopbot-chat"),msgs:document.getElementById("shopbot-msgs"),status:document.getElementById("shopbot-status")}}function b(t,e,o){t.chat.classList.add("visible");let n=document.createElement("div");return n.className=`shopbot-msg ${o}`,n.innerText=e,t.msgs.appendChild(n),t.msgs.scrollTop=t.msgs.scrollHeight,n}function y(t,e,o){e&&(e.innerText=o,t.msgs.scrollTop=t.msgs.scrollHeight)}function U(t,e){let o=null,n=[],s=!1;async function i(){try{let f=await navigator.mediaDevices.getUserMedia({audio:!0});o=new MediaRecorder(f),n=[],o.ondataavailable=m=>{m.data.size>0&&n.push(m.data)},o.onstop=async()=>{let m=new Blob(n,{type:"audio/webm"});f.getTracks().forEach(a=>a.stop()),await t(m)},o.start(),s=!0,e("recording")}catch(f){console.error("Microphone access denied",f),e("error")}}function r(){o&&o.state!=="inactive"&&o.stop(),s=!1,e("processing")}function h(){s?r():i()}return{toggle:h}}var g=document.currentScript,D="__AI_PUBLIC_API_URL__",M="__AI_DEFAULT_SITE_ID__";function u(t){return String(t||"").trim()}function j(){let t=u(g?.getAttribute("src"));if(!t)return null;try{return new URL(t,window.location.href)}catch{return null}}function G(t){return u(g?.getAttribute("data-site-id"))||u(t?.searchParams.get("site"))||u(t?.searchParams.get("site_id"))||u(t?.searchParams.get("shop"))||(M.startsWith("__AI_")?"":M)||"site_1"}function V(t){let e=u(g?.getAttribute("data-api-url"));return e?e.replace(/\/+$/,""):t?.origin?t.origin.replace(/\/+$/,""):D.startsWith("__AI_")?window.location.origin.replace(/\/+$/,""):D.replace(/\/+$/,"")}var N=j(),d={siteId:G(N),apiUrl:V(N),useWebSocket:u(g?.getAttribute("data-use-websocket")).toLowerCase()!=="false",autoGreet:u(g?.getAttribute("data-auto-greet")).toLowerCase()!=="false",brandName:u(g?.getAttribute("data-brand"))||"AI-KART"};var J="https://demo.vercel.store/placeholder.png";function w(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}function K(t){if(!t)return null;let e=String(t.id||t.product_id||"").trim(),o=String(t.name||t.title||"Untitled product").trim(),n=Number(t.price||0);return!e||!o?null:{id:e,name:o,brand:t.brand||t.vendor||"Unknown Brand",category:t.category||t.category_name||"Products",description:t.description||"",price:Number.isFinite(n)?n:0,imageUrl:t.image_url||t.image||t.thumbnail||""}}function Q(){if(document.getElementById("shopbot-product-overlay-styles"))return;let t=document.createElement("style");t.id="shopbot-product-overlay-styles",t.textContent=`
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
  `,document.head.appendChild(t)}function X(){Q();let t=document.getElementById("shopbot-product-panel");return t||(t=document.createElement("div"),t.id="shopbot-product-panel",t.setAttribute("aria-live","polite"),t.innerHTML=`
    <div class="shopbot-product-header">
      <h2 class="shopbot-product-title">Recommended products</h2>
      <button class="shopbot-product-close" type="button" aria-label="Close recommendations">&times;</button>
    </div>
    <div class="shopbot-product-grid"></div>
  `,t.querySelector(".shopbot-product-close").addEventListener("click",()=>{t.classList.remove("active")}),document.body.appendChild(t),t)}async function Y(t){let e=(Array.isArray(t)?t:[]).map(r=>String(r||"").trim()).filter(Boolean);if(!e.length)return[];let o=new URL("/v1/products/by-ids",d.apiUrl);o.searchParams.set("site_id",d.siteId),o.searchParams.set("ids",e.join(","));let n=await fetch(o.toString(),{headers:{Accept:"application/json"}});if(!n.ok)throw new Error("Failed to fetch recommended products");let s=(await n.json()).map(K).filter(Boolean),i=new Map(s.map(r=>[String(r.id),r]));return e.map(r=>i.get(String(r))).filter(Boolean)}async function Z(t){let e=window.ShopCart;if(e&&typeof e.addItem=="function"){await e.addItem(t,1),typeof e.open=="function"&&e.open();return}let o={action:"ADD_TO_CART",params:{product_id:t,quantity:1},parameters:{product_id:t,quantity:1}};window.dispatchEvent(new CustomEvent("shopbot:action",{detail:o}))}async function tt(t){let e=window.ShopCart;if(e&&typeof e.showProductDetail=="function"){await e.showProductDetail(t);return}let o={action:"SHOW_PRODUCT_DETAIL",params:{product_id:t},parameters:{product_id:t}};window.dispatchEvent(new CustomEvent("shopbot:action",{detail:o}))}function et(t){return t<=1?"count-1":t===2?"count-2":t===3?"count-3":"count-many"}function ot(t){return t<=1?1:t===2?2:3}function B(t,e){let o=X(),n=o.querySelector(".shopbot-product-grid"),s=o.querySelector(".shopbot-product-title"),i=t.length;if(o.classList.remove("count-1","count-2","count-3","count-many"),o.classList.add(et(i)),o.style.setProperty("--shopbot-card-count",String(ot(i))),s.textContent=e||"Recommended products",!i){n.innerHTML='<p class="shopbot-product-empty">No matching products are currently available.</p>',o.classList.add("active"),H();return}n.innerHTML=t.map(r=>{let h=w(r.id);return`
        <article class="shopbot-product-card" data-product-id="${h}">
          <img class="shopbot-product-image" src="${w(r.imageUrl||J)}" alt="${w(r.name)}">
          <h3 class="shopbot-product-name">${w(r.name)}</h3>
          <p class="shopbot-product-meta">${w(r.brand)} - $${Number(r.price||0).toFixed(2)} USD</p>
          <div class="shopbot-product-actions">
            <button type="button" data-add="${h}">Add</button>
            <button type="button" class="secondary" data-view="${h}">View</button>
          </div>
        </article>
      `}).join(""),n.querySelectorAll("[data-add]").forEach(r=>{r.addEventListener("click",async()=>{await Z(r.getAttribute("data-add"))})}),n.querySelectorAll("[data-view]").forEach(r=>{r.addEventListener("click",async()=>{await tt(r.getAttribute("data-view"))})}),o.classList.add("active"),H()}function H(){window.setTimeout(()=>{let t=document.getElementById("shopbot-chat"),e=document.getElementById("shopbot-msgs");e&&(e.innerHTML=""),t&&t.classList.remove("visible")},180)}async function W(t,e="Recommended products"){try{let o=await Y(t);return B(o,e),!0}catch(o){return console.warn("[ShopBot] Product overlay failed:",o),B([],e),!0}}function nt(t){let e=t?.params||t?.parameters||{};return{...t||{},params:e,parameters:e}}function $(t){let e=String(t||"").trim();if(!e||/^https?:\/\//i.test(e))return"";if(e==="home"||e==="/")return"/";let o=e.replace(/^\/+|\/+$/g,"");return o?`/${o}/`:"/"}var _=class{canHandle(e){return e.action==="SHOW_PRODUCTS"}async handle(e){let o=e.parameters||{};return await W(o.product_ids||[],o.search_query||"Recommended products"),!0}},v=class{canHandle(e){let o=window.ShopBotConfig;if(!o)return!1;if(e.action==="ADD_TO_CART")return typeof o.onAddToCart=="function";if(e.action==="FILTER_PRODUCTS")return typeof o.onFilter=="function";if(e.action==="CHECKOUT")return typeof o.onCheckout=="function";if(e.action==="NAVIGATE_TO"){let n=e.parameters?.page;return(n==="cart"||n==="/cart")&&typeof o.onOpenCart=="function"?!0:typeof o.onNavigate=="function"}return!1}async handle(e){let o=window.ShopBotConfig;if(e.action==="ADD_TO_CART")return await o.onAddToCart(e.parameters?.product_id,e.parameters?.quantity),!0;if(e.action==="FILTER_PRODUCTS")return await o.onFilter(e.parameters),!0;if(e.action==="CHECKOUT")return await o.onCheckout(e.parameters),!0;if(e.action==="NAVIGATE_TO"){let n=e.parameters?.page;return(n==="cart"||n==="/cart")&&typeof o.onOpenCart=="function"?(await o.onOpenCart(e.parameters),!0):(await o.onNavigate(n,e.parameters),!0)}return!1}},T=class{canHandle(e){let o=window.ShopCart;if(!o)return!1;let n=e.parameters?.page;return e.action==="ADD_TO_CART"&&typeof o.addItem=="function"||e.action==="CLEAR_CART"&&typeof o.clear=="function"||e.action==="NAVIGATE_TO"&&(n==="cart"||n==="/cart")&&typeof o.open=="function"||e.action==="CHECKOUT"&&typeof o.checkout=="function"||e.action==="SHOW_PRODUCTS"&&typeof o.showProducts=="function"||e.action==="SHOW_COMPARISON"&&typeof o.showComparison=="function"||e.action==="FILTER_PRODUCTS"&&typeof o.filterProducts=="function"||e.action==="SHOW_PRODUCT_DETAIL"&&typeof o.showProductDetail=="function"||e.action==="REMOVE_FROM_CART"&&typeof o.removeItem=="function"||e.action==="UPDATE_CART_QUANTITY"&&typeof o.updateQuantity=="function"}async handle(e){let o=window.ShopCart,n=e.parameters||{};return e.action==="ADD_TO_CART"?(await o.addItem(n.product_id,n.quantity||1),!0):e.action==="CLEAR_CART"?(o.clear(),!0):e.action==="NAVIGATE_TO"?(o.open(),!0):e.action==="CHECKOUT"?(await o.checkout(n),!0):e.action==="SHOW_PRODUCTS"?(await o.showProducts(n.product_ids||[],n.search_query||"Recommended products"),!0):e.action==="SHOW_COMPARISON"?(await o.showComparison(n.product_ids||[]),!0):e.action==="FILTER_PRODUCTS"?(await o.filterProducts(n),!0):e.action==="SHOW_PRODUCT_DETAIL"?(await o.showProductDetail(n.product_id),!0):e.action==="REMOVE_FROM_CART"?(await o.removeItem(n.product_id),!0):e.action==="UPDATE_CART_QUANTITY"?(await o.updateQuantity(n.product_id,Number(n.quantity)||0),!0):!1}},A=class{canHandle(e){return e.action==="NAVIGATE_TO"&&!!$(e.parameters?.page)}handle(e){return window.location.href=$(e.parameters?.page),!0}},C=class{canHandle(){return!0}handle(e){return window.dispatchEvent(new CustomEvent("shopbot:action",{detail:e})),!0}},S=class{constructor(e){this.adapters=e}async execute(e){for(let o of e||[]){let n=nt(o);console.log("ShopBot executing action:",n);for(let s of this.adapters){if(!s.canHandle(n))continue;if(await s.handle(n))break}}}},rt=new S([new _,new v,new T,new A,new C]);function k(t){return rt.execute(t)}var st=3;function it(t,e){let o=new URL("/v1/ws/shop",t);return o.protocol=o.protocol==="https:"?"wss:":"ws:",o.searchParams.set("site_id",e),o.toString()}function at(t){return new Promise((e,o)=>{let n=new FileReader;n.onloadend=()=>{let s=String(n.result||"");e(s.includes(",")?s.split(",").pop():s)},n.onerror=()=>o(n.error||new Error("Failed to read audio blob")),n.readAsDataURL(t)})}var E=class{constructor(){this.queue=[],this.playing=!1}push(e){e&&(this.queue.push(e),this.playNext())}playNext(){if(this.playing||this.queue.length===0)return;this.playing=!0;let e=new Audio("data:audio/wav;base64,"+this.queue.shift());e.onended=()=>{this.playing=!1,this.playNext()},e.onerror=()=>{this.playing=!1,this.playNext()},e.play().catch(o=>{console.error("Audio playback failed",o),this.playing=!1,this.playNext()})}},R=class{async sendAudio(e,o,n=[]){let s=new FormData;s.append("audio",e,"audio.webm"),s.append("site_id",d.siteId),n&&n.length>0&&s.append("conversation_history",JSON.stringify(n));let i=await fetch(`${d.apiUrl}/v1/shop`,{method:"POST",body:s});if(!i.ok)throw new Error("API Error");let r=await i.json();r.transcript&&o.onUserMessage?.(r.transcript),r.response_text&&o.onAssistantMessage?.(r.response_text,r.ui_actions||[]),o.onStatusChange?.("ready"),r.audio_b64&&pt(r.audio_b64),r.ui_actions&&r.ui_actions.length>0&&await k(r.ui_actions),o.onComplete?.(r)}},I=class{constructor(){this.ws=null,this.connected=!1,this.connecting=null,this.failed=!1,this.retries=0,this.audioQueue=new E,this.callbacks=null,this.turnText=""}async ensureConnected(e=[]){return this.failed||!d.useWebSocket||!("WebSocket"in window)?!1:this.connected&&this.ws?.readyState===WebSocket.OPEN?!0:this.connecting?this.connecting:(this.connecting=new Promise(o=>{let n=new WebSocket(it(d.apiUrl,d.siteId));this.ws=n;let s=()=>{this.connected=!1,this.connecting=null,this.retries+=1,this.retries>=st&&(this.failed=!0),o(!1)},i=window.setTimeout(s,2500);n.onopen=()=>{window.clearTimeout(i),this.connected=!0,this.connecting=null,this.retries=0,this.sendJson({type:"config",history:e||[]}),o(!0)},n.onmessage=r=>this.handleMessage(r),n.onerror=s,n.onclose=()=>{this.connected=!1}}),this.connecting)}sendJson(e){return!this.ws||this.ws.readyState!==WebSocket.OPEN?!1:(this.ws.send(JSON.stringify(e)),!0)}async sendAudio(e,o,n=[]){if(!await this.ensureConnected(n))return!1;this.callbacks=o,this.turnText="",this.sendJson({type:"config",history:n||[]});let i=await at(e);return this.sendJson({type:"audio_chunk",data:i}),this.sendJson({type:"audio_end"}),!0}async handleMessage(e){let o=this.callbacks;if(!o)return;let n={};try{n=JSON.parse(e.data)}catch{return}if(n.type==="transcript"){o.onUserMessage?.(n.text||"");return}if(n.type==="text_chunk"){this.turnText+=n.text||"",o.onAssistantChunk?.(n.text||"",this.turnText);return}if(n.type==="audio_chunk"){this.audioQueue.push(n.audio_b64);return}if(n.type==="done"){let s=n.response_text||this.turnText;o.onAssistantMessage?.(s,n.ui_actions||[],{streamed:!0}),o.onStatusChange?.("ready"),n.ui_actions&&n.ui_actions.length>0&&await k(n.ui_actions),o.onComplete?.(n),this.callbacks=null;return}n.type==="error"&&(o.onStatusChange?.("error"),o.onComplete?.({error:n.message||"WebSocket error"}),this.callbacks=null)}},ct=new R,dt=new I;async function q(t,e,o,n=[]){try{if(d.useWebSocket&&await dt.sendAudio(t,o,n))return;await ct.sendAudio(t,o,n)}catch(s){console.error(s),o.onStatusChange?.("error"),o.onComplete?.({error:String(s)})}}function pt(t){let e="data:audio/wav;base64,"+t;new Audio(e).play().catch(n=>console.error("Audio playback failed",n))}window.__shopbot_identifier="voice-orb";function z(){if(window.__shopbotBooted||document.getElementById("shopbot-widget"))return;window.__shopbotBooted=!0,P();let t=L(),e=null;function o(a=2400){e&&window.clearTimeout(e),e=window.setTimeout(()=>{t.msgs.innerHTML="",t.chat.classList.remove("visible"),e=null},a)}function n(a){t.status.className="",a==="recording"?(e&&(window.clearTimeout(e),e=null),t.msgs.innerHTML="",t.btn.classList.add("recording"),t.chat.classList.add("visible"),t.status.innerText="Listening...",t.status.classList.add("listening")):a==="processing"?(t.btn.classList.remove("recording"),t.chat.classList.add("visible"),t.status.innerText="Analyzing...",t.status.classList.add("processing")):a==="ready"?(t.status.innerText="Ready",t.status.classList.add("ready")):a==="error"&&(t.status.innerText="Error",t.status.classList.add("error"),t.btn.classList.remove("recording"))}let s=[],i=null,r="";function h(a,c){let p=[];for(let x of c||[]){let l=x.params||{};if(l.product_ids&&Array.isArray(l.product_ids))for(let O of l.product_ids)p.includes(O)||p.push(O);l.product_id&&!p.includes(l.product_id)&&p.push(l.product_id)}return p.length>0?a+` [PRODUCT_IDS: ${p.join(",")}]`:a}async function f(a){i=null,r="",await q(a,t,{onUserMessage:c=>{b(t,c,"user"),s.push({role:"user",content:c}),s.length>12&&s.shift()},onAssistantChunk:(c,p)=>{r=p,i||(i=b(t,"","ai")),y(t,i,r)},onAssistantMessage:(c,p,x={})=>{x.streamed&&i?y(t,i,c):b(t,c,"ai");let l=h(c,p);s.push({role:"assistant",content:l}),s.length>12&&s.shift(),i=null,r=""},onStatusChange:n,onComplete:()=>o()},s)}let m=U(f,n);t.btn.addEventListener("click",()=>{m.toggle()}),ut()&&(lt(),window.setTimeout(()=>{if(s.length>0)return;let a=`Welcome to ${d.brandName}. How can I help you today?`;b(t,a,"ai"),n("ready"),o(4200);try{if("speechSynthesis"in window){let c=new SpeechSynthesisUtterance(a);c.rate=1,c.pitch=1,window.speechSynthesis.speak(c)}}catch{}},900))}function ut(){if(!d.autoGreet||!ht())return!1;try{return window.sessionStorage.getItem(F())!=="1"}catch{return!window.__shopbotAutoGreeted}}function lt(){window.__shopbotAutoGreeted=!0;try{window.sessionStorage.setItem(F(),"1")}catch{}}function F(){return`shopbot:auto-greeted:${d.siteId}`}function ht(){let t=window.location.pathname.replace(/\/+$/,"")||"/";return t==="/"||t.endsWith("/index.html")}document.readyState==="loading"?document.addEventListener("DOMContentLoaded",z):z();})();
