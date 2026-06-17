(()=>{function J(){let t=document.createElement("style");t.textContent=`
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
  `,document.head.appendChild(t)}function Z(){let t=document.createElement("div");return t.id="shopbot-widget",t.innerHTML=`
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
  `,document.body.appendChild(t),{btn:document.getElementById("shopbot-btn"),chat:document.getElementById("shopbot-chat"),msgs:document.getElementById("shopbot-msgs"),status:document.getElementById("shopbot-status")}}function x(t,e,o){t.chat.classList.add("visible");let n=document.createElement("div");return n.className=`shopbot-msg ${o}`,n.innerText=e,t.msgs.appendChild(n),t.msgs.scrollTop=t.msgs.scrollHeight,n}function L(t,e,o){e&&(e.innerText=o,t.msgs.scrollTop=t.msgs.scrollHeight)}var i=Object.freeze({ADD_TO_CART:"ADD_TO_CART",CHECKOUT:"CHECKOUT",CLEAR_CART:"CLEAR_CART",FILTER_PRODUCTS:"FILTER_PRODUCTS",NAVIGATE_TO:"NAVIGATE_TO",REMOVE_FROM_CART:"REMOVE_FROM_CART",SHOW_COMPARISON:"SHOW_COMPARISON",SHOW_PRODUCT_DETAIL:"SHOW_PRODUCT_DETAIL",SHOW_PRODUCTS:"SHOW_PRODUCTS",UPDATE_CART_QUANTITY:"UPDATE_CART_QUANTITY"}),a=Object.freeze({PAGE:"page",PRODUCT_ID:"product_id",PRODUCT_IDS:"product_ids",QUANTITY:"quantity",SEARCH_QUERY:"search_query"}),P=new Set(["cart","/cart"]),w="Recommended products",A=Object.freeze({PRODUCTS_BY_IDS:"/v1/products/by-ids",SHOP:"/v1/shop",SHOP_WS:"/v1/ws/shop",WIDGET_STATUS:"/v1/widget/status"}),y=Object.freeze({DATA_WAV_PREFIX:"data:audio/wav;base64,",WEBM_FILENAME:"audio.webm",WEBM_MIME_TYPE:"audio/webm"}),tt=Object.freeze({POST:"POST"}),l=Object.freeze({ERROR:"error",PROCESSING:"processing",READY:"ready",RECORDING:"recording"}),N=12,et=2400,ot=900,nt=4200,U=1,rt=180,st=3e3,I=Object.freeze({SHOPBOT_ACTION:"shopbot:action"}),it=2500,b=Object.freeze({AUDIO_CHUNK:"audio_chunk",AUDIO_END:"audio_end",CONFIG:"config",DONE:"done",ERROR:"error",TEXT_CHUNK:"text_chunk",TRANSCRIPT:"transcript"});function at(t,e){let o=null,n=null,r=[],c=!1,s=!1;async function f(){try{let u=await navigator.mediaDevices.getUserMedia({audio:!0});n=u,s=!1,o=new MediaRecorder(u),r=[],o.ondataavailable=T=>{T.data.size>0&&r.push(T.data)},o.onstop=async()=>{let T=new Blob(r,{type:y.WEBM_MIME_TYPE});if(h(),s){s=!1;return}await t(T)},o.start(),c=!0,e(l.RECORDING)}catch(u){console.error("Microphone access denied",u),e(l.ERROR)}}function E({discard:u=!1}={}){if(s=u,o&&o.state!=="inactive"){o.stop(),c=!1,u||e(l.PROCESSING);return}c=!1,h(),u||e(l.PROCESSING)}function D(){c?E():f()}function p(){E({discard:!0})}function h(){n&&(n.getTracks().forEach(u=>u.stop()),n=null)}return{toggle:D,cancel:p}}var O=document.currentScript,ct="__AI_PUBLIC_API_URL__",ut="__AI_DEFAULT_SITE_ID__",Rt="shopbot:session:";function m(t){return String(t||"").trim()}function Ct(){let t=m(O?.getAttribute("src"));if(!t)return null;try{return new URL(t,window.location.href)}catch{return null}}function Dt(t){return m(O?.getAttribute("data-site-id"))||m(t?.searchParams.get("site"))||m(t?.searchParams.get("site_id"))||m(t?.searchParams.get("shop"))||(ut.startsWith("__AI_")?"":ut)||"site_1"}function Pt(t){let e=m(O?.getAttribute("data-api-url"));if(e)return e.replace(/\/+$/,"");if(!ct.startsWith("__AI_"))return ct.replace(/\/+$/,"");if(t?.origin){let o=t.pathname.replace(/\/shopbot(?:-widget)?\.js$/,"");return`${t.origin}${o}`.replace(/\/+$/,"")}return window.location.origin.replace(/\/+$/,"")}function Ut(t){let e=m(window.ShopBotConfig?.sessionId);if(e)return e.slice(0,120);let o=`${Rt}${t}`;try{let n=window.sessionStorage.getItem(o);if(n)return n;let r=dt(t);return window.sessionStorage.setItem(o,r),r}catch{return dt(t)}}function dt(t){let e=window.crypto?.randomUUID?.()||`${Date.now()}-${Math.random().toString(16).slice(2)}`;return`${t}-${e}`.slice(0,120)}var lt=Ct(),pt=Dt(lt),d={siteId:pt,get sessionId(){return Ut(pt)},apiUrl:Pt(lt),useWebSocket:m(O?.getAttribute("data-use-websocket")).toLowerCase()!=="false",autoGreet:m(O?.getAttribute("data-auto-greet")).toLowerCase()!=="false",brandName:m(O?.getAttribute("data-brand"))||"AI-KART"};var vt=Object.freeze(["/api/products.json","/products.json","/collections/all/products.json"]),Lt=Object.freeze(["products","data","items","results"]),ft=Object.freeze(["id","product_id","handle","sku"]),mt=Object.freeze(["name","title"]),Nt=Object.freeze(["url","href","permalink","product_url"]),Mt=Object.freeze(["image_url","image","thumbnail","featured_image"]),kt=Object.freeze(["brand","vendor"]),Ht=Object.freeze(["category","category_name","product_type"]),Bt=Object.freeze(["description","summary","body_html"]),Ft="Unknown Brand",Wt="Products",Gt="/product/",jt="/products/",zt="/",$t=/^[a-z0-9][a-z0-9-]*$/i,M=null;function g(t){return t==null||typeof t=="object"?"":String(t||"").trim()}function Yt(t){return g(t).toLowerCase().replace(/[^a-z0-9]+/g," ").trim()}function k(t,e){return e.map(o=>g(t?.[o])).filter(Boolean)}function S(t,e){return k(t,e)[0]||""}function Vt(t){let e=S(t,Mt);if(e)return e;let o=t?.image||t?.featured_image;return o&&typeof o=="object"?g(o.src||o.url):Array.isArray(t?.images)?g(t.images[0]?.src||t.images[0]?.url||t.images[0]):""}function Qt(t){let e=g(t);if(!e)return"";try{let o=new URL(e,window.location.origin);return o.origin!==window.location.origin?"":`${o.pathname}${o.search}${o.hash}`}catch{return""}}function qt(t){return t==="/products.json"||t.includes("/collections/")?jt:Gt}function Kt(t,e,o){let n=Qt(S(t,Nt));return n||(!$t.test(e)||!/[a-z]/i.test(e)?"":`${qt(o)}${encodeURIComponent(e)}${zt}`)}function gt(t,e=""){if(!t)return null;let o=S(t,ft),n=g(t.handle||t.slug||t.product_handle),r=S(t,mt),c=Number(t.price||t.amount||t.cost||0);return!o&&!n?null:{id:o,handle:n,name:r,title:g(t.title||r),brand:S(t,kt)||Ft,category:S(t,Ht)||Wt,description:S(t,Bt),price:Number.isFinite(c)?c:0,imageUrl:Vt(t),url:Kt(t,n||o,e)}}function Xt(t){return k(t,ft)}function ht(t){return k(t,mt).map(Yt)}function Jt(t,e){let o=g(e);return!!(o&&Xt(t).includes(o))}function Zt(t,e){let o=new Set(ht(e));return ht(t).some(n=>o.has(n))}function te(t,e){return!!(t?.imageUrl&&t.imageUrl===e?.imageUrl)}function ee(t){if(Array.isArray(t))return t;for(let e of Lt){let o=t?.[e];if(Array.isArray(o))return o}return[]}async function oe(t){try{let e=await fetch(new URL(t,window.location.origin),{headers:{Accept:"application/json"}});if(!e.ok)return[];let o=await e.json();return ee(o).map(n=>gt(n,t)).filter(Boolean)}catch(e){return console.warn(`[ShopBot] Catalog endpoint lookup failed for ${t}:`,e),[]}}async function ne(){return M||(M=Promise.all(vt.map(oe)).then(t=>t.flat())),M}async function H(t){let e=(Array.isArray(t)?t:[]).map(g).filter(Boolean);if(!e.length)return[];let o=new URL(A.PRODUCTS_BY_IDS,d.apiUrl);o.searchParams.set("site_id",d.siteId),o.searchParams.set("ids",e.join(","));let n=await fetch(o.toString(),{headers:{Accept:"application/json"}});if(!n.ok)throw new Error("Failed to fetch products from ShopBot API");let r=(await n.json()).map(s=>gt(s)).filter(Boolean),c=new Map(r.map(s=>[String(s.id),s]));return e.map(s=>c.get(s)).filter(Boolean)}async function v(t){let e=g(t);if(!e)return"";let[o]=await H([e]);if(o?.url)return o.url;let n=await ne(),r=n.find(s=>Jt(s,e));return r?.url?r.url:o&&n.find(s=>Zt(s,o)||te(s,o))?.url||""}var re="https://demo.vercel.store/placeholder.png";function R(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}function se(){if(document.getElementById("shopbot-product-overlay-styles"))return;let t=document.createElement("style");t.id="shopbot-product-overlay-styles",t.textContent=`
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
  `,document.head.appendChild(t)}function ie(){se();let t=document.getElementById("shopbot-product-panel");return t||(t=document.createElement("div"),t.id="shopbot-product-panel",t.setAttribute("aria-live","polite"),t.innerHTML=`
    <div class="shopbot-product-header">
      <h2 class="shopbot-product-title">${w}</h2>
      <button class="shopbot-product-close" type="button" aria-label="Close recommendations">&times;</button>
    </div>
    <div class="shopbot-product-grid"></div>
  `,t.querySelector(".shopbot-product-close").addEventListener("click",()=>{t.classList.remove("active")}),document.body.appendChild(t),t)}async function ae(t){return H(t)}async function ce(t){let e=window.ShopCart;if(e&&typeof e.addItem=="function"){await e.addItem(t,U),typeof e.open=="function"&&e.open();return}let o={action:i.ADD_TO_CART,params:{[a.PRODUCT_ID]:t,[a.QUANTITY]:U},parameters:{[a.PRODUCT_ID]:t,[a.QUANTITY]:U}};window.dispatchEvent(new CustomEvent(I.SHOPBOT_ACTION,{detail:o}))}async function ue(t){try{let n=await v(t);if(n){window.location.href=n;return}}catch(n){console.warn("[ShopBot] Product detail URL lookup failed:",n)}let e=window.ShopCart;if(e&&typeof e.showProductDetail=="function"){await e.showProductDetail(t);return}let o={action:i.SHOW_PRODUCT_DETAIL,params:{[a.PRODUCT_ID]:t},parameters:{[a.PRODUCT_ID]:t}};window.dispatchEvent(new CustomEvent(I.SHOPBOT_ACTION,{detail:o}))}function de(t){return t<=1?"count-1":t===2?"count-2":t===3?"count-3":"count-many"}function pe(t){return t<=1?1:t===2?2:3}function bt(t,e){let o=ie(),n=o.querySelector(".shopbot-product-grid"),r=o.querySelector(".shopbot-product-title"),c=t.length;if(o.classList.remove("count-1","count-2","count-3","count-many"),o.classList.add(de(c)),o.style.setProperty("--shopbot-card-count",String(pe(c))),r.textContent=e||w,!c){n.innerHTML='<p class="shopbot-product-empty">No matching products are currently available.</p>',o.classList.add("active"),Tt();return}n.innerHTML=t.map(s=>{let f=R(s.id);return`
        <article class="shopbot-product-card" data-product-id="${f}">
          <img class="shopbot-product-image" src="${R(s.imageUrl||re)}" alt="${R(s.name)}">
          <h3 class="shopbot-product-name">${R(s.name)}</h3>
          <p class="shopbot-product-meta">${R(s.brand)} - $${Number(s.price||0).toFixed(2)} USD</p>
          <div class="shopbot-product-actions">
            <button type="button" data-add="${f}">Add</button>
            <button type="button" class="secondary" data-view="${f}">View</button>
          </div>
        </article>
      `}).join(""),n.querySelectorAll("[data-add]").forEach(s=>{s.addEventListener("click",async()=>{await ce(s.getAttribute("data-add"))})}),n.querySelectorAll("[data-view]").forEach(s=>{s.addEventListener("click",async()=>{await ue(s.getAttribute("data-view"))})}),o.classList.add("active"),Tt()}function Tt(){window.setTimeout(()=>{let t=document.getElementById("shopbot-chat"),e=document.getElementById("shopbot-msgs");e&&(e.innerHTML=""),t&&t.classList.remove("visible")},rt)}async function _t(t,e=w){try{let o=await ae(t);return bt(o,e),!0}catch(o){return console.warn("[ShopBot] Product overlay failed:",o),bt([],e),!0}}function le(t){let e=t?.params||t?.parameters||{};return{...t||{},params:e,parameters:e}}function wt(t){let e=String(t||"").trim();if(!e||/^https?:\/\//i.test(e))return"";if(e==="home"||e==="/")return"/";let o=e.replace(/^\/+|\/+$/g,"");return o?`/${o}/`:"/"}var B=class{canHandle(e){return e.action===i.SHOW_PRODUCTS}async handle(e){let o=e.parameters||{};return await _t(o[a.PRODUCT_IDS]||[],o[a.SEARCH_QUERY]||w),!0}},F=class{canHandle(e){return e.action===i.SHOW_PRODUCT_DETAIL}async handle(e){let o="";try{let n=e.parameters?.[a.PRODUCT_ID];o=await v(n)}catch(n){return console.warn("[ShopBot] Product detail URL lookup failed:",n),!1}return o?(window.location.href=o,!0):!1}},W=class{canHandle(e){let o=window.ShopBotConfig;if(!o)return!1;if(e.action===i.ADD_TO_CART)return typeof o.onAddToCart=="function";if(e.action===i.FILTER_PRODUCTS)return typeof o.onFilter=="function";if(e.action===i.CHECKOUT)return typeof o.onCheckout=="function";if(e.action===i.NAVIGATE_TO){let n=e.parameters?.[a.PAGE];return P.has(n)&&typeof o.onOpenCart=="function"?!0:typeof o.onNavigate=="function"}return!1}async handle(e){let o=window.ShopBotConfig;if(e.action===i.ADD_TO_CART)return await o.onAddToCart(e.parameters?.[a.PRODUCT_ID],e.parameters?.[a.QUANTITY]),!0;if(e.action===i.FILTER_PRODUCTS)return await o.onFilter(e.parameters),!0;if(e.action===i.CHECKOUT)return await o.onCheckout(e.parameters),!0;if(e.action===i.NAVIGATE_TO){let n=e.parameters?.[a.PAGE];return P.has(n)&&typeof o.onOpenCart=="function"?(await o.onOpenCart(e.parameters),!0):(await o.onNavigate(n,e.parameters),!0)}return!1}},G=class{canHandle(e){let o=window.ShopCart;if(!o)return!1;let n=e.parameters?.[a.PAGE];return e.action===i.ADD_TO_CART&&typeof o.addItem=="function"||e.action===i.CLEAR_CART&&typeof o.clear=="function"||e.action===i.NAVIGATE_TO&&P.has(n)&&typeof o.open=="function"||e.action===i.CHECKOUT&&typeof o.checkout=="function"||e.action===i.SHOW_PRODUCTS&&typeof o.showProducts=="function"||e.action===i.SHOW_COMPARISON&&typeof o.showComparison=="function"||e.action===i.FILTER_PRODUCTS&&typeof o.filterProducts=="function"||e.action===i.SHOW_PRODUCT_DETAIL&&typeof o.showProductDetail=="function"||e.action===i.REMOVE_FROM_CART&&typeof o.removeItem=="function"||e.action===i.UPDATE_CART_QUANTITY&&typeof o.updateQuantity=="function"}async handle(e){let o=window.ShopCart,n=e.parameters||{};return e.action===i.ADD_TO_CART?(await o.addItem(n[a.PRODUCT_ID],n[a.QUANTITY]||1),!0):e.action===i.CLEAR_CART?(o.clear(),!0):e.action===i.NAVIGATE_TO?(o.open(),!0):e.action===i.CHECKOUT?(await o.checkout(n),!0):e.action===i.SHOW_PRODUCTS?(await o.showProducts(n[a.PRODUCT_IDS]||[],n[a.SEARCH_QUERY]||w),!0):e.action===i.SHOW_COMPARISON?(await o.showComparison(n[a.PRODUCT_IDS]||[]),!0):e.action===i.FILTER_PRODUCTS?(await o.filterProducts(n),!0):e.action===i.SHOW_PRODUCT_DETAIL?(await o.showProductDetail(n[a.PRODUCT_ID]),!0):e.action===i.REMOVE_FROM_CART?(await o.removeItem(n[a.PRODUCT_ID]),!0):e.action===i.UPDATE_CART_QUANTITY?(await o.updateQuantity(n[a.PRODUCT_ID],Number(n[a.QUANTITY])||0),!0):!1}},j=class{canHandle(e){return e.action===i.NAVIGATE_TO&&!!wt(e.parameters?.[a.PAGE])}handle(e){return window.location.href=wt(e.parameters?.[a.PAGE]),!0}},z=class{canHandle(){return!0}handle(e){return window.dispatchEvent(new CustomEvent(I.SHOPBOT_ACTION,{detail:e})),!0}},$=class{constructor(e){this.adapters=e}async execute(e){for(let o of e||[]){let n=le(o);if(n.action)for(let r of this.adapters){if(!r.canHandle(n))continue;if(await r.handle(n))break}}}},he=new $([new B,new F,new W,new G,new j,new z]);function Y(t){return he.execute(t)}var fe=3;function me(t,e){let o=new URL(A.SHOP_WS,t);return o.protocol=o.protocol==="https:"?"wss:":"ws:",o.searchParams.set("site_id",e),o.searchParams.set("session_id",d.sessionId),o.toString()}function ge(t){return new Promise((e,o)=>{let n=new FileReader;n.onloadend=()=>{let r=String(n.result||"");e(r.includes(",")?r.split(",").pop():r)},n.onerror=()=>o(n.error||new Error("Failed to read audio blob")),n.readAsDataURL(t)})}var V=class{constructor(){this.queue=[],this.playing=!1}push(e){e&&(this.queue.push(e),this.playNext())}playNext(){if(this.playing||this.queue.length===0)return;this.playing=!0;let e=new Audio(y.DATA_WAV_PREFIX+this.queue.shift());e.onended=()=>{this.playing=!1,this.playNext()},e.onerror=()=>{this.playing=!1,this.playNext()},e.play().catch(o=>{console.error("Audio playback failed",o),this.playing=!1,this.playNext()})}},Q=class{async sendAudio(e,o,n=[]){let r=new FormData;r.append("audio",e,y.WEBM_FILENAME),r.append("site_id",d.siteId),r.append("session_id",d.sessionId),n&&n.length>0&&r.append("conversation_history",JSON.stringify(n));let c=await fetch(`${d.apiUrl}${A.SHOP}`,{method:tt.POST,body:r});if(!c.ok)throw new Error("ShopBot API request failed");let s=await c.json();s.transcript&&o.onUserMessage?.(s.transcript),s.response_text&&o.onAssistantMessage?.(s.response_text,s.ui_actions||[]),o.onStatusChange?.(l.READY),s.audio_b64&&_e(s.audio_b64),s.ui_actions&&s.ui_actions.length>0&&await Y(s.ui_actions),o.onComplete?.(s)}},q=class{constructor(){this.ws=null,this.connected=!1,this.connecting=null,this.failed=!1,this.retries=0,this.audioQueue=new V,this.callbacks=null,this.turnText=""}async ensureConnected(e=[]){return this.canUseWebSocket()?this.isOpen()?!0:this.connecting?this.connecting:(this.connecting=this.openConnection(e),this.connecting):!1}canUseWebSocket(){return!this.failed&&d.useWebSocket&&"WebSocket"in window}isOpen(){return this.connected&&this.ws?.readyState===WebSocket.OPEN}openConnection(e=[]){return new Promise(o=>{let n=new WebSocket(me(d.apiUrl,d.siteId)),r=!1;this.ws=n;let c=(f=null)=>{r||(r=!0,this.markConnectionFailed(o,f,n))},s=window.setTimeout(()=>{c()},it);n.onopen=()=>{r||(r=!0,this.handleConnectionOpen(s,e,o))},n.onmessage=f=>{this.handleMessage(f).catch(E=>this.handleTransportError(E))},n.onerror=()=>c(s),n.onclose=()=>{this.connected=!1,c(s)}})}markConnectionOpen(){this.connected=!0,this.connecting=null,this.retries=0}handleConnectionOpen(e,o,n){window.clearTimeout(e),this.markConnectionOpen(),this.sendConfig(o),n(!0)}markConnectionFailed(e,o=null,n=null){o&&window.clearTimeout(o),this.connected=!1,this.connecting=null,this.retries+=1,this.retries>=fe&&(this.failed=!0),n&&n.readyState!==WebSocket.CLOSED&&n.close(),e(!1)}sendConfig(e=[]){this.sendJson({type:b.CONFIG,history:e||[],session_id:d.sessionId})}sendJson(e){return!this.ws||this.ws.readyState!==WebSocket.OPEN?!1:(this.ws.send(JSON.stringify(e)),!0)}async sendAudio(e,o,n=[]){if(!await this.ensureConnected(n))return!1;this.callbacks=o,this.turnText="",this.sendConfig(n);let c=await ge(e);return this.sendJson({type:b.AUDIO_CHUNK,data:c}),this.sendJson({type:b.AUDIO_END}),!0}async handleMessage(e){let o=this.callbacks;if(!o)return;let n=this.parseMessage(e.data);if(!n){this.completeWithError(o,"Invalid WebSocket message");return}if(!this.handleIncrementalMessage(n,o)){if(n.type===b.DONE){await this.handleDoneMessage(n,o);return}n.type===b.ERROR&&this.completeWithError(o,n.message||"WebSocket error")}}parseMessage(e){try{let o=JSON.parse(e);return o&&typeof o=="object"?o:null}catch{return null}}handleIncrementalMessage(e,o){return e.type===b.TRANSCRIPT?(o.onUserMessage?.(e.text||""),!0):e.type===b.TEXT_CHUNK?(this.turnText+=e.text||"",o.onAssistantChunk?.(e.text||"",this.turnText),!0):e.type===b.AUDIO_CHUNK?(this.audioQueue.push(e.audio_b64),!0):!1}async handleDoneMessage(e,o){let n=e.response_text||this.turnText;o.onAssistantMessage?.(n,e.ui_actions||[],{streamed:!0}),o.onStatusChange?.(l.READY);try{e.ui_actions&&e.ui_actions.length>0&&await Y(e.ui_actions),o.onComplete?.(e)}catch(r){this.handleTransportError(r)}finally{this.callbacks=null}}completeWithError(e,o){e.onStatusChange?.(l.ERROR),e.onComplete?.({error:o}),this.callbacks=null}handleTransportError(e){console.error("ShopBot WebSocket transport failed",e);let o=this.callbacks;o&&this.completeWithError(o,String(e))}},be=new Q,Te=new q;async function At(t,e,o,n=[]){try{if(d.useWebSocket&&await Te.sendAudio(t,o,n))return;await be.sendAudio(t,o,n)}catch(r){console.error(r),o.onStatusChange?.(l.ERROR),o.onComplete?.({error:String(r)})}}function _e(t){let e=y.DATA_WAV_PREFIX+t;new Audio(e).play().catch(n=>console.error("Audio playback failed",n))}window.__shopbot_identifier="voice-orb";var K=null,St=null,C="";function Et(){if(window.__shopbotBooted||document.getElementById("shopbot-widget"))return;window.__shopbotBooted=!0,J();let t=Z(),e=null;function o(p=et){e&&window.clearTimeout(e),e=window.setTimeout(()=>{t.msgs.innerHTML="",t.chat.classList.remove("visible"),e=null},p)}function n(p){t.status.className="",p===l.RECORDING?(e&&(window.clearTimeout(e),e=null),t.msgs.innerHTML="",t.btn.classList.add("recording"),t.chat.classList.add("visible"),t.status.innerText="Listening...",t.status.classList.add("listening")):p===l.PROCESSING?(t.btn.classList.remove("recording"),t.chat.classList.add("visible"),t.status.innerText="Analyzing...",t.status.classList.add("processing")):p===l.READY?(t.status.innerText="Ready",t.status.classList.add("ready")):p===l.ERROR&&(t.status.innerText="Error",t.status.classList.add("error"),t.btn.classList.remove("recording"))}let r=[],c=null,s="";function f(p,h){let u=[];for(let T of h||[]){let _=T.params||{};if(_[a.PRODUCT_IDS]&&Array.isArray(_[a.PRODUCT_IDS]))for(let X of _[a.PRODUCT_IDS])u.includes(X)||u.push(X);_[a.PRODUCT_ID]&&!u.includes(_[a.PRODUCT_ID])&&u.push(_[a.PRODUCT_ID])}return u.length>0?p+` [PRODUCT_IDS: ${u.join(",")}]`:p}async function E(p){c=null,s="",await At(p,t,{onUserMessage:h=>{x(t,h,"user"),r.push({role:"user",content:h}),r.length>N&&r.shift()},onAssistantChunk:(h,u)=>{s=u,c||(c=x(t,"","ai")),L(t,c,s)},onAssistantMessage:(h,u,T={})=>{T.streamed&&c?L(t,c,h):x(t,h,"ai");let _=f(h,u);r.push({role:"assistant",content:_}),r.length>N&&r.shift(),c=null,s=""},onStatusChange:n,onComplete:()=>o()},r)}let D=at(E,n);K=D,t.btn.addEventListener("click",()=>{D.toggle()}),Ee()&&(ye(),window.setTimeout(()=>{if(r.length>0)return;let p=`Welcome to ${d.brandName}. How can I help you today?`;x(t,p,"ai"),n(l.READY),o(nt),xt(p)},ot))}function xt(t){if(!("speechSynthesis"in window)||!("SpeechSynthesisUtterance"in window))return;C=t;let e=()=>{try{let o=new SpeechSynthesisUtterance(t);o.rate=1,o.pitch=1,o.onstart=()=>{C=""},o.onend=()=>{C=""},window.speechSynthesis.cancel(),window.speechSynthesis.resume(),window.speechSynthesis.speak(o)}catch{}};if(window.speechSynthesis.getVoices().length>0){e();return}window.speechSynthesis.onvoiceschanged=e,window.setTimeout(e,300)}function we(){C&&xt(C)}function Ae(){K?.cancel(),K=null,window.__shopbotBooted=!1,document.getElementById("shopbot-widget")?.remove(),document.getElementById("shopbot-product-panel")?.remove();try{window.speechSynthesis?.cancel()}catch{}}async function Se(){let t=new URL(A.WIDGET_STATUS,d.apiUrl);t.searchParams.set("site_id",d.siteId);let e=await fetch(t.toString(),{cache:"no-store",headers:{Accept:"application/json"}});return e.ok?(await e.json()).enabled!==!1:!0}async function yt(){try{if(await Se()){Et();return}Ae()}catch{Et()}}function Ot(){St||(yt(),St=window.setInterval(yt,st))}function Ee(){if(!d.autoGreet||!Oe())return!1;try{return window.sessionStorage.getItem(It())!=="1"}catch{return!window.__shopbotAutoGreeted}}function ye(){window.__shopbotAutoGreeted=!0;try{window.sessionStorage.setItem(It(),"1")}catch{}}function It(){return`shopbot:auto-greeted:${d.siteId}`}function Oe(){let t=window.location.pathname.replace(/\/+$/,"")||"/";return t==="/"||t.endsWith("/index.html")}document.readyState==="loading"?document.addEventListener("DOMContentLoaded",Ot):Ot();document.addEventListener("pointerdown",we,{capture:!0});})();
