// shared: load data.json, site hotkeys (h=horyz.io, l=lab, n=notion)
const SITES={h:"https://horyz.io/",l:"https://lab.horyz.io/"};
addEventListener("keydown",e=>{if(e.target.tagName==="TEXTAREA"||e.metaKey||e.ctrlKey)return;const u=SITES[e.key];if(u)open(u,"_blank")});
const load=()=>fetch("data.json?"+Date.now()).then(r=>r.json());
const pct=(a,b)=>b?Math.round(a/b*100):0;
