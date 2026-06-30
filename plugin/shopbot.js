(()=>{function Nt(){let t="#5d5fef",e=document.querySelector('meta[name="theme-color"]');if(e&&e.content)t=e.content;else{let b=document.querySelector('button[class*="primary"], .btn-primary, [data-primary]');if(b){let d=window.getComputedStyle(b).backgroundColor;d&&d!=="rgba(0, 0, 0, 0)"&&d!=="transparent"&&(t=d)}}let o=window.matchMedia&&window.matchMedia("(prefers-color-scheme: dark)").matches,n=o?"rgba(24, 24, 27, 0.75)":"rgba(255, 255, 255, 0.85)",r=o?"rgba(255, 255, 255, 0.1)":"rgba(0, 0, 0, 0.08)",s=o?"#f3f4f6":"#111827",a=o?"rgba(255, 255, 255, 0.1)":"rgba(0, 0, 0, 0.05)",p=o?"rgba(0, 0, 0, 0.25)":"#ffffff",T=document.createElement("style");T.textContent=`
    :root {
      --shopbot-primary: ${t};
      --shopbot-surface: ${n};
      --shopbot-border: ${r};
      --shopbot-text: ${s};
      --shopbot-user-bg: ${a};
      --shopbot-bot-bg: ${p};
    }

    #shopbot-widget {
      position: fixed;
      bottom: max(24px, env(safe-area-inset-bottom));
      left: 50%;
      right: auto;
      transform: translateX(-50%);
      z-index: 2147483647;
      font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      color: var(--shopbot-text);
      letter-spacing: -0.01em;
      width: auto;
      max-width: calc(100vw - 32px);
      -webkit-font-smoothing: antialiased;
    }

    #shopbot-btn {
      position: relative;
      width: 64px;
      height: 64px;
      border-radius: 50%;
      border: 1px solid rgba(255, 255, 255, 0.15);
      background: var(--shopbot-primary);
      box-shadow: 0 12px 32px -8px var(--shopbot-primary), 0 4px 12px rgba(0,0,0,0.15);
      color: #ffffff;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: all 0.3s cubic-bezier(0.25, 1, 0.5, 1);
      outline: none;
    }
    
    #shopbot-btn svg {
      position: relative;
      z-index: 2;
      width: 28px;
      height: 28px;
      transition: transform 0.3s ease;
    }

    .shopbot-btn-ring {
      position: absolute;
      inset: -6px;
      border-radius: inherit;
      border: 2px solid var(--shopbot-primary);
      opacity: 0.4;
      pointer-events: none;
      transition: all 0.3s ease;
    }

    #shopbot-btn:hover {
      transform: translateY(-4px) scale(1.02);
      box-shadow: 0 16px 40px -8px var(--shopbot-primary), 0 8px 24px rgba(0,0,0,0.2);
    }
    
    #shopbot-btn:hover .shopbot-btn-ring {
      inset: -10px;
      opacity: 0.15;
    }

    #shopbot-btn.recording {
      background: #ef4444;
      box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7);
      animation: shopbotPulseRecord 1.5s infinite cubic-bezier(0.66, 0, 0, 1);
    }

    #shopbot-chat {
      position: absolute;
      bottom: 96px;
      left: 50%;
      transform: translateX(-50%) translateY(20px) scale(0.95);
      width: min(400px, calc(100vw - 32px));
      max-height: min(600px, calc(100vh - 140px));
      background: var(--shopbot-surface);
      backdrop-filter: blur(24px) saturate(180%);
      -webkit-backdrop-filter: blur(24px) saturate(180%);
      border: 1px solid var(--shopbot-border);
      border-radius: 20px;
      box-shadow: 0 24px 48px -12px rgba(0, 0, 0, 0.18), 0 0 0 1px rgba(255, 255, 255, 0.05) inset;
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 16px;
      opacity: 0;
      pointer-events: none;
      visibility: hidden;
      transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    }

    #shopbot-chat.visible {
      opacity: 1;
      pointer-events: all;
      visibility: visible;
      transform: translateX(-50%) translateY(0) scale(1);
    }

    .shopbot-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--shopbot-border);
    }

    .shopbot-header strong {
      display: block;
      font-size: 16px;
      font-weight: 600;
      line-height: 1.3;
    }

    .shopbot-kicker {
      display: block;
      margin-bottom: 4px;
      color: var(--shopbot-primary);
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .shopbot-live-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #10b981;
      box-shadow: 0 0 0 4px rgba(16, 185, 129, 0.15);
      flex: 0 0 auto;
    }

    #shopbot-msgs {
      padding-right: 4px;
      scrollbar-width: thin;
      scrollbar-color: var(--shopbot-border) transparent;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    
    #shopbot-msgs::-webkit-scrollbar {
      width: 4px;
    }
    #shopbot-msgs::-webkit-scrollbar-thumb {
      background-color: var(--shopbot-border);
      border-radius: 4px;
    }

    .shopbot-msg {
      max-width: 85%;
      padding: 12px 16px;
      border-radius: 16px;
      font-size: 14.5px;
      line-height: 1.5;
      overflow-wrap: anywhere;
      animation: shopbotSlideUpFade 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards;
      opacity: 0;
      transform: translateY(10px);
    }

    .shopbot-msg.user {
      background: var(--shopbot-user-bg);
      align-self: flex-end;
      border-bottom-right-radius: 4px;
    }

    .shopbot-msg.ai {
      background: var(--shopbot-bot-bg);
      align-self: flex-start;
      border-bottom-left-radius: 4px;
      border: 1px solid var(--shopbot-border);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
    }

    #shopbot-status {
      font-size: 12px;
      color: var(--shopbot-text);
      opacity: 0.6;
      text-align: center;
      min-height: 18px;
      margin-top: 4px;
      font-weight: 500;
      transition: all 0.3s ease;
    }

    #shopbot-status.listening {
      color: var(--shopbot-primary);
      opacity: 1;
      animation: shopbotTextPulse 1.5s infinite ease-in-out;
    }

    #shopbot-status.processing {
      color: var(--shopbot-text);
      opacity: 0.8;
      animation: shopbotTextPulse 1.5s infinite ease-in-out;
    }

    @keyframes shopbotSlideUpFade {
      from { opacity: 0; transform: translateY(8px) scale(0.98); }
      to { opacity: 1; transform: translateY(0) scale(1); }
    }

    @keyframes shopbotTextPulse {
      0%, 100% { opacity: 0.5; }
      50% { opacity: 1; }
    }

    @keyframes shopbotPulseRecord {
      to { box-shadow: 0 0 0 24px rgba(239, 68, 68, 0); }
    }

    @media (max-width: 520px) {
      #shopbot-widget {
        bottom: max(16px, env(safe-area-inset-bottom));
      }
      #shopbot-btn {
        width: 56px;
        height: 56px;
      }
      #shopbot-chat {
        bottom: 84px;
        width: calc(100vw - 32px);
      }
    }
  `,document.head.appendChild(T)}var tt="site_1",oo="__AI_";var no="aihub:auto-site-id:",ro=["data-aihub-scope","data-site-scope"],io=["data-site-id","data-aihub-site-id"];function m(t){return String(t||"").trim()}function M(t){return m(t).replace(/\/+$/,"")}function Lt(t,e,o,n=tt){return ao(t,e,o)||so()||m(n)||tt}function ao(t,e,o){for(let s of io){let a=m(t?.getAttribute(s));if(a)return a}let n=m(e?.searchParams.get("site"))||m(e?.searchParams.get("site_id"))||m(e?.searchParams.get("shop"));if(n)return n;let r=m(o);return r&&!r.startsWith(oo)?r:""}function so(){let t=co(),e=`${no}${t}`,o=To(e);if(o)return o;let n=m(window.location.host||window.location.hostname||"site"),r=Dt(),s=ho(`${n}${r?`_${r.replace(/\//g,"_")}`:""}`),a=mo(`auto_${s}_${_o(t)}`);return bo(e,a),a}function co(){return`${window.location.origin}${Dt()}`}function Dt(){return uo()}function uo(){for(let e of ro){let o=m(po()?.getAttribute(e));if(o)return Pt(o)}let t=document.querySelector("meta[name='aihub-site-scope']")?.getAttribute("content");return Pt(t)}function po(){return document.currentScript}function Pt(t){let e=m(t);if(!e||e==="/")return"";try{let n=new URL(e,window.location.href);if(n.origin===window.location.origin){let[r]=lo(n.pathname);return r?`/${r}`:""}}catch{}let[o]=e.replace(/^\/+/,"").split("/");return o?`/${o}`:""}function lo(t=window.location.pathname){return m(t).split("/").map(e=>fo(e).trim()).filter(Boolean)}function fo(t){try{return decodeURIComponent(t)}catch{return String(t||"")}}function ho(t){return m(t).toLowerCase().replace(/[^a-z0-9_-]+/g,"_").replace(/^_+|_+$/g,"")||"site"}function mo(t){return m(t).slice(0,80).replace(/_+$/g,"")||tt}function _o(t){let e=2166136261,o=m(t);for(let n=0;n<o.length;n+=1)e^=o.charCodeAt(n),e=Math.imul(e,16777619);return(e>>>0).toString(36)}function To(t){try{return m(window.localStorage.getItem(t))}catch{return""}}function bo(t,e){try{window.localStorage.setItem(t,e)}catch{}}var g=document.currentScript,Ut="__AI_PUBLIC_API_URL__",Eo="__AI_DEFAULT_SITE_ID__",Ao="shopbot:session:",go="Maya",yo="AI Salesperson",Io="female";function R(t){return String(t||"").trim()}function So(){let t=R(g?.getAttribute("src"));if(!t)return null;try{return new URL(t,window.location.href)}catch{return null}}function Oo(t){let e=R(g?.getAttribute("data-api-url"));if(e)return M(e);if(!Ut.startsWith("__AI_"))return M(Ut);if(t?.origin){let o=t.pathname.replace(/\/shopbot(?:-widget)?\.js$/,"");return M(`${t.origin}${o}`)}return M(window.location.origin)}function xo(t){let e=`${Ao}${t}`;try{let o=window.sessionStorage.getItem(e);if(o)return o;let n=vt(t);return window.sessionStorage.setItem(e,n),n}catch{return vt(t)}}function vt(t){let e=window.crypto?.randomUUID?.()||`${Date.now()}-${Math.random().toString(16).slice(2)}`;return`${t}-${e}`.slice(0,120)}var Mt=So(),Ht=Lt(g,Mt,Eo),l={siteId:Ht,get sessionId(){return xo(Ht)},apiUrl:Oo(Mt),useWebSocket:R(g?.getAttribute("data-use-websocket")).toLowerCase()!=="false",autoGreet:R(g?.getAttribute("data-auto-greet")).toLowerCase()!=="false",brandName:R(g?.getAttribute("data-brand"))||go,assistantTitle:R(g?.getAttribute("data-assistant-title"))||yo,speechVoiceName:R(g?.getAttribute("data-speech-voice")),speechVoicePreference:R(g?.getAttribute("data-speech-voice-preference"))||Io};function Ft(){let t=document.createElement("div");return t.id="shopbot-widget",t.innerHTML=`
    <div id="shopbot-chat">
      <div class="shopbot-header">
        <div>
          <span class="shopbot-kicker"></span>
          <strong class="shopbot-title"></strong>
        </div>
        <span class="shopbot-live-dot" aria-hidden="true"></span>
      </div>
      <div id="shopbot-msgs" style="max-height: 300px; overflow-y: auto; display: flex; flex-direction: column; gap: 8px;"></div>
      <div id="shopbot-status">Ready</div>
    </div>
    <button id="shopbot-btn" aria-label="Talk to Maya">
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
        <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
        <line x1="12" x2="12" y1="19" y2="22"/>
      </svg>
      <span class="shopbot-btn-ring" aria-hidden="true"></span>
    </button>
  `,document.body.appendChild(t),t.querySelector(".shopbot-kicker").textContent=l.brandName,t.querySelector(".shopbot-title").textContent=l.assistantTitle,{btn:document.getElementById("shopbot-btn"),chat:document.getElementById("shopbot-chat"),msgs:document.getElementById("shopbot-msgs"),status:document.getElementById("shopbot-status")}}function F(t,e,o){t.chat.classList.add("visible");let n=document.createElement("div");return n.className=`shopbot-msg ${o}`,n.innerText=e,t.msgs.appendChild(n),t.msgs.scrollTop=t.msgs.scrollHeight,n}function et(t,e,o){e&&(e.innerText=o,t.msgs.scrollTop=t.msgs.scrollHeight)}var i=Object.freeze({ADD_TO_CART:"ADD_TO_CART",CHECKOUT:"CHECKOUT",CHECKOUT_HANDOFF:"CHECKOUT_HANDOFF",CHECK_APPOINTMENT_AVAILABILITY:"CHECK_APPOINTMENT_AVAILABILITY",CHECK_AVAILABILITY:"CHECK_AVAILABILITY",CHECK_DELIVERY_AVAILABILITY:"CHECK_DELIVERY_AVAILABILITY",CHECK_ELIGIBILITY_SOFT:"CHECK_ELIGIBILITY_SOFT",CHECK_PREREQUISITES:"CHECK_PREREQUISITES",CLEAR_CART:"CLEAR_CART",CLEAR_FILTERS:"CLEAR_FILTERS",CLEAR_HISTORY:"CLEAR_HISTORY",BUILD_ITINERARY:"BUILD_ITINERARY",BUILD_LEARNING_PATH:"BUILD_LEARNING_PATH",CAPTURE_LEAD:"CAPTURE_LEAD",CAPTURE_PATIENT_LEAD:"CAPTURE_PATIENT_LEAD",FILTER_PRODUCTS:"FILTER_PRODUCTS",FILTER_ENTITIES:"FILTER_ENTITIES",COMPARE_ENTITIES:"COMPARE_ENTITIES",CONTACT_AGENT:"CONTACT_AGENT",HANDOFF_TO_ADVISOR:"HANDOFF_TO_ADVISOR",HANDOFF_TO_AGENT:"HANDOFF_TO_AGENT",HANDOFF_TO_CLINIC:"HANDOFF_TO_CLINIC",HANDOFF_TO_HUMAN:"HANDOFF_TO_HUMAN",HANDOFF_TO_LAWYER:"HANDOFF_TO_LAWYER",HANDOFF_TO_LICENSED_AGENT:"HANDOFF_TO_LICENSED_AGENT",HANDOFF_TO_RECRUITER:"HANDOFF_TO_RECRUITER",JOIN_WAITLIST:"JOIN_WAITLIST",MATCH_JOBS:"MATCH_JOBS",NAVIGATE_TO:"NAVIGATE_TO",OPEN_CLAIM_FLOW:"OPEN_CLAIM_FLOW",OPEN_CONTACT:"OPEN_CONTACT",OPEN_DISCLOSURE:"OPEN_DISCLOSURE",OPEN_ENTITY_DETAIL:"OPEN_ENTITY_DETAIL",OPEN_LOCATION:"OPEN_LOCATION",OPEN_MAP:"OPEN_MAP",OPEN_POLICY:"OPEN_POLICY",OPEN_PROJECTS:"OPEN_PROJECTS",OPEN_RENEWAL_FLOW:"OPEN_RENEWAL_FLOW",OPEN_SERVICES:"OPEN_SERVICES",OPEN_SYLLABUS:"OPEN_SYLLABUS",OPEN_TELECONSULT:"OPEN_TELECONSULT",REMOVE_FROM_CART:"REMOVE_FROM_CART",REQUEST_APPOINTMENT:"REQUEST_APPOINTMENT",REQUEST_CALLBACK:"REQUEST_CALLBACK",REQUEST_CONSULTATION:"REQUEST_CONSULTATION",REQUEST_COUNSELOR_CALLBACK:"REQUEST_COUNSELOR_CALLBACK",REQUEST_ESTIMATE:"REQUEST_ESTIMATE",REQUEST_SITE_VISIT:"REQUEST_SITE_VISIT",REQUEST_TEST_DRIVE:"REQUEST_TEST_DRIVE",REQUEST_VIEWING:"REQUEST_VIEWING",RUN_DOM_SEQUENCE:"RUN_DOM_SEQUENCE",RUN_AFFORDABILITY_CALCULATOR:"RUN_AFFORDABILITY_CALCULATOR",RUN_CALCULATOR:"RUN_CALCULATOR",SAVE_SEARCH:"SAVE_SEARCH",SCHEDULE_ORDER:"SCHEDULE_ORDER",SEARCH_AVAILABILITY:"SEARCH_AVAILABILITY",SET_LOCATION:"SET_LOCATION",SHOW_COMPARISON:"SHOW_COMPARISON",SHOW_EMERGENCY_NOTICE:"SHOW_EMERGENCY_NOTICE",SHOW_ENTITIES:"SHOW_ENTITIES",SHOW_PRODUCT_DETAIL:"SHOW_PRODUCT_DETAIL",SHOW_PRODUCTS:"SHOW_PRODUCTS",SORT_ENTITIES:"SORT_ENTITIES",SORT_PRODUCTS:"SORT_PRODUCTS",START_APPLICATION:"START_APPLICATION",START_BOOKING:"START_BOOKING",START_ENROLLMENT:"START_ENROLLMENT",START_INTAKE:"START_INTAKE",START_QUOTE:"START_QUOTE",START_TICKET_PURCHASE:"START_TICKET_PURCHASE",UPDATE_CART_QUANTITY:"UPDATE_CART_QUANTITY",UPDATE_PREFERENCES:"UPDATE_PREFERENCES",BOOK_APPOINTMENT_REQUEST:"BOOK_APPOINTMENT_REQUEST"}),u=Object.freeze({ENTITY_ID:"entity_id",ENTITY_IDS:"entity_ids",MESSAGE:"message",PAGE:"page",PRODUCT_ID:"product_id",PRODUCT_IDS:"product_ids",QUANTITY:"quantity",REASON:"reason",SEARCH_QUERY:"search_query",URL:"url"}),kt=new Set(["cart","/cart"]),y="Recommended products",C="Relevant options",I=Object.freeze({KNOWLEDGE_BY_IDS:"/v1/knowledge/by-ids",PRODUCTS_BY_IDS:"/v1/products/by-ids",SHOP:"/v1/shop",SHOP_WS:"/v1/ws/shop",WIDGET_STATUS:"/v1/widget/status"}),D=Object.freeze({DATA_WAV_PREFIX:"data:audio/wav;base64,",WEBM_FILENAME:"audio.webm",WEBM_MIME_TYPE:"audio/webm"}),Bt=Object.freeze({POST:"POST"}),h=Object.freeze({ERROR:"error",PROCESSING:"processing",READY:"ready",RECORDING:"recording"}),ot=12,Yt=2400,zt=900,Gt=4200,nt=1,U=180,$t=3e3,k=Object.freeze({SHOPBOT_ACTION:"shopbot:action"}),Vt=2500,S=Object.freeze({AUDIO_CHUNK:"audio_chunk",AUDIO_END:"audio_end",CONFIG:"config",DONE:"done",ERROR:"error",TEXT_CHUNK:"text_chunk",TRANSCRIPT:"transcript"});function Wt(t,e){let o=null,n=null,r=[],s=!1,a=!1;async function p(){try{let f=await navigator.mediaDevices.getUserMedia({audio:!0});n=f,a=!1,o=new MediaRecorder(f),r=[],o.ondataavailable=x=>{x.data.size>0&&r.push(x.data)},o.onstop=async()=>{let x=new Blob(r,{type:D.WEBM_MIME_TYPE});if(_(),a){a=!1;return}await t(x)},o.start(),s=!0,e(h.RECORDING)}catch(f){console.error("Microphone access denied",f),e(h.ERROR)}}function T({discard:f=!1}={}){if(a=f,o&&o.state!=="inactive"){o.stop(),s=!1,f||e(h.PROCESSING);return}s=!1,_(),f||e(h.PROCESSING)}function b(){s?T():p()}function d(){T({discard:!0})}function _(){n&&(n.getTracks().forEach(f=>f.stop()),n=null)}return{toggle:b,cancel:d}}var jt="shopify",qt="woocommerce",wo="custom";function W(t){let e=String(t||"").trim();return/^\d+$/.test(e)?e:""}function j(t,e=1){let o=Number(t?.[u.QUANTITY]);return Number.isFinite(o)&&o>0?Math.floor(o):e}async function N(t,e){return(await fetch(new URL(t,window.location.origin),{method:"POST",headers:{Accept:"application/json","Content-Type":"application/json"},body:JSON.stringify(e),credentials:"same-origin"})).ok}function Ro(){return Co()?jt:No()?qt:wo}async function Kt(t){let e=Ro();return e===jt?Po(t):e===qt?Lo(t):!1}function Co(){return!!(window.Shopify||document.querySelector('meta[name="shopify-checkout-api-token"]')||document.querySelector('script[src*="cdn.shopify.com"]'))}function No(){return!!(document.body?.classList?.contains("woocommerce")||window.wc_add_to_cart_params||document.querySelector('link[href*="woocommerce"], script[src*="woocommerce"]'))}async function Po(t){let e=t.parameters||{};if(t.action===i.ADD_TO_CART){let o=W(e.variant_id||e.cart_id||e[u.PRODUCT_ID]);return o?N("/cart/add.js",{items:[{id:o,quantity:j(e)}]}):!1}if(t.action===i.REMOVE_FROM_CART){let o=W(e.cart_id||e.variant_id||e[u.PRODUCT_ID]);return o?N("/cart/change.js",{id:o,quantity:0}):!1}if(t.action===i.UPDATE_CART_QUANTITY){let o=W(e.cart_id||e.variant_id||e[u.PRODUCT_ID]);return o?N("/cart/change.js",{id:o,quantity:j(e,0)}):!1}return t.action===i.CLEAR_CART?N("/cart/clear.js",{}):t.action===i.CHECKOUT?q("/checkout"):Qt(t)?q("/cart"):!1}async function Lo(t){let e=t.parameters||{};if(t.action===i.ADD_TO_CART){let o=W(e.variant_id||e.cart_id||e[u.PRODUCT_ID]);return o?N("/wp-json/wc/store/cart/add-item",{id:Number(o),quantity:j(e)}):!1}if(t.action===i.REMOVE_FROM_CART){let o=String(e.cart_key||e.key||"").trim();return o?N("/wp-json/wc/store/cart/remove-item",{key:o}):!1}if(t.action===i.UPDATE_CART_QUANTITY){let o=String(e.cart_key||e.key||"").trim();return o?N("/wp-json/wc/store/cart/update-item",{key:o,quantity:j(e,0)}):!1}return t.action===i.CHECKOUT?q("/checkout"):Qt(t)?q("/cart"):!1}function Qt(t){return t.action===i.NAVIGATE_TO&&kt.has(t.parameters?.[u.PAGE])}function q(t){return window.location.href=t,!0}function Xt(t){if(!t||typeof t!="string")return[];let e=[];for(let o of Do()){try{e.push(...Array.from(o.querySelectorAll(t)))}catch{return[]}if(e.length>=600)return e.slice(0,600)}return Mo(e)}function Do(){let t=[],e=new Set,o=[document];for(;o.length&&t.length<60;){let n=o.shift();!n||e.has(n)||(e.add(n),t.push(n),o.push(...Uo(n)))}return t}function Uo(t){let e=[];for(let o of vo(t)){o.shadowRoot&&e.push(o.shadowRoot);let n=Ho(o);n&&e.push(n)}return e}function vo(t){try{return Array.from(t.querySelectorAll("*"))}catch{return[]}}function Ho(t){if(String(t?.tagName||"").toLowerCase()!=="iframe")return null;try{let e=t.contentDocument;return e?.documentElement?e:null}catch{return null}}function Mo(t){return Array.from(new Set(t))}var Wr=Object.freeze([c("stripe",["stripe","stripe.com","checkout.stripe.com","js.stripe.com"]),c("paypal",["paypal","paypal.com","paypalobjects.com"]),c("razorpay",["razorpay","checkout.razorpay.com"]),c("paytm",["paytm","securegw.paytm.in"]),c("cashfree",["cashfree","cashfree.com"]),c("checkout.com",["checkout.com","cko-session-id"]),c("adyen",["adyen","checkoutshopper"]),c("square",["squareup","squarecdn","square.site"]),c("braintree",["braintree","braintreegateway"]),c("mollie",["mollie","mollie.com"]),c("klarna",["klarna","klarna.com"]),c("afterpay",["afterpay","afterpay.com","clearpay"]),c("payu",["payu","payu.in","payu.com"]),c("paystack",["paystack","paystack.co"]),c("phonepe",["phonepe","phonepe.com"]),c("billdesk",["billdesk","billdesk.com"]),c("authorize.net",["authorize.net","accept.authorize.net"])]),Jt=Object.freeze([c("calendly",["calendly","calendly.com"]),c("acuity",["acuityscheduling","squarespace scheduling"]),c("booksy",["booksy","booksy.com"]),c("zocdoc",["zocdoc","zocdoc.com"]),c("appointlet",["appointlet","appointlet.com"]),c("setmore",["setmore","setmore.com"]),c("cal.com",["cal.com","calcom"]),c("google_calendar",["calendar.google.com","google calendar"]),c("microsoft_bookings",["microsoft bookings","outlook.office365.com/book"]),c("simplybook",["simplybook","simplybook.me"]),c("tidycal",["tidycal","tidycal.com"]),c("savvycal",["savvycal","savvycal.com"]),c("fresha",["fresha","fresha.com"])]),Zt=Object.freeze([c("google_maps",["google.com/maps","maps.googleapis","maps.google"]),c("mapbox",["mapbox","mapbox.com"]),c("openstreetmap",["openstreetmap","osm.org"]),c("leaflet",["leaflet","leafletjs"]),c("here_maps",["here.com","hereapi","wego.here.com"]),c("bing_maps",["bing.com/maps","virtualearth"]),c("mappls",["mappls","mapmyindia"])]),te=Object.freeze([c("whatsapp",["wa.me","api.whatsapp.com","web.whatsapp.com"]),c("telegram",["t.me/","telegram.me"]),c("messenger",["m.me/","messenger.com/t"]),c("zendesk",["zendesk.com","zdassets.com/hc"]),c("intercom",["intercom.help","intercom.com"]),c("freshchat",["freshchat.com"])]),jr=Object.freeze([c("recaptcha",["recaptcha","g-recaptcha","google.com/recaptcha"]),c("hcaptcha",["hcaptcha","h-captcha"]),c("turnstile",["turnstile","challenges.cloudflare.com"]),c("cloudflare_challenge",["cf-chl","cloudflare challenge"])]);function c(t,e){return{name:t,tokens:e}}function rt(t,e,o=10){let n=it(t);return e.filter(r=>r.tokens.some(s=>n.includes(s))).map(r=>r.name).slice(0,o)}function it(t){return String(t||"").replace(/\s+/g," ").trim().toLowerCase()}var ee="a[href], iframe[src]",Fo="a[href]",ne=new Set(["http:","https:"]),K=new Set(["mailto:","tel:"]),ko=Object.freeze([u.URL,"href","link","target_url","provider_url","booking_url","appointment_url","calendar_url","map_url","location_url","contact_url"]),re=new Set([i.OPEN_MAP,i.OPEN_LOCATION,i.SET_LOCATION]),ie=new Set([i.CHECK_APPOINTMENT_AVAILABILITY,i.REQUEST_APPOINTMENT,i.BOOK_APPOINTMENT_REQUEST,i.REQUEST_CONSULTATION,i.REQUEST_SITE_VISIT,i.START_BOOKING]),ae=new Set([i.OPEN_CONTACT,i.CONTACT_AGENT,i.REQUEST_CALLBACK,i.REQUEST_COUNSELOR_CALLBACK,i.HANDOFF_TO_ADVISOR,i.HANDOFF_TO_AGENT,i.HANDOFF_TO_CLINIC,i.HANDOFF_TO_HUMAN,i.HANDOFF_TO_LAWYER,i.HANDOFF_TO_LICENSED_AGENT,i.HANDOFF_TO_RECRUITER]);function se(t){let e=pe(t);return re.has(e)||ie.has(e)||ae.has(e)}async function ce(t){let e=pe(t);return re.has(e)?at(t,Zt,ee,st):ie.has(e)?at(t,Jt,ee,st):ae.has(e)?at(t,te,Fo,Go):!1}function at(t,e,o,n){let r=Bo(t?.parameters||t?.params||{},e,n);if(r)return oe(r);let s=Yo(o,e,n);return s?oe(s):!1}function Bo(t,e,o){for(let n of ko){let r=ue(t?.[n]);if(r&&o(r,e))return r}return null}function Yo(t,e,o){for(let n of Xt(t)){let r=zo(n);if(!(!r||!o(r,e))&&$o(r,n,e))return r}return null}function zo(t){return ue(t?.getAttribute?.("href")||t?.getAttribute?.("src"))}function st(t,e){return ne.has(t.protocol)&&rt(t.href,e).length>0}function Go(t,e){return K.has(t.protocol)?!0:st(t,e)}function $o(t,e,o){if(K.has(t.protocol))return!0;let n=[t.href,e?.textContent||"",e?.getAttribute?.("aria-label")||"",e?.getAttribute?.("title")||""].join(" ");return rt(it(n),o).length>0}function oe(t){if(K.has(t.protocol)||t.origin===window.location.origin)return window.location.href=t.href,!0;let e=window.open(t.href,"_blank","noopener,noreferrer");return e?(e.opener=null,!0):(window.location.href=t.href,!0)}function ue(t){let e=String(t||"").trim();if(!e||e.startsWith("#"))return null;try{let o=new URL(e,window.location.href);return ne.has(o.protocol)||K.has(o.protocol)?o:null}catch{return null}}function pe(t){return String(t?.action||"").trim().toUpperCase()}var Vo=Object.freeze(["title","name"]),Wo=Object.freeze(["summary","description","body"]),jo=Object.freeze(["image_url","imageUrl","image","thumbnail"]),qo=Object.freeze(["url","href","permalink","source_url"]),Ko="knowledge_item",Qo=30;function E(t){return t==null||typeof t=="object"?"":String(t||"").trim()}function Xo(t){let e=new Set;return(Array.isArray(t)?t:[]).map(E).filter(Boolean).filter(o=>e.has(o)||e.size>=Qo?!1:(e.add(o),!0))}function Q(t,e){for(let o of e){let n=E(t?.[o]);if(n)return n}return""}function B(t){return t&&typeof t=="object"&&!Array.isArray(t)?t:{}}function Jo(t){let e=Zo([t?.price,t?.amount,t?.premium,t?.premium_min,t?.monthly_premium,t?.annual_premium,t?.min_price,t?.starting_price]),o=E(t?.currency||"INR");return!Number.isFinite(e)||e<=0?"":`${o} ${e.toLocaleString()}`}function Zo(t){for(let e of t){let o=Number(String(e??"").replace(/,/g,""));if(Number.isFinite(o)&&o>0)return o}return 0}function tn(t){return!t||typeof t!="object"?"":t.in_stock===!0?"Available":t.in_stock===!1?"Unavailable":E(t.status||t.availability||"")}function en(t){let e=E(t);if(!e)return"";try{let o=new URL(e,window.location.origin);return/^https?:$/i.test(o.protocol)?o.origin===window.location.origin?`${o.pathname}${o.search}${o.hash}`:o.toString():""}catch{return""}}function on(t){if(!t)return null;let e=E(t.id);if(!e)return null;let o=B(t.pricing),n=B(t.availability);return{id:e,externalId:E(t.external_id),entityType:E(t.entity_type||t.category_name)||Ko,title:Q(t,Vo)||e,subtitle:E(t.subtitle||t.category_name||t.entity_type),summary:Q(t,Wo),body:E(t.body),url:en(Q(t,qo)),imageUrl:Q(t,jo),attributes:B(t.attributes),pricing:o,availability:n,location:B(t.location),contact:B(t.contact),displayPrice:Jo(o),displayAvailability:tn(n)}}async function ct(t){let e=Xo(t);if(!e.length)return[];let o=new URL(I.KNOWLEDGE_BY_IDS,l.apiUrl);o.searchParams.set("site_id",l.siteId),o.searchParams.set("ids",e.join(","));let n=await fetch(o.toString(),{headers:{Accept:"application/json"}});if(!n.ok)throw new Error("Failed to fetch entities from AI Hub API");let r=(await n.json()).map(on).filter(Boolean),s=new Map(r.map(a=>[String(a.id),a]));return e.map(a=>s.get(a)).filter(Boolean)}async function le(t){let[e]=await ct([t]);return e?.url||""}var nn=2,de=Number.POSITIVE_INFINITY,X=Number.NEGATIVE_INFINITY,ut=[],pt=C;function O(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}function _e(t){return String(t||"item").replace(/[_-]+/g," ").trim().split(/\s+/).slice(0,nn).join(" ")}function rn(){if(document.getElementById("shopbot-entity-overlay-styles"))return;let t=document.createElement("style");t.id="shopbot-entity-overlay-styles",t.textContent=`
    #shopbot-entity-panel {
      position: fixed;
      left: 50%;
      bottom: 96px;
      z-index: 2147483638;
      width: min(calc(100vw - 32px), var(--shopbot-entity-panel-width, 760px));
      max-height: min(72vh, 620px);
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
    #shopbot-entity-panel.active {
      transform: translate(-50%, 0);
      opacity: 1;
      pointer-events: auto;
    }
    #shopbot-entity-panel.count-1 { --shopbot-entity-panel-width: 420px; }
    #shopbot-entity-panel.count-2 { --shopbot-entity-panel-width: 660px; }
    #shopbot-entity-panel.count-3,
    #shopbot-entity-panel.count-many { --shopbot-entity-panel-width: 980px; }
    .shopbot-entity-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
      padding: 14px 16px;
      border-bottom: 1px solid rgba(22, 22, 21, 0.1);
    }
    .shopbot-entity-title {
      margin: 0;
      color: #161615;
      font-size: 15px;
      font-weight: 800;
      line-height: 1.25;
      letter-spacing: 0;
    }
    .shopbot-entity-close {
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
    .shopbot-entity-grid {
      display: grid;
      grid-template-columns: repeat(var(--shopbot-entity-card-count, 2), minmax(0, 1fr));
      gap: 12px;
      padding: 14px;
      overflow: auto;
      scrollbar-width: thin;
    }
    .shopbot-entity-card {
      display: grid;
      grid-template-rows: auto auto auto 1fr auto;
      gap: 10px;
      min-width: 0;
      border: 1px solid rgba(22, 22, 21, 0.1);
      border-radius: 8px;
      background: #ffffff;
      padding: 12px;
    }
    .shopbot-entity-media {
      display: grid;
      place-items: center;
      min-height: 116px;
      border-radius: 8px;
      background: #f1f2ee;
      overflow: hidden;
    }
    .shopbot-entity-media img {
      width: 100%;
      height: 150px;
      object-fit: contain;
      padding: 8px;
    }
    .shopbot-entity-badge {
      display: grid;
      place-items: center;
      width: 100%;
      min-height: 116px;
      padding: 12px;
      color: #534d44;
      font-size: 13px;
      font-weight: 760;
      text-align: center;
      text-transform: capitalize;
    }
    .shopbot-entity-name {
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
    .shopbot-entity-meta {
      margin: 0;
      color: #686660;
      font-size: 12px;
      line-height: 1.35;
      overflow-wrap: anywhere;
      text-transform: capitalize;
    }
    .shopbot-entity-summary {
      margin: 0;
      color: #3d3933;
      font-size: 13px;
      line-height: 1.42;
      display: -webkit-box;
      -webkit-line-clamp: 4;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    .shopbot-entity-facts {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }
    .shopbot-entity-fact {
      border: 1px solid rgba(22, 22, 21, 0.1);
      border-radius: 999px;
      padding: 5px 8px;
      color: #534d44;
      background: #f7f7f3;
      font-size: 11px;
      font-weight: 700;
      line-height: 1;
      overflow-wrap: anywhere;
    }
    .shopbot-entity-actions {
      display: flex;
      justify-content: flex-end;
      align-self: end;
    }
    .shopbot-entity-actions button {
      min-height: 36px;
      min-width: 86px;
      border: 1px solid rgba(22, 22, 21, 0.12);
      border-radius: 8px;
      background: #161615;
      color: #ffffff;
      cursor: pointer;
      font-size: 12px;
      font-weight: 760;
      line-height: 1;
    }
    .shopbot-entity-empty {
      margin: 0;
      padding: 14px;
      color: #686660;
      font-size: 14px;
    }
    @media (max-width: 720px) {
      #shopbot-entity-panel {
        bottom: 86px;
        width: min(calc(100vw - 20px), 520px);
      }
      #shopbot-entity-panel.count-2,
      #shopbot-entity-panel.count-3,
      #shopbot-entity-panel.count-many {
        --shopbot-entity-card-count: 2;
      }
      .shopbot-entity-grid {
        padding: 12px;
      }
      .shopbot-entity-media img {
        height: 132px;
      }
    }
    @media (max-width: 430px) {
      #shopbot-entity-panel {
        bottom: 82px;
      }
      #shopbot-entity-panel.count-1,
      #shopbot-entity-panel.count-2,
      #shopbot-entity-panel.count-3,
      #shopbot-entity-panel.count-many {
        --shopbot-entity-card-count: 1;
      }
    }
  `,document.head.appendChild(t)}function an(){rn();let t=document.getElementById("shopbot-entity-panel");return t||(t=document.createElement("div"),t.id="shopbot-entity-panel",t.setAttribute("aria-live","polite"),t.innerHTML=`
    <div class="shopbot-entity-header">
      <h2 class="shopbot-entity-title">${C}</h2>
      <button class="shopbot-entity-close" type="button" aria-label="Close recommendations">&times;</button>
    </div>
    <div class="shopbot-entity-grid"></div>
  `,t.querySelector(".shopbot-entity-close").addEventListener("click",()=>{t.classList.remove("active")}),document.body.appendChild(t),t)}function sn(t){return t<=1?"count-1":t===2?"count-2":t===3?"count-3":"count-many"}function cn(t){return t<=1?1:t===2?2:3}function un(t){return[t.displayPrice,t.displayAvailability,t.location?.city,t.attributes?.category].map(e=>String(e||"").trim()).filter(Boolean).slice(0,3)}function pn(t){return t.imageUrl?`
      <div class="shopbot-entity-media">
        <img src="${O(t.imageUrl)}" alt="${O(t.title)}">
      </div>
    `:`
    <div class="shopbot-entity-media">
      <div class="shopbot-entity-badge">${O(_e(t.entityType))}</div>
    </div>
  `}function ln(t){let e=un(t);return e.length?`
    <div class="shopbot-entity-facts">
      ${e.map(o=>`<span class="shopbot-entity-fact">${O(o)}</span>`).join("")}
    </div>
  `:""}function dn(t){return t.url?`
    <div class="shopbot-entity-actions">
      <button type="button" data-view-entity="${O(t.id)}">Open</button>
    </div>
  `:""}function lt(t,e){let o=an(),n=o.querySelector(".shopbot-entity-grid"),r=o.querySelector(".shopbot-entity-title"),s=t.length;if(ut=Array.isArray(t)?[...t]:[],pt=e||C,o.classList.remove("count-1","count-2","count-3","count-many"),o.classList.add(sn(s)),o.style.setProperty("--shopbot-entity-card-count",String(cn(s))),r.textContent=pt,!s){n.innerHTML='<p class="shopbot-entity-empty">No matching records are currently available.</p>',o.classList.add("active"),fe();return}n.innerHTML=t.map(a=>`
        <article class="shopbot-entity-card" data-entity-id="${O(a.id)}">
          ${pn(a)}
          <h3 class="shopbot-entity-name">${O(a.title)}</h3>
          <p class="shopbot-entity-meta">${O(a.subtitle||_e(a.entityType))}</p>
          <p class="shopbot-entity-summary">${O(a.summary||a.body||"Details are available on the website.")}</p>
          ${ln(a)}
          ${dn(a)}
        </article>
      `).join(""),n.querySelectorAll("[data-view-entity]").forEach(a=>{a.addEventListener("click",async()=>{await dt(a.getAttribute("data-view-entity"))})}),o.classList.add("active"),fe()}function fn(t){if(!t)return!1;try{let e=new URL(t,window.location.origin);return e.origin===window.location.origin?(window.location.href=`${e.pathname}${e.search}${e.hash}`,!0):(window.open(e.toString(),"_blank","noopener,noreferrer"),!0)}catch{return!1}}function fe(){window.setTimeout(()=>{let t=document.getElementById("shopbot-chat"),e=document.getElementById("shopbot-msgs");e&&(e.innerHTML=""),t&&t.classList.remove("visible")},U)}async function dt(t){let e=await le(t);return fn(e)}async function Te(t,e=C){try{let o=await ct(t);return lt(o,e),!0}catch(o){return console.warn("[AI Hub Widget] Entity overlay failed:",o),lt([],e),!0}}function be(t){return t[u.ENTITY_IDS]||t.ids||t.items||[]}function Ee(t={}){if(!ut.length)return!1;let e=String(t.sort_by||t.sortBy||"price_asc").trim().toLowerCase(),o=[...ut].sort((r,s)=>hn(r,s,e)),n=_n(pt,e);return lt(o,n),!0}function hn(t,e,o){return o==="price_desc"?J(e,X)-J(t,X):o==="rating"?he(e,X)-he(t,X):o==="newest"?me(e)-me(t):J(t,de)-J(e,de)}function J(t,e){return Ae([t?.pricing?.price,t?.pricing?.amount,t?.pricing?.premium,t?.pricing?.premium_min,t?.pricing?.monthly_premium,t?.pricing?.annual_premium,t?.pricing?.min_price,t?.pricing?.starting_price,t?.attributes?.price,t?.attributes?.amount,t?.attributes?.premium,t?.attributes?.monthly_premium,t?.attributes?.annual_premium,t?.displayPrice],e)}function he(t,e){return Ae([t?.attributes?.rating,t?.attributes?.review_rating,t?.attributes?.stars,t?.availability?.rating],e)}function me(t){let e=t?.attributes?.updated_at||t?.attributes?.date||t?.availability?.updated_at||"",o=Date.parse(String(e||""));return Number.isFinite(o)?o:0}function Ae(t,e){for(let o of t){let n=mn(o);if(Number.isFinite(n))return n}return e}function mn(t){if(typeof t=="number")return t;let e=String(t??"").replace(/,/g,"").match(/-?\d+(?:\.\d+)?/);return e?Number(e[0]):Number.NaN}function _n(t,e){let o={price_asc:"sorted low to high",price_desc:"sorted high to low",rating:"sorted by rating",newest:"newest first"};return`${String(t||C).replace(/\s+-\s+sorted.*$/i,"")} - ${o[e]||o.price_asc}`}function ge(t){return t.action===i.SHOW_ENTITIES||t.action===i.COMPARE_ENTITIES||t.action===i.OPEN_ENTITY_DETAIL||t.action===i.SORT_ENTITIES}async function ye(t){return t.action===i.SHOW_ENTITIES||t.action===i.COMPARE_ENTITIES?Tn(t.parameters||{}):t.action===i.OPEN_ENTITY_DETAIL?dt(t.parameters?.[u.ENTITY_ID]||t.parameters?.id):t.action===i.SORT_ENTITIES?Ee(t.parameters||{}):!1}function Tn(t){return Te(be(t),t[u.SEARCH_QUERY]||t.title||C)}var Y="shopbot-handoff-panel",Ie="shopbot-handoff-overlay-styles",bn=Object.freeze(["contact","support","help"]),En=Object.freeze(["checkout","cart"]),we=new Set([i.CHECKOUT_HANDOFF,i.HANDOFF_TO_ADVISOR,i.HANDOFF_TO_AGENT,i.HANDOFF_TO_CLINIC,i.HANDOFF_TO_HUMAN,i.HANDOFF_TO_LAWYER,i.HANDOFF_TO_LICENSED_AGENT,i.HANDOFF_TO_RECRUITER]),Se=Object.freeze({[i.CHECKOUT_HANDOFF]:{title:"Checkout needs your confirmation",body:"This step may include payment or a secure checkout page. I can take you there, then you complete the final step yourself.",primary:"Open checkout"},[i.HANDOFF_TO_ADVISOR]:{title:"Advisor handoff",body:"This request needs a qualified advisor. I can open the contact path so the site team can continue.",primary:"Contact advisor"},[i.HANDOFF_TO_AGENT]:{title:"Agent handoff",body:"This step needs an agent or account-specific help. I can open the contact path for follow-up.",primary:"Contact agent"},[i.HANDOFF_TO_CLINIC]:{title:"Clinic handoff",body:"This request needs clinic confirmation. I can open the appointment or contact path for the next step.",primary:"Contact clinic"},[i.HANDOFF_TO_HUMAN]:{title:"Human handoff",body:"This step needs human confirmation. I can open the most relevant contact path.",primary:"Open contact"},[i.HANDOFF_TO_LAWYER]:{title:"Legal handoff",body:"This request needs a legal professional. I can open the consultation or contact path.",primary:"Contact lawyer"},[i.HANDOFF_TO_LICENSED_AGENT]:{title:"Licensed agent handoff",body:"This request needs a licensed agent. I can open the quote or contact path for follow-up.",primary:"Contact agent"},[i.HANDOFF_TO_RECRUITER]:{title:"Recruiter handoff",body:"This request needs recruiter review. I can open the application or contact path.",primary:"Contact recruiter"}});function v(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}function P(t){return String(t||"").trim()}function An(){if(document.getElementById(Ie))return;let t=document.createElement("style");t.id=Ie,t.textContent=`
    #${Y} {
      position: fixed;
      left: 50%;
      bottom: 96px;
      z-index: 2147483639;
      width: min(calc(100vw - 32px), 460px);
      transform: translate(-50%, calc(100% + 32px));
      opacity: 0;
      pointer-events: none;
      border: 1px solid rgba(22, 22, 21, 0.12);
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.98);
      box-shadow: 0 24px 70px rgba(22, 22, 21, 0.18);
      color: #161615;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      transition: transform 0.26s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.2s ease;
    }
    #${Y}.active {
      transform: translate(-50%, 0);
      opacity: 1;
      pointer-events: auto;
    }
    .shopbot-handoff-body {
      display: grid;
      gap: 12px;
      padding: 16px;
    }
    .shopbot-handoff-top {
      display: flex;
      align-items: start;
      justify-content: space-between;
      gap: 14px;
    }
    .shopbot-handoff-title {
      margin: 0;
      color: #161615;
      font-size: 16px;
      font-weight: 800;
      line-height: 1.25;
      letter-spacing: 0;
    }
    .shopbot-handoff-close {
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
    .shopbot-handoff-text {
      margin: 0;
      color: #534d44;
      font-size: 14px;
      line-height: 1.45;
    }
    .shopbot-handoff-reason {
      margin: 0;
      border-left: 3px solid #d9b66f;
      padding: 8px 10px;
      background: #fbf6ea;
      color: #534d44;
      font-size: 12px;
      line-height: 1.35;
      overflow-wrap: anywhere;
    }
    .shopbot-handoff-meta {
      display: grid;
      gap: 4px;
      margin: 0;
      color: #6f665b;
      font-size: 12px;
      line-height: 1.35;
      overflow-wrap: anywhere;
    }
    .shopbot-handoff-meta strong {
      color: #161615;
      font-weight: 760;
    }
    .shopbot-handoff-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: flex-end;
    }
    .shopbot-handoff-actions button {
      min-height: 38px;
      border: 1px solid rgba(22, 22, 21, 0.12);
      border-radius: 8px;
      background: #161615;
      color: #ffffff;
      cursor: pointer;
      font-size: 13px;
      font-weight: 760;
      line-height: 1;
      padding: 0 14px;
    }
    .shopbot-handoff-actions button.secondary {
      background: #ffffff;
      color: #161615;
    }
    @media (max-width: 430px) {
      #${Y} {
        bottom: 82px;
        width: min(calc(100vw - 20px), 420px);
      }
    }
  `,document.head.appendChild(t)}function gn(){An();let t=document.getElementById(Y);return t||(t=document.createElement("div"),t.id=Y,t.setAttribute("aria-live","polite"),document.body.appendChild(t),t)}function yn(){return window.AIHubAdapterRuntime?.config?.adapter?.routes||window.AIHubAdapter?.config?.adapter?.routes||{}}function In(t,e){let o=Oe(e[u.URL]||e.path||e.href||e.handoff_flow?.page_url);if(o)return o;let n=yn(),r=t===i.CHECKOUT_HANDOFF?En:bn;for(let s of r){let a=Oe(n[s]);if(a)return a}return""}function Oe(t){let e=P(t);if(!e)return"";try{let o=new URL(e,window.location.origin);return o.origin!==window.location.origin?"":`${o.pathname}${o.search}${o.hash}`||"/"}catch{return""}}function Sn(t){return Se[t]||Se[i.HANDOFF_TO_HUMAN]}function On(t){return t&&typeof t=="object"?t:{}}function xn(t,e){return P(t.title)||e}function wn(t,e,o){return P(e[u.MESSAGE])||P(t.handling)||o}function Rn(t,e){return P(e[u.REASON]||e.reason||e.blocked_reason||t.key)}function Cn(t){let e=[["Provider",t.provider_label||t.provider],["Boundary",t.automation_boundary],["Recovery",t.recovery],["Evidence",t.evidence],["Page",t.page_url]].filter(([,o])=>P(o));return e.length?`
    <p class="shopbot-handoff-meta">
      ${e.map(([o,n])=>`<span><strong>${v(o)}:</strong> ${v(n)}</span>`).join("")}
    </p>
  `:""}function xe(t){t.classList.remove("active")}function Nn(){window.setTimeout(()=>{let t=document.getElementById("shopbot-chat"),e=document.getElementById("shopbot-msgs");e&&(e.innerHTML=""),t&&t.classList.remove("visible")},U)}function Re(t,e={}){let o=P(t).toUpperCase(),n=Sn(o),r=On(e.handoff_flow),s=gn(),a=In(o,e),p=xn(r,n.title),T=wn(r,e,n.body),b=Rn(r,e);return s.innerHTML=`
    <div class="shopbot-handoff-body">
      <div class="shopbot-handoff-top">
        <h2 class="shopbot-handoff-title">${v(p)}</h2>
        <button class="shopbot-handoff-close" type="button" aria-label="Close handoff">&times;</button>
      </div>
      <p class="shopbot-handoff-text">${v(T)}</p>
      ${Cn(r)}
      ${b?`<p class="shopbot-handoff-reason">${v(b)}</p>`:""}
      <div class="shopbot-handoff-actions">
        <button type="button" class="secondary" data-close-handoff>Close</button>
        ${a?`<button type="button" data-open-handoff>${v(n.primary)}</button>`:""}
      </div>
    </div>
  `,s.querySelector(".shopbot-handoff-close")?.addEventListener("click",()=>xe(s)),s.querySelector("[data-close-handoff]")?.addEventListener("click",()=>xe(s)),s.querySelector("[data-open-handoff]")?.addEventListener("click",()=>{window.location.href=a}),s.classList.add("active"),Nn(),!0}function Ce(t){return we.has(t.action)}function Ne(t){return Re(t.action,t.parameters||{})}function Pe(t){return t.action===i.NAVIGATE_TO&&!!De(t.parameters?.[u.PAGE])}function Le(t){return window.location.href=De(t.parameters?.[u.PAGE]),!0}function De(t){let e=String(t||"").trim();if(!e||/^https?:\/\//i.test(e))return"";if(e==="home"||e==="/")return"/";let o=e.replace(/^\/+|\/+$/g,"");return o?`/${o}/`:"/"}function Ue(t){let e=t?.params||t?.parameters||{};return{...t||{},action:String(t?.action||"").trim().toUpperCase(),params:e,parameters:e}}var Pn=Object.freeze([{path:"/api/products.json",routePrefix:""},{path:"/products.json",routePrefix:"/products/"},{path:"/collections/all/products.json",routePrefix:"/products/"}]),Ln=Object.freeze(["products","data","items","results"]),He=Object.freeze(["id","product_id","handle","sku"]),Me=Object.freeze(["name","title"]),Dn=Object.freeze(["url","href","permalink","product_url"]),Un=Object.freeze(["image_url","image","thumbnail","featured_image"]),vn=Object.freeze(["brand","vendor"]),Hn=Object.freeze(["category","category_name","product_type"]),Mn=Object.freeze(["description","summary","body_html"]),Fn="Unknown Brand",kn="Products",Bn="/",Yn=/^[a-z0-9][a-z0-9-]*$/i,ft=null;function A(t){return t==null||typeof t=="object"?"":String(t||"").trim()}function zn(t){return A(t).toLowerCase().replace(/[^a-z0-9]+/g," ").trim()}function ht(t,e){return e.map(o=>A(t?.[o])).filter(Boolean)}function L(t,e){return ht(t,e)[0]||""}function Gn(t){let e=L(t,Un);if(e)return e;let o=t?.image||t?.featured_image;return o&&typeof o=="object"?A(o.src||o.url):Array.isArray(t?.images)?A(t.images[0]?.src||t.images[0]?.url||t.images[0]):""}function $n(t){let e=A(t);if(!e)return"";try{let o=new URL(e,window.location.origin);return o.origin!==window.location.origin?"":`${o.pathname}${o.search}${o.hash}`}catch{return""}}function Vn(t,e,o){let n=$n(L(t,Dn));return n||(!Yn.test(e)||!/[a-z]/i.test(e)||!o?.routePrefix?"":`${o.routePrefix}${encodeURIComponent(e)}${Bn}`)}function Fe(t,e={}){if(!t)return null;let o=L(t,He),n=A(t.handle||t.slug||t.product_handle),r=L(t,Me),s=Number(t.price||t.amount||t.cost||0);return!o&&!n?null:{id:o,handle:n,name:r,title:A(t.title||r),brand:L(t,vn)||Fn,category:L(t,Hn)||kn,description:L(t,Mn),price:Number.isFinite(s)?s:0,imageUrl:Gn(t),url:Vn(t,n||o,e)}}function Wn(t){return ht(t,He)}function ve(t){return ht(t,Me).map(zn)}function jn(t,e){let o=A(e);return!!(o&&Wn(t).includes(o))}function qn(t,e){let o=new Set(ve(e));return ve(t).some(n=>o.has(n))}function Kn(t,e){return!!(t?.imageUrl&&t.imageUrl===e?.imageUrl)}function Qn(t){if(Array.isArray(t))return t;for(let e of Ln){let o=t?.[e];if(Array.isArray(o))return o}return[]}async function Xn(t){try{let e=await fetch(new URL(t.path,window.location.origin),{headers:{Accept:"application/json"}});if(!e.ok)return[];let o=await e.json();return Qn(o).map(n=>Fe(n,t)).filter(Boolean)}catch(e){return console.warn(`[AI Hub Widget] Catalog endpoint lookup failed for ${t.path}:`,e),[]}}async function Jn(){return ft||(ft=Promise.all(Pn.map(Xn)).then(t=>t.flat())),ft}async function mt(t){let e=(Array.isArray(t)?t:[]).map(A).filter(Boolean);if(!e.length)return[];let o=new URL(I.PRODUCTS_BY_IDS,l.apiUrl);o.searchParams.set("site_id",l.siteId),o.searchParams.set("ids",e.join(","));let n=await fetch(o.toString(),{headers:{Accept:"application/json"}});if(!n.ok)throw new Error("Failed to fetch products from AI Hub API");let r=(await n.json()).map(a=>Fe(a)).filter(Boolean),s=new Map(r.map(a=>[String(a.id),a]));return e.map(a=>s.get(a)).filter(Boolean)}async function Z(t){let e=A(t);if(!e)return"";let[o]=await mt([e]);if(o?.url)return o.url;let n=await Jn(),r=n.find(a=>jn(a,e));return r?.url?r.url:o&&n.find(a=>qn(a,o)||Kn(a,o))?.url||""}var _t="AIHubAdapterRuntime",Tt="AIHubAdapter";function Zn(t){let e=t?.params||t?.parameters||{};return{...t||{},params:e,parameters:e}}function z(){return!!(window[_t]?.executeAction||window[Tt]?.handleAction)}async function bt(t){return(await Et(t)).succeeded}async function Et(t){let e=Zn(t);if(window[_t]?.executeAction){let o=window[_t],n=await o.executeAction(e)===!0,r=o.lastActionResult||{};return{succeeded:n,handled:r.handled===!0||n,status:r.status||(n?"ok":"not_handled"),reason:r.reason||"",blocked:r.status==="blocked",disabled:r.status==="disabled"}}if(window[Tt]?.handleAction){let o=await window[Tt].handleAction(e)===!0;return{succeeded:o,handled:o,status:o?"ok":"not_handled",reason:"",blocked:!1,disabled:!1}}return{succeeded:!1,handled:!1,status:"missing_adapter",reason:"",blocked:!1,disabled:!1}}var tr=["data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='320' height='240' viewBox='0 0 320 240'%3E","%3Crect width='320' height='240' fill='%23f1f2ee'/%3E","%3Cpath d='M98 156h124l-31-40-25 30-17-22-51 32Z' fill='%23c8c3ba'/%3E","%3Ccircle cx='117' cy='95' r='17' fill='%23d8d3ca'/%3E","%3Ctext x='160' y='198' text-anchor='middle' fill='%23686660' font-family='Arial,sans-serif' font-size='16'%3EImage pending%3C/text%3E","%3C/svg%3E"].join(""),At=[],gt=y;function G(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}function er(){if(document.getElementById("shopbot-product-overlay-styles"))return;let t=document.createElement("style");t.id="shopbot-product-overlay-styles",t.textContent=`
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
  `,document.head.appendChild(t)}function or(){er();let t=document.getElementById("shopbot-product-panel");return t||(t=document.createElement("div"),t.id="shopbot-product-panel",t.setAttribute("aria-live","polite"),t.innerHTML=`
    <div class="shopbot-product-header">
      <h2 class="shopbot-product-title">${y}</h2>
      <button class="shopbot-product-close" type="button" aria-label="Close recommendations">&times;</button>
    </div>
    <div class="shopbot-product-grid"></div>
  `,t.querySelector(".shopbot-product-close").addEventListener("click",()=>{t.classList.remove("active")}),document.body.appendChild(t),t)}async function nr(t){return mt(t)}async function rr(t){let e={action:i.ADD_TO_CART,params:{[u.PRODUCT_ID]:t,[u.QUANTITY]:nt},parameters:{[u.PRODUCT_ID]:t,[u.QUANTITY]:nt}};z()&&await bt(e)||window.dispatchEvent(new CustomEvent(k.SHOPBOT_ACTION,{detail:e}))}async function ir(t){try{let o=await Z(t);if(o){window.location.href=o;return}}catch(o){console.warn("[AI Hub Widget] Product detail URL lookup failed:",o)}let e={action:i.SHOW_PRODUCT_DETAIL,params:{[u.PRODUCT_ID]:t},parameters:{[u.PRODUCT_ID]:t}};z()&&await bt(e)||window.dispatchEvent(new CustomEvent(k.SHOPBOT_ACTION,{detail:e}))}function ar(t){return t<=1?"count-1":t===2?"count-2":t===3?"count-3":"count-many"}function sr(t){return t<=1?1:t===2?2:3}function yt(t,e){let o=or(),n=o.querySelector(".shopbot-product-grid"),r=o.querySelector(".shopbot-product-title"),s=t.length;if(At=Array.isArray(t)?[...t]:[],gt=e||y,o.classList.remove("count-1","count-2","count-3","count-many"),o.classList.add(ar(s)),o.style.setProperty("--shopbot-card-count",String(sr(s))),r.textContent=gt,!s){n.innerHTML='<p class="shopbot-product-empty">No matching products are currently available.</p>',o.classList.add("active"),ke();return}n.innerHTML=t.map(a=>{let p=G(a.id);return`
        <article class="shopbot-product-card" data-product-id="${p}">
          <img class="shopbot-product-image" src="${G(a.imageUrl||tr)}" alt="${G(a.name)}">
          <h3 class="shopbot-product-name">${G(a.name)}</h3>
          <p class="shopbot-product-meta">${G(a.brand)} - $${Number(a.price||0).toFixed(2)} USD</p>
          <div class="shopbot-product-actions">
            <button type="button" data-add="${p}">Add</button>
            <button type="button" class="secondary" data-view="${p}">View</button>
          </div>
        </article>
      `}).join(""),n.querySelectorAll("[data-add]").forEach(a=>{a.addEventListener("click",async()=>{await rr(a.getAttribute("data-add"))})}),n.querySelectorAll("[data-view]").forEach(a=>{a.addEventListener("click",async()=>{await ir(a.getAttribute("data-view"))})}),o.classList.add("active"),ke()}function ke(){window.setTimeout(()=>{let t=document.getElementById("shopbot-chat"),e=document.getElementById("shopbot-msgs");e&&(e.innerHTML=""),t&&t.classList.remove("visible")},U)}async function Ye(t,e=y){try{let o=await nr(t);return yt(o,e),!0}catch(o){return console.warn("[AI Hub Widget] Product overlay failed:",o),yt([],e),!0}}function ze(t={}){if(!At.length)return!1;let e=String(t.sort_by||t.sortBy||"price_asc").trim().toLowerCase(),o=[...At].sort((n,r)=>cr(n,r,e));return yt(o,ur(gt,e)),!0}function cr(t,e,o){return o==="price_desc"?H(e.price,Number.NEGATIVE_INFINITY)-H(t.price,Number.NEGATIVE_INFINITY):o==="rating"?H(e.rating||e.review_rating,Number.NEGATIVE_INFINITY)-H(t.rating||t.review_rating,Number.NEGATIVE_INFINITY):o==="newest"?Be(e)-Be(t):H(t.price,Number.POSITIVE_INFINITY)-H(e.price,Number.POSITIVE_INFINITY)}function H(t,e){let o=String(t??"").replace(/,/g,"").match(/-?\d+(?:\.\d+)?/);if(!o)return e;let n=Number(o[0]);return Number.isFinite(n)?n:e}function Be(t){let e=t?.updated_at||t?.created_at||t?.date||"",o=Date.parse(String(e||""));return Number.isFinite(o)?o:0}function ur(t,e){let o={price_asc:"sorted low to high",price_desc:"sorted high to low",rating:"sorted by rating",newest:"newest first"};return`${String(t||y).replace(/\s+-\s+sorted.*$/i,"")} - ${o[e]||o.price_asc}`}function Ge(t){return t.action===i.SHOW_PRODUCTS||t.action===i.SHOW_COMPARISON||t.action===i.SHOW_PRODUCT_DETAIL||t.action===i.SORT_PRODUCTS}async function $e(t){return t.action===i.SHOW_PRODUCTS||t.action===i.SHOW_COMPARISON?pr(t.parameters||{},t.action===i.SHOW_COMPARISON?"Product comparison":y):t.action===i.SHOW_PRODUCT_DETAIL?lr(t.parameters||{}):t.action===i.SORT_PRODUCTS?ze(t.parameters||{}):!1}async function pr(t,e=y){return await Ye(t[u.PRODUCT_IDS]||[],t[u.SEARCH_QUERY]||t.title||e),!0}async function lr(t){let e="";try{e=await Z(t[u.PRODUCT_ID])}catch(o){return console.warn("[AI Hub Widget] Product detail URL lookup failed:",o),!1}return e?(window.location.href=e,!0):!1}var It="stop_action_fallback",dr=new Set([i.SHOW_PRODUCTS,i.SHOW_COMPARISON,i.SHOW_PRODUCT_DETAIL,i.SORT_PRODUCTS]);function Ve(t){return z()&&!dr.has(t.action)}async function We(t){let e=await Et(t);return e.succeeded?!0:e.blocked||e.disabled?It:!1}function je(t){return window.dispatchEvent(new CustomEvent(k.SHOPBOT_ACTION,{detail:t})),!0}var fr=Object.freeze([{canExecute:Ve,execute:We},{canExecute:Ge,execute:$e},{canExecute:ge,execute:ye},{canExecute:Ce,execute:Ne},{canExecute:()=>!0,execute:Kt},{canExecute:se,execute:ce},{canExecute:Pe,execute:Le},{canExecute:()=>!0,execute:je}]);async function St(t){for(let e of t||[])await hr(Ue(e))}async function hr(t){if(t.action)for(let e of fr){if(!e.canExecute(t))continue;let o=await e.execute(t);if(o===!0||o===It)return}}var mr=3,_r="AIHubAdapterRuntime",Tr="AIHubAdapter";function br(t,e){let o=new URL(I.SHOP_WS,t);return o.protocol=o.protocol==="https:"?"wss:":"ws:",o.searchParams.set("site_id",e),o.searchParams.set("session_id",l.sessionId),o.toString()}function Er(t){return new Promise((e,o)=>{let n=new FileReader;n.onloadend=()=>{let r=String(n.result||"");e(r.includes(",")?r.split(",").pop():r)},n.onerror=()=>o(n.error||new Error("Failed to read audio blob")),n.readAsDataURL(t)})}var Ot=class{constructor(){this.queue=[],this.playing=!1}push(e){e&&(this.queue.push(e),this.playNext())}playNext(){if(this.playing||this.queue.length===0)return;this.playing=!0;let e=new Audio(D.DATA_WAV_PREFIX+this.queue.shift());e.onended=()=>{this.playing=!1,this.playNext()},e.onerror=()=>{this.playing=!1,this.playNext()},e.play().catch(o=>{console.error("Audio playback failed",o),this.playing=!1,this.playNext()})}},xt=class{async sendAudio(e,o,n=[]){let r=new FormData;r.append("audio",e,D.WEBM_FILENAME),r.append("site_id",l.siteId),r.append("session_id",l.sessionId),n&&n.length>0&&r.append("conversation_history",JSON.stringify(n));let s=Ke();s&&r.append("page_context",JSON.stringify(s));let a=await fetch(`${l.apiUrl}${I.SHOP}`,{method:Bt.POST,body:r});if(!a.ok)throw new Error("AI Hub API request failed");let p=await a.json();p.transcript&&o.onUserMessage?.(p.transcript),p.response_text&&o.onAssistantMessage?.(p.response_text,p.ui_actions||[]),o.onStatusChange?.(h.READY),p.audio_b64&&yr(p.audio_b64),p.ui_actions&&p.ui_actions.length>0&&await St(p.ui_actions),o.onComplete?.(p)}},wt=class{constructor(){this.ws=null,this.connected=!1,this.connecting=null,this.failed=!1,this.retries=0,this.audioQueue=new Ot,this.callbacks=null,this.turnText=""}async ensureConnected(e=[]){return this.canUseWebSocket()?this.isOpen()?!0:this.connecting?this.connecting:(this.connecting=this.openConnection(e),this.connecting):!1}canUseWebSocket(){return!this.failed&&l.useWebSocket&&"WebSocket"in window}isOpen(){return this.connected&&this.ws?.readyState===WebSocket.OPEN}openConnection(e=[]){return new Promise(o=>{let n=new WebSocket(br(l.apiUrl,l.siteId)),r=!1;this.ws=n;let s=(p=null)=>{r||(r=!0,this.markConnectionFailed(o,p,n))},a=window.setTimeout(()=>{s()},Vt);n.onopen=()=>{r||(r=!0,this.handleConnectionOpen(a,e,o))},n.onmessage=p=>{this.handleMessage(p).catch(T=>this.handleTransportError(T))},n.onerror=()=>s(a),n.onclose=()=>{this.connected=!1,s(a)}})}markConnectionOpen(){this.connected=!0,this.connecting=null,this.retries=0}handleConnectionOpen(e,o,n){window.clearTimeout(e),this.markConnectionOpen(),this.sendConfig(o),n(!0)}markConnectionFailed(e,o=null,n=null){o&&window.clearTimeout(o),this.connected=!1,this.connecting=null,this.retries+=1,this.retries>=mr&&(this.failed=!0),n&&n.readyState!==WebSocket.CLOSED&&n.close(),e(!1)}sendConfig(e=[]){this.sendJson({type:S.CONFIG,history:e||[],session_id:l.sessionId,page_context:Ke()})}sendJson(e){return!this.ws||this.ws.readyState!==WebSocket.OPEN?!1:(this.ws.send(JSON.stringify(e)),!0)}async sendAudio(e,o,n=[]){if(!await this.ensureConnected(n))return!1;this.callbacks=o,this.turnText="",this.sendConfig(n);let s=await Er(e);return this.sendJson({type:S.AUDIO_CHUNK,data:s}),this.sendJson({type:S.AUDIO_END}),!0}async handleMessage(e){let o=this.callbacks;if(!o)return;let n=this.parseMessage(e.data);if(!n){this.completeWithError(o,"Invalid WebSocket message");return}if(!this.handleIncrementalMessage(n,o)){if(n.type===S.DONE){await this.handleDoneMessage(n,o);return}n.type===S.ERROR&&this.completeWithError(o,n.message||"WebSocket error")}}parseMessage(e){try{let o=JSON.parse(e);return o&&typeof o=="object"?o:null}catch{return null}}handleIncrementalMessage(e,o){return e.type===S.TRANSCRIPT?(o.onUserMessage?.(e.text||""),!0):e.type===S.TEXT_CHUNK?(this.turnText+=e.text||"",o.onAssistantChunk?.(e.text||"",this.turnText),!0):e.type===S.AUDIO_CHUNK?(this.audioQueue.push(e.audio_b64),!0):!1}async handleDoneMessage(e,o){let n=e.response_text||this.turnText;o.onAssistantMessage?.(n,e.ui_actions||[],{streamed:!0}),o.onStatusChange?.(h.READY);try{e.ui_actions&&e.ui_actions.length>0&&await St(e.ui_actions),o.onComplete?.(e)}catch(r){this.handleTransportError(r)}finally{this.callbacks=null}}completeWithError(e,o){e.onStatusChange?.(h.ERROR),e.onComplete?.({error:o}),this.callbacks=null}handleTransportError(e){console.error("AI Hub WebSocket transport failed",e);let o=this.callbacks;o&&this.completeWithError(o,String(e))}},Ar=new xt,gr=new wt;async function qe(t,e,o,n=[]){try{if(l.useWebSocket&&await gr.sendAudio(t,o,n))return;await Ar.sendAudio(t,o,n)}catch(r){console.error(r),o.onStatusChange?.(h.ERROR),o.onComplete?.({error:String(r)})}}function yr(t){let e=D.DATA_WAV_PREFIX+t;new Audio(e).play().catch(n=>console.error("Audio playback failed",n))}function Ke(){let t=window[_r],e=window[Tr];try{if(typeof t?.getContext=="function")return t.getContext();if(typeof e?.getContext=="function")return e.getContext()}catch(o){console.warn("[AI Hub Widget] Page context collection failed:",o)}return null}window.__shopbot_identifier="voice-orb";var Rt=null,Qe=null,V="",$="",Ir=1,Sr=1.08,Or=300,xr=Object.freeze(["hannah","zira","aria","jenny","samantha","victoria","tessa","moira","karen","female","woman","nova","shimmer","google us english","microsoft aria"]);function Xe(){if(window.__shopbotBooted||document.getElementById("shopbot-widget"))return;window.__shopbotBooted=!0,Nt();let t=Ft(),e=null;function o(d=Yt){e&&window.clearTimeout(e),e=window.setTimeout(()=>{t.msgs.innerHTML="",t.chat.classList.remove("visible"),e=null},d)}function n(d){t.status.className="",d===h.RECORDING?(e&&(window.clearTimeout(e),e=null),t.msgs.innerHTML="",t.btn.classList.add("recording"),t.chat.classList.add("visible"),t.status.innerText="Listening...",t.status.classList.add("listening")):d===h.PROCESSING?(t.btn.classList.remove("recording"),t.chat.classList.add("visible"),t.status.innerText="Analyzing...",t.status.classList.add("processing")):d===h.READY?(t.status.innerText="Ready",t.status.classList.add("ready")):d===h.ERROR&&(t.status.innerText="Error",t.status.classList.add("error"),t.btn.classList.remove("recording"))}let r=[],s=null,a="";function p(d,_){let f=[];for(let x of _||[]){let w=x.params||{};if(w[u.PRODUCT_IDS]&&Array.isArray(w[u.PRODUCT_IDS]))for(let Ct of w[u.PRODUCT_IDS])f.includes(Ct)||f.push(Ct);w[u.PRODUCT_ID]&&!f.includes(w[u.PRODUCT_ID])&&f.push(w[u.PRODUCT_ID])}return f.length>0?d+` [PRODUCT_IDS: ${f.join(",")}]`:d}async function T(d){s=null,a="",await qe(d,t,{onUserMessage:_=>{F(t,_,"user"),r.push({role:"user",content:_}),r.length>ot&&r.shift()},onAssistantChunk:(_,f)=>{a=f,s||(s=F(t,"","ai")),et(t,s,a)},onAssistantMessage:(_,f,x={})=>{x.streamed&&s?et(t,s,_):F(t,_,"ai");let w=p(_,f);r.push({role:"assistant",content:w}),r.length>ot&&r.shift(),s=null,a=""},onStatusChange:n,onComplete:()=>o()},r)}let b=Wt(T,n);Rt=b,t.btn.addEventListener("click",()=>{b.toggle()}),Pr()&&(Lr(),window.setTimeout(()=>{if(r.length>0)return;let d=`Welcome to ${l.brandName}. How can I help you today?`;F(t,d,"ai"),n(h.READY),o(Gt),to(d)},zt))}function to(t){if(!("speechSynthesis"in window)||!("SpeechSynthesisUtterance"in window))return;V=t;let e=()=>{try{let o=new SpeechSynthesisUtterance(t),n=wr(window.speechSynthesis.getVoices());n&&(o.voice=n),o.rate=Ir,o.pitch=Sr,o.onstart=()=>{V=""},o.onend=()=>{V=""},window.speechSynthesis.cancel(),window.speechSynthesis.resume(),window.speechSynthesis.speak(o)}catch{}};if(window.speechSynthesis.getVoices().length>0){e();return}window.speechSynthesis.onvoiceschanged=e,window.setTimeout(e,Or)}function wr(t){if(!Array.isArray(t)||t.length===0)return null;if($){let n=t.find(r=>r.name===$);if(n)return n}let e=l.speechVoiceName.toLowerCase();if(e){let n=t.find(r=>r.name.toLowerCase()===e);if(n)return $=n.name,n}let o=null;return l.speechVoicePreference.toLowerCase()!=="female"?o=t.find(n=>n.default)||t[0]:o=t.find(n=>xr.some(r=>n.name.toLowerCase().includes(r)))||t.find(n=>n.default)||t[0],o&&($=o.name),o}function Rr(){V&&to(V)}function Cr(){Rt?.cancel(),Rt=null,$="",window.__shopbotBooted=!1,document.getElementById("shopbot-widget")?.remove(),document.getElementById("shopbot-product-panel")?.remove();try{window.speechSynthesis?.cancel()}catch{}}async function Nr(){let t=new URL(I.WIDGET_STATUS,l.apiUrl);t.searchParams.set("site_id",l.siteId);let e=await fetch(t.toString(),{cache:"no-store",headers:{Accept:"application/json"}});return e.ok?(await e.json()).enabled!==!1:!0}async function Je(){try{if(await Nr()){Xe();return}Cr()}catch{Xe()}}function Ze(){Qe||(Je(),Qe=window.setInterval(Je,$t))}function Pr(){if(!l.autoGreet||!Dr())return!1;try{return window.sessionStorage.getItem(eo())!=="1"}catch{return!window.__shopbotAutoGreeted}}function Lr(){window.__shopbotAutoGreeted=!0;try{window.sessionStorage.setItem(eo(),"1")}catch{}}function eo(){return`shopbot:auto-greeted:${l.siteId}`}function Dr(){let t=window.location.pathname.replace(/\/+$/,"")||"/";return t==="/"||t.endsWith("/index.html")}document.readyState==="loading"?document.addEventListener("DOMContentLoaded",Ze):Ze();document.addEventListener("pointerdown",Rr,{capture:!0});})();
