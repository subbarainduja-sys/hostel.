function toast(msg,type){const c=document.getElementById('toasts');const d=document.createElement('div');
d.className='toast show text-bg-'+(type||'primary');d.innerHTML='<div class="toast-body">'+msg+'</div>';
c.appendChild(d);setTimeout(()=>d.remove(),4000)}
document.querySelectorAll('[data-flash]').forEach(e=>toast(e.dataset.flash,e.dataset.cat));
