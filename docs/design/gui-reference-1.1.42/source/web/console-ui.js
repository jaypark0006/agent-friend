export const $=id=>document.getElementById(id);
const urls=new Map();
export function asset(key,blob) {
    const old=urls.get(key); if(old) URL.revokeObjectURL(old);
    urls.delete(key);
    if(!blob)return '';
    const url=URL.createObjectURL(blob);urls.set(key,url);return url;
}
let toastTimer;
export function toast(message) { $('toast').textContent=message;$('toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').hidden=true,3800); }
export function message(id,text,error=false) { const node=$(id);node.textContent=text;node.classList.toggle('error',error);node.classList.remove('success'); }
export function number(value,digits=0) { return typeof value==='number'&&Number.isFinite(value)?value.toFixed(digits):'—'; }
export function vector(value) { return Array.isArray(value)?value.map(v=>number(v,2)).join(' / '):'—'; }
export async function copyText(text) {
    if(text==null)return;
    try {if(navigator.clipboard?.writeText){await navigator.clipboard.writeText(text);toast('已复制');return;}}catch{/* HTTP LAN pages may lack Clipboard API. */}
    const input=document.createElement('textarea');input.value=text;input.style.cssText='position:fixed;left:-9999px';document.body.append(input);input.select();
    let copied=false;try{copied=document.execCommand('copy');}finally{input.remove();}
    toast(copied?'已复制':'浏览器未允许复制，请手动选择内容。');
}

export function releaseAssets(){for(const key of [...urls.keys()])asset(key,null);clearTimeout(toastTimer);}
