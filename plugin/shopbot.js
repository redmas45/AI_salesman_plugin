(()=>{function b(){let o=document.createElement("style");o.textContent=`
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
  `,document.head.appendChild(o)}function f(){let o=document.createElement("div");return o.id="shopbot-widget",o.innerHTML=`
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
  `,document.body.appendChild(o),{btn:document.getElementById("shopbot-btn"),chat:document.getElementById("shopbot-chat"),msgs:document.getElementById("shopbot-msgs"),status:document.getElementById("shopbot-status")}}function m(o,t,e){o.chat.classList.add("visible");let s=document.createElement("div");s.className=`shopbot-msg ${e}`,s.innerText=t,o.msgs.appendChild(s),o.msgs.scrollTop=o.msgs.scrollHeight}function x(o,t){let e=null,s=[],n=!1;async function p(){try{let i=await navigator.mediaDevices.getUserMedia({audio:!0});e=new MediaRecorder(i),s=[],e.ondataavailable=d=>{d.data.size>0&&s.push(d.data)},e.onstop=async()=>{let d=new Blob(s,{type:"audio/webm"});i.getTracks().forEach(a=>a.stop()),await o(d)},e.start(),n=!0,t("recording")}catch(i){console.error("Microphone access denied",i),t("error")}}function r(){e&&e.state!=="inactive"&&e.stop(),n=!1,t("processing")}function u(){n?r():p()}return{toggle:u}}var w=document.currentScript,y="__AI_PUBLIC_API_URL__",T=y.startsWith("__AI_")?window.location.origin:y,g={siteId:w?.getAttribute("data-site-id")||"__AI_DEFAULT_SITE_ID__",apiUrl:w?.getAttribute("data-api-url")||T};function C(o){let t=String(o||"").trim();if(!t||/^https?:\/\//i.test(t))return"";if(t==="home"||t==="/")return"/";let e=t.replace(/^\/+|\/+$/g,"");return e?`/${e}/`:"/"}function _(o){o.forEach(t=>{console.log("ShopBot executing action:",t);let e=t.params||t.parameters||{};if(t.params=e,t.parameters=e,window.ShopBotConfig){if(t.action==="ADD_TO_CART"&&window.ShopBotConfig.onAddToCart){window.ShopBotConfig.onAddToCart(t.parameters?.product_id,t.parameters?.quantity);return}if(t.action==="FILTER_PRODUCTS"&&window.ShopBotConfig.onFilter){window.ShopBotConfig.onFilter(t.parameters);return}}if(window.ShopCart){if(t.action==="ADD_TO_CART"){window.ShopCart.addItem(t.parameters?.product_id,t.parameters?.quantity||1);return}if(t.action==="CLEAR_CART"){window.ShopCart.clear();return}if(t.action==="NAVIGATE_TO"&&(t.parameters?.page==="cart"||t.parameters?.page==="/cart")){window.ShopCart.open();return}if(t.action==="CHECKOUT"&&window.ShopCart.checkout){window.ShopCart.checkout(t.parameters);return}}if(t.action==="NAVIGATE_TO"){let s=C(t.parameters?.page);s&&(window.location.href=s)}window.dispatchEvent(new CustomEvent("shopbot:action",{detail:t}))})}async function v(o,t,e,s=[]){let n=new FormData;n.append("audio",o,"audio.webm"),n.append("site_id",g.siteId),s&&s.length>0&&n.append("conversation_history",JSON.stringify(s));try{let p=await fetch(`${g.apiUrl}/v1/shop`,{method:"POST",body:n});if(!p.ok)throw new Error("API Error");let r=await p.json();r.transcript&&e.onMessage(r.transcript,"user"),r.response_text&&e.onMessage(r.response_text,"ai",r.ui_actions||[]),e.onStatusChange("ready"),r.audio_b64&&k(r.audio_b64),r.ui_actions&&r.ui_actions.length>0&&_(r.ui_actions),e.onComplete?.(r)}catch(p){console.error(p),e.onStatusChange("error"),e.onComplete?.({error:String(p)})}}function k(o){let t="data:audio/wav;base64,"+o;new Audio(t).play().catch(s=>console.error("Audio playback failed",s))}window.__shopbot_identifier="voice-orb";function A(){if(window.__shopbotBooted||document.getElementById("shopbot-widget"))return;window.__shopbotBooted=!0,b();let o=f(),t=null;function e(i=2400){t&&window.clearTimeout(t),t=window.setTimeout(()=>{o.msgs.innerHTML="",o.chat.classList.remove("visible"),t=null},i)}function s(i){o.status.className="",i==="recording"?(t&&(window.clearTimeout(t),t=null),o.msgs.innerHTML="",o.btn.classList.add("recording"),o.chat.classList.add("visible"),o.status.innerText="Listening...",o.status.classList.add("listening")):i==="processing"?(o.btn.classList.remove("recording"),o.chat.classList.add("visible"),o.status.innerText="Analyzing...",o.status.classList.add("processing")):i==="ready"?(o.status.innerText="Ready",o.status.classList.add("ready")):i==="error"&&(o.status.innerText="Error",o.status.classList.add("error"),o.btn.classList.remove("recording"))}let n=[];function p(i,d){let a=[];for(let h of d||[]){let c=h.params||{};if(c.product_ids&&Array.isArray(c.product_ids))for(let l of c.product_ids)a.includes(l)||a.push(l);c.product_id&&!a.includes(c.product_id)&&a.push(c.product_id)}return a.length>0?i+` [PRODUCT_IDS: ${a.join(",")}]`:i}async function r(i){await v(i,o,{onMessage:(d,a,h)=>{m(o,d,a);let c=a==="ai"?"assistant":a,l=c==="assistant"?p(d,h):d;n.push({role:c,content:l}),n.length>12&&n.shift()},onStatusChange:s,onComplete:()=>e()},n)}let u=x(r,s);o.btn.addEventListener("click",()=>{u.toggle()})}document.readyState==="loading"?document.addEventListener("DOMContentLoaded",A):A();})();
