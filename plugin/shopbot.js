(()=>{function g(){let t=document.createElement("style");t.textContent=`
    #shopbot-widget { position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); z-index: 999999; font-family: system-ui, -apple-system, sans-serif; }
    #shopbot-btn {
      width: 60px; height: 60px; border-radius: 50%;
      border: 1px solid rgba(255, 255, 255, 0.2);
      background: rgba(10, 10, 10, 0.85);
      backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3), inset 0 0 15px rgba(255, 255, 255, 0.1);
      color: white; display: flex; align-items: center; justify-content: center;
      cursor: pointer; transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
      outline: none;
    }
    #shopbot-btn:hover {
      transform: scale(1.05) translateY(-3px);
      box-shadow: 0 15px 40px rgba(0,0,0,0.4), 0 0 20px rgba(139,92,246,0.4), inset 0 0 15px rgba(255,255,255,0.2);
      border-color: rgba(255,255,255,0.4);
    }
    #shopbot-btn.recording {
      background: rgba(239, 68, 68, 0.85);
      border-color: rgba(255, 255, 255, 0.4);
      animation: pulse 1.5s infinite cubic-bezier(0.66, 0, 0, 1);
    }
    #shopbot-chat {
      position: absolute; bottom: 80px; left: 50%; transform: translateX(-50%); width: 320px;
      background: rgba(10, 10, 10, 0.85);
      backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
      border: 1px solid rgba(255, 255, 255, 0.15);
      border-radius: 16px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.3), inset 0 0 15px rgba(255,255,255,0.05);
      padding: 16px; display: none; flex-direction: column; gap: 12px;
      color: white;
    }
    #shopbot-chat.visible { display: flex; }
    .shopbot-msg { padding: 12px 16px; border-radius: 12px; font-size: 14px; line-height: 1.5; }
    .shopbot-msg.user { background: rgba(255, 255, 255, 0.1); color: white; align-self: flex-end; border-bottom-right-radius: 4px; border: 1px solid rgba(255, 255, 255, 0.1); }
    .shopbot-msg.ai { background: rgba(139, 92, 246, 0.8); color: white; align-self: flex-start; border-bottom-left-radius: 4px; border: 1px solid rgba(255, 255, 255, 0.2); }
    #shopbot-status {
      font-size: 14px;
      color: rgba(255, 255, 255, 0.7);
      text-align: center;
      margin-top: 6px;
      transition: all 0.3s ease;
      font-weight: 500;
    }
    #shopbot-status.listening {
      font-size: 18px;
      color: #f87171; /* Brighter red */
      font-weight: 600;
      text-shadow: 0 0 8px rgba(239, 68, 68, 0.5);
      animation: textPulse 1.5s infinite ease-in-out;
    }
    #shopbot-status.processing {
      font-size: 16px;
      color: #c084fc; /* Purple */
      font-weight: 600;
      animation: textPulse 1.5s infinite ease-in-out;
    }
    #shopbot-status.ready {
      color: #4ade80; /* Green */
    }
    #shopbot-status.error {
      color: #f87171; /* Red */
      font-weight: 600;
    }
    @keyframes textPulse {
      0%, 100% { opacity: 0.7; transform: scale(0.98); }
      50% { opacity: 1; transform: scale(1.02); }
    }
    @keyframes pulse {
      to { box-shadow: 0 0 0 20px rgba(239, 68, 68, 0); }
    }
  `,document.head.appendChild(t)}function b(){let t=document.createElement("div");return t.id="shopbot-widget",t.innerHTML=`
    <div id="shopbot-chat">
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
  `,document.body.appendChild(t),{btn:document.getElementById("shopbot-btn"),chat:document.getElementById("shopbot-chat"),msgs:document.getElementById("shopbot-msgs"),status:document.getElementById("shopbot-status")}}function f(t,e,o){t.chat.classList.add("visible");let s=document.createElement("div");s.className=`shopbot-msg ${o}`,s.innerText=e,t.msgs.appendChild(s),t.msgs.scrollTop=t.msgs.scrollHeight}function h(t,e){let o=null,s=[],n=!1;async function d(){try{let i=await navigator.mediaDevices.getUserMedia({audio:!0});o=new MediaRecorder(i),s=[],o.ondataavailable=p=>{p.data.size>0&&s.push(p.data)},o.onstop=async()=>{let p=new Blob(s,{type:"audio/webm"});i.getTracks().forEach(a=>a.stop()),await t(p)},o.start(),n=!0,e("recording")}catch(i){console.error("Microphone access denied",i),e("error")}}function r(){o&&o.state!=="inactive"&&o.stop(),n=!1,e("processing")}function c(){n?r():d()}return{toggle:c}}var m=document.currentScript,u={siteId:m?.getAttribute("data-site-id")||"site_1",apiUrl:m?.getAttribute("data-api-url")||"http://localhost:8000"};function x(t){t.forEach(e=>{console.log("ShopBot executing action:",e);let o=e.params||e.parameters||{};if(e.params=o,e.parameters=o,window.ShopBotConfig){if(e.action==="ADD_TO_CART"&&window.ShopBotConfig.onAddToCart){window.ShopBotConfig.onAddToCart(e.parameters?.product_id,e.parameters?.quantity);return}if(e.action==="FILTER_PRODUCTS"&&window.ShopBotConfig.onFilter){window.ShopBotConfig.onFilter(e.parameters);return}}if(window.ShopCart){if(e.action==="ADD_TO_CART"){window.ShopCart.addItem(e.parameters?.product_id,e.parameters?.quantity||1);return}if(e.action==="CLEAR_CART"){window.ShopCart.clear();return}if(e.action==="NAVIGATE_TO"&&(e.parameters?.page==="cart"||e.parameters?.page==="/cart")){window.ShopCart.open();return}}e.action==="NAVIGATE_TO"&&e.parameters?.page&&(window.location.href=e.parameters.page),window.dispatchEvent(new CustomEvent("shopbot:action",{detail:e}))})}async function w(t,e,o,s=[]){let n=new FormData;n.append("audio",t,"audio.webm"),n.append("site_id",u.siteId),s&&s.length>0&&n.append("conversation_history",JSON.stringify(s));try{let d=await fetch(`${u.apiUrl}/v1/shop`,{method:"POST",body:n});if(!d.ok)throw new Error("API Error");let r=await d.json();r.transcript&&o.onMessage(r.transcript,"user"),r.response_text&&o.onMessage(r.response_text,"ai",r.ui_actions||[]),o.onStatusChange("ready"),r.audio_b64&&v(r.audio_b64),r.ui_actions&&r.ui_actions.length>0&&x(r.ui_actions)}catch(d){console.error(d),o.onStatusChange("error")}}function v(t){let e="data:audio/wav;base64,"+t;new Audio(e).play().catch(s=>console.error("Audio playback failed",s))}window.__shopbot_identifier="voice-orb";function y(){g();let t=b();function e(r){t.status.className="",r==="recording"?(t.btn.classList.add("recording"),t.chat.classList.add("visible"),t.status.innerText="Listening...",t.status.classList.add("listening")):r==="processing"?(t.btn.classList.remove("recording"),t.status.innerText="Processing...",t.status.classList.add("processing")):r==="ready"?(t.status.innerText="Ready",t.status.classList.add("ready")):r==="error"&&(t.status.innerText="Error",t.status.classList.add("error"),t.btn.classList.remove("recording"))}let o=[];function s(r,c){let i=[];for(let p of c||[]){let a=p.params||{};if(a.product_ids&&Array.isArray(a.product_ids))for(let l of a.product_ids)i.includes(l)||i.push(l);a.product_id&&!i.includes(a.product_id)&&i.push(a.product_id)}return i.length>0?r+` [PRODUCT_IDS: ${i.join(",")}]`:r}async function n(r){await w(r,t,{onMessage:(c,i,p)=>{f(t,c,i);let a=i==="ai"?"assistant":i,l=a==="assistant"?s(c,p):c;o.push({role:a,content:l}),o.length>12&&o.shift()},onStatusChange:e},o)}let d=h(n,e);t.btn.addEventListener("click",()=>{d.toggle()})}document.readyState==="loading"?document.addEventListener("DOMContentLoaded",y):y();})();
