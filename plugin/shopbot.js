(()=>{function h(){let t=document.createElement("style");t.textContent=`
    #shopbot-widget {
      position: fixed;
      bottom: 20px;
      left: 50%;
      transform: translateX(-50%);
      z-index: 999999;
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
  `,document.head.appendChild(t)}function g(){let t=document.createElement("div");return t.id="shopbot-widget",t.innerHTML=`
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
  `,document.body.appendChild(t),{btn:document.getElementById("shopbot-btn"),chat:document.getElementById("shopbot-chat"),msgs:document.getElementById("shopbot-msgs"),status:document.getElementById("shopbot-status")}}function b(t,o,e){t.chat.classList.add("visible");let i=document.createElement("div");i.className=`shopbot-msg ${e}`,i.innerText=o,t.msgs.appendChild(i),t.msgs.scrollTop=t.msgs.scrollHeight}function f(t,o){let e=null,i=[],n=!1;async function d(){try{let r=await navigator.mediaDevices.getUserMedia({audio:!0});e=new MediaRecorder(r),i=[],e.ondataavailable=p=>{p.data.size>0&&i.push(p.data)},e.onstop=async()=>{let p=new Blob(i,{type:"audio/webm"});r.getTracks().forEach(a=>a.stop()),await t(p)},e.start(),n=!0,o("recording")}catch(r){console.error("Microphone access denied",r),o("error")}}function s(){e&&e.state!=="inactive"&&e.stop(),n=!1,o("processing")}function c(){n?s():d()}return{toggle:c}}var m=document.currentScript,x="__AI_PUBLIC_API_URL__",v=x.startsWith("__AI_")?window.location.origin:x,u={siteId:m?.getAttribute("data-site-id")||"__AI_DEFAULT_SITE_ID__",apiUrl:m?.getAttribute("data-api-url")||v};function w(t){t.forEach(o=>{console.log("ShopBot executing action:",o);let e=o.params||o.parameters||{};if(o.params=e,o.parameters=e,window.ShopBotConfig){if(o.action==="ADD_TO_CART"&&window.ShopBotConfig.onAddToCart){window.ShopBotConfig.onAddToCart(o.parameters?.product_id,o.parameters?.quantity);return}if(o.action==="FILTER_PRODUCTS"&&window.ShopBotConfig.onFilter){window.ShopBotConfig.onFilter(o.parameters);return}}if(window.ShopCart){if(o.action==="ADD_TO_CART"){window.ShopCart.addItem(o.parameters?.product_id,o.parameters?.quantity||1);return}if(o.action==="CLEAR_CART"){window.ShopCart.clear();return}if(o.action==="NAVIGATE_TO"&&(o.parameters?.page==="cart"||o.parameters?.page==="/cart")){window.ShopCart.open();return}}o.action==="NAVIGATE_TO"&&o.parameters?.page&&(window.location.href=o.parameters.page),window.dispatchEvent(new CustomEvent("shopbot:action",{detail:o}))})}async function y(t,o,e,i=[]){let n=new FormData;n.append("audio",t,"audio.webm"),n.append("site_id",u.siteId),i&&i.length>0&&n.append("conversation_history",JSON.stringify(i));try{let d=await fetch(`${u.apiUrl}/v1/shop`,{method:"POST",body:n});if(!d.ok)throw new Error("API Error");let s=await d.json();s.transcript&&e.onMessage(s.transcript,"user"),s.response_text&&e.onMessage(s.response_text,"ai",s.ui_actions||[]),e.onStatusChange("ready"),s.audio_b64&&A(s.audio_b64),s.ui_actions&&s.ui_actions.length>0&&w(s.ui_actions)}catch(d){console.error(d),e.onStatusChange("error")}}function A(t){let o="data:audio/wav;base64,"+t;new Audio(o).play().catch(i=>console.error("Audio playback failed",i))}window.__shopbot_identifier="voice-orb";function _(){if(window.__shopbotBooted||document.getElementById("shopbot-widget"))return;window.__shopbotBooted=!0,h();let t=g();function o(s){t.status.className="",s==="recording"?(t.btn.classList.add("recording"),t.chat.classList.add("visible"),t.status.innerText="Listening...",t.status.classList.add("listening")):s==="processing"?(t.btn.classList.remove("recording"),t.status.innerText="Processing...",t.status.classList.add("processing")):s==="ready"?(t.status.innerText="Ready",t.status.classList.add("ready")):s==="error"&&(t.status.innerText="Error",t.status.classList.add("error"),t.btn.classList.remove("recording"))}let e=[];function i(s,c){let r=[];for(let p of c||[]){let a=p.params||{};if(a.product_ids&&Array.isArray(a.product_ids))for(let l of a.product_ids)r.includes(l)||r.push(l);a.product_id&&!r.includes(a.product_id)&&r.push(a.product_id)}return r.length>0?s+` [PRODUCT_IDS: ${r.join(",")}]`:s}async function n(s){await y(s,t,{onMessage:(c,r,p)=>{b(t,c,r);let a=r==="ai"?"assistant":r,l=a==="assistant"?i(c,p):c;e.push({role:a,content:l}),e.length>12&&e.shift()},onStatusChange:o},e)}let d=f(n,o);t.btn.addEventListener("click",()=>{d.toggle()})}document.readyState==="loading"?document.addEventListener("DOMContentLoaded",_):_();})();
