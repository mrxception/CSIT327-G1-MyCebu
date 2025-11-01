document.addEventListener("DOMContentLoaded",function(){
  var qs=(s,r=document)=>r.querySelector(s);
  var qsa=(s,r=document)=>Array.from(r.querySelectorAll(s));
  function v(x){return (x||"").trim().toLowerCase()}

  var input=qs('#q-services');
  var cards=qsa('#grid-services .svc-card');
  var empty=qs('#empty-services');

  function apply(){
    var q=v(input&&input.value);
    var shown=0;
    cards.forEach(card=>{
      var t=card.dataset.title||"";
      var d=card.dataset.desc||"";
      var show=!q||t.includes(q)||d.includes(q);
      card.style.display=show?"":"none";
      if(show) shown++;
    });
    if(empty) empty.style.display=shown?"none":"block";
  }

  if(input){input.addEventListener('input',apply)}
  apply();

  qsa('.steps .step-item').forEach(item=>{
    item.addEventListener('click',function(){
      item.classList.toggle('active');
    });
  });
});
