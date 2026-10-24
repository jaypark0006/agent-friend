import {prepareImage} from '/image-upload.js';
import {createFrameSender,createRequestScope} from '/console-api.js';
import {$,asset,toast,message} from '/console-ui.js';
export function createSendFeature({runtime,invalidateHistory}) {
const scope=createRequestScope(),{postJSON}=scope;
const frameSender=createFrameSender(),receipts=[];
const state={sourceImage:null,sourceLabel:'',prepared:null,prepareGeneration:0,uploading:false,get route(){return runtime.route}};
async function prepareSelected() {
    const generation=++state.prepareGeneration,source=state.sourceImage;state.prepared=null;$('send-image').disabled=true;
    $('upload-preview').hidden=true;$('upload-preview').removeAttribute('src');$('upload-empty').hidden=false;$('download-image').hidden=true;asset('upload',null);
    if(!source)return;
    message('image-result','正在转换图片…');
    try {
        const image=await prepareImage(source,{fit:$('image-fit').value});if(generation!==state.prepareGeneration)return;
        state.prepared=image;const url=asset('upload',image.blob);$('upload-preview').src=url;$('upload-preview').hidden=false;$('upload-empty').hidden=true;
        $('download-image').href=url;$('download-image').hidden=false;
        $('image-details').textContent=`${state.sourceLabel} · ${image.sourceWidth}×${image.sourceHeight} → 480×480 · ${(image.blob.size/1024).toFixed(1)} KiB`;
        message('image-result','图片已准备好。');$('send-image').disabled=false;
    }catch(e){if(generation===state.prepareGeneration)message('image-result',e.message,true);}
}
function selectImage(blob,label) {
    if(state.uploading){toast('图片正在发送，请稍后再更换。');return;}
    state.sourceImage=blob;state.sourceLabel=label;prepareSelected();
}
$('file').onchange=()=>{const file=$('file').files[0];if(file)selectImage(file,file.name);};
$('image-fit').onchange=prepareSelected;
const dropZone=$('paste-zone');dropZone.onclick=e=>{if(e.target.tagName!=='LABEL')dropZone.focus();};
dropZone.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();if(!state.uploading)$('file').click();}});
for(const name of ['dragenter','dragover'])dropZone.addEventListener(name,e=>{e.preventDefault();dropZone.classList.add('dragging');});
for(const name of ['dragleave','drop'])dropZone.addEventListener(name,e=>{e.preventDefault();dropZone.classList.remove('dragging');});
dropZone.addEventListener('drop',e=>{const file=e.dataTransfer.files[0];if(file&&(/image\//.test(file.type)||/\.(heic|heif)$/i.test(file.name)))selectImage(file,file.name);else toast('请拖入一张图片。');});
document.addEventListener('paste',event=>{
    // Only the send entry accepts image paste. Do not disrupt HTTP editors.
    if(state.route!=='send')return;
    const clipboard=event.clipboardData;let image=null;
    for(const item of clipboard?.items||[]){if(item.kind==='file'&&item.type.startsWith('image/')){image=item.getAsFile();if(image)break;}}
    if(!image)image=Array.from(clipboard?.files||[]).find(f=>f.type.startsWith('image/'));
    if(!image)return;event.preventDefault();$('file').value='';selectImage(image,'粘贴的截图');
});
function received(kind,label,ack,error) {
    receipts.unshift({kind,label,id:ack?.accepted,error,time:new Date().toLocaleTimeString('zh-CN',{hour12:false})});
    receipts.length=Math.min(receipts.length,8);const list=$('send-receipts');list.replaceChildren();
    for(const item of receipts) {
        const row=document.createElement('div');row.className='receipt-row';const time=document.createElement('time');time.textContent=item.time;
        const type=document.createElement('span');type.textContent=item.kind==='image'?'图片':'文字';
        const label=document.createElement('span');label.textContent=item.label;
        const status=document.createElement('span');status.className=item.error?'error':'success';status.textContent=item.error?'未确认':`已接收 #${item.id}`;if(item.error)status.title=item.error;
        row.append(time,type,label,status);list.append(row);
    }
    invalidateHistory();
}
$('send-image').onclick=async()=>{
    if(!state.prepared||state.uploading)return;state.uploading=true;const image=state.prepared,label=state.sourceLabel;
    $('send-image').disabled=true;$('file').disabled=true;$('image-fit').disabled=true;message('image-result','发送中，等待回执…');
    try {const ack=await frameSender.send(image.blob);message('image-result',`已接收 #${ack.accepted} · ${ack.ms.toFixed(0)} ms`);$('image-result').classList.add('success');received('image',label,ack);}
    catch(error){message('image-result',error.message,true);received('image',label,null,error.message);}
    finally{state.uploading=false;$('send-image').disabled=!state.prepared;$('file').disabled=false;$('image-fit').disabled=false;}
};
function updateTextPreview() {
    const text=$('text-input').value,size=Number($('font-size').value),bytes=new TextEncoder().encode(text).length;
    $('text-counter').textContent=`${bytes} / 1024 字节`;$('text-counter').classList.toggle('error',bytes>1024);
    $('font-label').textContent=`${size} px`;$('text-preview-content').textContent=text||'你的文字会显示在这里';
    $('text-preview-content').style.fontSize=`${size}px`;$('text-preview-content').style.textAlign=$('text-align').value;
    $('text-preview-time').textContent=$('text-time').value||'设备时间';
}
for(const id of ['text-input','font-size','text-align','text-time'])$(id).addEventListener('input',updateTextPreview);
$('text-sample').onclick=()=>{$('text-input').value='任务完成，等待下一步。\n这是一条推送消息。';updateTextPreview();};
$('send-text').onclick=async()=>{
    if($('send-text').disabled)return;
    const text=$('text-input').value,size=Number($('font-size').value),time=$('text-time').value;
    if(!text.trim()){message('text-result','先输入一些文字。',true);return;}
    if(new TextEncoder().encode(text).length>1024){message('text-result','文字超过1024字节。',true);return;}
    if(!Number.isInteger(size)||size<16||size>64){message('text-result','字号需要在16–64之间。',true);return;}
    const values={text,font_size:size,align:$('text-align').value};if(time)values.time=time;
    $('send-text').disabled=true;message('text-result','正在推送…');
    try{const r=await postJSON('/api/text',values);if(!Number.isInteger(r.accepted))throw new Error('响应缺少消息编号，接收状态未确认');message('text-result',`已接收 #${r.accepted}`);$('text-result').classList.add('success');received('text',text.slice(0,80),r);}
    catch(e){message('text-result',e.message,true);received('text',text.slice(0,80),null,e.message);}
    finally{$('send-text').disabled=false;}
};
$('text-input').addEventListener('keydown',event=>{if(!event.isComposing&&event.key==='Enter'&&(event.metaKey||event.ctrlKey)){event.preventDefault();$('send-text').click();}});

function enter(){updateTextPreview();if(state.sourceImage&&!state.prepared)prepareSelected();}
function leave(){state.prepareGeneration++;scope.cancel();frameSender.close();}
return {
    enter,leave,suspend:leave,resume:enter,
    dispose(){leave();state.prepared=null;asset('upload',null);$('upload-preview').removeAttribute('src');$('upload-preview').hidden=true;$('upload-empty').hidden=false;$('download-image').hidden=true;$('send-image').disabled=true;},
    getImage:()=>state.prepared
};
}
