// Browser page previews only; actual device page owns the camera lifecycle.
// Browser previews are optional;
// neither raw camera downloads nor browser JPEG round-trips drive the LCD.
import {createRequestScope} from '/console-api.js';
export function createCameraFeature({$,message,isActive,hasLive}) {
    const scope=createRequestScope(),{request,jsonRequest,postJSON}=scope;
    let available=false,loaded=false,busy=false,previewBusy=false,timer=null,pollTimer=null,controller=null,generation=0;
    let pageEntered=false,visit=0,controlVersion=0,handledVersion=0,desired=null;
    const number=value=>typeof value==='number'&&Number.isFinite(value)?value.toFixed(1):'—';
    function render(camera) {
        const value=camera?.render;if(!value)return;
        available=true;
        if(isActive()&&!loaded&&!busy) {
            $('camera-render-fps').value=value.target_fps||30;
            const select=$('camera-render-block'),block=String(value.block_size||2);
            if(!Array.from(select.options).some(option=>option.value===block)){const option=document.createElement('option');option.value=block;option.textContent=`${block} px`;select.append(option);}
            select.value=block;loaded=true;
        }
        const status=({running:'运行中',pending:'等待摄像头',disabled:'已停止',error:'异常',stale:'画面暂未更新'})[value.state]||value.state;
        $('camera-render-state').textContent=status;
        $('camera-render-state').className=`badge${value.state==='error'?' offline':value.enabled?'':' subtle'}`;
        $('camera-render-capture-fps').textContent=`${number(camera.capture_fps)} FPS`;
        $('camera-render-actual-fps').textContent=`${number(value.render_fps)} / ${number(value.display_fps)} FPS`;
        $('camera-render-count').textContent=`${value.generated??0} / ${value.displayed??0}`;
        $('camera-render-ms').textContent=`${number(value.process_ms)} ms`;
        if(value.error&&value.error!=='ESP_OK')message('camera-render-result',value.error,true);
        if(!busy){$('camera-render-start').disabled=!camera.ready;$('camera-render-stop').disabled=!value.enabled;}
    }
    async function read() {
        try {const value=await jsonRequest('/api/camera',{timeout:4500});if(isActive()){if(!value.render)throw new Error('当前固件尚未提供色块功能');render(value);}}
        catch(error){if(isActive()){message('camera-render-result',error.message,true);if(!available){$('camera-render-start').disabled=true;$('camera-render-stop').disabled=true;}}}
    }
    function poll() {
        clearTimeout(pollTimer);if(!isActive())return;
        const job=hasLive()?Promise.resolve():read();
        job.finally(()=>{if(isActive())pollTimer=setTimeout(poll,2000);});
    }
    async function applyControl() {
        if(busy)return;
        busy=true;$('camera-render-start').disabled=$('camera-render-stop').disabled=true;
        try {
            while(desired && handledVersion!==controlVersion) {
                const version=controlVersion,body=desired;
                try {
                    const value=await postJSON('/api/camera/render',body);
                    if(version===controlVersion){render({ready:true,render:value});message('camera-render-result',body.enabled?'设备摄像头页请求已接收':'设备退出摄像头页请求已接收');}
                } catch(error) {
                    if(version===controlVersion)message('camera-render-result',error.message,true);
                }
                handledVersion=version;
            }
        } finally {busy=false;if(isActive())await read();}
    }
    function configure(enabled) {
        if(enabled&&!available)return;
        const fps=Number($('camera-render-fps').value),block=Number($('camera-render-block').value);
        if(enabled&&(!Number.isInteger(fps)||fps<1||fps>30||!Number.isInteger(block)||block<1||block>64)) {
            message('camera-render-result','目标帧率需要是1–30整数，色块大小为1–64',true);return;
        }
        desired=enabled?{enabled:true,target_fps:fps,block_size:block}:{enabled:false};
        controlVersion++;
        message('camera-render-result',enabled?'正在切换设备到摄像头页…':'正在退出设备摄像头页…');
        void applyControl();
    }
    async function preview() {
        if(!isActive()||!$('camera-render-preview').checked||previewBusy)return;
        previewBusy=true;const current=generation,abort=new AbortController();controller=abort;
        try {
            const response=await request('/api/camera/render/frame',{signal:abort.signal,timeout:5000});
            if(!response.ok)throw new Error(response.status===503?'等待本地色块画面':`预览 HTTP ${response.status}`);
            if(response.headers.get('X-Pixel-Format')!=='RGB565_BE'||response.blob.size!==256*256*2)throw new Error('预览帧格式不匹配');
            const bytes=new Uint8Array(await response.blob.arrayBuffer());if(current!==generation||!isActive())return;
            const canvas=$('camera-render-canvas'),ctx=canvas.getContext('2d');if(!ctx)throw new Error('浏览器不支持画布');
            const image=ctx.createImageData(256,256);
            for(let i=0,j=0;i<bytes.length;i+=2,j+=4){const rgb=(bytes[i]<<8)|bytes[i+1],r=(rgb>>11)&31,g=(rgb>>5)&63,b=rgb&31;image.data[j]=(r<<3)|(r>>2);image.data[j+1]=(g<<2)|(g>>4);image.data[j+2]=(b<<3)|(b>>2);image.data[j+3]=255;}
            ctx.putImageData(image,0,0);message('camera-render-preview-state',`网页预览 · 帧 #${response.headers.get('X-Sample-Sequence')||'—'}`);
        } catch(error){if(error.name!=='AbortError'&&current===generation)message('camera-render-preview-state',error.message,true);}
        finally {previewBusy=false;if(controller===abort)controller=null;if(current===generation&&isActive()&&$('camera-render-preview').checked)timer=setTimeout(preview,200);}
    }
    function stopPreview() {generation++;clearTimeout(timer);controller?.abort();controller=null;}
    $('camera-render-preview').onchange=()=>{stopPreview();if($('camera-render-preview').checked){if(previewBusy)timer=setTimeout(preview,250);else preview();}};
    $('camera-render-start').onclick=()=>configure(true);$('camera-render-stop').onclick=()=>configure(false);
    $('camera-render-start').disabled=$('camera-render-stop').disabled=true;
    const feature={
        render,
        enter(){
            if(pageEntered)return;
            pageEntered=true;const current=++visit;
            loaded=false;clearTimeout(pollTimer);$('camera-render-preview').checked=true;
            read().finally(()=>{
                if(current!==visit||!isActive())return;
                pollTimer=setTimeout(poll,2000);
                if(!previewBusy)preview();else timer=setTimeout(preview,250);
            });
        },
        leave(){
            if(!pageEntered)return;
            pageEntered=false;visit++;scope.cancel();desired=null;handledVersion=++controlVersion;
            clearTimeout(pollTimer);stopPreview();$('camera-render-preview').checked=false;
        }
    };
    feature.suspend=()=>feature.leave();feature.resume=()=>feature.enter();feature.dispose=()=>feature.leave();
    return feature;
}
