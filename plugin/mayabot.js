(()=>{function Tn(){let t="#5d5fef",e=document.querySelector('meta[name="theme-color"]');if(e&&e.content)t=e.content;else{let f=document.querySelector('button[class*="primary"], .btn-primary, [data-primary]');if(f){let E=window.getComputedStyle(f).backgroundColor;E&&E!=="rgba(0, 0, 0, 0)"&&E!=="transparent"&&(t=E)}}let n=window.matchMedia&&window.matchMedia("(prefers-color-scheme: dark)").matches,r=n?"rgba(24, 24, 27, 0.75)":"rgba(255, 255, 255, 0.85)",o=n?"rgba(255, 255, 255, 0.1)":"rgba(0, 0, 0, 0.08)",i=n?"#f3f4f6":"#111827",a=n?"rgba(255, 255, 255, 0.1)":"rgba(0, 0, 0, 0.05)",s=n?"rgba(0, 0, 0, 0.25)":"#ffffff",u=document.createElement("style");u.textContent=`
    :root {
      --mayabot-primary: ${t};
      --mayabot-surface: ${r};
      --mayabot-border: ${o};
      --mayabot-text: ${i};
      --mayabot-user-bg: ${a};
      --mayabot-bot-bg: ${s};
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
      /* Idle: a red microphone on a white orb, no ripple. The listening and
         speaking states below change the treatment so each state is distinct. */
      border: 1px solid rgba(0, 0, 0, 0.08);
      background: #ffffff;
      box-shadow: 0 12px 32px -8px rgba(0,0,0,0.25), 0 4px 12px rgba(0,0,0,0.12);
      color: #ef4444;
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
      /* No ripple at idle. The ring only animates while listening. */
      opacity: 0;
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

    /* Listening: active colour treatment with a visible ripple. */
    #mayabot-btn.recording {
      background: var(--mayabot-primary);
      color: #ffffff;
      box-shadow: 0 0 0 6px rgba(37, 99, 235, 0.18), 0 8px 24px rgba(0,0,0,0.18);
    }

    #mayabot-btn.recording .mayabot-btn-ring {
      opacity: 0.5;
      animation: mayabotRipple 1.4s ease-out infinite;
    }

    /* Speaking: distinct from idle and listening, and clearly stoppable. */
    #mayabot-btn.speaking {
      background: var(--mayabot-primary);
      color: #ffffff;
      box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.14), 0 8px 24px rgba(0,0,0,0.18);
    }

    @keyframes mayabotRipple {
      0% { inset: -6px; opacity: 0.5; }
      100% { inset: -16px; opacity: 0; }
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
  `,document.head.appendChild(u)}var me="site_1",ni="__AI_";var ri="aihub:auto-site-id:",oi=["data-aihub-scope","data-site-scope"],ii=["data-site-id","data-aihub-site-id"];function w(t){return String(t||"").trim()}function bt(t){return w(t).replace(/\/+$/,"")}function Sn(t,e,n,r=me){return ai(t,e,n)||si()||w(r)||me}function ai(t,e,n){for(let i of ii){let a=w(t?.getAttribute(i));if(a)return a}let r=w(e?.searchParams.get("site"))||w(e?.searchParams.get("site_id"))||w(e?.searchParams.get("shop"));if(r)return r;let o=w(n);return o&&!o.startsWith(ni)?o:""}function si(){let t=ci(),e=`${ri}${t}`,n=_i(e);if(n){let s=mi(n);return s!==n&&En(e,s),s}let r=w(window.location.host||window.location.hostname||"site"),o=wn(),i=fi(`${r}${o?`_${o.replace(/\//g,"_")}`:""}`),a=In(`auto_${i}_${hi(t)}`);return En(e,a),a}function ci(){return`${window.location.origin}${wn()}`}function wn(){return ui()}function ui(){for(let e of oi){let n=w(li()?.getAttribute(e));if(n)return An(n)}let t=document.querySelector("meta[name='aihub-site-scope']")?.getAttribute("content");return An(t)}function li(){return document.currentScript}function An(t){let e=w(t);if(!e||e==="/")return"";try{let r=new URL(e,window.location.href);if(r.origin===window.location.origin){let[o]=di(r.pathname);return o?`/${o}`:""}}catch{}let[n]=e.replace(/^\/+/,"").split("/");return n?`/${n}`:""}function di(t=window.location.pathname){return w(t).split("/").map(e=>pi(e).trim()).filter(Boolean)}function pi(t){try{return decodeURIComponent(t)}catch{return String(t||"")}}function fi(t){return w(t).toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/^_+|_+$/g,"")||"site"}function In(t){return w(t).slice(0,80).replace(/_+$/g,"")||me}function mi(t){let e=w(t);return e.startsWith("auto_")?In(e.toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/^_+|_+$/g,"")):e}function hi(t){let e=2166136261,n=w(t);for(let r=0;r<n.length;r+=1)e^=n.charCodeAt(r),e=Math.imul(e,16777619);return(e>>>0).toString(36)}function _i(t){try{return w(window.localStorage.getItem(t))}catch{return""}}function En(t,e){try{window.localStorage.setItem(t,e)}catch{}}var z=document.currentScript,On="__AI_PUBLIC_API_URL__",yi="__AI_DEFAULT_SITE_ID__",Cn="mayabot:session:",gi="Maya",bi="AI Salesperson",Ti="female";function J(t){return String(t||"").trim()}function Ai(){let t=J(z?.getAttribute("src"));if(!t)return null;try{return new URL(t,window.location.href)}catch{return null}}function Ei(t){let e=J(z?.getAttribute("data-api-url"));if(e)return bt(e);if(!On.startsWith("__AI_"))return bt(On);if(t?.origin){let n=t.pathname.replace(/\/mayabot(?:-widget)?\.js$/,"");return bt(`${t.origin}${n}`)}return bt(window.location.origin)}function Si(t){let e=`${Cn}${t}`;try{let n=window.sessionStorage.getItem(e);if(n)return n;let r=_e(t);return window.sessionStorage.setItem(e,r),r}catch{return _e(t)}}function wi(t){let e=_e(t);try{window.sessionStorage.setItem(`${Cn}${t}`,e)}catch{}return e}function _e(t){let e=window.crypto?.randomUUID?.()||`${Date.now()}-${Math.random().toString(16).slice(2)}`;return`${t}-${e}`.slice(0,120)}var Rn=Ai(),he=Sn(z,Rn,yi),d={siteId:he,get sessionId(){return Si(he)},rotateSessionId(){return wi(he)},apiUrl:Ei(Rn),useWebSocket:J(z?.getAttribute("data-use-websocket")).toLowerCase()==="true",autoGreet:J(z?.getAttribute("data-auto-greet")).toLowerCase()!=="false",brandName:J(z?.getAttribute("data-brand"))||gi,assistantTitle:J(z?.getAttribute("data-assistant-title"))||bi,speechVoiceName:J(z?.getAttribute("data-speech-voice")),speechVoicePreference:J(z?.getAttribute("data-speech-voice-preference"))||Ti};function xn(){let t=document.createElement("div");return t.id="mayabot-widget",t.innerHTML=`
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
  `,document.body.appendChild(t),t.querySelector(".mayabot-kicker").textContent=d.brandName,t.querySelector(".mayabot-title").textContent=d.assistantTitle,{btn:document.getElementById("mayabot-btn"),chat:document.getElementById("mayabot-chat"),msgs:document.getElementById("mayabot-msgs"),status:document.getElementById("mayabot-status")}}function Tt(t,e,n){t.chat.classList.add("visible");let r=document.createElement("div");return r.className=`mayabot-msg ${n}`,r.innerText=e,t.msgs.appendChild(r),t.msgs.scrollTop=t.msgs.scrollHeight,r}function ye(t,e,n){e&&(e.innerText=n,t.msgs.scrollTop=t.msgs.scrollHeight)}var c=Object.freeze({ADD_TO_CART:"ADD_TO_CART",BOOK_APPOINTMENT_REQUEST:"BOOK_APPOINTMENT_REQUEST",BUILD_ITINERARY:"BUILD_ITINERARY",BUILD_LEARNING_PATH:"BUILD_LEARNING_PATH",CAPTURE_LEAD:"CAPTURE_LEAD",CAPTURE_PATIENT_LEAD:"CAPTURE_PATIENT_LEAD",CHECKOUT:"CHECKOUT",CHECKOUT_HANDOFF:"CHECKOUT_HANDOFF",CHECK_APPOINTMENT_AVAILABILITY:"CHECK_APPOINTMENT_AVAILABILITY",CHECK_AVAILABILITY:"CHECK_AVAILABILITY",CHECK_DELIVERY_AVAILABILITY:"CHECK_DELIVERY_AVAILABILITY",CHECK_ELIGIBILITY_SOFT:"CHECK_ELIGIBILITY_SOFT",CHECK_PREREQUISITES:"CHECK_PREREQUISITES",CLEAR_CART:"CLEAR_CART",CLEAR_FILTERS:"CLEAR_FILTERS",CLEAR_HISTORY:"CLEAR_HISTORY",COMPARE_ENTITIES:"COMPARE_ENTITIES",CONTACT_AGENT:"CONTACT_AGENT",FILTER_ENTITIES:"FILTER_ENTITIES",FILTER_PRODUCTS:"FILTER_PRODUCTS",HANDOFF_TO_ADVISOR:"HANDOFF_TO_ADVISOR",HANDOFF_TO_AGENT:"HANDOFF_TO_AGENT",HANDOFF_TO_CLINIC:"HANDOFF_TO_CLINIC",HANDOFF_TO_HUMAN:"HANDOFF_TO_HUMAN",HANDOFF_TO_LAWYER:"HANDOFF_TO_LAWYER",HANDOFF_TO_LICENSED_AGENT:"HANDOFF_TO_LICENSED_AGENT",HANDOFF_TO_RECRUITER:"HANDOFF_TO_RECRUITER",JOIN_WAITLIST:"JOIN_WAITLIST",MATCH_JOBS:"MATCH_JOBS",NAVIGATE_TO:"NAVIGATE_TO",OPEN_CLAIM_FLOW:"OPEN_CLAIM_FLOW",OPEN_CONTACT:"OPEN_CONTACT",OPEN_DISCLOSURE:"OPEN_DISCLOSURE",OPEN_ENTITY_DETAIL:"OPEN_ENTITY_DETAIL",OPEN_LOCATION:"OPEN_LOCATION",OPEN_MAP:"OPEN_MAP",OPEN_POLICY:"OPEN_POLICY",OPEN_PROJECTS:"OPEN_PROJECTS",OPEN_RENEWAL_FLOW:"OPEN_RENEWAL_FLOW",OPEN_SERVICES:"OPEN_SERVICES",OPEN_SYLLABUS:"OPEN_SYLLABUS",OPEN_TELECONSULT:"OPEN_TELECONSULT",REMOVE_FROM_CART:"REMOVE_FROM_CART",REQUEST_APPOINTMENT:"REQUEST_APPOINTMENT",REQUEST_CALLBACK:"REQUEST_CALLBACK",REQUEST_CONSULTATION:"REQUEST_CONSULTATION",REQUEST_COUNSELOR_CALLBACK:"REQUEST_COUNSELOR_CALLBACK",REQUEST_ESTIMATE:"REQUEST_ESTIMATE",REQUEST_SITE_VISIT:"REQUEST_SITE_VISIT",REQUEST_TEST_DRIVE:"REQUEST_TEST_DRIVE",REQUEST_VIEWING:"REQUEST_VIEWING",RUN_AFFORDABILITY_CALCULATOR:"RUN_AFFORDABILITY_CALCULATOR",RUN_CALCULATOR:"RUN_CALCULATOR",RUN_DOM_SEQUENCE:"RUN_DOM_SEQUENCE",SAVE_SEARCH:"SAVE_SEARCH",SCHEDULE_ORDER:"SCHEDULE_ORDER",SEARCH_AVAILABILITY:"SEARCH_AVAILABILITY",SET_LOCATION:"SET_LOCATION",SHOW_COMPARISON:"SHOW_COMPARISON",SHOW_EMERGENCY_NOTICE:"SHOW_EMERGENCY_NOTICE",SHOW_ENTITIES:"SHOW_ENTITIES",SHOW_PRODUCT_DETAIL:"SHOW_PRODUCT_DETAIL",SHOW_PRODUCTS:"SHOW_PRODUCTS",SORT_ENTITIES:"SORT_ENTITIES",SORT_PRODUCTS:"SORT_PRODUCTS",START_APPLICATION:"START_APPLICATION",START_BOOKING:"START_BOOKING",START_ENROLLMENT:"START_ENROLLMENT",START_INTAKE:"START_INTAKE",START_QUOTE:"START_QUOTE",START_TICKET_PURCHASE:"START_TICKET_PURCHASE",UPDATE_CART_QUANTITY:"UPDATE_CART_QUANTITY",UPDATE_PREFERENCES:"UPDATE_PREFERENCES"}),p=Object.freeze({ENTITY_ID:"entity_id",ENTITY_IDS:"entity_ids",MESSAGE:"message",PAGE:"page",PRODUCT_ID:"product_id",PRODUCT_IDS:"product_ids",PRODUCT_NAME:"product_name",QUANTITY:"quantity",REASON:"reason",SEARCH_QUERY:"search_query",URL:"url"}),Fu=Object.freeze({BLOCKED:"blocked",EXECUTING:"executing",FAILED:"failed",REQUESTED:"requested",SKIPPED:"skipped",SUCCEEDED:"succeeded",UNKNOWN:"unknown"}),k=Object.freeze({KNOWLEDGE_BY_IDS:"/v1/knowledge/by-ids",PRODUCTS_BY_IDS:"/v1/products/by-ids",SHOP:"/v1/shop",SHOP_WS:"/v1/ws/shop",WIDGET_STATUS:"/v1/widget/status"}),M=Object.freeze({AUDIO_CHUNK:"audio_chunk",AUDIO_END:"audio_end",CONFIG:"config",DONE:"done",ERROR:"error",TEXT_CHUNK:"text_chunk",TRANSCRIPT:"transcript"});var Nn=new Set(["cart","/cart"]),G="Recommended products",Z="Relevant options",At=Object.freeze({DATA_WAV_PREFIX:"data:audio/wav;base64,",WEBM_FILENAME:"audio.webm",WEBM_MIME_TYPE:"audio/webm"}),vn=Object.freeze({POST:"POST"}),y=Object.freeze({ERROR:"error",PROCESSING:"processing",READY:"ready",RECORDING:"recording"});var Pn=2400,Ln=900,Dn=4200,ge=1,lt=180,Un=3e3,Et=Object.freeze({MAYABOT_ACTION:"mayabot:action"}),kn=2500,Mn=45e3;var Ii=["audio/webm;codecs=opus","audio/webm","audio/ogg;codecs=opus","audio/ogg","audio/mp4"],Oi=250,Ci=128;function Hn(t,e){let n=null,r=null,o=[],i=!1,a=!1,s=!1;async function u(){if(!(a||i)){a=!0;try{let b=await navigator.mediaDevices.getUserMedia({audio:!0});r=b,s=!1;let R=Ri();n=new MediaRecorder(b,R?{mimeType:R}:void 0),o=[],n.ondataavailable=I=>{I.data.size>0&&o.push(I.data)},n.onstop=async()=>{let I=new Blob(o,{type:n.mimeType||R||At.WEBM_MIME_TYPE});if(C(),s){s=!1;return}if(I.size<Ci){console.warn("Microphone recording was empty or too short",{size:I.size}),e(y.READY);return}await t(I)},n.onerror=I=>{console.error("Microphone recording failed",I.error||I),i=!1,a=!1,C(),e(y.ERROR,"Recording failed")},n.start(Oi),i=!0,e(y.RECORDING)}catch(b){console.error("Microphone access denied",b),e(y.ERROR,"Mic unavailable")}finally{a=!1}}}function f({discard:b=!1}={}){if(s=b,n&&n.state!=="inactive"){try{n.requestData()}catch{}n.stop(),i=!1,b||e(y.PROCESSING);return}i=!1,C(),b||e(y.PROCESSING)}function E(){a||(i?f():u())}function v(){f({discard:!0})}function C(){r&&(r.getTracks().forEach(b=>b.stop()),r=null)}return{toggle:E,cancel:v}}function Ri(){return!("MediaRecorder"in window)||typeof MediaRecorder.isTypeSupported!="function"?"":Ii.find(t=>MediaRecorder.isTypeSupported(t))||""}var Fn="shopify",Bn="woocommerce",xi="custom";function Ft(t){let e=String(t||"").trim();return/^\d+$/.test(e)?e:""}function Bt(t,e=1){let n=Number(t?.[p.QUANTITY]);return Number.isFinite(n)&&n>0?Math.floor(n):e}async function ot(t,e){return(await fetch(new URL(t,window.location.origin),{method:"POST",headers:{Accept:"application/json","Content-Type":"application/json"},body:JSON.stringify(e),credentials:"same-origin"})).ok}function Ni(){return vi()?Fn:Pi()?Bn:xi}async function Yn(t){let e=Ni();return e===Fn?Li(t):e===Bn?Di(t):!1}function vi(){return!!(window.Shopify||document.querySelector('meta[name="shopify-checkout-api-token"]')||document.querySelector('script[src*="cdn.shopify.com"]'))}function Pi(){return!!(document.body?.classList?.contains("woocommerce")||window.wc_add_to_cart_params||document.querySelector('link[href*="woocommerce"], script[src*="woocommerce"]'))}async function Li(t){let e=t.parameters||{};if(t.action===c.ADD_TO_CART){let n=Ft(e.variant_id||e.cart_id||e[p.PRODUCT_ID]);return n?ot("/cart/add.js",{items:[{id:n,quantity:Bt(e)}]}):!1}if(t.action===c.REMOVE_FROM_CART){let n=Ft(e.cart_id||e.variant_id||e[p.PRODUCT_ID]);return n?ot("/cart/change.js",{id:n,quantity:0}):!1}if(t.action===c.UPDATE_CART_QUANTITY){let n=Ft(e.cart_id||e.variant_id||e[p.PRODUCT_ID]);return n?ot("/cart/change.js",{id:n,quantity:Bt(e,0)}):!1}return t.action===c.CLEAR_CART?ot("/cart/clear.js",{}):t.action===c.CHECKOUT?Yt("/checkout"):$n(t)?Yt("/cart"):!1}async function Di(t){let e=t.parameters||{};if(t.action===c.ADD_TO_CART){let n=Ft(e.variant_id||e.cart_id||e[p.PRODUCT_ID]);return n?ot("/wp-json/wc/store/cart/add-item",{id:Number(n),quantity:Bt(e)}):!1}if(t.action===c.REMOVE_FROM_CART){let n=String(e.cart_key||e.key||"").trim();return n?ot("/wp-json/wc/store/cart/remove-item",{key:n}):!1}if(t.action===c.UPDATE_CART_QUANTITY){let n=String(e.cart_key||e.key||"").trim();return n?ot("/wp-json/wc/store/cart/update-item",{key:n,quantity:Bt(e,0)}):!1}return t.action===c.CHECKOUT?Yt("/checkout"):$n(t)?Yt("/cart"):!1}function $n(t){return t.action===c.NAVIGATE_TO&&Nn.has(t.parameters?.[p.PAGE])}function Yt(t){return window.location.href=t,!0}var Ui="/v1/widget/action-event";function L(t){return String(t||"").trim()}function ki(t,e){return new URL(t,e).toString()}function Mi(t){return!t||typeof t!="object"?[]:Object.keys(t).map(e=>L(e)).filter(Boolean).slice(0,20)}function Hi(t){if(!t||typeof t!="object")return{};let e={};for(let[n,r]of Object.entries(t).slice(0,20)){let o=L(n).slice(0,80);o&&(typeof r=="boolean"||r===null?e[o]=r:typeof r=="number"?e[o]=Number.isFinite(r)?r:0:e[o]=L(r).slice(0,240))}return e}async function $t(t,e,n,r){if(!t||!e||!n?.action)return;let o=JSON.stringify({site_id:e,origin:window.location.origin,url:window.location.href,occurred_at:new Date().toISOString(),request_id:L(n.request_id||n.action_request_id),turn_id:L(n.turn_id),sequence:Number(n.sequence||0),action:L(n.action).toUpperCase(),status:L(r?.status)||"unknown",stage:L(r?.stage),reason:L(r?.reason),duration_ms:Number(r?.duration_ms||0),param_keys:Mi(n.parameters||n.params),requested_url:L(r?.requested_url),final_url:L(r?.final_url||window.location.href),evidence:Hi(r?.evidence)}),i=ki(Ui,t);if(!Fi(i,o))try{await fetch(i,{method:"POST",headers:{Accept:"application/json","Content-Type":"application/json"},body:o,keepalive:!0})}catch(a){console.warn("[AIHubAdapter] Action execution report failed.",a)}}function Fi(t,e){if(typeof navigator>"u"||typeof navigator.sendBeacon!="function"||typeof Blob!="function")return!1;try{return navigator.sendBeacon(t,new Blob([e],{type:"application/json"}))}catch{return!1}}function x(t){if(!t||typeof t!="string")return[];let e=[];for(let n of Bi()){try{e.push(...Array.from(n.querySelectorAll(t)))}catch{return[]}if(e.length>=600)return e.slice(0,600)}return qi(e)}function Bi(){let t=[],e=new Set,n=[document];for(;n.length&&t.length<60;){let r=n.shift();!r||e.has(r)||(e.add(r),t.push(r),n.push(...Yi(r)))}return t}function Yi(t){let e=[];for(let n of $i(t)){n.shadowRoot&&e.push(n.shadowRoot);let r=ji(n);r&&e.push(r)}return e}function $i(t){try{return Array.from(t.querySelectorAll("*"))}catch{return[]}}function ji(t){if(String(t?.tagName||"").toLowerCase()!=="iframe")return null;try{let e=t.contentDocument;return e?.documentElement?e:null}catch{return null}}function qi(t){return Array.from(new Set(t))}var Ku=Object.freeze([l("stripe",["stripe","stripe.com","checkout.stripe.com","js.stripe.com"]),l("paypal",["paypal","paypal.com","paypalobjects.com"]),l("razorpay",["razorpay","checkout.razorpay.com"]),l("paytm",["paytm","securegw.paytm.in"]),l("cashfree",["cashfree","cashfree.com"]),l("checkout.com",["checkout.com","cko-session-id"]),l("adyen",["adyen","checkoutshopper"]),l("square",["squareup","squarecdn","square.site"]),l("braintree",["braintree","braintreegateway"]),l("mollie",["mollie","mollie.com"]),l("klarna",["klarna","klarna.com"]),l("afterpay",["afterpay","afterpay.com","clearpay"]),l("payu",["payu","payu.in","payu.com"]),l("paystack",["paystack","paystack.co"]),l("phonepe",["phonepe","phonepe.com"]),l("billdesk",["billdesk","billdesk.com"]),l("authorize.net",["authorize.net","accept.authorize.net"])]),jn=Object.freeze([l("calendly",["calendly","calendly.com"]),l("acuity",["acuityscheduling","squarespace scheduling"]),l("booksy",["booksy","booksy.com"]),l("zocdoc",["zocdoc","zocdoc.com"]),l("appointlet",["appointlet","appointlet.com"]),l("setmore",["setmore","setmore.com"]),l("cal.com",["cal.com","calcom"]),l("google_calendar",["calendar.google.com","google calendar"]),l("microsoft_bookings",["microsoft bookings","outlook.office365.com/book"]),l("simplybook",["simplybook","simplybook.me"]),l("tidycal",["tidycal","tidycal.com"]),l("savvycal",["savvycal","savvycal.com"]),l("fresha",["fresha","fresha.com"])]),qn=Object.freeze([l("google_maps",["google.com/maps","maps.googleapis","maps.google"]),l("mapbox",["mapbox","mapbox.com"]),l("openstreetmap",["openstreetmap","osm.org"]),l("leaflet",["leaflet","leafletjs"]),l("here_maps",["here.com","hereapi","wego.here.com"]),l("bing_maps",["bing.com/maps","virtualearth"]),l("mappls",["mappls","mapmyindia"])]),Vn=Object.freeze([l("whatsapp",["wa.me","api.whatsapp.com","web.whatsapp.com"]),l("telegram",["t.me/","telegram.me"]),l("messenger",["m.me/","messenger.com/t"]),l("zendesk",["zendesk.com","zdassets.com/hc"]),l("intercom",["intercom.help","intercom.com"]),l("freshchat",["freshchat.com"])]),Qu=Object.freeze([l("recaptcha",["recaptcha","g-recaptcha","google.com/recaptcha"]),l("hcaptcha",["hcaptcha","h-captcha"]),l("turnstile",["turnstile","challenges.cloudflare.com"]),l("cloudflare_challenge",["cf-chl","cloudflare challenge"])]);function l(t,e){return{name:t,tokens:e}}function be(t,e,n=10){let r=Te(t);return e.filter(o=>o.tokens.some(i=>r.includes(i))).map(o=>o.name).slice(0,n)}function Te(t){return String(t||"").replace(/\s+/g," ").trim().toLowerCase()}var zn="a[href], iframe[src]",Vi="a[href]",Wn=new Set(["http:","https:"]),jt=new Set(["mailto:","tel:"]),zi=Object.freeze([p.URL,"href","link","target_url","provider_url","booking_url","appointment_url","calendar_url","map_url","location_url","contact_url"]),Kn=new Set([c.OPEN_MAP,c.OPEN_LOCATION,c.SET_LOCATION]),Qn=new Set([c.CHECK_APPOINTMENT_AVAILABILITY,c.REQUEST_APPOINTMENT,c.BOOK_APPOINTMENT_REQUEST,c.REQUEST_CONSULTATION,c.REQUEST_SITE_VISIT,c.START_BOOKING]),Xn=new Set([c.OPEN_CONTACT,c.CONTACT_AGENT,c.REQUEST_CALLBACK,c.REQUEST_COUNSELOR_CALLBACK,c.HANDOFF_TO_ADVISOR,c.HANDOFF_TO_AGENT,c.HANDOFF_TO_CLINIC,c.HANDOFF_TO_HUMAN,c.HANDOFF_TO_LAWYER,c.HANDOFF_TO_LICENSED_AGENT,c.HANDOFF_TO_RECRUITER]);function Jn(t){let e=er(t);return Kn.has(e)||Qn.has(e)||Xn.has(e)}async function Zn(t){let e=er(t);return Kn.has(e)?Ae(t,qn,zn,Ee):Qn.has(e)?Ae(t,jn,zn,Ee):Xn.has(e)?Ae(t,Vn,Vi,Qi):!1}function Ae(t,e,n,r){let o=Gi(t?.parameters||t?.params||{},e,r);if(o)return Gn(o);let i=Wi(n,e,r);return i?Gn(i):!1}function Gi(t,e,n){for(let r of zi){let o=tr(t?.[r]);if(o&&n(o,e))return o}return null}function Wi(t,e,n){for(let r of x(t)){let o=Ki(r);if(!(!o||!n(o,e))&&Xi(o,r,e))return o}return null}function Ki(t){return tr(t?.getAttribute?.("href")||t?.getAttribute?.("src"))}function Ee(t,e){return Wn.has(t.protocol)&&be(t.href,e).length>0}function Qi(t,e){return jt.has(t.protocol)?!0:Ee(t,e)}function Xi(t,e,n){if(jt.has(t.protocol))return!0;let r=[t.href,e?.textContent||"",e?.getAttribute?.("aria-label")||"",e?.getAttribute?.("title")||""].join(" ");return be(Te(r),n).length>0}function Gn(t){if(jt.has(t.protocol)||t.origin===window.location.origin)return window.location.href=t.href,!0;let e=window.open(t.href,"_blank","noopener,noreferrer");return e?(e.opener=null,!0):(window.location.href=t.href,!0)}function tr(t){let e=String(t||"").trim();if(!e||e.startsWith("#"))return null;try{let n=new URL(e,window.location.href);return Wn.has(n.protocol)||jt.has(n.protocol)?n:null}catch{return null}}function er(t){return String(t?.action||"").trim().toUpperCase()}var Ji=Object.freeze(["title","name"]),Zi=Object.freeze(["summary","description","body"]),ta=Object.freeze(["image_url","imageUrl","image","thumbnail"]),ea=Object.freeze(["url","href","permalink","source_url"]),na="knowledge_item",ra=30;function H(t){return t==null||typeof t=="object"?"":String(t||"").trim()}function oa(t){let e=new Set;return(Array.isArray(t)?t:[]).map(H).filter(Boolean).filter(n=>e.has(n)||e.size>=ra?!1:(e.add(n),!0))}function qt(t,e){for(let n of e){let r=H(t?.[n]);if(r)return r}return""}function St(t){return t&&typeof t=="object"&&!Array.isArray(t)?t:{}}function ia(t){let e=aa([t?.price,t?.amount,t?.premium,t?.premium_min,t?.monthly_premium,t?.annual_premium,t?.min_price,t?.starting_price]),n=H(t?.currency||"INR");return!Number.isFinite(e)||e<=0?"":`${n} ${e.toLocaleString()}`}function aa(t){for(let e of t){let n=Number(String(e??"").replace(/,/g,""));if(Number.isFinite(n)&&n>0)return n}return 0}function sa(t){return!t||typeof t!="object"?"":t.in_stock===!0?"Available":t.in_stock===!1?"Unavailable":H(t.status||t.availability||"")}function ca(t){let e=H(t);if(!e)return"";try{let n=new URL(e,window.location.origin);return/^https?:$/i.test(n.protocol)?n.origin===window.location.origin?`${n.pathname}${n.search}${n.hash}`:n.toString():""}catch{return""}}function ua(t){if(!t)return null;let e=H(t.id);if(!e)return null;let n=St(t.pricing),r=St(t.availability);return{id:e,externalId:H(t.external_id),entityType:H(t.entity_type||t.category_name)||na,title:qt(t,Ji)||e,subtitle:H(t.subtitle||t.category_name||t.entity_type),summary:qt(t,Zi),body:H(t.body),url:ca(qt(t,ea)),imageUrl:qt(t,ta),attributes:St(t.attributes),pricing:n,availability:r,location:St(t.location),contact:St(t.contact),displayPrice:ia(n),displayAvailability:sa(r)}}async function Se(t){let e=oa(t);if(!e.length)return[];let n=new URL(k.KNOWLEDGE_BY_IDS,d.apiUrl);n.searchParams.set("site_id",d.siteId),n.searchParams.set("ids",e.join(","));let r=await fetch(n.toString(),{headers:{Accept:"application/json"}});if(!r.ok)throw new Error("Failed to fetch entities from AI Hub API");let o=(await r.json()).map(ua).filter(Boolean),i=new Map(o.map(a=>[String(a.id),a]));return e.map(a=>i.get(a)).filter(Boolean)}async function nr(t){let[e]=await Se([t]);return e?.url||""}function rr(){if(document.getElementById("mayabot-entity-overlay-styles"))return;let t=document.createElement("style");t.id="mayabot-entity-overlay-styles",t.textContent=`
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
  `,document.head.appendChild(t)}var la=2,or=Number.POSITIVE_INFINITY,Vt=Number.NEGATIVE_INFINITY,ir=12,Ie=[],Oe=Z;function W(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}function ur(t){return String(t||"item").replace(/[_-]+/g," ").trim().split(/\s+/).slice(0,la).join(" ")}function da(){rr();let t=document.getElementById("mayabot-entity-panel");return t||(t=document.createElement("div"),t.id="mayabot-entity-panel",t.setAttribute("aria-live","polite"),t.innerHTML=`
    <div class="mayabot-entity-header">
      <h2 class="mayabot-entity-title">${Z}</h2>
      <button class="mayabot-entity-close" type="button" aria-label="Close recommendations">&times;</button>
    </div>
    <div class="mayabot-entity-grid"></div>
  `,t.querySelector(".mayabot-entity-close").addEventListener("click",()=>{t.classList.remove("active")}),document.body.appendChild(t),t)}function pa(t){return t<=1?"count-1":t===2?"count-2":t===3?"count-3":"count-many"}function fa(t){return t<=1?1:t===2?2:3}function we(t,e,n=""){let r=(Array.isArray(e)?e:[]).map(s=>String(s?.id??"").trim()).filter(Boolean),o=r.length,i=t.length,a=o>0?"succeeded":"failed";return{status:a,stage:"entity_overlay",reason:n||(a==="succeeded"?"":"no_matching_entities_rendered"),evidence:{requested_entity_count:i,rendered_entity_count:o,missing_entity_count:Math.max(i-o,0),requested_entity_ids:t.slice(0,ir).join(","),rendered_entity_ids:r.slice(0,ir).join(",")}}}function ma(t){return[t.displayPrice,t.displayAvailability,t.location?.city,t.attributes?.category].map(e=>String(e||"").trim()).filter(Boolean).slice(0,3)}function ha(t){return t.imageUrl?`
      <div class="mayabot-entity-media">
        <img src="${W(t.imageUrl)}" alt="${W(t.title)}">
      </div>
    `:`
    <div class="mayabot-entity-media">
      <div class="mayabot-entity-badge">${W(ur(t.entityType))}</div>
    </div>
  `}function _a(t){let e=ma(t);return e.length?`
    <div class="mayabot-entity-facts">
      ${e.map(n=>`<span class="mayabot-entity-fact">${W(n)}</span>`).join("")}
    </div>
  `:""}function ya(t){return t.url?`
    <div class="mayabot-entity-actions">
      <button type="button" data-view-entity="${W(t.id)}">Open</button>
    </div>
  `:""}function Gt(t,e){let n=da(),r=n.querySelector(".mayabot-entity-grid"),o=n.querySelector(".mayabot-entity-title"),i=t.length;if(Ie=Array.isArray(t)?[...t]:[],Oe=e||Z,n.classList.remove("count-1","count-2","count-3","count-many"),n.classList.add(pa(i)),n.style.setProperty("--mayabot-entity-card-count",String(fa(i))),o.textContent=Oe,!i){r.innerHTML='<p class="mayabot-entity-empty">No matching records are currently available.</p>',n.classList.add("active"),ar();return}r.innerHTML=t.map(a=>`
        <article class="mayabot-entity-card" data-entity-id="${W(a.id)}">
          ${ha(a)}
          <h3 class="mayabot-entity-name">${W(a.title)}</h3>
          <p class="mayabot-entity-meta">${W(a.subtitle||ur(a.entityType))}</p>
          <p class="mayabot-entity-summary">${W(a.summary||a.body||"Details are available on the website.")}</p>
          ${_a(a)}
          ${ya(a)}
        </article>
      `).join(""),r.querySelectorAll("[data-view-entity]").forEach(a=>{a.addEventListener("click",async()=>{await Ce(a.getAttribute("data-view-entity"))})}),n.classList.add("active"),ar()}function ga(t){if(!t)return!1;try{let e=new URL(t,window.location.origin);return e.origin===window.location.origin?(window.location.href=`${e.pathname}${e.search}${e.hash}`,!0):(window.open(e.toString(),"_blank","noopener,noreferrer"),!0)}catch{return!1}}function ar(){window.setTimeout(()=>{let t=document.getElementById("mayabot-chat"),e=document.getElementById("mayabot-msgs");e&&(e.innerHTML=""),t&&t.classList.remove("visible")},lt)}async function Ce(t){let e=await nr(t);return ga(e)}async function lr(t,e=Z){let n=Re({[p.ENTITY_IDS]:t});if(!n.length)return Gt([],e),we([],[],"missing_entity_ids");try{let r=await Se(n);return Gt(r,e),we(n,r)}catch(r){return console.warn("[AI Hub Widget] Entity overlay failed:",r),Gt([],e),we(n,[],"entity_overlay_fetch_failed")}}function Re(t){let e=t[p.ENTITY_IDS]||t.ids||t.items||[],n=new Set;return(Array.isArray(e)?e:[]).map(r=>String(r??"").trim()).filter(Boolean).filter(r=>n.has(r)?!1:(n.add(r),!0))}function dr(t={}){if(!Ie.length)return!1;let e=String(t.sort_by||t.sortBy||"price_asc").trim().toLowerCase(),n=[...Ie].sort((o,i)=>ba(o,i,e)),r=Aa(Oe,e);return Gt(n,r),!0}function ba(t,e,n){return n==="price_desc"?zt(e,Vt)-zt(t,Vt):n==="rating"?sr(e,Vt)-sr(t,Vt):n==="newest"?cr(e)-cr(t):zt(t,or)-zt(e,or)}function zt(t,e){return pr([t?.pricing?.price,t?.pricing?.amount,t?.pricing?.premium,t?.pricing?.premium_min,t?.pricing?.monthly_premium,t?.pricing?.annual_premium,t?.pricing?.min_price,t?.pricing?.starting_price,t?.attributes?.price,t?.attributes?.amount,t?.attributes?.premium,t?.attributes?.monthly_premium,t?.attributes?.annual_premium,t?.displayPrice],e)}function sr(t,e){return pr([t?.attributes?.rating,t?.attributes?.review_rating,t?.attributes?.stars,t?.availability?.rating],e)}function cr(t){let e=t?.attributes?.updated_at||t?.attributes?.date||t?.availability?.updated_at||"",n=Date.parse(String(e||""));return Number.isFinite(n)?n:0}function pr(t,e){for(let n of t){let r=Ta(n);if(Number.isFinite(r))return r}return e}function Ta(t){if(typeof t=="number")return t;let e=String(t??"").replace(/,/g,"").match(/-?\d+(?:\.\d+)?/);return e?Number(e[0]):Number.NaN}function Aa(t,e){let n={price_asc:"sorted low to high",price_desc:"sorted high to low",rating:"sorted by rating",newest:"newest first"};return`${String(t||Z).replace(/\s+-\s+sorted.*$/i,"")} - ${n[e]||n.price_asc}`}function fr(t){return t.action===c.SHOW_ENTITIES||t.action===c.COMPARE_ENTITIES||t.action===c.OPEN_ENTITY_DETAIL||t.action===c.SORT_ENTITIES}async function mr(t){return t.action===c.SHOW_ENTITIES||t.action===c.COMPARE_ENTITIES?Ea(t.parameters||{}):t.action===c.OPEN_ENTITY_DETAIL?Ce(t.parameters?.[p.ENTITY_ID]||t.parameters?.id):t.action===c.SORT_ENTITIES?dr(t.parameters||{}):!1}function Ea(t){return lr(Re(t),t[p.SEARCH_QUERY]||t.title||Z)}var wt="mayabot-handoff-panel",hr="mayabot-handoff-overlay-styles",Sa=Object.freeze(["contact","support","help"]),wa=Object.freeze(["checkout","cart"]),br=new Set([c.CHECKOUT_HANDOFF,c.HANDOFF_TO_ADVISOR,c.HANDOFF_TO_AGENT,c.HANDOFF_TO_CLINIC,c.HANDOFF_TO_HUMAN,c.HANDOFF_TO_LAWYER,c.HANDOFF_TO_LICENSED_AGENT,c.HANDOFF_TO_RECRUITER]),_r=Object.freeze({[c.CHECKOUT_HANDOFF]:{title:"Checkout needs your confirmation",body:"This step may include payment or a secure checkout page. I can take you there, then you complete the final step yourself.",primary:"Open checkout"},[c.HANDOFF_TO_ADVISOR]:{title:"Advisor handoff",body:"This request needs a qualified advisor. I can open the contact path so the site team can continue.",primary:"Contact advisor"},[c.HANDOFF_TO_AGENT]:{title:"Agent handoff",body:"This step needs an agent or account-specific help. I can open the contact path for follow-up.",primary:"Contact agent"},[c.HANDOFF_TO_CLINIC]:{title:"Clinic handoff",body:"This request needs clinic confirmation. I can open the appointment or contact path for the next step.",primary:"Contact clinic"},[c.HANDOFF_TO_HUMAN]:{title:"Human handoff",body:"This step needs human confirmation. I can open the most relevant contact path.",primary:"Open contact"},[c.HANDOFF_TO_LAWYER]:{title:"Legal handoff",body:"This request needs a legal professional. I can open the consultation or contact path.",primary:"Contact lawyer"},[c.HANDOFF_TO_LICENSED_AGENT]:{title:"Licensed agent handoff",body:"This request needs a licensed agent. I can open the quote or contact path for follow-up.",primary:"Contact agent"},[c.HANDOFF_TO_RECRUITER]:{title:"Recruiter handoff",body:"This request needs recruiter review. I can open the application or contact path.",primary:"Contact recruiter"}});function dt(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}function it(t){return String(t||"").trim()}function Ia(){if(document.getElementById(hr))return;let t=document.createElement("style");t.id=hr,t.textContent=`
    #${wt} {
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
    #${wt}.active {
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
      #${wt} {
        bottom: 82px;
        width: min(calc(100vw - 20px), 420px);
      }
    }
  `,document.head.appendChild(t)}function Oa(){Ia();let t=document.getElementById(wt);return t||(t=document.createElement("div"),t.id=wt,t.setAttribute("aria-live","polite"),document.body.appendChild(t),t)}function Ca(){return window.AIHubAdapterRuntime?.config?.adapter?.routes||window.AIHubAdapter?.config?.adapter?.routes||{}}function Ra(t,e){let n=yr(e[p.URL]||e.path||e.href||e.handoff_flow?.page_url);if(n)return n;let r=Ca(),o=t===c.CHECKOUT_HANDOFF?wa:Sa;for(let i of o){let a=yr(r[i]);if(a)return a}return""}function yr(t){let e=it(t);if(!e)return"";try{let n=new URL(e,window.location.origin);return n.origin!==window.location.origin?"":`${n.pathname}${n.search}${n.hash}`||"/"}catch{return""}}function xa(t){return _r[t]||_r[c.HANDOFF_TO_HUMAN]}function Na(t){return t&&typeof t=="object"?t:{}}function va(t,e){return it(t.title)||e}function Pa(t,e,n){return it(e[p.MESSAGE])||it(t.handling)||n}function La(t,e){return it(e[p.REASON]||e.reason||e.blocked_reason||t.key)}function Da(t){let e=[["Provider",t.provider_label||t.provider],["Boundary",t.automation_boundary],["Recovery",t.recovery],["Evidence",t.evidence],["Page",t.page_url]].filter(([,n])=>it(n));return e.length?`
    <p class="mayabot-handoff-meta">
      ${e.map(([n,r])=>`<span><strong>${dt(n)}:</strong> ${dt(r)}</span>`).join("")}
    </p>
  `:""}function gr(t){t.classList.remove("active")}function Ua(){window.setTimeout(()=>{let t=document.getElementById("mayabot-chat"),e=document.getElementById("mayabot-msgs");e&&(e.innerHTML=""),t&&t.classList.remove("visible")},lt)}function Tr(t,e={}){let n=it(t).toUpperCase(),r=xa(n),o=Na(e.handoff_flow),i=Oa(),a=Ra(n,e),s=va(o,r.title),u=Pa(o,e,r.body),f=La(o,e);return i.innerHTML=`
    <div class="mayabot-handoff-body">
      <div class="mayabot-handoff-top">
        <h2 class="mayabot-handoff-title">${dt(s)}</h2>
        <button class="mayabot-handoff-close" type="button" aria-label="Close handoff">&times;</button>
      </div>
      <p class="mayabot-handoff-text">${dt(u)}</p>
      ${Da(o)}
      ${f?`<p class="mayabot-handoff-reason">${dt(f)}</p>`:""}
      <div class="mayabot-handoff-actions">
        <button type="button" class="secondary" data-close-handoff>Close</button>
        ${a?`<button type="button" data-open-handoff>${dt(r.primary)}</button>`:""}
      </div>
    </div>
  `,i.querySelector(".mayabot-handoff-close")?.addEventListener("click",()=>gr(i)),i.querySelector("[data-close-handoff]")?.addEventListener("click",()=>gr(i)),i.querySelector("[data-open-handoff]")?.addEventListener("click",()=>{window.location.href=a}),i.classList.add("active"),Ua(),!0}function Ar(t){return br.has(t.action)}function Er(t){return Tr(t.action,t.parameters||{})}function wr(t){return t.action===c.NAVIGATE_TO&&!!Or(t.parameters?.[p.PAGE])}function Ir(t){return window.location.href=Or(t.parameters?.[p.PAGE]),!0}function Or(t){let e=String(t||"").trim();if(!e||Cr(e)||/^https?:\/\//i.test(e))return"";if(e==="home"||e==="/")return"/";let n=ka(e);if(n)return n;let r=e.replace(/^\/+|\/+$/g,"");return r?`/${r}`:"/"}function ka(t){let e=window.AIHubAdapterRuntime?.config?.adapter?.routes||window.AIHubAdapter?.config?.adapter?.routes||{},n=Ma(t);for(let r of n){let o=e[r],i=Sr(o);if(i)return i}for(let[r,o]of Object.entries(e)){if(!n.includes(xe(r)))continue;let i=Sr(o);if(i)return i}return""}function Ma(t){let e=xe(t),n=String(t||"").trim().replace(/^\/+|\/+$/g,"").toLowerCase(),r=n.split("?")[0].split("#")[0].split("/").filter(Boolean).pop()||"";return Array.from(new Set([e,n,xe(r)].filter(Boolean)))}function xe(t){return String(t||"").trim().toLowerCase().replace(/[^a-z0-9/_\s-]+/g," ").replace(/[_-]+/g," ").replace(/\s+/g," ").trim().replace(/\s+/g,"-")}function Sr(t){let e=String(t||"").trim();if(!e||Cr(e))return"";if(/^https?:\/\//i.test(e))try{let n=new URL(e);return n.origin!==window.location.origin?"":`${n.pathname||"/"}${n.search||""}${n.hash||""}`}catch{return""}return e.startsWith("/")?e:`/${e.replace(/^\/+/,"")}`}function Cr(t){return/^(?:javascript:|data:|\/\/)/i.test(String(t||"").trim())}function Rr(t){let e=t?.params||t?.parameters||{};return{...t||{},action:String(t?.action||"").trim().toUpperCase(),params:e,parameters:e}}var Ne="AIHubAdapterRuntime",ve="AIHubAdapter";function Ha(t){let e=t?.params||t?.parameters||{};return{...t||{},params:e,parameters:e}}function It(){return!!(window[Ne]?.executeAction||window[ve]?.handleAction)}async function Pe(t){return(await Ot(t)).succeeded}async function Ot(t){let e=Ha(t);if(window[Ne]?.executeAction){let n=window[Ne],r=await n.executeAction(e)===!0,o=n.lastActionResult||{};return{succeeded:r,handled:o.handled===!0||r,status:o.status||(r?"ok":"not_handled"),reason:o.reason||"",blocked:o.status==="blocked",disabled:o.status==="disabled"}}if(window[ve]?.handleAction){let n=await window[ve].handleAction(e)===!0;return{succeeded:n,handled:n,status:n?"ok":"not_handled",reason:"",blocked:!1,disabled:!1}}return{succeeded:!1,handled:!1,status:"missing_adapter",reason:"",blocked:!1,disabled:!1}}var Fa=Object.freeze([{path:"/api/products?per_page=96",routePrefix:"/product/"},{path:"/api/products",routePrefix:"/product/"},{path:"/api/products.json",routePrefix:""},{path:"/products.json",routePrefix:"/products/"},{path:"/collections/all/products.json",routePrefix:"/products/"}]),Ba=Object.freeze(["products","data","items","results"]),Nr=Object.freeze(["id","product_id","handle","sku"]),vr=Object.freeze(["name","title"]),Ya=Object.freeze(["url","href","permalink","product_url"]),$a=Object.freeze(["image_url","imageUrl","image_src","imageSrc","image","images","media","thumbnail","thumbnail_url","featured_image","featuredImage","featured_image_url"]),ja=Object.freeze(["brand","vendor"]),qa=Object.freeze(["category","category_name","product_type"]),Va=Object.freeze(["description","summary","body_html"]),za=Object.freeze(["original_price","compare_at_price","regular_price"]),Pr=Object.freeze(["currency","currency_code"]),Ga=Object.freeze(["display_price","price_text","formatted_price"]),Wa="Unknown Brand",Ka="Products",Qa="/",Xa=/^[a-z0-9][a-z0-9-]*$/i,Le=null;function D(t){return t==null||typeof t=="object"?"":String(t||"").trim()}function ke(t){return D(t).toLowerCase().replace(/[^a-z0-9]+/g," ").trim()}function Lr(t){let e=new Set(["a","am","an","and","ask","asked","did","for","me","not","on","only","please","show","some","the","to","wanna","want","what","with","you","your"]),n=[],r=new Set;for(let o of Ja(ke(t)).split(" ")){let i=Za(o);i.length<=1||e.has(i)||r.has(i)||(n.push(i),r.add(i))}return n}function Ja(t){return t.replace(/\b(?:i\s+)?did\s+not\s+ask\s+for\s+(?:a\s+|an\s+)?[a-z0-9]+\b/g," ")}function Za(t){return["phone","phones","mobile","mobiles"].includes(t)?"phone":["book","books"].includes(t)?"books":t}function Me(t,e){return e.map(n=>D(t?.[n])).filter(Boolean)}function F(t,e){return Me(t,e)[0]||""}function Wt(t){let e=D(t).replace(/,/g,"");if(!e)return 0;let n=e.match(/-?\d+(?:\.\d+)?/),r=Number(n?n[0]:e);return Number.isFinite(r)?r:0}function ts(t,e){let n=F(t,Ga);if(n)return n;let r=F(t,Pr).toUpperCase();return e>0&&r?`${r} ${e.toLocaleString()}`:e>0?e.toLocaleString():""}function es(t){for(let e of $a){let n=De(t?.[e]);if(n)return n}return""}function De(t){if(!t)return"";if(Array.isArray(t)){for(let e of t){let n=De(e);if(n)return n}return""}if(typeof t=="object"){for(let e of["src","url","image_url","imageUrl","image_src","imageSrc","thumbnail","thumbnail_url","featured_image","featuredImage","featured_image_url"]){let n=De(t[e]);if(n)return n}return""}return ns(t)}function ns(t){let e=D(t);if(!e||/^javascript:/i.test(e))return"";if(/^data:image\//i.test(e))return e;try{let n=new URL(e,window.location.origin);return["http:","https:"].includes(n.protocol)?n.toString():""}catch{return""}}function rs(t){let e=D(t);if(!e)return"";try{let n=new URL(e,window.location.origin);return n.origin!==window.location.origin?"":`${n.pathname}${n.search}${n.hash}`}catch{return""}}function os(t,e,n){let r=rs(F(t,Ya));return r||(!Xa.test(e)||!/[a-z]/i.test(e)||!n?.routePrefix?"":`${n.routePrefix}${encodeURIComponent(e)}${Qa}`)}function He(t,e={}){if(!t)return null;let n=F(t,Nr),r=D(t.handle||t.slug||t.product_handle),o=F(t,vr),i=Wt(t.price||t.amount||t.cost),a=Wt(F(t,za));return!n&&!r?null:{id:n,handle:r,name:o,title:D(t.title||o),brand:F(t,ja)||Wa,category:F(t,qa)||Ka,description:F(t,Va),price:Number.isFinite(i)?i:0,originalPrice:Number.isFinite(a)?a:0,displayPrice:ts(t,i),currency:F(t,Pr),rating:Wt(t.rating||t.review_rating),reviewCount:Wt(t.review_count||t.reviews_count||t.reviews),imageUrl:es(t),url:os(t,r||n,e)}}function is(t){return Me(t,Nr)}function xr(t){return Me(t,vr).map(ke)}function Dr(t,e){let n=D(e);return!!(n&&is(t).includes(n))}function Ur(t,e){let n=Lr(e);if(!n.length)return!1;let r=ke([t?.name,t?.title,t?.brand,t?.category,t?.category_name,t?.product_type,t?.description,t?.tags].join(" "));return n.every(o=>r.includes(o)||r.includes(o.replace(/s$/,"")))}function as(t,e){let n=new Set(xr(e));return xr(t).some(r=>n.has(r))}function ss(t,e){return!!(t?.imageUrl&&t.imageUrl===e?.imageUrl)}function cs(t){if(Array.isArray(t))return t;for(let e of Ba){let n=t?.[e];if(Array.isArray(n))return n}return[]}async function us(t){try{let e=await fetch(new URL(t.path,window.location.origin),{headers:{Accept:"application/json"}});if(!e.ok)return[];let n=await e.json();return cs(n).map(r=>He(r,t)).filter(Boolean)}catch(e){return console.warn(`[AI Hub Widget] Catalog endpoint lookup failed for ${t.path}:`,e),[]}}async function Ue(){return Le||(Le=Promise.all(Fa.map(us)).then(t=>t.flat())),Le}async function ls(t,e=120){if(!Lr(t).length)return[];let r=new URL("/v1/products",d.apiUrl);r.searchParams.set("site_id",d.siteId),r.searchParams.set("limit",String(e));try{let o=await fetch(r.toString(),{headers:{Accept:"application/json"}});return o.ok?(await o.json()).map(i=>He(i)).filter(Boolean).filter(i=>Ur(i,t)).slice(0,12):[]}catch(o){return console.warn("[AI Hub Widget] Hub product search fallback failed:",o),[]}}async function kr(t,e=""){let n=(Array.isArray(t)?t:[]).map(D).filter(Boolean),r=[],o="",i="";if(n.length)try{r=await Mr(n),o="hub_by_ids"}catch(a){i="hub_product_lookup_failed",console.warn("[AI Hub Widget] Hub product ID lookup failed:",a)}if(!r.length&&n.length){let a=await Ue();r=n.map(s=>a.find(u=>Dr(u,s))).filter(Boolean),r.length&&(o="host_by_ids")}return!r.length&&e&&(r=await ls(e),r.length&&(o="hub_search")),!r.length&&e&&(r=(await Ue()).filter(s=>Ur(s,e)).slice(0,12),r.length&&(o="host_search")),{products:r,source:o,reason:r.length?"":i||"no_matching_products_rendered"}}async function Mr(t){let e=(Array.isArray(t)?t:[]).map(D).filter(Boolean);if(!e.length)return[];let n=new URL(k.PRODUCTS_BY_IDS,d.apiUrl);n.searchParams.set("site_id",d.siteId),n.searchParams.set("ids",e.join(","));let r=await fetch(n.toString(),{headers:{Accept:"application/json"}});if(!r.ok)throw new Error("Failed to fetch products from AI Hub API");let o=(await r.json()).map(a=>He(a)).filter(Boolean),i=new Map(o.map(a=>[String(a.id),a]));return e.map(a=>i.get(a)).filter(Boolean)}async function Kt(t){let e=D(t);if(!e)return"";let[n]=await Mr([e]);if(n?.url)return n.url;let r=await Ue(),o=r.find(a=>Dr(a,e));return o?.url?o.url:n&&r.find(a=>as(a,n)||ss(a,n))?.url||""}var ds=1,ps=1.08,fs=300,ms=Object.freeze(["hannah","sonia","libby","ava","susan","hazel","heera","salli","joanna","amy","emma","olivia","natasha","zira","aria","jenny","samantha","victoria","tessa","moira","karen","female","woman","nova","shimmer","google us english","microsoft aria"]),K="",Qt="",Ct=null,Fe=0;function at(t){if(!("speechSynthesis"in window)||!("SpeechSynthesisUtterance"in window))return!1;Xt();let e=++Fe;K=t;let n=()=>{if(e!==Fe||K!==t)return!1;try{let r=new SpeechSynthesisUtterance(t),o=hs(window.speechSynthesis.getVoices());return o?(o&&(r.voice=o),r.rate=ds,r.pitch=ps,r.onstart=Hr,r.onend=Hr,Xt(),window.speechSynthesis.cancel(),window.speechSynthesis.resume(),window.speechSynthesis.speak(r),!0):(K="",!1)}catch{return!1}};return window.speechSynthesis.getVoices().length>0?n():(window.speechSynthesis.onvoiceschanged=n,Ct=window.setTimeout(()=>{Ct=null,n()},fs),!0)}function Jt(){K&&at(K)}function Fr(){try{return!!K||!!window.speechSynthesis?.speaking||!!window.speechSynthesis?.pending}catch{return!!K}}function Zt(){Fe+=1,Xt(),K="",Qt="";try{window.speechSynthesis?.cancel()}catch{}}function hs(t){if(!Array.isArray(t)||t.length===0)return null;let e=_s(t)||ys(t);return e&&(Qt=e.name),e}function _s(t){if(Qt){let n=t.find(r=>r.name===Qt);if(n)return n}let e=String(d.speechVoiceName||"").toLowerCase();return e&&t.find(n=>n.name.toLowerCase()===e)||null}function ys(t){return d.speechVoicePreference.toLowerCase()!=="female"?t.find(e=>e.default)||t[0]:t.find(e=>ms.some(n=>e.name.toLowerCase().includes(n)))||null}function Hr(){Xt(),K=""}function Xt(){Ct&&window.clearTimeout(Ct),Ct=null,window.speechSynthesis&&(window.speechSynthesis.onvoiceschanged=null)}var gs=["data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='320' height='240' viewBox='0 0 320 240'%3E","%3Crect width='320' height='240' fill='%23f1f2ee'/%3E","%3Cpath d='M98 156h124l-31-40-25 30-17-22-51 32Z' fill='%23c8c3ba'/%3E","%3Ccircle cx='117' cy='95' r='17' fill='%23d8d3ca'/%3E","%3Ctext x='160' y='198' text-anchor='middle' fill='%23686660' font-family='Arial,sans-serif' font-size='16'%3EImage pending%3C/text%3E","%3C/svg%3E"].join(""),Br=12,bs=4,Ts=6,As=700,ee=[],Ye=G,ne=new Map,$e=!1;function Es(){try{Zt()}catch{}}function tt(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}function Ss(){if(document.getElementById("mayabot-product-overlay-styles"))return;let t=document.createElement("style");t.id="mayabot-product-overlay-styles",t.textContent=`
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
    /* Facts flow naturally: the grid is the single scroll area, so there is no
       nested scroll trap. Add/View stay reachable by scrolling the grid. */
    .mayabot-product-facts {
      margin: 0;
      display: grid;
      gap: 6px;
      flex: 0 0 auto;
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
    /* Speak-choice prompt: asked once per comparison, above the grid so it is
       reachable without scrolling and never overlaps the results. */
    .mayabot-compare-speak {
      display: none;
      align-items: center;
      gap: 10px;
      flex: 0 0 auto;
      padding: 11px 16px;
      border-bottom: 1px solid rgba(22, 22, 21, 0.1);
      background: #fbfbf8;
      font-size: 13px;
      line-height: 1.35;
    }
    #mayabot-product-panel.ask-speak .mayabot-compare-speak { display: flex; }
    .mayabot-compare-speak p { margin: 0; flex: 1 1 auto; overflow-wrap: anywhere; }
    .mayabot-compare-speak button {
      min-height: 32px;
      padding: 0 14px;
      border: 1px solid rgba(22, 22, 21, 0.14);
      border-radius: 8px;
      background: #161615;
      color: #ffffff;
      cursor: pointer;
      font-size: 12px;
      font-weight: 700;
    }
    .mayabot-compare-speak button.secondary { background: #ffffff; color: #161615; }
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
  `,document.head.appendChild(t)}function ws(){Ss();let t=document.getElementById("mayabot-product-panel");return t||(t=document.createElement("div"),t.id="mayabot-product-panel",t.setAttribute("aria-live","polite"),t.setAttribute("role","dialog"),t.setAttribute("tabindex","-1"),t.innerHTML=`
    <div class="mayabot-product-header">
      <h2 class="mayabot-product-title">${G}</h2>
      <button class="mayabot-product-close" type="button" aria-label="Close recommendations">&times;</button>
    </div>
    <div class="mayabot-compare-speak" role="group" aria-label="Speak comparison">
      <p>Would you like me to speak all the comparison points?</p>
      <button type="button" class="mayabot-compare-yes">Yes</button>
      <button type="button" class="mayabot-compare-no secondary">No</button>
    </div>
    <div class="mayabot-product-grid"></div>
  `,t.querySelector(".mayabot-product-close").addEventListener("click",Yr),t.querySelector(".mayabot-compare-yes").addEventListener("click",()=>$r(!0)),t.querySelector(".mayabot-compare-no").addEventListener("click",()=>$r(!1)),t.addEventListener("keydown",e=>{e.key==="Escape"&&Yr()}),document.body.appendChild(t),t)}function Yr(){let t=document.getElementById("mayabot-product-panel");t&&(t.classList.remove("active","ask-speak"),Es())}function $r(t){let e=document.getElementById("mayabot-product-panel");if(e&&e.classList.remove("ask-speak"),$e=!0,t){let n=Os(ee);n&&at(n)}}function Is(t,e){let n=document.getElementById("mayabot-product-panel");if(!n)return;if(!(e&&Array.isArray(t)&&t.length>=2)||$e){n.classList.remove("ask-speak");return}n.classList.add("ask-speak"),window.setTimeout(()=>n.querySelector(".mayabot-compare-yes")?.focus(),0)}function Os(t){let e=[];for(let n of(t||[]).slice(0,bs)){let o=(ne.get(String(n.id))||[]).slice(0,Ts).map(a=>`${a.label}: ${a.value}`).join(", "),i=n.name||n.title||"This product";e.push(o?`${i}. ${o}.`:`${i}.`)}return e.join(" ").slice(0,As)}async function Cs(t){let e={action:c.ADD_TO_CART,params:{[p.PRODUCT_ID]:t,[p.QUANTITY]:ge},parameters:{[p.PRODUCT_ID]:t,[p.QUANTITY]:ge}};It()&&await Pe(e)||window.dispatchEvent(new CustomEvent(Et.MAYABOT_ACTION,{detail:e}))}async function Rs(t){try{let n=await Kt(t);if(n){window.location.href=n;return}}catch(n){console.warn("[AI Hub Widget] Product detail URL lookup failed:",n)}let e={action:c.SHOW_PRODUCT_DETAIL,params:{[p.PRODUCT_ID]:t},parameters:{[p.PRODUCT_ID]:t}};It()&&await Pe(e)||window.dispatchEvent(new CustomEvent(Et.MAYABOT_ACTION,{detail:e}))}function xs(t){return t<=1?"count-1":t===2?"count-2":t===3?"count-3":"count-many"}function Ns(t){return t<=1?1:t===2?2:3}function vs(t){let e=new Set;return(Array.isArray(t)?t:[]).map(n=>String(n??"").trim()).filter(Boolean).filter(n=>e.has(n)?!1:(e.add(n),!0))}function Be(t,e,n="",r={}){let o=(Array.isArray(e)?e:[]).map(u=>String(u?.id??"").trim()).filter(Boolean),i=o.length,a=t.length,s=i>0?"succeeded":"failed";return{status:s,stage:"product_overlay",reason:n||(s==="succeeded"?"":"no_matching_products_rendered"),evidence:{requested_product_count:a,rendered_product_count:i,missing_product_count:Math.max(a-i,0),requested_product_ids:t.slice(0,Br).join(","),rendered_product_ids:o.slice(0,Br).join(","),lookup_source:r.source||"",search_query:r.searchQuery||""}}}function Ps(t){let e=String(t?.displayPrice||"").trim();if(e)return e;let n=Number(t?.price||0);return Number.isFinite(n)&&n>0?n.toLocaleString():"Price unavailable"}var Ls=6,Ds=24,Us=120;function ks(t){let e=new Map;return Array.isArray(t)&&t.forEach(n=>{if(!n||typeof n!="object")return;let r=String(n.product_id||"").trim();if(!r||!Array.isArray(n.facts))return;let o=n.facts.filter(i=>i&&typeof i=="object"&&i.label&&i.value).slice(0,Ls).map(i=>({label:String(i.label).slice(0,Ds),value:String(i.value).slice(0,Us)}));o.length&&e.set(r,o)}),e}function Ms(t){let e=ne.get(String(t));return!e||!e.length?"":`<dl class="mayabot-product-facts">${e.map(r=>`<div class="mayabot-fact"><dt>${tt(r.label)}</dt><dd>${tt(r.value)}</dd></div>`).join("")}</dl>`}function te(t,e){let n=ws(),r=n.querySelector(".mayabot-product-grid"),o=n.querySelector(".mayabot-product-title"),i=t.length;if(ee=Array.isArray(t)?[...t]:[],Ye=e||G,n.classList.remove("count-1","count-2","count-3","count-many"),n.classList.add(xs(i)),n.style.setProperty("--mayabot-card-count",String(Ns(i))),o.textContent=Ye,!i){r.innerHTML='<p class="mayabot-product-empty">No matching products are currently available.</p>',n.classList.add("active");return}r.innerHTML=t.map(a=>{let s=tt(a.id);return`
        <article class="mayabot-product-card" data-product-id="${s}">
          <img class="mayabot-product-image" src="${tt(a.imageUrl||gs)}" alt="${tt(a.name)}">
          <h3 class="mayabot-product-name">${tt(a.name||a.title||"Product")}</h3>
          <p class="mayabot-product-meta">${tt(a.brand)} - ${tt(Ps(a))}</p>
          ${Ms(a.id)}
          <div class="mayabot-product-actions">
            <button type="button" data-add="${s}">Add</button>
            <button type="button" class="secondary" data-view="${s}">View</button>
          </div>
        </article>
      `}).join(""),r.querySelectorAll("[data-add]").forEach(a=>{a.addEventListener("click",async()=>{await Cs(a.getAttribute("data-add"))})}),r.querySelectorAll("[data-view]").forEach(a=>{a.addEventListener("click",async()=>{await Rs(a.getAttribute("data-view"))})}),n.classList.add("active"),t.length>0&&Hs()}function Hs(){window.setTimeout(()=>{let t=document.getElementById("mayabot-chat"),e=document.getElementById("mayabot-msgs");e&&(e.innerHTML=""),t&&t.classList.remove("visible")},lt)}async function qr(t,e=G,n={}){let r=vs(t),o=String(n.searchQuery||"").trim();ne=ks(n.comparisonFacts);let i=ne.size>0;if($e=!1,!r.length&&!o)return te([],e),Be([],[],"missing_product_ids");try{let{products:a,source:s,reason:u}=await kr(r,o);return te(a,e),Is(a,i),Be(r,a,u,{source:s,searchQuery:o})}catch(a){return console.warn("[AI Hub Widget] Product overlay failed:",a),te([],e),Be(r,[],"product_overlay_fetch_failed",{searchQuery:o})}}function Vr(t={}){if(!ee.length)return!1;let e=String(t.sort_by||t.sortBy||"price_asc").trim().toLowerCase(),n=[...ee].sort((r,o)=>Fs(r,o,e));return te(n,Bs(Ye,e)),!0}function Fs(t,e,n){return n==="price_desc"?pt(e.price,Number.NEGATIVE_INFINITY)-pt(t.price,Number.NEGATIVE_INFINITY):n==="rating"?pt(e.rating||e.review_rating,Number.NEGATIVE_INFINITY)-pt(t.rating||t.review_rating,Number.NEGATIVE_INFINITY):n==="newest"?jr(e)-jr(t):pt(t.price,Number.POSITIVE_INFINITY)-pt(e.price,Number.POSITIVE_INFINITY)}function pt(t,e){let n=String(t??"").replace(/,/g,"").match(/-?\d+(?:\.\d+)?/);if(!n)return e;let r=Number(n[0]);return Number.isFinite(r)?r:e}function jr(t){let e=t?.updated_at||t?.created_at||t?.date||"",n=Date.parse(String(e||""));return Number.isFinite(n)?n:0}function Bs(t,e){let n={price_asc:"sorted low to high",price_desc:"sorted high to low",rating:"sorted by rating",newest:"newest first"};return`${String(t||G).replace(/\s+-\s+sorted.*$/i,"")} - ${n[e]||n.price_asc}`}function Gr(t){return t.action===c.SHOW_PRODUCTS||t.action===c.SHOW_COMPARISON||t.action===c.SHOW_PRODUCT_DETAIL||t.action===c.SORT_PRODUCTS}async function Wr(t){return t.action===c.SHOW_COMPARISON?zr(t.parameters||{},"Product comparison",{syncListing:!1,comparisonFacts:(t.parameters||{}).comparison}):t.action===c.SHOW_PRODUCTS?zr(t.parameters||{},G):t.action===c.SHOW_PRODUCT_DETAIL?js(t.parameters||{}):t.action===c.SORT_PRODUCTS?Vr(t.parameters||{}):!1}async function zr(t,e=G,n={}){let r=Array.isArray(t[p.PRODUCT_IDS])?t[p.PRODUCT_IDS]:[],o=$s(t),a=n.syncListing!==!1?await Ys(o):{succeeded:!1,handled:!1,status:"skipped",stage:"product_display_sync",reason:"comparison_overlay"},s=await qr(r,t.title||o||e,{searchQuery:o,comparisonFacts:n.comparisonFacts}),u={...s.evidence||{},listing_sync_status:a.status||"",listing_sync_stage:a.stage||"",listing_sync_reason:a.reason||""};return s.status!=="succeeded"?{...s,evidence:u}:o&&a.handled&&!a.succeeded?{status:"failed",stage:"product_display_sync",reason:a.reason||a.status||"listing_sync_failed",evidence:u}:{...s,stage:a.succeeded?"product_display_sync":s.stage,evidence:u}}async function Ys(t){let e=Kr(t);return e?Ot({action:c.FILTER_PRODUCTS,params:{[p.SEARCH_QUERY]:e,query:e,q:e}}):{succeeded:!1,handled:!1,status:"skipped",stage:"product_display_sync",reason:"missing_search_query"}}function $s(t){return Kr(t[p.SEARCH_QUERY]||t.search||t.query||t.q||"")}function Kr(t){return String(t||"").trim()}async function js(t){let e="";try{e=await Kt(t[p.PRODUCT_ID])}catch(n){return console.warn("[AI Hub Widget] Product detail URL lookup failed:",n),!1}return e?(window.location.href=e,!0):!1}var je="stop_action_fallback",qs=new Set([c.SHOW_PRODUCTS,c.SHOW_COMPARISON,c.SHOW_PRODUCT_DETAIL,c.SORT_PRODUCTS]);function Qr(t){return It()&&!qs.has(t.action)}async function Xr(t){let e=await Ot(t);return e.succeeded?!0:e.blocked||e.disabled?je:!1}function Jr(t){return window.dispatchEvent(new CustomEvent(Et.MAYABOT_ACTION,{detail:t})),{status:"requested",stage:"browser_event",reason:"event_dispatched_without_confirmation"}}var Vs=12,zs=8,Gs=80,Zr=Object.freeze([["data-entity-id",""],["data-product-id","product"],["data-listing-id","listing"],["data-offer-id","offer"],["data-plan-id","plan"],["data-item-id",""]]),Ws="data-entity-type",Ks="entity",to=Object.freeze(["sort","sort_by","sortby","orderby","order_by","order"]),Qs=Object.freeze(["page","p","offset","cursor","q","query","search","token","session","email","phone","name","address","utm_source","utm_medium","utm_campaign"]),Xs=Object.freeze([["price","[data-price], [itemprop='price'], .price"],["rating","[data-rating], [itemprop='ratingValue'], .rating"],["availability","[data-availability], [itemprop='availability'], .availability, .stock"]]);function B(t){return String(t||"").replace(/\s+/g," ").trim().slice(0,Gs)}function Js(t){if(!t||typeof t.getBoundingClientRect!="function")return!1;let e=t.getBoundingClientRect();if(e.width<=0||e.height<=0)return!1;let n=t.ownerDocument?.defaultView,r=n?.getComputedStyle?.(t);if(r&&(r.visibility==="hidden"||r.display==="none"))return!1;let o=t.ownerDocument?.documentElement,i=Number(n?.innerWidth||o?.clientWidth||0),a=Number(n?.innerHeight||o?.clientHeight||0);return i>0&&a>0&&e.bottom>0&&e.right>0&&e.top<a&&e.left<i}function Zs(t){for(let[e,n]of Zr){let r=B(t.getAttribute(e));if(r)return{id:r,impliedType:n}}return null}function tc(t,e){return B(t.getAttribute(Ws)).toLowerCase()||e||Ks}function ec(t){let e=t.querySelector?.("h1, h2, h3, h4, [data-entity-name], [itemprop='name']");return B(e?.textContent||t.getAttribute("aria-label")||t.getAttribute("title"))}function nc(t){let e=t.matches?.("a[href]")?t:t.querySelector?.("a[href]");return uc(e?.href||"")}function rc(t){let e={};for(let[n,r]of Xs){let o=t.querySelector?.(r);if(!o)continue;let i=B(o.getAttribute?.("content")||o.getAttribute?.(`data-${n}`)||o.textContent);i&&(e[n]=i)}return e}function oc(){return Zr.map(([t])=>`[${t}]`).join(",")}function ic(){let t=new Set,e=[];for(let n of x(oc())){if(e.length>=Vs)break;let r=Zs(n);!r||t.has(r.id)||!Js(n)||(t.add(r.id),e.push({id:r.id,entity_type:tc(n,r.impliedType),label:ec(n),route:nc(n),facts:rc(n)}))}return e}function ac(){let t=eo();if(!t)return{};let e={};for(let[n,r]of t.entries()){let o=n.toLowerCase();if(!(Qs.includes(o)||to.includes(o))){if(Object.keys(e).length>=zs)break;e[B(n)]=B(r)}}return e}function sc(){let t=eo();for(let n of to){let r=B(t?.get?.(n));if(r)return r}let e=x("select[name*='sort' i], select[id*='sort' i]")[0];return B(e?.value)}function cc(){try{return{path:B(window.location.pathname)||"/",search:B(window.location.search)}}catch{return{path:"",search:""}}}function re(){return{route:cc(),filters:ac(),sort:sc(),visible_entities:ic()}}function eo(){try{return new URLSearchParams(window.location.search)}catch{return null}}function uc(t){if(!t)return"";try{let e=new URL(t,window.location.origin);return e.origin!==window.location.origin?"":`${e.pathname}${e.search}`||"/"}catch{return""}}var jl=Object.freeze(["CHECKOUT","CLEAR_CART","REMOVE_FROM_CART","UPDATE_CART_QUANTITY","CLEAR_HISTORY","SUBMIT_PAYMENT","PLACE_ORDER"]);var T=Object.freeze({DISPLAY:"display",NAVIGATION:"navigation",DETAIL:"detail",FILTER:"filter",SORT:"sort",CART:"cart",NONE:"none"}),lc=1200,dc=60,pc=Object.freeze({SHOW_PRODUCTS:T.DISPLAY,SHOW_ENTITIES:T.DISPLAY,SHOW_COMPARISON:T.DISPLAY,COMPARE_ENTITIES:T.DISPLAY,NAVIGATE_TO:T.NAVIGATION,SHOW_PRODUCT_DETAIL:T.DETAIL,OPEN_ENTITY_DETAIL:T.DETAIL,FILTER_PRODUCTS:T.FILTER,CLEAR_FILTERS:T.FILTER,SORT_PRODUCTS:T.SORT,SORT_ENTITIES:T.SORT,ADD_TO_CART:T.CART,REMOVE_FROM_CART:T.CART,UPDATE_CART_QUANTITY:T.CART,CLEAR_CART:T.CART}),fc="[data-cart-count], [data-testid='cart-count'], .cart-count, #cart-count";function ro(t){return pc[String(t||"").toUpperCase()]||T.NONE}function ze(){let t=re();return{path:t.route.path,search:t.route.search,filters:t.filters,sort:String(t.sort||"").toLowerCase(),visibleIds:t.visible_entities.map(e=>String(e.id)),cartCount:mc()}}function mc(){let t=document.querySelector(fc);if(!t)return null;let e=t.getAttribute("data-cart-count")??t.textContent,n=Number.parseInt(String(e||"").replace(/[^\d-]/g,""),10);return Number.isFinite(n)?n:null}function oo(t){let e=[];for(let n of["product_ids","entity_ids"])Array.isArray(t[n])&&e.push(...t[n].map(String));for(let n of["product_id","entity_id"])t[n]&&e.push(String(t[n]));return e}function Rt(t){let e=String(t||"").split("?")[0].split("#")[0];return e.length>1?e.replace(/\/+$/,""):e}function qe(t){return String(t||"").trim().toLowerCase().replace(/[^a-z0-9/_\s-]+/g," ").replace(/[_-]+/g," ").replace(/\s+/g," ").trim().replace(/\s+/g,"-")}function no(t){let e=String(t||"").trim();if(!e||/^(?:javascript:|data:|\/\/)/i.test(e))return"";try{let n=new URL(e,window.location.origin);return n.origin!==window.location.origin?"":Rt(n.pathname||"/")}catch{return""}}function hc(t){let e=String(t||"").trim();if(!e)return"";if(e==="/"||qe(e)==="home")return"/";let n=window.AIHubAdapterRuntime?.config?.adapter?.routes||window.AIHubAdapter?.config?.adapter?.routes||{},r=qe(e);for(let[o,i]of Object.entries(n)){if(qe(o)!==r)continue;let a=no(i);if(a)return a}return e.startsWith("/")||/^https?:\/\//i.test(e)?no(e):Rt(`/${r}`)}function _c(t,e){let n=oo(t);return n.length?n.filter(o=>!e.visibleIds.includes(o)).length?{satisfied:!1,reason:"requested_records_not_visible"}:{satisfied:!0,reason:""}:e.visibleIds.length>0?{satisfied:!0,reason:""}:{satisfied:!1,reason:"nothing_visible"}}function yc(t,e,n){let r=hc(t.page),o=Rt(e.path);return r&&o===r?{satisfied:!0,reason:""}:!r&&o!==Rt(n.path)?{satisfied:!0,reason:""}:r&&o!==Rt(n.path)?{satisfied:!1,reason:"wrong_route"}:{satisfied:!1,reason:"route_unchanged"}}function gc(t,e,n){let r=oo(t)[0];return r?`${e.path}${e.search}`.includes(r)?{satisfied:!0,reason:""}:e.visibleIds.includes(r)&&e.path!==n.path?{satisfied:!0,reason:""}:{satisfied:!1,reason:"record_not_opened"}:{satisfied:!1,reason:"no_record_requested"}}function bc(t,e,n){if(t==="CLEAR_FILTERS")return Object.keys(n.filters).length===0?{satisfied:!0,reason:""}:{satisfied:!1,reason:"filters_still_active"};let r=new Map(Object.entries(n.filters).map(([u,f])=>[u.toLowerCase(),Ve(f)])),o=e.filters&&typeof e.filters=="object"?e.filters:e,i=new Set(["product_ids","entity_ids","page","search_query","query","q","request_id"]),a=Object.entries(o||{}).filter(([u,f])=>!i.has(u.toLowerCase())&&Ve(f));return a.length?a.every(([u,f])=>{let E=r.get(u.toLowerCase());return E!==void 0&&E===Ve(f)})?{satisfied:!0,reason:""}:{satisfied:!1,reason:"filter_value_mismatch"}:r.size>0?{satisfied:!0,reason:""}:{satisfied:!1,reason:"no_filter_observed"}}function Ve(t){return(Array.isArray(t)?t:[t]).map(n=>String(n??"").trim().toLowerCase()).filter(Boolean).sort().join(",")}function Tc(t,e,n){let r=String(t.sort_by||"").toLowerCase();return r&&e.sort&&e.sort.includes(r.split("_")[0])?{satisfied:!0,reason:""}:e.visibleIds.join(",")!==n.visibleIds.join(",")?{satisfied:!0,reason:""}:{satisfied:!1,reason:"order_unchanged"}}function Ac(t,e,n){if(n.cartCount===null||e.cartCount===null)return{satisfied:!1,reason:"cart_state_unobservable"};let r=e.cartCount>n.cartCount,o=e.cartCount<n.cartCount;return t==="ADD_TO_CART"?r?{satisfied:!0,reason:""}:{satisfied:!1,reason:"cart_unchanged"}:t==="REMOVE_FROM_CART"?o?{satisfied:!0,reason:""}:{satisfied:!1,reason:"cart_unchanged"}:t==="CLEAR_CART"?e.cartCount===0?{satisfied:!0,reason:""}:{satisfied:!1,reason:"cart_not_empty"}:e.cartCount!==n.cartCount?{satisfied:!0,reason:""}:{satisfied:!1,reason:"cart_unchanged"}}function Ec(t,e,n){let r=String(t?.action||"").toUpperCase(),o=t?.parameters||t?.params||{},i=ro(r);return i===T.DISPLAY?_c(o,e):i===T.NAVIGATION?yc(o,e,n):i===T.DETAIL?gc(o,e,n):i===T.FILTER?bc(r,o,e):i===T.SORT?Tc(o,e,n):i===T.CART?Ac(r,e,n):{satisfied:!0,reason:"no_postcondition"}}async function io(t,e){let n=ro(t?.action);if(n===T.NONE)return{family:n,verified:!0,reason:"no_postcondition"};let r=Date.now()+lc,o={satisfied:!1,reason:"not_observed"};for(;Date.now()<r&&(o=Ec(t,ze(),e),!o.satisfied);)await Sc(dc);return{family:n,verified:o.satisfied,reason:o.reason}}function Sc(t){return new Promise(e=>window.setTimeout(e,t))}var h=Object.freeze({searchForm:"search-form",searchInput:"search-input",searchSubmit:"search-submit",searchResults:"search-results",addToCart:"add-to-cart",checkout:"checkout",clearCart:"clear-cart",cartButton:"cart-button",cartLineItem:"cart-line-item",navLink:"nav-link",productCard:"product-card",productLink:"product-link",productName:"product-name",productDetail:"product-detail",productTitle:"product-title"}),Ge="data-aihub-nav",ao="data-entity-name",Y=4e3,so=1500,wc=80,Ic='[id^="mayabot"], [data-aihub-widget]';function ft(t){return!!t&&!t.closest?.(Ic)}var mt=t=>`[data-aihub-role="${t}"]`,et=t=>x(mt(t)).filter(ft),S=t=>et(t)[0]||null;function Oc(t){let e=g(t);return e&&x(`[data-product-id="${We(e)}"]`).find(ft)||null}function g(t){return String(t??"").trim()}function We(t){return window.CSS?.escape?window.CSS.escape(t):g(t).replace(/["\\]/g,"\\$&")}async function U(t,e){let n=Date.now()+e;for(;;){let r=t();if(r)return r;if(Date.now()>=n)return null;await new Promise(o=>window.setTimeout(o,wc))}}function Q(){return!!(S(h.searchForm)||S(h.searchInput)||S(h.searchSubmit))}function xt(){return!!S(h.addToCart)}function Nt(){return!!S(h.checkout)}function vt(){return!!S(h.clearCart)}function Pt(){return et(h.navLink).length>0}function ct(){return Ke().length>0}function $(t){let e=String(t||"").split("?")[0].split("#")[0];return e.length>1?e.replace(/\/+$/,""):e||"/"}function oe(t){try{let e=new URL(String(t||""),window.location.origin);return e.origin!==window.location.origin?"":`${e.pathname}${e.search}`||"/"}catch{return""}}function Lt(t){return g(t).toLowerCase().replace(/[^a-z0-9]+/g," ").trim()}function st(t){return g(t).toLowerCase().replace(/[\s\-_/\\,.:;|]+/g," ").replace(/\s+/g," ").trim()}function Ke(){let t=et(h.productCard);return t.length?t:x("[data-product-id]").filter(ft)}function ie(t){let e=g(t?.getAttribute?.(ao));return e||g(t?.querySelector?.(mt(h.productName))?.textContent)}var Qe="product_id",Cc="product_name";function ae(t,e){let n=Oc(t);if(n)return{card:n,matchedBy:Qe};let r=st(e);if(!r)return null;let o=Ke().filter(i=>st(ie(i))===r);return o.length===1?{card:o[0],matchedBy:Cc}:o.length>1?{ambiguous:!0,matchCount:o.length}:null}function j(t,e,n=""){return{handled:!0,status:"succeeded",self_verified:!0,stage:t,reason:n,evidence:e||{}}}function A(t,e,n){return{handled:!0,status:"failed",stage:t,reason:e,evidence:n||{}}}function co(t,e,n){return{handled:!0,status:"unconfirmed",stage:t,reason:e,evidence:n||{}}}function uo(t,e){return{handled:!0,status:"unsupported_host",stage:t,reason:e,evidence:{}}}function q(t){return t?(ho(t),lo(t,"down"),lo(t,"up"),typeof t.click=="function"?t.click():_o(t,"click"),vc(t),!0):!1}function fo(t,e){return t?(ho(t),Rc(t,ce(e)),xc(t),!0):!1}function mo(t){if(!t)return!1;let e=ce(t.tagName).toLowerCase()==="form"?t:t.closest?.("form");return e&&typeof e.requestSubmit=="function"?(e.requestSubmit(),!0):q(t)}function ho(t){try{t.scrollIntoView?.({behavior:"smooth",block:"center",inline:"center"})}catch{}typeof t.focus=="function"&&t.focus({preventScroll:!0})}function Rc(t,e){if(Pc(t)){t.textContent=e;return}let n=Object.getPrototypeOf(t),r=Object.getOwnPropertyDescriptor(n,"value");if(r?.set){r.set.call(t,e);return}t.value=e}function xc(t){po(t,"beforeinput"),po(t,"input"),t.dispatchEvent(new Event("change",{bubbles:!0}))}function lo(t,e){Nc(t,`pointer${e}`),_o(t,`mouse${e}`)}function Nc(t,e){typeof PointerEvent=="function"&&t.dispatchEvent(new PointerEvent(e,{bubbles:!0,cancelable:!0,pointerType:"mouse",isPrimary:!0}))}function _o(t,e){t.dispatchEvent(new MouseEvent(e,{bubbles:!0,cancelable:!0,view:window}))}function po(t,e){if(typeof InputEvent=="function"){t.dispatchEvent(new InputEvent(e,{bubbles:!0,cancelable:!0,inputType:"insertText"}));return}t.dispatchEvent(new Event(e,{bubbles:!0,cancelable:!0}))}function vc(t){let e=ce(t.getAttribute?.("role")).toLowerCase();["button","link","menuitem","option","tab"].includes(e)&&(se(t,"keydown","Enter"),se(t,"keyup","Enter"),(e==="button"||e==="tab")&&(se(t,"keydown"," "),se(t,"keyup"," ")))}function se(t,e,n){t.dispatchEvent(new KeyboardEvent(e,{bubbles:!0,cancelable:!0,key:n}))}function Pc(t){let e=ce(t?.getAttribute?.("role")).toLowerCase();return!!(t?.isContentEditable||!("value"in t)&&["searchbox","textbox"].includes(e))}function ce(t){return String(t||"").trim()}function Lc(t){try{let e=`${window.location.pathname}${window.location.search}`.toLowerCase();return e.includes(encodeURIComponent(t).toLowerCase())||e.includes(t.toLowerCase())}catch{return!1}}var Dc=1;function Uc(t){let e=g(t).split(/\s+/).filter(n=>n.length>2);return e.length<2?"":e.reduce((n,r)=>r.length>n.length?r:n,"")}async function Dt(t,{broadenIfSparse:e=!1}={}){let n=g(t);if(!Q())return null;if(!n)return uo("host_search","empty_query");let r=await yo(n);if(!e||!r||r.status!=="succeeded")return r;let o=r.evidence?.result_count;if(typeof o!="number"||o>Dc)return r;let i=Uc(n);if(!i||i===n)return r;let a=await yo(i);return a?.status==="succeeded"&&(a.evidence?.result_count||0)>o?{...a,evidence:{...a.evidence,broadened_from:n}}:r}async function yo(t){let e=S(h.searchInput);if(!e){let s=S(h.searchSubmit)||S(h.searchForm);s&&q(s),e=await U(()=>S(h.searchInput),so)}if(!e)return A("host_search","search_input_unavailable");fo(e,t);let n=e.closest?.("form")||S(h.searchForm);mo(n||S(h.searchSubmit)||e);let r=await U(()=>{let s=S(h.searchResults);return!s||s.getAttribute("data-results-loading")==="true"?null:s},Y);if(!r)return co("host_search","results_not_settled");let o=Number(r.getAttribute("data-result-count")),i={result_count:Number.isFinite(o)?o:null,query:r.getAttribute("data-query")||"",route:`${window.location.pathname}${window.location.search}`,route_reflects_query:Lc(t)};return i.route_reflects_query||i.query.toLowerCase().includes(t.toLowerCase())?r.getAttribute("data-results-empty")==="true"||i.result_count===0?A("host_search","no_results",i):j("host_search",i):A("host_search","query_not_reflected",i)}var Ut="host_add_to_cart",ht="host_clear_cart",kt="host_product_detail";function _t(){let t=S(h.cartButton)||x("[data-cart-count]").find(ft)||null;if(!t)return null;let e=Number(t.getAttribute("data-cart-count"));return Number.isFinite(e)?e:null}function Xe(){return et(h.cartLineItem).map(t=>g(t.getAttribute("data-product-id"))).filter(Boolean)}function go(t){return!!t.disabled||t.getAttribute("aria-disabled")==="true"}async function bo(t,e,n){let r=ae(e,n);if(!r&&n&&Q()){let o=await Dt(n);o&&o.status==="succeeded"&&(r=ae(e,n))}return r?r.ambiguous?{error:A(t,"ambiguous_product",{product_name:g(n),match_count:r.matchCount})}:r:{error:A(t,"product_not_on_page",{product_id:g(e),product_name:g(n)})}}function kc(t,e){let n=g(e);if(n){let r=x(`${mt(h.addToCart)}[data-product-id="${We(n)}"]`).find(ft);if(r)return r}return t?.querySelector?.(mt(h.addToCart))||null}async function Je(t){if(!xt()&&!ct())return null;let e=g(t?.product_id||t?.entity_id),n=g(t?.product_name),r=await bo(Ut,e,n);if(r.error)return r.error;let o=g(r.card.getAttribute("data-product-id"))||e,i=kc(r.card,r.matchedBy===Qe?e:o);if(!i)return A(Ut,"add_control_missing",{product_id:o,product_name:n});if(go(i))return A(Ut,"add_control_disabled",{product_id:o,product_name:n});let a=_t(),s=Xe();q(i);let u=await U(()=>{let E=_t(),v=Xe(),C=a!=null&&E!=null&&E>a,b=o&&v.includes(o)&&!s.includes(o),R=v.length>s.length;return C||b||R?{afterCount:E,lines:v}:null},Y),f={cart_before:a,cart_after:_t(),product_id:o,product_name:n,matched_by:r.matchedBy};return u?j(Ut,{...f,line_item_present:o?Xe().includes(o):!0}):A(Ut,"cart_unchanged",f)}async function Ze(){if(!vt())return null;let t=S(h.clearCart);if(!t)return A(ht,"clear_control_missing");if(go(t))return A(ht,"clear_control_disabled");let e=_t();if(e==null)return A(ht,"cart_state_unobservable");if(e===0)return j(ht,{cart_before:0,cart_after:0});q(t);let n=await U(()=>_t()===0?!0:null,Y),r={cart_before:e,cart_after:_t()};return n?j(ht,r):A(ht,"cart_not_empty",r)}function Mc(t){return t?.querySelector?.(mt(h.productLink))||t?.querySelector?.("a[href]")||null}function Hc(t,e){let n=S(h.productDetail),r=st(e);if(n){let i=g(n.getAttribute("data-product-id"));if(t&&i&&i===t)return"product_id";let a=st(ie(n));if(r&&a&&a===r)return"product_name"}let o=S(h.productTitle);return o&&r&&st(o.textContent)===r?"product_title":""}async function tn(t){if(!ct()&&!Q())return null;let e=g(t?.product_id||t?.entity_id),n=g(t?.product_name),r=await bo(kt,e,n);if(r.error)return r.error;let o=g(r.card.getAttribute("data-product-id"))||e,i=Mc(r.card);if(!i)return A(kt,"product_link_missing",{product_id:o,product_name:n});let a=$(window.location.pathname);q(i);let s=await U(()=>Hc(o,n)||null,Y),u={product_id:o,product_name:n,matched_by:r.matchedBy,route:`${window.location.pathname}${window.location.search}`,verified_by:s||""};return s?j(kt,u):$(window.location.pathname)===a?A(kt,"route_unchanged",u):A(kt,"product_page_not_confirmed",u)}var Mt="host_navigate",To="host_checkout",Fc="main, [data-aihub-role='search-results'], [data-product-id]";function Bc(t){let e=Lt(t);if(!e)return null;let n=et(h.navLink),r=s=>[Lt(s.getAttribute(Ge)),Lt(s.textContent),Lt(oe(s.getAttribute("href")||s.href))].filter(Boolean),o=n.find(s=>r(s).includes(e));if(o)return o;let i=null,a=0;for(let s of n)for(let u of r(s))!e.includes(u)&&!u.includes(e)||u.length>a&&(a=u.length,i=s);return i}function Yc(t){try{return new URL(String(t||""),window.location.origin).searchParams}catch{return new URLSearchParams}}function Ao(t){if($(window.location.pathname)!==$(t))return!1;let e=new URLSearchParams(window.location.search);for(let[n,r]of Yc(t).entries())if(e.get(n)!==r)return!1;return!0}async function en(t){if(!Pt())return null;let e=Bc(t);if(!e)return A(Mt,"no_matching_nav_target",{target:g(t)});let n=oe(e.getAttribute("href")||e.href),r=$(window.location.pathname);q(e);let o=await U(()=>n&&Ao(n)?!0:null,Y),i=$(window.location.pathname),a={target:g(t),expected:$(n),route:`${window.location.pathname}${window.location.search}`};return o?await U(()=>document.querySelector(Fc)?!0:null,Y)?j(Mt,a):A(Mt,"page_not_ready",a):i!==r?A(Mt,"wrong_route",{...a,actual:i}):A(Mt,"route_unchanged",{...a,actual:i})}async function nn(){if(!Nt())return null;let t=et(h.checkout)[0];if(!t)return null;let e=`${window.location.pathname}${window.location.search}`,n=oe(t.getAttribute("href")||"/checkout");q(t);let r=await U(()=>n&&Ao(n)?!0:null,Y),o=`${window.location.pathname}${window.location.search}`,i={expected:$(n||"/checkout"),route:o};return r?j(To,i):A(To,o===e?"route_unchanged":"wrong_route",i)}var So=new Set([c.FILTER_PRODUCTS,c.SHOW_PRODUCTS]),wo=new Set([c.SHOW_PRODUCT_DETAIL]);function ue(t){return t.parameters||t.params||{}}function Io(t){let e=ue(t);return String(e[p.SEARCH_QUERY]||e.search||e.query||e.q||"").trim()}function Oo(t){let e=ue(t);return String(e[p.PAGE]||e.page||e.target||"").trim()}function Eo(t){let e=ue(t);return!!(e[p.PRODUCT_ID]||e.entity_id||String(e[p.PRODUCT_NAME]||"").trim())}function Co(t){let e=t.action;return e===c.ADD_TO_CART?(xt()||ct())&&Eo(t):e===c.CHECKOUT?Nt():e===c.CLEAR_CART?vt():wo.has(e)?(ct()||Q())&&Eo(t):So.has(e)?Q()&&!!Io(t):e===c.NAVIGATE_TO?Pt()&&!!Oo(t):!1}async function Ro(t){let e=t.action,n=ue(t);if(e===c.ADD_TO_CART)return Je(n);if(e===c.CHECKOUT)return nn();if(e===c.CLEAR_CART)return Ze();if(wo.has(e))return tn(n);if(So.has(e)){let r=Io(t);return r?Dt(r,{broadenIfSparse:!0}):null}if(e===c.NAVIGATE_TO){let r=Oo(t);return r?en(r):null}return null}var $c=Object.freeze([{name:"host_contract",canExecute:Co,execute:Ro},{name:"runtime_adapter",canExecute:Qr,execute:Xr},{name:"product_overlay",canExecute:Gr,execute:Wr},{name:"entity_overlay",canExecute:fr,execute:mr},{name:"handoff_overlay",canExecute:Ar,execute:Er},{name:"platform_adapter",canExecute:()=>!0,execute:Yn},{name:"provider_adapter",canExecute:Jn,execute:Zn},{name:"navigation",canExecute:wr,execute:Ir},{name:"browser_event",canExecute:()=>!0,execute:Jr}]);async function on(t){let e=[];for(let n of t||[]){let r=Rr(n),o=await jc(r);o&&e.push(o)}return e}async function jc(t){if(!t.action)return;let e=Date.now(),n=window.location.href,r=ze();await $t(d.apiUrl,d.siteId,t,{status:"requested",stage:"widget_dispatch",requested_url:n,final_url:n,evidence:rn(t,n,n)}),await $t(d.apiUrl,d.siteId,t,{status:"executing",stage:"widget_dispatch",requested_url:n,final_url:window.location.href,evidence:rn(t,n,window.location.href)});let o;try{o=await qc(t)}catch(u){o={status:"failed",stage:"widget_dispatch",reason:u instanceof Error?u.message:"execution_error"}}let i=o.status==="succeeded"&&o.self_verified?{family:o.stage||"host_contract",verified:!0,reason:o.reason||""}:o.status==="succeeded"?await io(t,r):{family:"none",verified:!1,reason:o.reason||"execution_failed"},a=window.location.href,s={...rn(t,n,a,o),postcondition_family:i.family,postcondition_verified:i.verified,postcondition_reason:i.reason};return await $t(d.apiUrl,d.siteId,t,{status:o.status,stage:o.stage,reason:o.reason,duration_ms:Date.now()-e,requested_url:n,final_url:a,evidence:s}),{action:t.action,request_id:t.request_id||t.action_request_id||"",turn_id:t.turn_id||"",sequence:Number(t.sequence||0),status:o.status,stage:o.stage,reason:o.reason,verified:i.verified,postcondition:i.family,requested_url:n,final_url:a,evidence:s}}async function qc(t){if(!t.action)return{status:"failed",stage:"normalization",reason:"missing_action"};for(let e of $c){if(!e.canExecute(t))continue;let n=await e.execute(t),r=Vc(n,e.name);if(r)return r}return{status:"failed",stage:"all",reason:"no_executor_succeeded"}}function Vc(t,e){if(t===!0)return{status:"succeeded",stage:e,reason:""};if(t===je)return{status:"blocked",stage:e,reason:"action_blocked"};if(!t||typeof t!="object")return null;let n=String(t.status||"").trim().toLowerCase();return n?{status:n,stage:String(t.stage||e).trim()||e,reason:String(t.reason||"").trim(),self_verified:!!t.self_verified,evidence:t.evidence&&typeof t.evidence=="object"?t.evidence:{}}:null}function rn(t,e,n,r={}){let o=t.parameters||t.params||{},i={requested_url:e,final_url:n,url_changed:e!==n,path_changed:xo(e)!==xo(n),title:document.title||"",stage:r.stage||"",result_status:r.status||""};return o.page&&(i.target_page=o.page),o.product_id&&(i.product_id=o.product_id),o.entity_id&&(i.entity_id=o.entity_id),Array.isArray(o.product_ids)&&(i.product_count=o.product_ids.length),Array.isArray(o.entity_ids)&&(i.entity_count=o.entity_ids.length),{...i,...r.evidence&&typeof r.evidence=="object"?r.evidence:{}}}function xo(t){try{return new URL(t,window.location.href).pathname}catch{return""}}var m=Object.freeze({CANCELLED:"cancelled",NETWORK:"network",TIMEOUT:"timeout",ACCESS_DENIED:"access_denied",INVALID_REQUEST:"invalid_request",PAYLOAD_TOO_LARGE:"payload_too_large",UNSUPPORTED_MEDIA:"unsupported_media",RATE_LIMITED:"rate_limited",PROVIDER_UNAVAILABLE:"provider_unavailable",SERVER_ERROR:"server_error",MICROPHONE:"microphone",UNKNOWN:"unknown"}),No=Object.freeze({[m.CANCELLED]:"Stopped",[m.NETWORK]:"Connection issue",[m.TIMEOUT]:"Timed out",[m.ACCESS_DENIED]:"Access denied",[m.INVALID_REQUEST]:"Try again",[m.PAYLOAD_TOO_LARGE]:"Recording too long",[m.UNSUPPORTED_MEDIA]:"Audio not supported",[m.RATE_LIMITED]:"Service busy",[m.PROVIDER_UNAVAILABLE]:"Service unavailable",[m.SERVER_ERROR]:"Service error",[m.MICROPHONE]:"Mic unavailable",[m.UNKNOWN]:"Try again"}),vo=64,O=class extends Error{constructor(e,{status:n=0,code:r="",requestId:o="",stage:i=""}={}){super(`voice_transport_${e}`),this.name="VoiceTransportError",this.category=e,this.status=Number(n)||0,this.code=String(r||"").slice(0,vo),this.requestId=String(o||"").slice(0,vo),this.stage=i}get customerMessage(){return zc(this.category)}toDiagnostics(){return{category:this.category,status:this.status,code:this.code,request_id:this.requestId,stage:this.stage}}};function zc(t){return No[t]||No[m.UNKNOWN]}function Po(t){return t instanceof O&&t.category===m.CANCELLED}function Gc(t){let e=Number(t)||0;return e===401||e===403?m.ACCESS_DENIED:e===408?m.TIMEOUT:e===413?m.PAYLOAD_TOO_LARGE:e===415?m.UNSUPPORTED_MEDIA:e===429?m.RATE_LIMITED:e===502||e===503||e===504?m.PROVIDER_UNAVAILABLE:e>=500?m.SERVER_ERROR:e>=400?m.INVALID_REQUEST:m.UNKNOWN}function Ht(t){if(t instanceof O)return t;let e=String(t?.message||t||"").toLowerCase();return t?.name==="AbortError"||e.includes("abort")||e.includes("timeout")||e.includes("timed out")?new O(m.TIMEOUT):e.includes("microphone")||e.includes("permission")||e.includes("notallowed")?new O(m.MICROPHONE):t?.name==="TypeError"||e.includes("failed to fetch")||e.includes("network")||e.includes("load failed")?new O(m.NETWORK):new O(m.UNKNOWN)}function Lo(t,e=null){let n=Number(t?.status)||0,r=t?.headers?.get?.("x-request-id")||t?.headers?.get?.("x-correlation-id")||"",o=e&&typeof e=="object"&&(e.code||e.error_code)||"",i=/^[A-Za-z0-9_.:-]{1,64}$/.test(String(o||""))?String(o):"";return new O(Gc(n),{status:n,code:i,requestId:r,stage:"http_response"})}var Wc="/v1/widget/runtime-event",Kc=16;function N(t={}){let e=JSON.stringify({client_id:d.siteId,site_id:d.siteId,origin:window.location.origin,occurred_at:new Date().toISOString(),session_id:d.sessionId,turn_id:V(t.turn_id,80),request_id:V(t.request_id,80),component:V(t.component||"voice",60),stage:V(t.stage,80),event_type:V(t.event_type||"runtime_event",80),severity:V(t.severity||"info",20),status:V(t.status||"ok",20),message_code:V(t.message_code,80),duration_ms:Do(t.duration_ms),metadata:Qc(t.metadata)}),n=new URL(Wc,d.apiUrl).toString();fetch(n,{method:"POST",headers:{Accept:"application/json","Content-Type":"application/json"},body:e,keepalive:!0}).catch(()=>{})}function Qc(t){if(!t||typeof t!="object"||Array.isArray(t))return{};let e={};for(let[n,r]of Object.entries(t).slice(0,Kc)){let o=V(n,60).toLowerCase();!o||Xc(o)||(typeof r=="boolean"||r===null?e[o]=r:typeof r=="number"?e[o]=Do(r):typeof r=="string"&&(e[o]=V(r,120)))}return e}function Xc(t){return["audio","transcript","response","error","exception","token","secret"].some(e=>t.includes(e))}function V(t,e){return String(t||"").replace(/\s+/g," ").trim().slice(0,e)}function Do(t){let e=Number(t||0);return Number.isFinite(e)?Math.max(0,e):0}var Jc=3,Zc="AIHubAdapterRuntime",tu="AIHubAdapter";function eu(t,e){let n=new URL(k.SHOP_WS,t);return n.protocol=n.protocol==="https:"?"wss:":"ws:",n.searchParams.set("site_id",e),n.searchParams.set("session_id",d.sessionId),n.toString()}function nu(t){return new Promise((e,n)=>{let r=new FileReader;r.onloadend=()=>{let o=String(r.result||"");e(o.includes(",")?o.split(",").pop():o)},r.onerror=()=>n(r.error||new Error("Failed to read audio blob")),r.readAsDataURL(t)})}var an=class{constructor(){this.queue=[],this.blocked=[],this.playing=!1,this.current=null,this.lastPlaybackStartMs=0,this.installUnlockListeners()}push(e,n=""){e&&(this.queue.push({audioB64:e,fallbackText:n}),this.playNext())}playNext(){if(this.playing||this.queue.length===0)return;this.playing=!0;let e=this.queue.shift(),n=new Audio(At.DATA_WAV_PREFIX+e.audioB64);n.preload="auto",this.current=n,n.onplay=()=>{this.lastPlaybackStartMs=typeof performance<"u"?performance.now():0},n.onended=()=>{this.current=null,this.playing=!1,this.playNext()},n.onerror=()=>{this.current=null,e.fallbackText&&nt(e.fallbackText),this.playing=!1,this.playNext()},n.play().catch(r=>{if(console.warn("Audio playback failed",r),this.current=null,this.isAutoplayBlocked(r)){e.fallbackText?nt(e.fallbackText):this.blocked.unshift(e),this.playing=!1;return}e.fallbackText&&nt(e.fallbackText),this.playing=!1,this.playNext()})}installUnlockListeners(){if(typeof window>"u")return;let e=()=>{this.retryBlocked(),Jt()};window.addEventListener("pointerdown",e,{capture:!0,passive:!0}),window.addEventListener("keydown",e,{capture:!0}),window.addEventListener("touchstart",e,{capture:!0,passive:!0})}retryBlocked(){this.blocked.length&&(this.queue.unshift(...this.blocked.splice(0)),this.playNext())}speakInsteadOfBlocked(e){!e||!this.blocked.length||(this.blocked=[],nt(e))}isAutoplayBlocked(e){let n=`${e?.name||""} ${e?.message||e||""}`.toLowerCase();return n.includes("notallowed")||n.includes("user didn't interact")||n.includes("not allowed")}stop(){if(this.queue=[],this.blocked=[],this.current){try{this.current.pause(),this.current.currentTime=0}catch{}this.current.onended=null,this.current.onerror=null,this.current=null}this.playing=!1,Zt()}isSpeaking(){return this.playing||this.queue.length>0||Fr()}},le=new an;function de(){le.stop()}function un(){return le.isSpeaking()}function ln(t="reset"){Mo.reset(t),ko.reset(t)}var sn=class{constructor(){this.inFlight=null,this.cancelled=!1}reset(e="reset"){this.cancelled=e==="user_cancel";try{this.inFlight?.abort()}catch{}this.inFlight=null}async sendAudio(e,n,r=[]){let o=X();N({event_type:"voice_turn_started",stage:"http_request",status:"started",metadata:{transport:"http",audio_type:e?.type||"unknown"}});let i=new FormData;i.append("audio",e,iu(e)),i.append("site_id",d.siteId),i.append("session_id",d.sessionId),r&&r.length>0&&i.append("conversation_history",JSON.stringify(r));let a=Yo();a&&i.append("page_context",JSON.stringify(a));let s,u=typeof AbortController=="function"?new AbortController:null;this.inFlight=u,this.cancelled=!1;try{s=await fetch(`${d.apiUrl}${k.SHOP}`,{method:vn.POST,body:i,signal:u?.signal})}catch(I){throw this.cancelled||I?.name==="AbortError"?new O(m.CANCELLED,{stage:"user_cancel"}):Ht(I)}if(!s.ok)throw Lo(s,await cu(s));let f=await s.json();f.transcript&&n.onUserMessage?.(f.transcript);let E=Array.isArray(f.ui_actions)?f.ui_actions:[],v=[];E.length>0&&(v=await on(E),n.onActionResults?.(v));let C=f.response_text||"",b=Fo(C,E,v,f.success_text||"");b&&n.onAssistantMessage?.(b,E),n.onStatusChange?.(y.READY);let R=b===C;R&&f.audio_b64?ou(f.audio_b64,f.spoken_text||C):R?nt(f.spoken_text||C):b&&nt(b),n.onComplete?.(f),N({event_type:"voice_turn_completed",stage:"http_response",status:"ok",request_id:ru(s),duration_ms:X()-o,metadata:{transport:"http",action_count:f.ui_actions?.length||0}})}},cn=class{constructor(){this.ws=null,this.connected=!1,this.connecting=null,this.failed=!1,this.retries=0,this.audioQueue=le,this.callbacks=null,this.turnText="",this.receivedAudio=!1,this.pendingAudioChunks=[]}async ensureConnected(e=[]){return this.canUseWebSocket()?this.isOpen()?!0:this.connecting?this.connecting:(this.connecting=this.openConnection(e),this.connecting):!1}canUseWebSocket(){return!this.failed&&d.useWebSocket&&"WebSocket"in window}isOpen(){return this.connected&&this.ws?.readyState===WebSocket.OPEN}openConnection(e=[]){return new Promise(n=>{let r=new WebSocket(eu(d.apiUrl,d.siteId)),o=!1;this.ws=r;let i=(s=null)=>{o||(o=!0,this.markConnectionFailed(n,s,r))},a=window.setTimeout(()=>{i()},kn);r.onopen=()=>{o||(o=!0,this.handleConnectionOpen(a,e,n))},r.onmessage=s=>{this.handleMessage(s).catch(u=>this.handleTransportError(u))},r.onerror=()=>{if(o){this.failActiveTurn(m.NETWORK);return}i(a)},r.onclose=()=>{if(this.connected=!1,o){this.failActiveTurn(m.NETWORK);return}i(a)}})}markConnectionOpen(){this.connected=!0,this.connecting=null,this.retries=0}handleConnectionOpen(e,n,r){window.clearTimeout(e),this.markConnectionOpen(),this.sendConfig(n),r(!0)}markConnectionFailed(e,n=null,r=null){n&&window.clearTimeout(n),this.connected=!1,this.connecting=null,this.retries+=1,this.retries>=Jc&&(this.failed=!0),r&&r.readyState!==WebSocket.CLOSED&&r.close(),e(!1)}sendConfig(e=[]){this.sendJson({type:M.CONFIG,history:e||[],session_id:d.sessionId,page_context:Yo()})}sendJson(e){return!this.ws||this.ws.readyState!==WebSocket.OPEN?!1:(this.ws.send(JSON.stringify(e)),!0)}async sendAudio(e,n,r=[]){if(!await this.ensureConnected(r))return!1;this.callbacks=n,this.turnText="",this.receivedAudio=!1,this.pendingAudioChunks=[],this.sendConfig(r);let i=await nu(e),a=this.beginTurn();return this.turnStartedAt=X(),N({event_type:"voice_turn_started",stage:"websocket_send",status:"started",metadata:{transport:"websocket",audio_type:e?.type||"unknown"}}),this.sendJson({type:M.AUDIO_CHUNK,data:i,mime_type:e?.type||""})&&this.sendJson({type:M.AUDIO_END,mime_type:e?.type||""})?(await a,!0):(this.settleTurn(),this.callbacks=null,!1)}beginTurn(){return this.settleTurn(),new Promise(e=>{let n=window.setTimeout(()=>{this.failActiveTurn(m.TIMEOUT)},Mn);this.activeTurn={resolve:e,timer:n}})}settleTurn(){let e=this.activeTurn;return this.activeTurn=null,e?(window.clearTimeout(e.timer),e.resolve(),!0):!1}failActiveTurn(e){if(!this.activeTurn)return;let n=this.callbacks;if(this.callbacks=null,this.pendingAudioChunks=[],n){let r=new O(e,{stage:"websocket"});n.onStatusChange?.(y.ERROR,r.customerMessage),n.onComplete?.({error:r.category}),N({event_type:"voice_turn_failed",stage:"websocket",severity:"error",status:"failed",message_code:r.code||r.category,duration_ms:X()-(this.turnStartedAt||X()),metadata:{transport:"websocket",category:r.category,http_status:r.status}})}this.settleTurn()}async handleMessage(e){let n=this.callbacks;if(!n)return;let r=this.parseMessage(e.data);if(!r){this.completeWithError(n,"Invalid WebSocket message");return}if(!this.handleIncrementalMessage(r,n)){if(r.type===M.DONE){await this.handleDoneMessage(r,n);return}r.type===M.ERROR&&this.completeWithError(n,r.message||"WebSocket error")}}parseMessage(e){try{let n=JSON.parse(e);return n&&typeof n=="object"?n:null}catch{return null}}handleIncrementalMessage(e,n){return e.type===M.TRANSCRIPT?(n.onUserMessage?.(e.text||""),!0):e.type===M.TEXT_CHUNK?(this.turnText+=e.text||"",!0):e.type===M.AUDIO_CHUNK?(this.receivedAudio=!!e.audio_b64||this.receivedAudio,e.audio_b64&&this.pendingAudioChunks.push(e.audio_b64),!0):!1}async handleDoneMessage(e,n){let r=e.response_text||this.turnText;try{let o=Array.isArray(e.ui_actions)?e.ui_actions:[],i=[];o.length>0&&(i=await on(o),n.onActionResults?.(i));let a=Fo(r,o,i,e.success_text||"");n.onAssistantMessage?.(a,o,{streamed:!0}),n.onStatusChange?.(y.READY);let s=a===r;if(this.receivedAudio&&s)for(let u of this.pendingAudioChunks)this.audioQueue.push(u);else s?nt(e.spoken_text||r):a&&nt(a);n.onComplete?.(e),N({event_type:"voice_turn_completed",stage:"websocket_done",status:"ok",duration_ms:X()-(this.turnStartedAt||X()),metadata:{transport:"websocket",action_count:e.ui_actions?.length||0}})}catch(o){this.handleTransportError(o)}finally{this.pendingAudioChunks=[],this.callbacks=null,this.settleTurn()}}completeWithError(e,n){e.onStatusChange?.(y.ERROR,Bo(n)),e.onComplete?.({error:n});let r=Ht(n);N({event_type:"voice_turn_failed",stage:"websocket_message",severity:"error",status:"failed",message_code:r.code||r.category,duration_ms:X()-(this.turnStartedAt||X()),metadata:{transport:"websocket",category:r.category,http_status:r.status}}),this.callbacks=null,this.settleTurn()}handleTransportError(e){console.error("AI Hub WebSocket transport failed",e);let n=this.callbacks;n&&this.completeWithError(n,String(e))}reset(e="reset"){this.callbacks=null,this.turnText="",this.receivedAudio=!1,this.pendingAudioChunks=[],this.settleTurn();try{this.ws?.close()}catch{}this.ws=null,this.connected=!1,this.connecting=null,this.failed=!1,this.retries=0}},ko=new sn,Mo=new cn;async function Ho(t,e,n,r=[]){try{if(d.useWebSocket&&await Mo.sendAudio(t,n,r))return;await ko.sendAudio(t,n,r)}catch(o){let i=o instanceof O?o:Ht(o);if(Po(i)){N({event_type:"voice_turn_cancelled",stage:i.stage||"transport",status:"cancelled",metadata:{transport:d.useWebSocket?"websocket_or_http":"http"}}),n.onStatusChange?.(y.READY),n.onComplete?.({cancelled:!0});return}console.error(o),N({event_type:"voice_turn_failed",stage:i.stage||"transport",severity:"error",status:"failed",request_id:i.requestId,message_code:i.code||i.category,metadata:{transport:d.useWebSocket?"websocket_or_http":"http",category:i.category,http_status:i.status}}),n.onStatusChange?.(y.ERROR,Bo(o)),n.onComplete?.({error:String(o)})}}function ru(t){return t?.headers?.get?.("x-request-id")||t?.headers?.get?.("x-correlation-id")||""}function X(){return typeof performance<"u"?performance.now():Date.now()}function ou(t,e=""){le.push(t,e)}function iu(t){let e=String(t?.type||"").toLowerCase();return e.includes("mp4")?"audio.mp4":e.includes("ogg")?"audio.ogg":e.includes("wav")?"audio.wav":At.WEBM_FILENAME}var au=/\b(opened|opening|taking you|took you|navigat|sorted|sorting|filtered|filtering|showing|shown|displayed|added to (?:your )?cart|here (?:it |they )?(?:is|are))\b/i,su=/\b(?:i(?:'ll| will)\s+try\s+to|i'?m\s+(?:going\s+to|about\s+to)|let me)\b/i,Uo="I could not complete that on the page. The site may not have responded - please try again, or do it manually.";function Fo(t,e,n,r=""){let o=String(t||"");if(!o||!Array.isArray(e)||e.length===0)return o;let i=String(r||"");if(!(!!i||au.test(o)||su.test(o)))return o;let s=Array.isArray(n)?n:[];return s.length!==e.length||!s.every(f=>f?.status==="succeeded"&&f?.verified!==!1)?Uo:i||o}async function cu(t){try{return await t.json()}catch{return null}}function Bo(t){if(t instanceof O)return t.customerMessage;let e=String(t?.message||t||"").toLowerCase();return e.includes("quota")?"Quota reached":e.includes("transcription")||e.includes("speech")?"Voice unavailable":Ht(t).customerMessage}function nt(t){return t?at(String(t).slice(0,700)):!1}function Yo(){let t=window[Zc],e=window[tu];try{if(typeof t?.getContext=="function")return t.getContext();if(typeof e?.getContext=="function")return e.getContext()}catch(n){console.warn("[AI Hub Widget] Page context collection failed:",n)}return uu()}function uu(){try{return{title:document.title||"",url:window.location.href,path:window.location.pathname,...re()}}catch(t){return console.warn("[AI Hub Widget] Local page state collection failed:",t),null}}var lu=4,du=40,pu=24,fu=80,mu=120,dn=6,hu=40,_u=600,yu=6,gu=12,$o=/\[PRODUCT_IDS:\s*([^\]]+)\]/g;function jo(){let t=[];function e(n,r){let o=String(r||"").trim();o&&(t.push({role:n,content:o}),t.length>hu&&t.shift())}return{history:t,historyForRequest(){if(t.length<=dn)return t.map(i=>({...i}));let n=t.slice(0,t.length-dn),r=t.slice(t.length-dn).map(i=>({...i})),o=bu(n);return o?[o,...r]:r},clear(){t.length=0},rememberUserMessage(n){e("user",n)},rememberAssistantMessage(n,r){e("assistant",Tu(n,r))},rememberActionResults(n){let r=Eu(n);r&&e("assistant",r)}}}function bu(t){let e=[],n=[];for(let o of t){o.role==="user"&&e.length<yu&&e.push(o.content.replace(/\s+/g," ").trim().slice(0,80));let i;for($o.lastIndex=0;(i=$o.exec(o.content))!==null;)pn(n,i[1].split(",").map(a=>a.trim()))}let r=[];return e.length&&r.push(`Earlier the customer asked: ${e.join("; ")}.`),n.length&&r.push(`Products discussed: ${n.slice(0,gu).join(", ")}.`),r.length?{role:"system",content:`[CONVERSATION_SUMMARY] ${r.join(" ")}`.slice(0,_u)}:null}function Tu(t,e){let n=Au(e);return n.length?`${t} [PRODUCT_IDS: ${n.join(",")}]`:t}function Au(t){let e=[];for(let n of t||[]){let r=n.params||{};pn(e,r[p.PRODUCT_IDS]),pn(e,[r[p.PRODUCT_ID]])}return e}function pn(t,e){for(let n of Array.isArray(e)?e:[])n&&!t.includes(n)&&t.push(n)}function Eu(t){let e=(Array.isArray(t)?t:[]).map(Su).filter(Boolean).slice(0,lu);return e.length?`[BROWSER_ACTION_RESULTS: ${e.join(" | ")}]`:""}function Su(t){if(!t||typeof t!="object"||!t.action)return"";let e=[pe(t.action,du),`status=${pe(t.status,pu)||"unknown"}`],n=Iu(t.final_url);return n&&e.push(`final_path=${pe(n,mu)}`),t.reason&&e.push(`reason=${pe(t.reason,fu)}`),wu(e,t.evidence),e.join(" ")}function wu(t,e={}){e.rendered_product_count!==void 0&&t.push(`rendered_products=${Number(e.rendered_product_count||0)}`),e.rendered_entity_count!==void 0&&t.push(`rendered_records=${Number(e.rendered_entity_count||0)}`)}function pe(t,e){return String(t||"").replace(/\s+/g," ").trim().slice(0,e)}function Iu(t){try{let e=new URL(String(t||""),window.location.href);return`${e.pathname}${e.search}${e.hash}`}catch{return""}}var qo="aihub:session-reset",fe="AIHub",Ou=Object.freeze(["mayabot:","aihub:"]);function Cu(t){let e=[];for(let n=0;n<t.length;n+=1){let r=t.key(n);r&&Ou.some(o=>r.startsWith(o))&&e.push(r)}return e}function Vo(t){if(!t)return[];try{let e=Cu(t);for(let n of e)t.removeItem(n);return e}catch{return[]}}function Ru(){let t=[];try{t.push(...Vo(window.sessionStorage))}catch{}try{t.push(...Vo(window.localStorage))}catch{}return t}function zo({cancelRecording:t,stopPlayback:e,resetTransport:n,conversationMemory:r,clearOverlays:o,rotateSessionId:i}={}){return function(){let s={stopped_recording:!1,stopped_audio:!1,cleared_keys:[],session_id:""};return s.stopped_recording=yt(t),s.stopped_audio=yt(e),yt(n),yt(()=>r?.clear?.()),yt(o),s.cleared_keys=Ru(),s.session_id=String(yt(i)||""),s}}function yt(t){if(typeof t!="function")return!1;try{let e=t();return e===void 0?!0:e}catch(e){return console.warn("[AI Hub Widget] Session reset step failed:",e),!1}}function Go(t){let e=window[fe]||{};e.resetSession=t,window[fe]=e;let n=()=>t();return window.addEventListener(qo,n),()=>{window.removeEventListener(qo,n),window[fe]?.resetSession===t&&delete window[fe].resetSession}}var Wo=null;function fn(t){Wo||(Ko(t),Wo=window.setInterval(()=>Ko(t),Un))}async function Ko({boot:t,shutdownWidget:e}){try{if(await xu()){t();return}e()}catch{t()}}async function xu(){let t=new URL(k.WIDGET_STATUS,d.apiUrl);t.searchParams.set("site_id",d.siteId);let e=await fetch(t.toString(),{cache:"no-store",headers:{Accept:"application/json"}});return e.ok?(await e.json()).enabled!==!1:!0}window.__mayabot_identifier="voice-orb";var mn=null,hn=null;function Qo(){if(window.__mayabotBooted||document.getElementById("mayabot-widget"))return;window.__mayabotBooted=!0,Tn();let t=xn(),e=null,n=null,r=!1;function o(_=Pn){e&&window.clearTimeout(e),e=window.setTimeout(()=>{t.msgs.innerHTML="",t.chat.classList.remove("visible"),e=null},_)}function i(_,ut=""){r=_===y.RECORDING,yn(Zo(_)),t.status.className="",_===y.RECORDING?(e&&(window.clearTimeout(e),e=null),t.msgs.innerHTML="",t.chat.classList.add("visible"),t.status.innerText="Listening...",t.status.classList.add("listening")):_===y.PROCESSING?(t.chat.classList.add("visible"),t.status.innerText="Analyzing...",t.status.classList.add("processing")):_===y.READY?(t.status.innerText="Ready",t.status.classList.add("ready")):_===y.ERROR&&(t.status.innerText=ut||"Try again",t.status.classList.add("error"))}let a=jo(),s=null,u="",f=!1,E=0;async function v(_){if(f)return;f=!0;let ut=++E,rt=()=>ut===E;t.btn.disabled=!0,s=null,u="";try{await Ho(_,t,{onUserMessage:P=>{rt()&&(Tt(t,P,"user"),a.rememberUserMessage(P))},onAssistantChunk:(P,gt)=>{rt()&&(u=gt,s||(s=Tt(t,"","ai")),ye(t,s,u))},onAssistantMessage:(P,gt,ei={})=>{rt()&&(ei.streamed&&s?ye(t,s,P):Tt(t,P,"ai"),a.rememberAssistantMessage(P,gt),s=null,u="")},onActionResults:P=>{rt()&&a.rememberActionResults(P)},onStatusChange:(P,gt)=>{rt()&&i(P,gt)},onComplete:()=>{rt()&&o()}},a.historyForRequest())}finally{rt()&&(f=!1,t.btn.disabled=!1),s=null,u=""}}function C(){E+=1,ln("user_cancel"),de(),f=!1,t.btn.disabled=!1,s=null,u="",N({event_type:"voice_turn_cancelled",stage:"orb_gesture",status:"cancelled"}),i(y.READY)}let b=Hn(v,i);mn=b;function R(){return f||un()}function I(){if(R()){C();return}b.toggle()}let _n={idle:{label:"Maya voice assistant. Click, press Enter, or press Space to talk.",title:"Click to talk"},recording:{label:"Maya is listening. Click once to send, or press Escape to cancel.",title:"Click once to send - Escape to cancel"},processing:{label:"Maya is working on your request. Please wait.",title:"Request in progress"},speaking:{label:"Maya is speaking. Click to stop, or press Escape to stop.",title:"Click to stop Maya"}};function Zo(_){return _===y.RECORDING?"recording":_===y.PROCESSING?"processing":un()?"speaking":"idle"}function yn(_){let ut=_n[_]||_n.idle;t.btn.setAttribute("aria-label",ut.label),t.btn.setAttribute("title",ut.title),t.btn.setAttribute("data-orb-state",_),t.btn.classList.toggle("recording",_==="recording"),t.btn.classList.toggle("speaking",_==="speaking")}yn("idle"),t.btn.addEventListener("click",_=>{_.detail>1||I()});let gn=_=>{if(_.key==="Escape"){if(r){b.cancel(),N({event_type:"voice_recording_cancelled",stage:"keyboard_escape",status:"cancelled"}),i(y.READY);return}R()&&C()}};document.addEventListener("keydown",gn);let bn=_=>{t.btn.contains(_.target)||Jt()};document.addEventListener("pointerdown",bn,{capture:!0});let ti=Go(zo({cancelRecording:()=>b.cancel(),stopPlayback:de,resetTransport:ln,conversationMemory:a,clearOverlays:()=>{t.msgs.innerHTML="",t.chat.classList.remove("visible"),document.getElementById("mayabot-product-panel")?.remove()},rotateSessionId:()=>d.rotateSessionId()}));hn=()=>{document.removeEventListener("keydown",gn),document.removeEventListener("pointerdown",bn,{capture:!0}),ti(),e&&window.clearTimeout(e),e=null,n&&window.clearTimeout(n),n=null,hn=null},Nu()&&(vu(),n=window.setTimeout(()=>{if(a.history.length>0)return;let _=`Welcome to ${d.brandName}. How can I help you today?`;Tt(t,_,"ai"),i(y.READY),o(Dn),at(_)},Ln))}function Xo(){mn?.cancel(),mn=null,hn?.(),de(),window.__mayabotBooted=!1,document.getElementById("mayabot-widget")?.remove(),document.getElementById("mayabot-product-panel")?.remove()}function Nu(){if(!d.autoGreet||!Pu())return!1;try{return window.sessionStorage.getItem(Jo())!=="1"}catch{return!window.__mayabotAutoGreeted}}function vu(){window.__mayabotAutoGreeted=!0;try{window.sessionStorage.setItem(Jo(),"1")}catch{}}function Jo(){return`mayabot:auto-greeted:${d.siteId}`}function Pu(){let t=window.location.pathname.replace(/\/+$/,"")||"/";return t==="/"||t.endsWith("/index.html")}document.readyState==="loading"?document.addEventListener("DOMContentLoaded",()=>fn({boot:Qo,shutdownWidget:Xo})):fn({boot:Qo,shutdownWidget:Xo});})();
