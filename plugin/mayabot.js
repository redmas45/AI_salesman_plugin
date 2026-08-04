(()=>{function Qe(){let t="#5d5fef",e=document.querySelector('meta[name="theme-color"]');if(e&&e.content)t=e.content;else{let f=document.querySelector('button[class*="primary"], .btn-primary, [data-primary]');if(f){let g=window.getComputedStyle(f).backgroundColor;g&&g!=="rgba(0, 0, 0, 0)"&&g!=="transparent"&&(t=g)}}let n=window.matchMedia&&window.matchMedia("(prefers-color-scheme: dark)").matches,r=n?"rgba(24, 24, 27, 0.75)":"rgba(255, 255, 255, 0.85)",o=n?"rgba(255, 255, 255, 0.1)":"rgba(0, 0, 0, 0.08)",i=n?"#f3f4f6":"#111827",a=n?"rgba(255, 255, 255, 0.1)":"rgba(0, 0, 0, 0.05)",c=n?"rgba(0, 0, 0, 0.25)":"#ffffff",u=document.createElement("style");u.textContent=`
    :root {
      --mayabot-primary: ${t};
      --mayabot-surface: ${r};
      --mayabot-border: ${o};
      --mayabot-text: ${i};
      --mayabot-user-bg: ${a};
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
  `,document.head.appendChild(u)}var Kt="site_1",Oo="__AI_";var Ro="aihub:auto-site-id:",Co=["data-aihub-scope","data-site-scope"],xo=["data-site-id","data-aihub-site-id"];function A(t){return String(t||"").trim()}function at(t){return A(t).replace(/\/+$/,"")}function Ze(t,e,n,r=Kt){return No(t,e,n)||vo()||A(r)||Kt}function No(t,e,n){for(let i of xo){let a=A(t?.getAttribute(i));if(a)return a}let r=A(e?.searchParams.get("site"))||A(e?.searchParams.get("site_id"))||A(e?.searchParams.get("shop"));if(r)return r;let o=A(n);return o&&!o.startsWith(Oo)?o:""}function vo(){let t=Lo(),e=`${Ro}${t}`,n=Bo(e);if(n){let c=Fo(n);return c!==n&&Je(e,c),c}let r=A(window.location.host||window.location.hostname||"site"),o=tn(),i=Mo(`${r}${o?`_${o.replace(/\//g,"_")}`:""}`),a=en(`auto_${i}_${Ho(t)}`);return Je(e,a),a}function Lo(){return`${window.location.origin}${tn()}`}function tn(){return Po()}function Po(){for(let e of Co){let n=A(Do()?.getAttribute(e));if(n)return Xe(n)}let t=document.querySelector("meta[name='aihub-site-scope']")?.getAttribute("content");return Xe(t)}function Do(){return document.currentScript}function Xe(t){let e=A(t);if(!e||e==="/")return"";try{let r=new URL(e,window.location.href);if(r.origin===window.location.origin){let[o]=Uo(r.pathname);return o?`/${o}`:""}}catch{}let[n]=e.replace(/^\/+/,"").split("/");return n?`/${n}`:""}function Uo(t=window.location.pathname){return A(t).split("/").map(e=>ko(e).trim()).filter(Boolean)}function ko(t){try{return decodeURIComponent(t)}catch{return String(t||"")}}function Mo(t){return A(t).toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/^_+|_+$/g,"")||"site"}function en(t){return A(t).slice(0,80).replace(/_+$/g,"")||Kt}function Fo(t){let e=A(t);return e.startsWith("auto_")?en(e.toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/^_+|_+$/g,"")):e}function Ho(t){let e=2166136261,n=A(t);for(let r=0;r<n.length;r+=1)e^=n.charCodeAt(r),e=Math.imul(e,16777619);return(e>>>0).toString(36)}function Bo(t){try{return A(window.localStorage.getItem(t))}catch{return""}}function Je(t,e){try{window.localStorage.setItem(t,e)}catch{}}var F=document.currentScript,nn="__AI_PUBLIC_API_URL__",Yo="__AI_DEFAULT_SITE_ID__",rn="mayabot:session:",$o="Maya",jo="AI Salesperson",qo="female";function q(t){return String(t||"").trim()}function Vo(){let t=q(F?.getAttribute("src"));if(!t)return null;try{return new URL(t,window.location.href)}catch{return null}}function zo(t){let e=q(F?.getAttribute("data-api-url"));if(e)return at(e);if(!nn.startsWith("__AI_"))return at(nn);if(t?.origin){let n=t.pathname.replace(/\/mayabot(?:-widget)?\.js$/,"");return at(`${t.origin}${n}`)}return at(window.location.origin)}function Wo(t){let e=`${rn}${t}`;try{let n=window.sessionStorage.getItem(e);if(n)return n;let r=Xt(t);return window.sessionStorage.setItem(e,r),r}catch{return Xt(t)}}function Go(t){let e=Xt(t);try{window.sessionStorage.setItem(`${rn}${t}`,e)}catch{}return e}function Xt(t){let e=window.crypto?.randomUUID?.()||`${Date.now()}-${Math.random().toString(16).slice(2)}`;return`${t}-${e}`.slice(0,120)}var on=Vo(),Qt=Ze(F,on,Yo),d={siteId:Qt,get sessionId(){return Wo(Qt)},rotateSessionId(){return Go(Qt)},apiUrl:zo(on),useWebSocket:q(F?.getAttribute("data-use-websocket")).toLowerCase()==="true",autoGreet:q(F?.getAttribute("data-auto-greet")).toLowerCase()!=="false",brandName:q(F?.getAttribute("data-brand"))||$o,assistantTitle:q(F?.getAttribute("data-assistant-title"))||jo,speechVoiceName:q(F?.getAttribute("data-speech-voice")),speechVoicePreference:q(F?.getAttribute("data-speech-voice-preference"))||qo};function an(){let t=document.createElement("div");return t.id="mayabot-widget",t.innerHTML=`
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
  `,document.body.appendChild(t),t.querySelector(".mayabot-kicker").textContent=d.brandName,t.querySelector(".mayabot-title").textContent=d.assistantTitle,{btn:document.getElementById("mayabot-btn"),chat:document.getElementById("mayabot-chat"),msgs:document.getElementById("mayabot-msgs"),status:document.getElementById("mayabot-status")}}function st(t,e,n){t.chat.classList.add("visible");let r=document.createElement("div");return r.className=`mayabot-msg ${n}`,r.innerText=e,t.msgs.appendChild(r),t.msgs.scrollTop=t.msgs.scrollHeight,r}function Jt(t,e,n){e&&(e.innerText=n,t.msgs.scrollTop=t.msgs.scrollHeight)}var s=Object.freeze({ADD_TO_CART:"ADD_TO_CART",BOOK_APPOINTMENT_REQUEST:"BOOK_APPOINTMENT_REQUEST",BUILD_ITINERARY:"BUILD_ITINERARY",BUILD_LEARNING_PATH:"BUILD_LEARNING_PATH",CAPTURE_LEAD:"CAPTURE_LEAD",CAPTURE_PATIENT_LEAD:"CAPTURE_PATIENT_LEAD",CHECKOUT:"CHECKOUT",CHECKOUT_HANDOFF:"CHECKOUT_HANDOFF",CHECK_APPOINTMENT_AVAILABILITY:"CHECK_APPOINTMENT_AVAILABILITY",CHECK_AVAILABILITY:"CHECK_AVAILABILITY",CHECK_DELIVERY_AVAILABILITY:"CHECK_DELIVERY_AVAILABILITY",CHECK_ELIGIBILITY_SOFT:"CHECK_ELIGIBILITY_SOFT",CHECK_PREREQUISITES:"CHECK_PREREQUISITES",CLEAR_CART:"CLEAR_CART",CLEAR_FILTERS:"CLEAR_FILTERS",CLEAR_HISTORY:"CLEAR_HISTORY",COMPARE_ENTITIES:"COMPARE_ENTITIES",CONTACT_AGENT:"CONTACT_AGENT",FILTER_ENTITIES:"FILTER_ENTITIES",FILTER_PRODUCTS:"FILTER_PRODUCTS",HANDOFF_TO_ADVISOR:"HANDOFF_TO_ADVISOR",HANDOFF_TO_AGENT:"HANDOFF_TO_AGENT",HANDOFF_TO_CLINIC:"HANDOFF_TO_CLINIC",HANDOFF_TO_HUMAN:"HANDOFF_TO_HUMAN",HANDOFF_TO_LAWYER:"HANDOFF_TO_LAWYER",HANDOFF_TO_LICENSED_AGENT:"HANDOFF_TO_LICENSED_AGENT",HANDOFF_TO_RECRUITER:"HANDOFF_TO_RECRUITER",JOIN_WAITLIST:"JOIN_WAITLIST",MATCH_JOBS:"MATCH_JOBS",NAVIGATE_TO:"NAVIGATE_TO",OPEN_CLAIM_FLOW:"OPEN_CLAIM_FLOW",OPEN_CONTACT:"OPEN_CONTACT",OPEN_DISCLOSURE:"OPEN_DISCLOSURE",OPEN_ENTITY_DETAIL:"OPEN_ENTITY_DETAIL",OPEN_LOCATION:"OPEN_LOCATION",OPEN_MAP:"OPEN_MAP",OPEN_POLICY:"OPEN_POLICY",OPEN_PROJECTS:"OPEN_PROJECTS",OPEN_RENEWAL_FLOW:"OPEN_RENEWAL_FLOW",OPEN_SERVICES:"OPEN_SERVICES",OPEN_SYLLABUS:"OPEN_SYLLABUS",OPEN_TELECONSULT:"OPEN_TELECONSULT",REMOVE_FROM_CART:"REMOVE_FROM_CART",REQUEST_APPOINTMENT:"REQUEST_APPOINTMENT",REQUEST_CALLBACK:"REQUEST_CALLBACK",REQUEST_CONSULTATION:"REQUEST_CONSULTATION",REQUEST_COUNSELOR_CALLBACK:"REQUEST_COUNSELOR_CALLBACK",REQUEST_ESTIMATE:"REQUEST_ESTIMATE",REQUEST_SITE_VISIT:"REQUEST_SITE_VISIT",REQUEST_TEST_DRIVE:"REQUEST_TEST_DRIVE",REQUEST_VIEWING:"REQUEST_VIEWING",RUN_AFFORDABILITY_CALCULATOR:"RUN_AFFORDABILITY_CALCULATOR",RUN_CALCULATOR:"RUN_CALCULATOR",RUN_DOM_SEQUENCE:"RUN_DOM_SEQUENCE",SAVE_SEARCH:"SAVE_SEARCH",SCHEDULE_ORDER:"SCHEDULE_ORDER",SEARCH_AVAILABILITY:"SEARCH_AVAILABILITY",SET_LOCATION:"SET_LOCATION",SHOW_COMPARISON:"SHOW_COMPARISON",SHOW_EMERGENCY_NOTICE:"SHOW_EMERGENCY_NOTICE",SHOW_ENTITIES:"SHOW_ENTITIES",SHOW_PRODUCT_DETAIL:"SHOW_PRODUCT_DETAIL",SHOW_PRODUCTS:"SHOW_PRODUCTS",SORT_ENTITIES:"SORT_ENTITIES",SORT_PRODUCTS:"SORT_PRODUCTS",START_APPLICATION:"START_APPLICATION",START_BOOKING:"START_BOOKING",START_ENROLLMENT:"START_ENROLLMENT",START_INTAKE:"START_INTAKE",START_QUOTE:"START_QUOTE",START_TICKET_PURCHASE:"START_TICKET_PURCHASE",UPDATE_CART_QUANTITY:"UPDATE_CART_QUANTITY",UPDATE_PREFERENCES:"UPDATE_PREFERENCES"}),p=Object.freeze({ENTITY_ID:"entity_id",ENTITY_IDS:"entity_ids",MESSAGE:"message",PAGE:"page",PRODUCT_ID:"product_id",PRODUCT_IDS:"product_ids",QUANTITY:"quantity",REASON:"reason",SEARCH_QUERY:"search_query",URL:"url"}),iu=Object.freeze({BLOCKED:"blocked",EXECUTING:"executing",FAILED:"failed",REQUESTED:"requested",SKIPPED:"skipped",SUCCEEDED:"succeeded",UNKNOWN:"unknown"}),v=Object.freeze({KNOWLEDGE_BY_IDS:"/v1/knowledge/by-ids",PRODUCTS_BY_IDS:"/v1/products/by-ids",SHOP:"/v1/shop",SHOP_WS:"/v1/ws/shop",WIDGET_STATUS:"/v1/widget/status"}),L=Object.freeze({AUDIO_CHUNK:"audio_chunk",AUDIO_END:"audio_end",CONFIG:"config",DONE:"done",ERROR:"error",TEXT_CHUNK:"text_chunk",TRANSCRIPT:"transcript"});var sn=new Set(["cart","/cart"]),H="Recommended products",V="Relevant options",ct=Object.freeze({DATA_WAV_PREFIX:"data:audio/wav;base64,",WEBM_FILENAME:"audio.webm",WEBM_MIME_TYPE:"audio/webm"}),cn=Object.freeze({POST:"POST"}),_=Object.freeze({ERROR:"error",PROCESSING:"processing",READY:"ready",RECORDING:"recording"});var un=2400,ln=900,dn=4200,Zt=1,tt=180,pn=3e3,ut=Object.freeze({MAYABOT_ACTION:"mayabot:action"}),fn=2500,mn=45e3;var Ko=["audio/webm;codecs=opus","audio/webm","audio/ogg;codecs=opus","audio/ogg","audio/mp4"],Qo=250,Xo=128;function hn(t,e){let n=null,r=null,o=[],i=!1,a=!1,c=!1;async function u(){if(!(a||i)){a=!0;try{let b=await navigator.mediaDevices.getUserMedia({audio:!0});r=b,c=!1;let R=Jo();n=new MediaRecorder(b,R?{mimeType:R}:void 0),o=[],n.ondataavailable=E=>{E.data.size>0&&o.push(E.data)},n.onstop=async()=>{let E=new Blob(o,{type:n.mimeType||R||ct.WEBM_MIME_TYPE});if(w(),c){c=!1;return}if(E.size<Xo){console.warn("Microphone recording was empty or too short",{size:E.size}),e(_.READY);return}await t(E)},n.onerror=E=>{console.error("Microphone recording failed",E.error||E),i=!1,a=!1,w(),e(_.ERROR,"Recording failed")},n.start(Qo),i=!0,e(_.RECORDING)}catch(b){console.error("Microphone access denied",b),e(_.ERROR,"Mic unavailable")}finally{a=!1}}}function f({discard:b=!1}={}){if(c=b,n&&n.state!=="inactive"){try{n.requestData()}catch{}n.stop(),i=!1,b||e(_.PROCESSING);return}i=!1,w(),b||e(_.PROCESSING)}function g(){a||(i?f():u())}function M(){f({discard:!0})}function w(){r&&(r.getTracks().forEach(b=>b.stop()),r=null)}return{toggle:g,cancel:M}}function Jo(){return!("MediaRecorder"in window)||typeof MediaRecorder.isTypeSupported!="function"?"":Ko.find(t=>MediaRecorder.isTypeSupported(t))||""}var _n="shopify",yn="woocommerce",Zo="custom";function Tt(t){let e=String(t||"").trim();return/^\d+$/.test(e)?e:""}function At(t,e=1){let n=Number(t?.[p.QUANTITY]);return Number.isFinite(n)&&n>0?Math.floor(n):e}async function Q(t,e){return(await fetch(new URL(t,window.location.origin),{method:"POST",headers:{Accept:"application/json","Content-Type":"application/json"},body:JSON.stringify(e),credentials:"same-origin"})).ok}function ti(){return ei()?_n:ni()?yn:Zo}async function gn(t){let e=ti();return e===_n?ri(t):e===yn?oi(t):!1}function ei(){return!!(window.Shopify||document.querySelector('meta[name="shopify-checkout-api-token"]')||document.querySelector('script[src*="cdn.shopify.com"]'))}function ni(){return!!(document.body?.classList?.contains("woocommerce")||window.wc_add_to_cart_params||document.querySelector('link[href*="woocommerce"], script[src*="woocommerce"]'))}async function ri(t){let e=t.parameters||{};if(t.action===s.ADD_TO_CART){let n=Tt(e.variant_id||e.cart_id||e[p.PRODUCT_ID]);return n?Q("/cart/add.js",{items:[{id:n,quantity:At(e)}]}):!1}if(t.action===s.REMOVE_FROM_CART){let n=Tt(e.cart_id||e.variant_id||e[p.PRODUCT_ID]);return n?Q("/cart/change.js",{id:n,quantity:0}):!1}if(t.action===s.UPDATE_CART_QUANTITY){let n=Tt(e.cart_id||e.variant_id||e[p.PRODUCT_ID]);return n?Q("/cart/change.js",{id:n,quantity:At(e,0)}):!1}return t.action===s.CLEAR_CART?Q("/cart/clear.js",{}):t.action===s.CHECKOUT?Et("/checkout"):bn(t)?Et("/cart"):!1}async function oi(t){let e=t.parameters||{};if(t.action===s.ADD_TO_CART){let n=Tt(e.variant_id||e.cart_id||e[p.PRODUCT_ID]);return n?Q("/wp-json/wc/store/cart/add-item",{id:Number(n),quantity:At(e)}):!1}if(t.action===s.REMOVE_FROM_CART){let n=String(e.cart_key||e.key||"").trim();return n?Q("/wp-json/wc/store/cart/remove-item",{key:n}):!1}if(t.action===s.UPDATE_CART_QUANTITY){let n=String(e.cart_key||e.key||"").trim();return n?Q("/wp-json/wc/store/cart/update-item",{key:n,quantity:At(e,0)}):!1}return t.action===s.CHECKOUT?Et("/checkout"):bn(t)?Et("/cart"):!1}function bn(t){return t.action===s.NAVIGATE_TO&&sn.has(t.parameters?.[p.PAGE])}function Et(t){return window.location.href=t,!0}var ii="/v1/widget/action-event";function x(t){return String(t||"").trim()}function ai(t,e){return new URL(t,e).toString()}function si(t){return!t||typeof t!="object"?[]:Object.keys(t).map(e=>x(e)).filter(Boolean).slice(0,20)}function ci(t){if(!t||typeof t!="object")return{};let e={};for(let[n,r]of Object.entries(t).slice(0,20)){let o=x(n).slice(0,80);o&&(typeof r=="boolean"||r===null?e[o]=r:typeof r=="number"?e[o]=Number.isFinite(r)?r:0:e[o]=x(r).slice(0,240))}return e}async function St(t,e,n,r){if(!t||!e||!n?.action)return;let o=JSON.stringify({site_id:e,origin:window.location.origin,url:window.location.href,occurred_at:new Date().toISOString(),request_id:x(n.request_id||n.action_request_id),turn_id:x(n.turn_id),sequence:Number(n.sequence||0),action:x(n.action).toUpperCase(),status:x(r?.status)||"unknown",stage:x(r?.stage),reason:x(r?.reason),duration_ms:Number(r?.duration_ms||0),param_keys:si(n.parameters||n.params),requested_url:x(r?.requested_url),final_url:x(r?.final_url||window.location.href),evidence:ci(r?.evidence)}),i=ai(ii,t);if(!ui(i,o))try{await fetch(i,{method:"POST",headers:{Accept:"application/json","Content-Type":"application/json"},body:o,keepalive:!0})}catch(a){console.warn("[AIHubAdapter] Action execution report failed.",a)}}function ui(t,e){if(typeof navigator>"u"||typeof navigator.sendBeacon!="function"||typeof Blob!="function")return!1;try{return navigator.sendBeacon(t,new Blob([e],{type:"application/json"}))}catch{return!1}}function lt(t){return z(t)[0]||null}function z(t){if(!t||typeof t!="string")return[];let e=[];for(let n of li()){try{e.push(...Array.from(n.querySelectorAll(t)))}catch{return[]}if(e.length>=600)return e.slice(0,600)}return mi(e)}function li(){let t=[],e=new Set,n=[document];for(;n.length&&t.length<60;){let r=n.shift();!r||e.has(r)||(e.add(r),t.push(r),n.push(...di(r)))}return t}function di(t){let e=[];for(let n of pi(t)){n.shadowRoot&&e.push(n.shadowRoot);let r=fi(n);r&&e.push(r)}return e}function pi(t){try{return Array.from(t.querySelectorAll("*"))}catch{return[]}}function fi(t){if(String(t?.tagName||"").toLowerCase()!=="iframe")return null;try{let e=t.contentDocument;return e?.documentElement?e:null}catch{return null}}function mi(t){return Array.from(new Set(t))}var hu=Object.freeze([l("stripe",["stripe","stripe.com","checkout.stripe.com","js.stripe.com"]),l("paypal",["paypal","paypal.com","paypalobjects.com"]),l("razorpay",["razorpay","checkout.razorpay.com"]),l("paytm",["paytm","securegw.paytm.in"]),l("cashfree",["cashfree","cashfree.com"]),l("checkout.com",["checkout.com","cko-session-id"]),l("adyen",["adyen","checkoutshopper"]),l("square",["squareup","squarecdn","square.site"]),l("braintree",["braintree","braintreegateway"]),l("mollie",["mollie","mollie.com"]),l("klarna",["klarna","klarna.com"]),l("afterpay",["afterpay","afterpay.com","clearpay"]),l("payu",["payu","payu.in","payu.com"]),l("paystack",["paystack","paystack.co"]),l("phonepe",["phonepe","phonepe.com"]),l("billdesk",["billdesk","billdesk.com"]),l("authorize.net",["authorize.net","accept.authorize.net"])]),Tn=Object.freeze([l("calendly",["calendly","calendly.com"]),l("acuity",["acuityscheduling","squarespace scheduling"]),l("booksy",["booksy","booksy.com"]),l("zocdoc",["zocdoc","zocdoc.com"]),l("appointlet",["appointlet","appointlet.com"]),l("setmore",["setmore","setmore.com"]),l("cal.com",["cal.com","calcom"]),l("google_calendar",["calendar.google.com","google calendar"]),l("microsoft_bookings",["microsoft bookings","outlook.office365.com/book"]),l("simplybook",["simplybook","simplybook.me"]),l("tidycal",["tidycal","tidycal.com"]),l("savvycal",["savvycal","savvycal.com"]),l("fresha",["fresha","fresha.com"])]),An=Object.freeze([l("google_maps",["google.com/maps","maps.googleapis","maps.google"]),l("mapbox",["mapbox","mapbox.com"]),l("openstreetmap",["openstreetmap","osm.org"]),l("leaflet",["leaflet","leafletjs"]),l("here_maps",["here.com","hereapi","wego.here.com"]),l("bing_maps",["bing.com/maps","virtualearth"]),l("mappls",["mappls","mapmyindia"])]),En=Object.freeze([l("whatsapp",["wa.me","api.whatsapp.com","web.whatsapp.com"]),l("telegram",["t.me/","telegram.me"]),l("messenger",["m.me/","messenger.com/t"]),l("zendesk",["zendesk.com","zdassets.com/hc"]),l("intercom",["intercom.help","intercom.com"]),l("freshchat",["freshchat.com"])]),_u=Object.freeze([l("recaptcha",["recaptcha","g-recaptcha","google.com/recaptcha"]),l("hcaptcha",["hcaptcha","h-captcha"]),l("turnstile",["turnstile","challenges.cloudflare.com"]),l("cloudflare_challenge",["cf-chl","cloudflare challenge"])]);function l(t,e){return{name:t,tokens:e}}function te(t,e,n=10){let r=ee(t);return e.filter(o=>o.tokens.some(i=>r.includes(i))).map(o=>o.name).slice(0,n)}function ee(t){return String(t||"").replace(/\s+/g," ").trim().toLowerCase()}var Sn="a[href], iframe[src]",hi="a[href]",In=new Set(["http:","https:"]),wt=new Set(["mailto:","tel:"]),_i=Object.freeze([p.URL,"href","link","target_url","provider_url","booking_url","appointment_url","calendar_url","map_url","location_url","contact_url"]),On=new Set([s.OPEN_MAP,s.OPEN_LOCATION,s.SET_LOCATION]),Rn=new Set([s.CHECK_APPOINTMENT_AVAILABILITY,s.REQUEST_APPOINTMENT,s.BOOK_APPOINTMENT_REQUEST,s.REQUEST_CONSULTATION,s.REQUEST_SITE_VISIT,s.START_BOOKING]),Cn=new Set([s.OPEN_CONTACT,s.CONTACT_AGENT,s.REQUEST_CALLBACK,s.REQUEST_COUNSELOR_CALLBACK,s.HANDOFF_TO_ADVISOR,s.HANDOFF_TO_AGENT,s.HANDOFF_TO_CLINIC,s.HANDOFF_TO_HUMAN,s.HANDOFF_TO_LAWYER,s.HANDOFF_TO_LICENSED_AGENT,s.HANDOFF_TO_RECRUITER]);function xn(t){let e=Ln(t);return On.has(e)||Rn.has(e)||Cn.has(e)}async function Nn(t){let e=Ln(t);return On.has(e)?ne(t,An,Sn,re):Rn.has(e)?ne(t,Tn,Sn,re):Cn.has(e)?ne(t,En,hi,Ti):!1}function ne(t,e,n,r){let o=yi(t?.parameters||t?.params||{},e,r);if(o)return wn(o);let i=gi(n,e,r);return i?wn(i):!1}function yi(t,e,n){for(let r of _i){let o=vn(t?.[r]);if(o&&n(o,e))return o}return null}function gi(t,e,n){for(let r of z(t)){let o=bi(r);if(!(!o||!n(o,e))&&Ai(o,r,e))return o}return null}function bi(t){return vn(t?.getAttribute?.("href")||t?.getAttribute?.("src"))}function re(t,e){return In.has(t.protocol)&&te(t.href,e).length>0}function Ti(t,e){return wt.has(t.protocol)?!0:re(t,e)}function Ai(t,e,n){if(wt.has(t.protocol))return!0;let r=[t.href,e?.textContent||"",e?.getAttribute?.("aria-label")||"",e?.getAttribute?.("title")||""].join(" ");return te(ee(r),n).length>0}function wn(t){if(wt.has(t.protocol)||t.origin===window.location.origin)return window.location.href=t.href,!0;let e=window.open(t.href,"_blank","noopener,noreferrer");return e?(e.opener=null,!0):(window.location.href=t.href,!0)}function vn(t){let e=String(t||"").trim();if(!e||e.startsWith("#"))return null;try{let n=new URL(e,window.location.href);return In.has(n.protocol)||wt.has(n.protocol)?n:null}catch{return null}}function Ln(t){return String(t?.action||"").trim().toUpperCase()}var Ei=Object.freeze(["title","name"]),Si=Object.freeze(["summary","description","body"]),wi=Object.freeze(["image_url","imageUrl","image","thumbnail"]),Ii=Object.freeze(["url","href","permalink","source_url"]),Oi="knowledge_item",Ri=30;function P(t){return t==null||typeof t=="object"?"":String(t||"").trim()}function Ci(t){let e=new Set;return(Array.isArray(t)?t:[]).map(P).filter(Boolean).filter(n=>e.has(n)||e.size>=Ri?!1:(e.add(n),!0))}function It(t,e){for(let n of e){let r=P(t?.[n]);if(r)return r}return""}function dt(t){return t&&typeof t=="object"&&!Array.isArray(t)?t:{}}function xi(t){let e=Ni([t?.price,t?.amount,t?.premium,t?.premium_min,t?.monthly_premium,t?.annual_premium,t?.min_price,t?.starting_price]),n=P(t?.currency||"INR");return!Number.isFinite(e)||e<=0?"":`${n} ${e.toLocaleString()}`}function Ni(t){for(let e of t){let n=Number(String(e??"").replace(/,/g,""));if(Number.isFinite(n)&&n>0)return n}return 0}function vi(t){return!t||typeof t!="object"?"":t.in_stock===!0?"Available":t.in_stock===!1?"Unavailable":P(t.status||t.availability||"")}function Li(t){let e=P(t);if(!e)return"";try{let n=new URL(e,window.location.origin);return/^https?:$/i.test(n.protocol)?n.origin===window.location.origin?`${n.pathname}${n.search}${n.hash}`:n.toString():""}catch{return""}}function Pi(t){if(!t)return null;let e=P(t.id);if(!e)return null;let n=dt(t.pricing),r=dt(t.availability);return{id:e,externalId:P(t.external_id),entityType:P(t.entity_type||t.category_name)||Oi,title:It(t,Ei)||e,subtitle:P(t.subtitle||t.category_name||t.entity_type),summary:It(t,Si),body:P(t.body),url:Li(It(t,Ii)),imageUrl:It(t,wi),attributes:dt(t.attributes),pricing:n,availability:r,location:dt(t.location),contact:dt(t.contact),displayPrice:xi(n),displayAvailability:vi(r)}}async function oe(t){let e=Ci(t);if(!e.length)return[];let n=new URL(v.KNOWLEDGE_BY_IDS,d.apiUrl);n.searchParams.set("site_id",d.siteId),n.searchParams.set("ids",e.join(","));let r=await fetch(n.toString(),{headers:{Accept:"application/json"}});if(!r.ok)throw new Error("Failed to fetch entities from AI Hub API");let o=(await r.json()).map(Pi).filter(Boolean),i=new Map(o.map(a=>[String(a.id),a]));return e.map(a=>i.get(a)).filter(Boolean)}async function Pn(t){let[e]=await oe([t]);return e?.url||""}function Dn(){if(document.getElementById("mayabot-entity-overlay-styles"))return;let t=document.createElement("style");t.id="mayabot-entity-overlay-styles",t.textContent=`
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
  `,document.head.appendChild(t)}var Di=2,Un=Number.POSITIVE_INFINITY,Ot=Number.NEGATIVE_INFINITY,kn=12,ae=[],se=V;function B(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}function Bn(t){return String(t||"item").replace(/[_-]+/g," ").trim().split(/\s+/).slice(0,Di).join(" ")}function Ui(){Dn();let t=document.getElementById("mayabot-entity-panel");return t||(t=document.createElement("div"),t.id="mayabot-entity-panel",t.setAttribute("aria-live","polite"),t.innerHTML=`
    <div class="mayabot-entity-header">
      <h2 class="mayabot-entity-title">${V}</h2>
      <button class="mayabot-entity-close" type="button" aria-label="Close recommendations">&times;</button>
    </div>
    <div class="mayabot-entity-grid"></div>
  `,t.querySelector(".mayabot-entity-close").addEventListener("click",()=>{t.classList.remove("active")}),document.body.appendChild(t),t)}function ki(t){return t<=1?"count-1":t===2?"count-2":t===3?"count-3":"count-many"}function Mi(t){return t<=1?1:t===2?2:3}function ie(t,e,n=""){let r=(Array.isArray(e)?e:[]).map(c=>String(c?.id??"").trim()).filter(Boolean),o=r.length,i=t.length,a=o>0?"succeeded":"failed";return{status:a,stage:"entity_overlay",reason:n||(a==="succeeded"?"":"no_matching_entities_rendered"),evidence:{requested_entity_count:i,rendered_entity_count:o,missing_entity_count:Math.max(i-o,0),requested_entity_ids:t.slice(0,kn).join(","),rendered_entity_ids:r.slice(0,kn).join(",")}}}function Fi(t){return[t.displayPrice,t.displayAvailability,t.location?.city,t.attributes?.category].map(e=>String(e||"").trim()).filter(Boolean).slice(0,3)}function Hi(t){return t.imageUrl?`
      <div class="mayabot-entity-media">
        <img src="${B(t.imageUrl)}" alt="${B(t.title)}">
      </div>
    `:`
    <div class="mayabot-entity-media">
      <div class="mayabot-entity-badge">${B(Bn(t.entityType))}</div>
    </div>
  `}function Bi(t){let e=Fi(t);return e.length?`
    <div class="mayabot-entity-facts">
      ${e.map(n=>`<span class="mayabot-entity-fact">${B(n)}</span>`).join("")}
    </div>
  `:""}function Yi(t){return t.url?`
    <div class="mayabot-entity-actions">
      <button type="button" data-view-entity="${B(t.id)}">Open</button>
    </div>
  `:""}function Ct(t,e){let n=Ui(),r=n.querySelector(".mayabot-entity-grid"),o=n.querySelector(".mayabot-entity-title"),i=t.length;if(ae=Array.isArray(t)?[...t]:[],se=e||V,n.classList.remove("count-1","count-2","count-3","count-many"),n.classList.add(ki(i)),n.style.setProperty("--mayabot-entity-card-count",String(Mi(i))),o.textContent=se,!i){r.innerHTML='<p class="mayabot-entity-empty">No matching records are currently available.</p>',n.classList.add("active"),Mn();return}r.innerHTML=t.map(a=>`
        <article class="mayabot-entity-card" data-entity-id="${B(a.id)}">
          ${Hi(a)}
          <h3 class="mayabot-entity-name">${B(a.title)}</h3>
          <p class="mayabot-entity-meta">${B(a.subtitle||Bn(a.entityType))}</p>
          <p class="mayabot-entity-summary">${B(a.summary||a.body||"Details are available on the website.")}</p>
          ${Bi(a)}
          ${Yi(a)}
        </article>
      `).join(""),r.querySelectorAll("[data-view-entity]").forEach(a=>{a.addEventListener("click",async()=>{await ce(a.getAttribute("data-view-entity"))})}),n.classList.add("active"),Mn()}function $i(t){if(!t)return!1;try{let e=new URL(t,window.location.origin);return e.origin===window.location.origin?(window.location.href=`${e.pathname}${e.search}${e.hash}`,!0):(window.open(e.toString(),"_blank","noopener,noreferrer"),!0)}catch{return!1}}function Mn(){window.setTimeout(()=>{let t=document.getElementById("mayabot-chat"),e=document.getElementById("mayabot-msgs");e&&(e.innerHTML=""),t&&t.classList.remove("visible")},tt)}async function ce(t){let e=await Pn(t);return $i(e)}async function Yn(t,e=V){let n=ue({[p.ENTITY_IDS]:t});if(!n.length)return Ct([],e),ie([],[],"missing_entity_ids");try{let r=await oe(n);return Ct(r,e),ie(n,r)}catch(r){return console.warn("[AI Hub Widget] Entity overlay failed:",r),Ct([],e),ie(n,[],"entity_overlay_fetch_failed")}}function ue(t){let e=t[p.ENTITY_IDS]||t.ids||t.items||[],n=new Set;return(Array.isArray(e)?e:[]).map(r=>String(r??"").trim()).filter(Boolean).filter(r=>n.has(r)?!1:(n.add(r),!0))}function $n(t={}){if(!ae.length)return!1;let e=String(t.sort_by||t.sortBy||"price_asc").trim().toLowerCase(),n=[...ae].sort((o,i)=>ji(o,i,e)),r=Vi(se,e);return Ct(n,r),!0}function ji(t,e,n){return n==="price_desc"?Rt(e,Ot)-Rt(t,Ot):n==="rating"?Fn(e,Ot)-Fn(t,Ot):n==="newest"?Hn(e)-Hn(t):Rt(t,Un)-Rt(e,Un)}function Rt(t,e){return jn([t?.pricing?.price,t?.pricing?.amount,t?.pricing?.premium,t?.pricing?.premium_min,t?.pricing?.monthly_premium,t?.pricing?.annual_premium,t?.pricing?.min_price,t?.pricing?.starting_price,t?.attributes?.price,t?.attributes?.amount,t?.attributes?.premium,t?.attributes?.monthly_premium,t?.attributes?.annual_premium,t?.displayPrice],e)}function Fn(t,e){return jn([t?.attributes?.rating,t?.attributes?.review_rating,t?.attributes?.stars,t?.availability?.rating],e)}function Hn(t){let e=t?.attributes?.updated_at||t?.attributes?.date||t?.availability?.updated_at||"",n=Date.parse(String(e||""));return Number.isFinite(n)?n:0}function jn(t,e){for(let n of t){let r=qi(n);if(Number.isFinite(r))return r}return e}function qi(t){if(typeof t=="number")return t;let e=String(t??"").replace(/,/g,"").match(/-?\d+(?:\.\d+)?/);return e?Number(e[0]):Number.NaN}function Vi(t,e){let n={price_asc:"sorted low to high",price_desc:"sorted high to low",rating:"sorted by rating",newest:"newest first"};return`${String(t||V).replace(/\s+-\s+sorted.*$/i,"")} - ${n[e]||n.price_asc}`}function qn(t){return t.action===s.SHOW_ENTITIES||t.action===s.COMPARE_ENTITIES||t.action===s.OPEN_ENTITY_DETAIL||t.action===s.SORT_ENTITIES}async function Vn(t){return t.action===s.SHOW_ENTITIES||t.action===s.COMPARE_ENTITIES?zi(t.parameters||{}):t.action===s.OPEN_ENTITY_DETAIL?ce(t.parameters?.[p.ENTITY_ID]||t.parameters?.id):t.action===s.SORT_ENTITIES?$n(t.parameters||{}):!1}function zi(t){return Yn(ue(t),t[p.SEARCH_QUERY]||t.title||V)}var pt="mayabot-handoff-panel",zn="mayabot-handoff-overlay-styles",Wi=Object.freeze(["contact","support","help"]),Gi=Object.freeze(["checkout","cart"]),Qn=new Set([s.CHECKOUT_HANDOFF,s.HANDOFF_TO_ADVISOR,s.HANDOFF_TO_AGENT,s.HANDOFF_TO_CLINIC,s.HANDOFF_TO_HUMAN,s.HANDOFF_TO_LAWYER,s.HANDOFF_TO_LICENSED_AGENT,s.HANDOFF_TO_RECRUITER]),Wn=Object.freeze({[s.CHECKOUT_HANDOFF]:{title:"Checkout needs your confirmation",body:"This step may include payment or a secure checkout page. I can take you there, then you complete the final step yourself.",primary:"Open checkout"},[s.HANDOFF_TO_ADVISOR]:{title:"Advisor handoff",body:"This request needs a qualified advisor. I can open the contact path so the site team can continue.",primary:"Contact advisor"},[s.HANDOFF_TO_AGENT]:{title:"Agent handoff",body:"This step needs an agent or account-specific help. I can open the contact path for follow-up.",primary:"Contact agent"},[s.HANDOFF_TO_CLINIC]:{title:"Clinic handoff",body:"This request needs clinic confirmation. I can open the appointment or contact path for the next step.",primary:"Contact clinic"},[s.HANDOFF_TO_HUMAN]:{title:"Human handoff",body:"This step needs human confirmation. I can open the most relevant contact path.",primary:"Open contact"},[s.HANDOFF_TO_LAWYER]:{title:"Legal handoff",body:"This request needs a legal professional. I can open the consultation or contact path.",primary:"Contact lawyer"},[s.HANDOFF_TO_LICENSED_AGENT]:{title:"Licensed agent handoff",body:"This request needs a licensed agent. I can open the quote or contact path for follow-up.",primary:"Contact agent"},[s.HANDOFF_TO_RECRUITER]:{title:"Recruiter handoff",body:"This request needs recruiter review. I can open the application or contact path.",primary:"Contact recruiter"}});function et(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}function X(t){return String(t||"").trim()}function Ki(){if(document.getElementById(zn))return;let t=document.createElement("style");t.id=zn,t.textContent=`
    #${pt} {
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
    #${pt}.active {
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
      #${pt} {
        bottom: 82px;
        width: min(calc(100vw - 20px), 420px);
      }
    }
  `,document.head.appendChild(t)}function Qi(){Ki();let t=document.getElementById(pt);return t||(t=document.createElement("div"),t.id=pt,t.setAttribute("aria-live","polite"),document.body.appendChild(t),t)}function Xi(){return window.AIHubAdapterRuntime?.config?.adapter?.routes||window.AIHubAdapter?.config?.adapter?.routes||{}}function Ji(t,e){let n=Gn(e[p.URL]||e.path||e.href||e.handoff_flow?.page_url);if(n)return n;let r=Xi(),o=t===s.CHECKOUT_HANDOFF?Gi:Wi;for(let i of o){let a=Gn(r[i]);if(a)return a}return""}function Gn(t){let e=X(t);if(!e)return"";try{let n=new URL(e,window.location.origin);return n.origin!==window.location.origin?"":`${n.pathname}${n.search}${n.hash}`||"/"}catch{return""}}function Zi(t){return Wn[t]||Wn[s.HANDOFF_TO_HUMAN]}function ta(t){return t&&typeof t=="object"?t:{}}function ea(t,e){return X(t.title)||e}function na(t,e,n){return X(e[p.MESSAGE])||X(t.handling)||n}function ra(t,e){return X(e[p.REASON]||e.reason||e.blocked_reason||t.key)}function oa(t){let e=[["Provider",t.provider_label||t.provider],["Boundary",t.automation_boundary],["Recovery",t.recovery],["Evidence",t.evidence],["Page",t.page_url]].filter(([,n])=>X(n));return e.length?`
    <p class="mayabot-handoff-meta">
      ${e.map(([n,r])=>`<span><strong>${et(n)}:</strong> ${et(r)}</span>`).join("")}
    </p>
  `:""}function Kn(t){t.classList.remove("active")}function ia(){window.setTimeout(()=>{let t=document.getElementById("mayabot-chat"),e=document.getElementById("mayabot-msgs");e&&(e.innerHTML=""),t&&t.classList.remove("visible")},tt)}function Xn(t,e={}){let n=X(t).toUpperCase(),r=Zi(n),o=ta(e.handoff_flow),i=Qi(),a=Ji(n,e),c=ea(o,r.title),u=na(o,e,r.body),f=ra(o,e);return i.innerHTML=`
    <div class="mayabot-handoff-body">
      <div class="mayabot-handoff-top">
        <h2 class="mayabot-handoff-title">${et(c)}</h2>
        <button class="mayabot-handoff-close" type="button" aria-label="Close handoff">&times;</button>
      </div>
      <p class="mayabot-handoff-text">${et(u)}</p>
      ${oa(o)}
      ${f?`<p class="mayabot-handoff-reason">${et(f)}</p>`:""}
      <div class="mayabot-handoff-actions">
        <button type="button" class="secondary" data-close-handoff>Close</button>
        ${a?`<button type="button" data-open-handoff>${et(r.primary)}</button>`:""}
      </div>
    </div>
  `,i.querySelector(".mayabot-handoff-close")?.addEventListener("click",()=>Kn(i)),i.querySelector("[data-close-handoff]")?.addEventListener("click",()=>Kn(i)),i.querySelector("[data-open-handoff]")?.addEventListener("click",()=>{window.location.href=a}),i.classList.add("active"),ia(),!0}function Jn(t){return Qn.has(t.action)}function Zn(t){return Xn(t.action,t.parameters||{})}function er(t){return t.action===s.NAVIGATE_TO&&!!rr(t.parameters?.[p.PAGE])}function nr(t){return window.location.href=rr(t.parameters?.[p.PAGE]),!0}function rr(t){let e=String(t||"").trim();if(!e||or(e)||/^https?:\/\//i.test(e))return"";if(e==="home"||e==="/")return"/";let n=aa(e);if(n)return n;let r=e.replace(/^\/+|\/+$/g,"");return r?`/${r}`:"/"}function aa(t){let e=window.AIHubAdapterRuntime?.config?.adapter?.routes||window.AIHubAdapter?.config?.adapter?.routes||{},n=sa(t);for(let r of n){let o=e[r],i=tr(o);if(i)return i}for(let[r,o]of Object.entries(e)){if(!n.includes(le(r)))continue;let i=tr(o);if(i)return i}return""}function sa(t){let e=le(t),n=String(t||"").trim().replace(/^\/+|\/+$/g,"").toLowerCase(),r=n.split("?")[0].split("#")[0].split("/").filter(Boolean).pop()||"";return Array.from(new Set([e,n,le(r)].filter(Boolean)))}function le(t){return String(t||"").trim().toLowerCase().replace(/[^a-z0-9/_\s-]+/g," ").replace(/[_-]+/g," ").replace(/\s+/g," ").trim().replace(/\s+/g,"-")}function tr(t){let e=String(t||"").trim();if(!e||or(e))return"";if(/^https?:\/\//i.test(e))try{let n=new URL(e);return n.origin!==window.location.origin?"":`${n.pathname||"/"}${n.search||""}${n.hash||""}`}catch{return""}return e.startsWith("/")?e:`/${e.replace(/^\/+/,"")}`}function or(t){return/^(?:javascript:|data:|\/\/)/i.test(String(t||"").trim())}function ir(t){let e=t?.params||t?.parameters||{};return{...t||{},action:String(t?.action||"").trim().toUpperCase(),params:e,parameters:e}}var de="AIHubAdapterRuntime",pe="AIHubAdapter";function ca(t){let e=t?.params||t?.parameters||{};return{...t||{},params:e,parameters:e}}function ft(){return!!(window[de]?.executeAction||window[pe]?.handleAction)}async function fe(t){return(await mt(t)).succeeded}async function mt(t){let e=ca(t);if(window[de]?.executeAction){let n=window[de],r=await n.executeAction(e)===!0,o=n.lastActionResult||{};return{succeeded:r,handled:o.handled===!0||r,status:o.status||(r?"ok":"not_handled"),reason:o.reason||"",blocked:o.status==="blocked",disabled:o.status==="disabled"}}if(window[pe]?.handleAction){let n=await window[pe].handleAction(e)===!0;return{succeeded:n,handled:n,status:n?"ok":"not_handled",reason:"",blocked:!1,disabled:!1}}return{succeeded:!1,handled:!1,status:"missing_adapter",reason:"",blocked:!1,disabled:!1}}var ua=Object.freeze([{path:"/api/products?per_page=96",routePrefix:"/product/"},{path:"/api/products",routePrefix:"/product/"},{path:"/api/products.json",routePrefix:""},{path:"/products.json",routePrefix:"/products/"},{path:"/collections/all/products.json",routePrefix:"/products/"}]),la=Object.freeze(["products","data","items","results"]),sr=Object.freeze(["id","product_id","handle","sku"]),cr=Object.freeze(["name","title"]),da=Object.freeze(["url","href","permalink","product_url"]),pa=Object.freeze(["image_url","imageUrl","image_src","imageSrc","image","images","media","thumbnail","thumbnail_url","featured_image","featuredImage","featured_image_url"]),fa=Object.freeze(["brand","vendor"]),ma=Object.freeze(["category","category_name","product_type"]),ha=Object.freeze(["description","summary","body_html"]),_a=Object.freeze(["original_price","compare_at_price","regular_price"]),ur=Object.freeze(["currency","currency_code"]),ya=Object.freeze(["display_price","price_text","formatted_price"]),ga="Unknown Brand",ba="Products",Ta="/",Aa=/^[a-z0-9][a-z0-9-]*$/i,me=null;function N(t){return t==null||typeof t=="object"?"":String(t||"").trim()}function ye(t){return N(t).toLowerCase().replace(/[^a-z0-9]+/g," ").trim()}function lr(t){let e=new Set(["a","am","an","and","ask","asked","did","for","me","not","on","only","please","show","some","the","to","wanna","want","what","with","you","your"]),n=[],r=new Set;for(let o of Ea(ye(t)).split(" ")){let i=Sa(o);i.length<=1||e.has(i)||r.has(i)||(n.push(i),r.add(i))}return n}function Ea(t){return t.replace(/\b(?:i\s+)?did\s+not\s+ask\s+for\s+(?:a\s+|an\s+)?[a-z0-9]+\b/g," ")}function Sa(t){return["phone","phones","mobile","mobiles"].includes(t)?"phone":["book","books"].includes(t)?"books":t}function ge(t,e){return e.map(n=>N(t?.[n])).filter(Boolean)}function D(t,e){return ge(t,e)[0]||""}function xt(t){let e=N(t).replace(/,/g,"");if(!e)return 0;let n=e.match(/-?\d+(?:\.\d+)?/),r=Number(n?n[0]:e);return Number.isFinite(r)?r:0}function wa(t,e){let n=D(t,ya);if(n)return n;let r=D(t,ur).toUpperCase();return e>0&&r?`${r} ${e.toLocaleString()}`:e>0?e.toLocaleString():""}function Ia(t){for(let e of pa){let n=he(t?.[e]);if(n)return n}return""}function he(t){if(!t)return"";if(Array.isArray(t)){for(let e of t){let n=he(e);if(n)return n}return""}if(typeof t=="object"){for(let e of["src","url","image_url","imageUrl","image_src","imageSrc","thumbnail","thumbnail_url","featured_image","featuredImage","featured_image_url"]){let n=he(t[e]);if(n)return n}return""}return Oa(t)}function Oa(t){let e=N(t);if(!e||/^javascript:/i.test(e))return"";if(/^data:image\//i.test(e))return e;try{let n=new URL(e,window.location.origin);return["http:","https:"].includes(n.protocol)?n.toString():""}catch{return""}}function Ra(t){let e=N(t);if(!e)return"";try{let n=new URL(e,window.location.origin);return n.origin!==window.location.origin?"":`${n.pathname}${n.search}${n.hash}`}catch{return""}}function Ca(t,e,n){let r=Ra(D(t,da));return r||(!Aa.test(e)||!/[a-z]/i.test(e)||!n?.routePrefix?"":`${n.routePrefix}${encodeURIComponent(e)}${Ta}`)}function be(t,e={}){if(!t)return null;let n=D(t,sr),r=N(t.handle||t.slug||t.product_handle),o=D(t,cr),i=xt(t.price||t.amount||t.cost),a=xt(D(t,_a));return!n&&!r?null:{id:n,handle:r,name:o,title:N(t.title||o),brand:D(t,fa)||ga,category:D(t,ma)||ba,description:D(t,ha),price:Number.isFinite(i)?i:0,originalPrice:Number.isFinite(a)?a:0,displayPrice:wa(t,i),currency:D(t,ur),rating:xt(t.rating||t.review_rating),reviewCount:xt(t.review_count||t.reviews_count||t.reviews),imageUrl:Ia(t),url:Ca(t,r||n,e)}}function xa(t){return ge(t,sr)}function ar(t){return ge(t,cr).map(ye)}function dr(t,e){let n=N(e);return!!(n&&xa(t).includes(n))}function pr(t,e){let n=lr(e);if(!n.length)return!1;let r=ye([t?.name,t?.title,t?.brand,t?.category,t?.category_name,t?.product_type,t?.description,t?.tags].join(" "));return n.every(o=>r.includes(o)||r.includes(o.replace(/s$/,"")))}function Na(t,e){let n=new Set(ar(e));return ar(t).some(r=>n.has(r))}function va(t,e){return!!(t?.imageUrl&&t.imageUrl===e?.imageUrl)}function La(t){if(Array.isArray(t))return t;for(let e of la){let n=t?.[e];if(Array.isArray(n))return n}return[]}async function Pa(t){try{let e=await fetch(new URL(t.path,window.location.origin),{headers:{Accept:"application/json"}});if(!e.ok)return[];let n=await e.json();return La(n).map(r=>be(r,t)).filter(Boolean)}catch(e){return console.warn(`[AI Hub Widget] Catalog endpoint lookup failed for ${t.path}:`,e),[]}}async function _e(){return me||(me=Promise.all(ua.map(Pa)).then(t=>t.flat())),me}async function Da(t,e=120){if(!lr(t).length)return[];let r=new URL("/v1/products",d.apiUrl);r.searchParams.set("site_id",d.siteId),r.searchParams.set("limit",String(e));try{let o=await fetch(r.toString(),{headers:{Accept:"application/json"}});return o.ok?(await o.json()).map(i=>be(i)).filter(Boolean).filter(i=>pr(i,t)).slice(0,12):[]}catch(o){return console.warn("[AI Hub Widget] Hub product search fallback failed:",o),[]}}async function fr(t,e=""){let n=(Array.isArray(t)?t:[]).map(N).filter(Boolean),r=[],o="",i="";if(n.length)try{r=await mr(n),o="hub_by_ids"}catch(a){i="hub_product_lookup_failed",console.warn("[AI Hub Widget] Hub product ID lookup failed:",a)}if(!r.length&&n.length){let a=await _e();r=n.map(c=>a.find(u=>dr(u,c))).filter(Boolean),r.length&&(o="host_by_ids")}return!r.length&&e&&(r=await Da(e),r.length&&(o="hub_search")),!r.length&&e&&(r=(await _e()).filter(c=>pr(c,e)).slice(0,12),r.length&&(o="host_search")),{products:r,source:o,reason:r.length?"":i||"no_matching_products_rendered"}}async function mr(t){let e=(Array.isArray(t)?t:[]).map(N).filter(Boolean);if(!e.length)return[];let n=new URL(v.PRODUCTS_BY_IDS,d.apiUrl);n.searchParams.set("site_id",d.siteId),n.searchParams.set("ids",e.join(","));let r=await fetch(n.toString(),{headers:{Accept:"application/json"}});if(!r.ok)throw new Error("Failed to fetch products from AI Hub API");let o=(await r.json()).map(a=>be(a)).filter(Boolean),i=new Map(o.map(a=>[String(a.id),a]));return e.map(a=>i.get(a)).filter(Boolean)}async function Nt(t){let e=N(t);if(!e)return"";let[n]=await mr([e]);if(n?.url)return n.url;let r=await _e(),o=r.find(a=>dr(a,e));return o?.url?o.url:n&&r.find(a=>Na(a,n)||va(a,n))?.url||""}var Ua=1,ka=1.08,Ma=300,Fa=Object.freeze(["hannah","sonia","libby","ava","susan","hazel","heera","salli","joanna","amy","emma","olivia","natasha","zira","aria","jenny","samantha","victoria","tessa","moira","karen","female","woman","nova","shimmer","google us english","microsoft aria"]),Y="",vt="",ht=null,Te=0;function J(t){if(!("speechSynthesis"in window)||!("SpeechSynthesisUtterance"in window))return!1;Lt();let e=++Te;Y=t;let n=()=>{if(e!==Te||Y!==t)return!1;try{let r=new SpeechSynthesisUtterance(t),o=Ha(window.speechSynthesis.getVoices());return o?(o&&(r.voice=o),r.rate=Ua,r.pitch=ka,r.onstart=hr,r.onend=hr,Lt(),window.speechSynthesis.cancel(),window.speechSynthesis.resume(),window.speechSynthesis.speak(r),!0):(Y="",!1)}catch{return!1}};return window.speechSynthesis.getVoices().length>0?n():(window.speechSynthesis.onvoiceschanged=n,ht=window.setTimeout(()=>{ht=null,n()},Ma),!0)}function Pt(){Y&&J(Y)}function _r(){try{return!!Y||!!window.speechSynthesis?.speaking||!!window.speechSynthesis?.pending}catch{return!!Y}}function Dt(){Te+=1,Lt(),Y="",vt="";try{window.speechSynthesis?.cancel()}catch{}}function Ha(t){if(!Array.isArray(t)||t.length===0)return null;let e=Ba(t)||Ya(t);return e&&(vt=e.name),e}function Ba(t){if(vt){let n=t.find(r=>r.name===vt);if(n)return n}let e=String(d.speechVoiceName||"").toLowerCase();return e&&t.find(n=>n.name.toLowerCase()===e)||null}function Ya(t){return d.speechVoicePreference.toLowerCase()!=="female"?t.find(e=>e.default)||t[0]:t.find(e=>Fa.some(n=>e.name.toLowerCase().includes(n)))||null}function hr(){Lt(),Y=""}function Lt(){ht&&window.clearTimeout(ht),ht=null,window.speechSynthesis&&(window.speechSynthesis.onvoiceschanged=null)}var $a=["data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='320' height='240' viewBox='0 0 320 240'%3E","%3Crect width='320' height='240' fill='%23f1f2ee'/%3E","%3Cpath d='M98 156h124l-31-40-25 30-17-22-51 32Z' fill='%23c8c3ba'/%3E","%3Ccircle cx='117' cy='95' r='17' fill='%23d8d3ca'/%3E","%3Ctext x='160' y='198' text-anchor='middle' fill='%23686660' font-family='Arial,sans-serif' font-size='16'%3EImage pending%3C/text%3E","%3C/svg%3E"].join(""),yr=12,ja=4,qa=6,Va=700,kt=[],Ee=H,Mt=new Map,Se=!1;function za(){try{Dt()}catch{}}function W(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}function Wa(){if(document.getElementById("mayabot-product-overlay-styles"))return;let t=document.createElement("style");t.id="mayabot-product-overlay-styles",t.textContent=`
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
  `,document.head.appendChild(t)}function Ga(){Wa();let t=document.getElementById("mayabot-product-panel");return t||(t=document.createElement("div"),t.id="mayabot-product-panel",t.setAttribute("aria-live","polite"),t.setAttribute("role","dialog"),t.setAttribute("tabindex","-1"),t.innerHTML=`
    <div class="mayabot-product-header">
      <h2 class="mayabot-product-title">${H}</h2>
      <button class="mayabot-product-close" type="button" aria-label="Close recommendations">&times;</button>
    </div>
    <div class="mayabot-compare-speak" role="group" aria-label="Speak comparison">
      <p>Would you like me to speak all the comparison points?</p>
      <button type="button" class="mayabot-compare-yes">Yes</button>
      <button type="button" class="mayabot-compare-no secondary">No</button>
    </div>
    <div class="mayabot-product-grid"></div>
  `,t.querySelector(".mayabot-product-close").addEventListener("click",gr),t.querySelector(".mayabot-compare-yes").addEventListener("click",()=>br(!0)),t.querySelector(".mayabot-compare-no").addEventListener("click",()=>br(!1)),t.addEventListener("keydown",e=>{e.key==="Escape"&&gr()}),document.body.appendChild(t),t)}function gr(){let t=document.getElementById("mayabot-product-panel");t&&(t.classList.remove("active","ask-speak"),za())}function br(t){let e=document.getElementById("mayabot-product-panel");if(e&&e.classList.remove("ask-speak"),Se=!0,t){let n=Qa(kt);n&&J(n)}}function Ka(t,e){let n=document.getElementById("mayabot-product-panel");if(!n)return;if(!(e&&Array.isArray(t)&&t.length>=2)||Se){n.classList.remove("ask-speak");return}n.classList.add("ask-speak"),window.setTimeout(()=>n.querySelector(".mayabot-compare-yes")?.focus(),0)}function Qa(t){let e=[];for(let n of(t||[]).slice(0,ja)){let o=(Mt.get(String(n.id))||[]).slice(0,qa).map(a=>`${a.label}: ${a.value}`).join(", "),i=n.name||n.title||"This product";e.push(o?`${i}. ${o}.`:`${i}.`)}return e.join(" ").slice(0,Va)}async function Xa(t){let e={action:s.ADD_TO_CART,params:{[p.PRODUCT_ID]:t,[p.QUANTITY]:Zt},parameters:{[p.PRODUCT_ID]:t,[p.QUANTITY]:Zt}};ft()&&await fe(e)||window.dispatchEvent(new CustomEvent(ut.MAYABOT_ACTION,{detail:e}))}async function Ja(t){try{let n=await Nt(t);if(n){window.location.href=n;return}}catch(n){console.warn("[AI Hub Widget] Product detail URL lookup failed:",n)}let e={action:s.SHOW_PRODUCT_DETAIL,params:{[p.PRODUCT_ID]:t},parameters:{[p.PRODUCT_ID]:t}};ft()&&await fe(e)||window.dispatchEvent(new CustomEvent(ut.MAYABOT_ACTION,{detail:e}))}function Za(t){return t<=1?"count-1":t===2?"count-2":t===3?"count-3":"count-many"}function ts(t){return t<=1?1:t===2?2:3}function es(t){let e=new Set;return(Array.isArray(t)?t:[]).map(n=>String(n??"").trim()).filter(Boolean).filter(n=>e.has(n)?!1:(e.add(n),!0))}function Ae(t,e,n="",r={}){let o=(Array.isArray(e)?e:[]).map(u=>String(u?.id??"").trim()).filter(Boolean),i=o.length,a=t.length,c=i>0?"succeeded":"failed";return{status:c,stage:"product_overlay",reason:n||(c==="succeeded"?"":"no_matching_products_rendered"),evidence:{requested_product_count:a,rendered_product_count:i,missing_product_count:Math.max(a-i,0),requested_product_ids:t.slice(0,yr).join(","),rendered_product_ids:o.slice(0,yr).join(","),lookup_source:r.source||"",search_query:r.searchQuery||""}}}function ns(t){let e=String(t?.displayPrice||"").trim();if(e)return e;let n=Number(t?.price||0);return Number.isFinite(n)&&n>0?n.toLocaleString():"Price unavailable"}var rs=6,os=24,is=120;function as(t){let e=new Map;return Array.isArray(t)&&t.forEach(n=>{if(!n||typeof n!="object")return;let r=String(n.product_id||"").trim();if(!r||!Array.isArray(n.facts))return;let o=n.facts.filter(i=>i&&typeof i=="object"&&i.label&&i.value).slice(0,rs).map(i=>({label:String(i.label).slice(0,os),value:String(i.value).slice(0,is)}));o.length&&e.set(r,o)}),e}function ss(t){let e=Mt.get(String(t));return!e||!e.length?"":`<dl class="mayabot-product-facts">${e.map(r=>`<div class="mayabot-fact"><dt>${W(r.label)}</dt><dd>${W(r.value)}</dd></div>`).join("")}</dl>`}function Ut(t,e){let n=Ga(),r=n.querySelector(".mayabot-product-grid"),o=n.querySelector(".mayabot-product-title"),i=t.length;if(kt=Array.isArray(t)?[...t]:[],Ee=e||H,n.classList.remove("count-1","count-2","count-3","count-many"),n.classList.add(Za(i)),n.style.setProperty("--mayabot-card-count",String(ts(i))),o.textContent=Ee,!i){r.innerHTML='<p class="mayabot-product-empty">No matching products are currently available.</p>',n.classList.add("active");return}r.innerHTML=t.map(a=>{let c=W(a.id);return`
        <article class="mayabot-product-card" data-product-id="${c}">
          <img class="mayabot-product-image" src="${W(a.imageUrl||$a)}" alt="${W(a.name)}">
          <h3 class="mayabot-product-name">${W(a.name||a.title||"Product")}</h3>
          <p class="mayabot-product-meta">${W(a.brand)} - ${W(ns(a))}</p>
          ${ss(a.id)}
          <div class="mayabot-product-actions">
            <button type="button" data-add="${c}">Add</button>
            <button type="button" class="secondary" data-view="${c}">View</button>
          </div>
        </article>
      `}).join(""),r.querySelectorAll("[data-add]").forEach(a=>{a.addEventListener("click",async()=>{await Xa(a.getAttribute("data-add"))})}),r.querySelectorAll("[data-view]").forEach(a=>{a.addEventListener("click",async()=>{await Ja(a.getAttribute("data-view"))})}),n.classList.add("active"),t.length>0&&cs()}function cs(){window.setTimeout(()=>{let t=document.getElementById("mayabot-chat"),e=document.getElementById("mayabot-msgs");e&&(e.innerHTML=""),t&&t.classList.remove("visible")},tt)}async function Ar(t,e=H,n={}){let r=es(t),o=String(n.searchQuery||"").trim();Mt=as(n.comparisonFacts);let i=Mt.size>0;if(Se=!1,!r.length&&!o)return Ut([],e),Ae([],[],"missing_product_ids");try{let{products:a,source:c,reason:u}=await fr(r,o);return Ut(a,e),Ka(a,i),Ae(r,a,u,{source:c,searchQuery:o})}catch(a){return console.warn("[AI Hub Widget] Product overlay failed:",a),Ut([],e),Ae(r,[],"product_overlay_fetch_failed",{searchQuery:o})}}function Er(t={}){if(!kt.length)return!1;let e=String(t.sort_by||t.sortBy||"price_asc").trim().toLowerCase(),n=[...kt].sort((r,o)=>us(r,o,e));return Ut(n,ls(Ee,e)),!0}function us(t,e,n){return n==="price_desc"?nt(e.price,Number.NEGATIVE_INFINITY)-nt(t.price,Number.NEGATIVE_INFINITY):n==="rating"?nt(e.rating||e.review_rating,Number.NEGATIVE_INFINITY)-nt(t.rating||t.review_rating,Number.NEGATIVE_INFINITY):n==="newest"?Tr(e)-Tr(t):nt(t.price,Number.POSITIVE_INFINITY)-nt(e.price,Number.POSITIVE_INFINITY)}function nt(t,e){let n=String(t??"").replace(/,/g,"").match(/-?\d+(?:\.\d+)?/);if(!n)return e;let r=Number(n[0]);return Number.isFinite(r)?r:e}function Tr(t){let e=t?.updated_at||t?.created_at||t?.date||"",n=Date.parse(String(e||""));return Number.isFinite(n)?n:0}function ls(t,e){let n={price_asc:"sorted low to high",price_desc:"sorted high to low",rating:"sorted by rating",newest:"newest first"};return`${String(t||H).replace(/\s+-\s+sorted.*$/i,"")} - ${n[e]||n.price_asc}`}function wr(t){return t.action===s.SHOW_PRODUCTS||t.action===s.SHOW_COMPARISON||t.action===s.SHOW_PRODUCT_DETAIL||t.action===s.SORT_PRODUCTS}async function Ir(t){return t.action===s.SHOW_COMPARISON?Sr(t.parameters||{},"Product comparison",{syncListing:!1,comparisonFacts:(t.parameters||{}).comparison}):t.action===s.SHOW_PRODUCTS?Sr(t.parameters||{},H):t.action===s.SHOW_PRODUCT_DETAIL?fs(t.parameters||{}):t.action===s.SORT_PRODUCTS?Er(t.parameters||{}):!1}async function Sr(t,e=H,n={}){let r=Array.isArray(t[p.PRODUCT_IDS])?t[p.PRODUCT_IDS]:[],o=ps(t),a=n.syncListing!==!1?await ds(o):{succeeded:!1,handled:!1,status:"skipped",stage:"product_display_sync",reason:"comparison_overlay"},c=await Ar(r,t.title||o||e,{searchQuery:o,comparisonFacts:n.comparisonFacts}),u={...c.evidence||{},listing_sync_status:a.status||"",listing_sync_stage:a.stage||"",listing_sync_reason:a.reason||""};return c.status!=="succeeded"?{...c,evidence:u}:o&&a.handled&&!a.succeeded?{status:"failed",stage:"product_display_sync",reason:a.reason||a.status||"listing_sync_failed",evidence:u}:{...c,stage:a.succeeded?"product_display_sync":c.stage,evidence:u}}async function ds(t){let e=Or(t);return e?mt({action:s.FILTER_PRODUCTS,params:{[p.SEARCH_QUERY]:e,query:e,q:e}}):{succeeded:!1,handled:!1,status:"skipped",stage:"product_display_sync",reason:"missing_search_query"}}function ps(t){return Or(t[p.SEARCH_QUERY]||t.search||t.query||t.q||"")}function Or(t){return String(t||"").trim()}async function fs(t){let e="";try{e=await Nt(t[p.PRODUCT_ID])}catch(n){return console.warn("[AI Hub Widget] Product detail URL lookup failed:",n),!1}return e?(window.location.href=e,!0):!1}var we="stop_action_fallback",ms=new Set([s.SHOW_PRODUCTS,s.SHOW_COMPARISON,s.SHOW_PRODUCT_DETAIL,s.SORT_PRODUCTS]);function Rr(t){return ft()&&!ms.has(t.action)}async function Cr(t){let e=await mt(t);return e.succeeded?!0:e.blocked||e.disabled?we:!1}function xr(t){return window.dispatchEvent(new CustomEvent(ut.MAYABOT_ACTION,{detail:t})),{status:"requested",stage:"browser_event",reason:"event_dispatched_without_confirmation"}}var hs=12,_s=8,ys=80,Nr=Object.freeze([["data-entity-id",""],["data-product-id","product"],["data-listing-id","listing"],["data-offer-id","offer"],["data-plan-id","plan"],["data-item-id",""]]),gs="data-entity-type",bs="entity",vr=Object.freeze(["sort","sort_by","sortby","orderby","order_by","order"]),Ts=Object.freeze(["page","p","offset","cursor","q","query","search","token","session","email","phone","name","address","utm_source","utm_medium","utm_campaign"]),As=Object.freeze([["price","[data-price], [itemprop='price'], .price"],["rating","[data-rating], [itemprop='ratingValue'], .rating"],["availability","[data-availability], [itemprop='availability'], .availability, .stock"]]);function U(t){return String(t||"").replace(/\s+/g," ").trim().slice(0,ys)}function Es(t){if(!t||typeof t.getBoundingClientRect!="function")return!1;let e=t.getBoundingClientRect();if(e.width<=0||e.height<=0)return!1;let n=t.ownerDocument?.defaultView,r=n?.getComputedStyle?.(t);if(r&&(r.visibility==="hidden"||r.display==="none"))return!1;let o=t.ownerDocument?.documentElement,i=Number(n?.innerWidth||o?.clientWidth||0),a=Number(n?.innerHeight||o?.clientHeight||0);return i>0&&a>0&&e.bottom>0&&e.right>0&&e.top<a&&e.left<i}function Ss(t){for(let[e,n]of Nr){let r=U(t.getAttribute(e));if(r)return{id:r,impliedType:n}}return null}function ws(t,e){return U(t.getAttribute(gs)).toLowerCase()||e||bs}function Is(t){let e=t.querySelector?.("h1, h2, h3, h4, [data-entity-name], [itemprop='name']");return U(e?.textContent||t.getAttribute("aria-label")||t.getAttribute("title"))}function Os(t){let e=t.matches?.("a[href]")?t:t.querySelector?.("a[href]");return Ps(e?.href||"")}function Rs(t){let e={};for(let[n,r]of As){let o=t.querySelector?.(r);if(!o)continue;let i=U(o.getAttribute?.("content")||o.getAttribute?.(`data-${n}`)||o.textContent);i&&(e[n]=i)}return e}function Cs(){return Nr.map(([t])=>`[${t}]`).join(",")}function xs(){let t=new Set,e=[];for(let n of z(Cs())){if(e.length>=hs)break;let r=Ss(n);!r||t.has(r.id)||!Es(n)||(t.add(r.id),e.push({id:r.id,entity_type:ws(n,r.impliedType),label:Is(n),route:Os(n),facts:Rs(n)}))}return e}function Ns(){let t=Lr();if(!t)return{};let e={};for(let[n,r]of t.entries()){let o=n.toLowerCase();if(!(Ts.includes(o)||vr.includes(o))){if(Object.keys(e).length>=_s)break;e[U(n)]=U(r)}}return e}function vs(){let t=Lr();for(let n of vr){let r=U(t?.get?.(n));if(r)return r}let e=z("select[name*='sort' i], select[id*='sort' i]")[0];return U(e?.value)}function Ls(){try{return{path:U(window.location.pathname)||"/",search:U(window.location.search)}}catch{return{path:"",search:""}}}function Ft(){return{route:Ls(),filters:Ns(),sort:vs(),visible_entities:xs()}}function Lr(){try{return new URLSearchParams(window.location.search)}catch{return null}}function Ps(t){if(!t)return"";try{let e=new URL(t,window.location.origin);return e.origin!==window.location.origin?"":`${e.pathname}${e.search}`||"/"}catch{return""}}var ul=Object.freeze(["CHECKOUT","CLEAR_CART","REMOVE_FROM_CART","UPDATE_CART_QUANTITY","CLEAR_HISTORY","SUBMIT_PAYMENT","PLACE_ORDER"]);var y=Object.freeze({DISPLAY:"display",NAVIGATION:"navigation",DETAIL:"detail",FILTER:"filter",SORT:"sort",CART:"cart",NONE:"none"}),Ds=1200,Us=60,ks=Object.freeze({SHOW_PRODUCTS:y.DISPLAY,SHOW_ENTITIES:y.DISPLAY,SHOW_COMPARISON:y.DISPLAY,COMPARE_ENTITIES:y.DISPLAY,NAVIGATE_TO:y.NAVIGATION,SHOW_PRODUCT_DETAIL:y.DETAIL,OPEN_ENTITY_DETAIL:y.DETAIL,FILTER_PRODUCTS:y.FILTER,CLEAR_FILTERS:y.FILTER,SORT_PRODUCTS:y.SORT,SORT_ENTITIES:y.SORT,ADD_TO_CART:y.CART,REMOVE_FROM_CART:y.CART,UPDATE_CART_QUANTITY:y.CART,CLEAR_CART:y.CART}),Ms="[data-cart-count], [data-testid='cart-count'], .cart-count, #cart-count";function Dr(t){return ks[String(t||"").toUpperCase()]||y.NONE}function Re(){let t=Ft();return{path:t.route.path,search:t.route.search,filters:t.filters,sort:String(t.sort||"").toLowerCase(),visibleIds:t.visible_entities.map(e=>String(e.id)),cartCount:Fs()}}function Fs(){let t=document.querySelector(Ms);if(!t)return null;let e=t.getAttribute("data-cart-count")??t.textContent,n=Number.parseInt(String(e||"").replace(/[^\d-]/g,""),10);return Number.isFinite(n)?n:null}function Ur(t){let e=[];for(let n of["product_ids","entity_ids"])Array.isArray(t[n])&&e.push(...t[n].map(String));for(let n of["product_id","entity_id"])t[n]&&e.push(String(t[n]));return e}function _t(t){let e=String(t||"").split("?")[0].split("#")[0];return e.length>1?e.replace(/\/+$/,""):e}function Ie(t){return String(t||"").trim().toLowerCase().replace(/[^a-z0-9/_\s-]+/g," ").replace(/[_-]+/g," ").replace(/\s+/g," ").trim().replace(/\s+/g,"-")}function Pr(t){let e=String(t||"").trim();if(!e||/^(?:javascript:|data:|\/\/)/i.test(e))return"";try{let n=new URL(e,window.location.origin);return n.origin!==window.location.origin?"":_t(n.pathname||"/")}catch{return""}}function Hs(t){let e=String(t||"").trim();if(!e)return"";if(e==="/"||Ie(e)==="home")return"/";let n=window.AIHubAdapterRuntime?.config?.adapter?.routes||window.AIHubAdapter?.config?.adapter?.routes||{},r=Ie(e);for(let[o,i]of Object.entries(n)){if(Ie(o)!==r)continue;let a=Pr(i);if(a)return a}return e.startsWith("/")||/^https?:\/\//i.test(e)?Pr(e):_t(`/${r}`)}function Bs(t,e){let n=Ur(t);return n.length?n.filter(o=>!e.visibleIds.includes(o)).length?{satisfied:!1,reason:"requested_records_not_visible"}:{satisfied:!0,reason:""}:e.visibleIds.length>0?{satisfied:!0,reason:""}:{satisfied:!1,reason:"nothing_visible"}}function Ys(t,e,n){let r=Hs(t.page),o=_t(e.path);return r&&o===r?{satisfied:!0,reason:""}:!r&&o!==_t(n.path)?{satisfied:!0,reason:""}:r&&o!==_t(n.path)?{satisfied:!1,reason:"wrong_route"}:{satisfied:!1,reason:"route_unchanged"}}function $s(t,e,n){let r=Ur(t)[0];return r?`${e.path}${e.search}`.includes(r)?{satisfied:!0,reason:""}:e.visibleIds.includes(r)&&e.path!==n.path?{satisfied:!0,reason:""}:{satisfied:!1,reason:"record_not_opened"}:{satisfied:!1,reason:"no_record_requested"}}function js(t,e,n){if(t==="CLEAR_FILTERS")return Object.keys(n.filters).length===0?{satisfied:!0,reason:""}:{satisfied:!1,reason:"filters_still_active"};let r=new Map(Object.entries(n.filters).map(([u,f])=>[u.toLowerCase(),Oe(f)])),o=e.filters&&typeof e.filters=="object"?e.filters:e,i=new Set(["product_ids","entity_ids","page","search_query","query","q","request_id"]),a=Object.entries(o||{}).filter(([u,f])=>!i.has(u.toLowerCase())&&Oe(f));return a.length?a.every(([u,f])=>{let g=r.get(u.toLowerCase());return g!==void 0&&g===Oe(f)})?{satisfied:!0,reason:""}:{satisfied:!1,reason:"filter_value_mismatch"}:r.size>0?{satisfied:!0,reason:""}:{satisfied:!1,reason:"no_filter_observed"}}function Oe(t){return(Array.isArray(t)?t:[t]).map(n=>String(n??"").trim().toLowerCase()).filter(Boolean).sort().join(",")}function qs(t,e,n){let r=String(t.sort_by||"").toLowerCase();return r&&e.sort&&e.sort.includes(r.split("_")[0])?{satisfied:!0,reason:""}:e.visibleIds.join(",")!==n.visibleIds.join(",")?{satisfied:!0,reason:""}:{satisfied:!1,reason:"order_unchanged"}}function Vs(t,e,n){if(n.cartCount===null||e.cartCount===null)return{satisfied:!1,reason:"cart_state_unobservable"};let r=e.cartCount>n.cartCount,o=e.cartCount<n.cartCount;return t==="ADD_TO_CART"?r?{satisfied:!0,reason:""}:{satisfied:!1,reason:"cart_unchanged"}:t==="REMOVE_FROM_CART"?o?{satisfied:!0,reason:""}:{satisfied:!1,reason:"cart_unchanged"}:t==="CLEAR_CART"?e.cartCount===0?{satisfied:!0,reason:""}:{satisfied:!1,reason:"cart_not_empty"}:e.cartCount!==n.cartCount?{satisfied:!0,reason:""}:{satisfied:!1,reason:"cart_unchanged"}}function zs(t,e,n){let r=String(t?.action||"").toUpperCase(),o=t?.parameters||t?.params||{},i=Dr(r);return i===y.DISPLAY?Bs(o,e):i===y.NAVIGATION?Ys(o,e,n):i===y.DETAIL?$s(o,e,n):i===y.FILTER?js(r,o,e):i===y.SORT?qs(o,e,n):i===y.CART?Vs(r,e,n):{satisfied:!0,reason:"no_postcondition"}}async function kr(t,e){let n=Dr(t?.action);if(n===y.NONE)return{family:n,verified:!0,reason:"no_postcondition"};let r=Date.now()+Ds,o={satisfied:!1,reason:"not_observed"};for(;Date.now()<r&&(o=zs(t,Re(),e),!o.satisfied);)await Ws(Us);return{family:n,verified:o.satisfied,reason:o.reason}}function Ws(t){return new Promise(e=>window.setTimeout(e,t))}function yt(t){return t?(Yr(t),Mr(t,"down"),Mr(t,"up"),typeof t.click=="function"?t.click():$r(t,"click"),Xs(t),!0):!1}function Hr(t,e){return t?(Yr(t),Gs(t,Bt(e)),Ks(t),!0):!1}function Br(t){if(!t)return!1;let e=Bt(t.tagName).toLowerCase()==="form"?t:t.closest?.("form");return e&&typeof e.requestSubmit=="function"?(e.requestSubmit(),!0):yt(t)}function Yr(t){try{t.scrollIntoView?.({behavior:"smooth",block:"center",inline:"center"})}catch{}typeof t.focus=="function"&&t.focus({preventScroll:!0})}function Gs(t,e){if(Js(t)){t.textContent=e;return}let n=Object.getPrototypeOf(t),r=Object.getOwnPropertyDescriptor(n,"value");if(r?.set){r.set.call(t,e);return}t.value=e}function Ks(t){Fr(t,"beforeinput"),Fr(t,"input"),t.dispatchEvent(new Event("change",{bubbles:!0}))}function Mr(t,e){Qs(t,`pointer${e}`),$r(t,`mouse${e}`)}function Qs(t,e){typeof PointerEvent=="function"&&t.dispatchEvent(new PointerEvent(e,{bubbles:!0,cancelable:!0,pointerType:"mouse",isPrimary:!0}))}function $r(t,e){t.dispatchEvent(new MouseEvent(e,{bubbles:!0,cancelable:!0,view:window}))}function Fr(t,e){if(typeof InputEvent=="function"){t.dispatchEvent(new InputEvent(e,{bubbles:!0,cancelable:!0,inputType:"insertText"}));return}t.dispatchEvent(new Event(e,{bubbles:!0,cancelable:!0}))}function Xs(t){let e=Bt(t.getAttribute?.("role")).toLowerCase();["button","link","menuitem","option","tab"].includes(e)&&(Ht(t,"keydown","Enter"),Ht(t,"keyup","Enter"),(e==="button"||e==="tab")&&(Ht(t,"keydown"," "),Ht(t,"keyup"," ")))}function Ht(t,e,n){t.dispatchEvent(new KeyboardEvent(e,{bubbles:!0,cancelable:!0,key:n}))}function Js(t){let e=Bt(t?.getAttribute?.("role")).toLowerCase();return!!(t?.isContentEditable||!("value"in t)&&["searchbox","textbox"].includes(e))}function Bt(t){return String(t||"").trim()}var T=Object.freeze({searchForm:"search-form",searchInput:"search-input",searchSubmit:"search-submit",searchResults:"search-results",addToCart:"add-to-cart",cartButton:"cart-button",cartLineItem:"cart-line-item",navLink:"nav-link"}),Zs="data-aihub-nav",jt=4e3,tc=1500,ec=80,qt=t=>`[data-aihub-role="${t}"]`,I=t=>lt(qt(t)),Ne=t=>z(qt(t));function ve(){return!!(I(T.searchForm)||I(T.searchInput)||I(T.searchSubmit))}function Le(){return!!I(T.addToCart)}function Pe(){return Ne(T.navLink).length>0}function G(t){return String(t??"").trim()}function jr(t){return window.CSS?.escape?window.CSS.escape(t):G(t).replace(/["\\]/g,"\\$&")}async function gt(t,e){let n=Date.now()+e;for(;;){let r=t();if(r)return r;if(Date.now()>=n)return null;await new Promise(o=>window.setTimeout(o,ec))}}function nc(t){try{let e=`${window.location.pathname}${window.location.search}`.toLowerCase();return e.includes(encodeURIComponent(t).toLowerCase())||e.includes(t.toLowerCase())}catch{return!1}}async function qr(t){let e=G(t);if(!ve())return null;if(!e)return cc("host_search","empty_query");let n=I(T.searchInput);if(!n){let u=I(T.searchSubmit)||I(T.searchForm);u&&yt(u),n=await gt(()=>I(T.searchInput),tc)}if(!n)return $("host_search","search_input_unavailable");Hr(n,e);let r=n.closest?.("form")||I(T.searchForm);Br(r||I(T.searchSubmit)||n);let o=await gt(()=>{let u=I(T.searchResults);return!u||u.getAttribute("data-results-loading")==="true"?null:u},jt);if(!o)return sc("host_search","results_not_settled");let i=Number(o.getAttribute("data-result-count")),a={result_count:Number.isFinite(i)?i:null,query:o.getAttribute("data-query")||"",route:`${window.location.pathname}${window.location.search}`,route_reflects_query:nc(e)};return a.route_reflects_query||a.query.toLowerCase().includes(e.toLowerCase())?o.getAttribute("data-results-empty")==="true"||a.result_count===0?{handled:!0,status:"succeeded",self_verified:!0,stage:"host_search",reason:"no_results",evidence:a}:{handled:!0,status:"succeeded",self_verified:!0,stage:"host_search",evidence:a}:$("host_search","query_not_reflected",a)}function Ce(){let t=I(T.cartButton)||lt("[data-cart-count]");if(!t)return null;let e=Number(t.getAttribute("data-cart-count"));return Number.isFinite(e)?e:null}function xe(){return Ne(T.cartLineItem).map(t=>G(t.getAttribute("data-product-id"))).filter(Boolean)}function rc(t){let e=G(t);if(e){let n=lt(`${qt(T.addToCart)}[data-product-id="${jr(e)}"]`);if(n)return n;let o=lt(`[data-product-id="${jr(e)}"]`)?.querySelector?.(qt(T.addToCart));return o||null}return I(T.addToCart)}function oc(t){return!!t.disabled||t.getAttribute("aria-disabled")==="true"}async function Vr(t){if(!Le())return null;let e=G(t?.product_id||t?.entity_id),n=rc(e);if(!n)return $("host_add_to_cart",e?"product_not_on_page":"add_control_missing",{product_id:e});if(oc(n))return $("host_add_to_cart","add_control_disabled",{product_id:e});let r=Ce(),o=xe();yt(n);let i=await gt(()=>{let u=Ce(),f=xe(),g=r!=null&&u!=null&&u>r,M=e&&f.includes(e)&&!o.includes(e),w=f.length>o.length;return g||M||w?{afterCount:u,lines:f}:null},jt),a=Ce(),c={cart_before:r,cart_after:a,product_id:e};return i?{handled:!0,status:"succeeded",self_verified:!0,stage:"host_add_to_cart",evidence:{...c,line_item_present:e?xe().includes(e):!0}}:$("host_add_to_cart","cart_unchanged",c)}function Yt(t){return G(t).toLowerCase().replace(/[^a-z0-9]+/g," ").trim()}function $t(t){let e=String(t||"").split("?")[0].split("#")[0];return e.length>1?e.replace(/\/+$/,""):e||"/"}function ic(t){try{let e=new URL(String(t||""),window.location.origin);return e.origin!==window.location.origin?"":`${e.pathname}${e.search}`||"/"}catch{return""}}function ac(t){let e=Yt(t);if(!e)return null;let n=Ne(T.navLink);return n.find(r=>Yt(r.getAttribute(Zs))===e)||n.find(r=>Yt(r.textContent)===e)||n.find(r=>{let o=Yt(r.textContent);return o&&(o.includes(e)||e.includes(o))})||null}async function zr(t){if(!Pe())return null;let e=ac(t);if(!e)return $("host_navigate","no_matching_nav_target",{target:G(t)});let n=$t(ic(e.getAttribute("href")||e.href)),r=$t(window.location.pathname);yt(e);let o=await gt(()=>n&&$t(window.location.pathname)===n?!0:null,jt),i=$t(window.location.pathname),a={target:G(t),expected:n,route:`${window.location.pathname}${window.location.search}`};return o?await gt(()=>document.querySelector("main, [data-aihub-role='search-results'], [data-product-id]")?!0:null,jt)?{handled:!0,status:"succeeded",self_verified:!0,stage:"host_navigate",evidence:a}:$("host_navigate","page_not_ready",a):i!==r?$("host_navigate","wrong_route",{...a,actual:i}):$("host_navigate","route_unchanged",{...a,actual:i})}function $(t,e,n){return{handled:!0,status:"failed",stage:t,reason:e,evidence:n||{}}}function sc(t,e,n){return{handled:!0,status:"unconfirmed",stage:t,reason:e,evidence:n||{}}}function cc(t,e){return{handled:!0,status:"unsupported_host",stage:t,reason:e,evidence:{}}}var Wr=new Set([s.FILTER_PRODUCTS]);function Gr(t){let e=t.parameters||t.params||{};return String(e[p.SEARCH_QUERY]||e.search||e.query||e.q||"").trim()}function Kr(t){let e=t.parameters||t.params||{};return String(e[p.PAGE]||e.page||e.target||"").trim()}function Qr(t){let e=t.action;return e===s.ADD_TO_CART?Le():Wr.has(e)?ve()&&!!Gr(t):e===s.NAVIGATE_TO?Pe()&&!!Kr(t):!1}async function Xr(t){let e=t.action,n=t.parameters||t.params||{};if(e===s.ADD_TO_CART)return Vr(n);if(Wr.has(e)){let r=Gr(t);return r?qr(r):null}if(e===s.NAVIGATE_TO){let r=Kr(t);return r?zr(r):null}return null}var uc=Object.freeze([{name:"host_contract",canExecute:Qr,execute:Xr},{name:"runtime_adapter",canExecute:Rr,execute:Cr},{name:"product_overlay",canExecute:wr,execute:Ir},{name:"entity_overlay",canExecute:qn,execute:Vn},{name:"handoff_overlay",canExecute:Jn,execute:Zn},{name:"platform_adapter",canExecute:()=>!0,execute:gn},{name:"provider_adapter",canExecute:xn,execute:Nn},{name:"navigation",canExecute:er,execute:nr},{name:"browser_event",canExecute:()=>!0,execute:xr}]);async function Ue(t){let e=[];for(let n of t||[]){let r=ir(n),o=await lc(r);o&&e.push(o)}return e}async function lc(t){if(!t.action)return;let e=Date.now(),n=window.location.href,r=Re();await St(d.apiUrl,d.siteId,t,{status:"requested",stage:"widget_dispatch",requested_url:n,final_url:n,evidence:De(t,n,n)}),await St(d.apiUrl,d.siteId,t,{status:"executing",stage:"widget_dispatch",requested_url:n,final_url:window.location.href,evidence:De(t,n,window.location.href)});let o;try{o=await dc(t)}catch(u){o={status:"failed",stage:"widget_dispatch",reason:u instanceof Error?u.message:"execution_error"}}let i=o.status==="succeeded"&&o.self_verified?{family:o.stage||"host_contract",verified:!0,reason:o.reason||""}:o.status==="succeeded"?await kr(t,r):{family:"none",verified:!1,reason:o.reason||"execution_failed"},a=window.location.href,c={...De(t,n,a,o),postcondition_family:i.family,postcondition_verified:i.verified,postcondition_reason:i.reason};return await St(d.apiUrl,d.siteId,t,{status:o.status,stage:o.stage,reason:o.reason,duration_ms:Date.now()-e,requested_url:n,final_url:a,evidence:c}),{action:t.action,request_id:t.request_id||t.action_request_id||"",turn_id:t.turn_id||"",sequence:Number(t.sequence||0),status:o.status,stage:o.stage,reason:o.reason,verified:i.verified,postcondition:i.family,requested_url:n,final_url:a,evidence:c}}async function dc(t){if(!t.action)return{status:"failed",stage:"normalization",reason:"missing_action"};for(let e of uc){if(!e.canExecute(t))continue;let n=await e.execute(t),r=pc(n,e.name);if(r)return r}return{status:"failed",stage:"all",reason:"no_executor_succeeded"}}function pc(t,e){if(t===!0)return{status:"succeeded",stage:e,reason:""};if(t===we)return{status:"blocked",stage:e,reason:"action_blocked"};if(!t||typeof t!="object")return null;let n=String(t.status||"").trim().toLowerCase();return n?{status:n,stage:String(t.stage||e).trim()||e,reason:String(t.reason||"").trim(),self_verified:!!t.self_verified,evidence:t.evidence&&typeof t.evidence=="object"?t.evidence:{}}:null}function De(t,e,n,r={}){let o=t.parameters||t.params||{},i={requested_url:e,final_url:n,url_changed:e!==n,path_changed:Jr(e)!==Jr(n),title:document.title||"",stage:r.stage||"",result_status:r.status||""};return o.page&&(i.target_page=o.page),o.product_id&&(i.product_id=o.product_id),o.entity_id&&(i.entity_id=o.entity_id),Array.isArray(o.product_ids)&&(i.product_count=o.product_ids.length),Array.isArray(o.entity_ids)&&(i.entity_count=o.entity_ids.length),{...i,...r.evidence&&typeof r.evidence=="object"?r.evidence:{}}}function Jr(t){try{return new URL(t,window.location.href).pathname}catch{return""}}var m=Object.freeze({CANCELLED:"cancelled",NETWORK:"network",TIMEOUT:"timeout",ACCESS_DENIED:"access_denied",INVALID_REQUEST:"invalid_request",PAYLOAD_TOO_LARGE:"payload_too_large",UNSUPPORTED_MEDIA:"unsupported_media",RATE_LIMITED:"rate_limited",PROVIDER_UNAVAILABLE:"provider_unavailable",SERVER_ERROR:"server_error",MICROPHONE:"microphone",UNKNOWN:"unknown"}),Zr=Object.freeze({[m.CANCELLED]:"Stopped",[m.NETWORK]:"Connection issue",[m.TIMEOUT]:"Timed out",[m.ACCESS_DENIED]:"Access denied",[m.INVALID_REQUEST]:"Try again",[m.PAYLOAD_TOO_LARGE]:"Recording too long",[m.UNSUPPORTED_MEDIA]:"Audio not supported",[m.RATE_LIMITED]:"Service busy",[m.PROVIDER_UNAVAILABLE]:"Service unavailable",[m.SERVER_ERROR]:"Service error",[m.MICROPHONE]:"Mic unavailable",[m.UNKNOWN]:"Try again"}),to=64,S=class extends Error{constructor(e,{status:n=0,code:r="",requestId:o="",stage:i=""}={}){super(`voice_transport_${e}`),this.name="VoiceTransportError",this.category=e,this.status=Number(n)||0,this.code=String(r||"").slice(0,to),this.requestId=String(o||"").slice(0,to),this.stage=i}get customerMessage(){return fc(this.category)}toDiagnostics(){return{category:this.category,status:this.status,code:this.code,request_id:this.requestId,stage:this.stage}}};function fc(t){return Zr[t]||Zr[m.UNKNOWN]}function eo(t){return t instanceof S&&t.category===m.CANCELLED}function mc(t){let e=Number(t)||0;return e===401||e===403?m.ACCESS_DENIED:e===408?m.TIMEOUT:e===413?m.PAYLOAD_TOO_LARGE:e===415?m.UNSUPPORTED_MEDIA:e===429?m.RATE_LIMITED:e===502||e===503||e===504?m.PROVIDER_UNAVAILABLE:e>=500?m.SERVER_ERROR:e>=400?m.INVALID_REQUEST:m.UNKNOWN}function bt(t){if(t instanceof S)return t;let e=String(t?.message||t||"").toLowerCase();return t?.name==="AbortError"||e.includes("abort")||e.includes("timeout")||e.includes("timed out")?new S(m.TIMEOUT):e.includes("microphone")||e.includes("permission")||e.includes("notallowed")?new S(m.MICROPHONE):t?.name==="TypeError"||e.includes("failed to fetch")||e.includes("network")||e.includes("load failed")?new S(m.NETWORK):new S(m.UNKNOWN)}function no(t,e=null){let n=Number(t?.status)||0,r=t?.headers?.get?.("x-request-id")||t?.headers?.get?.("x-correlation-id")||"",o=e&&typeof e=="object"&&(e.code||e.error_code)||"",i=/^[A-Za-z0-9_.:-]{1,64}$/.test(String(o||""))?String(o):"";return new S(mc(n),{status:n,code:i,requestId:r,stage:"http_response"})}var hc="/v1/widget/runtime-event",_c=16;function O(t={}){let e=JSON.stringify({client_id:d.siteId,site_id:d.siteId,origin:window.location.origin,occurred_at:new Date().toISOString(),session_id:d.sessionId,turn_id:k(t.turn_id,80),request_id:k(t.request_id,80),component:k(t.component||"voice",60),stage:k(t.stage,80),event_type:k(t.event_type||"runtime_event",80),severity:k(t.severity||"info",20),status:k(t.status||"ok",20),message_code:k(t.message_code,80),duration_ms:ro(t.duration_ms),metadata:yc(t.metadata)}),n=new URL(hc,d.apiUrl).toString();fetch(n,{method:"POST",headers:{Accept:"application/json","Content-Type":"application/json"},body:e,keepalive:!0}).catch(()=>{})}function yc(t){if(!t||typeof t!="object"||Array.isArray(t))return{};let e={};for(let[n,r]of Object.entries(t).slice(0,_c)){let o=k(n,60).toLowerCase();!o||gc(o)||(typeof r=="boolean"||r===null?e[o]=r:typeof r=="number"?e[o]=ro(r):typeof r=="string"&&(e[o]=k(r,120)))}return e}function gc(t){return["audio","transcript","response","error","exception","token","secret"].some(e=>t.includes(e))}function k(t,e){return String(t||"").replace(/\s+/g," ").trim().slice(0,e)}function ro(t){let e=Number(t||0);return Number.isFinite(e)?Math.max(0,e):0}var bc=3,Tc="AIHubAdapterRuntime",Ac="AIHubAdapter";function Ec(t,e){let n=new URL(v.SHOP_WS,t);return n.protocol=n.protocol==="https:"?"wss:":"ws:",n.searchParams.set("site_id",e),n.searchParams.set("session_id",d.sessionId),n.toString()}function Sc(t){return new Promise((e,n)=>{let r=new FileReader;r.onloadend=()=>{let o=String(r.result||"");e(o.includes(",")?o.split(",").pop():o)},r.onerror=()=>n(r.error||new Error("Failed to read audio blob")),r.readAsDataURL(t)})}var ke=class{constructor(){this.queue=[],this.blocked=[],this.playing=!1,this.current=null,this.lastPlaybackStartMs=0,this.installUnlockListeners()}push(e,n=""){e&&(this.queue.push({audioB64:e,fallbackText:n}),this.playNext())}playNext(){if(this.playing||this.queue.length===0)return;this.playing=!0;let e=this.queue.shift(),n=new Audio(ct.DATA_WAV_PREFIX+e.audioB64);n.preload="auto",this.current=n,n.onplay=()=>{this.lastPlaybackStartMs=typeof performance<"u"?performance.now():0},n.onended=()=>{this.current=null,this.playing=!1,this.playNext()},n.onerror=()=>{this.current=null,e.fallbackText&&rt(e.fallbackText),this.playing=!1,this.playNext()},n.play().catch(r=>{if(console.warn("Audio playback failed",r),this.current=null,this.isAutoplayBlocked(r)){e.fallbackText?rt(e.fallbackText):this.blocked.unshift(e),this.playing=!1;return}e.fallbackText&&rt(e.fallbackText),this.playing=!1,this.playNext()})}installUnlockListeners(){if(typeof window>"u")return;let e=()=>{this.retryBlocked(),Pt()};window.addEventListener("pointerdown",e,{capture:!0,passive:!0}),window.addEventListener("keydown",e,{capture:!0}),window.addEventListener("touchstart",e,{capture:!0,passive:!0})}retryBlocked(){this.blocked.length&&(this.queue.unshift(...this.blocked.splice(0)),this.playNext())}speakInsteadOfBlocked(e){!e||!this.blocked.length||(this.blocked=[],rt(e))}isAutoplayBlocked(e){let n=`${e?.name||""} ${e?.message||e||""}`.toLowerCase();return n.includes("notallowed")||n.includes("user didn't interact")||n.includes("not allowed")}stop(){if(this.queue=[],this.blocked=[],this.current){try{this.current.pause(),this.current.currentTime=0}catch{}this.current.onended=null,this.current.onerror=null,this.current=null}this.playing=!1,Dt()}isSpeaking(){return this.playing||this.queue.length>0||_r()}},Vt=new ke;function zt(){Vt.stop()}function He(){return Vt.isSpeaking()}function Be(t="reset"){ao.reset(t),io.reset(t)}var Me=class{constructor(){this.inFlight=null,this.cancelled=!1}reset(e="reset"){this.cancelled=e==="user_cancel";try{this.inFlight?.abort()}catch{}this.inFlight=null}async sendAudio(e,n,r=[]){let o=j();O({event_type:"voice_turn_started",stage:"http_request",status:"started",metadata:{transport:"http",audio_type:e?.type||"unknown"}});let i=new FormData;i.append("audio",e,Oc(e)),i.append("site_id",d.siteId),i.append("session_id",d.sessionId),r&&r.length>0&&i.append("conversation_history",JSON.stringify(r));let a=lo();a&&i.append("page_context",JSON.stringify(a));let c,u=typeof AbortController=="function"?new AbortController:null;this.inFlight=u,this.cancelled=!1;try{c=await fetch(`${d.apiUrl}${v.SHOP}`,{method:cn.POST,body:i,signal:u?.signal})}catch(E){throw this.cancelled||E?.name==="AbortError"?new S(m.CANCELLED,{stage:"user_cancel"}):bt(E)}if(!c.ok)throw no(c,await Cc(c));let f=await c.json();f.transcript&&n.onUserMessage?.(f.transcript);let g=Array.isArray(f.ui_actions)?f.ui_actions:[],M=[];g.length>0&&(M=await Ue(g),n.onActionResults?.(M));let w=co(f.response_text||"",g,M);w&&n.onAssistantMessage?.(w,g),n.onStatusChange?.(_.READY);let b=w===(f.response_text||""),R=b?f.spoken_text||f.response_text||"":w;f.audio_b64&&b?Ic(f.audio_b64,R):R&&rt(R),n.onComplete?.(f),O({event_type:"voice_turn_completed",stage:"http_response",status:"ok",request_id:wc(c),duration_ms:j()-o,metadata:{transport:"http",action_count:f.ui_actions?.length||0}})}},Fe=class{constructor(){this.ws=null,this.connected=!1,this.connecting=null,this.failed=!1,this.retries=0,this.audioQueue=Vt,this.callbacks=null,this.turnText="",this.receivedAudio=!1,this.pendingAudioChunks=[]}async ensureConnected(e=[]){return this.canUseWebSocket()?this.isOpen()?!0:this.connecting?this.connecting:(this.connecting=this.openConnection(e),this.connecting):!1}canUseWebSocket(){return!this.failed&&d.useWebSocket&&"WebSocket"in window}isOpen(){return this.connected&&this.ws?.readyState===WebSocket.OPEN}openConnection(e=[]){return new Promise(n=>{let r=new WebSocket(Ec(d.apiUrl,d.siteId)),o=!1;this.ws=r;let i=(c=null)=>{o||(o=!0,this.markConnectionFailed(n,c,r))},a=window.setTimeout(()=>{i()},fn);r.onopen=()=>{o||(o=!0,this.handleConnectionOpen(a,e,n))},r.onmessage=c=>{this.handleMessage(c).catch(u=>this.handleTransportError(u))},r.onerror=()=>{if(o){this.failActiveTurn(m.NETWORK);return}i(a)},r.onclose=()=>{if(this.connected=!1,o){this.failActiveTurn(m.NETWORK);return}i(a)}})}markConnectionOpen(){this.connected=!0,this.connecting=null,this.retries=0}handleConnectionOpen(e,n,r){window.clearTimeout(e),this.markConnectionOpen(),this.sendConfig(n),r(!0)}markConnectionFailed(e,n=null,r=null){n&&window.clearTimeout(n),this.connected=!1,this.connecting=null,this.retries+=1,this.retries>=bc&&(this.failed=!0),r&&r.readyState!==WebSocket.CLOSED&&r.close(),e(!1)}sendConfig(e=[]){this.sendJson({type:L.CONFIG,history:e||[],session_id:d.sessionId,page_context:lo()})}sendJson(e){return!this.ws||this.ws.readyState!==WebSocket.OPEN?!1:(this.ws.send(JSON.stringify(e)),!0)}async sendAudio(e,n,r=[]){if(!await this.ensureConnected(r))return!1;this.callbacks=n,this.turnText="",this.receivedAudio=!1,this.pendingAudioChunks=[],this.sendConfig(r);let i=await Sc(e),a=this.beginTurn();return this.turnStartedAt=j(),O({event_type:"voice_turn_started",stage:"websocket_send",status:"started",metadata:{transport:"websocket",audio_type:e?.type||"unknown"}}),this.sendJson({type:L.AUDIO_CHUNK,data:i,mime_type:e?.type||""})&&this.sendJson({type:L.AUDIO_END,mime_type:e?.type||""})?(await a,!0):(this.settleTurn(),this.callbacks=null,!1)}beginTurn(){return this.settleTurn(),new Promise(e=>{let n=window.setTimeout(()=>{this.failActiveTurn(m.TIMEOUT)},mn);this.activeTurn={resolve:e,timer:n}})}settleTurn(){let e=this.activeTurn;return this.activeTurn=null,e?(window.clearTimeout(e.timer),e.resolve(),!0):!1}failActiveTurn(e){if(!this.activeTurn)return;let n=this.callbacks;if(this.callbacks=null,this.pendingAudioChunks=[],n){let r=new S(e,{stage:"websocket"});n.onStatusChange?.(_.ERROR,r.customerMessage),n.onComplete?.({error:r.category}),O({event_type:"voice_turn_failed",stage:"websocket",severity:"error",status:"failed",message_code:r.code||r.category,duration_ms:j()-(this.turnStartedAt||j()),metadata:{transport:"websocket",category:r.category,http_status:r.status}})}this.settleTurn()}async handleMessage(e){let n=this.callbacks;if(!n)return;let r=this.parseMessage(e.data);if(!r){this.completeWithError(n,"Invalid WebSocket message");return}if(!this.handleIncrementalMessage(r,n)){if(r.type===L.DONE){await this.handleDoneMessage(r,n);return}r.type===L.ERROR&&this.completeWithError(n,r.message||"WebSocket error")}}parseMessage(e){try{let n=JSON.parse(e);return n&&typeof n=="object"?n:null}catch{return null}}handleIncrementalMessage(e,n){return e.type===L.TRANSCRIPT?(n.onUserMessage?.(e.text||""),!0):e.type===L.TEXT_CHUNK?(this.turnText+=e.text||"",!0):e.type===L.AUDIO_CHUNK?(this.receivedAudio=!!e.audio_b64||this.receivedAudio,e.audio_b64&&this.pendingAudioChunks.push(e.audio_b64),!0):!1}async handleDoneMessage(e,n){let r=e.response_text||this.turnText;try{let o=Array.isArray(e.ui_actions)?e.ui_actions:[],i=[];o.length>0&&(i=await Ue(o),n.onActionResults?.(i));let a=co(r,o,i);n.onAssistantMessage?.(a,o,{streamed:!0}),n.onStatusChange?.(_.READY);let c=a===r,u=c?e.spoken_text||r:a;if(this.receivedAudio&&c)for(let f of this.pendingAudioChunks)this.audioQueue.push(f);else u&&rt(u);n.onComplete?.(e),O({event_type:"voice_turn_completed",stage:"websocket_done",status:"ok",duration_ms:j()-(this.turnStartedAt||j()),metadata:{transport:"websocket",action_count:e.ui_actions?.length||0}})}catch(o){this.handleTransportError(o)}finally{this.pendingAudioChunks=[],this.callbacks=null,this.settleTurn()}}completeWithError(e,n){e.onStatusChange?.(_.ERROR,uo(n)),e.onComplete?.({error:n});let r=bt(n);O({event_type:"voice_turn_failed",stage:"websocket_message",severity:"error",status:"failed",message_code:r.code||r.category,duration_ms:j()-(this.turnStartedAt||j()),metadata:{transport:"websocket",category:r.category,http_status:r.status}}),this.callbacks=null,this.settleTurn()}handleTransportError(e){console.error("AI Hub WebSocket transport failed",e);let n=this.callbacks;n&&this.completeWithError(n,String(e))}reset(e="reset"){this.callbacks=null,this.turnText="",this.receivedAudio=!1,this.pendingAudioChunks=[],this.settleTurn();try{this.ws?.close()}catch{}this.ws=null,this.connected=!1,this.connecting=null,this.failed=!1,this.retries=0}},io=new Me,ao=new Fe;async function so(t,e,n,r=[]){try{if(d.useWebSocket&&await ao.sendAudio(t,n,r))return;await io.sendAudio(t,n,r)}catch(o){let i=o instanceof S?o:bt(o);if(eo(i)){O({event_type:"voice_turn_cancelled",stage:i.stage||"transport",status:"cancelled",metadata:{transport:d.useWebSocket?"websocket_or_http":"http"}}),n.onStatusChange?.(_.READY),n.onComplete?.({cancelled:!0});return}console.error(o),O({event_type:"voice_turn_failed",stage:i.stage||"transport",severity:"error",status:"failed",request_id:i.requestId,message_code:i.code||i.category,metadata:{transport:d.useWebSocket?"websocket_or_http":"http",category:i.category,http_status:i.status}}),n.onStatusChange?.(_.ERROR,uo(o)),n.onComplete?.({error:String(o)})}}function wc(t){return t?.headers?.get?.("x-request-id")||t?.headers?.get?.("x-correlation-id")||""}function j(){return typeof performance<"u"?performance.now():Date.now()}function Ic(t,e=""){Vt.push(t,e)}function Oc(t){let e=String(t?.type||"").toLowerCase();return e.includes("mp4")?"audio.mp4":e.includes("ogg")?"audio.ogg":e.includes("wav")?"audio.wav":ct.WEBM_FILENAME}var Rc=/\b(opened|opening|taking you|took you|navigat|sorted|sorting|filtered|filtering|showing|shown|displayed|added to (?:your )?cart|here (?:it |they )?(?:is|are))\b/i,oo="I could not complete that on the page. The site may not have responded - please try again, or do it manually.";function co(t,e,n){let r=String(t||"");if(!r||!Array.isArray(e)||e.length===0||!Rc.test(r))return r;let o=Array.isArray(n)?n:[];return o.length!==e.length?oo:o.every(a=>a?.status==="succeeded"&&a?.verified!==!1)?r:oo}async function Cc(t){try{return await t.json()}catch{return null}}function uo(t){if(t instanceof S)return t.customerMessage;let e=String(t?.message||t||"").toLowerCase();return e.includes("quota")?"Quota reached":e.includes("transcription")||e.includes("speech")?"Voice unavailable":bt(t).customerMessage}function rt(t){return t?J(String(t).slice(0,700)):!1}function lo(){let t=window[Tc],e=window[Ac];try{if(typeof t?.getContext=="function")return t.getContext();if(typeof e?.getContext=="function")return e.getContext()}catch(n){console.warn("[AI Hub Widget] Page context collection failed:",n)}return xc()}function xc(){try{return{title:document.title||"",url:window.location.href,path:window.location.pathname,...Ft()}}catch(t){return console.warn("[AI Hub Widget] Local page state collection failed:",t),null}}var Nc=4,vc=40,Lc=24,Pc=80,Dc=120,Ye=6,Uc=40,kc=600,Mc=6,Fc=12,po=/\[PRODUCT_IDS:\s*([^\]]+)\]/g;function fo(){let t=[];function e(n,r){let o=String(r||"").trim();o&&(t.push({role:n,content:o}),t.length>Uc&&t.shift())}return{history:t,historyForRequest(){if(t.length<=Ye)return t.map(i=>({...i}));let n=t.slice(0,t.length-Ye),r=t.slice(t.length-Ye).map(i=>({...i})),o=Hc(n);return o?[o,...r]:r},clear(){t.length=0},rememberUserMessage(n){e("user",n)},rememberAssistantMessage(n,r){e("assistant",Bc(n,r))},rememberActionResults(n){let r=$c(n);r&&e("assistant",r)}}}function Hc(t){let e=[],n=[];for(let o of t){o.role==="user"&&e.length<Mc&&e.push(o.content.replace(/\s+/g," ").trim().slice(0,80));let i;for(po.lastIndex=0;(i=po.exec(o.content))!==null;)$e(n,i[1].split(",").map(a=>a.trim()))}let r=[];return e.length&&r.push(`Earlier the customer asked: ${e.join("; ")}.`),n.length&&r.push(`Products discussed: ${n.slice(0,Fc).join(", ")}.`),r.length?{role:"system",content:`[CONVERSATION_SUMMARY] ${r.join(" ")}`.slice(0,kc)}:null}function Bc(t,e){let n=Yc(e);return n.length?`${t} [PRODUCT_IDS: ${n.join(",")}]`:t}function Yc(t){let e=[];for(let n of t||[]){let r=n.params||{};$e(e,r[p.PRODUCT_IDS]),$e(e,[r[p.PRODUCT_ID]])}return e}function $e(t,e){for(let n of Array.isArray(e)?e:[])n&&!t.includes(n)&&t.push(n)}function $c(t){let e=(Array.isArray(t)?t:[]).map(jc).filter(Boolean).slice(0,Nc);return e.length?`[BROWSER_ACTION_RESULTS: ${e.join(" | ")}]`:""}function jc(t){if(!t||typeof t!="object"||!t.action)return"";let e=[Wt(t.action,vc),`status=${Wt(t.status,Lc)||"unknown"}`],n=Vc(t.final_url);return n&&e.push(`final_path=${Wt(n,Dc)}`),t.reason&&e.push(`reason=${Wt(t.reason,Pc)}`),qc(e,t.evidence),e.join(" ")}function qc(t,e={}){e.rendered_product_count!==void 0&&t.push(`rendered_products=${Number(e.rendered_product_count||0)}`),e.rendered_entity_count!==void 0&&t.push(`rendered_records=${Number(e.rendered_entity_count||0)}`)}function Wt(t,e){return String(t||"").replace(/\s+/g," ").trim().slice(0,e)}function Vc(t){try{let e=new URL(String(t||""),window.location.href);return`${e.pathname}${e.search}${e.hash}`}catch{return""}}var mo="aihub:session-reset",Gt="AIHub",zc=Object.freeze(["mayabot:","aihub:"]);function Wc(t){let e=[];for(let n=0;n<t.length;n+=1){let r=t.key(n);r&&zc.some(o=>r.startsWith(o))&&e.push(r)}return e}function ho(t){if(!t)return[];try{let e=Wc(t);for(let n of e)t.removeItem(n);return e}catch{return[]}}function Gc(){let t=[];try{t.push(...ho(window.sessionStorage))}catch{}try{t.push(...ho(window.localStorage))}catch{}return t}function _o({cancelRecording:t,stopPlayback:e,resetTransport:n,conversationMemory:r,clearOverlays:o,rotateSessionId:i}={}){return function(){let c={stopped_recording:!1,stopped_audio:!1,cleared_keys:[],session_id:""};return c.stopped_recording=ot(t),c.stopped_audio=ot(e),ot(n),ot(()=>r?.clear?.()),ot(o),c.cleared_keys=Gc(),c.session_id=String(ot(i)||""),c}}function ot(t){if(typeof t!="function")return!1;try{let e=t();return e===void 0?!0:e}catch(e){return console.warn("[AI Hub Widget] Session reset step failed:",e),!1}}function yo(t){let e=window[Gt]||{};e.resetSession=t,window[Gt]=e;let n=()=>t();return window.addEventListener(mo,n),()=>{window.removeEventListener(mo,n),window[Gt]?.resetSession===t&&delete window[Gt].resetSession}}var go=null;function je(t){go||(bo(t),go=window.setInterval(()=>bo(t),pn))}async function bo({boot:t,shutdownWidget:e}){try{if(await Kc()){t();return}e()}catch{t()}}async function Kc(){let t=new URL(v.WIDGET_STATUS,d.apiUrl);t.searchParams.set("site_id",d.siteId);let e=await fetch(t.toString(),{cache:"no-store",headers:{Accept:"application/json"}});return e.ok?(await e.json()).enabled!==!1:!0}window.__mayabot_identifier="voice-orb";var qe=null,Ve=null;function To(){if(window.__mayabotBooted||document.getElementById("mayabot-widget"))return;window.__mayabotBooted=!0,Qe();let t=an(),e=null,n=null,r=!1;function o(h=un){e&&window.clearTimeout(e),e=window.setTimeout(()=>{t.msgs.innerHTML="",t.chat.classList.remove("visible"),e=null},h)}function i(h,Z=""){r=h===_.RECORDING,We(So(h)),t.status.className="",h===_.RECORDING?(e&&(window.clearTimeout(e),e=null),t.msgs.innerHTML="",t.chat.classList.add("visible"),t.status.innerText="Listening...",t.status.classList.add("listening")):h===_.PROCESSING?(t.chat.classList.add("visible"),t.status.innerText="Analyzing...",t.status.classList.add("processing")):h===_.READY?(t.status.innerText="Ready",t.status.classList.add("ready")):h===_.ERROR&&(t.status.innerText=Z||"Try again",t.status.classList.add("error"))}let a=fo(),c=null,u="",f=!1,g=0;async function M(h){if(f)return;f=!0;let Z=++g,K=()=>Z===g;t.btn.disabled=!0,c=null,u="";try{await so(h,t,{onUserMessage:C=>{K()&&(st(t,C,"user"),a.rememberUserMessage(C))},onAssistantChunk:(C,it)=>{K()&&(u=it,c||(c=st(t,"","ai")),Jt(t,c,u))},onAssistantMessage:(C,it,Io={})=>{K()&&(Io.streamed&&c?Jt(t,c,C):st(t,C,"ai"),a.rememberAssistantMessage(C,it),c=null,u="")},onActionResults:C=>{K()&&a.rememberActionResults(C)},onStatusChange:(C,it)=>{K()&&i(C,it)},onComplete:()=>{K()&&o()}},a.historyForRequest())}finally{K()&&(f=!1,t.btn.disabled=!1),c=null,u=""}}function w(){g+=1,Be("user_cancel"),zt(),f=!1,t.btn.disabled=!1,c=null,u="",O({event_type:"voice_turn_cancelled",stage:"orb_gesture",status:"cancelled"}),i(_.READY)}let b=hn(M,i);qe=b;function R(){return f||He()}function E(){if(R()){w();return}b.toggle()}let ze={idle:{label:"Maya voice assistant. Click, press Enter, or press Space to talk.",title:"Click to talk"},recording:{label:"Maya is listening. Click once to send, or press Escape to cancel.",title:"Click once to send - Escape to cancel"},processing:{label:"Maya is working on your request. Please wait.",title:"Request in progress"},speaking:{label:"Maya is speaking. Click to stop, or press Escape to stop.",title:"Click to stop Maya"}};function So(h){return h===_.RECORDING?"recording":h===_.PROCESSING?"processing":He()?"speaking":"idle"}function We(h){let Z=ze[h]||ze.idle;t.btn.setAttribute("aria-label",Z.label),t.btn.setAttribute("title",Z.title),t.btn.setAttribute("data-orb-state",h),t.btn.classList.toggle("recording",h==="recording"),t.btn.classList.toggle("speaking",h==="speaking")}We("idle"),t.btn.addEventListener("click",h=>{h.detail>1||E()});let Ge=h=>{if(h.key==="Escape"){if(r){b.cancel(),O({event_type:"voice_recording_cancelled",stage:"keyboard_escape",status:"cancelled"}),i(_.READY);return}R()&&w()}};document.addEventListener("keydown",Ge);let Ke=h=>{t.btn.contains(h.target)||Pt()};document.addEventListener("pointerdown",Ke,{capture:!0});let wo=yo(_o({cancelRecording:()=>b.cancel(),stopPlayback:zt,resetTransport:Be,conversationMemory:a,clearOverlays:()=>{t.msgs.innerHTML="",t.chat.classList.remove("visible"),document.getElementById("mayabot-product-panel")?.remove()},rotateSessionId:()=>d.rotateSessionId()}));Ve=()=>{document.removeEventListener("keydown",Ge),document.removeEventListener("pointerdown",Ke,{capture:!0}),wo(),e&&window.clearTimeout(e),e=null,n&&window.clearTimeout(n),n=null,Ve=null},Qc()&&(Xc(),n=window.setTimeout(()=>{if(a.history.length>0)return;let h=`Welcome to ${d.brandName}. How can I help you today?`;st(t,h,"ai"),i(_.READY),o(dn),J(h)},ln))}function Ao(){qe?.cancel(),qe=null,Ve?.(),zt(),window.__mayabotBooted=!1,document.getElementById("mayabot-widget")?.remove(),document.getElementById("mayabot-product-panel")?.remove()}function Qc(){if(!d.autoGreet||!Jc())return!1;try{return window.sessionStorage.getItem(Eo())!=="1"}catch{return!window.__mayabotAutoGreeted}}function Xc(){window.__mayabotAutoGreeted=!0;try{window.sessionStorage.setItem(Eo(),"1")}catch{}}function Eo(){return`mayabot:auto-greeted:${d.siteId}`}function Jc(){let t=window.location.pathname.replace(/\/+$/,"")||"/";return t==="/"||t.endsWith("/index.html")}document.readyState==="loading"?document.addEventListener("DOMContentLoaded",()=>je({boot:To,shutdownWidget:Ao})):je({boot:To,shutdownWidget:Ao});})();
