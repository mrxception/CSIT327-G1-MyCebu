document.addEventListener("DOMContentLoaded",function(){
  document.querySelectorAll(".ui-select").forEach(function(root){
    var native = root.querySelector(".native-select");
    var trigger = root.querySelector("[data-trigger]");
    var menu = root.querySelector("[data-menu]");
    var options = Array.from(menu.querySelectorAll(".ui-select__option"));
    var value = native.value || (native.querySelector("option[selected]")||{}).value || (native.querySelector("option")||{}).value || "";
    function labelFor(v){var o=Array.from(native.options).find(function(op){return op.value===v});return o?o.textContent:"";}
    function setSelected(v){value=v;native.value=v;trigger.textContent=labelFor(v);options.forEach(function(li){li.classList.toggle("is-selected",li.getAttribute("data-value")===v)})}
    function open(){root.setAttribute("aria-expanded","true")}
    function close(){root.setAttribute("aria-expanded","false")}
    setSelected(value);
    trigger.addEventListener("click",function(){root.getAttribute("aria-expanded")==="true"?close():open()});
    options.forEach(function(li){
      li.addEventListener("click",function(){
        setSelected(li.getAttribute("data-value"));
        close();
      });
    });
    document.addEventListener("click",function(e){if(!root.contains(e.target))close()});
    trigger.addEventListener("keydown",function(e){
      var i=options.findIndex(function(li){return li.classList.contains("is-selected")});
      if(e.key==="ArrowDown"){e.preventDefault();open();var ni=Math.min(options.length-1,i+1);options[ni].focus?options[ni].focus():null;setSelected(options[ni].getAttribute("data-value"))}
      if(e.key==="ArrowUp"){e.preventDefault();open();var pi=Math.max(0,i-1);options[pi].focus?options[pi].focus():null;setSelected(options[pi].getAttribute("data-value"))}
      if(e.key==="Enter"||e.key===" "){e.preventDefault();root.getAttribute("aria-expanded")==="true"?close():open()}
      if(e.key==="Escape"){e.preventDefault();close()}
    });
  });
});
