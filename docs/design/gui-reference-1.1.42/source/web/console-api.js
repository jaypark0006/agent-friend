// Shared by HTTP Try and ordinary controls. No requests run on import.
const activeRequests = new Set();
export const RESPONSE_LIMIT = 4 * 1024 * 1024;
const json = body => ({status:200,headers:{'Content-Type':'application/json'},body});
const accepted = body => ({...json(body),status:202});
const reading = (id,title,path,mock) => ({id,title,method:'GET',path,kind:'none',headers:{},mock:json(mock)});
const writing = (id,title,path,body,mock={accepted:true}) => ({id,title,method:'POST',path,kind:'json',headers:{'Content-Type':'application/json'},body,mock:json(mock)});
const orientation = {valid:true,reason:'stable',down_face:'bottom',rotation_cw_deg:0,display_rotation_cw_deg:0,auto_rotation:true};
export const presets = [
    reading('status','设备状态','/api/status',{app:'lan_screen',version:'mock',connected:true,ip:'mock-device',ssid:'Mock Wi-Fi',page:'image',display_fps:29.6,image_unread:2,message_unread:1,received:120,displayed:118,dropped:2}),
    reading('sensors','传感器快照','/api/sensors',{timestamp_us:123000000,accel_g:[0,-1,0],gyro_dps:[0,0,0],mag0_uT:[12,3,42],mag1_uT:[11,4,41],battery:{soc_percent:82,voltage_mv:4080},orientation,buttons:{event_sequence:1,events:[{seq:1,button:'ai',event:'click',timestamp_us:122000000}]},microphone:{enabled:false,valid:false,state:'disabled'},camera:{enabled:false,valid:false,state:'disabled'}}),
    reading('orientation','朝向与旋转','/api/orientation',orientation),
    reading('history','内容历史','/api/history',{page:'image',images:{count:1,unread:1,entries:[{id:1,time:'14:26',read:false}]},messages:{count:1,unread:1,entries:[{id:1,time:'14:26',read:false,text:'任务完成，等待下一步。',font_size:32,align:'left'}]}}),
    reading('screenshot','屏幕截图','/api/screenshot',{mock_binary:'RGB565 BMP',note:'这是本地Mock占位数据；真实设备请求返回截图二进制。'}),
    reading('config','读取设备设置','/api/config',{auto_switch:false,new_message_action:'keep'}),
    reading('buttons','按键状态','/api/buttons',{ready:true,ai:{available:true,pressed:false,held_ms:0,press_count:2},boot:{available:true,pressed:false,held_ms:0,press_count:0},event_sequence:1,events:[{seq:1,button:'ai',event:'click',timestamp_us:122000000}]}),
    reading('microphone','麦克风音量','/api/microphone',{ready:true,state:'running',requested_enabled:true,enabled:true,valid:true,request_id:1,applied_request_id:1,sample_rate_hz:48000,window_ms:20,levels:[{channel:0,rms:0.08,peak:0.2,rms_dbfs:-21.9,clipped_samples:0},{channel:1,rms:0,peak:0,rms_dbfs:-120,clipped_samples:0}]}),
    reading('audio','音频片段','/api/microphone/audio',{mock_binary:'20ms PCM16 stereo WAV',note:'本地Mock不生成音频。'}),
    reading('camera','摄像头状态','/api/camera',{module_presence:'present',camera_identified:true,state:'running',enabled:true,valid:true,pixel_format:'UYVY',width:1024,height:768,bytes_per_line:2048,capture_fps:25}),
    reading('camera-render','色块状态','/api/camera/render',{enabled:false,state:'disabled',target_fps:30,block_size:2,width:256,height:256,generated:0,displayed:0,render_fps:0,display_fps:0}),
    {...writing('camera-render-start','开始摄像头色块','/api/camera/render',{enabled:true,target_fps:30,block_size:2}),mock:accepted({enabled:true,state:'pending',target_fps:30,block_size:2,width:256,height:256})},
    {...writing('camera-render-stop','停止摄像头色块','/api/camera/render',{enabled:false}),mock:accepted({enabled:false,state:'disabled',target_fps:30,block_size:2,width:256,height:256})},
    reading('camera-render-frame','色块预览帧','/api/camera/render/frame',{mock_binary:'256x256 RGB565_BE',note:'真实请求返回131072字节色块帧，本地Mock仅提供元数据。'}),
    reading('camera-frame','摄像头原始帧','/api/camera/frame',{mock_binary:'UYVY',width:1024,height:768,note:'真实请求返回UYVY二进制，本地Mock仅提供元数据占位。'}),
    reading('image-history','下载历史图片','/api/image?id=1',{mock_binary:'JPEG',note:'id需取自设备当前历史；本地Mock不生成图片。'}),
    reading('interact','交互子板状态','/api/interact',{ready:true,slots:{right:{identified:true,valid:true,input_mode:'touch',light_level:65,motion_detected:false,left_pressed:false,right_pressed:false,led_brightness:32}}}),
    writing('interact-leds','交互子板灯光','/api/interact/leds',{slot:'right',color:[37,99,235],brightness:32},{accepted:1,status:'queued'}),
    writing('interact-ir','交互子板红外','/api/interact/ir',{slot:'right',address:0,command:0},{accepted:2,status:'queued'}),
    writing('interact-config','交互子板输入模式','/api/interact/config',{slot:'right',enabled:true,input_mode:'auto'},{accepted:3,status:'queued'}),
    reading('info','接口清单','/api/info',{app:'lan_screen',version:'mock',sensor_push_hz:10}),
    writing('text','推送文字','/api/text',{text:'任务完成，等待下一步。',font_size:32,align:'left',time:'14:26'},{accepted:12,content_type:'text'}),
    {...writing('frame','推送已准备图片','/api/frame',null,{accepted:123}),kind:'image',headers:{'Content-Type':'image/jpeg'}},
    writing('view-image','显示图片页','/api/view',{page:'image'}),
    writing('view-text','显示文字页','/api/view',{page:'text'}),
    writing('view-camera','显示摄像头页','/api/view',{page:'camera'}),
    writing('view-settings','显示设置页','/api/view',{page:'settings'}),
    writing('scroll','文字滚动到底部','/api/view',{page:'text',scroll_y:-1,duration_ms:500}),
    writing('save-config','自动切换','/api/config',{auto_switch:true},{auto_switch:true,new_message_action:'switch'}),
    {...writing('mic-on','开启麦克风','/api/microphone',{enabled:true}),mock:accepted({request_id:1,applied_request_id:0,requested_enabled:true,enabled:false,valid:false,state:'pending'})},
    {...writing('mic-off','关闭麦克风','/api/microphone',{enabled:false}),mock:accepted({request_id:2,applied_request_id:1,requested_enabled:false,enabled:true,valid:false,state:'pending'})},
    {...writing('cam-on','开启摄像头','/api/camera',{enabled:true}),mock:accepted({request_id:1,applied_request_id:0,requested_enabled:true,enabled:false,valid:false,state:'pending'})},
    {...writing('cam-off','关闭摄像头','/api/camera',{enabled:false}),mock:accepted({request_id:2,applied_request_id:1,requested_enabled:false,enabled:true,valid:false,state:'pending'})},
];
export function deviceURL(path) {
    const url = new URL(path,location.origin);
    if(url.origin!==location.origin || url.username || url.password || url.hash)
        throw new Error('请输入当前设备的路径，例如 /api/status。');
    return url;
}
export function parseHeaders(text) {
    let value;
    try { value=JSON.parse(text); } catch { throw new Error('Headers需要有效的JSON对象。'); }
    if(!value || typeof value!=='object' || Array.isArray(value) || Object.values(value).some(v=>typeof v!=='string'))
        throw new Error('Headers需要JSON对象，值必须是字符串。');
    return new Headers(value);
}
async function readBlob(response,signal) {
    const contentLength=Number(response.headers.get('Content-Length'));
    if(contentLength>RESPONSE_LIMIT) throw new Error('响应超过4 MiB，已停止读取。');
    if(!response.body) return new Blob([],{type:response.headers.get('Content-Type')||''});
    const reader=response.body.getReader(),chunks=[];let bytes=0;
    try {
        while(true) {
            if(signal.aborted) throw new DOMException('Aborted','AbortError');
            const {done,value}=await reader.read();
            if(done) break;
            bytes+=value.byteLength;
            if(bytes>RESPONSE_LIMIT) throw new Error('响应超过4 MiB，已停止读取。');
            chunks.push(value);
        }
    } catch(error) { await reader.cancel().catch(()=>{}); throw error; }
    finally { reader.releaseLock(); }
    return new Blob(chunks,{type:response.headers.get('Content-Type')||''});
}
export async function request(path,{method='GET',headers={},body,timeout=10000,signal}={}) {
    const url=deviceURL(path),controller=new AbortController();
    activeRequests.add(controller);
    const onAbort=()=>controller.abort();
    if(signal?.aborted) controller.abort();
    signal?.addEventListener('abort',onAbort,{once:true});
    let timedOut=false;
    const timer=setTimeout(()=>{timedOut=true;controller.abort();},timeout);
    const started=performance.now();
    try {
        const response=await fetch(url,{method,headers,body,cache:'no-store',redirect:'error',credentials:'same-origin',signal:controller.signal});
        const blob=await readBlob(response,controller.signal);
        return {status:response.status,statusText:response.statusText,ok:response.ok,headers:response.headers,blob,ms:performance.now()-started,mock:false};
    } catch(error) {
        if(timedOut) throw new Error('请求超时；写入可能已被设备接收，请查看设备状态。');
        throw error;
    } finally { clearTimeout(timer);activeRequests.delete(controller);signal?.removeEventListener('abort',onAbort); }
}
export async function jsonRequest(path,options={}) {
    const result=await request(path,options),text=await result.blob.text();
    if(!result.ok) throw new Error(`HTTP ${result.status} · ${text.slice(0,300)}`);
    try { return JSON.parse(text); } catch { throw new Error('设备响应不是JSON。'); }
}
export const postJSON=(path,body)=>jsonRequest(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
export function cancelRequests() { for(const controller of activeRequests) controller.abort(); }
export function mockResult(template) {
    const started=performance.now();let data;
    try { data=JSON.parse(template); } catch { throw new Error('Mock模板需要有效JSON。'); }
    if(!data || !Number.isInteger(data.status) || data.status<200 || data.status>599 || !('body' in data))
        throw new Error('Mock模板需要status（200–599）、headers、body。');
    const headers=parseHeaders(JSON.stringify(data.headers||{}));
    if(!headers.has('Content-Type')) headers.set('Content-Type','application/json');
    const text=typeof data.body==='string'?data.body:JSON.stringify(data.body);
    return {status:data.status,statusText:'Mock',ok:data.status<400,headers,blob:new Blob([text],{type:headers.get('Content-Type')}),ms:performance.now()-started,mock:true};
}
export const formatJSON=value=>JSON.stringify(value,null,2);

// One in-flight JPEG per socket: each JSON ACK belongs to that pending frame.
// On timeout/disconnect, close the socket and never automatically resend.
export function createFrameSender() {
    let socket=null,pending=null;
    function complete(error,ack) {
        if(!pending)return;
        const operation=pending;pending=null;clearTimeout(operation.timer);
        if(error)operation.reject(error);
        else operation.resolve({...ack,ms:performance.now()-operation.sentAt});
    }
    function close(reason='连接已关闭，未收到接收确认；请自行决定是否重发。') {
        const old=socket;socket=null;
        complete(new Error(reason));
        if(old){old.onopen=old.onmessage=old.onerror=old.onclose=null;old.close();}
    }
    function transmit() {
        if(!pending||pending.sent||socket?.readyState!==WebSocket.OPEN)return;
        const operation=pending;clearTimeout(operation.timer);
        try {
            operation.sentAt=performance.now();socket.send(operation.blob);operation.sent=true;
            operation.timer=setTimeout(()=>close('未收到接收确认；图片可能已送达，请自行决定是否重发。'),8000);
        } catch(error){close(error.message);}
    }
    function connect() {
        if(socket?.readyState===WebSocket.OPEN){transmit();return;}
        if(socket?.readyState===WebSocket.CONNECTING)return;
        const ws=new WebSocket(wsURL('frames'));socket=ws;
        ws.onopen=()=>{if(socket===ws)transmit();};
        ws.onmessage=({data})=>{
            if(socket!==ws||!pending?.sent)return;
            let ack;
            try {ack=JSON.parse(data);} catch {close('收到无法识别的回执，接收状态未确认。');return;}
            if(typeof ack?.error==='string'){complete(new Error(ack.error));return;}
            if(!Number.isInteger(ack?.accepted)||ack.accepted<0){close('回执缺少图片编号，接收状态未确认。');return;}
            complete(null,ack);
        };
        ws.onerror=()=>{if(socket===ws)close(pending?.sent?'图片连接中断，接收状态未确认。':'无法连接图片推送接口。');};
        ws.onclose=()=>{if(socket===ws){socket=null;complete(new Error('图片连接已断开，接收状态未确认。'));}};
    }
    return {
        send(blob) {
            if(pending)return Promise.reject(new Error('上一张图片还在等待回执。'));
            return new Promise((resolve,reject)=>{
                pending={blob,resolve,reject,sent:false,sentAt:0,timer:setTimeout(()=>close('图片接口连接超时，尚未发送。'),5000)};
                try {connect();} catch(error){close(error.message);}
            });
        },
        close
    };
}

export function createRequestScope() {
    const controllers=new Set();let generation=0;
    async function scopedRequest(path,options={}) {
        const controller=new AbortController(),current=generation;
        const abort=()=>controller.abort();controllers.add(controller);
        if(options.signal?.aborted)controller.abort();options.signal?.addEventListener('abort',abort,{once:true});
        try {
            const result=await request(path,{...options,signal:controller.signal});
            if(current!==generation)throw new DOMException('Aborted','AbortError');return result;
        } finally{controllers.delete(controller);options.signal?.removeEventListener('abort',abort);}
    }
    async function scopedJSON(path,options={}) {
        const current=generation,result=await scopedRequest(path,options),text=await result.blob.text();
        if(current!==generation)throw new DOMException('Aborted','AbortError');
        if(!result.ok)throw new Error(`HTTP ${result.status} · ${text.slice(0,300)}`);
        try{return JSON.parse(text);}catch{throw new Error('设备响应不是JSON。');}
    }
    return {request:scopedRequest,jsonRequest:scopedJSON,
        postJSON:(path,body)=>scopedJSON(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}),
        cancel(){generation++;for(const controller of controllers)controller.abort();},get generation(){return generation;}};
}

