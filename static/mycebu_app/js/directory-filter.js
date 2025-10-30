document.addEventListener("DOMContentLoaded",function(){
  var qs=(s,r=document)=>r.querySelector(s);
  var qsa=(s,r=document)=>Array.from(r.querySelectorAll(s));

  function closeAll(){qsa('.ui-select[aria-expanded="true"]').forEach(s=>s.setAttribute('aria-expanded','false'))}
  qsa('.ui-select').forEach(sel=>{
    var trigger=qs('[data-trigger]',sel);
    var menu=qs('[data-menu]',sel);
    var native=qs('.native-select',sel);
    if(!trigger||!menu||!native)return;
    if(native.selectedIndex>=0){trigger.textContent=native.options[native.selectedIndex].textContent}
    trigger.addEventListener('click',e=>{
      e.stopPropagation();
      var open=sel.getAttribute('aria-expanded')==='true';
      closeAll();
      sel.setAttribute('aria-expanded',open?'false':'true');
    });
    qsa('.ui-select__option',menu).forEach(opt=>{
      opt.addEventListener('click',e=>{
        e.stopPropagation();
        var value=opt.dataset.value;
        native.value=value;
        trigger.textContent=opt.textContent.trim();
        native.dispatchEvent(new Event('input',{bubbles:true}));
        native.dispatchEvent(new Event('change',{bubbles:true}));
        sel.setAttribute('aria-expanded','false');
      });
    });
  });
  document.addEventListener('click',closeAll);

  function v(x){return (x||"").trim().toLowerCase()}
  function getVal(name){
    var root=document.querySelector('.ui-select[data-name="'+name+'"]');
    var native=root?root.querySelector(".native-select"):null;
    return native?(native.value||"all"):"all";
  }
  function getOrCreateEmptyAfter(gridSel, preferExistingSel, text){
    var grid=qs(gridSel);
    if(!grid) return null;
    var existing = qs(preferExistingSel) || grid.nextElementSibling && (grid.nextElementSibling.matches('.empty, .empty-msg') ? grid.nextElementSibling : null);
    if(existing){ return existing; }
    var div=document.createElement('div');
    div.className='empty-msg';
    div.textContent=text;
    div.style.display='none';
    div.style.textAlign='center';
    div.style.color='var(--muted)';
    div.style.fontSize='1.1rem';
    div.style.marginTop='32px';
    div.style.fontWeight='500';
    grid.parentNode.insertBefore(div, grid.nextSibling);
    return div;
  }

  var officialsInput=qs('#q-officials');
  var officialsCards=qsa('#grid-officials .card');
  var emptyOfficials=getOrCreateEmptyAfter('#grid-officials', '#grid-officials + .empty, #grid-officials + .empty-msg', 'No Officials Found');
  function applyOfficials(){
    var q=v(officialsInput&&officialsInput.value);
    var pos=v(getVal("position"));
    var dist=v(getVal("district"));
    var shown=0;
    officialsCards.forEach(card=>{
      var n=card.dataset.name||"";
      var p=card.dataset.position||"";
      var o=card.dataset.office||"";
      var d=card.dataset.district||"";
      var mq=!q||n.includes(q)||p.includes(q)||o.includes(q)||d.includes(q);
      var mp=pos==="all"||p===pos;
      var md=dist==="all"||d===dist;
      var show=mq&&mp&&md;
      card.style.display=show?"":"none";
      if(show)shown++;
    });
    if(emptyOfficials) emptyOfficials.style.display=shown?"none":"block";
  }
  if(officialsInput) officialsInput.addEventListener("input",applyOfficials);
  document.addEventListener("change",e=>{
    if(e.target.matches(".native-select")) applyOfficials();
  });
  applyOfficials();

  var officeInput=qs('#q-offices');
  var officeCards=qsa('#grid-offices .card');
  var emptyOffices=getOrCreateEmptyAfter('#grid-offices', '#grid-offices + .empty, #grid-offices + .empty-msg', 'No Offices Found');
  function applyOffices(){
    var q=v(officeInput&&officeInput.value);
    var shown=0;
    officeCards.forEach(card=>{
      var n=card.dataset.name||"";
      var h=card.dataset.head||"";
      var show=!q||n.includes(q)||h.includes(q);
      card.style.display=show?"":"none";
      if(show) shown++;
    });
    if(emptyOffices) emptyOffices.style.display=shown?"none":"block";
  }
  if(officeInput) officeInput.addEventListener("input",applyOffices);
  applyOffices();

  var hotlineInput=qs('#q-hotlines');
  var hotlineCards=qsa('#grid-hotlines .card');
  var emptyHotlines=getOrCreateEmptyAfter('#grid-hotlines', '#grid-hotlines + .empty, #grid-hotlines + .empty-msg', 'No Hotlines Found');
  function applyHotlines(){
    var q=v(hotlineInput&&hotlineInput.value);
    var shown=0;
    hotlineCards.forEach(card=>{
      var s=card.dataset.service||"";
      var n=card.dataset.numbers||"";
      var show=!q||s.includes(q)||n.includes(q);
      card.style.display=show?"":"none";
      if(show) shown++;
    });
    if(emptyHotlines) emptyHotlines.style.display=shown?"none":"block";
  }
  if(hotlineInput) hotlineInput.addEventListener("input",applyHotlines);
  applyHotlines();
});
