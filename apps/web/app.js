let city = "Mumbai", language = "en", ws;
const chatHistory = [];
const $ = (id) => document.getElementById(id);
function escapeHtml(s){return String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}

async function loadWeather(){
  city=$('city').value;
  $('sideCity').textContent=city;
  try{
    const r=await fetch(`/v1/weather?city=${encodeURIComponent(city)}`); const d=await r.json();
    const c=d.current||{};
    $('currentCard').innerHTML=`<div class="city-line"><span>⌖ ${escapeHtml(d.city)}</span><span>☀️ Clear</span></div><div class="weather-temp">${c.temperature_2m ?? '--'}°C</div><div class="weather-meta">Humidity ${c.relative_humidity_2m ?? '--'}% · Wind ${c.wind_speed_10m ?? '--'} km/h</div><div class="weather-divider"></div><div class="provenance">◉ Source: ${escapeHtml(d.provenance?.source||'Weather API')} · ${escapeHtml(d.provenance?.freshness||'live')}</div>`;
  }catch(e){$('currentCard').innerHTML='<div class="loading">Weather service unavailable. Try again.</div>';}
}

async function send(){
  const input=$('message'), text=input.value.trim(); if(!text)return;
  $('messages').insertAdjacentHTML('beforeend',`<div class="bubble user">${escapeHtml(text)}</div>`);
  input.value="";
  const bubble=document.createElement('div'); bubble.className='bubble bot'; bubble.innerHTML='<span>Thinking…</span>'; $('messages').appendChild(bubble); $('messages').scrollTop=$('messages').scrollHeight;
  const historyForApi=chatHistory.slice(-10);
  try{
    const res=await fetch('/v1/chat/stream',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text,city,language,latitude:0,longitude:0,history:historyForApi})});
    if(!res.ok) throw new Error(`HTTP ${res.status}`);
    const reader=res.body.getReader(),decoder=new TextDecoder(); let answer='',meta=null;
    let buffer='';
    while(true){
      const {done,value}=await reader.read();
      if(done)break;
      buffer += decoder.decode(value,{stream:true});
      const events=buffer.split('\n\n'); buffer=events.pop()||'';
      for(const event of events){
        const line=event.split('\n').find(x=>x.startsWith('data:'));
        if(!line)continue;
        const payload=line.slice(5).trim();
        if(payload==='[DONE]')continue;
        try{
          const obj=JSON.parse(payload);
          if(obj.token){answer+=obj.token;bubble.innerHTML=escapeHtml(answer);$('messages').scrollTop=$('messages').scrollHeight;}
          if(obj.provenance || obj.model) meta=obj;
        }catch{}
      }
    }
    // Some servers send the metadata as a separate SSE event after [DONE].
    if(buffer.trim()){
      const line=buffer.split('\n').find(x=>x.startsWith('data:'));
      if(line){try{const obj=JSON.parse(line.slice(5).trim());if(obj.provenance||obj.model)meta=obj;}catch{}}
    }
    chatHistory.push({role:'user',content:text});
    chatHistory.push({role:'assistant',content:answer});
    if(chatHistory.length>12) chatHistory.splice(0,chatHistory.length-12);
    const source=meta?.provenance?.source||'Weather API';
    const model=meta?.model||'WeatherGPT';
    bubble.innerHTML=escapeHtml(answer)+`<div class="provenance">Source: ${escapeHtml(source)} · AI: ${escapeHtml(model)} · ${escapeHtml(meta?.provenance?.freshness||'live')}</div>`;
  }catch(e){
    bubble.innerHTML='<b>Unable to reach WeatherGPT.</b><div class="provenance">Check that the FastAPI server is running on port 8000.</div>';
  }
  $('messages').scrollTop=$('messages').scrollHeight;
}

