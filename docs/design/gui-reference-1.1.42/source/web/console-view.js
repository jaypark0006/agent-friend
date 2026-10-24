import {formatJSON,createRequestScope,createSensorStream} from '/console-api.js';
import {$,asset,toast,message,number,vector,copyText} from '/console-ui.js';
export function createViewFeature({runtime,onCamera,isExecuting}) {
const scope=createRequestScope(),{request,jsonRequest,postJSON}=scope;
const state={status:null,sensors:null,history:null,historyKind:'images',previewOn:false,previewBusy:false,previewGeneration:0,previewTimer:null,previewAbort:null,sensorAt:0,sensorRenderAt:0,pollTimer:null,pollBusy:false,configLoaded:false,configSaving:false,configSaved:false,get route(){return runtime.route},get alive(){return runtime.alive}};
const pageNames={status:'系统看板',widget:'AI流水线',image:'媒体画框',text:'文字卡片',camera:'摄像头页',settings:'控制中心'};
const faceNames={bottom:'底部 · Type-C',top:'顶部 · AI键',left:'左侧',right:'右侧',screen:'屏幕面',back:'背面',unknown:'暂不确定'};
function online(ok) {
    $('connection').textContent=ok?'设备在线':'连接中断';$('connection').className=`badge${ok?'':' offline'}`;
    $('sidebar-state').textContent=ok?'已连接设备':'连接中断';$('sidebar-dot').classList.toggle('online',ok);
}
function renderStatus(s) {
    state.status=s;online(true);
    $('firmware').textContent=`固件 ${s.version||'—'}`;
    $('home-page').textContent=pageNames[s.page]||s.page||'—';$('device-page').textContent=pageNames[s.page]||'—';
    $('home-unread').textContent=number(s.message_unread);$('home-fps').textContent=`${number(s.page==='camera'?s.camera_display_fps:s.page==='image'?s.display_fps:s.gui?.fps,1)} FPS`;
    $('wifi-name').textContent=s.ssid||'未连接';$('device-ip').textContent=s.ip||location.hostname;
    $('image-unread').textContent=number(s.image_unread);$('message-unread').textContent=number(s.message_unread);
    $('fps-value').textContent=`${number(s.display_fps,1)} / ${number(s.gui?.fps,1)}`;
    $('frame-counts').textContent=`${number(s.received)} / ${number(s.displayed)} / ${number(s.dropped)}`;
    $('timings').textContent=`${number(s.decode_ms,1)} / ${number(s.lcd_transfer_ms,1)} ms`;
    document.querySelectorAll('[data-page]').forEach(b=>{b.classList.toggle('selected',b.dataset.page===s.page);b.setAttribute('aria-pressed',String(b.dataset.page===s.page));});
    if(state.configLoaded&&!state.configSaving&&typeof s.auto_switch==='boolean') {
        state.configSaved=s.auto_switch;$('auto-switch').checked=s.auto_switch;
    }
    $('last-update').textContent=`状态更新 ${new Date().toLocaleTimeString()}`;
}
async function refreshStatus() {
    if(state.pollBusy||!state.alive||document.hidden||isExecuting())return false;
    state.pollBusy=true;
    try {
        renderStatus(await jsonRequest('/api/status',{timeout:4500}));
        return true;
    } catch(error) { if(error.name!=='AbortError'){online(false);$('last-update').textContent='暂时无法获取最新状态';}
        return false; }
    finally { state.pollBusy=false; }
}
function poll() {
    clearTimeout(state.pollTimer);
    if(!state.alive||document.hidden)return;
    refreshStatus().finally(()=>{
        if(state.route==='pipeline') refreshPipeline();
        if(state.alive&&!document.hidden)state.pollTimer=setTimeout(poll,3000);
    });
}
function captureState(value) {
    if(!value)return '当前固件未提供';
    if(value.error&&value.error!=='ESP_OK')return `异常 · ${value.error}`;
    return ({running:'采集中',disabled:'已关闭',pending:'正在处理',unavailable:'暂不可用',error:'采集异常'})[value.state]||(value.enabled?'采集中':'已关闭');
}
function renderSensors(s,source) {
    state.sensors=s;state.sensorAt=Date.now();
    $('sensor-source').textContent=source;
    $('battery-level').textContent=s.battery?`${number(s.battery.soc_percent)}%`:'未获取';
    $('battery-electrical').textContent=s.battery?`${number(s.battery.voltage_mv)} mV / ${number(s.battery.current_ma)} mA`:'—';
    $('battery-temperature').textContent=s.battery?`${number(s.battery.temperature_c,1)} °C`:'—';
    const o=s.orientation||{};
    $('down-face').textContent=o.valid?(faceNames[o.down_face]||'暂不确定'):'暂不确定';
    $('rotation').textContent=typeof o.display_rotation_cw_deg==='number'?`${o.display_rotation_cw_deg}°`:'—';
    $('motion-state').textContent=o.valid?'姿态稳定':o.reason==='flat'?'设备接近平放':'姿态暂不可靠';
    $('accel').textContent=vector(s.accel_g);$('gyro').textContent=vector(s.gyro_dps);$('magnetic').textContent=`${vector(s.mag0_uT)} / ${vector(s.mag1_uT)}`;
    for(const name of ['ai','boot']) {
        const b=s.buttons?.[name];$(name+'-button').textContent=`${name.toUpperCase()} ${!b?.available?'未提供':b.pressed?'按下':'松开'}`;
        $(name+'-button').classList.toggle('selected',!!b?.pressed);
    }
    const event=s.buttons?.events?.at(-1);
    const eventNames={down:'按下',up:'松开',click:'单击',double_click:'双击',long_press:'长按'};
    $('button-event').textContent=event?`最近：${String(event.button).toUpperCase()} ${eventNames[event.event]||event.event} · #${event.seq}`:'暂无事件';
    const mic=s.microphone,cam=s.camera;
    $('microphone-state').textContent=captureState(mic);$('camera-state').textContent=captureState(cam);
    const levels=mic?.valid?mic.levels||[]:[],peak=Math.max(0,...levels.map(l=>Number(l.peak)||0));
    $('mic-level').value=Math.min(1,peak);$('mic-value').textContent=levels.length?`峰值 ${Math.round(peak*100)}% · ${levels.map(l=>number(l.rms_dbfs,1)+' dBFS').join(' / ')}`:'暂无音量数据';
    $('camera-size').textContent=cam?.width?`${cam.width} × ${cam.height} · ${cam.pixel_format||'—'} · ${number(cam.capture_fps,1)} FPS`:cam?.module_presence==='absent'?'未检测到左侧摄像头':'尚未出帧';
    document.querySelectorAll('[data-capture]').forEach(b=>{const value=s[b.dataset.capture],supported=!!value?.ready;if(!b.dataset.busy){b.disabled=!supported;b.checked=!!value?.requested_enabled;}b.title=supported?'':'当前固件未提供此能力';});
    onCamera(s.camera);
    $('sensor-json').textContent=formatJSON(s);renderInteract();
}
function renderInteract() {
    const board=state.sensors?.interact?.slots?.[$('interact-slot').value];
    $('interact-presence').textContent=!board?'当前固件未提供':board.initialized?'已连接':board.identified?'已识别，未初始化':board.presence==='absent'?'未插入':'此槽未识别到交互子板';
    $('interact-presence').className='badge '+(board?.initialized?'':'subtle');
    const lightVal=board?.valid?board.light_level:0;
    $('interact-light').textContent=board?.valid?`${board.light_level} / 100`:'—';
    const lightBar=$('interact-light-bar');if(lightBar)lightBar.style.width=lightVal+'%';
    $('interact-motion').textContent=board?.valid?(board.motion_detected?'检测到人体运动':'暂无运动'):'—';
    const pirDot=$('interact-pir-dot');if(pirDot)pirDot.style.background=board?.motion_detected?'#f97316':'#94a3b8';
    const keyL=$('interact-key-l');if(keyL){keyL.textContent=board?.valid?(board.left_pressed?'左: 触发':'左: 松开'):'左: —';keyL.className='badge '+(board?.left_pressed?'':'subtle');}
    const keyR=$('interact-key-r');if(keyR){keyR.textContent=board?.valid?(board.right_pressed?'右: 触发':'右: 松开'):'右: —';keyR.className='badge '+(board?.right_pressed?'':'subtle');}
    $('interact-mode').textContent=({auto:'自动 (优先触摸)',key:'机械按键',touch:'触摸'})[board?.input_mode]||'—';
    const event=board?.events?.at(-1);$('interact-event').textContent=event?`最近事件：${event.input} ${event.active?'触发':'释放'} · #${event.seq}`:'暂无事件';
    for(const id of ['interact-led-send','interact-led-off','preset-notify-done','preset-notify-pulse','preset-notify-alert','interact-ir-send']){
        const el=$(id);if(el)el.disabled=!board?.initialized;
    }
    for(const id of ['interact-config','interact-disable']){
        const el=$(id);if(el)el.disabled=!state.sensors?.interact?.ready;
    }
    if(board?.error&&board.error!=='ESP_OK'&&board.identified)$('interact-event').textContent=`初始化/采样：${board.error}`;
    const last=state.sensors?.interact?.results?.at(-1);if(last&&last.id===state.interactRequest)message('interact-result',last.error==='ESP_OK'?`请求 #${last.id} 执行完成`:`请求 #${last.id} 失败：${last.error}`,last.error!=='ESP_OK');
    if(board?.colors&&Array.isArray(board.colors)){
        board.colors.forEach((c,idx)=>{
            const node=document.querySelector(`.led-node[data-idx="${idx}"]`);
            if(node){
                const active=(c.r||c.g||c.b);
                node.style.background=active?`rgb(${c.r},${c.g},${c.b})`:'#090d16';
                node.style.boxShadow=active?`0 0 10px rgb(${c.r},${c.g},${c.b})`:'none';
                node.style.borderColor=active?`rgb(${c.r},${c.g},${c.b})`:'#334155';
            }
        });
    }
}
$('interact-slot').onchange=renderInteract;
async function controlInteract(path,values,button){
    if(button)button.disabled=true;
    try{const r=await postJSON('/api/interact/'+path,{slot:$('interact-slot').value,...values});state.interactRequest=r.accepted;message('interact-result',`请求 #${r.accepted} 已排队`);}
    catch(e){message('interact-result',e.message,true);}
    finally{renderInteract();}
}
$('interact-led-send').onclick=()=>{
    const hex=$('interact-color').value,color=[1,3,5].map(at=>parseInt(hex.slice(at,at+2),16)),values={color,brightness:Number($('interact-brightness').value)};
    if($('interact-led').value!=='all')values.index=Number($('interact-led').value);
    controlInteract('leds',values,$('interact-led-send'));
};
$('interact-led-off').onclick=()=>controlInteract('leds',{color:[0,0,0]},$('interact-led-off'));
const pDone=$('preset-notify-done');if(pDone)pDone.onclick=()=>controlInteract('leds',{color:[40,220,80],brightness:16},pDone);
const pPulse=$('preset-notify-pulse');if(pPulse)pPulse.onclick=()=>controlInteract('leds',{color:[0,180,255],brightness:16},pPulse);
const pAlert=$('preset-notify-alert');if(pAlert)pAlert.onclick=()=>controlInteract('leds',{color:[240,140,0],brightness:16},pAlert);
document.querySelectorAll('.led-preset-btn').forEach(btn=>{
    btn.onclick=()=>{
        const effect=btn.dataset.effect;
        if(effect){controlInteract('leds',{effect},btn);toast(`已触发动画：${effect}`);}
    };
});
document.querySelectorAll('.color-chip').forEach(chip=>{
    chip.onclick=()=>{
        const col=chip.getAttribute('data-color');
        if(col){$('interact-color').value=col;}
    };
});
document.querySelectorAll('.led-node').forEach(node=>{
    node.onclick=()=>{
        const idx=node.getAttribute('data-idx');
        const sel=$('interact-led');
        if(sel){sel.value=(sel.value===idx)?'all':idx;}
        const label=$('interact-led-target-label');
        if(label){label.textContent=sel.value==='all'?'已选: 全部六颗':`已选: LED ${sel.value}`;}
    };
});
$('interact-led').onchange=()=>{
    const label=$('interact-led-target-label');
    if(label){label.textContent=$('interact-led').value==='all'?'已选: 全部六颗':`已选: LED ${$('interact-led').value}`;}
};
$('interact-brightness').oninput=()=>{
    const v=$('brightness-val');if(v)v.textContent=$('interact-brightness').value;
};
$('interact-ir-send').onclick=()=>{
    const address=Number($('interact-ir-address').value),command=Number($('interact-ir-command').value);
    if(![address,command].every(n=>Number.isInteger(n)&&n>=0&&n<=255)){message('interact-result','地址和命令需要是0–255整数。',true);return;}
    controlInteract('ir',{address,command},$('interact-ir-send'));
};
$('interact-config').onclick=()=>controlInteract('config',{enabled:true,input_mode:$('interact-input-mode').value},$('interact-config'));
$('interact-disable').onclick=()=>controlInteract('config',{enabled:false},$('interact-disable'));
function sensorRoute() { return state.route==='view'||state.route==='interact'||state.route==='devtools'||state.route==='camera'; }
async function readSensors() {
    try {const s=await jsonRequest('/api/sensors',{timeout:4500});if(sensorRoute()&&!document.hidden)renderSensors(s,'HTTP 快照');}
    catch(error){if(error.name!=='AbortError'&&!sensorStream.hasLive())$('sensor-source').textContent='快照不可用';}
}
const sensorStream=createSensorStream({
    onState:text=>{$('sensor-source').textContent=text;},
    onSnapshot:value=>{if(Date.now()-state.sensorRenderAt<100)return;state.sensorRenderAt=Date.now();renderSensors(value,'WS 实时 · 10 Hz');}
});
function stopSensors(){sensorStream.setConsumer('view',false);sensorStream.setConsumer('camera',false);}
function startSensors(){
    if(!sensorRoute()||!state.alive||document.hidden)return;
    sensorStream.setEnabled($('sensors-live').checked);sensorStream.setConsumer(state.route,true);
}
$('sensors-live').onchange=()=>{
    if($('sensors-live').checked){state.sensorRenderAt=0;startSensors();}
    else{stopSensors();$('sensor-source').textContent='已暂停 · 保留最后值';}
};
function stopPreview() {
    state.previewOn=false;state.previewGeneration++;clearTimeout(state.previewTimer);state.previewAbort?.abort();
    $('preview-toggle').checked=false;
}
async function getPreview(live=false) {
    if(state.previewBusy)return;
    const generation=state.previewGeneration,controller=new AbortController();state.previewAbort=controller;state.previewBusy=true;
    try {
        const result=await request('/api/screenshot',{signal:controller.signal,timeout:8000});
        if(!result.ok)throw new Error(`HTTP ${result.status}`);
        if(!result.blob.type.startsWith('image/'))throw new Error('设备尚未提供截图');
        if(generation!==state.previewGeneration||state.route!=='view')return;
        const url=asset('screen',result.blob);$('preview').src=url;$('preview').hidden=false;$('preview-empty').hidden=true;
        $('snapshot-download').href=url;$('snapshot-download').hidden=false;
        message('preview-state',`画面更新 ${new Date().toLocaleTimeString()}`);
    } catch(error) {if(error.name!=='AbortError'&&generation===state.previewGeneration)message('preview-state',error.message,true);}
    finally {
        state.previewBusy=false;if(state.previewAbort===controller)state.previewAbort=null;
        if(live&&state.previewOn&&generation===state.previewGeneration&&state.route==='view'&&!document.hidden)state.previewTimer=setTimeout(()=>getPreview(true),500);
    }
}
$('snapshot').onclick=()=>getPreview();
$('preview-toggle').onchange=()=>{if(!$('preview-toggle').checked){stopPreview();return;}state.previewOn=true;if(!state.previewBusy)getPreview(true);else state.previewTimer=setTimeout(()=>getPreview(true),600);};
document.querySelectorAll('[data-page]').forEach(button=>button.onclick=async()=>{
    const buttons=[...document.querySelectorAll('[data-page]')];buttons.forEach(b=>b.disabled=true);
    try {await postJSON('/api/view',{page:button.dataset.page});message('view-result','切页请求已接收');refreshStatus();}
    catch(error){message('view-result',error.message,true);}
    finally{buttons.forEach(b=>b.disabled=false);}
});
document.querySelectorAll('[data-capture]').forEach(button=>button.onchange=async()=>{
    const desired=button.checked;button.disabled=true;button.dataset.busy='true';
    try {const value=await postJSON(`/api/${button.dataset.capture}`,{enabled:desired});message('capture-result',`采集请求 #${value.request_id} 已接收`);await readSensors();}
    catch(error){button.checked=!desired;message('capture-result',error.message,true);}
    finally {delete button.dataset.busy;const value=state.sensors?.[button.dataset.capture];button.disabled=!value?.ready;if(value)button.checked=!!value.requested_enabled;}
});
$('copy-sensors').onclick=()=>copyText(state.sensors?formatJSON(state.sensors):null);
function renderHistory() {
    const list=$('history-list');list.replaceChildren();
    const items=state.history?.[state.historyKind]?.entries||[];
    if(!items.length){const p=document.createElement('p');p.className='hint';p.textContent='这里还没有内容。';list.append(p);return;}
    for(const item of [...items].reverse()) {
        const row=document.createElement('div');row.className='history-item';
        const info=document.createElement('div'),label=document.createElement('small'),dot=document.createElement('span');
        dot.className=`read-dot${item.read?' read':''}`;label.append(dot,document.createTextNode(`${item.time||'—'} · #${item.id} · ${item.read?'已读':'未读'}`));info.append(label);
        if(state.historyKind==='messages'){const p=document.createElement('p');p.textContent=item.text||'';info.append(p);row.append(info);}
        else {
            const actions=document.createElement('div');actions.className='row wrap';
            const preview=document.createElement('button');preview.className='secondary small';preview.textContent='查看图片';preview.onclick=()=>previewHistory(item.id);
            const show=document.createElement('button');show.className='small';show.textContent='显示到设备';show.onclick=async()=>{show.disabled=true;try{await postJSON('/api/view',{page:'image',id:item.id});toast('显示请求已接收');refreshStatus();}catch(e){toast(e.message);}finally{show.disabled=false;}};
            actions.append(preview,show);row.append(info,actions);
        }
        list.append(row);
    }
}
async function readHistory() {
    $('refresh-history').disabled=true;
    try {state.history=await jsonRequest('/api/history');renderHistory();message('history-state',`图片 ${state.history.images?.count||0} · 文字 ${state.history.messages?.count||0}，重启清空。`);}
    catch(e){message('history-state',e.message,true);}
    finally{$('refresh-history').disabled=false;}
}
let historyGeneration=0;
async function previewHistory(id) {
    const generation=++historyGeneration;
    try {const r=await request(`/api/image?id=${encodeURIComponent(id)}`);if(!r.ok)throw new Error(`图片已过期或获取失败 (${r.status})`);if(generation!==historyGeneration)return;$('history-preview').src=asset('history',r.blob);$('history-preview-wrap').hidden=false;}
    catch(e){message('history-state',e.message,true);}
}
function clearHistoryPreview(){historyGeneration++;$('history-preview-wrap').hidden=true;$('history-preview').removeAttribute('src');asset('history',null);}
$('close-history-preview').onclick=clearHistoryPreview;
$('history-detail').ontoggle=()=>{if($('history-detail').open)readHistory();else clearHistoryPreview();};
$('refresh-history').onclick=readHistory;
document.querySelectorAll('[data-history]').forEach(b=>b.onclick=()=>{state.historyKind=b.dataset.history;document.querySelectorAll('[data-history]').forEach(t=>t.classList.toggle('selected',t===b));clearHistoryPreview();renderHistory();});
let configGeneration=0;
async function readConfig() {
    if(state.configSaving)return;
    const generation=++configGeneration;state.configLoaded=false;$('auto-switch').disabled=true;
    try {
        const config=await jsonRequest('/api/config');if(generation!==configGeneration)return;
        const automatic=typeof config.auto_switch==='boolean'?config.auto_switch:config.new_message_action==='switch'?true:config.new_message_action==='keep'?false:null;
        if(automatic===null)throw new Error('设备设置格式异常');
        state.configSaved=automatic;$('auto-switch').checked=automatic;state.configLoaded=true;message('config-result','');
    } catch(e){if(generation===configGeneration)message('config-result',e.message,true);}
    finally{if(generation===configGeneration)$('auto-switch').disabled=!state.configLoaded;}
}
$('auto-switch').onchange=async()=>{
    if(!state.configLoaded||state.configSaving)return;
    const automatic=$('auto-switch').checked;state.configSaving=true;configGeneration++;$('auto-switch').disabled=true;
    message('config-result','保存中…');
    try{
        const result=await postJSON('/api/config',{auto_switch:automatic});
        if(result.auto_switch!==automatic)throw new Error('设备尚未确认开关状态');
        state.configSaved=automatic;message('config-result','已保存');
    } catch(e){
        $('auto-switch').checked=state.configSaved;state.configLoaded=false;
        message('config-result',`保存未确认：${e.message}。重新进入设备页可读取实际状态。`,true);
    } finally{state.configSaving=false;$('auto-switch').disabled=!state.configLoaded;}
};

async function refreshPipeline() {
    try {
        const data = await jsonRequest('/api/widget', {timeout: 4500});
        renderPipeline(data);
    } catch(e) {
        const list = $('pipeline-list');
        if(list) list.innerHTML = `<p class="hint error">获取流水线失败：${e.message}</p>`;
    }
}

function renderPipeline(data) {
    const list = $('pipeline-list');
    if(!list) return;
    const items = data?.agents || [];
    if(!items.length) {
        list.innerHTML = '<p class="hint">当前无活动或排队的 Agent 任务。</p>';
        return;
    }
    list.replaceChildren();
    for(const it of items) {
        const card = document.createElement('div');
        card.className = `pipeline-card${it.done ? ' done' : ''}`;
        
        const header = document.createElement('div');
        header.className = 'pipeline-header';
        
        const titleSpan = document.createElement('strong');
        titleSpan.textContent = it.title || it.id || 'Task';
        if(it.color) titleSpan.style.color = it.color;
        
        const badgeSpan = document.createElement('span');
        badgeSpan.className = `badge${it.done ? '' : ' subtle'}`;
        badgeSpan.textContent = it.done ? 'DONE' : (it.progress >= 0 ? `${it.progress}%` : 'RUNNING');
        header.append(titleSpan, badgeSpan);
        
        const statusP = document.createElement('p');
        statusP.className = 'hint';
        statusP.style.marginTop = '2px';
        statusP.textContent = it.status || '执行中...';
        card.append(header, statusP);
        
        if(it.progress >= 0) {
            const track = document.createElement('div');
            track.className = 'pipeline-bar-track';
            const fill = document.createElement('div');
            fill.className = 'pipeline-bar-fill';
            fill.style.width = Math.min(100, Math.max(0, it.progress)) + '%';
            fill.style.background = it.color || '#39e69d';
            track.append(fill);
            card.append(track);
        }
        
        const act = it.action;
        if(act && act.type === 'confirm') {
            const actionsDiv = document.createElement('div');
            actionsDiv.className = 'pipeline-actions';
            if(act.result) {
                const resLabel = document.createElement('span');
                resLabel.className = 'badge';
                resLabel.textContent = `已决策：${act.result}`;
                actionsDiv.append(resLabel);
            } else {
                const btn1 = document.createElement('button');
                btn1.className = 'small';
                btn1.textContent = act.btn1 || '批准';
                btn1.onclick = async () => {
                    btn1.disabled = true;
                    try {
                        await postJSON('/api/widget', { id: it.id, action: { result: act.btn1 || 'Approve' }, done: true });
                        toast(`已确认：${act.btn1 || '批准'}`);
                        await refreshPipeline();
                    } catch(err) { toast(err.message); }
                    finally { btn1.disabled = false; }
                };
                const btn2 = document.createElement('button');
                btn2.className = 'secondary small';
                btn2.textContent = act.btn2 || '取消';
                btn2.onclick = async () => {
                    btn2.disabled = true;
                    try {
                        await postJSON('/api/widget', { id: it.id, action: { result: act.btn2 || 'Cancel' }, done: true });
                        toast(`已取消：${act.btn2 || '取消'}`);
                        await refreshPipeline();
                    } catch(err) { toast(err.message); }
                    finally { btn2.disabled = false; }
                };
                actionsDiv.append(btn1, btn2);
            }
            card.append(actionsDiv);
        }
        list.append(card);
    }
}

const pipeSend = $('pipe-send');
if(pipeSend) pipeSend.onclick = async () => {
    pipeSend.disabled = true;
    message('pipe-result', '发送中…');
    try {
        const id = $('pipe-id').value.trim() || 'codex';
        const title = $('pipe-title').value.trim() || 'Codex';
        const status = $('pipe-status').value.trim();
        const progress = Number($('pipe-progress').value);
        const color = $('pipe-color').value;
        const confirm = $('pipe-confirm').checked;
        const payload = { id, title, status, progress, color, show: true };
        if(confirm) {
            payload.action = {
                type: 'confirm',
                options: [$('pipe-btn1').value.trim() || '批准', $('pipe-btn2').value.trim() || '取消']
            };
        }
        await postJSON('/api/widget', payload);
        message('pipe-result', '步骤已推送到随身屏流水线');
        await refreshPipeline();
    } catch(err) {
        message('pipe-result', err.message, true);
    } finally {
        pipeSend.disabled = false;
    }
};

const pipeDone = $('pipe-done');
if(pipeDone) pipeDone.onclick = async () => {
    pipeDone.disabled = true;
    message('pipe-result', '标记完成中…');
    try {
        const id = $('pipe-id').value.trim() || 'codex';
        const title = $('pipe-title').value.trim() || 'Codex';
        const status = $('pipe-status').value.trim() || '任务已完成';
        const color = $('pipe-color').value;
        await postJSON('/api/widget', { id, title, status, progress: 100, color, done: true, show: true });
        message('pipe-result', '任务已标记为 100% 完成');
        await refreshPipeline();
    } catch(err) {
        message('pipe-result', err.message, true);
    } finally {
        pipeDone.disabled = false;
    }
};

const pipeClear = $('pipeline-clear-all');
if(pipeClear) pipeClear.onclick = async () => {
    if(!window.confirm('确定清空随身屏上的全部任务卡片吗？')) return;
    try {
        await postJSON('/api/widget', { clear_all: true });
        toast('流水线队列已清空');
        await refreshPipeline();
    } catch(err) { toast(err.message); }
};

const pipeSwitch = $('pipeline-switch-screen');
if(pipeSwitch) pipeSwitch.onclick = async () => {
    try {
        await postJSON('/api/view', { page: 'widget' });
        toast('随身屏已切到流水线');
        await refreshStatus();
    } catch(err) { toast(err.message); }
};

const pipeProg = $('pipe-progress');
if(pipeProg) pipeProg.oninput = () => {
    const l = $('pipe-progress-label');
    if(l) l.textContent = pipeProg.value + '%';
};

const pipeConfCheck = $('pipe-confirm');
if(pipeConfCheck) pipeConfCheck.onchange = () => {
    const opts = $('pipe-confirm-opts');
    if(opts) opts.hidden = !pipeConfCheck.checked;
};

const pipeRefreshBtn = $('pipeline-refresh');
if(pipeRefreshBtn) pipeRefreshBtn.onclick = refreshPipeline;

function enter(){
    if(sensorRoute()){if($('sensors-live').checked)startSensors();else readSensors();}
    if(state.route==='view'){readConfig();}
    if(state.route==='send'){if($('history-detail')?.open)readHistory();}
    if(state.route==='pipeline'){refreshPipeline();}
    if(state.route==='interact'){readSensors();}
}
function leave(){stopPreview();stopSensors();clearHistoryPreview();scope.cancel();}
return {
    enter,leave,suspend(){leave();clearTimeout(state.pollTimer);},resume(){poll();enter();},
    dispose(){leave();clearTimeout(state.pollTimer);asset('screen',null);$('preview').removeAttribute('src');$('preview').hidden=true;$('preview-empty').hidden=false;$('snapshot-download').hidden=true;},
    poll,hasLive:()=>sensorStream.hasLive(),invalidateHistory(){state.history=null;}
};
}