export function wsURL(channel) {
    const url=new URL(location.href);url.protocol=location.protocol==='https:'?'wss:':'ws:';
    if(channel!=='sensors'&&channel!=='frames')throw new Error('Unknown WS channel');
    url.pathname=channel==='sensors'?'/ws/sensors':'/ws/frames';
    if(channel==='sensors')url.port='81';url.search=url.hash='';return url.href;
}
// Read-only consumers share a connection. The manual WS workbench never uses
// this object and owns its own subscription and editable request history.
export function createSensorStream({onSnapshot,onState}) {
    const consumers=new Set();let socket=null,retry=null,watch=null,enabled=true;
    const wanted=()=>enabled&&consumers.size>0&&!document.hidden;
    function close(){clearTimeout(retry);clearTimeout(watch);retry=watch=null;const ws=socket;socket=null;if(ws){ws.onopen=ws.onmessage=ws.onerror=ws.onclose=null;ws.close();}}
    function connect(){
        if(!wanted()||socket)return;
        clearTimeout(retry);onState('连接 WS…');
        let ws;try{ws=new WebSocket(wsURL('sensors'));}catch{onState('连接失败');retry=setTimeout(connect,1500);return;}
        socket=ws;
        const arm=()=>{clearTimeout(watch);watch=setTimeout(()=>{if(socket===ws){onState('数据中断，重连中');ws.close();}},5000);};
        arm();ws.onopen=()=>{if(socket===ws){onState('WS 等待数据');arm();}};
        ws.onmessage=({data})=>{
            if(socket!==ws||!wanted())return;
            try{const value=JSON.parse(data);if(!value||value.type!=='sensors')return;arm();onSnapshot(value);}
            catch{onState('数据格式异常');}
        };
        ws.onerror=()=>{if(socket===ws)onState('WS 断开，重连中');};
        ws.onclose=()=>{if(socket!==ws)return;socket=null;clearTimeout(watch);onState('WS 断开，重连中');if(wanted())retry=setTimeout(connect,1500);};
    }
    return {setConsumer(name,active){if(active)consumers.add(name);else consumers.delete(name);if(wanted())connect();else close();},
        setEnabled(value){enabled=value;if(wanted())connect();else close();},hasLive:()=>socket?.readyState===WebSocket.OPEN,
        dispose(){consumers.clear();close();}};
}
