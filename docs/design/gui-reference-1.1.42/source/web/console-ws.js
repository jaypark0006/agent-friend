import {wsURL} from '/console-api.js';
// A manual WS workbench. Only the connection checkbox opens a socket; pushes
// are never retried. Endpoint addresses always come from the current device.
export function createWSWorkbench({$,getImage,message}) {
    const sets={sensors:[
        ['订阅传感器',{type:'subscribe',topic:'sensors'}],['取消订阅',{type:'unsubscribe',topic:'sensors'}],
        ['读取一次',{type:'get',topic:'sensors'}],['Ping',{type:'ping'}]
    ],frames:[
        ['推送文字',{type:'text',text:'你好，这是一条 WS 消息。',font_size:32,align:'left'}],
        ['查看设备状态',{type:'get',topic:'status'}],['查看传感器',{type:'get',topic:'sensors'}],
        ['图片页',{type:'view',page:'image'}],['文字页',{type:'view',page:'text'}],['摄像头页',{type:'view',page:'camera'}],
        ['自动切换开',{type:'config',auto_switch:true}],['自动切换关',{type:'config',auto_switch:false}],['Ping',{type:'ping'}]
    ]};
    let socket=null,wanted=false,active=false,counter=0,sent=0,received=0,bytes=0,flushTimer=null,exportURL=null;
    const history=[],pending=[];const LIMIT=100,BUDGET=256*1024;
    function url(){return wsURL($('ws-channel').value);}
    function controls(label) {
        $('ws-url').value=url();$('ws-connect').checked=wanted;
        if(label)$('ws-state').textContent=label;
        const open=socket?.readyState===WebSocket.OPEN;
        $('ws-send').disabled=!open;$('ws-send-image').disabled=!open||$('ws-channel').value!=='frames'||!getImage();
        $('ws-count').textContent=`↑ ${sent} / ↓ ${received} · 保留 ${history.length}/${LIMIT}`;
    }
    function flush() {
        clearTimeout(flushTimer);flushTimer=null;
        const list=$('ws-history'),fragment=document.createDocumentFragment();
        if(history.length && list.firstElementChild?.classList.contains('ws-empty'))list.replaceChildren();
        for(const item of pending.splice(0)) {
            if(!history.includes(item))continue;
            const row=document.createElement('details');row.className=`ws-event ${item.direction}`;row.dataset.entry=item.key;
            const summary=document.createElement('summary'),arrow=document.createElement('span'),time=document.createElement('time'),brief=document.createElement('span');
            arrow.textContent=item.direction==='send'?'↑ 发出':item.direction==='receive'?'↓ 收到':'· 连接';
            time.textContent=item.time;brief.textContent=item.label;summary.append(arrow,time,brief);
            const pre=document.createElement('pre');pre.textContent=item.body;row.append(summary,pre);fragment.append(row);
        }
        list.append(fragment);
        const keys=new Set(history.map(item=>String(item.key)));
        for(const row of [...list.children])if(row.dataset.entry&&!keys.has(row.dataset.entry))row.remove();
        if($('ws-follow').checked)list.scrollTop=list.scrollHeight;
        controls();
    }
    function record(direction,body,label) {
        const item={key:++counter,direction,body,label,time:new Date().toLocaleTimeString('zh-CN',{hour12:false})};
        history.push(item);pending.push(item);bytes+=body.length;
        while(history.length>LIMIT||bytes>BUDGET){const old=history.shift();bytes-=old.body.length;}
        if(!flushTimer)flushTimer=setTimeout(flush,120);
    }
    function close(label='已断开') {
        const old=socket;socket=null;
        if(old){old.onopen=old.onmessage=old.onerror=old.onclose=null;old.close();record('system',label,label);}
        controls(label);
    }
    function transmit(value) {
        if(socket?.readyState!==WebSocket.OPEN)throw new Error('请先开启连接');
        if(socket.bufferedAmount>256*1024)throw new Error('连接正在发送，请稍后再发');
        if(!Object.hasOwn(value,'request_id'))value.request_id=`web-${++counter}`;
        const wire=JSON.stringify(value),limit=$('ws-channel').value==='sensors'?512:8192;
        if(new TextEncoder().encode(wire).length>limit)throw new Error(`本通道JSON上限 ${limit} 字节`);
        socket.send(wire);sent++;record('send',JSON.stringify(value,null,2),`${value.type||'JSON'} · ${value.request_id}`);
        message('ws-notice','已发出，设备响应请看下方历史');controls();
    }
    function connect() {
        if(!wanted||!active||document.hidden||socket)return;
        try {
            const ws=new WebSocket(url());socket=ws;ws.binaryType='arraybuffer';controls('连接中');
            ws.onopen=()=>{
                if(socket!==ws)return;controls('已连接');record('system',url(),'已连接');
                if($('ws-channel').value==='sensors')transmit({type:'subscribe',topic:'sensors'});
            };
            ws.onmessage=({data})=>{
                if(socket!==ws)return;received++;controls();
                if(!$('ws-record').checked)return;
                if(typeof data!=='string'){record('receive',`二进制 ${data.byteLength} 字节`,'二进制响应');return;}
                if(data.length>64*1024){record('receive',data.slice(0,64*1024)+'\n[超出64KiB，截断历史]',`收到 ${data.length} 字符`);return;}
                let body=data,label;
                try {
                    const value=JSON.parse(data);body=JSON.stringify(value,null,2);
                    label=value.type==='sensors'?'传感器更新':value.error?`错误 · ${value.error}`:Number.isInteger(value.accepted)?`已接收 #${value.accepted}`:`${value.command||value.type||'JSON'}${value.ok===true?' · 成功':''}`;
                    if(value.request_id!=null)label+=` · ${value.request_id}`;
                } catch {label='文本响应';}
                record('receive',body,label);
            };
            ws.onerror=()=>{if(socket===ws)message('ws-notice','连接异常；已发送消息可能送达，请查看历史，不会自动重发',true);};
            ws.onclose=({code})=>{if(socket!==ws)return;socket=null;record('system',`关闭代码 ${code}`,`连接关闭 ${code}`);wanted=false;controls('已断开');};
        } catch(error){socket=null;wanted=false;controls('连接失败');message('ws-notice',error.message,true);}
    }
    function examples() {
        const select=$('ws-preset');select.replaceChildren();
        sets[$('ws-channel').value].forEach(([label],index)=>{const option=document.createElement('option');option.value=index;option.textContent=label;select.append(option);});
        load();controls();
    }
    function load(){const value=sets[$('ws-channel').value][Number($('ws-preset').value)]?.[1];$('ws-json').value=JSON.stringify(value,null,2);}
    $('ws-preset').onchange=load;$('ws-reset').onclick=load;
    $('ws-channel').onchange=()=>{close('切换通道');examples();connect();};
    $('ws-connect').onchange=()=>{wanted=$('ws-connect').checked;if(wanted)connect();else close();};
    $('ws-send').onclick=()=>{
        try{const value=JSON.parse($('ws-json').value);if(!value||typeof value!=='object'||Array.isArray(value))throw new Error('请输入JSON对象');transmit(value);}
        catch(error){message('ws-notice',error.message,true);}
    };
    $('ws-json').onkeydown=event=>{if((event.metaKey||event.ctrlKey)&&event.key==='Enter'){event.preventDefault();$('ws-send').click();}};
    $('ws-send-image').onclick=()=>{
        try {
            const image=getImage();if(!image||$('ws-channel').value!=='frames'||socket?.readyState!==WebSocket.OPEN)throw new Error('请先在推送内容页准备图片，再连接推送通道');
            if(socket.bufferedAmount>0)throw new Error('当前有数据正在发送，请稍后');
            socket.send(image.blob);sent++;record('send',`JPEG ${image.blob.size} 字节 · 480×480`,'二进制图片已发出');controls();
        } catch(error){message('ws-notice',error.message,true);}
    };
    $('ws-clear').onclick=()=>{history.length=pending.length=0;bytes=0;sent=received=0;$('ws-history').replaceChildren();controls();};
    $('ws-export').onclick=()=>{
        if(exportURL)URL.revokeObjectURL(exportURL);exportURL=URL.createObjectURL(new Blob([JSON.stringify(history,null,2)],{type:'application/json'}));
        const link=document.createElement('a');link.href=exportURL;link.download='mosaico-ws-history.json';link.click();
    };
    examples();controls('未连接');
    const feature={enter(){active=true;if(pending.length)flush();controls();connect();},leave(){active=false;close('离开页面，连接暂停');},suspend(){close('页面隐藏，连接暂停');},dispose(){wanted=false;active=false;close();clearTimeout(flushTimer);flushTimer=null;if(exportURL)URL.revokeObjectURL(exportURL);}};
    feature.resume=()=>feature.enter();return feature;
}
