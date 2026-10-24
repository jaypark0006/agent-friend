import {$,message,releaseAssets} from '/console-ui.js';
import {cancelRequests} from '/console-api.js';
import {createViewFeature} from '/console-view.js';
import {createSendFeature} from '/console-send.js';
import {createHTTPFeature} from '/console-http.js';
import {createCameraFeature} from '/console-camera.js';
import {createWSWorkbench} from '/console-ws.js';
import {createLifecycle} from '/console-lifecycle.js';

const runtime={route:'view',alive:true},features={};
features.view=createViewFeature({runtime,onCamera:value=>features.camera?.render(value),isExecuting:()=>features.try?.isExecuting()||false});
features.send=createSendFeature({runtime,invalidateHistory:()=>features.view.invalidateHistory()});
features.try=createHTTPFeature({getImage:()=>features.send.getImage(),invalidateHistory:()=>features.view.invalidateHistory()});
features.camera=createCameraFeature({
    $,message,
    isActive:()=>runtime.alive&&!document.hidden&&(runtime.route==='camera'||(runtime.route==='devtools'&&!document.querySelector('[data-devpanel="camera"]')?.hidden)),
    hasLive:()=>features.view.hasLive()
});
features.ws=createWSWorkbench({$,getImage:()=>features.send.getImage(),message});
const lifecycle=createLifecycle(features,runtime);

const routeNames={
    view:'实时大屏',
    pipeline:'AI 流水线',
    send:'内容与历史',
    interact:'外设与传感器',
    devtools:'开发者工具'
};
$('host').textContent=location.host;$('sidebar-host').textContent=location.host;
$('ws-address').textContent=`ws://${location.hostname}:81/ws/sensors`;

const themeToggle=$('theme-toggle');
function applyTheme(t){
    if(t==='dark'){document.documentElement.setAttribute('data-theme','dark');if(themeToggle)themeToggle.textContent='☀️';}
    else if(t==='light'){document.documentElement.setAttribute('data-theme','light');if(themeToggle)themeToggle.textContent='🌙';}
    else{document.documentElement.removeAttribute('data-theme');const d=window.matchMedia('(prefers-color-scheme:dark)').matches;if(themeToggle)themeToggle.textContent=d?'☀️':'🌙';}
}
const savedTheme=localStorage.getItem('mosaico-theme');
applyTheme(savedTheme||'auto');
if(themeToggle){
    themeToggle.onclick=()=>{
        const cur=document.documentElement.getAttribute('data-theme');
        const isDark=cur?cur==='dark':window.matchMedia('(prefers-color-scheme:dark)').matches;
        const next=isDark?'light':'dark';
        localStorage.setItem('mosaico-theme',next);applyTheme(next);
    };
}

export function switchDevTab(tab) {
    const valid=['http','ws','camera'];
    const current=valid.includes(tab)?tab:'http';
    document.querySelectorAll('[data-devtab]').forEach(btn=>{
        btn.classList.toggle('selected',btn.dataset.devtab===current);
    });
    document.querySelectorAll('[data-devpanel]').forEach(panel=>{
        panel.hidden=(panel.dataset.devpanel!==current);
    });
    if(current==='camera'){
        features.camera?.enter?.();
    }
}
document.querySelectorAll('[data-devtab]').forEach(btn=>{
    btn.addEventListener('click',()=>switchDevTab(btn.dataset.devtab));
});

function navigate() {
    let raw=location.hash.slice(1);
    let devtab='http',name=raw;
    if(['try','http','ws','camera'].includes(raw)){
        devtab=(raw==='try'?'http':raw);
        name='devtools';
    }else{
        name=({home:'view',settings:'view',status:'view',files:'send',history:'send',sensors:'interact'})[raw]||raw;
    }
    const route=Object.hasOwn(routeNames,name)?name:'view';
    document.querySelectorAll('[data-screen]').forEach(n=>n.hidden=(n.dataset.screen!==route));
    document.querySelectorAll('[data-nav]').forEach(n=>{
        const active=(n.dataset.nav===route);
        n.classList.toggle('active',active);
        if(active)n.setAttribute('aria-current','page');
        else n.removeAttribute('aria-current');
    });
    $('breadcrumb').textContent=`控制台 / ${routeNames[route]}`;
    if(route==='devtools'){
        switchDevTab(devtab);
    }
    lifecycle.enter(route);
}

window.addEventListener('hashchange',navigate);
document.addEventListener('visibilitychange',()=>{
    if(document.hidden){
        lifecycle.suspend();
        if(!['view','interact','camera','devtools'].includes(runtime.route))features.view.suspend();
    } else {
        lifecycle.resume();features.view.poll();
    }
});
window.addEventListener('pagehide',()=>{runtime.alive=false;lifecycle.dispose();cancelRequests();releaseAssets();});
window.addEventListener('pageshow',event=>{if(!event.persisted)return;runtime.alive=true;navigate();features.view.poll();});
navigate();features.view.poll();
