(function(){
  var $=function(q,ctx){return (ctx||document).querySelector(q)}
  var $$=function(q,ctx){return Array.from((ctx||document).querySelectorAll(q))}
  var tabs=$$('.dash-tab'),panels={services:$('#tab-services'),complaints:$('#tab-complaints')}
  tabs.forEach(function(b){b.addEventListener('click',function(){tabs.forEach(function(x){x.classList.remove('is-active')});b.classList.add('is-active');Object.values(panels).forEach(function(p){p.classList.remove('is-active')});panels[b.dataset.tab].classList.add('is-active')})})

  var subTabs=$$('.dash-subtab'),subPanels={submit:$('#sub-submit'),track:$('#sub-track')}
  subTabs.forEach(function(b){b.addEventListener('click',function(){subTabs.forEach(function(x){x.classList.remove('is-active')});b.classList.add('is-active');Object.values(subPanels).forEach(function(p){p.classList.remove('is-active')});subPanels[b.dataset.subtab].classList.add('is-active')})})

  var categories={
    "Public Infrastructure & Utilities":["Roads & Transport","Water & Sanitation","Electricity & Power"],
    "Government Service & Governance":["Personnel Misconduct","Administrative Issues","Policy/Ordinance"],
    "Health, Safety & Environment":["Health Services","Public Safety","Environmental Concerns"],
    "Other/Miscellaneous":["Website/Digital Service","Positive Feedback","Other"]
  }

  var catSel=$('#cmp-category'),subSel=$('#cmp-subcategory'),wrapSub=$('#wrap-subcategory')
  var catRoot=document.querySelector('.ui-select[data-name="cmp-category"]')
  var subRoot=document.querySelector('.ui-select[data-name="cmp-subcategory"]')

  function setupUiSelect(root){
    if(!root)return null
    var native=root.querySelector('.native-select')
    var trigger=root.querySelector('[data-trigger]')
    var menu=root.querySelector('[data-menu]')
    if(!native||!trigger||!menu)return null
    function buildMenu(){
      menu.innerHTML=''
      Array.from(native.options).forEach(function(opt){
        var li=document.createElement('li')
        li.className='ui-select__option'
        li.dataset.value=opt.value
        li.textContent=opt.textContent
        if(native.value===opt.value){li.classList.add('is-selected')}
        li.addEventListener('click',function(e){
          e.stopPropagation()
          native.value=opt.value
          trigger.textContent=opt.textContent
          native.dispatchEvent(new Event('change',{bubbles:true}))
          root.setAttribute('aria-expanded','false')
        })
        menu.appendChild(li)
      })
      var selectedOpt=native.options[native.selectedIndex]
      trigger.textContent=selectedOpt?selectedOpt.textContent:''
    }
    trigger.addEventListener('click',function(e){
      e.stopPropagation()
      var open=root.getAttribute('aria-expanded')==='true'
      document.querySelectorAll('.ui-select[aria-expanded="true"]').forEach(function(el){
        if(el!==root){el.setAttribute('aria-expanded','false')}
      })
      root.setAttribute('aria-expanded',open?'false':'true')
    })
    document.addEventListener('click',function(){
      root.setAttribute('aria-expanded','false')
    })
    native.addEventListener('change',buildMenu)
    buildMenu()
    return{buildMenu:buildMenu,native:native}
  }

  Object.keys(categories).forEach(function(k){
    var o=document.createElement('option')
    o.value=k
    o.textContent=k
    catSel.appendChild(o)
  })

  var uiCat=setupUiSelect(catRoot)
  var uiSub=setupUiSelect(subRoot)

  catSel.addEventListener('change',function(){
    subSel.innerHTML=''
    if(!catSel.value){
      wrapSub.style.display='none'
      if(uiSub)uiSub.buildMenu()
      return
    }
    categories[catSel.value].forEach(function(s){
      var o=document.createElement('option')
      o.value=s
      o.textContent=s
      subSel.appendChild(o)
    })
    wrapSub.style.display='grid'
    if(uiSub)uiSub.buildMenu()
  })

  var subj=$('#cmp-subject'),subjCount=$('#cmp-subj-count')
  subj.addEventListener('input',function(){subjCount.textContent=String(subj.value.length)})

  var anon=$('#cmp-anon'),ident=$('#cmp-ident')
  anon.addEventListener('change',function(){ident.style.display=anon.checked?'none':'grid'})

  var fileInput=$('#cmp-files'),fileList=$('#cmp-filelist')
  fileInput.addEventListener('change',function(){
    fileList.innerHTML=''
    Array.from(fileInput.files||[]).forEach(function(f,i){
      var row=document.createElement('div')
      row.className='file-pill'
      var nm=document.createElement('span')
      nm.className='name'
      nm.textContent=f.name
      var rm=document.createElement('button')
      rm.type='button'
      rm.className='btn'
      rm.textContent='Remove'
      rm.addEventListener('click',function(){
        var dt=new DataTransfer()
        Array.from(fileInput.files||[]).forEach(function(ff,idx){
          if(idx!==i)dt.items.add(ff)
        })
        fileInput.files=dt.files
        row.remove()
      })
      row.appendChild(nm)
      row.appendChild(rm)
      fileList.appendChild(row)
    })
  })

  var form=$('#form-complaint'),success=$('#cmp-success'),trkOut=$('#cmp-trk'),btnNew=$('#cmp-new')
  function required(v){return v&&String(v).trim().length>0}
  form.addEventListener('submit',function(e){
    e.preventDefault()
    var data={
      category:catSel.value,
      subcategory:subSel.value,
      subject:$('#cmp-subject').value,
      location:$('#cmp-location').value,
      description:$('#cmp-description').value,
      name:$('#cmp-name')?$('#cmp-name').value:'',
      email:$('#cmp-email')?$('#cmp-email').value:'',
      phone:$('#cmp-phone')?$('#cmp-phone').value:''
    }
    if(!required(data.category)||!required(data.subcategory)||!required(data.subject)||!required(data.location)||!required(data.description))return alert('Please fill in all required fields.')
    var year=(new Date()).getFullYear(),rnd=String(Math.floor(Math.random()*10000)).padStart(4,'0'),id='GOV-'+year+'-'+rnd
    trkOut.textContent=id
    success.style.display='grid'
    form.style.display='none'
  })

  btnNew.addEventListener('click',function(){
    form.reset()
    fileList.innerHTML=''
    subjCount.textContent='0'
    wrapSub.style.display='none'
    ident.style.display=anon.checked?'none':'grid'
    form.style.display='grid'
    success.style.display='none'
    if(uiCat)uiCat.buildMenu()
    if(uiSub)uiSub.buildMenu()
  })

  var trkForm=$('#form-track'),trkInput=$('#trk-input'),res=$('#trk-result'),fId=$('#trk-id'),fDate=$('#trk-date'),fCat=$('#trk-cat'),fSub=$('#trk-sub'),fSubj=$('#trk-subj'),fBadge=$('#trk-badge')
  function badgeFor(status){
    var s=status.toLowerCase()
    var el=document.createElement('span')
    el.className='badge'
    el.textContent=status
    if(s==='in progress')el.classList.add('badge--warn')
    if(s==='approved'||s==='resolved')el.classList.add('badge--ok')
    return el
  }
  trkForm.addEventListener('submit',function(e){
    e.preventDefault()
    var id=String(trkInput.value||'').trim()
    if(!id)return
    var mock={id:id,status:'In Progress',submissionDate:'2025-01-15',category:'Public Infrastructure & Utilities',subcategory:'Roads & Transport',subject:'Pothole on Main Street'}
    fId.textContent=mock.id
    fDate.textContent=(new Date(mock.submissionDate)).toLocaleDateString()
    fCat.textContent=mock.category
    fSub.textContent=mock.subcategory
    fSubj.textContent=mock.subject
    fBadge.innerHTML=''
    fBadge.appendChild(badgeFor(mock.status))
    res.style.display='grid'
  })
})();
