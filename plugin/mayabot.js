(()=>{function fi(t){let e=String(t||"").trim(),n=e.match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/i);if(n){let i=n[1].length===3?n[1].replace(/./g,a=>a+a):n[1];return[0,2,4].map(a=>parseInt(i.slice(a,a+2),16))}let r=e.match(/rgba?\(([^)]+)\)/i);if(!r)return null;let o=r[1].split(",").map(i=>parseFloat(i));return o.length>=3&&o.slice(0,3).every(i=>!Number.isNaN(i))?o.slice(0,3):null}function wn(t){let e=t.map(n=>{let r=n/255;return r<=.03928?r/12.92:((r+.055)/1.055)**2.4});return .2126*e[0]+.7152*e[1]+.0722*e[2]}function In(t,e){let[n,r]=[wn(t),wn(e)].sort((o,i)=>i-o);return(n+.05)/(r+.05)}function mi(t,e,n){let r=n?[24,24,27]:[255,255,255],o=fi(t);if(!o)return e;if(In(o,r)>=4.5)return t;for(let i=1;i<=10;i+=1){let a=i/10,s=o.map(u=>Math.round(n?u+(255-u)*a:u*(1-a)));if(In(s,r)>=4.5)return`rgb(${s.join(", ")})`}return e}function On(){let t="#5d5fef",e=document.querySelector('meta[name="theme-color"]');if(e&&e.content)t=e.content;else{let w=document.querySelector('button[class*="primary"], .btn-primary, [data-primary]');if(w){let T=window.getComputedStyle(w).backgroundColor;T&&T!=="rgba(0, 0, 0, 0)"&&T!=="transparent"&&(t=T)}}let n=window.matchMedia&&window.matchMedia("(prefers-color-scheme: dark)").matches,r=n?"rgba(24, 24, 27, 0.75)":"rgba(255, 255, 255, 0.85)",o=n?"rgba(255, 255, 255, 0.1)":"rgba(0, 0, 0, 0.08)",i=n?"#f3f4f6":"#111827",a=n?"rgba(255, 255, 255, 0.1)":"rgba(0, 0, 0, 0.05)",s=n?"rgba(0, 0, 0, 0.25)":"#ffffff",u=mi(t,i,n),f=document.createElement("style");f.textContent=`
    :root {
      --mayabot-primary: ${t};
      --mayabot-accent-text: ${u};
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
      contain: style;
      isolation: isolate;
    }

    #mayabot-btn {
      position: relative;
      z-index: 1;
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

    /* Docked to the right edge for the full height of the window, so a long
       comparison reads as a column beside the page instead of a box floating
       over the middle of it. */
    #mayabot-chat {
      position: fixed;
      top: 0;
      bottom: 0;
      left: auto;
      right: 0;
      height: 100vh;
      height: 100dvh;
      transform: translateX(24px);
      /* A fifth of the window, bounded so it stays readable on a small screen
         and does not sprawl on a wide one. */
      width: 20vw;
      min-width: 260px;
      max-width: 380px;
      max-height: none;
      overflow: hidden;
      overscroll-behavior: contain;
      /* Room for the orb and its toggle, which stay clickable above the panel. */
      padding-bottom: 112px;
      border-radius: 20px 0 0 20px;
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
      transform: translateX(0);
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
      color: var(--mayabot-accent-text);
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

    #mayabot-msgs {
      flex: 1 1 auto;
      min-height: 0;
      overflow-y: auto;
      overscroll-behavior: contain;
      display: flex;
      flex-direction: column;
      gap: 8px;
      padding-right: 4px;
    }

    /* A small control directly above the orb, matching the direction the panel
       opens: collapsed leaves only the microphone, expanded shows the
       conversation so far. Centred on the 64px orb, clear of it by 8px. */
    #mayabot-toggle {
      position: absolute;
      right: 18px;
      bottom: 72px;
      z-index: 2;
      width: 28px;
      height: 28px;
      padding: 0;
      border-radius: 50%;
      border: 1px solid var(--mayabot-border);
      background: #ffffff;
      color: var(--mayabot-text);
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.16);
      transition: transform 0.25s ease, background-color 0.2s ease;
    }

    #mayabot-toggle svg {
      width: 14px;
      height: 14px;
    }

    #mayabot-toggle:hover {
      background: var(--mayabot-bot-bg);
    }

    #mayabot-toggle:focus-visible {
      outline: 2px solid var(--mayabot-accent-text);
      outline-offset: 2px;
    }

    /* Points up to open the column, down to close it. */
    #mayabot-toggle[aria-expanded="true"] svg {
      transform: rotate(180deg);
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
      color: var(--mayabot-accent-text);
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
        width: 100vw;
        min-width: 0;
        max-width: none;
        border-radius: 0;
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
  `,document.head.appendChild(f)}var _e="site_1",hi="__AI_";var _i="aihub:auto-site-id:",gi=["data-aihub-scope","data-site-scope"],yi=["data-site-id","data-aihub-site-id"];function C(t){return String(t||"").trim()}function At(t){return C(t).replace(/\/+$/,"")}function Rn(t,e,n,r=_e){return bi(t,e,n)||Ti()||C(r)||_e}function bi(t,e,n){for(let i of yi){let a=C(t?.getAttribute(i));if(a)return a}let r=C(e?.searchParams.get("site"))||C(e?.searchParams.get("site_id"))||C(e?.searchParams.get("shop"));if(r)return r;let o=C(n);return o&&!o.startsWith(hi)?o:""}function Ti(){let t=Ai(),e=`${_i}${t}`,n=Ri(e);if(n){let s=Ci(n);return s!==n&&xn(e,s),s}let r=C(window.location.host||window.location.hostname||"site"),o=Nn(),i=Oi(`${r}${o?`_${o.replace(/\//g,"_")}`:""}`),a=vn(`auto_${i}_${xi(t)}`);return xn(e,a),a}function Ai(){return`${window.location.origin}${Nn()}`}function Nn(){return Ei()}function Ei(){for(let e of gi){let n=C(Si()?.getAttribute(e));if(n)return Cn(n)}let t=document.querySelector("meta[name='aihub-site-scope']")?.getAttribute("content");return Cn(t)}function Si(){return document.currentScript}function Cn(t){let e=C(t);if(!e||e==="/")return"";try{let r=new URL(e,window.location.href);if(r.origin===window.location.origin){let[o]=wi(r.pathname);return o?`/${o}`:""}}catch{}let[n]=e.replace(/^\/+/,"").split("/");return n?`/${n}`:""}function wi(t=window.location.pathname){return C(t).split("/").map(e=>Ii(e).trim()).filter(Boolean)}function Ii(t){try{return decodeURIComponent(t)}catch{return String(t||"")}}function Oi(t){return C(t).toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/^_+|_+$/g,"")||"site"}function vn(t){return C(t).slice(0,80).replace(/_+$/g,"")||_e}function Ci(t){let e=C(t);return e.startsWith("auto_")?vn(e.toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/^_+|_+$/g,"")):e}function xi(t){let e=2166136261,n=C(t);for(let r=0;r<n.length;r+=1)e^=n.charCodeAt(r),e=Math.imul(e,16777619);return(e>>>0).toString(36)}function Ri(t){try{return C(window.localStorage.getItem(t))}catch{return""}}function xn(t,e){try{window.localStorage.setItem(t,e)}catch{}}var W=document.currentScript,Pn="__AI_PUBLIC_API_URL__",Ni="__AI_DEFAULT_SITE_ID__",Ln="mayabot:session:",vi="Maya",Pi="AI Salesperson",Li="female";function tt(t){return String(t||"").trim()}function Di(){let t=tt(W?.getAttribute("src"));if(!t)return null;try{return new URL(t,window.location.href)}catch{return null}}function Ui(t){let e=tt(W?.getAttribute("data-api-url"));if(e)return At(e);if(!Pn.startsWith("__AI_"))return At(Pn);if(t?.origin){let n=t.pathname.replace(/\/mayabot(?:-widget)?\.js$/,"");return At(`${t.origin}${n}`)}return At(window.location.origin)}function ki(t){let e=`${Ln}${t}`;try{let n=window.sessionStorage.getItem(e);if(n)return n;let r=ye(t);return window.sessionStorage.setItem(e,r),r}catch{return ye(t)}}function Mi(t){let e=ye(t);try{window.sessionStorage.setItem(`${Ln}${t}`,e)}catch{}return e}function ye(t){let e=window.crypto?.randomUUID?.()||`${Date.now()}-${Math.random().toString(16).slice(2)}`;return`${t}-${e}`.slice(0,120)}var Dn=Di(),ge=Rn(W,Dn,Ni),l={siteId:ge,get sessionId(){return ki(ge)},rotateSessionId(){return Mi(ge)},apiUrl:Ui(Dn),useWebSocket:tt(W?.getAttribute("data-use-websocket")).toLowerCase()==="true",autoGreet:tt(W?.getAttribute("data-auto-greet")).toLowerCase()!=="false",brandName:tt(W?.getAttribute("data-brand"))||vi,assistantTitle:tt(W?.getAttribute("data-assistant-title"))||Pi,speechVoiceName:tt(W?.getAttribute("data-speech-voice")),speechVoicePreference:tt(W?.getAttribute("data-speech-voice-preference"))||Li};function Un(){let t=document.createElement("div");t.id="mayabot-widget",t.innerHTML=`
    <div id="mayabot-chat">
      <div class="mayabot-header">
        <div>
          <span class="mayabot-kicker"></span>
          <strong class="mayabot-title"></strong>
        </div>
        <span class="mayabot-live-dot" aria-hidden="true"></span>
      </div>
      <div id="mayabot-msgs"></div>
      <div id="mayabot-status">Ready</div>
    </div>
    <button id="mayabot-toggle" type="button" aria-expanded="false" aria-controls="mayabot-chat" aria-label="Show conversation" title="Show conversation">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <polyline points="18 15 12 9 6 15"/>
      </svg>
    </button>
    <button id="mayabot-btn" aria-label="Talk to Maya">
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
        <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
        <line x1="12" x2="12" y1="19" y2="22"/>
      </svg>
      <span class="mayabot-btn-ring" aria-hidden="true"></span>
    </button>
  `,document.body.appendChild(t),t.querySelector(".mayabot-kicker").textContent=l.brandName,t.querySelector(".mayabot-title").textContent=l.assistantTitle;let e={btn:document.getElementById("mayabot-btn"),chat:document.getElementById("mayabot-chat"),msgs:document.getElementById("mayabot-msgs"),status:document.getElementById("mayabot-status"),toggle:document.getElementById("mayabot-toggle")};return Hi(e),e}function Hi(t){let{chat:e,toggle:n}=t;!e||!n||(n.addEventListener("click",()=>{be(t,!e.classList.contains("visible"),{explicit:!0})}),document.addEventListener("keydown",r=>{r.key!=="Escape"||!e.classList.contains("visible")||Fi(t)||(be(t,!1,{explicit:!0}),n.focus())}))}function Fi(t){return(t.btn?.getAttribute("data-orb-state")||"idle")!=="idle"}function be(t,e,{explicit:n=!1}={}){let{chat:r,toggle:o}=t;if(!r||(n&&(r.dataset.userCollapsed=e?"false":"true"),r.classList.toggle("visible",e),!o))return;o.setAttribute("aria-expanded",e?"true":"false");let i=e?"Hide conversation":"Show conversation";o.setAttribute("aria-label",i),o.setAttribute("title",i)}function at(t,e,n){t.chat.dataset.userCollapsed!=="true"&&be(t,!0);let r=document.createElement("div");return r.className=`mayabot-msg ${n}`,r.innerText=e,t.msgs.appendChild(r),t.msgs.scrollTop=t.msgs.scrollHeight,r}function Te(t,e,n){e&&(e.innerText=n,t.msgs.scrollTop=t.msgs.scrollHeight)}var c=Object.freeze({ADD_TO_CART:"ADD_TO_CART",BOOK_APPOINTMENT_REQUEST:"BOOK_APPOINTMENT_REQUEST",BUILD_ITINERARY:"BUILD_ITINERARY",BUILD_LEARNING_PATH:"BUILD_LEARNING_PATH",CAPTURE_LEAD:"CAPTURE_LEAD",CAPTURE_PATIENT_LEAD:"CAPTURE_PATIENT_LEAD",CHECKOUT:"CHECKOUT",CHECKOUT_HANDOFF:"CHECKOUT_HANDOFF",CHECK_APPOINTMENT_AVAILABILITY:"CHECK_APPOINTMENT_AVAILABILITY",CHECK_AVAILABILITY:"CHECK_AVAILABILITY",CHECK_DELIVERY_AVAILABILITY:"CHECK_DELIVERY_AVAILABILITY",CHECK_ELIGIBILITY_SOFT:"CHECK_ELIGIBILITY_SOFT",CHECK_PREREQUISITES:"CHECK_PREREQUISITES",CLEAR_CART:"CLEAR_CART",CLEAR_FILTERS:"CLEAR_FILTERS",CLEAR_HISTORY:"CLEAR_HISTORY",COMPARE_ENTITIES:"COMPARE_ENTITIES",CONTACT_AGENT:"CONTACT_AGENT",FILTER_ENTITIES:"FILTER_ENTITIES",FILTER_PRODUCTS:"FILTER_PRODUCTS",HANDOFF_TO_ADVISOR:"HANDOFF_TO_ADVISOR",HANDOFF_TO_AGENT:"HANDOFF_TO_AGENT",HANDOFF_TO_CLINIC:"HANDOFF_TO_CLINIC",HANDOFF_TO_HUMAN:"HANDOFF_TO_HUMAN",HANDOFF_TO_LAWYER:"HANDOFF_TO_LAWYER",HANDOFF_TO_LICENSED_AGENT:"HANDOFF_TO_LICENSED_AGENT",HANDOFF_TO_RECRUITER:"HANDOFF_TO_RECRUITER",JOIN_WAITLIST:"JOIN_WAITLIST",MATCH_JOBS:"MATCH_JOBS",NAVIGATE_TO:"NAVIGATE_TO",OPEN_CLAIM_FLOW:"OPEN_CLAIM_FLOW",OPEN_CONTACT:"OPEN_CONTACT",OPEN_DISCLOSURE:"OPEN_DISCLOSURE",OPEN_ENTITY_DETAIL:"OPEN_ENTITY_DETAIL",OPEN_LOCATION:"OPEN_LOCATION",OPEN_MAP:"OPEN_MAP",OPEN_POLICY:"OPEN_POLICY",OPEN_PROJECTS:"OPEN_PROJECTS",OPEN_RENEWAL_FLOW:"OPEN_RENEWAL_FLOW",OPEN_SERVICES:"OPEN_SERVICES",OPEN_SYLLABUS:"OPEN_SYLLABUS",OPEN_TELECONSULT:"OPEN_TELECONSULT",REMOVE_FROM_CART:"REMOVE_FROM_CART",REQUEST_APPOINTMENT:"REQUEST_APPOINTMENT",REQUEST_CALLBACK:"REQUEST_CALLBACK",REQUEST_CONSULTATION:"REQUEST_CONSULTATION",REQUEST_COUNSELOR_CALLBACK:"REQUEST_COUNSELOR_CALLBACK",REQUEST_ESTIMATE:"REQUEST_ESTIMATE",REQUEST_SITE_VISIT:"REQUEST_SITE_VISIT",REQUEST_TEST_DRIVE:"REQUEST_TEST_DRIVE",REQUEST_VIEWING:"REQUEST_VIEWING",RUN_AFFORDABILITY_CALCULATOR:"RUN_AFFORDABILITY_CALCULATOR",RUN_CALCULATOR:"RUN_CALCULATOR",RUN_DOM_SEQUENCE:"RUN_DOM_SEQUENCE",SAVE_SEARCH:"SAVE_SEARCH",SCHEDULE_ORDER:"SCHEDULE_ORDER",SEARCH_AVAILABILITY:"SEARCH_AVAILABILITY",SET_LOCATION:"SET_LOCATION",SHOW_COMPARISON:"SHOW_COMPARISON",SHOW_EMERGENCY_NOTICE:"SHOW_EMERGENCY_NOTICE",SHOW_ENTITIES:"SHOW_ENTITIES",SHOW_PRODUCT_DETAIL:"SHOW_PRODUCT_DETAIL",SHOW_PRODUCTS:"SHOW_PRODUCTS",SORT_ENTITIES:"SORT_ENTITIES",SORT_PRODUCTS:"SORT_PRODUCTS",START_APPLICATION:"START_APPLICATION",START_BOOKING:"START_BOOKING",START_ENROLLMENT:"START_ENROLLMENT",START_INTAKE:"START_INTAKE",START_QUOTE:"START_QUOTE",START_TICKET_PURCHASE:"START_TICKET_PURCHASE",UPDATE_CART_QUANTITY:"UPDATE_CART_QUANTITY",UPDATE_PREFERENCES:"UPDATE_PREFERENCES"}),d=Object.freeze({ENTITY_ID:"entity_id",ENTITY_IDS:"entity_ids",MESSAGE:"message",PAGE:"page",PRODUCT_ID:"product_id",PRODUCT_IDS:"product_ids",PRODUCT_NAME:"product_name",QUANTITY:"quantity",REASON:"reason",SEARCH_QUERY:"search_query",URL:"url"}),sl=Object.freeze({BLOCKED:"blocked",EXECUTING:"executing",FAILED:"failed",REQUESTED:"requested",SKIPPED:"skipped",SUCCEEDED:"succeeded",UNKNOWN:"unknown"}),k=Object.freeze({KNOWLEDGE_BY_IDS:"/v1/knowledge/by-ids",PRODUCTS_BY_IDS:"/v1/products/by-ids",SHOP:"/v1/shop",SHOP_WS:"/v1/ws/shop",WIDGET_STATUS:"/v1/widget/status"}),M=Object.freeze({AUDIO_CHUNK:"audio_chunk",AUDIO_END:"audio_end",CONFIG:"config",DONE:"done",ERROR:"error",TEXT_CHUNK:"text_chunk",TRANSCRIPT:"transcript"});var kn=new Set(["cart","/cart"]),K="Recommended products",et="Relevant options",Et=Object.freeze({DATA_WAV_PREFIX:"data:audio/wav;base64,",WEBM_FILENAME:"audio.webm",WEBM_MIME_TYPE:"audio/webm"}),Mn=Object.freeze({POST:"POST"}),A=Object.freeze({ERROR:"error",PROCESSING:"processing",READY:"ready",RECORDING:"recording"});var Hn=2400,Fn=900,Bn=4200,Ae=1,dt=180,$n=3e3,St=Object.freeze({MAYABOT_ACTION:"mayabot:action"}),Yn=2500,qn=45e3;var Bi=["audio/webm;codecs=opus","audio/webm","audio/ogg;codecs=opus","audio/ogg","audio/mp4"],$i=250,Yi=128;function jn(t,e){let n=null,r=null,o=[],i=!1,a=!1,s=!1;async function u(){if(!(a||i)){a=!0;try{let h=await navigator.mediaDevices.getUserMedia({audio:!0});r=h,s=!1;let x=qi();n=new MediaRecorder(h,x?{mimeType:x}:void 0),o=[],n.ondataavailable=b=>{b.data.size>0&&o.push(b.data)},n.onstop=async()=>{let b=new Blob(o,{type:n.mimeType||x||Et.WEBM_MIME_TYPE});if(I(),s){s=!1;return}if(b.size<Yi){console.warn("Microphone recording was empty or too short",{size:b.size}),e(A.READY);return}await t(b)},n.onerror=b=>{console.error("Microphone recording failed",b.error||b),i=!1,a=!1,I(),e(A.ERROR,"Recording failed")},n.start($i),i=!0,e(A.RECORDING)}catch(h){console.error("Microphone access denied",h),e(A.ERROR,"Mic unavailable")}finally{a=!1}}}function f({discard:h=!1}={}){if(s=h,n&&n.state!=="inactive"){try{n.requestData()}catch{}n.stop(),i=!1,h||e(A.PROCESSING);return}i=!1,I(),h||e(A.PROCESSING)}function w(){a||(i?f():u())}function T(){f({discard:!0})}function I(){r&&(r.getTracks().forEach(h=>h.stop()),r=null)}return{toggle:w,cancel:T}}function qi(){return!("MediaRecorder"in window)||typeof MediaRecorder.isTypeSupported!="function"?"":Bi.find(t=>MediaRecorder.isTypeSupported(t))||""}var zn="shopify",Vn="woocommerce",ji="custom";function qt(t){let e=String(t||"").trim();return/^\d+$/.test(e)?e:""}function jt(t,e=1){let n=Number(t?.[d.QUANTITY]);return Number.isFinite(n)&&n>0?Math.floor(n):e}async function st(t,e){return(await fetch(new URL(t,window.location.origin),{method:"POST",headers:{Accept:"application/json","Content-Type":"application/json"},body:JSON.stringify(e),credentials:"same-origin"})).ok}function zi(){return Vi()?zn:Gi()?Vn:ji}async function Gn(t){let e=zi();return e===zn?Wi(t):e===Vn?Ki(t):!1}function Vi(){return!!(window.Shopify||document.querySelector('meta[name="shopify-checkout-api-token"]')||document.querySelector('script[src*="cdn.shopify.com"]'))}function Gi(){return!!(document.body?.classList?.contains("woocommerce")||window.wc_add_to_cart_params||document.querySelector('link[href*="woocommerce"], script[src*="woocommerce"]'))}async function Wi(t){let e=t.parameters||{};if(t.action===c.ADD_TO_CART){let n=qt(e.variant_id||e.cart_id||e[d.PRODUCT_ID]);return n?st("/cart/add.js",{items:[{id:n,quantity:jt(e)}]}):!1}if(t.action===c.REMOVE_FROM_CART){let n=qt(e.cart_id||e.variant_id||e[d.PRODUCT_ID]);return n?st("/cart/change.js",{id:n,quantity:0}):!1}if(t.action===c.UPDATE_CART_QUANTITY){let n=qt(e.cart_id||e.variant_id||e[d.PRODUCT_ID]);return n?st("/cart/change.js",{id:n,quantity:jt(e,0)}):!1}return t.action===c.CLEAR_CART?st("/cart/clear.js",{}):t.action===c.CHECKOUT?zt("/checkout"):Wn(t)?zt("/cart"):!1}async function Ki(t){let e=t.parameters||{};if(t.action===c.ADD_TO_CART){let n=qt(e.variant_id||e.cart_id||e[d.PRODUCT_ID]);return n?st("/wp-json/wc/store/cart/add-item",{id:Number(n),quantity:jt(e)}):!1}if(t.action===c.REMOVE_FROM_CART){let n=String(e.cart_key||e.key||"").trim();return n?st("/wp-json/wc/store/cart/remove-item",{key:n}):!1}if(t.action===c.UPDATE_CART_QUANTITY){let n=String(e.cart_key||e.key||"").trim();return n?st("/wp-json/wc/store/cart/update-item",{key:n,quantity:jt(e,0)}):!1}return t.action===c.CHECKOUT?zt("/checkout"):Wn(t)?zt("/cart"):!1}function Wn(t){return t.action===c.NAVIGATE_TO&&kn.has(t.parameters?.[d.PAGE])}function zt(t){return window.location.href=t,!0}var Qi="/v1/widget/action-event";function L(t){return String(t||"").trim()}function Xi(t,e){return new URL(t,e).toString()}function Ji(t){return!t||typeof t!="object"?[]:Object.keys(t).map(e=>L(e)).filter(Boolean).slice(0,20)}function Zi(t){if(!t||typeof t!="object")return{};let e={};for(let[n,r]of Object.entries(t).slice(0,20)){let o=L(n).slice(0,80);o&&(typeof r=="boolean"||r===null?e[o]=r:typeof r=="number"?e[o]=Number.isFinite(r)?r:0:e[o]=L(r).slice(0,240))}return e}async function Vt(t,e,n,r){if(!t||!e||!n?.action)return;let o=JSON.stringify({site_id:e,origin:window.location.origin,url:window.location.href,occurred_at:new Date().toISOString(),request_id:L(n.request_id||n.action_request_id),turn_id:L(n.turn_id),sequence:Number(n.sequence||0),action:L(n.action).toUpperCase(),status:L(r?.status)||"unknown",stage:L(r?.stage),reason:L(r?.reason),duration_ms:Number(r?.duration_ms||0),param_keys:Ji(n.parameters||n.params),requested_url:L(r?.requested_url),final_url:L(r?.final_url||window.location.href),evidence:Zi(r?.evidence)}),i=Xi(Qi,t);if(!ta(i,o))try{await fetch(i,{method:"POST",headers:{Accept:"application/json","Content-Type":"application/json"},body:o,keepalive:!0})}catch(a){console.warn("[AIHubAdapter] Action execution report failed.",a)}}function ta(t,e){if(typeof navigator>"u"||typeof navigator.sendBeacon!="function"||typeof Blob!="function")return!1;try{return navigator.sendBeacon(t,new Blob([e],{type:"application/json"}))}catch{return!1}}function N(t){if(!t||typeof t!="string")return[];let e=[];for(let n of ea()){try{e.push(...Array.from(n.querySelectorAll(t)))}catch{return[]}if(e.length>=600)return e.slice(0,600)}return ia(e)}function ea(){let t=[],e=new Set,n=[document];for(;n.length&&t.length<60;){let r=n.shift();!r||e.has(r)||(e.add(r),t.push(r),n.push(...na(r)))}return t}function na(t){let e=[];for(let n of ra(t)){n.shadowRoot&&e.push(n.shadowRoot);let r=oa(n);r&&e.push(r)}return e}function ra(t){try{return Array.from(t.querySelectorAll("*"))}catch{return[]}}function oa(t){if(String(t?.tagName||"").toLowerCase()!=="iframe")return null;try{let e=t.contentDocument;return e?.documentElement?e:null}catch{return null}}function ia(t){return Array.from(new Set(t))}var gl=Object.freeze([p("stripe",["stripe","stripe.com","checkout.stripe.com","js.stripe.com"]),p("paypal",["paypal","paypal.com","paypalobjects.com"]),p("razorpay",["razorpay","checkout.razorpay.com"]),p("paytm",["paytm","securegw.paytm.in"]),p("cashfree",["cashfree","cashfree.com"]),p("checkout.com",["checkout.com","cko-session-id"]),p("adyen",["adyen","checkoutshopper"]),p("square",["squareup","squarecdn","square.site"]),p("braintree",["braintree","braintreegateway"]),p("mollie",["mollie","mollie.com"]),p("klarna",["klarna","klarna.com"]),p("afterpay",["afterpay","afterpay.com","clearpay"]),p("payu",["payu","payu.in","payu.com"]),p("paystack",["paystack","paystack.co"]),p("phonepe",["phonepe","phonepe.com"]),p("billdesk",["billdesk","billdesk.com"]),p("authorize.net",["authorize.net","accept.authorize.net"])]),Kn=Object.freeze([p("calendly",["calendly","calendly.com"]),p("acuity",["acuityscheduling","squarespace scheduling"]),p("booksy",["booksy","booksy.com"]),p("zocdoc",["zocdoc","zocdoc.com"]),p("appointlet",["appointlet","appointlet.com"]),p("setmore",["setmore","setmore.com"]),p("cal.com",["cal.com","calcom"]),p("google_calendar",["calendar.google.com","google calendar"]),p("microsoft_bookings",["microsoft bookings","outlook.office365.com/book"]),p("simplybook",["simplybook","simplybook.me"]),p("tidycal",["tidycal","tidycal.com"]),p("savvycal",["savvycal","savvycal.com"]),p("fresha",["fresha","fresha.com"])]),Qn=Object.freeze([p("google_maps",["google.com/maps","maps.googleapis","maps.google"]),p("mapbox",["mapbox","mapbox.com"]),p("openstreetmap",["openstreetmap","osm.org"]),p("leaflet",["leaflet","leafletjs"]),p("here_maps",["here.com","hereapi","wego.here.com"]),p("bing_maps",["bing.com/maps","virtualearth"]),p("mappls",["mappls","mapmyindia"])]),Xn=Object.freeze([p("whatsapp",["wa.me","api.whatsapp.com","web.whatsapp.com"]),p("telegram",["t.me/","telegram.me"]),p("messenger",["m.me/","messenger.com/t"]),p("zendesk",["zendesk.com","zdassets.com/hc"]),p("intercom",["intercom.help","intercom.com"]),p("freshchat",["freshchat.com"])]),yl=Object.freeze([p("recaptcha",["recaptcha","g-recaptcha","google.com/recaptcha"]),p("hcaptcha",["hcaptcha","h-captcha"]),p("turnstile",["turnstile","challenges.cloudflare.com"]),p("cloudflare_challenge",["cf-chl","cloudflare challenge"])]);function p(t,e){return{name:t,tokens:e}}function Ee(t,e,n=10){let r=Se(t);return e.filter(o=>o.tokens.some(i=>r.includes(i))).map(o=>o.name).slice(0,n)}function Se(t){return String(t||"").replace(/\s+/g," ").trim().toLowerCase()}var Jn="a[href], iframe[src]",aa="a[href]",tr=new Set(["http:","https:"]),Gt=new Set(["mailto:","tel:"]),sa=Object.freeze([d.URL,"href","link","target_url","provider_url","booking_url","appointment_url","calendar_url","map_url","location_url","contact_url"]),er=new Set([c.OPEN_MAP,c.OPEN_LOCATION,c.SET_LOCATION]),nr=new Set([c.CHECK_APPOINTMENT_AVAILABILITY,c.REQUEST_APPOINTMENT,c.BOOK_APPOINTMENT_REQUEST,c.REQUEST_CONSULTATION,c.REQUEST_SITE_VISIT,c.START_BOOKING]),rr=new Set([c.OPEN_CONTACT,c.CONTACT_AGENT,c.REQUEST_CALLBACK,c.REQUEST_COUNSELOR_CALLBACK,c.HANDOFF_TO_ADVISOR,c.HANDOFF_TO_AGENT,c.HANDOFF_TO_CLINIC,c.HANDOFF_TO_HUMAN,c.HANDOFF_TO_LAWYER,c.HANDOFF_TO_LICENSED_AGENT,c.HANDOFF_TO_RECRUITER]);function or(t){let e=sr(t);return er.has(e)||nr.has(e)||rr.has(e)}async function ir(t){let e=sr(t);return er.has(e)?we(t,Qn,Jn,Ie):nr.has(e)?we(t,Kn,Jn,Ie):rr.has(e)?we(t,Xn,aa,da):!1}function we(t,e,n,r){let o=ca(t?.parameters||t?.params||{},e,r);if(o)return Zn(o);let i=ua(n,e,r);return i?Zn(i):!1}function ca(t,e,n){for(let r of sa){let o=ar(t?.[r]);if(o&&n(o,e))return o}return null}function ua(t,e,n){for(let r of N(t)){let o=la(r);if(!(!o||!n(o,e))&&pa(o,r,e))return o}return null}function la(t){return ar(t?.getAttribute?.("href")||t?.getAttribute?.("src"))}function Ie(t,e){return tr.has(t.protocol)&&Ee(t.href,e).length>0}function da(t,e){return Gt.has(t.protocol)?!0:Ie(t,e)}function pa(t,e,n){if(Gt.has(t.protocol))return!0;let r=[t.href,e?.textContent||"",e?.getAttribute?.("aria-label")||"",e?.getAttribute?.("title")||""].join(" ");return Ee(Se(r),n).length>0}function Zn(t){if(Gt.has(t.protocol)||t.origin===window.location.origin)return window.location.href=t.href,!0;let e=window.open(t.href,"_blank","noopener,noreferrer");return e?(e.opener=null,!0):(window.location.href=t.href,!0)}function ar(t){let e=String(t||"").trim();if(!e||e.startsWith("#"))return null;try{let n=new URL(e,window.location.href);return tr.has(n.protocol)||Gt.has(n.protocol)?n:null}catch{return null}}function sr(t){return String(t?.action||"").trim().toUpperCase()}var fa=Object.freeze(["title","name"]),ma=Object.freeze(["summary","description","body"]),ha=Object.freeze(["image_url","imageUrl","image","thumbnail"]),_a=Object.freeze(["url","href","permalink","source_url"]),ga="knowledge_item",ya=30;function H(t){return t==null||typeof t=="object"?"":String(t||"").trim()}function ba(t){let e=new Set;return(Array.isArray(t)?t:[]).map(H).filter(Boolean).filter(n=>e.has(n)||e.size>=ya?!1:(e.add(n),!0))}function Wt(t,e){for(let n of e){let r=H(t?.[n]);if(r)return r}return""}function wt(t){return t&&typeof t=="object"&&!Array.isArray(t)?t:{}}function Ta(t){let e=Aa([t?.price,t?.amount,t?.premium,t?.premium_min,t?.monthly_premium,t?.annual_premium,t?.min_price,t?.starting_price]),n=H(t?.currency||"INR");return!Number.isFinite(e)||e<=0?"":`${n} ${e.toLocaleString()}`}function Aa(t){for(let e of t){let n=Number(String(e??"").replace(/,/g,""));if(Number.isFinite(n)&&n>0)return n}return 0}function Ea(t){return!t||typeof t!="object"?"":t.in_stock===!0?"Available":t.in_stock===!1?"Unavailable":H(t.status||t.availability||"")}function Sa(t){let e=H(t);if(!e)return"";try{let n=new URL(e,window.location.origin);return/^https?:$/i.test(n.protocol)?n.origin===window.location.origin?`${n.pathname}${n.search}${n.hash}`:n.toString():""}catch{return""}}function wa(t){if(!t)return null;let e=H(t.id);if(!e)return null;let n=wt(t.pricing),r=wt(t.availability);return{id:e,externalId:H(t.external_id),entityType:H(t.entity_type||t.category_name)||ga,title:Wt(t,fa)||e,subtitle:H(t.subtitle||t.category_name||t.entity_type),summary:Wt(t,ma),body:H(t.body),url:Sa(Wt(t,_a)),imageUrl:Wt(t,ha),attributes:wt(t.attributes),pricing:n,availability:r,location:wt(t.location),contact:wt(t.contact),displayPrice:Ta(n),displayAvailability:Ea(r)}}async function Oe(t){let e=ba(t);if(!e.length)return[];let n=new URL(k.KNOWLEDGE_BY_IDS,l.apiUrl);n.searchParams.set("site_id",l.siteId),n.searchParams.set("ids",e.join(","));let r=await fetch(n.toString(),{headers:{Accept:"application/json"}});if(!r.ok)throw new Error("Failed to fetch entities from AI Hub API");let o=(await r.json()).map(wa).filter(Boolean),i=new Map(o.map(a=>[String(a.id),a]));return e.map(a=>i.get(a)).filter(Boolean)}async function cr(t){let[e]=await Oe([t]);return e?.url||""}function ur(){if(document.getElementById("mayabot-entity-overlay-styles"))return;let t=document.createElement("style");t.id="mayabot-entity-overlay-styles",t.textContent=`
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
  `,document.head.appendChild(t)}var Ia=2,lr=Number.POSITIVE_INFINITY,Kt=Number.NEGATIVE_INFINITY,dr=12,xe=[],Re=et;function Q(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}function hr(t){return String(t||"item").replace(/[_-]+/g," ").trim().split(/\s+/).slice(0,Ia).join(" ")}function Oa(){ur();let t=document.getElementById("mayabot-entity-panel");return t||(t=document.createElement("div"),t.id="mayabot-entity-panel",t.setAttribute("aria-live","polite"),t.innerHTML=`
    <div class="mayabot-entity-header">
      <h2 class="mayabot-entity-title">${et}</h2>
      <button class="mayabot-entity-close" type="button" aria-label="Close recommendations">&times;</button>
    </div>
    <div class="mayabot-entity-grid"></div>
  `,t.querySelector(".mayabot-entity-close").addEventListener("click",()=>{t.classList.remove("active")}),document.body.appendChild(t),t)}function Ca(t){return t<=1?"count-1":t===2?"count-2":t===3?"count-3":"count-many"}function xa(t){return t<=1?1:t===2?2:3}function Ce(t,e,n=""){let r=(Array.isArray(e)?e:[]).map(s=>String(s?.id??"").trim()).filter(Boolean),o=r.length,i=t.length,a=o>0?"succeeded":"failed";return{status:a,stage:"entity_overlay",reason:n||(a==="succeeded"?"":"no_matching_entities_rendered"),evidence:{requested_entity_count:i,rendered_entity_count:o,missing_entity_count:Math.max(i-o,0),requested_entity_ids:t.slice(0,dr).join(","),rendered_entity_ids:r.slice(0,dr).join(",")}}}function Ra(t){return[t.displayPrice,t.displayAvailability,t.location?.city,t.attributes?.category].map(e=>String(e||"").trim()).filter(Boolean).slice(0,3)}function Na(t){return t.imageUrl?`
      <div class="mayabot-entity-media">
        <img src="${Q(t.imageUrl)}" alt="${Q(t.title)}">
      </div>
    `:`
    <div class="mayabot-entity-media">
      <div class="mayabot-entity-badge">${Q(hr(t.entityType))}</div>
    </div>
  `}function va(t){let e=Ra(t);return e.length?`
    <div class="mayabot-entity-facts">
      ${e.map(n=>`<span class="mayabot-entity-fact">${Q(n)}</span>`).join("")}
    </div>
  `:""}function Pa(t){return t.url?`
    <div class="mayabot-entity-actions">
      <button type="button" data-view-entity="${Q(t.id)}">Open</button>
    </div>
  `:""}function Xt(t,e){let n=Oa(),r=n.querySelector(".mayabot-entity-grid"),o=n.querySelector(".mayabot-entity-title"),i=t.length;if(xe=Array.isArray(t)?[...t]:[],Re=e||et,n.classList.remove("count-1","count-2","count-3","count-many"),n.classList.add(Ca(i)),n.style.setProperty("--mayabot-entity-card-count",String(xa(i))),o.textContent=Re,!i){r.innerHTML='<p class="mayabot-entity-empty">No matching records are currently available.</p>',n.classList.add("active"),pr();return}r.innerHTML=t.map(a=>`
        <article class="mayabot-entity-card" data-entity-id="${Q(a.id)}">
          ${Na(a)}
          <h3 class="mayabot-entity-name">${Q(a.title)}</h3>
          <p class="mayabot-entity-meta">${Q(a.subtitle||hr(a.entityType))}</p>
          <p class="mayabot-entity-summary">${Q(a.summary||a.body||"Details are available on the website.")}</p>
          ${va(a)}
          ${Pa(a)}
        </article>
      `).join(""),r.querySelectorAll("[data-view-entity]").forEach(a=>{a.addEventListener("click",async()=>{await Ne(a.getAttribute("data-view-entity"))})}),n.classList.add("active"),pr()}function La(t){if(!t)return!1;try{let e=new URL(t,window.location.origin);return e.origin===window.location.origin?(window.location.href=`${e.pathname}${e.search}${e.hash}`,!0):(window.open(e.toString(),"_blank","noopener,noreferrer"),!0)}catch{return!1}}function pr(){window.setTimeout(()=>{let t=document.getElementById("mayabot-chat"),e=document.getElementById("mayabot-msgs");e&&(e.innerHTML=""),t&&t.classList.remove("visible")},dt)}async function Ne(t){let e=await cr(t);return La(e)}async function _r(t,e=et){let n=ve({[d.ENTITY_IDS]:t});if(!n.length)return Xt([],e),Ce([],[],"missing_entity_ids");try{let r=await Oe(n);return Xt(r,e),Ce(n,r)}catch(r){return console.warn("[AI Hub Widget] Entity overlay failed:",r),Xt([],e),Ce(n,[],"entity_overlay_fetch_failed")}}function ve(t){let e=t[d.ENTITY_IDS]||t.ids||t.items||[],n=new Set;return(Array.isArray(e)?e:[]).map(r=>String(r??"").trim()).filter(Boolean).filter(r=>n.has(r)?!1:(n.add(r),!0))}function gr(t={}){if(!xe.length)return!1;let e=String(t.sort_by||t.sortBy||"price_asc").trim().toLowerCase(),n=[...xe].sort((o,i)=>Da(o,i,e)),r=ka(Re,e);return Xt(n,r),!0}function Da(t,e,n){return n==="price_desc"?Qt(e,Kt)-Qt(t,Kt):n==="rating"?fr(e,Kt)-fr(t,Kt):n==="newest"?mr(e)-mr(t):Qt(t,lr)-Qt(e,lr)}function Qt(t,e){return yr([t?.pricing?.price,t?.pricing?.amount,t?.pricing?.premium,t?.pricing?.premium_min,t?.pricing?.monthly_premium,t?.pricing?.annual_premium,t?.pricing?.min_price,t?.pricing?.starting_price,t?.attributes?.price,t?.attributes?.amount,t?.attributes?.premium,t?.attributes?.monthly_premium,t?.attributes?.annual_premium,t?.displayPrice],e)}function fr(t,e){return yr([t?.attributes?.rating,t?.attributes?.review_rating,t?.attributes?.stars,t?.availability?.rating],e)}function mr(t){let e=t?.attributes?.updated_at||t?.attributes?.date||t?.availability?.updated_at||"",n=Date.parse(String(e||""));return Number.isFinite(n)?n:0}function yr(t,e){for(let n of t){let r=Ua(n);if(Number.isFinite(r))return r}return e}function Ua(t){if(typeof t=="number")return t;let e=String(t??"").replace(/,/g,"").match(/-?\d+(?:\.\d+)?/);return e?Number(e[0]):Number.NaN}function ka(t,e){let n={price_asc:"sorted low to high",price_desc:"sorted high to low",rating:"sorted by rating",newest:"newest first"};return`${String(t||et).replace(/\s+-\s+sorted.*$/i,"")} - ${n[e]||n.price_asc}`}function br(t){return t.action===c.SHOW_ENTITIES||t.action===c.COMPARE_ENTITIES||t.action===c.OPEN_ENTITY_DETAIL||t.action===c.SORT_ENTITIES}async function Tr(t){return t.action===c.SHOW_ENTITIES||t.action===c.COMPARE_ENTITIES?Ma(t.parameters||{}):t.action===c.OPEN_ENTITY_DETAIL?Ne(t.parameters?.[d.ENTITY_ID]||t.parameters?.id):t.action===c.SORT_ENTITIES?gr(t.parameters||{}):!1}function Ma(t){return _r(ve(t),t[d.SEARCH_QUERY]||t.title||et)}var It="mayabot-handoff-panel",Ar="mayabot-handoff-overlay-styles",Ha=Object.freeze(["contact","support","help"]),Fa=Object.freeze(["checkout","cart"]),Ir=new Set([c.CHECKOUT_HANDOFF,c.HANDOFF_TO_ADVISOR,c.HANDOFF_TO_AGENT,c.HANDOFF_TO_CLINIC,c.HANDOFF_TO_HUMAN,c.HANDOFF_TO_LAWYER,c.HANDOFF_TO_LICENSED_AGENT,c.HANDOFF_TO_RECRUITER]),Er=Object.freeze({[c.CHECKOUT_HANDOFF]:{title:"Checkout needs your confirmation",body:"This step may include payment or a secure checkout page. I can take you there, then you complete the final step yourself.",primary:"Open checkout"},[c.HANDOFF_TO_ADVISOR]:{title:"Advisor handoff",body:"This request needs a qualified advisor. I can open the contact path so the site team can continue.",primary:"Contact advisor"},[c.HANDOFF_TO_AGENT]:{title:"Agent handoff",body:"This step needs an agent or account-specific help. I can open the contact path for follow-up.",primary:"Contact agent"},[c.HANDOFF_TO_CLINIC]:{title:"Clinic handoff",body:"This request needs clinic confirmation. I can open the appointment or contact path for the next step.",primary:"Contact clinic"},[c.HANDOFF_TO_HUMAN]:{title:"Human handoff",body:"This step needs human confirmation. I can open the most relevant contact path.",primary:"Open contact"},[c.HANDOFF_TO_LAWYER]:{title:"Legal handoff",body:"This request needs a legal professional. I can open the consultation or contact path.",primary:"Contact lawyer"},[c.HANDOFF_TO_LICENSED_AGENT]:{title:"Licensed agent handoff",body:"This request needs a licensed agent. I can open the quote or contact path for follow-up.",primary:"Contact agent"},[c.HANDOFF_TO_RECRUITER]:{title:"Recruiter handoff",body:"This request needs recruiter review. I can open the application or contact path.",primary:"Contact recruiter"}});function pt(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}function ct(t){return String(t||"").trim()}function Ba(){if(document.getElementById(Ar))return;let t=document.createElement("style");t.id=Ar,t.textContent=`
    #${It} {
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
    #${It}.active {
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
      #${It} {
        bottom: 82px;
        width: min(calc(100vw - 20px), 420px);
      }
    }
  `,document.head.appendChild(t)}function $a(){Ba();let t=document.getElementById(It);return t||(t=document.createElement("div"),t.id=It,t.setAttribute("aria-live","polite"),document.body.appendChild(t),t)}function Ya(){return window.AIHubAdapterRuntime?.config?.adapter?.routes||window.AIHubAdapter?.config?.adapter?.routes||{}}function qa(t,e){let n=Sr(e[d.URL]||e.path||e.href||e.handoff_flow?.page_url);if(n)return n;let r=Ya(),o=t===c.CHECKOUT_HANDOFF?Fa:Ha;for(let i of o){let a=Sr(r[i]);if(a)return a}return""}function Sr(t){let e=ct(t);if(!e)return"";try{let n=new URL(e,window.location.origin);return n.origin!==window.location.origin?"":`${n.pathname}${n.search}${n.hash}`||"/"}catch{return""}}function ja(t){return Er[t]||Er[c.HANDOFF_TO_HUMAN]}function za(t){return t&&typeof t=="object"?t:{}}function Va(t,e){return ct(t.title)||e}function Ga(t,e,n){return ct(e[d.MESSAGE])||ct(t.handling)||n}function Wa(t,e){return ct(e[d.REASON]||e.reason||e.blocked_reason||t.key)}function Ka(t){let e=[["Provider",t.provider_label||t.provider],["Boundary",t.automation_boundary],["Recovery",t.recovery],["Evidence",t.evidence],["Page",t.page_url]].filter(([,n])=>ct(n));return e.length?`
    <p class="mayabot-handoff-meta">
      ${e.map(([n,r])=>`<span><strong>${pt(n)}:</strong> ${pt(r)}</span>`).join("")}
    </p>
  `:""}function wr(t){t.classList.remove("active")}function Qa(){window.setTimeout(()=>{let t=document.getElementById("mayabot-chat"),e=document.getElementById("mayabot-msgs");e&&(e.innerHTML=""),t&&t.classList.remove("visible")},dt)}function Or(t,e={}){let n=ct(t).toUpperCase(),r=ja(n),o=za(e.handoff_flow),i=$a(),a=qa(n,e),s=Va(o,r.title),u=Ga(o,e,r.body),f=Wa(o,e);return i.innerHTML=`
    <div class="mayabot-handoff-body">
      <div class="mayabot-handoff-top">
        <h2 class="mayabot-handoff-title">${pt(s)}</h2>
        <button class="mayabot-handoff-close" type="button" aria-label="Close handoff">&times;</button>
      </div>
      <p class="mayabot-handoff-text">${pt(u)}</p>
      ${Ka(o)}
      ${f?`<p class="mayabot-handoff-reason">${pt(f)}</p>`:""}
      <div class="mayabot-handoff-actions">
        <button type="button" class="secondary" data-close-handoff>Close</button>
        ${a?`<button type="button" data-open-handoff>${pt(r.primary)}</button>`:""}
      </div>
    </div>
  `,i.querySelector(".mayabot-handoff-close")?.addEventListener("click",()=>wr(i)),i.querySelector("[data-close-handoff]")?.addEventListener("click",()=>wr(i)),i.querySelector("[data-open-handoff]")?.addEventListener("click",()=>{window.location.href=a}),i.classList.add("active"),Qa(),!0}function Cr(t){return Ir.has(t.action)}function xr(t){return Or(t.action,t.parameters||{})}function Nr(t){return t.action===c.NAVIGATE_TO&&!!Pr(t.parameters?.[d.PAGE])}function vr(t){return window.location.href=Pr(t.parameters?.[d.PAGE]),!0}function Pr(t){let e=String(t||"").trim();if(!e||Lr(e)||/^https?:\/\//i.test(e))return"";if(e==="home"||e==="/")return"/";let n=Xa(e);if(n)return n;let r=e.replace(/^\/+|\/+$/g,"");return r?`/${r}`:"/"}function Xa(t){let e=window.AIHubAdapterRuntime?.config?.adapter?.routes||window.AIHubAdapter?.config?.adapter?.routes||{},n=Ja(t);for(let r of n){let o=e[r],i=Rr(o);if(i)return i}for(let[r,o]of Object.entries(e)){if(!n.includes(Pe(r)))continue;let i=Rr(o);if(i)return i}return""}function Ja(t){let e=Pe(t),n=String(t||"").trim().replace(/^\/+|\/+$/g,"").toLowerCase(),r=n.split("?")[0].split("#")[0].split("/").filter(Boolean).pop()||"";return Array.from(new Set([e,n,Pe(r)].filter(Boolean)))}function Pe(t){return String(t||"").trim().toLowerCase().replace(/[^a-z0-9/_\s-]+/g," ").replace(/[_-]+/g," ").replace(/\s+/g," ").trim().replace(/\s+/g,"-")}function Rr(t){let e=String(t||"").trim();if(!e||Lr(e))return"";if(/^https?:\/\//i.test(e))try{let n=new URL(e);return n.origin!==window.location.origin?"":`${n.pathname||"/"}${n.search||""}${n.hash||""}`}catch{return""}return e.startsWith("/")?e:`/${e.replace(/^\/+/,"")}`}function Lr(t){return/^(?:javascript:|data:|\/\/)/i.test(String(t||"").trim())}function Dr(t){let e=t?.params||t?.parameters||{};return{...t||{},action:String(t?.action||"").trim().toUpperCase(),params:e,parameters:e}}var Le="AIHubAdapterRuntime",De="AIHubAdapter";function Za(t){let e=t?.params||t?.parameters||{};return{...t||{},params:e,parameters:e}}function Ot(){return!!(window[Le]?.executeAction||window[De]?.handleAction)}async function Ue(t){return(await Ct(t)).succeeded}async function Ct(t){let e=Za(t);if(window[Le]?.executeAction){let n=window[Le],r=await n.executeAction(e)===!0,o=n.lastActionResult||{};return{succeeded:r,handled:o.handled===!0||r,status:o.status||(r?"ok":"not_handled"),reason:o.reason||"",blocked:o.status==="blocked",disabled:o.status==="disabled"}}if(window[De]?.handleAction){let n=await window[De].handleAction(e)===!0;return{succeeded:n,handled:n,status:n?"ok":"not_handled",reason:"",blocked:!1,disabled:!1}}return{succeeded:!1,handled:!1,status:"missing_adapter",reason:"",blocked:!1,disabled:!1}}var ts=Object.freeze([{path:"/api/products?per_page=96",routePrefix:"/product/"},{path:"/api/products",routePrefix:"/product/"},{path:"/api/products.json",routePrefix:""},{path:"/products.json",routePrefix:"/products/"},{path:"/collections/all/products.json",routePrefix:"/products/"}]),es=Object.freeze(["products","data","items","results"]),kr=Object.freeze(["id","product_id","handle","sku"]),Mr=Object.freeze(["name","title"]),ns=Object.freeze(["url","href","permalink","product_url"]),rs=Object.freeze(["image_url","imageUrl","image_src","imageSrc","image","images","media","thumbnail","thumbnail_url","featured_image","featuredImage","featured_image_url"]),os=Object.freeze(["brand","vendor"]),is=Object.freeze(["category","category_name","product_type"]),as=Object.freeze(["description","summary","body_html"]),ss=Object.freeze(["original_price","compare_at_price","regular_price"]),Hr=Object.freeze(["currency","currency_code"]),cs=Object.freeze(["display_price","price_text","formatted_price"]),us="Unknown Brand",ls="Products",ds="/",ps=/^[a-z0-9][a-z0-9-]*$/i,ke=null;function D(t){return t==null||typeof t=="object"?"":String(t||"").trim()}function Fe(t){return D(t).toLowerCase().replace(/[^a-z0-9]+/g," ").trim()}function Fr(t){let e=new Set(["a","am","an","and","ask","asked","did","for","me","not","on","only","please","show","some","the","to","wanna","want","what","with","you","your"]),n=[],r=new Set;for(let o of fs(Fe(t)).split(" ")){let i=ms(o);i.length<=1||e.has(i)||r.has(i)||(n.push(i),r.add(i))}return n}function fs(t){return t.replace(/\b(?:i\s+)?did\s+not\s+ask\s+for\s+(?:a\s+|an\s+)?[a-z0-9]+\b/g," ")}function ms(t){return["phone","phones","mobile","mobiles"].includes(t)?"phone":["book","books"].includes(t)?"books":t}function Be(t,e){return e.map(n=>D(t?.[n])).filter(Boolean)}function F(t,e){return Be(t,e)[0]||""}function Jt(t){let e=D(t).replace(/,/g,"");if(!e)return 0;let n=e.match(/-?\d+(?:\.\d+)?/),r=Number(n?n[0]:e);return Number.isFinite(r)?r:0}function hs(t,e){let n=F(t,cs);if(n)return n;let r=F(t,Hr).toUpperCase();return e>0&&r?`${r} ${e.toLocaleString()}`:e>0?e.toLocaleString():""}function _s(t){for(let e of rs){let n=Me(t?.[e]);if(n)return n}return""}function Me(t){if(!t)return"";if(Array.isArray(t)){for(let e of t){let n=Me(e);if(n)return n}return""}if(typeof t=="object"){for(let e of["src","url","image_url","imageUrl","image_src","imageSrc","thumbnail","thumbnail_url","featured_image","featuredImage","featured_image_url"]){let n=Me(t[e]);if(n)return n}return""}return gs(t)}function gs(t){let e=D(t);if(!e||/^javascript:/i.test(e))return"";if(/^data:image\//i.test(e))return e;try{let n=new URL(e,window.location.origin);return["http:","https:"].includes(n.protocol)?n.toString():""}catch{return""}}function ys(t){let e=D(t);if(!e)return"";try{let n=new URL(e,window.location.origin);return n.origin!==window.location.origin?"":`${n.pathname}${n.search}${n.hash}`}catch{return""}}function bs(t,e,n){let r=ys(F(t,ns));return r||(!ps.test(e)||!/[a-z]/i.test(e)||!n?.routePrefix?"":`${n.routePrefix}${encodeURIComponent(e)}${ds}`)}function $e(t,e={}){if(!t)return null;let n=F(t,kr),r=D(t.handle||t.slug||t.product_handle),o=F(t,Mr),i=Jt(t.price||t.amount||t.cost),a=Jt(F(t,ss));return!n&&!r?null:{id:n,handle:r,name:o,title:D(t.title||o),brand:F(t,os)||us,category:F(t,is)||ls,description:F(t,as),price:Number.isFinite(i)?i:0,originalPrice:Number.isFinite(a)?a:0,displayPrice:hs(t,i),currency:F(t,Hr),rating:Jt(t.rating||t.review_rating),reviewCount:Jt(t.review_count||t.reviews_count||t.reviews),imageUrl:_s(t),url:bs(t,r||n,e)}}function Ts(t){return Be(t,kr)}function Ur(t){return Be(t,Mr).map(Fe)}function Br(t,e){let n=D(e);return!!(n&&Ts(t).includes(n))}function $r(t,e){let n=Fr(e);if(!n.length)return!1;let r=Fe([t?.name,t?.title,t?.brand,t?.category,t?.category_name,t?.product_type,t?.description,t?.tags].join(" "));return n.every(o=>r.includes(o)||r.includes(o.replace(/s$/,"")))}function As(t,e){let n=new Set(Ur(e));return Ur(t).some(r=>n.has(r))}function Es(t,e){return!!(t?.imageUrl&&t.imageUrl===e?.imageUrl)}function Ss(t){if(Array.isArray(t))return t;for(let e of es){let n=t?.[e];if(Array.isArray(n))return n}return[]}async function ws(t){try{let e=await fetch(new URL(t.path,window.location.origin),{headers:{Accept:"application/json"}});if(!e.ok)return[];let n=await e.json();return Ss(n).map(r=>$e(r,t)).filter(Boolean)}catch(e){return console.warn(`[AI Hub Widget] Catalog endpoint lookup failed for ${t.path}:`,e),[]}}async function He(){return ke||(ke=Promise.all(ts.map(ws)).then(t=>t.flat())),ke}async function Is(t,e=120){if(!Fr(t).length)return[];let r=new URL("/v1/products",l.apiUrl);r.searchParams.set("site_id",l.siteId),r.searchParams.set("limit",String(e));try{let o=await fetch(r.toString(),{headers:{Accept:"application/json"}});return o.ok?(await o.json()).map(i=>$e(i)).filter(Boolean).filter(i=>$r(i,t)).slice(0,12):[]}catch(o){return console.warn("[AI Hub Widget] Hub product search fallback failed:",o),[]}}async function Yr(t,e=""){let n=(Array.isArray(t)?t:[]).map(D).filter(Boolean),r=[],o="",i="";if(n.length)try{r=await qr(n),o="hub_by_ids"}catch(a){i="hub_product_lookup_failed",console.warn("[AI Hub Widget] Hub product ID lookup failed:",a)}if(!r.length&&n.length){let a=await He();r=n.map(s=>a.find(u=>Br(u,s))).filter(Boolean),r.length&&(o="host_by_ids")}return!r.length&&e&&(r=await Is(e),r.length&&(o="hub_search")),!r.length&&e&&(r=(await He()).filter(s=>$r(s,e)).slice(0,12),r.length&&(o="host_search")),{products:r,source:o,reason:r.length?"":i||"no_matching_products_rendered"}}async function qr(t){let e=(Array.isArray(t)?t:[]).map(D).filter(Boolean);if(!e.length)return[];let n=new URL(k.PRODUCTS_BY_IDS,l.apiUrl);n.searchParams.set("site_id",l.siteId),n.searchParams.set("ids",e.join(","));let r=await fetch(n.toString(),{headers:{Accept:"application/json"}});if(!r.ok)throw new Error("Failed to fetch products from AI Hub API");let o=(await r.json()).map(a=>$e(a)).filter(Boolean),i=new Map(o.map(a=>[String(a.id),a]));return e.map(a=>i.get(a)).filter(Boolean)}async function Zt(t){let e=D(t);if(!e)return"";let[n]=await qr([e]);if(n?.url)return n.url;let r=await He(),o=r.find(a=>Br(a,e));return o?.url?o.url:n&&r.find(a=>As(a,n)||Es(a,n))?.url||""}var Os=1,Cs=1.08,xs=300,Rs=Object.freeze(["hannah","sonia","libby","ava","susan","hazel","heera","salli","joanna","amy","emma","olivia","natasha","zira","aria","jenny","samantha","victoria","tessa","moira","karen","female","woman","nova","shimmer","google us english","microsoft aria"]),X="",te="",xt=null,Ye=0;function ut(t){if(!("speechSynthesis"in window)||!("SpeechSynthesisUtterance"in window))return!1;ee();let e=++Ye;X=t;let n=()=>{if(e!==Ye||X!==t)return!1;try{let r=new SpeechSynthesisUtterance(t),o=Ns(window.speechSynthesis.getVoices());return o?(o&&(r.voice=o),r.rate=Os,r.pitch=Cs,r.onstart=jr,r.onend=jr,ee(),window.speechSynthesis.cancel(),window.speechSynthesis.resume(),window.speechSynthesis.speak(r),!0):(X="",!1)}catch{return!1}};return window.speechSynthesis.getVoices().length>0?n():(window.speechSynthesis.onvoiceschanged=n,xt=window.setTimeout(()=>{xt=null,n()},xs),!0)}function ne(){X&&ut(X)}function zr(){try{return!!X||!!window.speechSynthesis?.speaking||!!window.speechSynthesis?.pending}catch{return!!X}}function re(){Ye+=1,ee(),X="",te="";try{window.speechSynthesis?.cancel()}catch{}}function Ns(t){if(!Array.isArray(t)||t.length===0)return null;let e=vs(t)||Ps(t);return e&&(te=e.name),e}function vs(t){if(te){let n=t.find(r=>r.name===te);if(n)return n}let e=String(l.speechVoiceName||"").toLowerCase();return e&&t.find(n=>n.name.toLowerCase()===e)||null}function Ps(t){return l.speechVoicePreference.toLowerCase()!=="female"?t.find(e=>e.default)||t[0]:t.find(e=>Rs.some(n=>e.name.toLowerCase().includes(n)))||null}function jr(){ee(),X=""}function ee(){xt&&window.clearTimeout(xt),xt=null,window.speechSynthesis&&(window.speechSynthesis.onvoiceschanged=null)}var Ls=["data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='320' height='240' viewBox='0 0 320 240'%3E","%3Crect width='320' height='240' fill='%23f1f2ee'/%3E","%3Cpath d='M98 156h124l-31-40-25 30-17-22-51 32Z' fill='%23c8c3ba'/%3E","%3Ccircle cx='117' cy='95' r='17' fill='%23d8d3ca'/%3E","%3Ctext x='160' y='198' text-anchor='middle' fill='%23686660' font-family='Arial,sans-serif' font-size='16'%3EImage pending%3C/text%3E","%3C/svg%3E"].join(""),Vr=12,Ds=4,Us=6,ks=700,ie=[],je=K,ae=new Map,ze=!1;function Ms(){try{re()}catch{}}function nt(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}function Hs(){if(document.getElementById("mayabot-product-overlay-styles"))return;let t=document.createElement("style");t.id="mayabot-product-overlay-styles",t.textContent=`
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
  `,document.head.appendChild(t)}function Fs(){Hs();let t=document.getElementById("mayabot-product-panel");return t||(t=document.createElement("div"),t.id="mayabot-product-panel",t.setAttribute("aria-live","polite"),t.setAttribute("role","dialog"),t.setAttribute("tabindex","-1"),t.innerHTML=`
    <div class="mayabot-product-header">
      <h2 class="mayabot-product-title">${K}</h2>
      <button class="mayabot-product-close" type="button" aria-label="Close recommendations">&times;</button>
    </div>
    <div class="mayabot-compare-speak" role="group" aria-label="Speak comparison">
      <p>Would you like me to speak all the comparison points?</p>
      <button type="button" class="mayabot-compare-yes">Yes</button>
      <button type="button" class="mayabot-compare-no secondary">No</button>
    </div>
    <div class="mayabot-product-grid"></div>
  `,t.querySelector(".mayabot-product-close").addEventListener("click",Gr),t.querySelector(".mayabot-compare-yes").addEventListener("click",()=>Wr(!0)),t.querySelector(".mayabot-compare-no").addEventListener("click",()=>Wr(!1)),t.addEventListener("keydown",e=>{e.key==="Escape"&&Gr()}),document.body.appendChild(t),t)}function Gr(){let t=document.getElementById("mayabot-product-panel");t&&(t.classList.remove("active","ask-speak"),Ms())}function Wr(t){let e=document.getElementById("mayabot-product-panel");if(e&&e.classList.remove("ask-speak"),ze=!0,t){let n=$s(ie);n&&ut(n)}}function Bs(t,e){let n=document.getElementById("mayabot-product-panel");if(!n)return;if(!(e&&Array.isArray(t)&&t.length>=2)||ze){n.classList.remove("ask-speak");return}n.classList.add("ask-speak"),window.setTimeout(()=>n.querySelector(".mayabot-compare-yes")?.focus(),0)}function $s(t){let e=[];for(let n of(t||[]).slice(0,Ds)){let o=(ae.get(String(n.id))||[]).slice(0,Us).map(a=>`${a.label}: ${a.value}`).join(", "),i=n.name||n.title||"This product";e.push(o?`${i}. ${o}.`:`${i}.`)}return e.join(" ").slice(0,ks)}async function Ys(t){let e={action:c.ADD_TO_CART,params:{[d.PRODUCT_ID]:t,[d.QUANTITY]:Ae},parameters:{[d.PRODUCT_ID]:t,[d.QUANTITY]:Ae}};Ot()&&await Ue(e)||window.dispatchEvent(new CustomEvent(St.MAYABOT_ACTION,{detail:e}))}async function qs(t){try{let n=await Zt(t);if(n){window.location.href=n;return}}catch(n){console.warn("[AI Hub Widget] Product detail URL lookup failed:",n)}let e={action:c.SHOW_PRODUCT_DETAIL,params:{[d.PRODUCT_ID]:t},parameters:{[d.PRODUCT_ID]:t}};Ot()&&await Ue(e)||window.dispatchEvent(new CustomEvent(St.MAYABOT_ACTION,{detail:e}))}function js(t){return t<=1?"count-1":t===2?"count-2":t===3?"count-3":"count-many"}function zs(t){return t<=1?1:t===2?2:3}function Vs(t){let e=new Set;return(Array.isArray(t)?t:[]).map(n=>String(n??"").trim()).filter(Boolean).filter(n=>e.has(n)?!1:(e.add(n),!0))}function qe(t,e,n="",r={}){let o=(Array.isArray(e)?e:[]).map(u=>String(u?.id??"").trim()).filter(Boolean),i=o.length,a=t.length,s=i>0?"succeeded":"failed";return{status:s,stage:"product_overlay",reason:n||(s==="succeeded"?"":"no_matching_products_rendered"),evidence:{requested_product_count:a,rendered_product_count:i,missing_product_count:Math.max(a-i,0),requested_product_ids:t.slice(0,Vr).join(","),rendered_product_ids:o.slice(0,Vr).join(","),lookup_source:r.source||"",search_query:r.searchQuery||""}}}function Gs(t){let e=String(t?.displayPrice||"").trim();if(e)return e;let n=Number(t?.price||0);return Number.isFinite(n)&&n>0?n.toLocaleString():"Price unavailable"}var Ws=6,Ks=24,Qs=120;function Xs(t){let e=new Map;return Array.isArray(t)&&t.forEach(n=>{if(!n||typeof n!="object")return;let r=String(n.product_id||"").trim();if(!r||!Array.isArray(n.facts))return;let o=n.facts.filter(i=>i&&typeof i=="object"&&i.label&&i.value).slice(0,Ws).map(i=>({label:String(i.label).slice(0,Ks),value:String(i.value).slice(0,Qs)}));o.length&&e.set(r,o)}),e}function Js(t){let e=ae.get(String(t));return!e||!e.length?"":`<dl class="mayabot-product-facts">${e.map(r=>`<div class="mayabot-fact"><dt>${nt(r.label)}</dt><dd>${nt(r.value)}</dd></div>`).join("")}</dl>`}function oe(t,e){let n=Fs(),r=n.querySelector(".mayabot-product-grid"),o=n.querySelector(".mayabot-product-title"),i=t.length;if(ie=Array.isArray(t)?[...t]:[],je=e||K,n.classList.remove("count-1","count-2","count-3","count-many"),n.classList.add(js(i)),n.style.setProperty("--mayabot-card-count",String(zs(i))),o.textContent=je,!i){r.innerHTML='<p class="mayabot-product-empty">No matching products are currently available.</p>',n.classList.add("active");return}r.innerHTML=t.map(a=>{let s=nt(a.id);return`
        <article class="mayabot-product-card" data-product-id="${s}">
          <img class="mayabot-product-image" src="${nt(a.imageUrl||Ls)}" alt="${nt(a.name)}">
          <h3 class="mayabot-product-name">${nt(a.name||a.title||"Product")}</h3>
          <p class="mayabot-product-meta">${nt(a.brand)} - ${nt(Gs(a))}</p>
          ${Js(a.id)}
          <div class="mayabot-product-actions">
            <button type="button" data-add="${s}">Add</button>
            <button type="button" class="secondary" data-view="${s}">View</button>
          </div>
        </article>
      `}).join(""),r.querySelectorAll("[data-add]").forEach(a=>{a.addEventListener("click",async()=>{await Ys(a.getAttribute("data-add"))})}),r.querySelectorAll("[data-view]").forEach(a=>{a.addEventListener("click",async()=>{await qs(a.getAttribute("data-view"))})}),n.classList.add("active"),t.length>0&&Zs()}function Zs(){window.setTimeout(()=>{let t=document.getElementById("mayabot-chat"),e=document.getElementById("mayabot-msgs");e&&(e.innerHTML=""),t&&t.classList.remove("visible")},dt)}async function Qr(t,e=K,n={}){let r=Vs(t),o=String(n.searchQuery||"").trim();ae=Xs(n.comparisonFacts);let i=ae.size>0;if(ze=!1,!r.length&&!o)return oe([],e),qe([],[],"missing_product_ids");try{let{products:a,source:s,reason:u}=await Yr(r,o);return oe(a,e),Bs(a,i),qe(r,a,u,{source:s,searchQuery:o})}catch(a){return console.warn("[AI Hub Widget] Product overlay failed:",a),oe([],e),qe(r,[],"product_overlay_fetch_failed",{searchQuery:o})}}function Xr(t={}){if(!ie.length)return!1;let e=String(t.sort_by||t.sortBy||"price_asc").trim().toLowerCase(),n=[...ie].sort((r,o)=>tc(r,o,e));return oe(n,ec(je,e)),!0}function tc(t,e,n){return n==="price_desc"?ft(e.price,Number.NEGATIVE_INFINITY)-ft(t.price,Number.NEGATIVE_INFINITY):n==="rating"?ft(e.rating||e.review_rating,Number.NEGATIVE_INFINITY)-ft(t.rating||t.review_rating,Number.NEGATIVE_INFINITY):n==="newest"?Kr(e)-Kr(t):ft(t.price,Number.POSITIVE_INFINITY)-ft(e.price,Number.POSITIVE_INFINITY)}function ft(t,e){let n=String(t??"").replace(/,/g,"").match(/-?\d+(?:\.\d+)?/);if(!n)return e;let r=Number(n[0]);return Number.isFinite(r)?r:e}function Kr(t){let e=t?.updated_at||t?.created_at||t?.date||"",n=Date.parse(String(e||""));return Number.isFinite(n)?n:0}function ec(t,e){let n={price_asc:"sorted low to high",price_desc:"sorted high to low",rating:"sorted by rating",newest:"newest first"};return`${String(t||K).replace(/\s+-\s+sorted.*$/i,"")} - ${n[e]||n.price_asc}`}function Zr(t){return t.action===c.SHOW_PRODUCTS||t.action===c.SHOW_COMPARISON||t.action===c.SHOW_PRODUCT_DETAIL||t.action===c.SORT_PRODUCTS}async function to(t){return t.action===c.SHOW_COMPARISON?Jr(t.parameters||{},"Product comparison",{syncListing:!1,comparisonFacts:(t.parameters||{}).comparison}):t.action===c.SHOW_PRODUCTS?Jr(t.parameters||{},K):t.action===c.SHOW_PRODUCT_DETAIL?oc(t.parameters||{}):t.action===c.SORT_PRODUCTS?Xr(t.parameters||{}):!1}async function Jr(t,e=K,n={}){let r=Array.isArray(t[d.PRODUCT_IDS])?t[d.PRODUCT_IDS]:[],o=rc(t),a=n.syncListing!==!1?await nc(o):{succeeded:!1,handled:!1,status:"skipped",stage:"product_display_sync",reason:"comparison_overlay"},s=await Qr(r,t.title||o||e,{searchQuery:o,comparisonFacts:n.comparisonFacts}),u={...s.evidence||{},listing_sync_status:a.status||"",listing_sync_stage:a.stage||"",listing_sync_reason:a.reason||""};return s.status!=="succeeded"?{...s,evidence:u}:o&&a.handled&&!a.succeeded?{status:"failed",stage:"product_display_sync",reason:a.reason||a.status||"listing_sync_failed",evidence:u}:{...s,stage:a.succeeded?"product_display_sync":s.stage,evidence:u}}async function nc(t){let e=eo(t);return e?Ct({action:c.FILTER_PRODUCTS,params:{[d.SEARCH_QUERY]:e,query:e,q:e}}):{succeeded:!1,handled:!1,status:"skipped",stage:"product_display_sync",reason:"missing_search_query"}}function rc(t){return eo(t[d.SEARCH_QUERY]||t.search||t.query||t.q||"")}function eo(t){return String(t||"").trim()}async function oc(t){let e="";try{e=await Zt(t[d.PRODUCT_ID])}catch(n){return console.warn("[AI Hub Widget] Product detail URL lookup failed:",n),!1}return e?(window.location.href=e,!0):!1}var Ve="stop_action_fallback",ic=new Set([c.SHOW_PRODUCTS,c.SHOW_COMPARISON,c.SHOW_PRODUCT_DETAIL,c.SORT_PRODUCTS]);function no(t){return Ot()&&!ic.has(t.action)}async function ro(t){let e=await Ct(t);return e.succeeded?!0:e.blocked||e.disabled?Ve:!1}function oo(t){return window.dispatchEvent(new CustomEvent(St.MAYABOT_ACTION,{detail:t})),{status:"requested",stage:"browser_event",reason:"event_dispatched_without_confirmation"}}var ac=12,sc=8,cc=80,io=Object.freeze([["data-entity-id",""],["data-product-id","product"],["data-listing-id","listing"],["data-offer-id","offer"],["data-plan-id","plan"],["data-item-id",""]]),uc="data-entity-type",lc="entity",ao=Object.freeze(["sort","sort_by","sortby","orderby","order_by","order"]),dc=Object.freeze(["page","p","offset","cursor","q","query","search","token","session","email","phone","name","address","utm_source","utm_medium","utm_campaign"]),pc=Object.freeze([["price","[data-price], [itemprop='price'], .price"],["rating","[data-rating], [itemprop='ratingValue'], .rating"],["availability","[data-availability], [itemprop='availability'], .availability, .stock"]]);function B(t){return String(t||"").replace(/\s+/g," ").trim().slice(0,cc)}function fc(t){if(!t||typeof t.getBoundingClientRect!="function")return!1;let e=t.getBoundingClientRect();if(e.width<=0||e.height<=0)return!1;let n=t.ownerDocument?.defaultView,r=n?.getComputedStyle?.(t);if(r&&(r.visibility==="hidden"||r.display==="none"))return!1;let o=t.ownerDocument?.documentElement,i=Number(n?.innerWidth||o?.clientWidth||0),a=Number(n?.innerHeight||o?.clientHeight||0);return i>0&&a>0&&e.bottom>0&&e.right>0&&e.top<a&&e.left<i}function mc(t){for(let[e,n]of io){let r=B(t.getAttribute(e));if(r)return{id:r,impliedType:n}}return null}function hc(t,e){return B(t.getAttribute(uc)).toLowerCase()||e||lc}function _c(t){let e=t.querySelector?.("h1, h2, h3, h4, [data-entity-name], [itemprop='name']");return B(e?.textContent||t.getAttribute("aria-label")||t.getAttribute("title"))}function gc(t){let e=t.matches?.("a[href]")?t:t.querySelector?.("a[href]");return wc(e?.href||"")}function yc(t){let e={};for(let[n,r]of pc){let o=t.querySelector?.(r);if(!o)continue;let i=B(o.getAttribute?.("content")||o.getAttribute?.(`data-${n}`)||o.textContent);i&&(e[n]=i)}return e}function bc(){return io.map(([t])=>`[${t}]`).join(",")}function Tc(){let t=new Set,e=[];for(let n of N(bc())){if(e.length>=ac)break;let r=mc(n);!r||t.has(r.id)||!fc(n)||(t.add(r.id),e.push({id:r.id,entity_type:hc(n,r.impliedType),label:_c(n),route:gc(n),facts:yc(n)}))}return e}function Ac(){let t=so();if(!t)return{};let e={};for(let[n,r]of t.entries()){let o=n.toLowerCase();if(!(dc.includes(o)||ao.includes(o))){if(Object.keys(e).length>=sc)break;e[B(n)]=B(r)}}return e}function Ec(){let t=so();for(let n of ao){let r=B(t?.get?.(n));if(r)return r}let e=N("select[name*='sort' i], select[id*='sort' i]")[0];return B(e?.value)}function Sc(){try{return{path:B(window.location.pathname)||"/",search:B(window.location.search)}}catch{return{path:"",search:""}}}function se(){return{route:Sc(),filters:Ac(),sort:Ec(),visible_entities:Tc()}}function so(){try{return new URLSearchParams(window.location.search)}catch{return null}}function wc(t){if(!t)return"";try{let e=new URL(t,window.location.origin);return e.origin!==window.location.origin?"":`${e.pathname}${e.search}`||"/"}catch{return""}}var dd=Object.freeze(["CHECKOUT","CLEAR_CART","REMOVE_FROM_CART","UPDATE_CART_QUANTITY","CLEAR_HISTORY","SUBMIT_PAYMENT","PLACE_ORDER"]);var S=Object.freeze({DISPLAY:"display",NAVIGATION:"navigation",DETAIL:"detail",FILTER:"filter",SORT:"sort",CART:"cart",NONE:"none"}),Ic=1200,Oc=60,Cc=Object.freeze({SHOW_PRODUCTS:S.DISPLAY,SHOW_ENTITIES:S.DISPLAY,SHOW_COMPARISON:S.DISPLAY,COMPARE_ENTITIES:S.DISPLAY,NAVIGATE_TO:S.NAVIGATION,SHOW_PRODUCT_DETAIL:S.DETAIL,OPEN_ENTITY_DETAIL:S.DETAIL,FILTER_PRODUCTS:S.FILTER,CLEAR_FILTERS:S.FILTER,SORT_PRODUCTS:S.SORT,SORT_ENTITIES:S.SORT,ADD_TO_CART:S.CART,REMOVE_FROM_CART:S.CART,UPDATE_CART_QUANTITY:S.CART,CLEAR_CART:S.CART}),xc="[data-cart-count], [data-testid='cart-count'], .cart-count, #cart-count";function uo(t){return Cc[String(t||"").toUpperCase()]||S.NONE}function Ke(){let t=se();return{path:t.route.path,search:t.route.search,filters:t.filters,sort:String(t.sort||"").toLowerCase(),visibleIds:t.visible_entities.map(e=>String(e.id)),cartCount:Rc()}}function Rc(){let t=document.querySelector(xc);if(!t)return null;let e=t.getAttribute("data-cart-count")??t.textContent,n=Number.parseInt(String(e||"").replace(/[^\d-]/g,""),10);return Number.isFinite(n)?n:null}function lo(t){let e=[];for(let n of["product_ids","entity_ids"])Array.isArray(t[n])&&e.push(...t[n].map(String));for(let n of["product_id","entity_id"])t[n]&&e.push(String(t[n]));return e}function Rt(t){let e=String(t||"").split("?")[0].split("#")[0];return e.length>1?e.replace(/\/+$/,""):e}function Ge(t){return String(t||"").trim().toLowerCase().replace(/[^a-z0-9/_\s-]+/g," ").replace(/[_-]+/g," ").replace(/\s+/g," ").trim().replace(/\s+/g,"-")}function co(t){let e=String(t||"").trim();if(!e||/^(?:javascript:|data:|\/\/)/i.test(e))return"";try{let n=new URL(e,window.location.origin);return n.origin!==window.location.origin?"":Rt(n.pathname||"/")}catch{return""}}function Nc(t){let e=String(t||"").trim();if(!e)return"";if(e==="/"||Ge(e)==="home")return"/";let n=window.AIHubAdapterRuntime?.config?.adapter?.routes||window.AIHubAdapter?.config?.adapter?.routes||{},r=Ge(e);for(let[o,i]of Object.entries(n)){if(Ge(o)!==r)continue;let a=co(i);if(a)return a}return e.startsWith("/")||/^https?:\/\//i.test(e)?co(e):Rt(`/${r}`)}function vc(t,e){let n=lo(t);return n.length?n.filter(o=>!e.visibleIds.includes(o)).length?{satisfied:!1,reason:"requested_records_not_visible"}:{satisfied:!0,reason:""}:e.visibleIds.length>0?{satisfied:!0,reason:""}:{satisfied:!1,reason:"nothing_visible"}}function Pc(t,e,n){let r=Nc(t.page),o=Rt(e.path);return r&&o===r?{satisfied:!0,reason:""}:!r&&o!==Rt(n.path)?{satisfied:!0,reason:""}:r&&o!==Rt(n.path)?{satisfied:!1,reason:"wrong_route"}:{satisfied:!1,reason:"route_unchanged"}}function Lc(t,e,n){let r=lo(t)[0];return r?`${e.path}${e.search}`.includes(r)?{satisfied:!0,reason:""}:e.visibleIds.includes(r)&&e.path!==n.path?{satisfied:!0,reason:""}:{satisfied:!1,reason:"record_not_opened"}:{satisfied:!1,reason:"no_record_requested"}}function Dc(t,e,n){if(t==="CLEAR_FILTERS")return Object.keys(n.filters).length===0?{satisfied:!0,reason:""}:{satisfied:!1,reason:"filters_still_active"};let r=new Map(Object.entries(n.filters).map(([u,f])=>[u.toLowerCase(),We(f)])),o=e.filters&&typeof e.filters=="object"?e.filters:e,i=new Set(["product_ids","entity_ids","page","search_query","query","q","request_id"]),a=Object.entries(o||{}).filter(([u,f])=>!i.has(u.toLowerCase())&&We(f));return a.length?a.every(([u,f])=>{let w=r.get(u.toLowerCase());return w!==void 0&&w===We(f)})?{satisfied:!0,reason:""}:{satisfied:!1,reason:"filter_value_mismatch"}:r.size>0?{satisfied:!0,reason:""}:{satisfied:!1,reason:"no_filter_observed"}}function We(t){return(Array.isArray(t)?t:[t]).map(n=>String(n??"").trim().toLowerCase()).filter(Boolean).sort().join(",")}function Uc(t,e,n){let r=String(t.sort_by||"").toLowerCase();return r&&e.sort&&e.sort.includes(r.split("_")[0])?{satisfied:!0,reason:""}:e.visibleIds.join(",")!==n.visibleIds.join(",")?{satisfied:!0,reason:""}:{satisfied:!1,reason:"order_unchanged"}}function kc(t,e,n){if(n.cartCount===null||e.cartCount===null)return{satisfied:!1,reason:"cart_state_unobservable"};let r=e.cartCount>n.cartCount,o=e.cartCount<n.cartCount;return t==="ADD_TO_CART"?r?{satisfied:!0,reason:""}:{satisfied:!1,reason:"cart_unchanged"}:t==="REMOVE_FROM_CART"?o?{satisfied:!0,reason:""}:{satisfied:!1,reason:"cart_unchanged"}:t==="CLEAR_CART"?e.cartCount===0?{satisfied:!0,reason:""}:{satisfied:!1,reason:"cart_not_empty"}:e.cartCount!==n.cartCount?{satisfied:!0,reason:""}:{satisfied:!1,reason:"cart_unchanged"}}function Mc(t,e,n){let r=String(t?.action||"").toUpperCase(),o=t?.parameters||t?.params||{},i=uo(r);return i===S.DISPLAY?vc(o,e):i===S.NAVIGATION?Pc(o,e,n):i===S.DETAIL?Lc(o,e,n):i===S.FILTER?Dc(r,o,e):i===S.SORT?Uc(o,e,n):i===S.CART?kc(r,e,n):{satisfied:!0,reason:"no_postcondition"}}async function po(t,e){let n=uo(t?.action);if(n===S.NONE)return{family:n,verified:!0,reason:"no_postcondition"};let r=Date.now()+Ic,o={satisfied:!1,reason:"not_observed"};for(;Date.now()<r&&(o=Mc(t,Ke(),e),!o.satisfied);)await Hc(Oc);return{family:n,verified:o.satisfied,reason:o.reason}}function Hc(t){return new Promise(e=>window.setTimeout(e,t))}var y=Object.freeze({searchForm:"search-form",searchInput:"search-input",searchSubmit:"search-submit",searchResults:"search-results",addToCart:"add-to-cart",checkout:"checkout",clearCart:"clear-cart",cartButton:"cart-button",cartLineItem:"cart-line-item",navLink:"nav-link",productCard:"product-card",productLink:"product-link",productName:"product-name",productDetail:"product-detail",productTitle:"product-title"}),Qe="data-aihub-nav",fo="data-entity-name",Y=4e3,mo=1500,Fc=80,Bc='[id^="mayabot"], [data-aihub-widget]';function mt(t){return!!t&&!t.closest?.(Bc)}var ht=t=>`[data-aihub-role="${t}"]`,rt=t=>N(ht(t)).filter(mt),O=t=>rt(t)[0]||null;function $c(t){let e=_(t);return e&&N(`[data-product-id="${Xe(e)}"]`).find(mt)||null}function _(t){return String(t??"").trim()}function Xe(t){return window.CSS?.escape?window.CSS.escape(t):_(t).replace(/["\\]/g,"\\$&")}async function U(t,e){let n=Date.now()+e;for(;;){let r=t();if(r)return r;if(Date.now()>=n)return null;await new Promise(o=>window.setTimeout(o,Fc))}}function J(){return!!(O(y.searchForm)||O(y.searchInput)||O(y.searchSubmit))}function Nt(){return!!O(y.addToCart)}function vt(){return!!O(y.checkout)}function Pt(){return!!O(y.clearCart)}function Lt(){return rt(y.navLink).length>0}function lt(){return Ut().length>0}function q(t){let e=String(t||"").split("?")[0].split("#")[0];return e.length>1?e.replace(/\/+$/,""):e||"/"}function ce(t){try{let e=new URL(String(t||""),window.location.origin);return e.origin!==window.location.origin?"":`${e.pathname}${e.search}`||"/"}catch{return""}}function Dt(t){return _(t).toLowerCase().replace(/[^a-z0-9]+/g," ").trim()}function $(t){return _(t).toLowerCase().replace(/[\s\-_/\\,.:;|]+/g," ").replace(/\s+/g," ").trim()}function Ut(){let t=rt(y.productCard);return t.length?t:N("[data-product-id]").filter(mt)}function _t(t){let e=_(t?.getAttribute?.(fo));return e||_(t?.querySelector?.(ht(y.productName))?.textContent)}var Je="product_id",Yc="product_name";function ue(t,e){let n=$c(t);if(n)return{card:n,matchedBy:Je};let r=$(e);if(!r)return null;let o=Ut().filter(i=>$(_t(i))===r);return o.length===1?{card:o[0],matchedBy:Yc}:o.length>1?{ambiguous:!0,matchCount:o.length}:null}function j(t,e,n=""){return{handled:!0,status:"succeeded",self_verified:!0,stage:t,reason:n,evidence:e||{}}}function E(t,e,n){return{handled:!0,status:"failed",stage:t,reason:e,evidence:n||{}}}function ho(t,e,n){return{handled:!0,status:"unconfirmed",stage:t,reason:e,evidence:n||{}}}function _o(t,e){return{handled:!0,status:"unsupported_host",stage:t,reason:e,evidence:{}}}function z(t){return t?(Ao(t),go(t,"down"),go(t,"up"),typeof t.click=="function"?t.click():Eo(t,"click"),Vc(t),!0):!1}function bo(t,e){return t?(Ao(t),qc(t,de(e)),jc(t),!0):!1}function To(t){if(!t)return!1;let e=de(t.tagName).toLowerCase()==="form"?t:t.closest?.("form");return e&&typeof e.requestSubmit=="function"?(e.requestSubmit(),!0):z(t)}function Ao(t){try{t.scrollIntoView?.({behavior:"smooth",block:"center",inline:"center"})}catch{}typeof t.focus=="function"&&t.focus({preventScroll:!0})}function qc(t,e){if(Gc(t)){t.textContent=e;return}let n=Object.getPrototypeOf(t),r=Object.getOwnPropertyDescriptor(n,"value");if(r?.set){r.set.call(t,e);return}t.value=e}function jc(t){yo(t,"beforeinput"),yo(t,"input"),t.dispatchEvent(new Event("change",{bubbles:!0}))}function go(t,e){zc(t,`pointer${e}`),Eo(t,`mouse${e}`)}function zc(t,e){typeof PointerEvent=="function"&&t.dispatchEvent(new PointerEvent(e,{bubbles:!0,cancelable:!0,pointerType:"mouse",isPrimary:!0}))}function Eo(t,e){t.dispatchEvent(new MouseEvent(e,{bubbles:!0,cancelable:!0,view:window}))}function yo(t,e){if(typeof InputEvent=="function"){t.dispatchEvent(new InputEvent(e,{bubbles:!0,cancelable:!0,inputType:"insertText"}));return}t.dispatchEvent(new Event(e,{bubbles:!0,cancelable:!0}))}function Vc(t){let e=de(t.getAttribute?.("role")).toLowerCase();["button","link","menuitem","option","tab"].includes(e)&&(le(t,"keydown","Enter"),le(t,"keyup","Enter"),(e==="button"||e==="tab")&&(le(t,"keydown"," "),le(t,"keyup"," ")))}function le(t,e,n){t.dispatchEvent(new KeyboardEvent(e,{bubbles:!0,cancelable:!0,key:n}))}function Gc(t){let e=de(t?.getAttribute?.("role")).toLowerCase();return!!(t?.isContentEditable||!("value"in t)&&["searchbox","textbox"].includes(e))}function de(t){return String(t||"").trim()}function Wc(t){try{let e=`${window.location.pathname}${window.location.search}`.toLowerCase();return e.includes(encodeURIComponent(t).toLowerCase())||e.includes(t.toLowerCase())}catch{return!1}}var Kc=1;function Qc(t,e){let n=_(t).split(/\s+/).filter(Boolean);return n.length<2?!0:_(e).split(/\s+/).includes(n[0])}function Xc(t){let e=_(t).split(/\s+/).filter(n=>n.length>2);return e.length<2?"":e.reduce((n,r)=>r.length>n.length?r:n,"")}async function kt(t,{broadenIfSparse:e=!1,requested:n=[],filters:r={}}={}){let o=_(t);if(!J())return null;if(!o)return _o("host_search","empty_query");let i=await wo(o,n,r);if(!e||!i||i.status!=="succeeded")return i;let a=i.evidence?.result_count;if(typeof a!="number"||a>Kc)return i;let s=Xc(o);if(!s||s===o||!Qc(o,s))return i;let u=await wo(s,n,r);return u?.status==="succeeded"&&(u.evidence?.result_count||0)>a?{...u,evidence:{...u.evidence,broadened_from:o}}:i}function Jc(){return Ut().map(t=>({id:_(t.getAttribute?.("data-product-id")||""),name:_(_t(t))})).filter(t=>t.id||t.name)}function Zc(t){return(Array.isArray(t)?t:[]).map(e=>typeof e=="string"?{name:e}:e||{}).map(e=>({id:_(e.id||""),name:_(e.name||"")})).filter(e=>e.id||e.name)}function So(t,e){let n=new Set(e.map(o=>o.id).filter(Boolean)),r=new Set(e.map(o=>$(o.name)).filter(Boolean));return t.filter(o=>o.id&&n.has(o.id)||o.name&&r.has($(o.name))).length}function tu(t,e){if(!t||typeof t.querySelectorAll!="function")return[];let n=[];for(let r of t.querySelectorAll("[data-aihub-filter]")){let o=_(r.getAttribute("data-aihub-filter")),i=o&&e?e[o]:"";r.value=i!=null?String(i):"",r.value&&n.push(o)}return n}async function wo(t,e=[],n={}){let r=O(y.searchInput);if(!r){let b=O(y.searchSubmit)||O(y.searchForm);b&&z(b),r=await U(()=>O(y.searchInput),mo)}if(!r)return E("host_search","search_input_unavailable");bo(r,t);let o=r.closest?.("form")||O(y.searchForm),i=tu(o,n);To(o||O(y.searchSubmit)||r);let a=await U(()=>{let b=O(y.searchResults);return!b||b.getAttribute("data-results-loading")==="true"?null:b},Y);if(!a)return ho("host_search","results_not_settled");let s=Number(a.getAttribute("data-result-count")),u=Jc(),f=Zc(e),w=f.filter(b=>b.name),T=So(f,u),I=So(w,u),h={result_count:Number.isFinite(s)?s:null,query:a.getAttribute("data-query")||"",route:`${window.location.pathname}${window.location.search}`,route_reflects_query:Wc(t),requested_ids:f.map(b=>b.id).filter(Boolean),requested_count:f.length,named_requested_count:w.length,rendered_ids:u.map(b=>b.id).filter(Boolean),rendered_product_count:u.length,visible_requested_count:T,applied_filters:i};return h.route_reflects_query||h.query.toLowerCase().includes(t.toLowerCase())?a.getAttribute("data-results-empty")==="true"||h.result_count===0?E("host_search","no_results",h):w.length&&I===0?E("host_search","requested_records_not_visible",h):j("host_search",h):E("host_search","query_not_reflected",h)}var Mt="host_add_to_cart",gt="host_clear_cart",Ht="host_product_detail";function yt(){let t=O(y.cartButton)||N("[data-cart-count]").find(mt)||null;if(!t)return null;let e=Number(t.getAttribute("data-cart-count"));return Number.isFinite(e)?e:null}function Ze(){return rt(y.cartLineItem).map(t=>_(t.getAttribute("data-product-id"))).filter(Boolean)}function Io(t){return!!t.disabled||t.getAttribute("aria-disabled")==="true"}async function Oo(t,e,n){let r=ue(e,n);if(!r&&n&&J()){let o=await kt(n);o&&o.status==="succeeded"&&(r=ue(e,n))}return r?r.ambiguous?{error:E(t,"ambiguous_product",{product_name:_(n),match_count:r.matchCount})}:r:{error:E(t,"product_not_on_page",{product_id:_(e),product_name:_(n)})}}function eu(t,e){let n=_(e);if(n){let r=N(`${ht(y.addToCart)}[data-product-id="${Xe(n)}"]`).find(mt);if(r)return r}return t?.querySelector?.(ht(y.addToCart))||null}async function tn(t){if(!Nt()&&!lt())return null;let e=_(t?.product_id||t?.entity_id),n=_(t?.product_name),r=await Oo(Mt,e,n);if(r.error)return r.error;let o=_(r.card.getAttribute("data-product-id"))||e,i=eu(r.card,r.matchedBy===Je?e:o);if(!i)return E(Mt,"add_control_missing",{product_id:o,product_name:n});if(Io(i))return E(Mt,"add_control_disabled",{product_id:o,product_name:n});let a=yt(),s=Ze();z(i);let u=await U(()=>{let w=yt(),T=Ze(),I=a!=null&&w!=null&&w>a,h=o&&T.includes(o)&&!s.includes(o),x=T.length>s.length;return I||h||x?{afterCount:w,lines:T}:null},Y),f={cart_before:a,cart_after:yt(),product_id:o,product_name:n,matched_by:r.matchedBy};return u?j(Mt,{...f,line_item_present:o?Ze().includes(o):!0}):E(Mt,"cart_unchanged",f)}async function en(){if(!Pt())return null;let t=O(y.clearCart);if(!t)return E(gt,"clear_control_missing");if(Io(t))return E(gt,"clear_control_disabled");let e=yt();if(e==null)return E(gt,"cart_state_unobservable");if(e===0)return j(gt,{cart_before:0,cart_after:0});z(t);let n=await U(()=>yt()===0?!0:null,Y),r={cart_before:e,cart_after:yt()};return n?j(gt,r):E(gt,"cart_not_empty",r)}function nu(t){return t?.querySelector?.(ht(y.productLink))||t?.querySelector?.("a[href]")||null}function ru(t,e){let n=O(y.productDetail),r=$(e);if(n){let i=_(n.getAttribute("data-product-id"));if(t&&i&&i===t)return"product_id";let a=$(_t(n));if(r&&a&&a===r)return"product_name"}let o=O(y.productTitle);return o&&r&&$(o.textContent)===r?"product_title":""}async function nn(t){if(!lt()&&!J())return null;let e=_(t?.product_id||t?.entity_id),n=_(t?.product_name),r=await Oo(Ht,e,n);if(r.error)return r.error;let o=_(r.card.getAttribute("data-product-id"))||e,i=nu(r.card);if(!i)return E(Ht,"product_link_missing",{product_id:o,product_name:n});let a=q(window.location.pathname);z(i);let s=await U(()=>ru(o,n)||null,Y),u={product_id:o,product_name:n,matched_by:r.matchedBy,route:`${window.location.pathname}${window.location.search}`,verified_by:s||""};return s?j(Ht,u):q(window.location.pathname)===a?E(Ht,"route_unchanged",u):E(Ht,"product_page_not_confirmed",u)}var Ft="host_navigate",Co="host_checkout",ou="main, [data-aihub-role='search-results'], [data-product-id]";function iu(t){let e=Dt(t);if(!e)return null;let n=rt(y.navLink),r=s=>[Dt(s.getAttribute(Qe)),Dt(s.textContent),Dt(ce(s.getAttribute("href")||s.href))].filter(Boolean),o=n.find(s=>r(s).includes(e));if(o)return o;let i=null,a=0;for(let s of n)for(let u of r(s))!e.includes(u)&&!u.includes(e)||u.length>a&&(a=u.length,i=s);return i}function au(t){try{return new URL(String(t||""),window.location.origin).searchParams}catch{return new URLSearchParams}}function xo(t){if(q(window.location.pathname)!==q(t))return!1;let e=new URLSearchParams(window.location.search);for(let[n,r]of au(t).entries())if(e.get(n)!==r)return!1;return!0}async function rn(t){if(!Lt())return null;let e=iu(t);if(!e)return E(Ft,"no_matching_nav_target",{target:_(t)});let n=ce(e.getAttribute("href")||e.href),r=q(window.location.pathname);z(e);let o=await U(()=>n&&xo(n)?!0:null,Y),i=q(window.location.pathname),a={target:_(t),expected:q(n),route:`${window.location.pathname}${window.location.search}`};return o?await U(()=>document.querySelector(ou)?!0:null,Y)?j(Ft,a):E(Ft,"page_not_ready",a):i!==r?E(Ft,"wrong_route",{...a,actual:i}):E(Ft,"route_unchanged",{...a,actual:i})}async function on(){if(!vt())return null;let t=rt(y.checkout)[0];if(!t)return null;let e=`${window.location.pathname}${window.location.search}`,n=ce(t.getAttribute("href")||"/checkout");z(t);let r=await U(()=>n&&xo(n)?!0:null,Y),o=`${window.location.pathname}${window.location.search}`,i={expected:q(n||"/checkout"),route:o};return r?j(Co,i):E(Co,o===e?"route_unchanged":"wrong_route",i)}var No=new Set([c.FILTER_PRODUCTS,c.SHOW_PRODUCTS]);function su(t){let e=t?.params||{},n=e[d.PRODUCT_IDS]||e[d.ENTITY_IDS]||[],r=(Array.isArray(n)?n:[]).map(i=>({id:String(i||""),name:""})),o=e[d.PRODUCT_NAME];return!r.length&&o&&r.push({id:"",name:String(o)}),r}var vo=new Set([c.SHOW_PRODUCT_DETAIL]);function Bt(t){return t.parameters||t.params||{}}function cu(t){let e=Bt(t).filters;if(!e||typeof e!="object"||Array.isArray(e))return{};let n={};for(let[r,o]of Object.entries(e))o==null||o===""||typeof o!="object"&&(n[String(r)]=String(o));return n}function Po(t){let e=Bt(t);return String(e[d.SEARCH_QUERY]||e.search||e.query||e.q||"").trim()}function Lo(t){let e=Bt(t);return String(e[d.PAGE]||e.page||e.target||"").trim()}function Ro(t){let e=Bt(t);return!!(e[d.PRODUCT_ID]||e.entity_id||String(e[d.PRODUCT_NAME]||"").trim())}function Do(t){let e=t.action;return e===c.ADD_TO_CART?(Nt()||lt())&&Ro(t):e===c.CHECKOUT?vt():e===c.CLEAR_CART?Pt():vo.has(e)?(lt()||J())&&Ro(t):No.has(e)?J()&&!!Po(t):e===c.NAVIGATE_TO?Lt()&&!!Lo(t):!1}async function Uo(t){let e=t.action,n=Bt(t);if(e===c.ADD_TO_CART)return tn(n);if(e===c.CHECKOUT)return on();if(e===c.CLEAR_CART)return en();if(vo.has(e))return nn(n);if(No.has(e)){let r=Po(t);return r?kt(r,{broadenIfSparse:!0,requested:su(t),filters:cu(t)}):null}if(e===c.NAVIGATE_TO){let r=Lo(t);return r?rn(r):null}return null}var uu=Object.freeze([{name:"host_contract",canExecute:Do,execute:Uo},{name:"runtime_adapter",canExecute:no,execute:ro},{name:"product_overlay",canExecute:Zr,execute:to},{name:"entity_overlay",canExecute:br,execute:Tr},{name:"handoff_overlay",canExecute:Cr,execute:xr},{name:"platform_adapter",canExecute:()=>!0,execute:Gn},{name:"provider_adapter",canExecute:or,execute:ir},{name:"navigation",canExecute:Nr,execute:vr},{name:"browser_event",canExecute:()=>!0,execute:oo}]);async function sn(t){let e=[];for(let n of t||[]){let r=Dr(n),o=await lu(r);o&&e.push(o)}return e}async function lu(t){if(!t.action)return;let e=Date.now(),n=window.location.href,r=Ke();await Vt(l.apiUrl,l.siteId,t,{status:"requested",stage:"widget_dispatch",requested_url:n,final_url:n,evidence:an(t,n,n)}),await Vt(l.apiUrl,l.siteId,t,{status:"executing",stage:"widget_dispatch",requested_url:n,final_url:window.location.href,evidence:an(t,n,window.location.href)});let o;try{o=await du(t)}catch(u){o={status:"failed",stage:"widget_dispatch",reason:u instanceof Error?u.message:"execution_error"}}let i=o.status==="succeeded"&&o.self_verified?{family:o.stage||"host_contract",verified:!0,reason:o.reason||""}:o.status==="succeeded"?await po(t,r):{family:"none",verified:!1,reason:o.reason||"execution_failed"},a=window.location.href,s={...an(t,n,a,o),postcondition_family:i.family,postcondition_verified:i.verified,postcondition_reason:i.reason};return await Vt(l.apiUrl,l.siteId,t,{status:o.status,stage:o.stage,reason:o.reason,duration_ms:Date.now()-e,requested_url:n,final_url:a,evidence:s}),{action:t.action,request_id:t.request_id||t.action_request_id||"",turn_id:t.turn_id||"",sequence:Number(t.sequence||0),status:o.status,stage:o.stage,reason:o.reason,verified:i.verified,postcondition:i.family,requested_url:n,final_url:a,evidence:s}}async function du(t){if(!t.action)return{status:"failed",stage:"normalization",reason:"missing_action"};for(let e of uu){if(!e.canExecute(t))continue;let n=await e.execute(t),r=pu(n,e.name);if(r)return r}return{status:"failed",stage:"all",reason:"no_executor_succeeded"}}function pu(t,e){if(t===!0)return{status:"succeeded",stage:e,reason:""};if(t===Ve)return{status:"blocked",stage:e,reason:"action_blocked"};if(!t||typeof t!="object")return null;let n=String(t.status||"").trim().toLowerCase();return n?{status:n,stage:String(t.stage||e).trim()||e,reason:String(t.reason||"").trim(),self_verified:!!t.self_verified,evidence:t.evidence&&typeof t.evidence=="object"?t.evidence:{}}:null}function an(t,e,n,r={}){let o=t.parameters||t.params||{},i={requested_url:e,final_url:n,url_changed:e!==n,path_changed:ko(e)!==ko(n),title:document.title||"",stage:r.stage||"",result_status:r.status||""};return o.page&&(i.target_page=o.page),o.product_id&&(i.product_id=o.product_id),o.entity_id&&(i.entity_id=o.entity_id),Array.isArray(o.product_ids)&&(i.product_count=o.product_ids.length),Array.isArray(o.entity_ids)&&(i.entity_count=o.entity_ids.length),{...i,...r.evidence&&typeof r.evidence=="object"?r.evidence:{}}}function ko(t){try{return new URL(t,window.location.href).pathname}catch{return""}}var g=Object.freeze({CANCELLED:"cancelled",NETWORK:"network",TIMEOUT:"timeout",ACCESS_DENIED:"access_denied",INVALID_REQUEST:"invalid_request",PAYLOAD_TOO_LARGE:"payload_too_large",UNSUPPORTED_MEDIA:"unsupported_media",RATE_LIMITED:"rate_limited",PROVIDER_UNAVAILABLE:"provider_unavailable",SERVER_ERROR:"server_error",MICROPHONE:"microphone",UNKNOWN:"unknown"}),Mo=Object.freeze({[g.CANCELLED]:"Stopped",[g.NETWORK]:"Connection issue",[g.TIMEOUT]:"Timed out",[g.ACCESS_DENIED]:"Access denied",[g.INVALID_REQUEST]:"Try again",[g.PAYLOAD_TOO_LARGE]:"Recording too long",[g.UNSUPPORTED_MEDIA]:"Audio not supported",[g.RATE_LIMITED]:"Service busy",[g.PROVIDER_UNAVAILABLE]:"Service unavailable",[g.SERVER_ERROR]:"Service error",[g.MICROPHONE]:"Mic unavailable",[g.UNKNOWN]:"Try again"}),Ho=64,R=class extends Error{constructor(e,{status:n=0,code:r="",requestId:o="",stage:i=""}={}){super(`voice_transport_${e}`),this.name="VoiceTransportError",this.category=e,this.status=Number(n)||0,this.code=String(r||"").slice(0,Ho),this.requestId=String(o||"").slice(0,Ho),this.stage=i}get customerMessage(){return fu(this.category)}toDiagnostics(){return{category:this.category,status:this.status,code:this.code,request_id:this.requestId,stage:this.stage}}};function fu(t){return Mo[t]||Mo[g.UNKNOWN]}function Fo(t){return t instanceof R&&t.category===g.CANCELLED}function mu(t){let e=Number(t)||0;return e===401||e===403?g.ACCESS_DENIED:e===408?g.TIMEOUT:e===413?g.PAYLOAD_TOO_LARGE:e===415?g.UNSUPPORTED_MEDIA:e===429?g.RATE_LIMITED:e===502||e===503||e===504?g.PROVIDER_UNAVAILABLE:e>=500?g.SERVER_ERROR:e>=400?g.INVALID_REQUEST:g.UNKNOWN}function $t(t){if(t instanceof R)return t;let e=String(t?.message||t||"").toLowerCase();return t?.name==="AbortError"||e.includes("abort")||e.includes("timeout")||e.includes("timed out")?new R(g.TIMEOUT):e.includes("microphone")||e.includes("permission")||e.includes("notallowed")?new R(g.MICROPHONE):t?.name==="TypeError"||e.includes("failed to fetch")||e.includes("network")||e.includes("load failed")?new R(g.NETWORK):new R(g.UNKNOWN)}function Bo(t,e=null){let n=Number(t?.status)||0,r=t?.headers?.get?.("x-request-id")||t?.headers?.get?.("x-correlation-id")||"",o=e&&typeof e=="object"&&(e.code||e.error_code)||"",i=/^[A-Za-z0-9_.:-]{1,64}$/.test(String(o||""))?String(o):"";return new R(mu(n),{status:n,code:i,requestId:r,stage:"http_response"})}var hu="/v1/widget/runtime-event",_u=16;function v(t={}){let e=JSON.stringify({client_id:l.siteId,site_id:l.siteId,origin:window.location.origin,occurred_at:new Date().toISOString(),session_id:l.sessionId,turn_id:V(t.turn_id,80),request_id:V(t.request_id,80),component:V(t.component||"voice",60),stage:V(t.stage,80),event_type:V(t.event_type||"runtime_event",80),severity:V(t.severity||"info",20),status:V(t.status||"ok",20),message_code:V(t.message_code,80),duration_ms:$o(t.duration_ms),metadata:gu(t.metadata)}),n=new URL(hu,l.apiUrl).toString();fetch(n,{method:"POST",headers:{Accept:"application/json","Content-Type":"application/json"},body:e,keepalive:!0}).catch(()=>{})}function gu(t){if(!t||typeof t!="object"||Array.isArray(t))return{};let e={};for(let[n,r]of Object.entries(t).slice(0,_u)){let o=V(n,60).toLowerCase();!o||yu(o)||(typeof r=="boolean"||r===null?e[o]=r:typeof r=="number"?e[o]=$o(r):typeof r=="string"&&(e[o]=V(r,120)))}return e}function yu(t){return["audio","transcript","response","error","exception","token","secret"].some(e=>t.includes(e))}function V(t,e){return String(t||"").replace(/\s+/g," ").trim().slice(0,e)}function $o(t){let e=Number(t||0);return Number.isFinite(e)?Math.max(0,e):0}var bu=3,Tu="AIHubAdapterRuntime",Au="AIHubAdapter";function Eu(t,e){let n=new URL(k.SHOP_WS,t);return n.protocol=n.protocol==="https:"?"wss:":"ws:",n.searchParams.set("site_id",e),n.searchParams.set("session_id",l.sessionId),n.toString()}function Su(t){return new Promise((e,n)=>{let r=new FileReader;r.onloadend=()=>{let o=String(r.result||"");e(o.includes(",")?o.split(",").pop():o)},r.onerror=()=>n(r.error||new Error("Failed to read audio blob")),r.readAsDataURL(t)})}var cn=class{constructor(){this.queue=[],this.blocked=[],this.playing=!1,this.current=null,this.lastPlaybackStartMs=0,this.installUnlockListeners()}push(e,n=""){e&&(this.queue.push({audioB64:e,fallbackText:n}),this.playNext())}playNext(){if(this.playing||this.queue.length===0)return;this.playing=!0;let e=this.queue.shift(),n=new Audio(Et.DATA_WAV_PREFIX+e.audioB64);n.preload="auto",this.current=n,n.onplay=()=>{this.lastPlaybackStartMs=typeof performance<"u"?performance.now():0},n.onended=()=>{this.current=null,this.playing=!1,this.playNext()},n.onerror=()=>{this.current=null,e.fallbackText&&ot(e.fallbackText),this.playing=!1,this.playNext()},n.play().catch(r=>{if(console.warn("Audio playback failed",r),this.current=null,this.isAutoplayBlocked(r)){e.fallbackText?ot(e.fallbackText):this.blocked.unshift(e),this.playing=!1;return}e.fallbackText&&ot(e.fallbackText),this.playing=!1,this.playNext()})}installUnlockListeners(){if(typeof window>"u")return;let e=()=>{this.retryBlocked(),ne()};window.addEventListener("pointerdown",e,{capture:!0,passive:!0}),window.addEventListener("keydown",e,{capture:!0}),window.addEventListener("touchstart",e,{capture:!0,passive:!0})}retryBlocked(){this.blocked.length&&(this.queue.unshift(...this.blocked.splice(0)),this.playNext())}speakInsteadOfBlocked(e){!e||!this.blocked.length||(this.blocked=[],ot(e))}isAutoplayBlocked(e){let n=`${e?.name||""} ${e?.message||e||""}`.toLowerCase();return n.includes("notallowed")||n.includes("user didn't interact")||n.includes("not allowed")}stop(){if(this.queue=[],this.blocked=[],this.current){try{this.current.pause(),this.current.currentTime=0}catch{}this.current.onended=null,this.current.onerror=null,this.current=null}this.playing=!1,re()}isSpeaking(){return this.playing||this.queue.length>0||zr()}},pe=new cn;function fe(){pe.stop()}function dn(){return pe.isSpeaking()}function pn(t="reset"){jo.reset(t),qo.reset(t)}var un=class{constructor(){this.inFlight=null,this.cancelled=!1}reset(e="reset"){this.cancelled=e==="user_cancel";try{this.inFlight?.abort()}catch{}this.inFlight=null}async sendAudio(e,n,r=[]){let o=Z();v({event_type:"voice_turn_started",stage:"http_request",status:"started",metadata:{transport:"http",audio_type:e?.type||"unknown"}});let i=new FormData;i.append("audio",e,Ou(e)),i.append("site_id",l.siteId),i.append("session_id",l.sessionId),r&&r.length>0&&i.append("conversation_history",JSON.stringify(r));let a=Wo();a&&i.append("page_context",JSON.stringify(a));let s,u=typeof AbortController=="function"?new AbortController:null;this.inFlight=u,this.cancelled=!1;try{s=await fetch(`${l.apiUrl}${k.SHOP}`,{method:Mn.POST,body:i,signal:u?.signal})}catch(b){throw this.cancelled||b?.name==="AbortError"?new R(g.CANCELLED,{stage:"user_cancel"}):$t(b)}if(!s.ok)throw Bo(s,await Ru(s));let f=await s.json();f.transcript&&n.onUserMessage?.(f.transcript);let w=Array.isArray(f.ui_actions)?f.ui_actions:[],T=[];w.length>0&&(T=await sn(w),n.onActionResults?.(T));let I=f.response_text||"",h=Vo(I,w,T,f.success_text||"");h&&n.onAssistantMessage?.(h,w),n.onStatusChange?.(A.READY);let x=h===I;x&&f.audio_b64?Iu(f.audio_b64,f.spoken_text||I):x?ot(f.spoken_text||I):h&&ot(h),n.onComplete?.(f),v({event_type:"voice_turn_completed",stage:"http_response",status:"ok",request_id:wu(s),duration_ms:Z()-o,metadata:{transport:"http",action_count:f.ui_actions?.length||0}})}},ln=class{constructor(){this.ws=null,this.connected=!1,this.connecting=null,this.failed=!1,this.retries=0,this.audioQueue=pe,this.callbacks=null,this.turnText="",this.receivedAudio=!1,this.pendingAudioChunks=[]}async ensureConnected(e=[]){return this.canUseWebSocket()?this.isOpen()?!0:this.connecting?this.connecting:(this.connecting=this.openConnection(e),this.connecting):!1}canUseWebSocket(){return!this.failed&&l.useWebSocket&&"WebSocket"in window}isOpen(){return this.connected&&this.ws?.readyState===WebSocket.OPEN}openConnection(e=[]){return new Promise(n=>{let r=new WebSocket(Eu(l.apiUrl,l.siteId)),o=!1;this.ws=r;let i=(s=null)=>{o||(o=!0,this.markConnectionFailed(n,s,r))},a=window.setTimeout(()=>{i()},Yn);r.onopen=()=>{o||(o=!0,this.handleConnectionOpen(a,e,n))},r.onmessage=s=>{this.handleMessage(s).catch(u=>this.handleTransportError(u))},r.onerror=()=>{if(o){this.failActiveTurn(g.NETWORK);return}i(a)},r.onclose=()=>{if(this.connected=!1,o){this.failActiveTurn(g.NETWORK);return}i(a)}})}markConnectionOpen(){this.connected=!0,this.connecting=null,this.retries=0}handleConnectionOpen(e,n,r){window.clearTimeout(e),this.markConnectionOpen(),this.sendConfig(n),r(!0)}markConnectionFailed(e,n=null,r=null){n&&window.clearTimeout(n),this.connected=!1,this.connecting=null,this.retries+=1,this.retries>=bu&&(this.failed=!0),r&&r.readyState!==WebSocket.CLOSED&&r.close(),e(!1)}sendConfig(e=[]){this.sendJson({type:M.CONFIG,history:e||[],session_id:l.sessionId,page_context:Wo()})}sendJson(e){return!this.ws||this.ws.readyState!==WebSocket.OPEN?!1:(this.ws.send(JSON.stringify(e)),!0)}async sendAudio(e,n,r=[]){if(!await this.ensureConnected(r))return!1;this.callbacks=n,this.turnText="",this.receivedAudio=!1,this.pendingAudioChunks=[],this.sendConfig(r);let i=await Su(e),a=this.beginTurn();return this.turnStartedAt=Z(),v({event_type:"voice_turn_started",stage:"websocket_send",status:"started",metadata:{transport:"websocket",audio_type:e?.type||"unknown"}}),this.sendJson({type:M.AUDIO_CHUNK,data:i,mime_type:e?.type||""})&&this.sendJson({type:M.AUDIO_END,mime_type:e?.type||""})?(await a,!0):(this.settleTurn(),this.callbacks=null,!1)}beginTurn(){return this.settleTurn(),new Promise(e=>{let n=window.setTimeout(()=>{this.failActiveTurn(g.TIMEOUT)},qn);this.activeTurn={resolve:e,timer:n}})}settleTurn(){let e=this.activeTurn;return this.activeTurn=null,e?(window.clearTimeout(e.timer),e.resolve(),!0):!1}failActiveTurn(e){if(!this.activeTurn)return;let n=this.callbacks;if(this.callbacks=null,this.pendingAudioChunks=[],n){let r=new R(e,{stage:"websocket"});n.onStatusChange?.(A.ERROR,r.customerMessage),n.onComplete?.({error:r.category}),v({event_type:"voice_turn_failed",stage:"websocket",severity:"error",status:"failed",message_code:r.code||r.category,duration_ms:Z()-(this.turnStartedAt||Z()),metadata:{transport:"websocket",category:r.category,http_status:r.status}})}this.settleTurn()}async handleMessage(e){let n=this.callbacks;if(!n)return;let r=this.parseMessage(e.data);if(!r){this.completeWithError(n,"Invalid WebSocket message");return}if(!this.handleIncrementalMessage(r,n)){if(r.type===M.DONE){await this.handleDoneMessage(r,n);return}r.type===M.ERROR&&this.completeWithError(n,r.message||"WebSocket error")}}parseMessage(e){try{let n=JSON.parse(e);return n&&typeof n=="object"?n:null}catch{return null}}handleIncrementalMessage(e,n){return e.type===M.TRANSCRIPT?(n.onUserMessage?.(e.text||""),!0):e.type===M.TEXT_CHUNK?(this.turnText+=e.text||"",!0):e.type===M.AUDIO_CHUNK?(this.receivedAudio=!!e.audio_b64||this.receivedAudio,e.audio_b64&&this.pendingAudioChunks.push(e.audio_b64),!0):!1}async handleDoneMessage(e,n){let r=e.response_text||this.turnText;try{let o=Array.isArray(e.ui_actions)?e.ui_actions:[],i=[];o.length>0&&(i=await sn(o),n.onActionResults?.(i));let a=Vo(r,o,i,e.success_text||"");n.onAssistantMessage?.(a,o,{streamed:!0}),n.onStatusChange?.(A.READY);let s=a===r;if(this.receivedAudio&&s)for(let u of this.pendingAudioChunks)this.audioQueue.push(u);else s?ot(e.spoken_text||r):a&&ot(a);n.onComplete?.(e),v({event_type:"voice_turn_completed",stage:"websocket_done",status:"ok",duration_ms:Z()-(this.turnStartedAt||Z()),metadata:{transport:"websocket",action_count:e.ui_actions?.length||0}})}catch(o){this.handleTransportError(o)}finally{this.pendingAudioChunks=[],this.callbacks=null,this.settleTurn()}}completeWithError(e,n){e.onStatusChange?.(A.ERROR,Go(n)),e.onComplete?.({error:n});let r=$t(n);v({event_type:"voice_turn_failed",stage:"websocket_message",severity:"error",status:"failed",message_code:r.code||r.category,duration_ms:Z()-(this.turnStartedAt||Z()),metadata:{transport:"websocket",category:r.category,http_status:r.status}}),this.callbacks=null,this.settleTurn()}handleTransportError(e){console.error("AI Hub WebSocket transport failed",e);let n=this.callbacks;n&&this.completeWithError(n,String(e))}reset(e="reset"){this.callbacks=null,this.turnText="",this.receivedAudio=!1,this.pendingAudioChunks=[],this.settleTurn();try{this.ws?.close()}catch{}this.ws=null,this.connected=!1,this.connecting=null,this.failed=!1,this.retries=0}},qo=new un,jo=new ln;async function zo(t,e,n,r=[]){try{if(l.useWebSocket&&await jo.sendAudio(t,n,r))return;await qo.sendAudio(t,n,r)}catch(o){let i=o instanceof R?o:$t(o);if(Fo(i)){v({event_type:"voice_turn_cancelled",stage:i.stage||"transport",status:"cancelled",metadata:{transport:l.useWebSocket?"websocket_or_http":"http"}}),n.onStatusChange?.(A.READY),n.onComplete?.({cancelled:!0});return}console.error(o),v({event_type:"voice_turn_failed",stage:i.stage||"transport",severity:"error",status:"failed",request_id:i.requestId,message_code:i.code||i.category,metadata:{transport:l.useWebSocket?"websocket_or_http":"http",category:i.category,http_status:i.status}}),n.onStatusChange?.(A.ERROR,Go(o)),n.onComplete?.({error:String(o)})}}function wu(t){return t?.headers?.get?.("x-request-id")||t?.headers?.get?.("x-correlation-id")||""}function Z(){return typeof performance<"u"?performance.now():Date.now()}function Iu(t,e=""){pe.push(t,e)}function Ou(t){let e=String(t?.type||"").toLowerCase();return e.includes("mp4")?"audio.mp4":e.includes("ogg")?"audio.ogg":e.includes("wav")?"audio.wav":Et.WEBM_FILENAME}var Cu=/\b(opened|opening|taking you|took you|navigat|sorted|sorting|filtered|filtering|showing|shown|displayed|added to (?:your )?cart|here (?:it |they )?(?:is|are))\b/i,xu=/\b(?:i(?:'ll| will)\s+try\s+to|i'?m\s+(?:going\s+to|about\s+to)|let me)\b/i,Yo="I could not complete that on the page. The site may not have responded - please try again, or do it manually.";function Vo(t,e,n,r=""){let o=String(t||"");if(!o||!Array.isArray(e)||e.length===0)return o;let i=String(r||"");if(!(!!i||Cu.test(o)||xu.test(o)))return o;let s=Array.isArray(n)?n:[];return s.length!==e.length||!s.every(f=>f?.status==="succeeded"&&f?.verified!==!1)?Yo:i||o}async function Ru(t){try{return await t.json()}catch{return null}}function Go(t){if(t instanceof R)return t.customerMessage;let e=String(t?.message||t||"").toLowerCase();return e.includes("quota")?"Quota reached":e.includes("transcription")||e.includes("speech")?"Voice unavailable":$t(t).customerMessage}function ot(t){return t?ut(String(t).slice(0,700)):!1}function Wo(){let t=window[Tu],e=window[Au];try{if(typeof t?.getContext=="function")return t.getContext();if(typeof e?.getContext=="function")return e.getContext()}catch(n){console.warn("[AI Hub Widget] Page context collection failed:",n)}return Nu()}function Nu(){try{return{title:document.title||"",url:window.location.href,path:window.location.pathname,...se()}}catch(t){return console.warn("[AI Hub Widget] Local page state collection failed:",t),null}}var vu=4,Pu=40,Lu=24,Du=80,Uu=120,fn=6,Xo=40,ku=600,Mu=6,Hu=12,Ko=/\[PRODUCT_IDS:\s*([^\]]+)\]/g,Fu="mayabot_conversation:";function Jo(t){return`${Fu}${t||"default"}`}function Bu(t){try{let e=window.sessionStorage.getItem(Jo(t)),n=e?JSON.parse(e):null;return Array.isArray(n)?n.filter(r=>r&&typeof r.role=="string"&&typeof r.content=="string").slice(-Xo):[]}catch{return[]}}function Qo(t,e){try{window.sessionStorage.setItem(Jo(t),JSON.stringify(e))}catch{}}function Zo(t=""){let e=Bu(t);function n(r,o){let i=String(o||"").trim();i&&(e.push({role:r,content:i}),e.length>Xo&&e.shift(),Qo(t,e))}return{history:e,historyForRequest(){if(e.length<=fn)return e.map(a=>({...a}));let r=e.slice(0,e.length-fn),o=e.slice(e.length-fn).map(a=>({...a})),i=$u(r);return i?[i,...o]:o},clear(){e.length=0,Qo(t,e)},rememberUserMessage(r){n("user",r)},rememberAssistantMessage(r,o){n("assistant",Yu(r,o))},rememberActionResults(r){let o=ju(r);o&&n("assistant",o)}}}function $u(t){let e=[],n=[];for(let o of t){o.role==="user"&&e.length<Mu&&e.push(o.content.replace(/\s+/g," ").trim().slice(0,80));let i;for(Ko.lastIndex=0;(i=Ko.exec(o.content))!==null;)mn(n,i[1].split(",").map(a=>a.trim()))}let r=[];return e.length&&r.push(`Earlier the customer asked: ${e.join("; ")}.`),n.length&&r.push(`Products discussed: ${n.slice(0,Hu).join(", ")}.`),r.length?{role:"system",content:`[CONVERSATION_SUMMARY] ${r.join(" ")}`.slice(0,ku)}:null}function Yu(t,e){let n=qu(e);return n.length?`${t} [PRODUCT_IDS: ${n.join(",")}]`:t}function qu(t){let e=[];for(let n of t||[]){let r=n.params||{};mn(e,r[d.PRODUCT_IDS]),mn(e,[r[d.PRODUCT_ID]])}return e}function mn(t,e){for(let n of Array.isArray(e)?e:[])n&&!t.includes(n)&&t.push(n)}function ju(t){let e=(Array.isArray(t)?t:[]).map(zu).filter(Boolean).slice(0,vu);return e.length?`[BROWSER_ACTION_RESULTS: ${e.join(" | ")}]`:""}function zu(t){if(!t||typeof t!="object"||!t.action)return"";let e=[me(t.action,Pu),`status=${me(t.status,Lu)||"unknown"}`],n=Gu(t.final_url);return n&&e.push(`final_path=${me(n,Uu)}`),t.reason&&e.push(`reason=${me(t.reason,Du)}`),Vu(e,t.evidence),e.join(" ")}function Vu(t,e={}){e.rendered_product_count!==void 0&&t.push(`rendered_products=${Number(e.rendered_product_count||0)}`),e.rendered_entity_count!==void 0&&t.push(`rendered_records=${Number(e.rendered_entity_count||0)}`)}function me(t,e){return String(t||"").replace(/\s+/g," ").trim().slice(0,e)}function Gu(t){try{let e=new URL(String(t||""),window.location.href);return`${e.pathname}${e.search}${e.hash}`}catch{return""}}var ti="aihub:session-reset",he="AIHub",Wu=Object.freeze(["mayabot:","aihub:"]);function Ku(t){let e=[];for(let n=0;n<t.length;n+=1){let r=t.key(n);r&&Wu.some(o=>r.startsWith(o))&&e.push(r)}return e}function ei(t){if(!t)return[];try{let e=Ku(t);for(let n of e)t.removeItem(n);return e}catch{return[]}}function Qu(){let t=[];try{t.push(...ei(window.sessionStorage))}catch{}try{t.push(...ei(window.localStorage))}catch{}return t}function ni({cancelRecording:t,stopPlayback:e,resetTransport:n,conversationMemory:r,clearOverlays:o,rotateSessionId:i}={}){return function(){let s={stopped_recording:!1,stopped_audio:!1,cleared_keys:[],session_id:""};return s.stopped_recording=bt(t),s.stopped_audio=bt(e),bt(n),bt(()=>r?.clear?.()),bt(o),s.cleared_keys=Qu(),s.session_id=String(bt(i)||""),s}}function bt(t){if(typeof t!="function")return!1;try{let e=t();return e===void 0?!0:e}catch(e){return console.warn("[AI Hub Widget] Session reset step failed:",e),!1}}function ri(t){let e=window[he]||{};e.resetSession=t,window[he]=e;let n=()=>t();return window.addEventListener(ti,n),()=>{window.removeEventListener(ti,n),window[he]?.resetSession===t&&delete window[he].resetSession}}var oi=null;function hn(t){oi||(ii(t),oi=window.setInterval(()=>ii(t),$n))}async function ii({boot:t,shutdownWidget:e}){try{if(await Xu()){t();return}e()}catch{t()}}async function Xu(){let t=new URL(k.WIDGET_STATUS,l.apiUrl);t.searchParams.set("site_id",l.siteId);let e=await fetch(t.toString(),{cache:"no-store",headers:{Accept:"application/json"}});return e.ok?(await e.json()).enabled!==!1:!0}window.__mayabot_identifier="voice-orb";var _n=null,gn=null;function ai(){if(window.__mayabotBooted||document.getElementById("mayabot-widget"))return;window.__mayabotBooted=!0,On();let t=Un(),e=null,n=null,r=!1;function o(m=Hn){e&&window.clearTimeout(e),e=window.setTimeout(()=>{t.chat.classList.remove("visible"),e=null},m)}let i=40;function a(){let m=t.msgs.children;for(;m.length>i;)t.msgs.removeChild(m[0])}function s(m,G=""){r=m===A.RECORDING,An(li(m)),t.status.className="",m===A.RECORDING?(e&&(window.clearTimeout(e),e=null),a(),t.chat.classList.add("visible"),t.msgs.scrollTop=t.msgs.scrollHeight,t.status.innerText="Listening...",t.status.classList.add("listening")):m===A.PROCESSING?(t.chat.classList.add("visible"),t.status.innerText="Analyzing...",t.status.classList.add("processing")):m===A.READY?(t.status.innerText="Ready",t.status.classList.add("ready")):m===A.ERROR&&(t.status.innerText=G||"Try again",t.status.classList.add("error"))}let u=Zo(`${l.siteId}:${l.sessionId}`);f();function f(){for(let m of u.history){if(m.role==="user"){at(t,m.content,"user");continue}if(m.role!=="assistant")continue;let G=w(m.content);G&&at(t,G,"ai")}u.history.length&&(t.msgs.scrollTop=t.msgs.scrollHeight)}function w(m){return String(m||"").replace(/\s*\[PRODUCT_IDS:[^\]]*\]/g,"").replace(/\s*\[BROWSER_ACTION_RESULTS:[^\]]*\]/g,"").trim()}let T=null,I="",h=!1,x=0;async function b(m){if(h)return;h=!0;let G=++x,it=()=>G===x;T=null,I="";try{await zo(m,t,{onUserMessage:P=>{it()&&(at(t,P,"user"),u.rememberUserMessage(P))},onAssistantChunk:(P,Tt)=>{it()&&(I=Tt,T||(T=at(t,"","ai")),Te(t,T,I))},onAssistantMessage:(P,Tt,pi={})=>{it()&&(pi.streamed&&T?Te(t,T,P):at(t,P,"ai"),u.rememberAssistantMessage(P,Tt),T=null,I="")},onActionResults:P=>{it()&&u.rememberActionResults(P)},onStatusChange:(P,Tt)=>{it()&&s(P,Tt)},onComplete:()=>{it()&&o()}},u.historyForRequest())}finally{it()&&(h=!1),T=null,I=""}}function yn(){x+=1,pn("user_cancel"),fe(),h=!1,T=null,I="",v({event_type:"voice_turn_cancelled",stage:"orb_gesture",status:"cancelled"}),s(A.READY)}let Yt=jn(b,s);_n=Yt;function bn(){return h||dn()}function ui(){if(bn()){yn();return}Yt.toggle()}let Tn={idle:{label:"Maya voice assistant. Click, press Enter, or press Space to talk.",title:"Click to talk"},recording:{label:"Maya is listening. Click once to send, or press Escape to cancel.",title:"Click once to send - Escape to cancel"},processing:{label:"Maya is working on your request. Click or press Escape to stop.",title:"Click to stop"},speaking:{label:"Maya is speaking. Click to stop, or press Escape to stop.",title:"Click to stop Maya"}};function li(m){return m===A.RECORDING?"recording":m===A.PROCESSING?"processing":dn()?"speaking":"idle"}function An(m){let G=Tn[m]||Tn.idle;t.btn.setAttribute("aria-label",G.label),t.btn.setAttribute("title",G.title),t.btn.setAttribute("data-orb-state",m),t.btn.classList.toggle("recording",m==="recording"),t.btn.classList.toggle("speaking",m==="speaking")}An("idle"),t.btn.addEventListener("click",m=>{m.detail>1||ui()});let En=m=>{if(m.key==="Escape"){if(r){Yt.cancel(),v({event_type:"voice_recording_cancelled",stage:"keyboard_escape",status:"cancelled"}),s(A.READY);return}bn()&&yn()}};document.addEventListener("keydown",En);let Sn=m=>{t.btn.contains(m.target)||ne()};document.addEventListener("pointerdown",Sn,{capture:!0});let di=ri(ni({cancelRecording:()=>Yt.cancel(),stopPlayback:fe,resetTransport:pn,conversationMemory:u,clearOverlays:()=>{t.msgs.innerHTML="",t.chat.classList.remove("visible"),document.getElementById("mayabot-product-panel")?.remove()},rotateSessionId:()=>l.rotateSessionId()}));gn=()=>{document.removeEventListener("keydown",En),document.removeEventListener("pointerdown",Sn,{capture:!0}),di(),e&&window.clearTimeout(e),e=null,n&&window.clearTimeout(n),n=null,gn=null},Ju()&&(Zu(),n=window.setTimeout(()=>{if(u.history.length>0)return;let m=`Welcome to ${l.brandName}. How can I help you today?`;at(t,m,"ai"),s(A.READY),o(Bn),ut(m)},Fn))}function si(){_n?.cancel(),_n=null,gn?.(),fe(),window.__mayabotBooted=!1,document.getElementById("mayabot-widget")?.remove(),document.getElementById("mayabot-product-panel")?.remove()}function Ju(){if(!l.autoGreet||!tl())return!1;try{return window.sessionStorage.getItem(ci())!=="1"}catch{return!window.__mayabotAutoGreeted}}function Zu(){window.__mayabotAutoGreeted=!0;try{window.sessionStorage.setItem(ci(),"1")}catch{}}function ci(){return`mayabot:auto-greeted:${l.siteId}`}function tl(){let t=window.location.pathname.replace(/\/+$/,"")||"/";return t==="/"||t.endsWith("/index.html")}document.readyState==="loading"?document.addEventListener("DOMContentLoaded",()=>hn({boot:ai,shutdownWidget:si})):hn({boot:ai,shutdownWidget:si});})();
