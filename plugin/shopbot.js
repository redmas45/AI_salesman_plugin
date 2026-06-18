(()=>{function nt(){let e=document.createElement("style");e.textContent=`
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
  `,document.head.appendChild(e)}function rt(){let e=document.createElement("div");return e.id="shopbot-widget",e.innerHTML=`
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
  `,document.body.appendChild(e),{btn:document.getElementById("shopbot-btn"),chat:document.getElementById("shopbot-chat"),msgs:document.getElementById("shopbot-msgs"),status:document.getElementById("shopbot-status")}}function I(e,t,o){e.chat.classList.add("visible");let n=document.createElement("div");return n.className=`shopbot-msg ${o}`,n.innerText=t,e.msgs.appendChild(n),e.msgs.scrollTop=e.msgs.scrollHeight,n}function k(e,t,o){t&&(t.innerText=o,e.msgs.scrollTop=e.msgs.scrollHeight)}var r=Object.freeze({ADD_TO_CART:"ADD_TO_CART",CHECKOUT:"CHECKOUT",CLEAR_CART:"CLEAR_CART",FILTER_PRODUCTS:"FILTER_PRODUCTS",NAVIGATE_TO:"NAVIGATE_TO",REMOVE_FROM_CART:"REMOVE_FROM_CART",SHOW_COMPARISON:"SHOW_COMPARISON",SHOW_PRODUCT_DETAIL:"SHOW_PRODUCT_DETAIL",SHOW_PRODUCTS:"SHOW_PRODUCTS",UPDATE_CART_QUANTITY:"UPDATE_CART_QUANTITY"}),a=Object.freeze({PAGE:"page",PRODUCT_ID:"product_id",PRODUCT_IDS:"product_ids",QUANTITY:"quantity",SEARCH_QUERY:"search_query"}),S=new Set(["cart","/cart"]),A="Recommended products",w=Object.freeze({PRODUCTS_BY_IDS:"/v1/products/by-ids",SHOP:"/v1/shop",SHOP_WS:"/v1/ws/shop",WIDGET_STATUS:"/v1/widget/status"}),R=Object.freeze({DATA_WAV_PREFIX:"data:audio/wav;base64,",WEBM_FILENAME:"audio.webm",WEBM_MIME_TYPE:"audio/webm"}),st=Object.freeze({POST:"POST"}),l=Object.freeze({ERROR:"error",PROCESSING:"processing",READY:"ready",RECORDING:"recording"}),H=12,it=2400,at=900,ct=4200,v=1,ut=180,dt=3e3,x=Object.freeze({SHOPBOT_ACTION:"shopbot:action"}),pt=2500,_=Object.freeze({AUDIO_CHUNK:"audio_chunk",AUDIO_END:"audio_end",CONFIG:"config",DONE:"done",ERROR:"error",TEXT_CHUNK:"text_chunk",TRANSCRIPT:"transcript"});function lt(e,t){let o=null,n=null,s=[],c=!1,i=!1;async function f(){try{let u=await navigator.mediaDevices.getUserMedia({audio:!0});n=u,i=!1,o=new MediaRecorder(u),s=[],o.ondataavailable=g=>{g.data.size>0&&s.push(g.data)},o.onstop=async()=>{let g=new Blob(s,{type:R.WEBM_MIME_TYPE});if(h(),i){i=!1;return}await e(g)},o.start(),c=!0,t(l.RECORDING)}catch(u){console.error("Microphone access denied",u),t(l.ERROR)}}function O({discard:u=!1}={}){if(i=u,o&&o.state!=="inactive"){o.stop(),c=!1,u||t(l.PROCESSING);return}c=!1,h(),u||t(l.PROCESSING)}function P(){c?O():f()}function p(){O({discard:!0})}function h(){n&&(n.getTracks().forEach(u=>u.stop()),n=null)}return{toggle:P,cancel:p}}var C=document.currentScript,ht="__AI_PUBLIC_API_URL__",ft="__AI_DEFAULT_SITE_ID__",vt="shopbot:session:";function m(e){return String(e||"").trim()}function Lt(){let e=m(C?.getAttribute("src"));if(!e)return null;try{return new URL(e,window.location.href)}catch{return null}}function Nt(e){return m(C?.getAttribute("data-site-id"))||m(e?.searchParams.get("site"))||m(e?.searchParams.get("site_id"))||m(e?.searchParams.get("shop"))||(ft.startsWith("__AI_")?"":ft)||"site_1"}function Mt(e){let t=m(C?.getAttribute("data-api-url"));if(t)return t.replace(/\/+$/,"");if(!ht.startsWith("__AI_"))return ht.replace(/\/+$/,"");if(e?.origin){let o=e.pathname.replace(/\/shopbot(?:-widget)?\.js$/,"");return`${e.origin}${o}`.replace(/\/+$/,"")}return window.location.origin.replace(/\/+$/,"")}function kt(e){let t=m(window.ShopBotConfig?.sessionId);if(t)return t.slice(0,120);let o=`${vt}${e}`;try{let n=window.sessionStorage.getItem(o);if(n)return n;let s=mt(e);return window.sessionStorage.setItem(o,s),s}catch{return mt(e)}}function mt(e){let t=window.crypto?.randomUUID?.()||`${Date.now()}-${Math.random().toString(16).slice(2)}`;return`${e}-${t}`.slice(0,120)}var _t=Lt(),Tt=Nt(_t),d={siteId:Tt,get sessionId(){return kt(Tt)},apiUrl:Mt(_t),useWebSocket:m(C?.getAttribute("data-use-websocket")).toLowerCase()!=="false",autoGreet:m(C?.getAttribute("data-auto-greet")).toLowerCase()!=="false",brandName:m(C?.getAttribute("data-brand"))||"AI-KART"};var Ht=Object.freeze(["/api/products.json","/products.json","/collections/all/products.json"]),Ft=Object.freeze(["products","data","items","results"]),bt=Object.freeze(["id","product_id","handle","sku"]),At=Object.freeze(["name","title"]),Bt=Object.freeze(["url","href","permalink","product_url"]),Gt=Object.freeze(["image_url","image","thumbnail","featured_image"]),Wt=Object.freeze(["brand","vendor"]),jt=Object.freeze(["category","category_name","product_type"]),Vt=Object.freeze(["description","summary","body_html"]),Yt="Unknown Brand",$t="Products",zt="/product/",qt="/products/",Qt="/",Kt=/^[a-z0-9][a-z0-9-]*$/i,F=null;function T(e){return e==null||typeof e=="object"?"":String(e||"").trim()}function Xt(e){return T(e).toLowerCase().replace(/[^a-z0-9]+/g," ").trim()}function B(e,t){return t.map(o=>T(e?.[o])).filter(Boolean)}function E(e,t){return B(e,t)[0]||""}function Jt(e){let t=E(e,Gt);if(t)return t;let o=e?.image||e?.featured_image;return o&&typeof o=="object"?T(o.src||o.url):Array.isArray(e?.images)?T(e.images[0]?.src||e.images[0]?.url||e.images[0]):""}function Zt(e){let t=T(e);if(!t)return"";try{let o=new URL(t,window.location.origin);return o.origin!==window.location.origin?"":`${o.pathname}${o.search}${o.hash}`}catch{return""}}function te(e){return e==="/products.json"||e.includes("/collections/")?qt:zt}function ee(e,t,o){let n=Zt(E(e,Bt));return n||(!Kt.test(t)||!/[a-z]/i.test(t)?"":`${te(o)}${encodeURIComponent(t)}${Qt}`)}function wt(e,t=""){if(!e)return null;let o=E(e,bt),n=T(e.handle||e.slug||e.product_handle),s=E(e,At),c=Number(e.price||e.amount||e.cost||0);return!o&&!n?null:{id:o,handle:n,name:s,title:T(e.title||s),brand:E(e,Wt)||Yt,category:E(e,jt)||$t,description:E(e,Vt),price:Number.isFinite(c)?c:0,imageUrl:Jt(e),url:ee(e,n||o,t)}}function oe(e){return B(e,bt)}function gt(e){return B(e,At).map(Xt)}function ne(e,t){let o=T(t);return!!(o&&oe(e).includes(o))}function re(e,t){let o=new Set(gt(t));return gt(e).some(n=>o.has(n))}function se(e,t){return!!(e?.imageUrl&&e.imageUrl===t?.imageUrl)}function ie(e){if(Array.isArray(e))return e;for(let t of Ft){let o=e?.[t];if(Array.isArray(o))return o}return[]}async function ae(e){try{let t=await fetch(new URL(e,window.location.origin),{headers:{Accept:"application/json"}});if(!t.ok)return[];let o=await t.json();return ie(o).map(n=>wt(n,e)).filter(Boolean)}catch(t){return console.warn(`[ShopBot] Catalog endpoint lookup failed for ${e}:`,t),[]}}async function ce(){return F||(F=Promise.all(Ht.map(ae)).then(e=>e.flat())),F}async function G(e){let t=(Array.isArray(e)?e:[]).map(T).filter(Boolean);if(!t.length)return[];let o=new URL(w.PRODUCTS_BY_IDS,d.apiUrl);o.searchParams.set("site_id",d.siteId),o.searchParams.set("ids",t.join(","));let n=await fetch(o.toString(),{headers:{Accept:"application/json"}});if(!n.ok)throw new Error("Failed to fetch products from ShopBot API");let s=(await n.json()).map(i=>wt(i)).filter(Boolean),c=new Map(s.map(i=>[String(i.id),i]));return t.map(i=>c.get(i)).filter(Boolean)}async function L(e){let t=T(e);if(!t)return"";let[o]=await G([t]);if(o?.url)return o.url;let n=await ce(),s=n.find(i=>ne(i,t));return s?.url?s.url:o&&n.find(i=>re(i,o)||se(i,o))?.url||""}var ue="https://demo.vercel.store/placeholder.png";function D(e){return String(e??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}function de(){if(document.getElementById("shopbot-product-overlay-styles"))return;let e=document.createElement("style");e.id="shopbot-product-overlay-styles",e.textContent=`
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
  `,document.head.appendChild(e)}function pe(){de();let e=document.getElementById("shopbot-product-panel");return e||(e=document.createElement("div"),e.id="shopbot-product-panel",e.setAttribute("aria-live","polite"),e.innerHTML=`
    <div class="shopbot-product-header">
      <h2 class="shopbot-product-title">${A}</h2>
      <button class="shopbot-product-close" type="button" aria-label="Close recommendations">&times;</button>
    </div>
    <div class="shopbot-product-grid"></div>
  `,e.querySelector(".shopbot-product-close").addEventListener("click",()=>{e.classList.remove("active")}),document.body.appendChild(e),e)}async function le(e){return G(e)}async function he(e){let t=window.ShopCart;if(t&&typeof t.addItem=="function"){await t.addItem(e,v),typeof t.open=="function"&&t.open();return}let o={action:r.ADD_TO_CART,params:{[a.PRODUCT_ID]:e,[a.QUANTITY]:v},parameters:{[a.PRODUCT_ID]:e,[a.QUANTITY]:v}};window.dispatchEvent(new CustomEvent(x.SHOPBOT_ACTION,{detail:o}))}async function fe(e){try{let n=await L(e);if(n){window.location.href=n;return}}catch(n){console.warn("[ShopBot] Product detail URL lookup failed:",n)}let t=window.ShopCart;if(t&&typeof t.showProductDetail=="function"){await t.showProductDetail(e);return}let o={action:r.SHOW_PRODUCT_DETAIL,params:{[a.PRODUCT_ID]:e},parameters:{[a.PRODUCT_ID]:e}};window.dispatchEvent(new CustomEvent(x.SHOPBOT_ACTION,{detail:o}))}function me(e){return e<=1?"count-1":e===2?"count-2":e===3?"count-3":"count-many"}function Te(e){return e<=1?1:e===2?2:3}function Et(e,t){let o=pe(),n=o.querySelector(".shopbot-product-grid"),s=o.querySelector(".shopbot-product-title"),c=e.length;if(o.classList.remove("count-1","count-2","count-3","count-many"),o.classList.add(me(c)),o.style.setProperty("--shopbot-card-count",String(Te(c))),s.textContent=t||A,!c){n.innerHTML='<p class="shopbot-product-empty">No matching products are currently available.</p>',o.classList.add("active"),yt();return}n.innerHTML=e.map(i=>{let f=D(i.id);return`
        <article class="shopbot-product-card" data-product-id="${f}">
          <img class="shopbot-product-image" src="${D(i.imageUrl||ue)}" alt="${D(i.name)}">
          <h3 class="shopbot-product-name">${D(i.name)}</h3>
          <p class="shopbot-product-meta">${D(i.brand)} - $${Number(i.price||0).toFixed(2)} USD</p>
          <div class="shopbot-product-actions">
            <button type="button" data-add="${f}">Add</button>
            <button type="button" class="secondary" data-view="${f}">View</button>
          </div>
        </article>
      `}).join(""),n.querySelectorAll("[data-add]").forEach(i=>{i.addEventListener("click",async()=>{await he(i.getAttribute("data-add"))})}),n.querySelectorAll("[data-view]").forEach(i=>{i.addEventListener("click",async()=>{await fe(i.getAttribute("data-view"))})}),o.classList.add("active"),yt()}function yt(){window.setTimeout(()=>{let e=document.getElementById("shopbot-chat"),t=document.getElementById("shopbot-msgs");t&&(t.innerHTML=""),e&&e.classList.remove("visible")},ut)}async function Ot(e,t=A){try{let o=await le(e);return Et(o,t),!0}catch(o){return console.warn("[ShopBot] Product overlay failed:",o),Et([],t),!0}}function _e(e){let t=e?.params||e?.parameters||{};return{...e||{},params:t,parameters:t}}function St(e){let t=String(e||"").trim();if(!t||/^https?:\/\//i.test(t))return"";if(t==="home"||t==="/")return"/";let o=t.replace(/^\/+|\/+$/g,"");return o?`/${o}/`:"/"}function N(e){let t=String(e||"").trim();return/^\d+$/.test(t)?t:""}function M(e,t=1){let o=Number(e?.[a.QUANTITY]);return Number.isFinite(o)&&o>0?Math.floor(o):t}async function y(e,t){return(await fetch(new URL(e,window.location.origin),{method:"POST",headers:{Accept:"application/json","Content-Type":"application/json"},body:JSON.stringify(t),credentials:"same-origin"})).ok}var W=class{canHandle(t){return t.action===r.SHOW_PRODUCTS}async handle(t){let o=t.parameters||{};return await Ot(o[a.PRODUCT_IDS]||[],o[a.SEARCH_QUERY]||A),!0}},j=class{canHandle(t){return t.action===r.SHOW_PRODUCT_DETAIL}async handle(t){let o="";try{let n=t.parameters?.[a.PRODUCT_ID];o=await L(n)}catch(n){return console.warn("[ShopBot] Product detail URL lookup failed:",n),!1}return o?(window.location.href=o,!0):!1}},V=class{canHandle(t){let o=window.ShopBotConfig;if(!o)return!1;if(t.action===r.ADD_TO_CART)return typeof o.onAddToCart=="function";if(t.action===r.FILTER_PRODUCTS)return typeof o.onFilter=="function";if(t.action===r.CHECKOUT)return typeof o.onCheckout=="function";if(t.action===r.NAVIGATE_TO){let n=t.parameters?.[a.PAGE];return S.has(n)&&typeof o.onOpenCart=="function"?!0:typeof o.onNavigate=="function"}return!1}async handle(t){let o=window.ShopBotConfig;if(t.action===r.ADD_TO_CART)return await o.onAddToCart(t.parameters?.[a.PRODUCT_ID],t.parameters?.[a.QUANTITY]),!0;if(t.action===r.FILTER_PRODUCTS)return await o.onFilter(t.parameters),!0;if(t.action===r.CHECKOUT)return await o.onCheckout(t.parameters),!0;if(t.action===r.NAVIGATE_TO){let n=t.parameters?.[a.PAGE];return S.has(n)&&typeof o.onOpenCart=="function"?(await o.onOpenCart(t.parameters),!0):(await o.onNavigate(n,t.parameters),!0)}return!1}},Y=class{canHandle(t){let o=window.ShopCart;if(!o)return!1;let n=t.parameters?.[a.PAGE];return t.action===r.ADD_TO_CART&&typeof o.addItem=="function"||t.action===r.CLEAR_CART&&typeof o.clear=="function"||t.action===r.NAVIGATE_TO&&S.has(n)&&typeof o.open=="function"||t.action===r.CHECKOUT&&typeof o.checkout=="function"||t.action===r.SHOW_PRODUCTS&&typeof o.showProducts=="function"||t.action===r.SHOW_COMPARISON&&typeof o.showComparison=="function"||t.action===r.FILTER_PRODUCTS&&typeof o.filterProducts=="function"||t.action===r.SHOW_PRODUCT_DETAIL&&typeof o.showProductDetail=="function"||t.action===r.REMOVE_FROM_CART&&typeof o.removeItem=="function"||t.action===r.UPDATE_CART_QUANTITY&&typeof o.updateQuantity=="function"}async handle(t){let o=window.ShopCart,n=t.parameters||{};return t.action===r.ADD_TO_CART?(await o.addItem(n[a.PRODUCT_ID],n[a.QUANTITY]||1),!0):t.action===r.CLEAR_CART?(o.clear(),!0):t.action===r.NAVIGATE_TO?(o.open(),!0):t.action===r.CHECKOUT?(await o.checkout(n),!0):t.action===r.SHOW_PRODUCTS?(await o.showProducts(n[a.PRODUCT_IDS]||[],n[a.SEARCH_QUERY]||A),!0):t.action===r.SHOW_COMPARISON?(await o.showComparison(n[a.PRODUCT_IDS]||[]),!0):t.action===r.FILTER_PRODUCTS?(await o.filterProducts(n),!0):t.action===r.SHOW_PRODUCT_DETAIL?(await o.showProductDetail(n[a.PRODUCT_ID]),!0):t.action===r.REMOVE_FROM_CART?(await o.removeItem(n[a.PRODUCT_ID]),!0):t.action===r.UPDATE_CART_QUANTITY?(await o.updateQuantity(n[a.PRODUCT_ID],Number(n[a.QUANTITY])||0),!0):!1}},$=class{canHandle(t){return this.isShopify()?t.action===r.ADD_TO_CART||t.action===r.CLEAR_CART||t.action===r.CHECKOUT||t.action===r.REMOVE_FROM_CART||t.action===r.UPDATE_CART_QUANTITY||t.action===r.NAVIGATE_TO&&S.has(t.parameters?.[a.PAGE]):!1}isShopify(){return!!(window.Shopify||document.querySelector('meta[name="shopify-checkout-api-token"]')||document.querySelector('script[src*="cdn.shopify.com"]'))}async handle(t){let o=t.parameters||{};if(t.action===r.ADD_TO_CART){let n=N(o.variant_id||o.cart_id||o[a.PRODUCT_ID]);return n?y("/cart/add.js",{items:[{id:n,quantity:M(o)}]}):!1}if(t.action===r.REMOVE_FROM_CART){let n=N(o.cart_id||o.variant_id||o[a.PRODUCT_ID]);return n?y("/cart/change.js",{id:n,quantity:0}):!1}if(t.action===r.UPDATE_CART_QUANTITY){let n=N(o.cart_id||o.variant_id||o[a.PRODUCT_ID]);return n?y("/cart/change.js",{id:n,quantity:M(o,0)}):!1}return t.action===r.CLEAR_CART?y("/cart/clear.js",{}):t.action===r.CHECKOUT?(window.location.href="/checkout",!0):t.action===r.NAVIGATE_TO?(window.location.href="/cart",!0):!1}},z=class{canHandle(t){return this.isWooCommerce()?t.action===r.ADD_TO_CART||t.action===r.CHECKOUT||t.action===r.REMOVE_FROM_CART||t.action===r.UPDATE_CART_QUANTITY||t.action===r.NAVIGATE_TO&&S.has(t.parameters?.[a.PAGE]):!1}isWooCommerce(){return!!(document.body?.classList?.contains("woocommerce")||window.wc_add_to_cart_params||document.querySelector('link[href*="woocommerce"], script[src*="woocommerce"]'))}async handle(t){let o=t.parameters||{};if(t.action===r.ADD_TO_CART){let n=N(o.variant_id||o.cart_id||o[a.PRODUCT_ID]);return n?y("/wp-json/wc/store/cart/add-item",{id:Number(n),quantity:M(o)}):!1}if(t.action===r.REMOVE_FROM_CART){let n=String(o.cart_key||o.key||"").trim();return n?y("/wp-json/wc/store/cart/remove-item",{key:n}):!1}if(t.action===r.UPDATE_CART_QUANTITY){let n=String(o.cart_key||o.key||"").trim();return n?y("/wp-json/wc/store/cart/update-item",{key:n,quantity:M(o,0)}):!1}return t.action===r.CHECKOUT?(window.location.href="/checkout",!0):t.action===r.NAVIGATE_TO?(window.location.href="/cart",!0):!1}},q=class{canHandle(t){return t.action===r.NAVIGATE_TO&&!!St(t.parameters?.[a.PAGE])}handle(t){return window.location.href=St(t.parameters?.[a.PAGE]),!0}},Q=class{canHandle(){return!0}handle(t){return window.dispatchEvent(new CustomEvent(x.SHOPBOT_ACTION,{detail:t})),!0}},K=class{constructor(t){this.adapters=t}async execute(t){for(let o of t||[]){let n=_e(o);if(n.action)for(let s of this.adapters){if(!s.canHandle(n))continue;if(await s.handle(n))break}}}},ge=new K([new W,new j,new V,new Y,new $,new z,new q,new Q]);function X(e){return ge.execute(e)}var be=3;function Ae(e,t){let o=new URL(w.SHOP_WS,e);return o.protocol=o.protocol==="https:"?"wss:":"ws:",o.searchParams.set("site_id",t),o.searchParams.set("session_id",d.sessionId),o.toString()}function we(e){return new Promise((t,o)=>{let n=new FileReader;n.onloadend=()=>{let s=String(n.result||"");t(s.includes(",")?s.split(",").pop():s)},n.onerror=()=>o(n.error||new Error("Failed to read audio blob")),n.readAsDataURL(e)})}var J=class{constructor(){this.queue=[],this.playing=!1}push(t){t&&(this.queue.push(t),this.playNext())}playNext(){if(this.playing||this.queue.length===0)return;this.playing=!0;let t=new Audio(R.DATA_WAV_PREFIX+this.queue.shift());t.onended=()=>{this.playing=!1,this.playNext()},t.onerror=()=>{this.playing=!1,this.playNext()},t.play().catch(o=>{console.error("Audio playback failed",o),this.playing=!1,this.playNext()})}},Z=class{async sendAudio(t,o,n=[]){let s=new FormData;s.append("audio",t,R.WEBM_FILENAME),s.append("site_id",d.siteId),s.append("session_id",d.sessionId),n&&n.length>0&&s.append("conversation_history",JSON.stringify(n));let c=await fetch(`${d.apiUrl}${w.SHOP}`,{method:st.POST,body:s});if(!c.ok)throw new Error("ShopBot API request failed");let i=await c.json();i.transcript&&o.onUserMessage?.(i.transcript),i.response_text&&o.onAssistantMessage?.(i.response_text,i.ui_actions||[]),o.onStatusChange?.(l.READY),i.audio_b64&&Oe(i.audio_b64),i.ui_actions&&i.ui_actions.length>0&&await X(i.ui_actions),o.onComplete?.(i)}},tt=class{constructor(){this.ws=null,this.connected=!1,this.connecting=null,this.failed=!1,this.retries=0,this.audioQueue=new J,this.callbacks=null,this.turnText=""}async ensureConnected(t=[]){return this.canUseWebSocket()?this.isOpen()?!0:this.connecting?this.connecting:(this.connecting=this.openConnection(t),this.connecting):!1}canUseWebSocket(){return!this.failed&&d.useWebSocket&&"WebSocket"in window}isOpen(){return this.connected&&this.ws?.readyState===WebSocket.OPEN}openConnection(t=[]){return new Promise(o=>{let n=new WebSocket(Ae(d.apiUrl,d.siteId)),s=!1;this.ws=n;let c=(f=null)=>{s||(s=!0,this.markConnectionFailed(o,f,n))},i=window.setTimeout(()=>{c()},pt);n.onopen=()=>{s||(s=!0,this.handleConnectionOpen(i,t,o))},n.onmessage=f=>{this.handleMessage(f).catch(O=>this.handleTransportError(O))},n.onerror=()=>c(i),n.onclose=()=>{this.connected=!1,c(i)}})}markConnectionOpen(){this.connected=!0,this.connecting=null,this.retries=0}handleConnectionOpen(t,o,n){window.clearTimeout(t),this.markConnectionOpen(),this.sendConfig(o),n(!0)}markConnectionFailed(t,o=null,n=null){o&&window.clearTimeout(o),this.connected=!1,this.connecting=null,this.retries+=1,this.retries>=be&&(this.failed=!0),n&&n.readyState!==WebSocket.CLOSED&&n.close(),t(!1)}sendConfig(t=[]){this.sendJson({type:_.CONFIG,history:t||[],session_id:d.sessionId})}sendJson(t){return!this.ws||this.ws.readyState!==WebSocket.OPEN?!1:(this.ws.send(JSON.stringify(t)),!0)}async sendAudio(t,o,n=[]){if(!await this.ensureConnected(n))return!1;this.callbacks=o,this.turnText="",this.sendConfig(n);let c=await we(t);return this.sendJson({type:_.AUDIO_CHUNK,data:c}),this.sendJson({type:_.AUDIO_END}),!0}async handleMessage(t){let o=this.callbacks;if(!o)return;let n=this.parseMessage(t.data);if(!n){this.completeWithError(o,"Invalid WebSocket message");return}if(!this.handleIncrementalMessage(n,o)){if(n.type===_.DONE){await this.handleDoneMessage(n,o);return}n.type===_.ERROR&&this.completeWithError(o,n.message||"WebSocket error")}}parseMessage(t){try{let o=JSON.parse(t);return o&&typeof o=="object"?o:null}catch{return null}}handleIncrementalMessage(t,o){return t.type===_.TRANSCRIPT?(o.onUserMessage?.(t.text||""),!0):t.type===_.TEXT_CHUNK?(this.turnText+=t.text||"",o.onAssistantChunk?.(t.text||"",this.turnText),!0):t.type===_.AUDIO_CHUNK?(this.audioQueue.push(t.audio_b64),!0):!1}async handleDoneMessage(t,o){let n=t.response_text||this.turnText;o.onAssistantMessage?.(n,t.ui_actions||[],{streamed:!0}),o.onStatusChange?.(l.READY);try{t.ui_actions&&t.ui_actions.length>0&&await X(t.ui_actions),o.onComplete?.(t)}catch(s){this.handleTransportError(s)}finally{this.callbacks=null}}completeWithError(t,o){t.onStatusChange?.(l.ERROR),t.onComplete?.({error:o}),this.callbacks=null}handleTransportError(t){console.error("ShopBot WebSocket transport failed",t);let o=this.callbacks;o&&this.completeWithError(o,String(t))}},Ee=new Z,ye=new tt;async function Rt(e,t,o,n=[]){try{if(d.useWebSocket&&await ye.sendAudio(e,o,n))return;await Ee.sendAudio(e,o,n)}catch(s){console.error(s),o.onStatusChange?.(l.ERROR),o.onComplete?.({error:String(s)})}}function Oe(e){let t=R.DATA_WAV_PREFIX+e;new Audio(t).play().catch(n=>console.error("Audio playback failed",n))}window.__shopbot_identifier="voice-orb";var et=null,Ct=null,U="";function It(){if(window.__shopbotBooted||document.getElementById("shopbot-widget"))return;window.__shopbotBooted=!0,nt();let e=rt(),t=null;function o(p=it){t&&window.clearTimeout(t),t=window.setTimeout(()=>{e.msgs.innerHTML="",e.chat.classList.remove("visible"),t=null},p)}function n(p){e.status.className="",p===l.RECORDING?(t&&(window.clearTimeout(t),t=null),e.msgs.innerHTML="",e.btn.classList.add("recording"),e.chat.classList.add("visible"),e.status.innerText="Listening...",e.status.classList.add("listening")):p===l.PROCESSING?(e.btn.classList.remove("recording"),e.chat.classList.add("visible"),e.status.innerText="Analyzing...",e.status.classList.add("processing")):p===l.READY?(e.status.innerText="Ready",e.status.classList.add("ready")):p===l.ERROR&&(e.status.innerText="Error",e.status.classList.add("error"),e.btn.classList.remove("recording"))}let s=[],c=null,i="";function f(p,h){let u=[];for(let g of h||[]){let b=g.params||{};if(b[a.PRODUCT_IDS]&&Array.isArray(b[a.PRODUCT_IDS]))for(let ot of b[a.PRODUCT_IDS])u.includes(ot)||u.push(ot);b[a.PRODUCT_ID]&&!u.includes(b[a.PRODUCT_ID])&&u.push(b[a.PRODUCT_ID])}return u.length>0?p+` [PRODUCT_IDS: ${u.join(",")}]`:p}async function O(p){c=null,i="",await Rt(p,e,{onUserMessage:h=>{I(e,h,"user"),s.push({role:"user",content:h}),s.length>H&&s.shift()},onAssistantChunk:(h,u)=>{i=u,c||(c=I(e,"","ai")),k(e,c,i)},onAssistantMessage:(h,u,g={})=>{g.streamed&&c?k(e,c,h):I(e,h,"ai");let b=f(h,u);s.push({role:"assistant",content:b}),s.length>H&&s.shift(),c=null,i=""},onStatusChange:n,onComplete:()=>o()},s)}let P=lt(O,n);et=P,e.btn.addEventListener("click",()=>{P.toggle()}),Ie()&&(xe(),window.setTimeout(()=>{if(s.length>0)return;let p=`Welcome to ${d.brandName}. How can I help you today?`;I(e,p,"ai"),n(l.READY),o(ct),Ut(p)},at))}function Ut(e){if(!("speechSynthesis"in window)||!("SpeechSynthesisUtterance"in window))return;U=e;let t=()=>{try{let o=new SpeechSynthesisUtterance(e);o.rate=1,o.pitch=1,o.onstart=()=>{U=""},o.onend=()=>{U=""},window.speechSynthesis.cancel(),window.speechSynthesis.resume(),window.speechSynthesis.speak(o)}catch{}};if(window.speechSynthesis.getVoices().length>0){t();return}window.speechSynthesis.onvoiceschanged=t,window.setTimeout(t,300)}function Se(){U&&Ut(U)}function Re(){et?.cancel(),et=null,window.__shopbotBooted=!1,document.getElementById("shopbot-widget")?.remove(),document.getElementById("shopbot-product-panel")?.remove();try{window.speechSynthesis?.cancel()}catch{}}async function Ce(){let e=new URL(w.WIDGET_STATUS,d.apiUrl);e.searchParams.set("site_id",d.siteId);let t=await fetch(e.toString(),{cache:"no-store",headers:{Accept:"application/json"}});return t.ok?(await t.json()).enabled!==!1:!0}async function xt(){try{if(await Ce()){It();return}Re()}catch{It()}}function Dt(){Ct||(xt(),Ct=window.setInterval(xt,dt))}function Ie(){if(!d.autoGreet||!De())return!1;try{return window.sessionStorage.getItem(Pt())!=="1"}catch{return!window.__shopbotAutoGreeted}}function xe(){window.__shopbotAutoGreeted=!0;try{window.sessionStorage.setItem(Pt(),"1")}catch{}}function Pt(){return`shopbot:auto-greeted:${d.siteId}`}function De(){let e=window.location.pathname.replace(/\/+$/,"")||"/";return e==="/"||e.endsWith("/index.html")}document.readyState==="loading"?document.addEventListener("DOMContentLoaded",Dt):Dt();document.addEventListener("pointerdown",Se,{capture:!0});})();