async function loadAIStatus(){
  try{
    const d=await fetch('/v1/ai/status').then(r=>r.json());
    const el=$('aiStatus');
    if(!el)return;
    if(d.configured){el.textContent=`✦ AI Assistant Online · ${d.model}`;el.classList.add('online');}
    else{el.textContent='✦ Gemini AI · Real-time conversational weather intelligence';el.classList.add('demo');}
  }catch{}
}

async function advisory(){
  const sector=$('sector').value;
  const r=await fetch('/v1/advisory',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sector,city,latitude:19.0760,longitude:72.8777})});
  const d=await r.json();
  $('calendar').innerHTML=d.calendar.map(x=>`<div class="glass-soft day"><b>${escapeHtml(x.date)}</b><div class="rain">${x.rain_probability}% rain risk</div><p>${escapeHtml(x.action)}</p></div>`).join('');
}
async function trust(){
  const d=await fetch('/v1/trust').then(r=>r.json());
  $('metrics').innerHTML=[['Gold-set accuracy',d.gold_set.accuracy_percent+'%'],['TTFT',d.latency.ttft_seconds+'s'],['p95 latency',d.latency.p95_seconds+'s'],['Alert delivery',d.alerts.delivery_seconds+'s']].map(([a,b])=>`<div class="glass-soft metric"><div class="muted">${a}</div><div class="value">${b}</div></div>`).join('');
}
function connectAlerts(){
  ws=new WebSocket((location.protocol==='https:'?'wss://':'ws://')+location.host+'/ws/alerts');
  ws.onopen=()=>{$('wsStatus').style.background='#7ff0a5';$('wsText').textContent='Live alert stream connected';};
  ws.onclose=()=>{$('wsStatus').style.background='#ffd36b';$('wsText').textContent='Reconnecting…';setTimeout(connectAlerts,1500);};
  ws.onmessage=e=>{const a=JSON.parse(e.data);if(!a.id)return;addAlert(a);};
}
function addAlert(a){$('alertsList').insertAdjacentHTML('afterbegin',`<div class="glass-soft alert"><b>${escapeHtml(a.title)}</b><div>${escapeHtml(a.message)}</div><small>${escapeHtml(a.issued_at)} · ${escapeHtml(a.protocol)}</small><br><button class="action-btn" onclick="ack('${escapeHtml(a.id)}')">Acknowledge</button></div>`)}
async function ack(id){await fetch(`/v1/alerts/${encodeURIComponent(id)}/ack`,{method:'POST'});alert('Alert acknowledged');}

function showView(view){
  document.querySelectorAll('.nav-btn').forEach(x=>x.classList.toggle('active',x.dataset.view===view));
  document.querySelectorAll('.view').forEach(v=>v.classList.toggle('active',v.id===view));
  if(view==='trust')trust();
}
document.querySelectorAll('.nav-btn').forEach(b=>b.onclick=()=>showView(b.dataset.view));
document.querySelectorAll('.side-btn[data-view]').forEach(b=>b.onclick=()=>showView(b.dataset.view));
document.querySelectorAll('.lang').forEach(b=>b.onclick=()=>{document.querySelectorAll('.lang').forEach(x=>x.classList.remove('active'));b.classList.add('active');language=b.dataset.lang;});
$('city').onchange=loadWeather;$('send').onclick=send;$('message').onkeydown=e=>{if(e.key==='Enter')send();};$('loadAdvisory').onclick=advisory;
$('replay').onclick=async()=>{await fetch('/v1/alerts/replay',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:city,severity:'severe'})});};
$('mic').onclick=()=>{const SR=window.SpeechRecognition||window.webkitSpeechRecognition;if(!SR){alert('Speech recognition is not supported by this browser. Use text mode.');return;}const r=new SR();r.lang=language==='kn'?'kn-IN':language==='hi'?'hi-IN':language==='mr'?'mr-IN':'en-IN';r.onresult=e=>$('message').value=e.results[0][0].transcript;r.start();};
loadWeather();connectAlerts();trust();loadAIStatus();
