const state={busy:false};
document.querySelectorAll("[data-endpoint]").forEach(btn=>btn.addEventListener("click",async()=>{
  if(state.busy)return; state.busy=true; const out=btn.parentElement.querySelector(".result"); out.textContent="运行中";
  try{const res=await fetch(btn.dataset.endpoint,{method:btn.dataset.endpoint.includes("export")?"GET":"POST",headers:{"content-type":"application/json"},body:btn.dataset.endpoint.includes("export")?null:"{}"});out.textContent=await res.text()}catch(e){out.textContent="请求失败，请重试"}finally{state.busy=false}
}));
document.querySelector("#refresh")?.addEventListener("click",()=>location.reload());
