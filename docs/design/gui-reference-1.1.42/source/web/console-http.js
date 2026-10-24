import {presets,deviceURL,parseHeaders,mockResult,formatJSON,createRequestScope} from '/console-api.js';
import {$,asset,message,copyText} from '/console-ui.js';
export function createHTTPFeature({getImage,invalidateHistory}) {
const scope=createRequestScope(),{request}=scope;
const state={preset:null,executing:false,responseText:null};
function renderCollection() {
    const select=$('http-preset');select.disabled=state.executing;
    if(!select.options.length) {
        for(const [title,method] of [['查看','GET'],['发送 / 控制','POST']]) {
            const group=document.createElement('optgroup');group.label=title;
            for(const p of presets.filter(p=>p.method===method)){const option=document.createElement('option');option.value=p.id;option.textContent=`${p.title} · ${p.method} ${p.path}`;group.append(option);}
            select.append(group);
        }
        const custom=document.createElement('option');custom.value='custom';custom.textContent='自定义请求';select.append(custom);
    }
    select.value=state.preset?.id||presets[0].id;
}
const customPreset={id:'custom',title:'自定义请求',method:'GET',path:'/api/status',kind:'none',headers:{},mock:{status:200,headers:{'Content-Type':'application/json'},body:{message:'编辑这里的Mock数据'}}};
$('http-preset').onchange=()=>loadPreset(presets.find(p=>p.id===$('http-preset').value)||customPreset);
function clearResponse() {
    asset('response',null);state.responseText=null;$('response-content').replaceChildren();$('response-content').textContent='等待请求';
    $('response-meta').className='badge subtle';$('response-meta').textContent='尚未执行';$('copy-response').disabled=true;$('download-response').hidden=true;$('response-headers-detail').hidden=true;
}
function bodyFields() {
    const kind=$('http-body-kind').value;$('http-body').hidden=kind!=='json'&&kind!=='text';$('http-image-note').hidden=kind!=='image';$('http-file-field').hidden=kind!=='file';
}
function targetChanged() {
    const mock=$('http-target').value==='mock';$('mock-params').hidden=!mock;$('execute-request').textContent=mock?'运行 Mock':'执行';
    message('try-notice',mock?'本地Mock：只返回模板内容，不访问设备。':'真实设备：仅点击执行才发送请求。');
}
function loadPreset(p) {
    if(state.executing)return;
    state.preset=p;
    $('http-method').value=p.method;$('http-path').value=p.path;$('http-headers').value=formatJSON(p.headers||{});
    $('http-body-kind').value=p.kind||'none';$('http-body').value=p.body==null?'':typeof p.body==='string'?p.body:formatJSON(p.body);$('http-file').value='';
    $('mock-body').value=formatJSON(p.mock||{status:200,headers:{'Content-Type':'application/json'},body:{message:'Mock response'}});
    $('request-params').open=false;$('mock-params').open=false;$('response-headers-detail').open=false;
    bodyFields();targetChanged();clearResponse();renderCollection();
}
$('http-body-kind').onchange=bodyFields;$('http-target').onchange=targetChanged;
$('reset-request').onclick=()=>loadPreset(state.preset);
function setExecuting(executing) {
    state.executing=executing;
    for(const id of ['http-preset','execute-request','reset-request','http-method','http-path','http-target','http-headers','http-body-kind','http-body','http-file','mock-body'])$(id).disabled=executing;
    renderCollection();
}
function requestBody(headers,mock) {
    const kind=$('http-body-kind').value;
    if(kind==='none')return undefined;
    if(['GET','HEAD'].includes($('http-method').value))throw new Error('GET请求不能带Body，请选择“无请求体”。');
    if(kind==='json') {
        let data;try {data=JSON.parse($('http-body').value);}catch{throw new Error('Body需要有效JSON。');}
        if(!headers.has('Content-Type'))headers.set('Content-Type','application/json');return JSON.stringify(data);
    }
    if(kind==='text'){if(!headers.has('Content-Type'))headers.set('Content-Type','text/plain;charset=utf-8');return $('http-body').value;}
    if(kind==='image') {
        if(!getImage()){if(mock)return undefined;throw new Error('先到“推送内容”准备一张图片。');}
        if(!headers.has('Content-Type'))headers.set('Content-Type','image/jpeg');return getImage().blob;
    }
    const file=$('http-file').files[0];if(!file){if(mock)return undefined;throw new Error('先选择请求文件。');}
    if(file.size>4*1024*1024)throw new Error('调试文件请控制在4 MiB以内。');
    if(!headers.has('Content-Type'))headers.set('Content-Type',file.type||'application/octet-stream');return file;
}
async function renderResponse(result) {
    const generation=scope.generation;
    const box=$('response-content');box.replaceChildren();const type=(result.headers.get('Content-Type')||'').toLowerCase();
    const url=asset('response',result.blob);$('download-response').href=url;$('download-response').hidden=false;
    const ext=type.includes('json')?'json':type.includes('bmp')?'bmp':type.includes('jpeg')?'jpg':type.includes('wav')?'wav':'bin';$('download-response').download=`response.${ext}`;
    $('response-meta').className=`badge${result.mock?' mock':result.ok?'':' offline'}`;
    $('response-meta').textContent=`${result.mock?'本地Mock · ':''}${result.status} · ${result.ms.toFixed(0)} ms · ${(result.blob.size/1024).toFixed(1)} KiB`;
    const headers=Object.fromEntries(result.headers.entries());$('response-headers').textContent=formatJSON(headers);$('response-headers-detail').hidden=false;
    if(type.startsWith('image/')) {
        const image=document.createElement('img');image.src=url;image.alt='HTTP响应图片';box.append(image);state.responseText=null;
    } else if(type.startsWith('audio/')) {
        const audio=document.createElement('audio');audio.src=url;audio.controls=true;audio.preload='none';box.append(audio);state.responseText=null;
    } else {
        let text;
        if(type.includes('json')||type.startsWith('text/')||type.includes('xml')) {
            text=await result.blob.text();try{text=formatJSON(JSON.parse(text));}catch{/* Preserve non-JSON text responses. */}
        } else {
            const bytes=new Uint8Array(await result.blob.slice(0,256).arrayBuffer());text=`二进制响应 · ${result.blob.size} 字节\n下载响应以获取完整内容。\n\n${Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join(' ')}`;
        }
        if(generation!==scope.generation)return;
        state.responseText=text;const pre=document.createElement('pre');pre.textContent=text;box.append(pre);
    }
    $('copy-response').disabled=state.responseText==null;
}
$('execute-request').onclick=async()=>{
    if(state.executing)return;
    try {
        // Build and capture editable values before disabling the form.
        const path=$('http-path').value.trim(),method=$('http-method').value,mock=$('http-target').value==='mock';deviceURL(path);
        const headers=parseHeaders($('http-headers').value),body=requestBody(headers,mock),template=$('mock-body').value;
        clearResponse();setExecuting(true);message('try-notice',mock?'正在运行本地Mock…':'正在等待设备响应…');
        const result=mock?mockResult(template):await request(path,{method,headers,body,timeout:15000});await renderResponse(result);
        message('try-notice',result.mock?'本地Mock完成，未访问设备。':result.ok?'请求完成。':'设备返回错误，请查看响应。',!result.ok);
        if(!mock&&result.ok&&method!=='GET')invalidateHistory();
    }catch(e){message('try-notice',e.name==='AbortError'?'请求已中止，写入状态需以设备为准。':e.message,true);}
    finally{setExecuting(false);}
};
$('copy-response').onclick=()=>copyText(state.responseText);

function leave(){scope.cancel();}
renderCollection();loadPreset(presets[0]);
return {enter(){renderCollection();},leave,suspend:leave,resume(){renderCollection();},dispose(){leave();clearResponse();setExecuting(false);},isExecuting:()=>state.executing};
}
