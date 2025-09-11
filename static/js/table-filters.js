(function(){
  function debounce(fn, delay){
    let t; return function(){clearTimeout(t); t=setTimeout(fn, delay);};
  }
  function bind(root){
    const form = root.getElementById ? root : document.getElementById('filters');
    if(!form) return;
    const inputs = form.querySelectorAll('[data-inline-filter]');
    inputs.forEach(el=>{
      if(el._ifBound) return; el._ifBound=true;
      if(el.tagName === 'INPUT'){
        el.addEventListener('input', debounce(()=>{ window.htmx && window.htmx.trigger(form,'submit');},300));
      }else{
        el.addEventListener('change', ()=>{ window.htmx && window.htmx.trigger(form,'submit');});
      }
    });
  }
  document.addEventListener('DOMContentLoaded', ()=>bind(document));
  document.body.addEventListener('htmx:afterSwap', (e)=>bind(e.target));
})();
