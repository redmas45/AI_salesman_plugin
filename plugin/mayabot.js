(()=>{function le(){let t="#5d5fef",e=document.querySelector('meta[name="theme-color"]');if(e&&e.content)t=e.content;else{let h=document.querySelector('button[class*="primary"], .btn-primary, [data-primary]');if(h){let M=window.getComputedStyle(h).backgroundColor;M&&M!=="rgba(0, 0, 0, 0)"&&M!=="transparent"&&(t=M)}}let n=window.matchMedia&&window.matchMedia("(prefers-color-scheme: dark)").matches,r=n?"rgba(24, 24, 27, 0.75)":"rgba(255, 255, 255, 0.85)",o=n?"rgba(255, 255, 255, 0.1)":"rgba(0, 0, 0, 0.08)",a=n?"#f3f4f6":"#111827",i=n?"rgba(255, 255, 255, 0.1)":"rgba(0, 0, 0, 0.05)",c=n?"rgba(0, 0, 0, 0.25)":"#ffffff",p=document.createElement("style");p.textContent=`
    :root {
      --mayabot-primary: ${t};
      --mayabot-surface: ${r};
      --mayabot-border: ${o};
      --mayabot-text: ${a};
      --mayabot-user-bg: ${i};
      --mayabot-bot-bg: ${c};
    }

    #mayabot-widget {
      position: fixed;
      bottom: max(24px, env(safe-area-inset-bottom));
      left: auto;
      right: 24px;
      transform: none;
      z-index: 2147483647;
      font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      color: var(--mayabot-text);
      letter-spacing: 0;
      width: auto;
      max-width: calc(100vw - 32px);
      -webkit-font-smoothing: antialiased;
      contain: layout style;
      isolation: isolate;
    }

    #mayabot-btn {
      position: relative;
      /* Keep touch activation immediate and prevent browser zoom/highlight from
         competing with the orb's single-click voice control. */
      touch-action: manipulation;
      -webkit-tap-highlight-color: transparent;
      user-select: none;
      -webkit-user-select: none;
      width: 64px;
      height: 64px;
      border-radius: 50%;
      border: 1px solid rgba(255, 255, 255, 0.15);
      background: var(--mayabot-primary);
      box-shadow: 0 12px 32px -8px var(--mayabot-primary), 0 4px 12px rgba(0,0,0,0.15);
      color: #ffffff;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: transform 0.3s cubic-bezier(0.25, 1, 0.5, 1), box-shadow 0.3s ease, background-color 0.2s ease;
      outline: none;
    }
    
    #mayabot-btn svg {
      position: relative;
      z-index: 2;
      width: 28px;
      height: 28px;
      transition: transform 0.3s ease;
    }

    .mayabot-btn-ring {
      position: absolute;
      inset: -6px;
      border-radius: inherit;
      border: 2px solid var(--mayabot-primary);
      opacity: 0.4;
      pointer-events: none;
      transition: inset 0.3s ease, opacity 0.3s ease;
    }

    #mayabot-btn:hover {
      transform: translateY(-4px) scale(1.02);
      box-shadow: 0 16px 40px -8px var(--mayabot-primary), 0 8px 24px rgba(0,0,0,0.2);
    }
    
    #mayabot-btn:hover .mayabot-btn-ring {
      inset: -10px;
      opacity: 0.15;
    }

    #mayabot-btn.recording {
      background: #ef4444;
      box-shadow: 0 0 0 6px rgba(239, 68, 68, 0.2), 0 8px 24px rgba(0,0,0,0.18);
    }

    #mayabot-chat {
      position: absolute;
      bottom: 96px;
      left: auto;
      right: 0;
      transform: translateY(20px) scale(0.95);
      width: min(400px, calc(100vw - 32px));
      max-height: min(600px, calc(100vh - 140px));
      background: var(--mayabot-surface);
      backdrop-filter: blur(24px) saturate(180%);
      -webkit-backdrop-filter: blur(24px) saturate(180%);
      border: 1px solid var(--mayabot-border);
      border-radius: 20px;
      box-shadow: 0 24px 48px -12px rgba(0, 0, 0, 0.18), 0 0 0 1px rgba(255, 255, 255, 0.05) inset;
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 16px;
      opacity: 0;
      pointer-events: none;
      visibility: hidden;
      transition: opacity 0.25s ease, transform 0.3s cubic-bezier(0.16, 1, 0.3, 1), visibility 0s linear 0.3s;
    }

    #mayabot-chat.visible {
      opacity: 1;
      pointer-events: all;
      visibility: visible;
      transform: translateY(0) scale(1);
      transition-delay: 0s;
    }

    .mayabot-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--mayabot-border);
    }

    .mayabot-header strong {
      display: block;
      font-size: 16px;
      font-weight: 600;
      line-height: 1.3;
    }

    .mayabot-kicker {
      display: block;
      margin-bottom: 4px;
      color: var(--mayabot-primary);
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .mayabot-live-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #10b981;
      box-shadow: 0 0 0 4px rgba(16, 185, 129, 0.15);
      flex: 0 0 auto;
    }

    #mayabot-msgs {
      padding-right: 4px;
      scrollbar-width: thin;
      scrollbar-color: var(--mayabot-border) transparent;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    
    #mayabot-msgs::-webkit-scrollbar {
      width: 4px;
    }
    #mayabot-msgs::-webkit-scrollbar-thumb {
      background-color: var(--mayabot-border);
      border-radius: 4px;
    }

    .mayabot-msg {
      max-width: 85%;
      padding: 12px 16px;
      border-radius: 16px;
      font-size: 14.5px;
      line-height: 1.5;
      overflow-wrap: anywhere;
      animation: mayabotSlideUpFade 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards;
      opacity: 0;
      transform: translateY(10px);
    }

    .mayabot-msg.user {
      background: var(--mayabot-user-bg);
      align-self: flex-end;
      border-bottom-right-radius: 4px;
    }

    .mayabot-msg.ai {
      background: var(--mayabot-bot-bg);
      align-self: flex-start;
      border-bottom-left-radius: 4px;
      border: 1px solid var(--mayabot-border);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
    }

    #mayabot-status {
      font-size: 12px;
      color: var(--mayabot-text);
      opacity: 0.6;
      text-align: center;
      min-height: 18px;
      margin-top: 4px;
      font-weight: 500;
      transition: color 0.3s ease, opacity 0.3s ease;
    }

    #mayabot-status.listening {
      color: var(--mayabot-primary);
      opacity: 1;
      animation: mayabotTextPulse 1.5s infinite ease-in-out;
    }

    #mayabot-status.processing {
      color: var(--mayabot-text);
      opacity: 0.8;
      animation: mayabotTextPulse 1.5s infinite ease-in-out;
    }

    @keyframes mayabotSlideUpFade {
      from { opacity: 0; transform: translateY(8px) scale(0.98); }
      to { opacity: 1; transform: translateY(0) scale(1); }
    }

    @keyframes mayabotTextPulse {
      0%, 100% { opacity: 0.5; }
      50% { opacity: 1; }
    }

    @media (max-width: 520px) {
      #mayabot-widget {
        right: 16px;
        bottom: max(88px, calc(env(safe-area-inset-bottom) + 72px));
      }
      #mayabot-btn {
        width: 56px;
        height: 56px;
      }
      #mayabot-chat {
        bottom: 84px;
        width: calc(100vw - 32px);
      }
    }

    @media (prefers-reduced-motion: reduce) {
      #mayabot-btn,
      #mayabot-btn svg,
      .mayabot-btn-ring,
      #mayabot-chat,
      .mayabot-msg,
      #mayabot-status {
        animation: none !important;
        transition: none !important;
      }
    }
  `,document.head.appendChild(p)}var St="site_1",lr="__AI_";var dr="aihub:auto-site-id:",pr=["data-aihub-scope","data-site-scope"],fr=["data-site-id","data-aihub-site-id"];function y(t){return String(t||"").trim()}function q(t){return y(t).replace(/\/+$/,"")}function fe(t,e,n,r=St){return mr(t,e,n)||_r()||y(r)||St}function mr(t,e,n){for(let a of fr){let i=y(t?.getAttribute(a));if(i)return i}let r=y(e?.searchParams.get("site"))||y(e?.searchParams.get("site_id"))||y(e?.searchParams.get("shop"));if(r)return r;let o=y(n);return o&&!o.startsWith(lr)?o:""}function _r(){let t=hr(),e=`${dr}${t}`,n=Ir(e);if(n){let c=Ar(n);return c!==n&&pe(e,c),c}let r=y(window.location.host||window.location.hostname||"site"),o=me(),a=Er(`${r}${o?`_${o.replace(/\//g,"_")}`:""}`),i=_e(`auto_${a}_${Sr(t)}`);return pe(e,i),i}function hr(){return`${window.location.origin}${me()}`}function me(){return yr()}function yr(){for(let e of pr){let n=y(gr()?.getAttribute(e));if(n)return de(n)}let t=document.querySelector("meta[name='aihub-site-scope']")?.getAttribute("content");return de(t)}function gr(){return document.currentScript}function de(t){let e=y(t);if(!e||e==="/")return"";try{let r=new URL(e,window.location.href);if(r.origin===window.location.origin){let[o]=br(r.pathname);return o?`/${o}`:""}}catch{}let[n]=e.replace(/^\/+/,"").split("/");return n?`/${n}`:""}function br(t=window.location.pathname){return y(t).split("/").map(e=>Tr(e).trim()).filter(Boolean)}function Tr(t){try{return decodeURIComponent(t)}catch{return String(t||"")}}function Er(t){return y(t).toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/^_+|_+$/g,"")||"site"}function _e(t){return y(t).slice(0,80).replace(/_+$/g,"")||St}function Ar(t){let e=y(t);return e.startsWith("auto_")?_e(e.toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/^_+|_+$/g,"")):e}function Sr(t){let e=2166136261,n=y(t);for(let r=0;r<n.length;r+=1)e^=n.charCodeAt(r),e=Math.imul(e,16777619);return(e>>>0).toString(36)}function Ir(t){try{return y(window.localStorage.getItem(t))}catch{return""}}function pe(t,e){try{window.localStorage.setItem(t,e)}catch{}}var N=document.currentScript,he="__AI_PUBLIC_API_URL__",Or="__AI_DEFAULT_SITE_ID__",wr="mayabot:session:",xr="Maya",Rr="AI Salesperson",Cr="female";function k(t){return String(t||"").trim()}function Nr(){let t=k(N?.getAttribute("src"));if(!t)return null;try{return new URL(t,window.location.href)}catch{return null}}function vr(t){let e=k(N?.getAttribute("data-api-url"));if(e)return q(e);if(!he.startsWith("__AI_"))return q(he);if(t?.origin){let n=t.pathname.replace(/\/mayabot(?:-widget)?\.js$/,"");return q(`${t.origin}${n}`)}return q(window.location.origin)}function Lr(t){let e=`${wr}${t}`;try{let n=window.sessionStorage.getItem(e);if(n)return n;let r=ye(t);return window.sessionStorage.setItem(e,r),r}catch{return ye(t)}}function ye(t){let e=window.crypto?.randomUUID?.()||`${Date.now()}-${Math.random().toString(16).slice(2)}`;return`${t}-${e}`.slice(0,120)}var be=Nr(),ge=fe(N,be,Or),l={siteId:ge,get sessionId(){return Lr(ge)},apiUrl:vr(be),useWebSocket:k(N?.getAttribute("data-use-websocket")).toLowerCase()==="true",autoGreet:k(N?.getAttribute("data-auto-greet")).toLowerCase()!=="false",brandName:k(N?.getAttribute("data-brand"))||xr,assistantTitle:k(N?.getAttribute("data-assistant-title"))||Rr,speechVoiceName:k(N?.getAttribute("data-speech-voice")),speechVoicePreference:k(N?.getAttribute("data-speech-voice-preference"))||Cr};function Te(){let t=document.createElement("div");return t.id="mayabot-widget",t.innerHTML=`
    <div id="mayabot-chat">
      <div class="mayabot-header">
        <div>
          <span class="mayabot-kicker"></span>
          <strong class="mayabot-title"></strong>
        </div>
        <span class="mayabot-live-dot" aria-hidden="true"></span>
      </div>
      <div id="mayabot-msgs" style="max-height: 300px; overflow-y: auto; display: flex; flex-direction: column; gap: 8px;"></div>
      <div id="mayabot-status">Ready</div>
    </div>
    <button id="mayabot-btn" aria-label="Talk to Maya">
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
        <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
        <line x1="12" x2="12" y1="19" y2="22"/>
      </svg>
      <span class="mayabot-btn-ring" aria-hidden="true"></span>
    </button>
  `,document.body.appendChild(t),t.querySelector(".mayabot-kicker").textContent=l.brandName,t.querySelector(".mayabot-title").textContent=l.assistantTitle,{btn:document.getElementById("mayabot-btn"),chat:document.getElementById("mayabot-chat"),msgs:document.getElementById("mayabot-msgs"),status:document.getElementById("mayabot-status")}}function K(t,e,n){t.chat.classList.add("visible");let r=document.createElement("div");return r.className=`mayabot-msg ${n}`,r.innerText=e,t.msgs.appendChild(r),t.msgs.scrollTop=t.msgs.scrollHeight,r}function It(t,e,n){e&&(e.innerText=n,t.msgs.scrollTop=t.msgs.scrollHeight)}var s=Object.freeze({ADD_TO_CART:"ADD_TO_CART",BOOK_APPOINTMENT_REQUEST:"BOOK_APPOINTMENT_REQUEST",BUILD_ITINERARY:"BUILD_ITINERARY",BUILD_LEARNING_PATH:"BUILD_LEARNING_PATH",CAPTURE_LEAD:"CAPTURE_LEAD",CAPTURE_PATIENT_LEAD:"CAPTURE_PATIENT_LEAD",CHECKOUT:"CHECKOUT",CHECKOUT_HANDOFF:"CHECKOUT_HANDOFF",CHECK_APPOINTMENT_AVAILABILITY:"CHECK_APPOINTMENT_AVAILABILITY",CHECK_AVAILABILITY:"CHECK_AVAILABILITY",CHECK_DELIVERY_AVAILABILITY:"CHECK_DELIVERY_AVAILABILITY",CHECK_ELIGIBILITY_SOFT:"CHECK_ELIGIBILITY_SOFT",CHECK_PREREQUISITES:"CHECK_PREREQUISITES",CLEAR_CART:"CLEAR_CART",CLEAR_FILTERS:"CLEAR_FILTERS",CLEAR_HISTORY:"CLEAR_HISTORY",COMPARE_ENTITIES:"COMPARE_ENTITIES",CONTACT_AGENT:"CONTACT_AGENT",FILTER_ENTITIES:"FILTER_ENTITIES",FILTER_PRODUCTS:"FILTER_PRODUCTS",HANDOFF_TO_ADVISOR:"HANDOFF_TO_ADVISOR",HANDOFF_TO_AGENT:"HANDOFF_TO_AGENT",HANDOFF_TO_CLINIC:"HANDOFF_TO_CLINIC",HANDOFF_TO_HUMAN:"HANDOFF_TO_HUMAN",HANDOFF_TO_LAWYER:"HANDOFF_TO_LAWYER",HANDOFF_TO_LICENSED_AGENT:"HANDOFF_TO_LICENSED_AGENT",HANDOFF_TO_RECRUITER:"HANDOFF_TO_RECRUITER",JOIN_WAITLIST:"JOIN_WAITLIST",MATCH_JOBS:"MATCH_JOBS",NAVIGATE_TO:"NAVIGATE_TO",OPEN_CLAIM_FLOW:"OPEN_CLAIM_FLOW",OPEN_CONTACT:"OPEN_CONTACT",OPEN_DISCLOSURE:"OPEN_DISCLOSURE",OPEN_ENTITY_DETAIL:"OPEN_ENTITY_DETAIL",OPEN_LOCATION:"OPEN_LOCATION",OPEN_MAP:"OPEN_MAP",OPEN_POLICY:"OPEN_POLICY",OPEN_PROJECTS:"OPEN_PROJECTS",OPEN_RENEWAL_FLOW:"OPEN_RENEWAL_FLOW",OPEN_SERVICES:"OPEN_SERVICES",OPEN_SYLLABUS:"OPEN_SYLLABUS",OPEN_TELECONSULT:"OPEN_TELECONSULT",REMOVE_FROM_CART:"REMOVE_FROM_CART",REQUEST_APPOINTMENT:"REQUEST_APPOINTMENT",REQUEST_CALLBACK:"REQUEST_CALLBACK",REQUEST_CONSULTATION:"REQUEST_CONSULTATION",REQUEST_COUNSELOR_CALLBACK:"REQUEST_COUNSELOR_CALLBACK",REQUEST_ESTIMATE:"REQUEST_ESTIMATE",REQUEST_SITE_VISIT:"REQUEST_SITE_VISIT",REQUEST_TEST_DRIVE:"REQUEST_TEST_DRIVE",REQUEST_VIEWING:"REQUEST_VIEWING",RUN_AFFORDABILITY_CALCULATOR:"RUN_AFFORDABILITY_CALCULATOR",RUN_CALCULATOR:"RUN_CALCULATOR",RUN_DOM_SEQUENCE:"RUN_DOM_SEQUENCE",SAVE_SEARCH:"SAVE_SEARCH",SCHEDULE_ORDER:"SCHEDULE_ORDER",SEARCH_AVAILABILITY:"SEARCH_AVAILABILITY",SET_LOCATION:"SET_LOCATION",SHOW_COMPARISON:"SHOW_COMPARISON",SHOW_EMERGENCY_NOTICE:"SHOW_EMERGENCY_NOTICE",SHOW_ENTITIES:"SHOW_ENTITIES",SHOW_PRODUCT_DETAIL:"SHOW_PRODUCT_DETAIL",SHOW_PRODUCTS:"SHOW_PRODUCTS",SORT_ENTITIES:"SORT_ENTITIES",SORT_PRODUCTS:"SORT_PRODUCTS",START_APPLICATION:"START_APPLICATION",START_BOOKING:"START_BOOKING",START_ENROLLMENT:"START_ENROLLMENT",START_INTAKE:"START_INTAKE",START_QUOTE:"START_QUOTE",START_TICKET_PURCHASE:"START_TICKET_PURCHASE",UPDATE_CART_QUANTITY:"UPDATE_CART_QUANTITY",UPDATE_PREFERENCES:"UPDATE_PREFERENCES"}),d=Object.freeze({ENTITY_ID:"entity_id",ENTITY_IDS:"entity_ids",MESSAGE:"message",PAGE:"page",PRODUCT_ID:"product_id",PRODUCT_IDS:"product_ids",QUANTITY:"quantity",REASON:"reason",SEARCH_QUERY:"search_query",URL:"url"}),Ui=Object.freeze({BLOCKED:"blocked",EXECUTING:"executing",FAILED:"failed",REQUESTED:"requested",SKIPPED:"skipped",SUCCEEDED:"succeeded",UNKNOWN:"unknown"}),O=Object.freeze({KNOWLEDGE_BY_IDS:"/v1/knowledge/by-ids",PRODUCTS_BY_IDS:"/v1/products/by-ids",SHOP:"/v1/shop",SHOP_WS:"/v1/ws/shop",WIDGET_STATUS:"/v1/widget/status"}),w=Object.freeze({AUDIO_CHUNK:"audio_chunk",AUDIO_END:"audio_end",CONFIG:"config",DONE:"done",ERROR:"error",TEXT_CHUNK:"text_chunk",TRANSCRIPT:"transcript"});var Ee=new Set(["cart","/cart"]),v="Recommended products",F="Relevant options",Q=Object.freeze({DATA_WAV_PREFIX:"data:audio/wav;base64,",WEBM_FILENAME:"audio.webm",WEBM_MIME_TYPE:"audio/webm"}),Ae=Object.freeze({POST:"POST"}),_=Object.freeze({ERROR:"error",PROCESSING:"processing",READY:"ready",RECORDING:"recording"}),Se=12,Ie=2400,Oe=900,we=4200,Ot=1,V=180,xe=3e3,X=Object.freeze({MAYABOT_ACTION:"mayabot:action"}),Re=2500,Ce=45e3;var Pr=["audio/webm;codecs=opus","audio/webm","audio/ogg;codecs=opus","audio/ogg","audio/mp4"],Dr=250,Ur=128;function Ne(t,e){let n=null,r=null,o=[],a=!1,i=!1,c=!1;async function p(){if(!(i||a)){i=!0;try{let g=await navigator.mediaDevices.getUserMedia({audio:!0});r=g,c=!1;let B=Mr();n=new MediaRecorder(g,B?{mimeType:B}:void 0),o=[],n.ondataavailable=E=>{E.data.size>0&&o.push(E.data)},n.onstop=async()=>{let E=new Blob(o,{type:n.mimeType||B||Q.WEBM_MIME_TYPE});if(C(),c){c=!1;return}if(E.size<Ur){console.warn("Microphone recording was empty or too short",{size:E.size}),e(_.READY);return}await t(E)},n.onerror=E=>{console.error("Microphone recording failed",E.error||E),a=!1,i=!1,C(),e(_.ERROR,"Recording failed")},n.start(Dr),a=!0,e(_.RECORDING)}catch(g){console.error("Microphone access denied",g),e(_.ERROR,"Mic unavailable")}finally{i=!1}}}function h({discard:g=!1}={}){if(c=g,n&&n.state!=="inactive"){try{n.requestData()}catch{}n.stop(),a=!1,g||e(_.PROCESSING);return}a=!1,C(),g||e(_.PROCESSING)}function M(){i||(a?h():p())}function $(){h({discard:!0})}function C(){r&&(r.getTracks().forEach(g=>g.stop()),r=null)}return{toggle:M,cancel:$}}function Mr(){return!("MediaRecorder"in window)||typeof MediaRecorder.isTypeSupported!="function"?"":Pr.find(t=>MediaRecorder.isTypeSupported(t))||""}var ve="shopify",Le="woocommerce",kr="custom";function at(t){let e=String(t||"").trim();return/^\d+$/.test(e)?e:""}function it(t,e=1){let n=Number(t?.[d.QUANTITY]);return Number.isFinite(n)&&n>0?Math.floor(n):e}async function Y(t,e){return(await fetch(new URL(t,window.location.origin),{method:"POST",headers:{Accept:"application/json","Content-Type":"application/json"},body:JSON.stringify(e),credentials:"same-origin"})).ok}function Fr(){return Hr()?ve:Br()?Le:kr}async function Pe(t){let e=Fr();return e===ve?Yr(t):e===Le?jr(t):!1}function Hr(){return!!(window.Shopify||document.querySelector('meta[name="shopify-checkout-api-token"]')||document.querySelector('script[src*="cdn.shopify.com"]'))}function Br(){return!!(document.body?.classList?.contains("woocommerce")||window.wc_add_to_cart_params||document.querySelector('link[href*="woocommerce"], script[src*="woocommerce"]'))}async function Yr(t){let e=t.parameters||{};if(t.action===s.ADD_TO_CART){let n=at(e.variant_id||e.cart_id||e[d.PRODUCT_ID]);return n?Y("/cart/add.js",{items:[{id:n,quantity:it(e)}]}):!1}if(t.action===s.REMOVE_FROM_CART){let n=at(e.cart_id||e.variant_id||e[d.PRODUCT_ID]);return n?Y("/cart/change.js",{id:n,quantity:0}):!1}if(t.action===s.UPDATE_CART_QUANTITY){let n=at(e.cart_id||e.variant_id||e[d.PRODUCT_ID]);return n?Y("/cart/change.js",{id:n,quantity:it(e,0)}):!1}return t.action===s.CLEAR_CART?Y("/cart/clear.js",{}):t.action===s.CHECKOUT?st("/checkout"):De(t)?st("/cart"):!1}async function jr(t){let e=t.parameters||{};if(t.action===s.ADD_TO_CART){let n=at(e.variant_id||e.cart_id||e[d.PRODUCT_ID]);return n?Y("/wp-json/wc/store/cart/add-item",{id:Number(n),quantity:it(e)}):!1}if(t.action===s.REMOVE_FROM_CART){let n=String(e.cart_key||e.key||"").trim();return n?Y("/wp-json/wc/store/cart/remove-item",{key:n}):!1}if(t.action===s.UPDATE_CART_QUANTITY){let n=String(e.cart_key||e.key||"").trim();return n?Y("/wp-json/wc/store/cart/update-item",{key:n,quantity:it(e,0)}):!1}return t.action===s.CHECKOUT?st("/checkout"):De(t)?st("/cart"):!1}function De(t){return t.action===s.NAVIGATE_TO&&Ee.has(t.parameters?.[d.PAGE])}function st(t){return window.location.href=t,!0}var $r="/v1/widget/action-event";function A(t){return String(t||"").trim()}function Vr(t,e){return new URL(t,e).toString()}function zr(t){return!t||typeof t!="object"?[]:Object.keys(t).map(e=>A(e)).filter(Boolean).slice(0,20)}function Wr(t){if(!t||typeof t!="object")return{};let e={};for(let[n,r]of Object.entries(t).slice(0,20)){let o=A(n).slice(0,80);o&&(typeof r=="boolean"||r===null?e[o]=r:typeof r=="number"?e[o]=Number.isFinite(r)?r:0:e[o]=A(r).slice(0,240))}return e}async function ct(t,e,n,r){if(!t||!e||!n?.action)return;let o=JSON.stringify({site_id:e,origin:window.location.origin,url:window.location.href,occurred_at:new Date().toISOString(),request_id:A(n.request_id||n.action_request_id),turn_id:A(n.turn_id),sequence:Number(n.sequence||0),action:A(n.action).toUpperCase(),status:A(r?.status)||"unknown",stage:A(r?.stage),reason:A(r?.reason),duration_ms:Number(r?.duration_ms||0),param_keys:zr(n.parameters||n.params),requested_url:A(r?.requested_url),final_url:A(r?.final_url||window.location.href),evidence:Wr(r?.evidence)}),a=Vr($r,t);if(!Gr(a,o))try{await fetch(a,{method:"POST",headers:{Accept:"application/json","Content-Type":"application/json"},body:o,keepalive:!0})}catch(i){console.warn("[AIHubAdapter] Action execution report failed.",i)}}function Gr(t,e){if(typeof navigator>"u"||typeof navigator.sendBeacon!="function"||typeof Blob!="function")return!1;try{return navigator.sendBeacon(t,new Blob([e],{type:"application/json"}))}catch{return!1}}function Ue(t){if(!t||typeof t!="string")return[];let e=[];for(let n of qr()){try{e.push(...Array.from(n.querySelectorAll(t)))}catch{return[]}if(e.length>=600)return e.slice(0,600)}return Jr(e)}function qr(){let t=[],e=new Set,n=[document];for(;n.length&&t.length<60;){let r=n.shift();!r||e.has(r)||(e.add(r),t.push(r),n.push(...Kr(r)))}return t}function Kr(t){let e=[];for(let n of Qr(t)){n.shadowRoot&&e.push(n.shadowRoot);let r=Xr(n);r&&e.push(r)}return e}function Qr(t){try{return Array.from(t.querySelectorAll("*"))}catch{return[]}}function Xr(t){if(String(t?.tagName||"").toLowerCase()!=="iframe")return null;try{let e=t.contentDocument;return e?.documentElement?e:null}catch{return null}}function Jr(t){return Array.from(new Set(t))}var zi=Object.freeze([u("stripe",["stripe","stripe.com","checkout.stripe.com","js.stripe.com"]),u("paypal",["paypal","paypal.com","paypalobjects.com"]),u("razorpay",["razorpay","checkout.razorpay.com"]),u("paytm",["paytm","securegw.paytm.in"]),u("cashfree",["cashfree","cashfree.com"]),u("checkout.com",["checkout.com","cko-session-id"]),u("adyen",["adyen","checkoutshopper"]),u("square",["squareup","squarecdn","square.site"]),u("braintree",["braintree","braintreegateway"]),u("mollie",["mollie","mollie.com"]),u("klarna",["klarna","klarna.com"]),u("afterpay",["afterpay","afterpay.com","clearpay"]),u("payu",["payu","payu.in","payu.com"]),u("paystack",["paystack","paystack.co"]),u("phonepe",["phonepe","phonepe.com"]),u("billdesk",["billdesk","billdesk.com"]),u("authorize.net",["authorize.net","accept.authorize.net"])]),Me=Object.freeze([u("calendly",["calendly","calendly.com"]),u("acuity",["acuityscheduling","squarespace scheduling"]),u("booksy",["booksy","booksy.com"]),u("zocdoc",["zocdoc","zocdoc.com"]),u("appointlet",["appointlet","appointlet.com"]),u("setmore",["setmore","setmore.com"]),u("cal.com",["cal.com","calcom"]),u("google_calendar",["calendar.google.com","google calendar"]),u("microsoft_bookings",["microsoft bookings","outlook.office365.com/book"]),u("simplybook",["simplybook","simplybook.me"]),u("tidycal",["tidycal","tidycal.com"]),u("savvycal",["savvycal","savvycal.com"]),u("fresha",["fresha","fresha.com"])]),ke=Object.freeze([u("google_maps",["google.com/maps","maps.googleapis","maps.google"]),u("mapbox",["mapbox","mapbox.com"]),u("openstreetmap",["openstreetmap","osm.org"]),u("leaflet",["leaflet","leafletjs"]),u("here_maps",["here.com","hereapi","wego.here.com"]),u("bing_maps",["bing.com/maps","virtualearth"]),u("mappls",["mappls","mapmyindia"])]),Fe=Object.freeze([u("whatsapp",["wa.me","api.whatsapp.com","web.whatsapp.com"]),u("telegram",["t.me/","telegram.me"]),u("messenger",["m.me/","messenger.com/t"]),u("zendesk",["zendesk.com","zdassets.com/hc"]),u("intercom",["intercom.help","intercom.com"]),u("freshchat",["freshchat.com"])]),Wi=Object.freeze([u("recaptcha",["recaptcha","g-recaptcha","google.com/recaptcha"]),u("hcaptcha",["hcaptcha","h-captcha"]),u("turnstile",["turnstile","challenges.cloudflare.com"]),u("cloudflare_challenge",["cf-chl","cloudflare challenge"])]);function u(t,e){return{name:t,tokens:e}}function wt(t,e,n=10){let r=xt(t);return e.filter(o=>o.tokens.some(a=>r.includes(a))).map(o=>o.name).slice(0,n)}function xt(t){return String(t||"").replace(/\s+/g," ").trim().toLowerCase()}var He="a[href], iframe[src]",Zr="a[href]",Ye=new Set(["http:","https:"]),ut=new Set(["mailto:","tel:"]),to=Object.freeze([d.URL,"href","link","target_url","provider_url","booking_url","appointment_url","calendar_url","map_url","location_url","contact_url"]),je=new Set([s.OPEN_MAP,s.OPEN_LOCATION,s.SET_LOCATION]),$e=new Set([s.CHECK_APPOINTMENT_AVAILABILITY,s.REQUEST_APPOINTMENT,s.BOOK_APPOINTMENT_REQUEST,s.REQUEST_CONSULTATION,s.REQUEST_SITE_VISIT,s.START_BOOKING]),Ve=new Set([s.OPEN_CONTACT,s.CONTACT_AGENT,s.REQUEST_CALLBACK,s.REQUEST_COUNSELOR_CALLBACK,s.HANDOFF_TO_ADVISOR,s.HANDOFF_TO_AGENT,s.HANDOFF_TO_CLINIC,s.HANDOFF_TO_HUMAN,s.HANDOFF_TO_LAWYER,s.HANDOFF_TO_LICENSED_AGENT,s.HANDOFF_TO_RECRUITER]);function ze(t){let e=qe(t);return je.has(e)||$e.has(e)||Ve.has(e)}async function We(t){let e=qe(t);return je.has(e)?Rt(t,ke,He,Ct):$e.has(e)?Rt(t,Me,He,Ct):Ve.has(e)?Rt(t,Fe,Zr,oo):!1}function Rt(t,e,n,r){let o=eo(t?.parameters||t?.params||{},e,r);if(o)return Be(o);let a=no(n,e,r);return a?Be(a):!1}function eo(t,e,n){for(let r of to){let o=Ge(t?.[r]);if(o&&n(o,e))return o}return null}function no(t,e,n){for(let r of Ue(t)){let o=ro(r);if(!(!o||!n(o,e))&&ao(o,r,e))return o}return null}function ro(t){return Ge(t?.getAttribute?.("href")||t?.getAttribute?.("src"))}function Ct(t,e){return Ye.has(t.protocol)&&wt(t.href,e).length>0}function oo(t,e){return ut.has(t.protocol)?!0:Ct(t,e)}function ao(t,e,n){if(ut.has(t.protocol))return!0;let r=[t.href,e?.textContent||"",e?.getAttribute?.("aria-label")||"",e?.getAttribute?.("title")||""].join(" ");return wt(xt(r),n).length>0}function Be(t){if(ut.has(t.protocol)||t.origin===window.location.origin)return window.location.href=t.href,!0;let e=window.open(t.href,"_blank","noopener,noreferrer");return e?(e.opener=null,!0):(window.location.href=t.href,!0)}function Ge(t){let e=String(t||"").trim();if(!e||e.startsWith("#"))return null;try{let n=new URL(e,window.location.href);return Ye.has(n.protocol)||ut.has(n.protocol)?n:null}catch{return null}}function qe(t){return String(t?.action||"").trim().toUpperCase()}var io=Object.freeze(["title","name"]),so=Object.freeze(["summary","description","body"]),co=Object.freeze(["image_url","imageUrl","image","thumbnail"]),uo=Object.freeze(["url","href","permalink","source_url"]),lo="knowledge_item",po=30;function x(t){return t==null||typeof t=="object"?"":String(t||"").trim()}function fo(t){let e=new Set;return(Array.isArray(t)?t:[]).map(x).filter(Boolean).filter(n=>e.has(n)||e.size>=po?!1:(e.add(n),!0))}function lt(t,e){for(let n of e){let r=x(t?.[n]);if(r)return r}return""}function J(t){return t&&typeof t=="object"&&!Array.isArray(t)?t:{}}function mo(t){let e=_o([t?.price,t?.amount,t?.premium,t?.premium_min,t?.monthly_premium,t?.annual_premium,t?.min_price,t?.starting_price]),n=x(t?.currency||"INR");return!Number.isFinite(e)||e<=0?"":`${n} ${e.toLocaleString()}`}function _o(t){for(let e of t){let n=Number(String(e??"").replace(/,/g,""));if(Number.isFinite(n)&&n>0)return n}return 0}function ho(t){return!t||typeof t!="object"?"":t.in_stock===!0?"Available":t.in_stock===!1?"Unavailable":x(t.status||t.availability||"")}function yo(t){let e=x(t);if(!e)return"";try{let n=new URL(e,window.location.origin);return/^https?:$/i.test(n.protocol)?n.origin===window.location.origin?`${n.pathname}${n.search}${n.hash}`:n.toString():""}catch{return""}}function go(t){if(!t)return null;let e=x(t.id);if(!e)return null;let n=J(t.pricing),r=J(t.availability);return{id:e,externalId:x(t.external_id),entityType:x(t.entity_type||t.category_name)||lo,title:lt(t,io)||e,subtitle:x(t.subtitle||t.category_name||t.entity_type),summary:lt(t,so),body:x(t.body),url:yo(lt(t,uo)),imageUrl:lt(t,co),attributes:J(t.attributes),pricing:n,availability:r,location:J(t.location),contact:J(t.contact),displayPrice:mo(n),displayAvailability:ho(r)}}async function Nt(t){let e=fo(t);if(!e.length)return[];let n=new URL(O.KNOWLEDGE_BY_IDS,l.apiUrl);n.searchParams.set("site_id",l.siteId),n.searchParams.set("ids",e.join(","));let r=await fetch(n.toString(),{headers:{Accept:"application/json"}});if(!r.ok)throw new Error("Failed to fetch entities from AI Hub API");let o=(await r.json()).map(go).filter(Boolean),a=new Map(o.map(i=>[String(i.id),i]));return e.map(i=>a.get(i)).filter(Boolean)}async function Ke(t){let[e]=await Nt([t]);return e?.url||""}function Qe(){if(document.getElementById("mayabot-entity-overlay-styles"))return;let t=document.createElement("style");t.id="mayabot-entity-overlay-styles",t.textContent=`
    #mayabot-entity-panel {
      position: fixed;
      left: 50%;
      bottom: 96px;
      z-index: 2147483638;
      width: min(calc(100vw - 32px), var(--mayabot-entity-panel-width, 760px));
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
    #mayabot-entity-panel.active {
      transform: translate(-50%, 0);
      opacity: 1;
      pointer-events: auto;
    }
    #mayabot-entity-panel.count-1 { --mayabot-entity-panel-width: 420px; }
    #mayabot-entity-panel.count-2 { --mayabot-entity-panel-width: 660px; }
    #mayabot-entity-panel.count-3,
    #mayabot-entity-panel.count-many { --mayabot-entity-panel-width: 980px; }
    .mayabot-entity-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
      padding: 14px 16px;
      border-bottom: 1px solid rgba(22, 22, 21, 0.1);
    }
    .mayabot-entity-title {
      margin: 0;
      color: #161615;
      font-size: 15px;
      font-weight: 800;
      line-height: 1.25;
      letter-spacing: 0;
    }
    .mayabot-entity-close {
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
    .mayabot-entity-grid {
      display: grid;
      grid-template-columns: repeat(var(--mayabot-entity-card-count, 2), minmax(0, 1fr));
      gap: 12px;
      padding: 14px;
      overflow: auto;
      scrollbar-width: thin;
    }
    .mayabot-entity-card {
      display: grid;
      grid-template-rows: auto auto auto 1fr auto;
      gap: 10px;
      min-width: 0;
      border: 1px solid rgba(22, 22, 21, 0.1);
      border-radius: 8px;
      background: #ffffff;
      padding: 12px;
    }
    .mayabot-entity-media {
      display: grid;
      place-items: center;
      min-height: 116px;
      border-radius: 8px;
      background: #f1f2ee;
      overflow: hidden;
    }
    .mayabot-entity-media img {
      width: 100%;
      height: 150px;
      object-fit: contain;
      padding: 8px;
    }
    .mayabot-entity-badge {
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
    .mayabot-entity-name {
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
    .mayabot-entity-meta {
      margin: 0;
      color: #686660;
      font-size: 12px;
      line-height: 1.35;
      overflow-wrap: anywhere;
      text-transform: capitalize;
    }
    .mayabot-entity-summary {
      margin: 0;
      color: #3d3933;
      font-size: 13px;
      line-height: 1.42;
      display: -webkit-box;
      -webkit-line-clamp: 4;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    .mayabot-entity-facts {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }
    .mayabot-entity-fact {
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
    .mayabot-entity-actions {
      display: flex;
      justify-content: flex-end;
      align-self: end;
    }
    .mayabot-entity-actions button {
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
    .mayabot-entity-empty {
      margin: 0;
      padding: 14px;
      color: #686660;
      font-size: 14px;
    }
    @media (max-width: 720px) {
      #mayabot-entity-panel {
        bottom: 86px;
        width: min(calc(100vw - 20px), 520px);
      }
      #mayabot-entity-panel.count-2,
      #mayabot-entity-panel.count-3,
      #mayabot-entity-panel.count-many {
        --mayabot-entity-card-count: 2;
      }
      .mayabot-entity-grid {
        padding: 12px;
      }
      .mayabot-entity-media img {
        height: 132px;
      }
    }
    @media (max-width: 430px) {
      #mayabot-entity-panel {
        bottom: 82px;
      }
      #mayabot-entity-panel.count-1,
      #mayabot-entity-panel.count-2,
      #mayabot-entity-panel.count-3,
      #mayabot-entity-panel.count-many {
        --mayabot-entity-card-count: 1;
      }
    }
  `,document.head.appendChild(t)}var bo=2,Xe=Number.POSITIVE_INFINITY,dt=Number.NEGATIVE_INFINITY,Je=12,Lt=[],Pt=F;function L(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}function nn(t){return String(t||"item").replace(/[_-]+/g," ").trim().split(/\s+/).slice(0,bo).join(" ")}function To(){Qe();let t=document.getElementById("mayabot-entity-panel");return t||(t=document.createElement("div"),t.id="mayabot-entity-panel",t.setAttribute("aria-live","polite"),t.innerHTML=`
    <div class="mayabot-entity-header">
      <h2 class="mayabot-entity-title">${F}</h2>
      <button class="mayabot-entity-close" type="button" aria-label="Close recommendations">&times;</button>
    </div>
    <div class="mayabot-entity-grid"></div>
  `,t.querySelector(".mayabot-entity-close").addEventListener("click",()=>{t.classList.remove("active")}),document.body.appendChild(t),t)}function Eo(t){return t<=1?"count-1":t===2?"count-2":t===3?"count-3":"count-many"}function Ao(t){return t<=1?1:t===2?2:3}function vt(t,e,n=""){let r=(Array.isArray(e)?e:[]).map(c=>String(c?.id??"").trim()).filter(Boolean),o=r.length,a=t.length,i=o>0?"succeeded":"failed";return{status:i,stage:"entity_overlay",reason:n||(i==="succeeded"?"":"no_matching_entities_rendered"),evidence:{requested_entity_count:a,rendered_entity_count:o,missing_entity_count:Math.max(a-o,0),requested_entity_ids:t.slice(0,Je).join(","),rendered_entity_ids:r.slice(0,Je).join(",")}}}function So(t){return[t.displayPrice,t.displayAvailability,t.location?.city,t.attributes?.category].map(e=>String(e||"").trim()).filter(Boolean).slice(0,3)}function Io(t){return t.imageUrl?`
      <div class="mayabot-entity-media">
        <img src="${L(t.imageUrl)}" alt="${L(t.title)}">
      </div>
    `:`
    <div class="mayabot-entity-media">
      <div class="mayabot-entity-badge">${L(nn(t.entityType))}</div>
    </div>
  `}function Oo(t){let e=So(t);return e.length?`
    <div class="mayabot-entity-facts">
      ${e.map(n=>`<span class="mayabot-entity-fact">${L(n)}</span>`).join("")}
    </div>
  `:""}function wo(t){return t.url?`
    <div class="mayabot-entity-actions">
      <button type="button" data-view-entity="${L(t.id)}">Open</button>
    </div>
  `:""}function ft(t,e){let n=To(),r=n.querySelector(".mayabot-entity-grid"),o=n.querySelector(".mayabot-entity-title"),a=t.length;if(Lt=Array.isArray(t)?[...t]:[],Pt=e||F,n.classList.remove("count-1","count-2","count-3","count-many"),n.classList.add(Eo(a)),n.style.setProperty("--mayabot-entity-card-count",String(Ao(a))),o.textContent=Pt,!a){r.innerHTML='<p class="mayabot-entity-empty">No matching records are currently available.</p>',n.classList.add("active"),Ze();return}r.innerHTML=t.map(i=>`
        <article class="mayabot-entity-card" data-entity-id="${L(i.id)}">
          ${Io(i)}
          <h3 class="mayabot-entity-name">${L(i.title)}</h3>
          <p class="mayabot-entity-meta">${L(i.subtitle||nn(i.entityType))}</p>
          <p class="mayabot-entity-summary">${L(i.summary||i.body||"Details are available on the website.")}</p>
          ${Oo(i)}
          ${wo(i)}
        </article>
      `).join(""),r.querySelectorAll("[data-view-entity]").forEach(i=>{i.addEventListener("click",async()=>{await Dt(i.getAttribute("data-view-entity"))})}),n.classList.add("active"),Ze()}function xo(t){if(!t)return!1;try{let e=new URL(t,window.location.origin);return e.origin===window.location.origin?(window.location.href=`${e.pathname}${e.search}${e.hash}`,!0):(window.open(e.toString(),"_blank","noopener,noreferrer"),!0)}catch{return!1}}function Ze(){window.setTimeout(()=>{let t=document.getElementById("mayabot-chat"),e=document.getElementById("mayabot-msgs");e&&(e.innerHTML=""),t&&t.classList.remove("visible")},V)}async function Dt(t){let e=await Ke(t);return xo(e)}async function rn(t,e=F){let n=Ut({[d.ENTITY_IDS]:t});if(!n.length)return ft([],e),vt([],[],"missing_entity_ids");try{let r=await Nt(n);return ft(r,e),vt(n,r)}catch(r){return console.warn("[AI Hub Widget] Entity overlay failed:",r),ft([],e),vt(n,[],"entity_overlay_fetch_failed")}}function Ut(t){let e=t[d.ENTITY_IDS]||t.ids||t.items||[],n=new Set;return(Array.isArray(e)?e:[]).map(r=>String(r??"").trim()).filter(Boolean).filter(r=>n.has(r)?!1:(n.add(r),!0))}function on(t={}){if(!Lt.length)return!1;let e=String(t.sort_by||t.sortBy||"price_asc").trim().toLowerCase(),n=[...Lt].sort((o,a)=>Ro(o,a,e)),r=No(Pt,e);return ft(n,r),!0}function Ro(t,e,n){return n==="price_desc"?pt(e,dt)-pt(t,dt):n==="rating"?tn(e,dt)-tn(t,dt):n==="newest"?en(e)-en(t):pt(t,Xe)-pt(e,Xe)}function pt(t,e){return an([t?.pricing?.price,t?.pricing?.amount,t?.pricing?.premium,t?.pricing?.premium_min,t?.pricing?.monthly_premium,t?.pricing?.annual_premium,t?.pricing?.min_price,t?.pricing?.starting_price,t?.attributes?.price,t?.attributes?.amount,t?.attributes?.premium,t?.attributes?.monthly_premium,t?.attributes?.annual_premium,t?.displayPrice],e)}function tn(t,e){return an([t?.attributes?.rating,t?.attributes?.review_rating,t?.attributes?.stars,t?.availability?.rating],e)}function en(t){let e=t?.attributes?.updated_at||t?.attributes?.date||t?.availability?.updated_at||"",n=Date.parse(String(e||""));return Number.isFinite(n)?n:0}function an(t,e){for(let n of t){let r=Co(n);if(Number.isFinite(r))return r}return e}function Co(t){if(typeof t=="number")return t;let e=String(t??"").replace(/,/g,"").match(/-?\d+(?:\.\d+)?/);return e?Number(e[0]):Number.NaN}function No(t,e){let n={price_asc:"sorted low to high",price_desc:"sorted high to low",rating:"sorted by rating",newest:"newest first"};return`${String(t||F).replace(/\s+-\s+sorted.*$/i,"")} - ${n[e]||n.price_asc}`}function sn(t){return t.action===s.SHOW_ENTITIES||t.action===s.COMPARE_ENTITIES||t.action===s.OPEN_ENTITY_DETAIL||t.action===s.SORT_ENTITIES}async function cn(t){return t.action===s.SHOW_ENTITIES||t.action===s.COMPARE_ENTITIES?vo(t.parameters||{}):t.action===s.OPEN_ENTITY_DETAIL?Dt(t.parameters?.[d.ENTITY_ID]||t.parameters?.id):t.action===s.SORT_ENTITIES?on(t.parameters||{}):!1}function vo(t){return rn(Ut(t),t[d.SEARCH_QUERY]||t.title||F)}var Z="mayabot-handoff-panel",un="mayabot-handoff-overlay-styles",Lo=Object.freeze(["contact","support","help"]),Po=Object.freeze(["checkout","cart"]),fn=new Set([s.CHECKOUT_HANDOFF,s.HANDOFF_TO_ADVISOR,s.HANDOFF_TO_AGENT,s.HANDOFF_TO_CLINIC,s.HANDOFF_TO_HUMAN,s.HANDOFF_TO_LAWYER,s.HANDOFF_TO_LICENSED_AGENT,s.HANDOFF_TO_RECRUITER]),ln=Object.freeze({[s.CHECKOUT_HANDOFF]:{title:"Checkout needs your confirmation",body:"This step may include payment or a secure checkout page. I can take you there, then you complete the final step yourself.",primary:"Open checkout"},[s.HANDOFF_TO_ADVISOR]:{title:"Advisor handoff",body:"This request needs a qualified advisor. I can open the contact path so the site team can continue.",primary:"Contact advisor"},[s.HANDOFF_TO_AGENT]:{title:"Agent handoff",body:"This step needs an agent or account-specific help. I can open the contact path for follow-up.",primary:"Contact agent"},[s.HANDOFF_TO_CLINIC]:{title:"Clinic handoff",body:"This request needs clinic confirmation. I can open the appointment or contact path for the next step.",primary:"Contact clinic"},[s.HANDOFF_TO_HUMAN]:{title:"Human handoff",body:"This step needs human confirmation. I can open the most relevant contact path.",primary:"Open contact"},[s.HANDOFF_TO_LAWYER]:{title:"Legal handoff",body:"This request needs a legal professional. I can open the consultation or contact path.",primary:"Contact lawyer"},[s.HANDOFF_TO_LICENSED_AGENT]:{title:"Licensed agent handoff",body:"This request needs a licensed agent. I can open the quote or contact path for follow-up.",primary:"Contact agent"},[s.HANDOFF_TO_RECRUITER]:{title:"Recruiter handoff",body:"This request needs recruiter review. I can open the application or contact path.",primary:"Contact recruiter"}});function z(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}function j(t){return String(t||"").trim()}function Do(){if(document.getElementById(un))return;let t=document.createElement("style");t.id=un,t.textContent=`
    #${Z} {
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
    #${Z}.active {
      transform: translate(-50%, 0);
      opacity: 1;
      pointer-events: auto;
    }
    .mayabot-handoff-body {
      display: grid;
      gap: 12px;
      padding: 16px;
    }
    .mayabot-handoff-top {
      display: flex;
      align-items: start;
      justify-content: space-between;
      gap: 14px;
    }
    .mayabot-handoff-title {
      margin: 0;
      color: #161615;
      font-size: 16px;
      font-weight: 800;
      line-height: 1.25;
      letter-spacing: 0;
    }
    .mayabot-handoff-close {
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
    .mayabot-handoff-text {
      margin: 0;
      color: #534d44;
      font-size: 14px;
      line-height: 1.45;
    }
    .mayabot-handoff-reason {
      margin: 0;
      border-left: 3px solid #d9b66f;
      padding: 8px 10px;
      background: #fbf6ea;
      color: #534d44;
      font-size: 12px;
      line-height: 1.35;
      overflow-wrap: anywhere;
    }
    .mayabot-handoff-meta {
      display: grid;
      gap: 4px;
      margin: 0;
      color: #6f665b;
      font-size: 12px;
      line-height: 1.35;
      overflow-wrap: anywhere;
    }
    .mayabot-handoff-meta strong {
      color: #161615;
      font-weight: 760;
    }
    .mayabot-handoff-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: flex-end;
    }
    .mayabot-handoff-actions button {
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
    .mayabot-handoff-actions button.secondary {
      background: #ffffff;
      color: #161615;
    }
    @media (max-width: 430px) {
      #${Z} {
        bottom: 82px;
        width: min(calc(100vw - 20px), 420px);
      }
    }
  `,document.head.appendChild(t)}function Uo(){Do();let t=document.getElementById(Z);return t||(t=document.createElement("div"),t.id=Z,t.setAttribute("aria-live","polite"),document.body.appendChild(t),t)}function Mo(){return window.AIHubAdapterRuntime?.config?.adapter?.routes||window.AIHubAdapter?.config?.adapter?.routes||{}}function ko(t,e){let n=dn(e[d.URL]||e.path||e.href||e.handoff_flow?.page_url);if(n)return n;let r=Mo(),o=t===s.CHECKOUT_HANDOFF?Po:Lo;for(let a of o){let i=dn(r[a]);if(i)return i}return""}function dn(t){let e=j(t);if(!e)return"";try{let n=new URL(e,window.location.origin);return n.origin!==window.location.origin?"":`${n.pathname}${n.search}${n.hash}`||"/"}catch{return""}}function Fo(t){return ln[t]||ln[s.HANDOFF_TO_HUMAN]}function Ho(t){return t&&typeof t=="object"?t:{}}function Bo(t,e){return j(t.title)||e}function Yo(t,e,n){return j(e[d.MESSAGE])||j(t.handling)||n}function jo(t,e){return j(e[d.REASON]||e.reason||e.blocked_reason||t.key)}function $o(t){let e=[["Provider",t.provider_label||t.provider],["Boundary",t.automation_boundary],["Recovery",t.recovery],["Evidence",t.evidence],["Page",t.page_url]].filter(([,n])=>j(n));return e.length?`
    <p class="mayabot-handoff-meta">
      ${e.map(([n,r])=>`<span><strong>${z(n)}:</strong> ${z(r)}</span>`).join("")}
    </p>
  `:""}function pn(t){t.classList.remove("active")}function Vo(){window.setTimeout(()=>{let t=document.getElementById("mayabot-chat"),e=document.getElementById("mayabot-msgs");e&&(e.innerHTML=""),t&&t.classList.remove("visible")},V)}function mn(t,e={}){let n=j(t).toUpperCase(),r=Fo(n),o=Ho(e.handoff_flow),a=Uo(),i=ko(n,e),c=Bo(o,r.title),p=Yo(o,e,r.body),h=jo(o,e);return a.innerHTML=`
    <div class="mayabot-handoff-body">
      <div class="mayabot-handoff-top">
        <h2 class="mayabot-handoff-title">${z(c)}</h2>
        <button class="mayabot-handoff-close" type="button" aria-label="Close handoff">&times;</button>
      </div>
      <p class="mayabot-handoff-text">${z(p)}</p>
      ${$o(o)}
      ${h?`<p class="mayabot-handoff-reason">${z(h)}</p>`:""}
      <div class="mayabot-handoff-actions">
        <button type="button" class="secondary" data-close-handoff>Close</button>
        ${i?`<button type="button" data-open-handoff>${z(r.primary)}</button>`:""}
      </div>
    </div>
  `,a.querySelector(".mayabot-handoff-close")?.addEventListener("click",()=>pn(a)),a.querySelector("[data-close-handoff]")?.addEventListener("click",()=>pn(a)),a.querySelector("[data-open-handoff]")?.addEventListener("click",()=>{window.location.href=i}),a.classList.add("active"),Vo(),!0}function _n(t){return fn.has(t.action)}function hn(t){return mn(t.action,t.parameters||{})}function gn(t){return t.action===s.NAVIGATE_TO&&!!Tn(t.parameters?.[d.PAGE])}function bn(t){return window.location.href=Tn(t.parameters?.[d.PAGE]),!0}function Tn(t){let e=String(t||"").trim();if(!e||En(e)||/^https?:\/\//i.test(e))return"";if(e==="home"||e==="/")return"/";let n=zo(e);if(n)return n;let r=e.replace(/^\/+|\/+$/g,"");return r?`/${r}`:"/"}function zo(t){let e=window.AIHubAdapterRuntime?.config?.adapter?.routes||window.AIHubAdapter?.config?.adapter?.routes||{},n=Wo(t);for(let r of n){let o=e[r],a=yn(o);if(a)return a}for(let[r,o]of Object.entries(e)){if(!n.includes(Mt(r)))continue;let a=yn(o);if(a)return a}return""}function Wo(t){let e=Mt(t),n=String(t||"").trim().replace(/^\/+|\/+$/g,"").toLowerCase(),r=n.split("?")[0].split("#")[0].split("/").filter(Boolean).pop()||"";return Array.from(new Set([e,n,Mt(r)].filter(Boolean)))}function Mt(t){return String(t||"").trim().toLowerCase().replace(/[^a-z0-9/_\s-]+/g," ").replace(/[_-]+/g," ").replace(/\s+/g," ").trim().replace(/\s+/g,"-")}function yn(t){let e=String(t||"").trim();if(!e||En(e))return"";if(/^https?:\/\//i.test(e))try{let n=new URL(e);return n.origin!==window.location.origin?"":`${n.pathname||"/"}${n.search||""}${n.hash||""}`}catch{return""}return e.startsWith("/")?e:`/${e.replace(/^\/+/,"")}`}function En(t){return/^(?:javascript:|data:|\/\/)/i.test(String(t||"").trim())}function An(t){let e=t?.params||t?.parameters||{};return{...t||{},action:String(t?.action||"").trim().toUpperCase(),params:e,parameters:e}}var kt="AIHubAdapterRuntime",Ft="AIHubAdapter";function Go(t){let e=t?.params||t?.parameters||{};return{...t||{},params:e,parameters:e}}function tt(){return!!(window[kt]?.executeAction||window[Ft]?.handleAction)}async function Ht(t){return(await et(t)).succeeded}async function et(t){let e=Go(t);if(window[kt]?.executeAction){let n=window[kt],r=await n.executeAction(e)===!0,o=n.lastActionResult||{};return{succeeded:r,handled:o.handled===!0||r,status:o.status||(r?"ok":"not_handled"),reason:o.reason||"",blocked:o.status==="blocked",disabled:o.status==="disabled"}}if(window[Ft]?.handleAction){let n=await window[Ft].handleAction(e)===!0;return{succeeded:n,handled:n,status:n?"ok":"not_handled",reason:"",blocked:!1,disabled:!1}}return{succeeded:!1,handled:!1,status:"missing_adapter",reason:"",blocked:!1,disabled:!1}}var qo=Object.freeze([{path:"/api/products?per_page=96",routePrefix:"/product/"},{path:"/api/products",routePrefix:"/product/"},{path:"/api/products.json",routePrefix:""},{path:"/products.json",routePrefix:"/products/"},{path:"/collections/all/products.json",routePrefix:"/products/"}]),Ko=Object.freeze(["products","data","items","results"]),In=Object.freeze(["id","product_id","handle","sku"]),On=Object.freeze(["name","title"]),Qo=Object.freeze(["url","href","permalink","product_url"]),Xo=Object.freeze(["image_url","imageUrl","image_src","imageSrc","image","images","media","thumbnail","thumbnail_url","featured_image","featuredImage","featured_image_url"]),Jo=Object.freeze(["brand","vendor"]),Zo=Object.freeze(["category","category_name","product_type"]),ta=Object.freeze(["description","summary","body_html"]),ea=Object.freeze(["original_price","compare_at_price","regular_price"]),wn=Object.freeze(["currency","currency_code"]),na=Object.freeze(["display_price","price_text","formatted_price"]),ra="Unknown Brand",oa="Products",aa="/",ia=/^[a-z0-9][a-z0-9-]*$/i,Bt=null;function S(t){return t==null||typeof t=="object"?"":String(t||"").trim()}function $t(t){return S(t).toLowerCase().replace(/[^a-z0-9]+/g," ").trim()}function xn(t){let e=new Set(["a","am","an","and","ask","asked","did","for","me","not","on","only","please","show","some","the","to","wanna","want","what","with","you","your"]),n=[],r=new Set;for(let o of sa($t(t)).split(" ")){let a=ca(o);a.length<=1||e.has(a)||r.has(a)||(n.push(a),r.add(a))}return n}function sa(t){return t.replace(/\b(?:i\s+)?did\s+not\s+ask\s+for\s+(?:a\s+|an\s+)?[a-z0-9]+\b/g," ")}function ca(t){return["phone","phones","mobile","mobiles"].includes(t)?"phone":["book","books"].includes(t)?"books":t}function Vt(t,e){return e.map(n=>S(t?.[n])).filter(Boolean)}function R(t,e){return Vt(t,e)[0]||""}function mt(t){let e=S(t).replace(/,/g,"");if(!e)return 0;let n=e.match(/-?\d+(?:\.\d+)?/),r=Number(n?n[0]:e);return Number.isFinite(r)?r:0}function ua(t,e){let n=R(t,na);if(n)return n;let r=R(t,wn).toUpperCase();return e>0&&r?`${r} ${e.toLocaleString()}`:e>0?e.toLocaleString():""}function la(t){for(let e of Xo){let n=Yt(t?.[e]);if(n)return n}return""}function Yt(t){if(!t)return"";if(Array.isArray(t)){for(let e of t){let n=Yt(e);if(n)return n}return""}if(typeof t=="object"){for(let e of["src","url","image_url","imageUrl","image_src","imageSrc","thumbnail","thumbnail_url","featured_image","featuredImage","featured_image_url"]){let n=Yt(t[e]);if(n)return n}return""}return da(t)}function da(t){let e=S(t);if(!e||/^javascript:/i.test(e))return"";if(/^data:image\//i.test(e))return e;try{let n=new URL(e,window.location.origin);return["http:","https:"].includes(n.protocol)?n.toString():""}catch{return""}}function pa(t){let e=S(t);if(!e)return"";try{let n=new URL(e,window.location.origin);return n.origin!==window.location.origin?"":`${n.pathname}${n.search}${n.hash}`}catch{return""}}function fa(t,e,n){let r=pa(R(t,Qo));return r||(!ia.test(e)||!/[a-z]/i.test(e)||!n?.routePrefix?"":`${n.routePrefix}${encodeURIComponent(e)}${aa}`)}function zt(t,e={}){if(!t)return null;let n=R(t,In),r=S(t.handle||t.slug||t.product_handle),o=R(t,On),a=mt(t.price||t.amount||t.cost),i=mt(R(t,ea));return!n&&!r?null:{id:n,handle:r,name:o,title:S(t.title||o),brand:R(t,Jo)||ra,category:R(t,Zo)||oa,description:R(t,ta),price:Number.isFinite(a)?a:0,originalPrice:Number.isFinite(i)?i:0,displayPrice:ua(t,a),currency:R(t,wn),rating:mt(t.rating||t.review_rating),reviewCount:mt(t.review_count||t.reviews_count||t.reviews),imageUrl:la(t),url:fa(t,r||n,e)}}function ma(t){return Vt(t,In)}function Sn(t){return Vt(t,On).map($t)}function Rn(t,e){let n=S(e);return!!(n&&ma(t).includes(n))}function Cn(t,e){let n=xn(e);if(!n.length)return!1;let r=$t([t?.name,t?.title,t?.brand,t?.category,t?.category_name,t?.product_type,t?.description,t?.tags].join(" "));return n.every(o=>r.includes(o)||r.includes(o.replace(/s$/,"")))}function _a(t,e){let n=new Set(Sn(e));return Sn(t).some(r=>n.has(r))}function ha(t,e){return!!(t?.imageUrl&&t.imageUrl===e?.imageUrl)}function ya(t){if(Array.isArray(t))return t;for(let e of Ko){let n=t?.[e];if(Array.isArray(n))return n}return[]}async function ga(t){try{let e=await fetch(new URL(t.path,window.location.origin),{headers:{Accept:"application/json"}});if(!e.ok)return[];let n=await e.json();return ya(n).map(r=>zt(r,t)).filter(Boolean)}catch(e){return console.warn(`[AI Hub Widget] Catalog endpoint lookup failed for ${t.path}:`,e),[]}}async function jt(){return Bt||(Bt=Promise.all(qo.map(ga)).then(t=>t.flat())),Bt}async function ba(t,e=120){if(!xn(t).length)return[];let r=new URL("/v1/products",l.apiUrl);r.searchParams.set("site_id",l.siteId),r.searchParams.set("limit",String(e));try{let o=await fetch(r.toString(),{headers:{Accept:"application/json"}});return o.ok?(await o.json()).map(a=>zt(a)).filter(Boolean).filter(a=>Cn(a,t)).slice(0,12):[]}catch(o){return console.warn("[AI Hub Widget] Hub product search fallback failed:",o),[]}}async function Nn(t,e=""){let n=(Array.isArray(t)?t:[]).map(S).filter(Boolean),r=[],o="",a="";if(n.length)try{r=await vn(n),o="hub_by_ids"}catch(i){a="hub_product_lookup_failed",console.warn("[AI Hub Widget] Hub product ID lookup failed:",i)}if(!r.length&&n.length){let i=await jt();r=n.map(c=>i.find(p=>Rn(p,c))).filter(Boolean),r.length&&(o="host_by_ids")}return!r.length&&e&&(r=await ba(e),r.length&&(o="hub_search")),!r.length&&e&&(r=(await jt()).filter(c=>Cn(c,e)).slice(0,12),r.length&&(o="host_search")),{products:r,source:o,reason:r.length?"":a||"no_matching_products_rendered"}}async function vn(t){let e=(Array.isArray(t)?t:[]).map(S).filter(Boolean);if(!e.length)return[];let n=new URL(O.PRODUCTS_BY_IDS,l.apiUrl);n.searchParams.set("site_id",l.siteId),n.searchParams.set("ids",e.join(","));let r=await fetch(n.toString(),{headers:{Accept:"application/json"}});if(!r.ok)throw new Error("Failed to fetch products from AI Hub API");let o=(await r.json()).map(i=>zt(i)).filter(Boolean),a=new Map(o.map(i=>[String(i.id),i]));return e.map(i=>a.get(i)).filter(Boolean)}async function _t(t){let e=S(t);if(!e)return"";let[n]=await vn([e]);if(n?.url)return n.url;let r=await jt(),o=r.find(i=>Rn(i,e));return o?.url?o.url:n&&r.find(i=>_a(i,n)||ha(i,n))?.url||""}var Ta=["data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='320' height='240' viewBox='0 0 320 240'%3E","%3Crect width='320' height='240' fill='%23f1f2ee'/%3E","%3Cpath d='M98 156h124l-31-40-25 30-17-22-51 32Z' fill='%23c8c3ba'/%3E","%3Ccircle cx='117' cy='95' r='17' fill='%23d8d3ca'/%3E","%3Ctext x='160' y='198' text-anchor='middle' fill='%23686660' font-family='Arial,sans-serif' font-size='16'%3EImage pending%3C/text%3E","%3C/svg%3E"].join(""),Ln=12,Gt=[],qt=v,Un=new Map;function H(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}function Ea(){if(document.getElementById("mayabot-product-overlay-styles"))return;let t=document.createElement("style");t.id="mayabot-product-overlay-styles",t.textContent=`
    #mayabot-product-panel {
      position: fixed;
      left: 50%;
      bottom: 96px;
      z-index: 2147483638;
      width: min(calc(100vw - 32px), var(--mayabot-panel-width, 720px));
      max-height: min(72vh, var(--mayabot-panel-max-height, 560px));
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
    #mayabot-product-panel.active {
      transform: translate(-50%, 0);
      opacity: 1;
      pointer-events: auto;
    }
    #mayabot-product-panel.count-1 { --mayabot-panel-width: 360px; --mayabot-panel-max-height: 470px; }
    #mayabot-product-panel.count-2 { --mayabot-panel-width: 600px; --mayabot-panel-max-height: 500px; }
    #mayabot-product-panel.count-3 { --mayabot-panel-width: 860px; --mayabot-panel-max-height: 520px; }
    #mayabot-product-panel.count-many { --mayabot-panel-width: 980px; --mayabot-panel-max-height: 620px; }
    .mayabot-product-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
      padding: 14px 16px;
      border-bottom: 1px solid rgba(22, 22, 21, 0.1);
    }
    .mayabot-product-title {
      margin: 0;
      color: #161615;
      font-size: 15px;
      font-weight: 800;
      line-height: 1.25;
      letter-spacing: 0;
    }
    .mayabot-product-close {
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
    .mayabot-product-grid {
      display: grid;
      grid-template-columns: repeat(var(--mayabot-card-count, 2), minmax(0, 1fr));
      gap: 12px;
      padding: 14px;
      overflow: auto;
      scrollbar-width: thin;
    }
    .mayabot-product-card {
      display: flex;
      flex-direction: column;
      gap: 9px;
      min-width: 0;
      border: 1px solid rgba(22, 22, 21, 0.1);
      border-radius: 8px;
      background: #ffffff;
      padding: 12px;
    }
    /* Facts scroll inside the card so Add/View stay reachable on short screens. */
    .mayabot-product-facts {
      margin: 0;
      display: grid;
      gap: 6px;
      overflow: auto;
      max-height: 190px;
      flex: 1 1 auto;
      min-height: 0;
      font-size: 12px;
      line-height: 1.35;
    }
    .mayabot-fact {
      display: grid;
      grid-template-columns: minmax(64px, 38%) 1fr;
      gap: 8px;
      align-items: start;
      border-top: 1px solid rgba(22, 22, 21, 0.07);
      padding-top: 5px;
    }
    .mayabot-fact:first-child { border-top: 0; padding-top: 0; }
    .mayabot-fact dt {
      margin: 0;
      color: rgba(22, 22, 21, 0.55);
      font-weight: 600;
      overflow-wrap: anywhere;
    }
    .mayabot-fact dd {
      margin: 0;
      color: #161615;
      overflow-wrap: anywhere;
    }
    .mayabot-product-image {
      width: 100%;
      height: clamp(132px, 18vw, 178px);
      object-fit: contain;
      border-radius: 8px;
      background: #f1f2ee;
      padding: 8px;
      mix-blend-mode: multiply;
    }
    .mayabot-product-name {
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
    .mayabot-product-meta {
      margin: 0;
      color: #686660;
      font-size: 13px;
      line-height: 1.35;
      overflow-wrap: anywhere;
    }
    .mayabot-product-actions {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
      align-self: stretch;
      margin-top: auto;
      flex: 0 0 auto;
    }
    .mayabot-product-actions button {
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
    .mayabot-product-actions button.secondary {
      background: #ffffff;
      color: #161615;
    }
    .mayabot-product-empty {
      margin: 0;
      padding: 14px;
      color: #686660;
      font-size: 14px;
    }
    @media (max-width: 720px) {
      #mayabot-product-panel {
        bottom: 86px;
        width: min(calc(100vw - 20px), 520px);
      }
      #mayabot-product-panel.count-2,
      #mayabot-product-panel.count-3,
      #mayabot-product-panel.count-many {
        --mayabot-card-count: 2;
      }
      .mayabot-product-grid {
        padding: 12px;
      }
      .mayabot-product-image {
        height: clamp(118px, 32vw, 150px);
      }
    }
    @media (max-width: 430px) {
      #mayabot-product-panel {
        bottom: 82px;
      }
      .mayabot-product-grid {
        grid-template-columns: minmax(0, 1fr);
      }
    }
  `,document.head.appendChild(t)}function Aa(){Ea();let t=document.getElementById("mayabot-product-panel");return t||(t=document.createElement("div"),t.id="mayabot-product-panel",t.setAttribute("aria-live","polite"),t.innerHTML=`
    <div class="mayabot-product-header">
      <h2 class="mayabot-product-title">${v}</h2>
      <button class="mayabot-product-close" type="button" aria-label="Close recommendations">&times;</button>
    </div>
    <div class="mayabot-product-grid"></div>
  `,t.querySelector(".mayabot-product-close").addEventListener("click",()=>{t.classList.remove("active")}),document.body.appendChild(t),t)}async function Sa(t){let e={action:s.ADD_TO_CART,params:{[d.PRODUCT_ID]:t,[d.QUANTITY]:Ot},parameters:{[d.PRODUCT_ID]:t,[d.QUANTITY]:Ot}};tt()&&await Ht(e)||window.dispatchEvent(new CustomEvent(X.MAYABOT_ACTION,{detail:e}))}async function Ia(t){try{let n=await _t(t);if(n){window.location.href=n;return}}catch(n){console.warn("[AI Hub Widget] Product detail URL lookup failed:",n)}let e={action:s.SHOW_PRODUCT_DETAIL,params:{[d.PRODUCT_ID]:t},parameters:{[d.PRODUCT_ID]:t}};tt()&&await Ht(e)||window.dispatchEvent(new CustomEvent(X.MAYABOT_ACTION,{detail:e}))}function Oa(t){return t<=1?"count-1":t===2?"count-2":t===3?"count-3":"count-many"}function wa(t){return t<=1?1:t===2?2:3}function xa(t){let e=new Set;return(Array.isArray(t)?t:[]).map(n=>String(n??"").trim()).filter(Boolean).filter(n=>e.has(n)?!1:(e.add(n),!0))}function Wt(t,e,n="",r={}){let o=(Array.isArray(e)?e:[]).map(p=>String(p?.id??"").trim()).filter(Boolean),a=o.length,i=t.length,c=a>0?"succeeded":"failed";return{status:c,stage:"product_overlay",reason:n||(c==="succeeded"?"":"no_matching_products_rendered"),evidence:{requested_product_count:i,rendered_product_count:a,missing_product_count:Math.max(i-a,0),requested_product_ids:t.slice(0,Ln).join(","),rendered_product_ids:o.slice(0,Ln).join(","),lookup_source:r.source||"",search_query:r.searchQuery||""}}}function Ra(t){let e=String(t?.displayPrice||"").trim();if(e)return e;let n=Number(t?.price||0);return Number.isFinite(n)&&n>0?n.toLocaleString():"Price unavailable"}var Ca=6,Na=24,va=120;function La(t){let e=new Map;return Array.isArray(t)&&t.forEach(n=>{if(!n||typeof n!="object")return;let r=String(n.product_id||"").trim();if(!r||!Array.isArray(n.facts))return;let o=n.facts.filter(a=>a&&typeof a=="object"&&a.label&&a.value).slice(0,Ca).map(a=>({label:String(a.label).slice(0,Na),value:String(a.value).slice(0,va)}));o.length&&e.set(r,o)}),e}function Pa(t){let e=Un.get(String(t));return!e||!e.length?"":`<dl class="mayabot-product-facts">${e.map(r=>`<div class="mayabot-fact"><dt>${H(r.label)}</dt><dd>${H(r.value)}</dd></div>`).join("")}</dl>`}function ht(t,e){let n=Aa(),r=n.querySelector(".mayabot-product-grid"),o=n.querySelector(".mayabot-product-title"),a=t.length;if(Gt=Array.isArray(t)?[...t]:[],qt=e||v,n.classList.remove("count-1","count-2","count-3","count-many"),n.classList.add(Oa(a)),n.style.setProperty("--mayabot-card-count",String(wa(a))),o.textContent=qt,!a){r.innerHTML='<p class="mayabot-product-empty">No matching products are currently available.</p>',n.classList.add("active"),Pn();return}r.innerHTML=t.map(i=>{let c=H(i.id);return`
        <article class="mayabot-product-card" data-product-id="${c}">
          <img class="mayabot-product-image" src="${H(i.imageUrl||Ta)}" alt="${H(i.name)}">
          <h3 class="mayabot-product-name">${H(i.name||i.title||"Product")}</h3>
          <p class="mayabot-product-meta">${H(i.brand)} - ${H(Ra(i))}</p>
          ${Pa(i.id)}
          <div class="mayabot-product-actions">
            <button type="button" data-add="${c}">Add</button>
            <button type="button" class="secondary" data-view="${c}">View</button>
          </div>
        </article>
      `}).join(""),r.querySelectorAll("[data-add]").forEach(i=>{i.addEventListener("click",async()=>{await Sa(i.getAttribute("data-add"))})}),r.querySelectorAll("[data-view]").forEach(i=>{i.addEventListener("click",async()=>{await Ia(i.getAttribute("data-view"))})}),n.classList.add("active"),Pn()}function Pn(){window.setTimeout(()=>{let t=document.getElementById("mayabot-chat"),e=document.getElementById("mayabot-msgs");e&&(e.innerHTML=""),t&&t.classList.remove("visible")},V)}async function Mn(t,e=v,n={}){let r=xa(t),o=String(n.searchQuery||"").trim();if(Un=La(n.comparisonFacts),!r.length&&!o)return ht([],e),Wt([],[],"missing_product_ids");try{let{products:a,source:i,reason:c}=await Nn(r,o);return ht(a,e),Wt(r,a,c,{source:i,searchQuery:o})}catch(a){return console.warn("[AI Hub Widget] Product overlay failed:",a),ht([],e),Wt(r,[],"product_overlay_fetch_failed",{searchQuery:o})}}function kn(t={}){if(!Gt.length)return!1;let e=String(t.sort_by||t.sortBy||"price_asc").trim().toLowerCase(),n=[...Gt].sort((r,o)=>Da(r,o,e));return ht(n,Ua(qt,e)),!0}function Da(t,e,n){return n==="price_desc"?W(e.price,Number.NEGATIVE_INFINITY)-W(t.price,Number.NEGATIVE_INFINITY):n==="rating"?W(e.rating||e.review_rating,Number.NEGATIVE_INFINITY)-W(t.rating||t.review_rating,Number.NEGATIVE_INFINITY):n==="newest"?Dn(e)-Dn(t):W(t.price,Number.POSITIVE_INFINITY)-W(e.price,Number.POSITIVE_INFINITY)}function W(t,e){let n=String(t??"").replace(/,/g,"").match(/-?\d+(?:\.\d+)?/);if(!n)return e;let r=Number(n[0]);return Number.isFinite(r)?r:e}function Dn(t){let e=t?.updated_at||t?.created_at||t?.date||"",n=Date.parse(String(e||""));return Number.isFinite(n)?n:0}function Ua(t,e){let n={price_asc:"sorted low to high",price_desc:"sorted high to low",rating:"sorted by rating",newest:"newest first"};return`${String(t||v).replace(/\s+-\s+sorted.*$/i,"")} - ${n[e]||n.price_asc}`}function Hn(t){return t.action===s.SHOW_PRODUCTS||t.action===s.SHOW_COMPARISON||t.action===s.SHOW_PRODUCT_DETAIL||t.action===s.SORT_PRODUCTS}async function Bn(t){return t.action===s.SHOW_COMPARISON?Fn(t.parameters||{},"Product comparison",{syncListing:!1,comparisonFacts:(t.parameters||{}).comparison}):t.action===s.SHOW_PRODUCTS?Fn(t.parameters||{},v):t.action===s.SHOW_PRODUCT_DETAIL?Fa(t.parameters||{}):t.action===s.SORT_PRODUCTS?kn(t.parameters||{}):!1}async function Fn(t,e=v,n={}){let r=Array.isArray(t[d.PRODUCT_IDS])?t[d.PRODUCT_IDS]:[],o=ka(t),i=n.syncListing!==!1?await Ma(o):{succeeded:!1,handled:!1,status:"skipped",stage:"product_display_sync",reason:"comparison_overlay"},c=await Mn(r,t.title||o||e,{searchQuery:o,comparisonFacts:n.comparisonFacts}),p={...c.evidence||{},listing_sync_status:i.status||"",listing_sync_stage:i.stage||"",listing_sync_reason:i.reason||""};return c.status!=="succeeded"?{...c,evidence:p}:o&&i.handled&&!i.succeeded?{status:"failed",stage:"product_display_sync",reason:i.reason||i.status||"listing_sync_failed",evidence:p}:{...c,stage:i.succeeded?"product_display_sync":c.stage,evidence:p}}async function Ma(t){let e=Yn(t);return e?et({action:s.FILTER_PRODUCTS,params:{[d.SEARCH_QUERY]:e,query:e,q:e}}):{succeeded:!1,handled:!1,status:"skipped",stage:"product_display_sync",reason:"missing_search_query"}}function ka(t){return Yn(t[d.SEARCH_QUERY]||t.search||t.query||t.q||"")}function Yn(t){return String(t||"").trim()}async function Fa(t){let e="";try{e=await _t(t[d.PRODUCT_ID])}catch(n){return console.warn("[AI Hub Widget] Product detail URL lookup failed:",n),!1}return e?(window.location.href=e,!0):!1}var Kt="stop_action_fallback",Ha=new Set([s.SHOW_PRODUCTS,s.SHOW_COMPARISON,s.SHOW_PRODUCT_DETAIL,s.SORT_PRODUCTS]);function jn(t){return tt()&&!Ha.has(t.action)}async function $n(t){let e=await et(t);return e.succeeded?!0:e.blocked||e.disabled?Kt:!1}function Vn(t){return window.dispatchEvent(new CustomEvent(X.MAYABOT_ACTION,{detail:t})),!0}var Ba=Object.freeze([{name:"runtime_adapter",canExecute:jn,execute:$n},{name:"product_overlay",canExecute:Hn,execute:Bn},{name:"entity_overlay",canExecute:sn,execute:cn},{name:"handoff_overlay",canExecute:_n,execute:hn},{name:"platform_adapter",canExecute:()=>!0,execute:Pe},{name:"provider_adapter",canExecute:ze,execute:We},{name:"navigation",canExecute:gn,execute:bn},{name:"browser_event",canExecute:()=>!0,execute:Vn}]);async function Xt(t){let e=[];for(let n of t||[]){let r=An(n),o=await Ya(r);o&&e.push(o)}return e}async function Ya(t){if(!t.action)return;let e=Date.now(),n=window.location.href;await ct(l.apiUrl,l.siteId,t,{status:"requested",stage:"widget_dispatch",requested_url:n,final_url:n,evidence:Qt(t,n,n)}),await ct(l.apiUrl,l.siteId,t,{status:"executing",stage:"widget_dispatch",requested_url:n,final_url:window.location.href,evidence:Qt(t,n,window.location.href)});let r;try{r=await ja(t)}catch(i){r={status:"failed",stage:"widget_dispatch",reason:i instanceof Error?i.message:"execution_error"}}let o=window.location.href,a=Qt(t,n,o,r);return await ct(l.apiUrl,l.siteId,t,{status:r.status,stage:r.stage,reason:r.reason,duration_ms:Date.now()-e,requested_url:n,final_url:o,evidence:a}),{action:t.action,request_id:t.request_id||t.action_request_id||"",turn_id:t.turn_id||"",sequence:Number(t.sequence||0),status:r.status,stage:r.stage,reason:r.reason,requested_url:n,final_url:o,evidence:a}}async function ja(t){if(!t.action)return{status:"failed",stage:"normalization",reason:"missing_action"};for(let e of Ba){if(!e.canExecute(t))continue;let n=await e.execute(t),r=$a(n,e.name);if(r)return r}return{status:"failed",stage:"all",reason:"no_executor_succeeded"}}function $a(t,e){if(t===!0)return{status:"succeeded",stage:e,reason:""};if(t===Kt)return{status:"blocked",stage:e,reason:"action_blocked"};if(!t||typeof t!="object")return null;let n=String(t.status||"").trim().toLowerCase();return n?{status:n,stage:String(t.stage||e).trim()||e,reason:String(t.reason||"").trim(),evidence:t.evidence&&typeof t.evidence=="object"?t.evidence:{}}:null}function Qt(t,e,n,r={}){let o=t.parameters||t.params||{},a={requested_url:e,final_url:n,url_changed:e!==n,path_changed:zn(e)!==zn(n),title:document.title||"",stage:r.stage||"",result_status:r.status||""};return o.page&&(a.target_page=o.page),o.product_id&&(a.product_id=o.product_id),o.entity_id&&(a.entity_id=o.entity_id),Array.isArray(o.product_ids)&&(a.product_count=o.product_ids.length),Array.isArray(o.entity_ids)&&(a.entity_count=o.entity_ids.length),{...a,...r.evidence&&typeof r.evidence=="object"?r.evidence:{}}}function zn(t){try{return new URL(t,window.location.href).pathname}catch{return""}}var Va=1,za=1.08,Wa=300,Ga=Object.freeze(["hannah","sonia","libby","ava","susan","hazel","heera","salli","joanna","amy","emma","olivia","natasha","zira","aria","jenny","samantha","victoria","tessa","moira","karen","female","woman","nova","shimmer","google us english","microsoft aria"]),P="",yt="",nt=null,Jt=0;function rt(t){if(!("speechSynthesis"in window)||!("SpeechSynthesisUtterance"in window))return!1;gt();let e=++Jt;P=t;let n=()=>{if(e!==Jt||P!==t)return!1;try{let r=new SpeechSynthesisUtterance(t),o=qa(window.speechSynthesis.getVoices());return o?(o&&(r.voice=o),r.rate=Va,r.pitch=za,r.onstart=Wn,r.onend=Wn,gt(),window.speechSynthesis.cancel(),window.speechSynthesis.resume(),window.speechSynthesis.speak(r),!0):(P="",!1)}catch{return!1}};return window.speechSynthesis.getVoices().length>0?n():(window.speechSynthesis.onvoiceschanged=n,nt=window.setTimeout(()=>{nt=null,n()},Wa),!0)}function bt(){P&&rt(P)}function Gn(){try{return!!P||!!window.speechSynthesis?.speaking||!!window.speechSynthesis?.pending}catch{return!!P}}function qn(){Jt+=1,gt(),P="",yt="";try{window.speechSynthesis?.cancel()}catch{}}function qa(t){if(!Array.isArray(t)||t.length===0)return null;let e=Ka(t)||Qa(t);return e&&(yt=e.name),e}function Ka(t){if(yt){let n=t.find(r=>r.name===yt);if(n)return n}let e=String(l.speechVoiceName||"").toLowerCase();return e&&t.find(n=>n.name.toLowerCase()===e)||null}function Qa(t){return l.speechVoicePreference.toLowerCase()!=="female"?t.find(e=>e.default)||t[0]:t.find(e=>Ga.some(n=>e.name.toLowerCase().includes(n)))||null}function Wn(){gt(),P=""}function gt(){nt&&window.clearTimeout(nt),nt=null,window.speechSynthesis&&(window.speechSynthesis.onvoiceschanged=null)}var f=Object.freeze({NETWORK:"network",TIMEOUT:"timeout",ACCESS_DENIED:"access_denied",INVALID_REQUEST:"invalid_request",PAYLOAD_TOO_LARGE:"payload_too_large",UNSUPPORTED_MEDIA:"unsupported_media",RATE_LIMITED:"rate_limited",PROVIDER_UNAVAILABLE:"provider_unavailable",SERVER_ERROR:"server_error",MICROPHONE:"microphone",UNKNOWN:"unknown"}),Kn=Object.freeze({[f.NETWORK]:"Connection issue",[f.TIMEOUT]:"Timed out",[f.ACCESS_DENIED]:"Access denied",[f.INVALID_REQUEST]:"Try again",[f.PAYLOAD_TOO_LARGE]:"Recording too long",[f.UNSUPPORTED_MEDIA]:"Audio not supported",[f.RATE_LIMITED]:"Service busy",[f.PROVIDER_UNAVAILABLE]:"Service unavailable",[f.SERVER_ERROR]:"Service error",[f.MICROPHONE]:"Mic unavailable",[f.UNKNOWN]:"Try again"}),Qn=64,T=class extends Error{constructor(e,{status:n=0,code:r="",requestId:o="",stage:a=""}={}){super(`voice_transport_${e}`),this.name="VoiceTransportError",this.category=e,this.status=Number(n)||0,this.code=String(r||"").slice(0,Qn),this.requestId=String(o||"").slice(0,Qn),this.stage=a}get customerMessage(){return Xa(this.category)}toDiagnostics(){return{category:this.category,status:this.status,code:this.code,request_id:this.requestId,stage:this.stage}}};function Xa(t){return Kn[t]||Kn[f.UNKNOWN]}function Ja(t){let e=Number(t)||0;return e===401||e===403?f.ACCESS_DENIED:e===408?f.TIMEOUT:e===413?f.PAYLOAD_TOO_LARGE:e===415?f.UNSUPPORTED_MEDIA:e===429?f.RATE_LIMITED:e===502||e===503||e===504?f.PROVIDER_UNAVAILABLE:e>=500?f.SERVER_ERROR:e>=400?f.INVALID_REQUEST:f.UNKNOWN}function ot(t){if(t instanceof T)return t;let e=String(t?.message||t||"").toLowerCase();return t?.name==="AbortError"||e.includes("abort")||e.includes("timeout")||e.includes("timed out")?new T(f.TIMEOUT):e.includes("microphone")||e.includes("permission")||e.includes("notallowed")?new T(f.MICROPHONE):t?.name==="TypeError"||e.includes("failed to fetch")||e.includes("network")||e.includes("load failed")?new T(f.NETWORK):new T(f.UNKNOWN)}function Xn(t,e=null){let n=Number(t?.status)||0,r=t?.headers?.get?.("x-request-id")||t?.headers?.get?.("x-correlation-id")||"",o=e&&typeof e=="object"&&(e.code||e.error_code)||"",a=/^[A-Za-z0-9_.:-]{1,64}$/.test(String(o||""))?String(o):"";return new T(Ja(n),{status:n,code:a,requestId:r,stage:"http_response"})}var Za="/v1/widget/runtime-event",ti=16;function I(t={}){let e=JSON.stringify({site_id:l.siteId,origin:window.location.origin,occurred_at:new Date().toISOString(),session_id:l.sessionId,request_id:D(t.request_id,80),component:D(t.component||"voice",60),stage:D(t.stage,80),event_type:D(t.event_type||"runtime_event",80),severity:D(t.severity||"info",20),status:D(t.status||"ok",20),message_code:D(t.message_code,80),duration_ms:Jn(t.duration_ms),metadata:ei(t.metadata)}),n=new URL(Za,l.apiUrl).toString();fetch(n,{method:"POST",headers:{Accept:"application/json","Content-Type":"application/json"},body:e,keepalive:!0}).catch(()=>{})}function ei(t){if(!t||typeof t!="object"||Array.isArray(t))return{};let e={};for(let[n,r]of Object.entries(t).slice(0,ti)){let o=D(n,60).toLowerCase();!o||ni(o)||(typeof r=="boolean"||r===null?e[o]=r:typeof r=="number"?e[o]=Jn(r):typeof r=="string"&&(e[o]=D(r,120)))}return e}function ni(t){return["audio","transcript","response","error","exception","token","secret"].some(e=>t.includes(e))}function D(t,e){return String(t||"").replace(/\s+/g," ").trim().slice(0,e)}function Jn(t){let e=Number(t||0);return Number.isFinite(e)?Math.max(0,e):0}var ri=3,oi="AIHubAdapterRuntime",ai="AIHubAdapter";function ii(t,e){let n=new URL(O.SHOP_WS,t);return n.protocol=n.protocol==="https:"?"wss:":"ws:",n.searchParams.set("site_id",e),n.searchParams.set("session_id",l.sessionId),n.toString()}function si(t){return new Promise((e,n)=>{let r=new FileReader;r.onloadend=()=>{let o=String(r.result||"");e(o.includes(",")?o.split(",").pop():o)},r.onerror=()=>n(r.error||new Error("Failed to read audio blob")),r.readAsDataURL(t)})}var Zt=class{constructor(){this.queue=[],this.blocked=[],this.playing=!1,this.current=null,this.lastPlaybackStartMs=0,this.installUnlockListeners()}push(e,n=""){e&&(this.queue.push({audioB64:e,fallbackText:n}),this.playNext())}playNext(){if(this.playing||this.queue.length===0)return;this.playing=!0;let e=this.queue.shift(),n=new Audio(Q.DATA_WAV_PREFIX+e.audioB64);n.preload="auto",this.current=n,n.onplay=()=>{this.lastPlaybackStartMs=typeof performance<"u"?performance.now():0},n.onended=()=>{this.current=null,this.playing=!1,this.playNext()},n.onerror=()=>{this.current=null,e.fallbackText&&G(e.fallbackText),this.playing=!1,this.playNext()},n.play().catch(r=>{if(console.warn("Audio playback failed",r),this.current=null,this.isAutoplayBlocked(r)){e.fallbackText?G(e.fallbackText):this.blocked.unshift(e),this.playing=!1;return}e.fallbackText&&G(e.fallbackText),this.playing=!1,this.playNext()})}installUnlockListeners(){if(typeof window>"u")return;let e=()=>{this.retryBlocked(),bt()};window.addEventListener("pointerdown",e,{capture:!0,passive:!0}),window.addEventListener("keydown",e,{capture:!0}),window.addEventListener("touchstart",e,{capture:!0,passive:!0})}retryBlocked(){this.blocked.length&&(this.queue.unshift(...this.blocked.splice(0)),this.playNext())}speakInsteadOfBlocked(e){!e||!this.blocked.length||(this.blocked=[],G(e))}isAutoplayBlocked(e){let n=`${e?.name||""} ${e?.message||e||""}`.toLowerCase();return n.includes("notallowed")||n.includes("user didn't interact")||n.includes("not allowed")}stop(){if(this.queue=[],this.blocked=[],this.current){try{this.current.pause(),this.current.currentTime=0}catch{}this.current.onended=null,this.current.onerror=null,this.current=null}this.playing=!1,qn()}isSpeaking(){return this.playing||this.queue.length>0||Gn()}},Tt=new Zt;function ne(){Tt.stop()}function re(){return Tt.isSpeaking()}var te=class{async sendAudio(e,n,r=[]){let o=U();I({event_type:"voice_turn_started",stage:"http_request",status:"started",metadata:{transport:"http",audio_type:e?.type||"unknown"}});let a=new FormData;a.append("audio",e,pi(e)),a.append("site_id",l.siteId),a.append("session_id",l.sessionId),r&&r.length>0&&a.append("conversation_history",JSON.stringify(r));let i=er();i&&a.append("page_context",JSON.stringify(i));let c;try{c=await fetch(`${l.apiUrl}${O.SHOP}`,{method:Ae.POST,body:a})}catch(h){throw ot(h)}if(!c.ok)throw Xn(c,await fi(c));let p=await c.json();if(p.transcript&&n.onUserMessage?.(p.transcript),p.response_text&&n.onAssistantMessage?.(p.response_text,p.ui_actions||[]),n.onStatusChange?.(_.READY),p.audio_b64?di(p.audio_b64,p.response_text||""):p.response_text&&G(p.response_text),p.ui_actions&&p.ui_actions.length>0){let h=await Xt(p.ui_actions);n.onActionResults?.(h)}n.onComplete?.(p),I({event_type:"voice_turn_completed",stage:"http_response",status:"ok",request_id:li(c),duration_ms:U()-o,metadata:{transport:"http",action_count:p.ui_actions?.length||0}})}},ee=class{constructor(){this.ws=null,this.connected=!1,this.connecting=null,this.failed=!1,this.retries=0,this.audioQueue=Tt,this.callbacks=null,this.turnText="",this.receivedAudio=!1}async ensureConnected(e=[]){return this.canUseWebSocket()?this.isOpen()?!0:this.connecting?this.connecting:(this.connecting=this.openConnection(e),this.connecting):!1}canUseWebSocket(){return!this.failed&&l.useWebSocket&&"WebSocket"in window}isOpen(){return this.connected&&this.ws?.readyState===WebSocket.OPEN}openConnection(e=[]){return new Promise(n=>{let r=new WebSocket(ii(l.apiUrl,l.siteId)),o=!1;this.ws=r;let a=(c=null)=>{o||(o=!0,this.markConnectionFailed(n,c,r))},i=window.setTimeout(()=>{a()},Re);r.onopen=()=>{o||(o=!0,this.handleConnectionOpen(i,e,n))},r.onmessage=c=>{this.handleMessage(c).catch(p=>this.handleTransportError(p))},r.onerror=()=>{if(o){this.failActiveTurn(f.NETWORK);return}a(i)},r.onclose=()=>{if(this.connected=!1,o){this.failActiveTurn(f.NETWORK);return}a(i)}})}markConnectionOpen(){this.connected=!0,this.connecting=null,this.retries=0}handleConnectionOpen(e,n,r){window.clearTimeout(e),this.markConnectionOpen(),this.sendConfig(n),r(!0)}markConnectionFailed(e,n=null,r=null){n&&window.clearTimeout(n),this.connected=!1,this.connecting=null,this.retries+=1,this.retries>=ri&&(this.failed=!0),r&&r.readyState!==WebSocket.CLOSED&&r.close(),e(!1)}sendConfig(e=[]){this.sendJson({type:w.CONFIG,history:e||[],session_id:l.sessionId,page_context:er()})}sendJson(e){return!this.ws||this.ws.readyState!==WebSocket.OPEN?!1:(this.ws.send(JSON.stringify(e)),!0)}async sendAudio(e,n,r=[]){if(!await this.ensureConnected(r))return!1;this.callbacks=n,this.turnText="",this.receivedAudio=!1,this.sendConfig(r);let a=await si(e),i=this.beginTurn();return this.turnStartedAt=U(),I({event_type:"voice_turn_started",stage:"websocket_send",status:"started",metadata:{transport:"websocket",audio_type:e?.type||"unknown"}}),this.sendJson({type:w.AUDIO_CHUNK,data:a,mime_type:e?.type||""})&&this.sendJson({type:w.AUDIO_END,mime_type:e?.type||""})?(await i,!0):(this.settleTurn(),this.callbacks=null,!1)}beginTurn(){return this.settleTurn(),new Promise(e=>{let n=window.setTimeout(()=>{this.failActiveTurn(f.TIMEOUT)},Ce);this.activeTurn={resolve:e,timer:n}})}settleTurn(){let e=this.activeTurn;return this.activeTurn=null,e?(window.clearTimeout(e.timer),e.resolve(),!0):!1}failActiveTurn(e){if(!this.activeTurn)return;let n=this.callbacks;if(this.callbacks=null,n){let r=new T(e,{stage:"websocket"});n.onStatusChange?.(_.ERROR,r.customerMessage),n.onComplete?.({error:r.category}),I({event_type:"voice_turn_failed",stage:"websocket",severity:"error",status:"failed",message_code:r.code||r.category,duration_ms:U()-(this.turnStartedAt||U()),metadata:{transport:"websocket",category:r.category,http_status:r.status}})}this.settleTurn()}async handleMessage(e){let n=this.callbacks;if(!n)return;let r=this.parseMessage(e.data);if(!r){this.completeWithError(n,"Invalid WebSocket message");return}if(!this.handleIncrementalMessage(r,n)){if(r.type===w.DONE){await this.handleDoneMessage(r,n);return}r.type===w.ERROR&&this.completeWithError(n,r.message||"WebSocket error")}}parseMessage(e){try{let n=JSON.parse(e);return n&&typeof n=="object"?n:null}catch{return null}}handleIncrementalMessage(e,n){return e.type===w.TRANSCRIPT?(n.onUserMessage?.(e.text||""),!0):e.type===w.TEXT_CHUNK?(this.turnText+=e.text||"",n.onAssistantChunk?.(e.text||"",this.turnText),!0):e.type===w.AUDIO_CHUNK?(this.receivedAudio=!!e.audio_b64||this.receivedAudio,this.audioQueue.push(e.audio_b64),!0):!1}async handleDoneMessage(e,n){let r=e.response_text||this.turnText;n.onAssistantMessage?.(r,e.ui_actions||[],{streamed:!0}),n.onStatusChange?.(_.READY),!this.receivedAudio&&r?G(r):this.receivedAudio&&r&&this.audioQueue.speakInsteadOfBlocked(r);try{if(e.ui_actions&&e.ui_actions.length>0){let o=await Xt(e.ui_actions);n.onActionResults?.(o)}n.onComplete?.(e),I({event_type:"voice_turn_completed",stage:"websocket_done",status:"ok",duration_ms:U()-(this.turnStartedAt||U()),metadata:{transport:"websocket",action_count:e.ui_actions?.length||0}})}catch(o){this.handleTransportError(o)}finally{this.callbacks=null,this.settleTurn()}}completeWithError(e,n){e.onStatusChange?.(_.ERROR,tr(n)),e.onComplete?.({error:n});let r=ot(n);I({event_type:"voice_turn_failed",stage:"websocket_message",severity:"error",status:"failed",message_code:r.code||r.category,duration_ms:U()-(this.turnStartedAt||U()),metadata:{transport:"websocket",category:r.category,http_status:r.status}}),this.callbacks=null,this.settleTurn()}handleTransportError(e){console.error("AI Hub WebSocket transport failed",e);let n=this.callbacks;n&&this.completeWithError(n,String(e))}},ci=new te,ui=new ee;async function Zn(t,e,n,r=[]){try{if(l.useWebSocket&&await ui.sendAudio(t,n,r))return;await ci.sendAudio(t,n,r)}catch(o){console.error(o);let a=o instanceof T?o:ot(o);I({event_type:"voice_turn_failed",stage:a.stage||"transport",severity:"error",status:"failed",request_id:a.requestId,message_code:a.code||a.category,metadata:{transport:l.useWebSocket?"websocket_or_http":"http",category:a.category,http_status:a.status}}),n.onStatusChange?.(_.ERROR,tr(o)),n.onComplete?.({error:String(o)})}}function li(t){return t?.headers?.get?.("x-request-id")||t?.headers?.get?.("x-correlation-id")||""}function U(){return typeof performance<"u"?performance.now():Date.now()}function di(t,e=""){Tt.push(t,e)}function pi(t){let e=String(t?.type||"").toLowerCase();return e.includes("mp4")?"audio.mp4":e.includes("ogg")?"audio.ogg":e.includes("wav")?"audio.wav":Q.WEBM_FILENAME}async function fi(t){try{return await t.json()}catch{return null}}function tr(t){if(t instanceof T)return t.customerMessage;let e=String(t?.message||t||"").toLowerCase();return e.includes("quota")?"Quota reached":e.includes("transcription")||e.includes("speech")?"Voice unavailable":ot(t).customerMessage}function G(t){return t?rt(String(t).slice(0,700)):!1}function er(){let t=window[oi],e=window[ai];try{if(typeof t?.getContext=="function")return t.getContext();if(typeof e?.getContext=="function")return e.getContext()}catch(n){console.warn("[AI Hub Widget] Page context collection failed:",n)}return null}var mi=4,_i=40,hi=24,yi=80,gi=120;function rr(){let t=[];function e(n,r){let o=String(r||"").trim();o&&(t.push({role:n,content:o}),t.length>Se&&t.shift())}return{history:t,rememberUserMessage(n){e("user",n)},rememberAssistantMessage(n,r){e("assistant",bi(n,r))},rememberActionResults(n){let r=Ei(n);r&&e("assistant",r)}}}function bi(t,e){let n=Ti(e);return n.length?`${t} [PRODUCT_IDS: ${n.join(",")}]`:t}function Ti(t){let e=[];for(let n of t||[]){let r=n.params||{};nr(e,r[d.PRODUCT_IDS]),nr(e,[r[d.PRODUCT_ID]])}return e}function nr(t,e){for(let n of Array.isArray(e)?e:[])n&&!t.includes(n)&&t.push(n)}function Ei(t){let e=(Array.isArray(t)?t:[]).map(Ai).filter(Boolean).slice(0,mi);return e.length?`[BROWSER_ACTION_RESULTS: ${e.join(" | ")}]`:""}function Ai(t){if(!t||typeof t!="object"||!t.action)return"";let e=[Et(t.action,_i),`status=${Et(t.status,hi)||"unknown"}`],n=Ii(t.final_url);return n&&e.push(`final_path=${Et(n,gi)}`),t.reason&&e.push(`reason=${Et(t.reason,yi)}`),Si(e,t.evidence),e.join(" ")}function Si(t,e={}){e.rendered_product_count!==void 0&&t.push(`rendered_products=${Number(e.rendered_product_count||0)}`),e.rendered_entity_count!==void 0&&t.push(`rendered_records=${Number(e.rendered_entity_count||0)}`)}function Et(t,e){return String(t||"").replace(/\s+/g," ").trim().slice(0,e)}function Ii(t){try{let e=new URL(String(t||""),window.location.href);return`${e.pathname}${e.search}${e.hash}`}catch{return""}}var or=null;function oe(t){or||(ar(t),or=window.setInterval(()=>ar(t),xe))}async function ar({boot:t,shutdownWidget:e}){try{if(await Oi()){t();return}e()}catch{t()}}async function Oi(){let t=new URL(O.WIDGET_STATUS,l.apiUrl);t.searchParams.set("site_id",l.siteId);let e=await fetch(t.toString(),{cache:"no-store",headers:{Accept:"application/json"}});return e.ok?(await e.json()).enabled!==!1:!0}window.__mayabot_identifier="voice-orb";var ae=null,ie=null;function ir(){if(window.__mayabotBooted||document.getElementById("mayabot-widget"))return;window.__mayabotBooted=!0,le();let t=Te(),e=null,n=null,r=!1;function o(m=Ie){e&&window.clearTimeout(e),e=window.setTimeout(()=>{t.msgs.innerHTML="",t.chat.classList.remove("visible"),e=null},m)}function a(m,b=""){r=m===_.RECORDING,se(E(m)),t.status.className="",m===_.RECORDING?(e&&(window.clearTimeout(e),e=null),t.msgs.innerHTML="",t.btn.classList.add("recording"),t.chat.classList.add("visible"),t.status.innerText="Listening...",t.status.classList.add("listening")):m===_.PROCESSING?(t.btn.classList.remove("recording"),t.chat.classList.add("visible"),t.status.innerText="Analyzing...",t.status.classList.add("processing")):m===_.READY?(t.status.innerText="Ready",t.status.classList.add("ready")):m===_.ERROR&&(t.status.innerText=b||"Try again",t.status.classList.add("error"),t.btn.classList.remove("recording"))}let i=rr(),c=null,p="",h=!1;async function M(m){if(!h){h=!0,t.btn.disabled=!0,c=null,p="";try{await Zn(m,t,{onUserMessage:b=>{K(t,b,"user"),i.rememberUserMessage(b)},onAssistantChunk:(b,At)=>{p=At,c||(c=K(t,"","ai")),It(t,c,p)},onAssistantMessage:(b,At,ur={})=>{ur.streamed&&c?It(t,c,b):K(t,b,"ai"),i.rememberAssistantMessage(b,At),c=null,p=""},onActionResults:i.rememberActionResults,onStatusChange:a,onComplete:()=>o()},i.history)}finally{h=!1,t.btn.disabled=!1,c=null,p=""}}}let $=Ne(M,a);ae=$;function C(){return re()?(ne(),I({event_type:"voice_playback_stopped",stage:"orb_gesture",status:"cancelled"}),a(_.READY),!0):!1}function g(){if(h){C();return}if(r){$.toggle();return}C()||$.toggle()}let B={idle:{label:"Maya voice assistant. Click, press Enter, or press Space to talk.",title:"Click to talk"},recording:{label:"Maya is listening. Click once to send, or press Escape to cancel.",title:"Click once to send - Escape to cancel"},processing:{label:"Maya is working on your request. Please wait.",title:"Request in progress"},speaking:{label:"Maya is speaking. Click to stop, or press Escape to stop.",title:"Click to stop Maya"}};function E(m){return m===_.RECORDING?"recording":m===_.PROCESSING?"processing":re()?"speaking":"idle"}function se(m){let b=B[m]||B.idle;t.btn.setAttribute("aria-label",b.label),t.btn.setAttribute("title",b.title)}se("idle"),t.btn.addEventListener("click",m=>{if(h){C();return}C()||m.detail>1||g()});let ce=m=>{if(m.key==="Escape"){if(r){$.cancel(),I({event_type:"voice_recording_cancelled",stage:"keyboard_escape",status:"cancelled"}),a(_.READY);return}C()}};document.addEventListener("keydown",ce);let ue=m=>{t.btn.contains(m.target)||bt()};document.addEventListener("pointerdown",ue,{capture:!0}),ie=()=>{document.removeEventListener("keydown",ce),document.removeEventListener("pointerdown",ue,{capture:!0}),e&&window.clearTimeout(e),e=null,n&&window.clearTimeout(n),n=null,ie=null},wi()&&(xi(),n=window.setTimeout(()=>{if(i.history.length>0)return;let m=`Welcome to ${l.brandName}. How can I help you today?`;K(t,m,"ai"),a(_.READY),o(we),rt(m)},Oe))}function sr(){ae?.cancel(),ae=null,ie?.(),ne(),window.__mayabotBooted=!1,document.getElementById("mayabot-widget")?.remove(),document.getElementById("mayabot-product-panel")?.remove()}function wi(){if(!l.autoGreet||!Ri())return!1;try{return window.sessionStorage.getItem(cr())!=="1"}catch{return!window.__mayabotAutoGreeted}}function xi(){window.__mayabotAutoGreeted=!0;try{window.sessionStorage.setItem(cr(),"1")}catch{}}function cr(){return`mayabot:auto-greeted:${l.siteId}`}function Ri(){let t=window.location.pathname.replace(/\/+$/,"")||"/";return t==="/"||t.endsWith("/index.html")}document.readyState==="loading"?document.addEventListener("DOMContentLoaded",()=>oe({boot:ir,shutdownWidget:sr})):oe({boot:ir,shutdownWidget:sr});})();
