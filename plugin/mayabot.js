(()=>{function Qt(){let t="#5d5fef",e=document.querySelector('meta[name="theme-color"]');if(e&&e.content)t=e.content;else{let b=document.querySelector('button[class*="primary"], .btn-primary, [data-primary]');if(b){let N=window.getComputedStyle(b).backgroundColor;N&&N!=="rgba(0, 0, 0, 0)"&&N!=="transparent"&&(t=N)}}let n=window.matchMedia&&window.matchMedia("(prefers-color-scheme: dark)").matches,r=n?"rgba(24, 24, 27, 0.75)":"rgba(255, 255, 255, 0.85)",o=n?"rgba(255, 255, 255, 0.1)":"rgba(0, 0, 0, 0.08)",a=n?"#f3f4f6":"#111827",i=n?"rgba(255, 255, 255, 0.1)":"rgba(0, 0, 0, 0.05)",c=n?"rgba(0, 0, 0, 0.25)":"#ffffff",m=document.createElement("style");m.textContent=`
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
      left: 50%;
      right: auto;
      transform: translateX(-50%);
      z-index: 2147483647;
      font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      color: var(--mayabot-text);
      letter-spacing: -0.01em;
      width: auto;
      max-width: calc(100vw - 32px);
      -webkit-font-smoothing: antialiased;
    }

    #mayabot-btn {
      position: relative;
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
      transition: all 0.3s cubic-bezier(0.25, 1, 0.5, 1);
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
      transition: all 0.3s ease;
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
      box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7);
      animation: mayabotPulseRecord 1.5s infinite cubic-bezier(0.66, 0, 0, 1);
    }

    #mayabot-chat {
      position: absolute;
      bottom: 96px;
      left: 50%;
      transform: translateX(-50%) translateY(20px) scale(0.95);
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
      transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    }

    #mayabot-chat.visible {
      opacity: 1;
      pointer-events: all;
      visibility: visible;
      transform: translateX(-50%) translateY(0) scale(1);
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
      transition: all 0.3s ease;
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

    @keyframes mayabotPulseRecord {
      to { box-shadow: 0 0 0 24px rgba(239, 68, 68, 0); }
    }

    @media (max-width: 520px) {
      #mayabot-widget {
        bottom: max(16px, env(safe-area-inset-bottom));
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
  `,document.head.appendChild(m)}var mt="site_1",Mn="__AI_";var kn="aihub:auto-site-id:",Fn=["data-aihub-scope","data-site-scope"],Hn=["data-site-id","data-aihub-site-id"];function g(t){return String(t||"").trim()}function j(t){return g(t).replace(/\/+$/,"")}function Jt(t,e,n,r=mt){return Bn(t,e,n)||Yn()||g(r)||mt}function Bn(t,e,n){for(let a of Hn){let i=g(t?.getAttribute(a));if(i)return i}let r=g(e?.searchParams.get("site"))||g(e?.searchParams.get("site_id"))||g(e?.searchParams.get("shop"));if(r)return r;let o=g(n);return o&&!o.startsWith(Mn)?o:""}function Yn(){let t=$n(),e=`${kn}${t}`,n=Qn(e);if(n)return n;let r=g(window.location.host||window.location.hostname||"site"),o=Zt(),a=Vn(`${r}${o?`_${o.replace(/\//g,"_")}`:""}`),i=qn(`auto_${a}_${Kn(t)}`);return Xn(e,i),i}function $n(){return`${window.location.origin}${Zt()}`}function Zt(){return zn()}function zn(){for(let e of Fn){let n=g(jn()?.getAttribute(e));if(n)return Xt(n)}let t=document.querySelector("meta[name='aihub-site-scope']")?.getAttribute("content");return Xt(t)}function jn(){return document.currentScript}function Xt(t){let e=g(t);if(!e||e==="/")return"";try{let r=new URL(e,window.location.href);if(r.origin===window.location.origin){let[o]=Wn(r.pathname);return o?`/${o}`:""}}catch{}let[n]=e.replace(/^\/+/,"").split("/");return n?`/${n}`:""}function Wn(t=window.location.pathname){return g(t).split("/").map(e=>Gn(e).trim()).filter(Boolean)}function Gn(t){try{return decodeURIComponent(t)}catch{return String(t||"")}}function Vn(t){return g(t).toLowerCase().replace(/[^a-z0-9_-]+/g,"_").replace(/^_+|_+$/g,"")||"site"}function qn(t){return g(t).slice(0,80).replace(/_+$/g,"")||mt}function Kn(t){let e=2166136261,n=g(t);for(let r=0;r<n.length;r+=1)e^=n.charCodeAt(r),e=Math.imul(e,16777619);return(e>>>0).toString(36)}function Qn(t){try{return g(window.localStorage.getItem(t))}catch{return""}}function Xn(t,e){try{window.localStorage.setItem(t,e)}catch{}}var x=document.currentScript,te="__AI_PUBLIC_API_URL__",Jn="__AI_DEFAULT_SITE_ID__",Zn="mayabot:session:",tr="Maya",er="AI Salesperson",nr="female";function L(t){return String(t||"").trim()}function rr(){let t=L(x?.getAttribute("src"));if(!t)return null;try{return new URL(t,window.location.href)}catch{return null}}function or(t){let e=L(x?.getAttribute("data-api-url"));if(e)return j(e);if(!te.startsWith("__AI_"))return j(te);if(t?.origin){let n=t.pathname.replace(/\/mayabot(?:-widget)?\.js$/,"");return j(`${t.origin}${n}`)}return j(window.location.origin)}function ar(t){let e=`${Zn}${t}`;try{let n=window.sessionStorage.getItem(e);if(n)return n;let r=ee(t);return window.sessionStorage.setItem(e,r),r}catch{return ee(t)}}function ee(t){let e=window.crypto?.randomUUID?.()||`${Date.now()}-${Math.random().toString(16).slice(2)}`;return`${t}-${e}`.slice(0,120)}var re=rr(),ne=Jt(x,re,Jn),p={siteId:ne,get sessionId(){return ar(ne)},apiUrl:or(re),useWebSocket:L(x?.getAttribute("data-use-websocket")).toLowerCase()==="true",autoGreet:L(x?.getAttribute("data-auto-greet")).toLowerCase()!=="false",brandName:L(x?.getAttribute("data-brand"))||tr,assistantTitle:L(x?.getAttribute("data-assistant-title"))||er,speechVoiceName:L(x?.getAttribute("data-speech-voice")),speechVoicePreference:L(x?.getAttribute("data-speech-voice-preference"))||nr};function oe(){let t=document.createElement("div");return t.id="mayabot-widget",t.innerHTML=`
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
  `,document.body.appendChild(t),t.querySelector(".mayabot-kicker").textContent=p.brandName,t.querySelector(".mayabot-title").textContent=p.assistantTitle,{btn:document.getElementById("mayabot-btn"),chat:document.getElementById("mayabot-chat"),msgs:document.getElementById("mayabot-msgs"),status:document.getElementById("mayabot-status")}}function W(t,e,n){t.chat.classList.add("visible");let r=document.createElement("div");return r.className=`mayabot-msg ${n}`,r.innerText=e,t.msgs.appendChild(r),t.msgs.scrollTop=t.msgs.scrollHeight,r}function _t(t,e,n){e&&(e.innerText=n,t.msgs.scrollTop=t.msgs.scrollHeight)}var s=Object.freeze({ADD_TO_CART:"ADD_TO_CART",BOOK_APPOINTMENT_REQUEST:"BOOK_APPOINTMENT_REQUEST",BUILD_ITINERARY:"BUILD_ITINERARY",BUILD_LEARNING_PATH:"BUILD_LEARNING_PATH",CAPTURE_LEAD:"CAPTURE_LEAD",CAPTURE_PATIENT_LEAD:"CAPTURE_PATIENT_LEAD",CHECKOUT:"CHECKOUT",CHECKOUT_HANDOFF:"CHECKOUT_HANDOFF",CHECK_APPOINTMENT_AVAILABILITY:"CHECK_APPOINTMENT_AVAILABILITY",CHECK_AVAILABILITY:"CHECK_AVAILABILITY",CHECK_DELIVERY_AVAILABILITY:"CHECK_DELIVERY_AVAILABILITY",CHECK_ELIGIBILITY_SOFT:"CHECK_ELIGIBILITY_SOFT",CHECK_PREREQUISITES:"CHECK_PREREQUISITES",CLEAR_CART:"CLEAR_CART",CLEAR_FILTERS:"CLEAR_FILTERS",CLEAR_HISTORY:"CLEAR_HISTORY",COMPARE_ENTITIES:"COMPARE_ENTITIES",CONTACT_AGENT:"CONTACT_AGENT",FILTER_ENTITIES:"FILTER_ENTITIES",FILTER_PRODUCTS:"FILTER_PRODUCTS",HANDOFF_TO_ADVISOR:"HANDOFF_TO_ADVISOR",HANDOFF_TO_AGENT:"HANDOFF_TO_AGENT",HANDOFF_TO_CLINIC:"HANDOFF_TO_CLINIC",HANDOFF_TO_HUMAN:"HANDOFF_TO_HUMAN",HANDOFF_TO_LAWYER:"HANDOFF_TO_LAWYER",HANDOFF_TO_LICENSED_AGENT:"HANDOFF_TO_LICENSED_AGENT",HANDOFF_TO_RECRUITER:"HANDOFF_TO_RECRUITER",JOIN_WAITLIST:"JOIN_WAITLIST",MATCH_JOBS:"MATCH_JOBS",NAVIGATE_TO:"NAVIGATE_TO",OPEN_CLAIM_FLOW:"OPEN_CLAIM_FLOW",OPEN_CONTACT:"OPEN_CONTACT",OPEN_DISCLOSURE:"OPEN_DISCLOSURE",OPEN_ENTITY_DETAIL:"OPEN_ENTITY_DETAIL",OPEN_LOCATION:"OPEN_LOCATION",OPEN_MAP:"OPEN_MAP",OPEN_POLICY:"OPEN_POLICY",OPEN_PROJECTS:"OPEN_PROJECTS",OPEN_RENEWAL_FLOW:"OPEN_RENEWAL_FLOW",OPEN_SERVICES:"OPEN_SERVICES",OPEN_SYLLABUS:"OPEN_SYLLABUS",OPEN_TELECONSULT:"OPEN_TELECONSULT",REMOVE_FROM_CART:"REMOVE_FROM_CART",REQUEST_APPOINTMENT:"REQUEST_APPOINTMENT",REQUEST_CALLBACK:"REQUEST_CALLBACK",REQUEST_CONSULTATION:"REQUEST_CONSULTATION",REQUEST_COUNSELOR_CALLBACK:"REQUEST_COUNSELOR_CALLBACK",REQUEST_ESTIMATE:"REQUEST_ESTIMATE",REQUEST_SITE_VISIT:"REQUEST_SITE_VISIT",REQUEST_TEST_DRIVE:"REQUEST_TEST_DRIVE",REQUEST_VIEWING:"REQUEST_VIEWING",RUN_AFFORDABILITY_CALCULATOR:"RUN_AFFORDABILITY_CALCULATOR",RUN_CALCULATOR:"RUN_CALCULATOR",RUN_DOM_SEQUENCE:"RUN_DOM_SEQUENCE",SAVE_SEARCH:"SAVE_SEARCH",SCHEDULE_ORDER:"SCHEDULE_ORDER",SEARCH_AVAILABILITY:"SEARCH_AVAILABILITY",SET_LOCATION:"SET_LOCATION",SHOW_COMPARISON:"SHOW_COMPARISON",SHOW_EMERGENCY_NOTICE:"SHOW_EMERGENCY_NOTICE",SHOW_ENTITIES:"SHOW_ENTITIES",SHOW_PRODUCT_DETAIL:"SHOW_PRODUCT_DETAIL",SHOW_PRODUCTS:"SHOW_PRODUCTS",SORT_ENTITIES:"SORT_ENTITIES",SORT_PRODUCTS:"SORT_PRODUCTS",START_APPLICATION:"START_APPLICATION",START_BOOKING:"START_BOOKING",START_ENROLLMENT:"START_ENROLLMENT",START_INTAKE:"START_INTAKE",START_QUOTE:"START_QUOTE",START_TICKET_PURCHASE:"START_TICKET_PURCHASE",UPDATE_CART_QUANTITY:"UPDATE_CART_QUANTITY",UPDATE_PREFERENCES:"UPDATE_PREFERENCES"}),l=Object.freeze({ENTITY_ID:"entity_id",ENTITY_IDS:"entity_ids",MESSAGE:"message",PAGE:"page",PRODUCT_ID:"product_id",PRODUCT_IDS:"product_ids",QUANTITY:"quantity",REASON:"reason",SEARCH_QUERY:"search_query",URL:"url"}),Ya=Object.freeze({BLOCKED:"blocked",EXECUTING:"executing",FAILED:"failed",REQUESTED:"requested",SKIPPED:"skipped",SUCCEEDED:"succeeded",UNKNOWN:"unknown"}),S=Object.freeze({KNOWLEDGE_BY_IDS:"/v1/knowledge/by-ids",PRODUCTS_BY_IDS:"/v1/products/by-ids",SHOP:"/v1/shop",SHOP_WS:"/v1/ws/shop",WIDGET_STATUS:"/v1/widget/status"}),I=Object.freeze({AUDIO_CHUNK:"audio_chunk",AUDIO_END:"audio_end",CONFIG:"config",DONE:"done",ERROR:"error",TEXT_CHUNK:"text_chunk",TRANSCRIPT:"transcript"});var ae=new Set(["cart","/cart"]),R="Recommended products",v="Relevant options",G=Object.freeze({DATA_WAV_PREFIX:"data:audio/wav;base64,",WEBM_FILENAME:"audio.webm",WEBM_MIME_TYPE:"audio/webm"}),ie=Object.freeze({POST:"POST"}),_=Object.freeze({ERROR:"error",PROCESSING:"processing",READY:"ready",RECORDING:"recording"}),yt=12,se=2400,ce=900,ue=4200,ht=1,F=180,le=3e3,V=Object.freeze({MAYABOT_ACTION:"mayabot:action"}),de=2500;var ir=["audio/webm;codecs=opus","audio/webm","audio/ogg;codecs=opus","audio/ogg","audio/mp4"],sr=250,cr=128;function pe(t,e){let n=null,r=null,o=[],a=!1,i=!1,c=!1;async function m(){if(!(i||a)){i=!0;try{let h=await navigator.mediaDevices.getUserMedia({audio:!0});r=h,c=!1;let k=ur();n=new MediaRecorder(h,k?{mimeType:k}:void 0),o=[],n.ondataavailable=T=>{T.data.size>0&&o.push(T.data)},n.onstop=async()=>{let T=new Blob(o,{type:n.mimeType||k||G.WEBM_MIME_TYPE});if(z(),c){c=!1;return}if(T.size<cr){console.warn("Microphone recording was empty or too short",{size:T.size}),e(_.READY);return}await t(T)},n.onerror=T=>{console.error("Microphone recording failed",T.error||T),a=!1,i=!1,z(),e(_.ERROR,"Recording failed")},n.start(sr),a=!0,e(_.RECORDING)}catch(h){console.error("Microphone access denied",h),e(_.ERROR,"Mic unavailable")}finally{i=!1}}}function b({discard:h=!1}={}){if(c=h,n&&n.state!=="inactive"){try{n.requestData()}catch{}n.stop(),a=!1,h||e(_.PROCESSING);return}a=!1,z(),h||e(_.PROCESSING)}function N(){i||(a?b():m())}function pt(){b({discard:!0})}function z(){r&&(r.getTracks().forEach(h=>h.stop()),r=null)}return{toggle:N,cancel:pt}}function ur(){return!("MediaRecorder"in window)||typeof MediaRecorder.isTypeSupported!="function"?"":ir.find(t=>MediaRecorder.isTypeSupported(t))||""}var fe="shopify",me="woocommerce",lr="custom";function tt(t){let e=String(t||"").trim();return/^\d+$/.test(e)?e:""}function et(t,e=1){let n=Number(t?.[l.QUANTITY]);return Number.isFinite(n)&&n>0?Math.floor(n):e}async function D(t,e){return(await fetch(new URL(t,window.location.origin),{method:"POST",headers:{Accept:"application/json","Content-Type":"application/json"},body:JSON.stringify(e),credentials:"same-origin"})).ok}function dr(){return pr()?fe:fr()?me:lr}async function _e(t){let e=dr();return e===fe?mr(t):e===me?_r(t):!1}function pr(){return!!(window.Shopify||document.querySelector('meta[name="shopify-checkout-api-token"]')||document.querySelector('script[src*="cdn.shopify.com"]'))}function fr(){return!!(document.body?.classList?.contains("woocommerce")||window.wc_add_to_cart_params||document.querySelector('link[href*="woocommerce"], script[src*="woocommerce"]'))}async function mr(t){let e=t.parameters||{};if(t.action===s.ADD_TO_CART){let n=tt(e.variant_id||e.cart_id||e[l.PRODUCT_ID]);return n?D("/cart/add.js",{items:[{id:n,quantity:et(e)}]}):!1}if(t.action===s.REMOVE_FROM_CART){let n=tt(e.cart_id||e.variant_id||e[l.PRODUCT_ID]);return n?D("/cart/change.js",{id:n,quantity:0}):!1}if(t.action===s.UPDATE_CART_QUANTITY){let n=tt(e.cart_id||e.variant_id||e[l.PRODUCT_ID]);return n?D("/cart/change.js",{id:n,quantity:et(e,0)}):!1}return t.action===s.CLEAR_CART?D("/cart/clear.js",{}):t.action===s.CHECKOUT?nt("/checkout"):ye(t)?nt("/cart"):!1}async function _r(t){let e=t.parameters||{};if(t.action===s.ADD_TO_CART){let n=tt(e.variant_id||e.cart_id||e[l.PRODUCT_ID]);return n?D("/wp-json/wc/store/cart/add-item",{id:Number(n),quantity:et(e)}):!1}if(t.action===s.REMOVE_FROM_CART){let n=String(e.cart_key||e.key||"").trim();return n?D("/wp-json/wc/store/cart/remove-item",{key:n}):!1}if(t.action===s.UPDATE_CART_QUANTITY){let n=String(e.cart_key||e.key||"").trim();return n?D("/wp-json/wc/store/cart/update-item",{key:n,quantity:et(e,0)}):!1}return t.action===s.CHECKOUT?nt("/checkout"):ye(t)?nt("/cart"):!1}function ye(t){return t.action===s.NAVIGATE_TO&&ae.has(t.parameters?.[l.PAGE])}function nt(t){return window.location.href=t,!0}var yr="/v1/widget/action-event";function A(t){return String(t||"").trim()}function hr(t,e){return new URL(t,e).toString()}function gr(t){return!t||typeof t!="object"?[]:Object.keys(t).map(e=>A(e)).filter(Boolean).slice(0,20)}function br(t){if(!t||typeof t!="object")return{};let e={};for(let[n,r]of Object.entries(t).slice(0,20)){let o=A(n).slice(0,80);o&&(typeof r=="boolean"||r===null?e[o]=r:typeof r=="number"?e[o]=Number.isFinite(r)?r:0:e[o]=A(r).slice(0,240))}return e}async function rt(t,e,n,r){if(!t||!e||!n?.action)return;let o=JSON.stringify({site_id:e,origin:window.location.origin,url:window.location.href,occurred_at:new Date().toISOString(),request_id:A(n.request_id||n.action_request_id),turn_id:A(n.turn_id),sequence:Number(n.sequence||0),action:A(n.action).toUpperCase(),status:A(r?.status)||"unknown",stage:A(r?.stage),reason:A(r?.reason),duration_ms:Number(r?.duration_ms||0),param_keys:gr(n.parameters||n.params),requested_url:A(r?.requested_url),final_url:A(r?.final_url||window.location.href),evidence:br(r?.evidence)}),a=hr(yr,t);if(!Tr(a,o))try{await fetch(a,{method:"POST",headers:{Accept:"application/json","Content-Type":"application/json"},body:o,keepalive:!0})}catch(i){console.warn("[AIHubAdapter] Action execution report failed.",i)}}function Tr(t,e){if(typeof navigator>"u"||typeof navigator.sendBeacon!="function"||typeof Blob!="function")return!1;try{return navigator.sendBeacon(t,new Blob([e],{type:"application/json"}))}catch{return!1}}function he(t){if(!t||typeof t!="string")return[];let e=[];for(let n of Ar()){try{e.push(...Array.from(n.querySelectorAll(t)))}catch{return[]}if(e.length>=600)return e.slice(0,600)}return Or(e)}function Ar(){let t=[],e=new Set,n=[document];for(;n.length&&t.length<60;){let r=n.shift();!r||e.has(r)||(e.add(r),t.push(r),n.push(...Er(r)))}return t}function Er(t){let e=[];for(let n of Sr(t)){n.shadowRoot&&e.push(n.shadowRoot);let r=Ir(n);r&&e.push(r)}return e}function Sr(t){try{return Array.from(t.querySelectorAll("*"))}catch{return[]}}function Ir(t){if(String(t?.tagName||"").toLowerCase()!=="iframe")return null;try{let e=t.contentDocument;return e?.documentElement?e:null}catch{return null}}function Or(t){return Array.from(new Set(t))}var Xa=Object.freeze([u("stripe",["stripe","stripe.com","checkout.stripe.com","js.stripe.com"]),u("paypal",["paypal","paypal.com","paypalobjects.com"]),u("razorpay",["razorpay","checkout.razorpay.com"]),u("paytm",["paytm","securegw.paytm.in"]),u("cashfree",["cashfree","cashfree.com"]),u("checkout.com",["checkout.com","cko-session-id"]),u("adyen",["adyen","checkoutshopper"]),u("square",["squareup","squarecdn","square.site"]),u("braintree",["braintree","braintreegateway"]),u("mollie",["mollie","mollie.com"]),u("klarna",["klarna","klarna.com"]),u("afterpay",["afterpay","afterpay.com","clearpay"]),u("payu",["payu","payu.in","payu.com"]),u("paystack",["paystack","paystack.co"]),u("phonepe",["phonepe","phonepe.com"]),u("billdesk",["billdesk","billdesk.com"]),u("authorize.net",["authorize.net","accept.authorize.net"])]),ge=Object.freeze([u("calendly",["calendly","calendly.com"]),u("acuity",["acuityscheduling","squarespace scheduling"]),u("booksy",["booksy","booksy.com"]),u("zocdoc",["zocdoc","zocdoc.com"]),u("appointlet",["appointlet","appointlet.com"]),u("setmore",["setmore","setmore.com"]),u("cal.com",["cal.com","calcom"]),u("google_calendar",["calendar.google.com","google calendar"]),u("microsoft_bookings",["microsoft bookings","outlook.office365.com/book"]),u("simplybook",["simplybook","simplybook.me"]),u("tidycal",["tidycal","tidycal.com"]),u("savvycal",["savvycal","savvycal.com"]),u("fresha",["fresha","fresha.com"])]),be=Object.freeze([u("google_maps",["google.com/maps","maps.googleapis","maps.google"]),u("mapbox",["mapbox","mapbox.com"]),u("openstreetmap",["openstreetmap","osm.org"]),u("leaflet",["leaflet","leafletjs"]),u("here_maps",["here.com","hereapi","wego.here.com"]),u("bing_maps",["bing.com/maps","virtualearth"]),u("mappls",["mappls","mapmyindia"])]),Te=Object.freeze([u("whatsapp",["wa.me","api.whatsapp.com","web.whatsapp.com"]),u("telegram",["t.me/","telegram.me"]),u("messenger",["m.me/","messenger.com/t"]),u("zendesk",["zendesk.com","zdassets.com/hc"]),u("intercom",["intercom.help","intercom.com"]),u("freshchat",["freshchat.com"])]),Ja=Object.freeze([u("recaptcha",["recaptcha","g-recaptcha","google.com/recaptcha"]),u("hcaptcha",["hcaptcha","h-captcha"]),u("turnstile",["turnstile","challenges.cloudflare.com"]),u("cloudflare_challenge",["cf-chl","cloudflare challenge"])]);function u(t,e){return{name:t,tokens:e}}function gt(t,e,n=10){let r=bt(t);return e.filter(o=>o.tokens.some(a=>r.includes(a))).map(o=>o.name).slice(0,n)}function bt(t){return String(t||"").replace(/\s+/g," ").trim().toLowerCase()}var Ae="a[href], iframe[src]",wr="a[href]",Se=new Set(["http:","https:"]),ot=new Set(["mailto:","tel:"]),xr=Object.freeze([l.URL,"href","link","target_url","provider_url","booking_url","appointment_url","calendar_url","map_url","location_url","contact_url"]),Ie=new Set([s.OPEN_MAP,s.OPEN_LOCATION,s.SET_LOCATION]),Oe=new Set([s.CHECK_APPOINTMENT_AVAILABILITY,s.REQUEST_APPOINTMENT,s.BOOK_APPOINTMENT_REQUEST,s.REQUEST_CONSULTATION,s.REQUEST_SITE_VISIT,s.START_BOOKING]),we=new Set([s.OPEN_CONTACT,s.CONTACT_AGENT,s.REQUEST_CALLBACK,s.REQUEST_COUNSELOR_CALLBACK,s.HANDOFF_TO_ADVISOR,s.HANDOFF_TO_AGENT,s.HANDOFF_TO_CLINIC,s.HANDOFF_TO_HUMAN,s.HANDOFF_TO_LAWYER,s.HANDOFF_TO_LICENSED_AGENT,s.HANDOFF_TO_RECRUITER]);function xe(t){let e=Ne(t);return Ie.has(e)||Oe.has(e)||we.has(e)}async function Re(t){let e=Ne(t);return Ie.has(e)?Tt(t,be,Ae,At):Oe.has(e)?Tt(t,ge,Ae,At):we.has(e)?Tt(t,Te,wr,Pr):!1}function Tt(t,e,n,r){let o=Rr(t?.parameters||t?.params||{},e,r);if(o)return Ee(o);let a=Cr(n,e,r);return a?Ee(a):!1}function Rr(t,e,n){for(let r of xr){let o=Ce(t?.[r]);if(o&&n(o,e))return o}return null}function Cr(t,e,n){for(let r of he(t)){let o=Nr(r);if(!(!o||!n(o,e))&&Lr(o,r,e))return o}return null}function Nr(t){return Ce(t?.getAttribute?.("href")||t?.getAttribute?.("src"))}function At(t,e){return Se.has(t.protocol)&&gt(t.href,e).length>0}function Pr(t,e){return ot.has(t.protocol)?!0:At(t,e)}function Lr(t,e,n){if(ot.has(t.protocol))return!0;let r=[t.href,e?.textContent||"",e?.getAttribute?.("aria-label")||"",e?.getAttribute?.("title")||""].join(" ");return gt(bt(r),n).length>0}function Ee(t){if(ot.has(t.protocol)||t.origin===window.location.origin)return window.location.href=t.href,!0;let e=window.open(t.href,"_blank","noopener,noreferrer");return e?(e.opener=null,!0):(window.location.href=t.href,!0)}function Ce(t){let e=String(t||"").trim();if(!e||e.startsWith("#"))return null;try{let n=new URL(e,window.location.href);return Se.has(n.protocol)||ot.has(n.protocol)?n:null}catch{return null}}function Ne(t){return String(t?.action||"").trim().toUpperCase()}var vr=Object.freeze(["title","name"]),Dr=Object.freeze(["summary","description","body"]),Ur=Object.freeze(["image_url","imageUrl","image","thumbnail"]),Mr=Object.freeze(["url","href","permalink","source_url"]),kr="knowledge_item",Fr=30;function O(t){return t==null||typeof t=="object"?"":String(t||"").trim()}function Hr(t){let e=new Set;return(Array.isArray(t)?t:[]).map(O).filter(Boolean).filter(n=>e.has(n)||e.size>=Fr?!1:(e.add(n),!0))}function at(t,e){for(let n of e){let r=O(t?.[n]);if(r)return r}return""}function q(t){return t&&typeof t=="object"&&!Array.isArray(t)?t:{}}function Br(t){let e=Yr([t?.price,t?.amount,t?.premium,t?.premium_min,t?.monthly_premium,t?.annual_premium,t?.min_price,t?.starting_price]),n=O(t?.currency||"INR");return!Number.isFinite(e)||e<=0?"":`${n} ${e.toLocaleString()}`}function Yr(t){for(let e of t){let n=Number(String(e??"").replace(/,/g,""));if(Number.isFinite(n)&&n>0)return n}return 0}function $r(t){return!t||typeof t!="object"?"":t.in_stock===!0?"Available":t.in_stock===!1?"Unavailable":O(t.status||t.availability||"")}function zr(t){let e=O(t);if(!e)return"";try{let n=new URL(e,window.location.origin);return/^https?:$/i.test(n.protocol)?n.origin===window.location.origin?`${n.pathname}${n.search}${n.hash}`:n.toString():""}catch{return""}}function jr(t){if(!t)return null;let e=O(t.id);if(!e)return null;let n=q(t.pricing),r=q(t.availability);return{id:e,externalId:O(t.external_id),entityType:O(t.entity_type||t.category_name)||kr,title:at(t,vr)||e,subtitle:O(t.subtitle||t.category_name||t.entity_type),summary:at(t,Dr),body:O(t.body),url:zr(at(t,Mr)),imageUrl:at(t,Ur),attributes:q(t.attributes),pricing:n,availability:r,location:q(t.location),contact:q(t.contact),displayPrice:Br(n),displayAvailability:$r(r)}}async function Et(t){let e=Hr(t);if(!e.length)return[];let n=new URL(S.KNOWLEDGE_BY_IDS,p.apiUrl);n.searchParams.set("site_id",p.siteId),n.searchParams.set("ids",e.join(","));let r=await fetch(n.toString(),{headers:{Accept:"application/json"}});if(!r.ok)throw new Error("Failed to fetch entities from AI Hub API");let o=(await r.json()).map(jr).filter(Boolean),a=new Map(o.map(i=>[String(i.id),i]));return e.map(i=>a.get(i)).filter(Boolean)}async function Pe(t){let[e]=await Et([t]);return e?.url||""}var Wr=2,Le=Number.POSITIVE_INFINITY,it=Number.NEGATIVE_INFINITY,ve=12,It=[],Ot=v;function C(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}function ke(t){return String(t||"item").replace(/[_-]+/g," ").trim().split(/\s+/).slice(0,Wr).join(" ")}function Gr(){if(document.getElementById("mayabot-entity-overlay-styles"))return;let t=document.createElement("style");t.id="mayabot-entity-overlay-styles",t.textContent=`
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
  `,document.head.appendChild(t)}function Vr(){Gr();let t=document.getElementById("mayabot-entity-panel");return t||(t=document.createElement("div"),t.id="mayabot-entity-panel",t.setAttribute("aria-live","polite"),t.innerHTML=`
    <div class="mayabot-entity-header">
      <h2 class="mayabot-entity-title">${v}</h2>
      <button class="mayabot-entity-close" type="button" aria-label="Close recommendations">&times;</button>
    </div>
    <div class="mayabot-entity-grid"></div>
  `,t.querySelector(".mayabot-entity-close").addEventListener("click",()=>{t.classList.remove("active")}),document.body.appendChild(t),t)}function qr(t){return t<=1?"count-1":t===2?"count-2":t===3?"count-3":"count-many"}function Kr(t){return t<=1?1:t===2?2:3}function St(t,e,n=""){let r=(Array.isArray(e)?e:[]).map(c=>String(c?.id??"").trim()).filter(Boolean),o=r.length,a=t.length,i=o>0?"succeeded":"failed";return{status:i,stage:"entity_overlay",reason:n||(i==="succeeded"?"":"no_matching_entities_rendered"),evidence:{requested_entity_count:a,rendered_entity_count:o,missing_entity_count:Math.max(a-o,0),requested_entity_ids:t.slice(0,ve).join(","),rendered_entity_ids:r.slice(0,ve).join(",")}}}function Qr(t){return[t.displayPrice,t.displayAvailability,t.location?.city,t.attributes?.category].map(e=>String(e||"").trim()).filter(Boolean).slice(0,3)}function Xr(t){return t.imageUrl?`
      <div class="mayabot-entity-media">
        <img src="${C(t.imageUrl)}" alt="${C(t.title)}">
      </div>
    `:`
    <div class="mayabot-entity-media">
      <div class="mayabot-entity-badge">${C(ke(t.entityType))}</div>
    </div>
  `}function Jr(t){let e=Qr(t);return e.length?`
    <div class="mayabot-entity-facts">
      ${e.map(n=>`<span class="mayabot-entity-fact">${C(n)}</span>`).join("")}
    </div>
  `:""}function Zr(t){return t.url?`
    <div class="mayabot-entity-actions">
      <button type="button" data-view-entity="${C(t.id)}">Open</button>
    </div>
  `:""}function ct(t,e){let n=Vr(),r=n.querySelector(".mayabot-entity-grid"),o=n.querySelector(".mayabot-entity-title"),a=t.length;if(It=Array.isArray(t)?[...t]:[],Ot=e||v,n.classList.remove("count-1","count-2","count-3","count-many"),n.classList.add(qr(a)),n.style.setProperty("--mayabot-entity-card-count",String(Kr(a))),o.textContent=Ot,!a){r.innerHTML='<p class="mayabot-entity-empty">No matching records are currently available.</p>',n.classList.add("active"),De();return}r.innerHTML=t.map(i=>`
        <article class="mayabot-entity-card" data-entity-id="${C(i.id)}">
          ${Xr(i)}
          <h3 class="mayabot-entity-name">${C(i.title)}</h3>
          <p class="mayabot-entity-meta">${C(i.subtitle||ke(i.entityType))}</p>
          <p class="mayabot-entity-summary">${C(i.summary||i.body||"Details are available on the website.")}</p>
          ${Jr(i)}
          ${Zr(i)}
        </article>
      `).join(""),r.querySelectorAll("[data-view-entity]").forEach(i=>{i.addEventListener("click",async()=>{await wt(i.getAttribute("data-view-entity"))})}),n.classList.add("active"),De()}function to(t){if(!t)return!1;try{let e=new URL(t,window.location.origin);return e.origin===window.location.origin?(window.location.href=`${e.pathname}${e.search}${e.hash}`,!0):(window.open(e.toString(),"_blank","noopener,noreferrer"),!0)}catch{return!1}}function De(){window.setTimeout(()=>{let t=document.getElementById("mayabot-chat"),e=document.getElementById("mayabot-msgs");e&&(e.innerHTML=""),t&&t.classList.remove("visible")},F)}async function wt(t){let e=await Pe(t);return to(e)}async function Fe(t,e=v){let n=xt({[l.ENTITY_IDS]:t});if(!n.length)return ct([],e),St([],[],"missing_entity_ids");try{let r=await Et(n);return ct(r,e),St(n,r)}catch(r){return console.warn("[AI Hub Widget] Entity overlay failed:",r),ct([],e),St(n,[],"entity_overlay_fetch_failed")}}function xt(t){let e=t[l.ENTITY_IDS]||t.ids||t.items||[],n=new Set;return(Array.isArray(e)?e:[]).map(r=>String(r??"").trim()).filter(Boolean).filter(r=>n.has(r)?!1:(n.add(r),!0))}function He(t={}){if(!It.length)return!1;let e=String(t.sort_by||t.sortBy||"price_asc").trim().toLowerCase(),n=[...It].sort((o,a)=>eo(o,a,e)),r=ro(Ot,e);return ct(n,r),!0}function eo(t,e,n){return n==="price_desc"?st(e,it)-st(t,it):n==="rating"?Ue(e,it)-Ue(t,it):n==="newest"?Me(e)-Me(t):st(t,Le)-st(e,Le)}function st(t,e){return Be([t?.pricing?.price,t?.pricing?.amount,t?.pricing?.premium,t?.pricing?.premium_min,t?.pricing?.monthly_premium,t?.pricing?.annual_premium,t?.pricing?.min_price,t?.pricing?.starting_price,t?.attributes?.price,t?.attributes?.amount,t?.attributes?.premium,t?.attributes?.monthly_premium,t?.attributes?.annual_premium,t?.displayPrice],e)}function Ue(t,e){return Be([t?.attributes?.rating,t?.attributes?.review_rating,t?.attributes?.stars,t?.availability?.rating],e)}function Me(t){let e=t?.attributes?.updated_at||t?.attributes?.date||t?.availability?.updated_at||"",n=Date.parse(String(e||""));return Number.isFinite(n)?n:0}function Be(t,e){for(let n of t){let r=no(n);if(Number.isFinite(r))return r}return e}function no(t){if(typeof t=="number")return t;let e=String(t??"").replace(/,/g,"").match(/-?\d+(?:\.\d+)?/);return e?Number(e[0]):Number.NaN}function ro(t,e){let n={price_asc:"sorted low to high",price_desc:"sorted high to low",rating:"sorted by rating",newest:"newest first"};return`${String(t||v).replace(/\s+-\s+sorted.*$/i,"")} - ${n[e]||n.price_asc}`}function Ye(t){return t.action===s.SHOW_ENTITIES||t.action===s.COMPARE_ENTITIES||t.action===s.OPEN_ENTITY_DETAIL||t.action===s.SORT_ENTITIES}async function $e(t){return t.action===s.SHOW_ENTITIES||t.action===s.COMPARE_ENTITIES?oo(t.parameters||{}):t.action===s.OPEN_ENTITY_DETAIL?wt(t.parameters?.[l.ENTITY_ID]||t.parameters?.id):t.action===s.SORT_ENTITIES?He(t.parameters||{}):!1}function oo(t){return Fe(xt(t),t[l.SEARCH_QUERY]||t.title||v)}var K="mayabot-handoff-panel",ze="mayabot-handoff-overlay-styles",ao=Object.freeze(["contact","support","help"]),io=Object.freeze(["checkout","cart"]),Ve=new Set([s.CHECKOUT_HANDOFF,s.HANDOFF_TO_ADVISOR,s.HANDOFF_TO_AGENT,s.HANDOFF_TO_CLINIC,s.HANDOFF_TO_HUMAN,s.HANDOFF_TO_LAWYER,s.HANDOFF_TO_LICENSED_AGENT,s.HANDOFF_TO_RECRUITER]),je=Object.freeze({[s.CHECKOUT_HANDOFF]:{title:"Checkout needs your confirmation",body:"This step may include payment or a secure checkout page. I can take you there, then you complete the final step yourself.",primary:"Open checkout"},[s.HANDOFF_TO_ADVISOR]:{title:"Advisor handoff",body:"This request needs a qualified advisor. I can open the contact path so the site team can continue.",primary:"Contact advisor"},[s.HANDOFF_TO_AGENT]:{title:"Agent handoff",body:"This step needs an agent or account-specific help. I can open the contact path for follow-up.",primary:"Contact agent"},[s.HANDOFF_TO_CLINIC]:{title:"Clinic handoff",body:"This request needs clinic confirmation. I can open the appointment or contact path for the next step.",primary:"Contact clinic"},[s.HANDOFF_TO_HUMAN]:{title:"Human handoff",body:"This step needs human confirmation. I can open the most relevant contact path.",primary:"Open contact"},[s.HANDOFF_TO_LAWYER]:{title:"Legal handoff",body:"This request needs a legal professional. I can open the consultation or contact path.",primary:"Contact lawyer"},[s.HANDOFF_TO_LICENSED_AGENT]:{title:"Licensed agent handoff",body:"This request needs a licensed agent. I can open the quote or contact path for follow-up.",primary:"Contact agent"},[s.HANDOFF_TO_RECRUITER]:{title:"Recruiter handoff",body:"This request needs recruiter review. I can open the application or contact path.",primary:"Contact recruiter"}});function H(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}function U(t){return String(t||"").trim()}function so(){if(document.getElementById(ze))return;let t=document.createElement("style");t.id=ze,t.textContent=`
    #${K} {
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
    #${K}.active {
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
      #${K} {
        bottom: 82px;
        width: min(calc(100vw - 20px), 420px);
      }
    }
  `,document.head.appendChild(t)}function co(){so();let t=document.getElementById(K);return t||(t=document.createElement("div"),t.id=K,t.setAttribute("aria-live","polite"),document.body.appendChild(t),t)}function uo(){return window.AIHubAdapterRuntime?.config?.adapter?.routes||window.AIHubAdapter?.config?.adapter?.routes||{}}function lo(t,e){let n=We(e[l.URL]||e.path||e.href||e.handoff_flow?.page_url);if(n)return n;let r=uo(),o=t===s.CHECKOUT_HANDOFF?io:ao;for(let a of o){let i=We(r[a]);if(i)return i}return""}function We(t){let e=U(t);if(!e)return"";try{let n=new URL(e,window.location.origin);return n.origin!==window.location.origin?"":`${n.pathname}${n.search}${n.hash}`||"/"}catch{return""}}function po(t){return je[t]||je[s.HANDOFF_TO_HUMAN]}function fo(t){return t&&typeof t=="object"?t:{}}function mo(t,e){return U(t.title)||e}function _o(t,e,n){return U(e[l.MESSAGE])||U(t.handling)||n}function yo(t,e){return U(e[l.REASON]||e.reason||e.blocked_reason||t.key)}function ho(t){let e=[["Provider",t.provider_label||t.provider],["Boundary",t.automation_boundary],["Recovery",t.recovery],["Evidence",t.evidence],["Page",t.page_url]].filter(([,n])=>U(n));return e.length?`
    <p class="mayabot-handoff-meta">
      ${e.map(([n,r])=>`<span><strong>${H(n)}:</strong> ${H(r)}</span>`).join("")}
    </p>
  `:""}function Ge(t){t.classList.remove("active")}function go(){window.setTimeout(()=>{let t=document.getElementById("mayabot-chat"),e=document.getElementById("mayabot-msgs");e&&(e.innerHTML=""),t&&t.classList.remove("visible")},F)}function qe(t,e={}){let n=U(t).toUpperCase(),r=po(n),o=fo(e.handoff_flow),a=co(),i=lo(n,e),c=mo(o,r.title),m=_o(o,e,r.body),b=yo(o,e);return a.innerHTML=`
    <div class="mayabot-handoff-body">
      <div class="mayabot-handoff-top">
        <h2 class="mayabot-handoff-title">${H(c)}</h2>
        <button class="mayabot-handoff-close" type="button" aria-label="Close handoff">&times;</button>
      </div>
      <p class="mayabot-handoff-text">${H(m)}</p>
      ${ho(o)}
      ${b?`<p class="mayabot-handoff-reason">${H(b)}</p>`:""}
      <div class="mayabot-handoff-actions">
        <button type="button" class="secondary" data-close-handoff>Close</button>
        ${i?`<button type="button" data-open-handoff>${H(r.primary)}</button>`:""}
      </div>
    </div>
  `,a.querySelector(".mayabot-handoff-close")?.addEventListener("click",()=>Ge(a)),a.querySelector("[data-close-handoff]")?.addEventListener("click",()=>Ge(a)),a.querySelector("[data-open-handoff]")?.addEventListener("click",()=>{window.location.href=i}),a.classList.add("active"),go(),!0}function Ke(t){return Ve.has(t.action)}function Qe(t){return qe(t.action,t.parameters||{})}function Je(t){return t.action===s.NAVIGATE_TO&&!!tn(t.parameters?.[l.PAGE])}function Ze(t){return window.location.href=tn(t.parameters?.[l.PAGE]),!0}function tn(t){let e=String(t||"").trim();if(!e||en(e)||/^https?:\/\//i.test(e))return"";if(e==="home"||e==="/")return"/";let n=bo(e);if(n)return n;let r=e.replace(/^\/+|\/+$/g,"");return r?`/${r}`:"/"}function bo(t){let e=window.AIHubAdapterRuntime?.config?.adapter?.routes||window.AIHubAdapter?.config?.adapter?.routes||{},n=To(t);for(let r of n){let o=e[r],a=Xe(o);if(a)return a}for(let[r,o]of Object.entries(e)){if(!n.includes(Rt(r)))continue;let a=Xe(o);if(a)return a}return""}function To(t){let e=Rt(t),n=String(t||"").trim().replace(/^\/+|\/+$/g,"").toLowerCase(),r=n.split("?")[0].split("#")[0].split("/").filter(Boolean).pop()||"";return Array.from(new Set([e,n,Rt(r)].filter(Boolean)))}function Rt(t){return String(t||"").trim().toLowerCase().replace(/[^a-z0-9/_\s-]+/g," ").replace(/[_-]+/g," ").replace(/\s+/g," ").trim().replace(/\s+/g,"-")}function Xe(t){let e=String(t||"").trim();if(!e||en(e))return"";if(/^https?:\/\//i.test(e))try{let n=new URL(e);return n.origin!==window.location.origin?"":`${n.pathname||"/"}${n.search||""}${n.hash||""}`}catch{return""}return e.startsWith("/")?e:`/${e.replace(/^\/+/,"")}`}function en(t){return/^(?:javascript:|data:|\/\/)/i.test(String(t||"").trim())}function nn(t){let e=t?.params||t?.parameters||{};return{...t||{},action:String(t?.action||"").trim().toUpperCase(),params:e,parameters:e}}var Ct="AIHubAdapterRuntime",Nt="AIHubAdapter";function Ao(t){let e=t?.params||t?.parameters||{};return{...t||{},params:e,parameters:e}}function Q(){return!!(window[Ct]?.executeAction||window[Nt]?.handleAction)}async function Pt(t){return(await X(t)).succeeded}async function X(t){let e=Ao(t);if(window[Ct]?.executeAction){let n=window[Ct],r=await n.executeAction(e)===!0,o=n.lastActionResult||{};return{succeeded:r,handled:o.handled===!0||r,status:o.status||(r?"ok":"not_handled"),reason:o.reason||"",blocked:o.status==="blocked",disabled:o.status==="disabled"}}if(window[Nt]?.handleAction){let n=await window[Nt].handleAction(e)===!0;return{succeeded:n,handled:n,status:n?"ok":"not_handled",reason:"",blocked:!1,disabled:!1}}return{succeeded:!1,handled:!1,status:"missing_adapter",reason:"",blocked:!1,disabled:!1}}var Eo=Object.freeze([{path:"/api/products?per_page=96",routePrefix:"/product/"},{path:"/api/products",routePrefix:"/product/"},{path:"/api/products.json",routePrefix:""},{path:"/products.json",routePrefix:"/products/"},{path:"/collections/all/products.json",routePrefix:"/products/"}]),So=Object.freeze(["products","data","items","results"]),on=Object.freeze(["id","product_id","handle","sku"]),an=Object.freeze(["name","title"]),Io=Object.freeze(["url","href","permalink","product_url"]),Oo=Object.freeze(["image_url","imageUrl","image_src","imageSrc","image","images","media","thumbnail","thumbnail_url","featured_image","featuredImage","featured_image_url"]),wo=Object.freeze(["brand","vendor"]),xo=Object.freeze(["category","category_name","product_type"]),Ro=Object.freeze(["description","summary","body_html"]),Co=Object.freeze(["original_price","compare_at_price","regular_price"]),sn=Object.freeze(["currency","currency_code"]),No=Object.freeze(["display_price","price_text","formatted_price"]),Po="Unknown Brand",Lo="Products",vo="/",Do=/^[a-z0-9][a-z0-9-]*$/i,Lt=null;function E(t){return t==null||typeof t=="object"?"":String(t||"").trim()}function Ut(t){return E(t).toLowerCase().replace(/[^a-z0-9]+/g," ").trim()}function cn(t){let e=new Set(["a","am","an","and","ask","asked","did","for","me","not","on","only","please","show","some","the","to","wanna","want","what","with","you","your"]),n=[],r=new Set;for(let o of Uo(Ut(t)).split(" ")){let a=Mo(o);a.length<=1||e.has(a)||r.has(a)||(n.push(a),r.add(a))}return n}function Uo(t){return t.replace(/\b(?:i\s+)?did\s+not\s+ask\s+for\s+(?:a\s+|an\s+)?[a-z0-9]+\b/g," ")}function Mo(t){return["phone","phones","mobile","mobiles"].includes(t)?"phone":["book","books"].includes(t)?"books":t}function Mt(t,e){return e.map(n=>E(t?.[n])).filter(Boolean)}function w(t,e){return Mt(t,e)[0]||""}function ut(t){let e=E(t).replace(/,/g,"");if(!e)return 0;let n=e.match(/-?\d+(?:\.\d+)?/),r=Number(n?n[0]:e);return Number.isFinite(r)?r:0}function ko(t,e){let n=w(t,No);if(n)return n;let r=w(t,sn).toUpperCase();return e>0&&r?`${r} ${e.toLocaleString()}`:e>0?e.toLocaleString():""}function Fo(t){for(let e of Oo){let n=vt(t?.[e]);if(n)return n}return""}function vt(t){if(!t)return"";if(Array.isArray(t)){for(let e of t){let n=vt(e);if(n)return n}return""}if(typeof t=="object"){for(let e of["src","url","image_url","imageUrl","image_src","imageSrc","thumbnail","thumbnail_url","featured_image","featuredImage","featured_image_url"]){let n=vt(t[e]);if(n)return n}return""}return Ho(t)}function Ho(t){let e=E(t);if(!e||/^javascript:/i.test(e))return"";if(/^data:image\//i.test(e))return e;try{let n=new URL(e,window.location.origin);return["http:","https:"].includes(n.protocol)?n.toString():""}catch{return""}}function Bo(t){let e=E(t);if(!e)return"";try{let n=new URL(e,window.location.origin);return n.origin!==window.location.origin?"":`${n.pathname}${n.search}${n.hash}`}catch{return""}}function Yo(t,e,n){let r=Bo(w(t,Io));return r||(!Do.test(e)||!/[a-z]/i.test(e)||!n?.routePrefix?"":`${n.routePrefix}${encodeURIComponent(e)}${vo}`)}function kt(t,e={}){if(!t)return null;let n=w(t,on),r=E(t.handle||t.slug||t.product_handle),o=w(t,an),a=ut(t.price||t.amount||t.cost),i=ut(w(t,Co));return!n&&!r?null:{id:n,handle:r,name:o,title:E(t.title||o),brand:w(t,wo)||Po,category:w(t,xo)||Lo,description:w(t,Ro),price:Number.isFinite(a)?a:0,originalPrice:Number.isFinite(i)?i:0,displayPrice:ko(t,a),currency:w(t,sn),rating:ut(t.rating||t.review_rating),reviewCount:ut(t.review_count||t.reviews_count||t.reviews),imageUrl:Fo(t),url:Yo(t,r||n,e)}}function $o(t){return Mt(t,on)}function rn(t){return Mt(t,an).map(Ut)}function un(t,e){let n=E(e);return!!(n&&$o(t).includes(n))}function ln(t,e){let n=cn(e);if(!n.length)return!1;let r=Ut([t?.name,t?.title,t?.brand,t?.category,t?.category_name,t?.product_type,t?.description,t?.tags].join(" "));return n.every(o=>r.includes(o)||r.includes(o.replace(/s$/,"")))}function zo(t,e){let n=new Set(rn(e));return rn(t).some(r=>n.has(r))}function jo(t,e){return!!(t?.imageUrl&&t.imageUrl===e?.imageUrl)}function Wo(t){if(Array.isArray(t))return t;for(let e of So){let n=t?.[e];if(Array.isArray(n))return n}return[]}async function Go(t){try{let e=await fetch(new URL(t.path,window.location.origin),{headers:{Accept:"application/json"}});if(!e.ok)return[];let n=await e.json();return Wo(n).map(r=>kt(r,t)).filter(Boolean)}catch(e){return console.warn(`[AI Hub Widget] Catalog endpoint lookup failed for ${t.path}:`,e),[]}}async function Dt(){return Lt||(Lt=Promise.all(Eo.map(Go)).then(t=>t.flat())),Lt}async function Vo(t,e=120){if(!cn(t).length)return[];let r=new URL("/v1/products",p.apiUrl);r.searchParams.set("site_id",p.siteId),r.searchParams.set("limit",String(e));try{let o=await fetch(r.toString(),{headers:{Accept:"application/json"}});return o.ok?(await o.json()).map(a=>kt(a)).filter(Boolean).filter(a=>ln(a,t)).slice(0,12):[]}catch(o){return console.warn("[AI Hub Widget] Hub product search fallback failed:",o),[]}}async function dn(t,e=""){let n=(Array.isArray(t)?t:[]).map(E).filter(Boolean),r=[],o="",a="";if(n.length)try{r=await pn(n),o="hub_by_ids"}catch(i){a="hub_product_lookup_failed",console.warn("[AI Hub Widget] Hub product ID lookup failed:",i)}if(!r.length&&n.length){let i=await Dt();r=n.map(c=>i.find(m=>un(m,c))).filter(Boolean),r.length&&(o="host_by_ids")}return!r.length&&e&&(r=await Vo(e),r.length&&(o="hub_search")),!r.length&&e&&(r=(await Dt()).filter(c=>ln(c,e)).slice(0,12),r.length&&(o="host_search")),{products:r,source:o,reason:r.length?"":a||"no_matching_products_rendered"}}async function pn(t){let e=(Array.isArray(t)?t:[]).map(E).filter(Boolean);if(!e.length)return[];let n=new URL(S.PRODUCTS_BY_IDS,p.apiUrl);n.searchParams.set("site_id",p.siteId),n.searchParams.set("ids",e.join(","));let r=await fetch(n.toString(),{headers:{Accept:"application/json"}});if(!r.ok)throw new Error("Failed to fetch products from AI Hub API");let o=(await r.json()).map(i=>kt(i)).filter(Boolean),a=new Map(o.map(i=>[String(i.id),i]));return e.map(i=>a.get(i)).filter(Boolean)}async function lt(t){let e=E(t);if(!e)return"";let[n]=await pn([e]);if(n?.url)return n.url;let r=await Dt(),o=r.find(i=>un(i,e));return o?.url?o.url:n&&r.find(i=>zo(i,n)||jo(i,n))?.url||""}var qo=["data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='320' height='240' viewBox='0 0 320 240'%3E","%3Crect width='320' height='240' fill='%23f1f2ee'/%3E","%3Cpath d='M98 156h124l-31-40-25 30-17-22-51 32Z' fill='%23c8c3ba'/%3E","%3Ccircle cx='117' cy='95' r='17' fill='%23d8d3ca'/%3E","%3Ctext x='160' y='198' text-anchor='middle' fill='%23686660' font-family='Arial,sans-serif' font-size='16'%3EImage pending%3C/text%3E","%3C/svg%3E"].join(""),fn=12,Ht=[],Bt=R;function B(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}function Ko(){if(document.getElementById("mayabot-product-overlay-styles"))return;let t=document.createElement("style");t.id="mayabot-product-overlay-styles",t.textContent=`
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
      display: grid;
      grid-template-rows: auto auto auto 1fr;
      gap: 9px;
      min-width: 0;
      border: 1px solid rgba(22, 22, 21, 0.1);
      border-radius: 8px;
      background: #ffffff;
      padding: 12px;
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
      align-self: end;
      margin-top: 2px;
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
      #mayabot-product-panel.count-1,
      #mayabot-product-panel.count-2,
      #mayabot-product-panel.count-3,
      #mayabot-product-panel.count-many {
        --mayabot-card-count: 1;
      }
    }
  `,document.head.appendChild(t)}function Qo(){Ko();let t=document.getElementById("mayabot-product-panel");return t||(t=document.createElement("div"),t.id="mayabot-product-panel",t.setAttribute("aria-live","polite"),t.innerHTML=`
    <div class="mayabot-product-header">
      <h2 class="mayabot-product-title">${R}</h2>
      <button class="mayabot-product-close" type="button" aria-label="Close recommendations">&times;</button>
    </div>
    <div class="mayabot-product-grid"></div>
  `,t.querySelector(".mayabot-product-close").addEventListener("click",()=>{t.classList.remove("active")}),document.body.appendChild(t),t)}async function Xo(t){let e={action:s.ADD_TO_CART,params:{[l.PRODUCT_ID]:t,[l.QUANTITY]:ht},parameters:{[l.PRODUCT_ID]:t,[l.QUANTITY]:ht}};Q()&&await Pt(e)||window.dispatchEvent(new CustomEvent(V.MAYABOT_ACTION,{detail:e}))}async function Jo(t){try{let n=await lt(t);if(n){window.location.href=n;return}}catch(n){console.warn("[AI Hub Widget] Product detail URL lookup failed:",n)}let e={action:s.SHOW_PRODUCT_DETAIL,params:{[l.PRODUCT_ID]:t},parameters:{[l.PRODUCT_ID]:t}};Q()&&await Pt(e)||window.dispatchEvent(new CustomEvent(V.MAYABOT_ACTION,{detail:e}))}function Zo(t){return t<=1?"count-1":t===2?"count-2":t===3?"count-3":"count-many"}function ta(t){return t<=1?1:t===2?2:3}function ea(t){let e=new Set;return(Array.isArray(t)?t:[]).map(n=>String(n??"").trim()).filter(Boolean).filter(n=>e.has(n)?!1:(e.add(n),!0))}function Ft(t,e,n="",r={}){let o=(Array.isArray(e)?e:[]).map(m=>String(m?.id??"").trim()).filter(Boolean),a=o.length,i=t.length,c=a>0?"succeeded":"failed";return{status:c,stage:"product_overlay",reason:n||(c==="succeeded"?"":"no_matching_products_rendered"),evidence:{requested_product_count:i,rendered_product_count:a,missing_product_count:Math.max(i-a,0),requested_product_ids:t.slice(0,fn).join(","),rendered_product_ids:o.slice(0,fn).join(","),lookup_source:r.source||"",search_query:r.searchQuery||""}}}function na(t){let e=String(t?.displayPrice||"").trim();if(e)return e;let n=Number(t?.price||0);return Number.isFinite(n)&&n>0?n.toLocaleString():"Price unavailable"}function dt(t,e){let n=Qo(),r=n.querySelector(".mayabot-product-grid"),o=n.querySelector(".mayabot-product-title"),a=t.length;if(Ht=Array.isArray(t)?[...t]:[],Bt=e||R,n.classList.remove("count-1","count-2","count-3","count-many"),n.classList.add(Zo(a)),n.style.setProperty("--mayabot-card-count",String(ta(a))),o.textContent=Bt,!a){r.innerHTML='<p class="mayabot-product-empty">No matching products are currently available.</p>',n.classList.add("active"),mn();return}r.innerHTML=t.map(i=>{let c=B(i.id);return`
        <article class="mayabot-product-card" data-product-id="${c}">
          <img class="mayabot-product-image" src="${B(i.imageUrl||qo)}" alt="${B(i.name)}">
          <h3 class="mayabot-product-name">${B(i.name||i.title||"Product")}</h3>
          <p class="mayabot-product-meta">${B(i.brand)} - ${B(na(i))}</p>
          <div class="mayabot-product-actions">
            <button type="button" data-add="${c}">Add</button>
            <button type="button" class="secondary" data-view="${c}">View</button>
          </div>
        </article>
      `}).join(""),r.querySelectorAll("[data-add]").forEach(i=>{i.addEventListener("click",async()=>{await Xo(i.getAttribute("data-add"))})}),r.querySelectorAll("[data-view]").forEach(i=>{i.addEventListener("click",async()=>{await Jo(i.getAttribute("data-view"))})}),n.classList.add("active"),mn()}function mn(){window.setTimeout(()=>{let t=document.getElementById("mayabot-chat"),e=document.getElementById("mayabot-msgs");e&&(e.innerHTML=""),t&&t.classList.remove("visible")},F)}async function yn(t,e=R,n={}){let r=ea(t),o=String(n.searchQuery||"").trim();if(!r.length&&!o)return dt([],e),Ft([],[],"missing_product_ids");try{let{products:a,source:i,reason:c}=await dn(r,o);return dt(a,e),Ft(r,a,c,{source:i,searchQuery:o})}catch(a){return console.warn("[AI Hub Widget] Product overlay failed:",a),dt([],e),Ft(r,[],"product_overlay_fetch_failed",{searchQuery:o})}}function hn(t={}){if(!Ht.length)return!1;let e=String(t.sort_by||t.sortBy||"price_asc").trim().toLowerCase(),n=[...Ht].sort((r,o)=>ra(r,o,e));return dt(n,oa(Bt,e)),!0}function ra(t,e,n){return n==="price_desc"?Y(e.price,Number.NEGATIVE_INFINITY)-Y(t.price,Number.NEGATIVE_INFINITY):n==="rating"?Y(e.rating||e.review_rating,Number.NEGATIVE_INFINITY)-Y(t.rating||t.review_rating,Number.NEGATIVE_INFINITY):n==="newest"?_n(e)-_n(t):Y(t.price,Number.POSITIVE_INFINITY)-Y(e.price,Number.POSITIVE_INFINITY)}function Y(t,e){let n=String(t??"").replace(/,/g,"").match(/-?\d+(?:\.\d+)?/);if(!n)return e;let r=Number(n[0]);return Number.isFinite(r)?r:e}function _n(t){let e=t?.updated_at||t?.created_at||t?.date||"",n=Date.parse(String(e||""));return Number.isFinite(n)?n:0}function oa(t,e){let n={price_asc:"sorted low to high",price_desc:"sorted high to low",rating:"sorted by rating",newest:"newest first"};return`${String(t||R).replace(/\s+-\s+sorted.*$/i,"")} - ${n[e]||n.price_asc}`}function bn(t){return t.action===s.SHOW_PRODUCTS||t.action===s.SHOW_COMPARISON||t.action===s.SHOW_PRODUCT_DETAIL||t.action===s.SORT_PRODUCTS}async function Tn(t){return t.action===s.SHOW_COMPARISON?gn(t.parameters||{},"Product comparison",{syncListing:!1}):t.action===s.SHOW_PRODUCTS?gn(t.parameters||{},R):t.action===s.SHOW_PRODUCT_DETAIL?sa(t.parameters||{}):t.action===s.SORT_PRODUCTS?hn(t.parameters||{}):!1}async function gn(t,e=R,n={}){let r=Array.isArray(t[l.PRODUCT_IDS])?t[l.PRODUCT_IDS]:[],o=ia(t),i=n.syncListing!==!1?await aa(o):{succeeded:!1,handled:!1,status:"skipped",stage:"product_display_sync",reason:"comparison_overlay"},c=await yn(r,t.title||o||e,{searchQuery:o}),m={...c.evidence||{},listing_sync_status:i.status||"",listing_sync_stage:i.stage||"",listing_sync_reason:i.reason||""};return c.status!=="succeeded"?{...c,evidence:m}:o&&i.handled&&!i.succeeded?{status:"failed",stage:"product_display_sync",reason:i.reason||i.status||"listing_sync_failed",evidence:m}:{...c,stage:i.succeeded?"product_display_sync":c.stage,evidence:m}}async function aa(t){let e=An(t);return e?X({action:s.FILTER_PRODUCTS,params:{[l.SEARCH_QUERY]:e,query:e,q:e}}):{succeeded:!1,handled:!1,status:"skipped",stage:"product_display_sync",reason:"missing_search_query"}}function ia(t){return An(t[l.SEARCH_QUERY]||t.search||t.query||t.q||"")}function An(t){return String(t||"").trim()}async function sa(t){let e="";try{e=await lt(t[l.PRODUCT_ID])}catch(n){return console.warn("[AI Hub Widget] Product detail URL lookup failed:",n),!1}return e?(window.location.href=e,!0):!1}var Yt="stop_action_fallback",ca=new Set([s.SHOW_PRODUCTS,s.SHOW_COMPARISON,s.SHOW_PRODUCT_DETAIL,s.SORT_PRODUCTS]);function En(t){return Q()&&!ca.has(t.action)}async function Sn(t){let e=await X(t);return e.succeeded?!0:e.blocked||e.disabled?Yt:!1}function In(t){return window.dispatchEvent(new CustomEvent(V.MAYABOT_ACTION,{detail:t})),!0}var ua=Object.freeze([{name:"runtime_adapter",canExecute:En,execute:Sn},{name:"product_overlay",canExecute:bn,execute:Tn},{name:"entity_overlay",canExecute:Ye,execute:$e},{name:"handoff_overlay",canExecute:Ke,execute:Qe},{name:"platform_adapter",canExecute:()=>!0,execute:_e},{name:"provider_adapter",canExecute:xe,execute:Re},{name:"navigation",canExecute:Je,execute:Ze},{name:"browser_event",canExecute:()=>!0,execute:In}]);async function zt(t){let e=[];for(let n of t||[]){let r=nn(n),o=await la(r);o&&e.push(o)}return e}async function la(t){if(!t.action)return;let e=Date.now(),n=window.location.href;await rt(p.apiUrl,p.siteId,t,{status:"requested",stage:"widget_dispatch",requested_url:n,final_url:n,evidence:$t(t,n,n)}),await rt(p.apiUrl,p.siteId,t,{status:"executing",stage:"widget_dispatch",requested_url:n,final_url:window.location.href,evidence:$t(t,n,window.location.href)});let r;try{r=await da(t)}catch(i){r={status:"failed",stage:"widget_dispatch",reason:i instanceof Error?i.message:"execution_error"}}let o=window.location.href,a=$t(t,n,o,r);return await rt(p.apiUrl,p.siteId,t,{status:r.status,stage:r.stage,reason:r.reason,duration_ms:Date.now()-e,requested_url:n,final_url:o,evidence:a}),{action:t.action,request_id:t.request_id||t.action_request_id||"",turn_id:t.turn_id||"",sequence:Number(t.sequence||0),status:r.status,stage:r.stage,reason:r.reason,requested_url:n,final_url:o,evidence:a}}async function da(t){if(!t.action)return{status:"failed",stage:"normalization",reason:"missing_action"};for(let e of ua){if(!e.canExecute(t))continue;let n=await e.execute(t),r=pa(n,e.name);if(r)return r}return{status:"failed",stage:"all",reason:"no_executor_succeeded"}}function pa(t,e){if(t===!0)return{status:"succeeded",stage:e,reason:""};if(t===Yt)return{status:"blocked",stage:e,reason:"action_blocked"};if(!t||typeof t!="object")return null;let n=String(t.status||"").trim().toLowerCase();return n?{status:n,stage:String(t.stage||e).trim()||e,reason:String(t.reason||"").trim(),evidence:t.evidence&&typeof t.evidence=="object"?t.evidence:{}}:null}function $t(t,e,n,r={}){let o=t.parameters||t.params||{},a={requested_url:e,final_url:n,url_changed:e!==n,path_changed:On(e)!==On(n),title:document.title||"",stage:r.stage||"",result_status:r.status||""};return o.page&&(a.target_page=o.page),o.product_id&&(a.product_id=o.product_id),o.entity_id&&(a.entity_id=o.entity_id),Array.isArray(o.product_ids)&&(a.product_count=o.product_ids.length),Array.isArray(o.entity_ids)&&(a.entity_count=o.entity_ids.length),{...a,...r.evidence&&typeof r.evidence=="object"?r.evidence:{}}}function On(t){try{return new URL(t,window.location.href).pathname}catch{return""}}var fa=3,ma=700,_a="AIHubAdapterRuntime",ya="AIHubAdapter",$="";function ha(t,e){let n=new URL(S.SHOP_WS,t);return n.protocol=n.protocol==="https:"?"wss:":"ws:",n.searchParams.set("site_id",e),n.searchParams.set("session_id",p.sessionId),n.toString()}function ga(t){return new Promise((e,n)=>{let r=new FileReader;r.onloadend=()=>{let o=String(r.result||"");e(o.includes(",")?o.split(",").pop():o)},r.onerror=()=>n(r.error||new Error("Failed to read audio blob")),r.readAsDataURL(t)})}var jt=class{constructor(){this.queue=[],this.blocked=[],this.playing=!1,this.installUnlockListeners()}push(e,n=""){e&&(this.queue.push({audioB64:e,fallbackText:n}),this.playNext())}playNext(){if(this.playing||this.queue.length===0)return;this.playing=!0;let e=this.queue.shift(),n=new Audio(G.DATA_WAV_PREFIX+e.audioB64);n.preload="auto",n.onended=()=>{this.playing=!1,this.playNext()},n.onerror=()=>{e.fallbackText&&M(e.fallbackText),this.playing=!1,this.playNext()},n.play().catch(r=>{if(console.warn("Audio playback failed",r),this.isAutoplayBlocked(r)){e.fallbackText?M(e.fallbackText):this.blocked.unshift(e),this.playing=!1;return}e.fallbackText&&M(e.fallbackText),this.playing=!1,this.playNext()})}installUnlockListeners(){if(typeof window>"u")return;let e=()=>{this.retryBlocked(),Sa()};window.addEventListener("pointerdown",e,{capture:!0,passive:!0}),window.addEventListener("keydown",e,{capture:!0}),window.addEventListener("touchstart",e,{capture:!0,passive:!0})}retryBlocked(){this.blocked.length&&(this.queue.unshift(...this.blocked.splice(0)),this.playNext())}speakInsteadOfBlocked(e){!e||!this.blocked.length||(this.blocked=[],M(e))}isAutoplayBlocked(e){let n=`${e?.name||""} ${e?.message||e||""}`.toLowerCase();return n.includes("notallowed")||n.includes("user didn't interact")||n.includes("not allowed")}},wn=new jt,Wt=class{async sendAudio(e,n,r=[]){let o=new FormData;o.append("audio",e,Ea(e)),o.append("site_id",p.siteId),o.append("session_id",p.sessionId),r&&r.length>0&&o.append("conversation_history",JSON.stringify(r));let a=Cn();a&&o.append("page_context",JSON.stringify(a));let i=await fetch(`${p.apiUrl}${S.SHOP}`,{method:ie.POST,body:o});if(!i.ok)throw new Error("AI Hub API request failed");let c=await i.json();if(c.transcript&&n.onUserMessage?.(c.transcript),c.response_text&&n.onAssistantMessage?.(c.response_text,c.ui_actions||[]),n.onStatusChange?.(_.READY),c.audio_b64?Aa(c.audio_b64,c.response_text||""):c.response_text&&M(c.response_text),c.ui_actions&&c.ui_actions.length>0){let m=await zt(c.ui_actions);n.onActionResults?.(m)}n.onComplete?.(c)}},Gt=class{constructor(){this.ws=null,this.connected=!1,this.connecting=null,this.failed=!1,this.retries=0,this.audioQueue=wn,this.callbacks=null,this.turnText="",this.receivedAudio=!1}async ensureConnected(e=[]){return this.canUseWebSocket()?this.isOpen()?!0:this.connecting?this.connecting:(this.connecting=this.openConnection(e),this.connecting):!1}canUseWebSocket(){return!this.failed&&p.useWebSocket&&"WebSocket"in window}isOpen(){return this.connected&&this.ws?.readyState===WebSocket.OPEN}openConnection(e=[]){return new Promise(n=>{let r=new WebSocket(ha(p.apiUrl,p.siteId)),o=!1;this.ws=r;let a=(c=null)=>{o||(o=!0,this.markConnectionFailed(n,c,r))},i=window.setTimeout(()=>{a()},de);r.onopen=()=>{o||(o=!0,this.handleConnectionOpen(i,e,n))},r.onmessage=c=>{this.handleMessage(c).catch(m=>this.handleTransportError(m))},r.onerror=()=>a(i),r.onclose=()=>{this.connected=!1,a(i)}})}markConnectionOpen(){this.connected=!0,this.connecting=null,this.retries=0}handleConnectionOpen(e,n,r){window.clearTimeout(e),this.markConnectionOpen(),this.sendConfig(n),r(!0)}markConnectionFailed(e,n=null,r=null){n&&window.clearTimeout(n),this.connected=!1,this.connecting=null,this.retries+=1,this.retries>=fa&&(this.failed=!0),r&&r.readyState!==WebSocket.CLOSED&&r.close(),e(!1)}sendConfig(e=[]){this.sendJson({type:I.CONFIG,history:e||[],session_id:p.sessionId,page_context:Cn()})}sendJson(e){return!this.ws||this.ws.readyState!==WebSocket.OPEN?!1:(this.ws.send(JSON.stringify(e)),!0)}async sendAudio(e,n,r=[]){if(!await this.ensureConnected(r))return!1;this.callbacks=n,this.turnText="",this.receivedAudio=!1,this.sendConfig(r);let a=await ga(e);return this.sendJson({type:I.AUDIO_CHUNK,data:a,mime_type:e?.type||""}),this.sendJson({type:I.AUDIO_END,mime_type:e?.type||""}),!0}async handleMessage(e){let n=this.callbacks;if(!n)return;let r=this.parseMessage(e.data);if(!r){this.completeWithError(n,"Invalid WebSocket message");return}if(!this.handleIncrementalMessage(r,n)){if(r.type===I.DONE){await this.handleDoneMessage(r,n);return}r.type===I.ERROR&&this.completeWithError(n,r.message||"WebSocket error")}}parseMessage(e){try{let n=JSON.parse(e);return n&&typeof n=="object"?n:null}catch{return null}}handleIncrementalMessage(e,n){return e.type===I.TRANSCRIPT?(n.onUserMessage?.(e.text||""),!0):e.type===I.TEXT_CHUNK?(this.turnText+=e.text||"",n.onAssistantChunk?.(e.text||"",this.turnText),!0):e.type===I.AUDIO_CHUNK?(this.receivedAudio=!!e.audio_b64||this.receivedAudio,this.audioQueue.push(e.audio_b64),!0):!1}async handleDoneMessage(e,n){let r=e.response_text||this.turnText;n.onAssistantMessage?.(r,e.ui_actions||[],{streamed:!0}),n.onStatusChange?.(_.READY),!this.receivedAudio&&r?M(r):this.receivedAudio&&r&&this.audioQueue.speakInsteadOfBlocked(r);try{if(e.ui_actions&&e.ui_actions.length>0){let o=await zt(e.ui_actions);n.onActionResults?.(o)}n.onComplete?.(e)}catch(o){this.handleTransportError(o)}finally{this.callbacks=null}}completeWithError(e,n){e.onStatusChange?.(_.ERROR,Rn(n)),e.onComplete?.({error:n}),this.callbacks=null}handleTransportError(e){console.error("AI Hub WebSocket transport failed",e);let n=this.callbacks;n&&this.completeWithError(n,String(e))}},ba=new Wt,Ta=new Gt;async function xn(t,e,n,r=[]){try{if(p.useWebSocket&&await Ta.sendAudio(t,n,r))return;await ba.sendAudio(t,n,r)}catch(o){console.error(o),n.onStatusChange?.(_.ERROR,Rn(o)),n.onComplete?.({error:String(o)})}}function Aa(t,e=""){wn.push(t,e)}function Ea(t){let e=String(t?.type||"").toLowerCase();return e.includes("mp4")?"audio.mp4":e.includes("ogg")?"audio.ogg":e.includes("wav")?"audio.wav":G.WEBM_FILENAME}function Rn(t){let e=String(t?.message||t||"").toLowerCase();return e.includes("quota")?"Quota reached":e.includes("microphone")||e.includes("permission")?"Mic unavailable":e.includes("network")||e.includes("fetch")||e.includes("api request")?"Connection issue":"Try again"}function M(t){if(!t||!("speechSynthesis"in window)||!("SpeechSynthesisUtterance"in window))return!1;$=String(t).slice(0,ma);let e=new SpeechSynthesisUtterance($);e.rate=1,e.pitch=1,e.volume=1,e.onstart=()=>{$=""},e.onend=()=>{$=""};try{return window.speechSynthesis.cancel(),window.speechSynthesis.resume(),window.speechSynthesis.speak(e),!0}catch(n){return console.warn("Fallback speech failed",n),!1}}function Sa(){$&&M($)}function Cn(){let t=window[_a],e=window[ya];try{if(typeof t?.getContext=="function")return t.getContext();if(typeof e?.getContext=="function")return e.getContext()}catch(n){console.warn("[AI Hub Widget] Page context collection failed:",n)}return null}window.__mayabot_identifier="voice-orb";var Vt=null,Nn=null,Z="",J="",Ia=1,Oa=1.08,wa=300,xa=Object.freeze(["hannah","zira","aria","jenny","samantha","victoria","tessa","moira","karen","female","woman","nova","shimmer","google us english","microsoft aria"]);function Pn(){if(window.__mayabotBooted||document.getElementById("mayabot-widget"))return;window.__mayabotBooted=!0,Qt();let t=oe(),e=null;function n(d=se){e&&window.clearTimeout(e),e=window.setTimeout(()=>{t.msgs.innerHTML="",t.chat.classList.remove("visible"),e=null},d)}function r(d,f=""){t.status.className="",d===_.RECORDING?(e&&(window.clearTimeout(e),e=null),t.msgs.innerHTML="",t.btn.classList.add("recording"),t.chat.classList.add("visible"),t.status.innerText="Listening...",t.status.classList.add("listening")):d===_.PROCESSING?(t.btn.classList.remove("recording"),t.chat.classList.add("visible"),t.status.innerText="Analyzing...",t.status.classList.add("processing")):d===_.READY?(t.status.innerText="Ready",t.status.classList.add("ready")):d===_.ERROR&&(t.status.innerText=f||"Try again",t.status.classList.add("error"),t.btn.classList.remove("recording"))}let o=[],a=null,i="",c=!1;function m(d,f){let y=[];for(let ft of f||[]){let P=ft.params||{};if(P[l.PRODUCT_IDS]&&Array.isArray(P[l.PRODUCT_IDS]))for(let Kt of P[l.PRODUCT_IDS])y.includes(Kt)||y.push(Kt);P[l.PRODUCT_ID]&&!y.includes(P[l.PRODUCT_ID])&&y.push(P[l.PRODUCT_ID])}return y.length>0?d+` [PRODUCT_IDS: ${y.join(",")}]`:d}function b(d,f){let y=String(f||"").trim();y&&(o.push({role:d,content:y}),o.length>yt&&o.shift())}function N(d){let f=pt(d);f&&b("assistant",f)}function pt(d){let f=(Array.isArray(d)?d:[]).map(z).filter(Boolean).slice(0,4);return f.length?`[BROWSER_ACTION_RESULTS: ${f.join(" | ")}]`:""}function z(d){if(!d||typeof d!="object"||!d.action)return"";let f=[h(d.action,40),`status=${h(d.status,24)||"unknown"}`],y=k(d.final_url);return y&&f.push(`final_path=${h(y,120)}`),d.reason&&f.push(`reason=${h(d.reason,80)}`),d.evidence?.rendered_product_count!==void 0&&f.push(`rendered_products=${Number(d.evidence.rendered_product_count||0)}`),d.evidence?.rendered_entity_count!==void 0&&f.push(`rendered_records=${Number(d.evidence.rendered_entity_count||0)}`),f.join(" ")}function h(d,f){return String(d||"").replace(/\s+/g," ").trim().slice(0,f)}function k(d){try{let f=new URL(String(d||""),window.location.href);return`${f.pathname}${f.search}${f.hash}`}catch{return""}}async function T(d){if(!c){c=!0,t.btn.disabled=!0,a=null,i="";try{await xn(d,t,{onUserMessage:f=>{W(t,f,"user"),o.push({role:"user",content:f}),o.length>yt&&o.shift()},onAssistantChunk:(f,y)=>{i=y,a||(a=W(t,"","ai")),_t(t,a,i)},onAssistantMessage:(f,y,ft={})=>{ft.streamed&&a?_t(t,a,f):W(t,f,"ai");let P=m(f,y);b("assistant",P),a=null,i=""},onActionResults:N,onStatusChange:r,onComplete:()=>n()},o)}finally{c=!1,t.btn.disabled=!1,a=null,i=""}}}let qt=pe(T,r);Vt=qt,t.btn.addEventListener("click",()=>{c||qt.toggle()}),La()&&(va(),window.setTimeout(()=>{if(o.length>0)return;let d=`Welcome to ${p.brandName}. How can I help you today?`;W(t,d,"ai"),r(_.READY),n(ue),Dn(d)},ce))}function Dn(t){if(!("speechSynthesis"in window)||!("SpeechSynthesisUtterance"in window))return;Z=t;let e=()=>{try{let n=new SpeechSynthesisUtterance(t),r=Ra(window.speechSynthesis.getVoices());r&&(n.voice=r),n.rate=Ia,n.pitch=Oa,n.onstart=()=>{Z=""},n.onend=()=>{Z=""},window.speechSynthesis.cancel(),window.speechSynthesis.resume(),window.speechSynthesis.speak(n)}catch{}};if(window.speechSynthesis.getVoices().length>0){e();return}window.speechSynthesis.onvoiceschanged=e,window.setTimeout(e,wa)}function Ra(t){if(!Array.isArray(t)||t.length===0)return null;if(J){let r=t.find(o=>o.name===J);if(r)return r}let e=p.speechVoiceName.toLowerCase();if(e){let r=t.find(o=>o.name.toLowerCase()===e);if(r)return J=r.name,r}let n=null;return p.speechVoicePreference.toLowerCase()!=="female"?n=t.find(r=>r.default)||t[0]:n=t.find(r=>xa.some(o=>r.name.toLowerCase().includes(o)))||t.find(r=>r.default)||t[0],n&&(J=n.name),n}function Ca(){Z&&Dn(Z)}function Na(){Vt?.cancel(),Vt=null,J="",window.__mayabotBooted=!1,document.getElementById("mayabot-widget")?.remove(),document.getElementById("mayabot-product-panel")?.remove();try{window.speechSynthesis?.cancel()}catch{}}async function Pa(){let t=new URL(S.WIDGET_STATUS,p.apiUrl);t.searchParams.set("site_id",p.siteId);let e=await fetch(t.toString(),{cache:"no-store",headers:{Accept:"application/json"}});return e.ok?(await e.json()).enabled!==!1:!0}async function Ln(){try{if(await Pa()){Pn();return}Na()}catch{Pn()}}function vn(){Nn||(Ln(),Nn=window.setInterval(Ln,le))}function La(){if(!p.autoGreet||!Da())return!1;try{return window.sessionStorage.getItem(Un())!=="1"}catch{return!window.__mayabotAutoGreeted}}function va(){window.__mayabotAutoGreeted=!0;try{window.sessionStorage.setItem(Un(),"1")}catch{}}function Un(){return`mayabot:auto-greeted:${p.siteId}`}function Da(){let t=window.location.pathname.replace(/\/+$/,"")||"/";return t==="/"||t.endsWith("/index.html")}document.readyState==="loading"?document.addEventListener("DOMContentLoaded",vn):vn();document.addEventListener("pointerdown",Ca,{capture:!0});})();
