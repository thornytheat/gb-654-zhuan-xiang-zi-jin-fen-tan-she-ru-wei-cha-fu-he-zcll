document.querySelectorAll(".ledger td").forEach(cell=>{cell.tabIndex=0;cell.title=cell.textContent.trim()});
document.addEventListener("keydown",event=>{if(event.key==="Escape")document.activeElement?.blur()});
