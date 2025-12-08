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

  var complaints=[
    {id:"GOV-2025-0001",date:"2025-01-15",status:"In Progress",category:"Public Infrastructure & Utilities",subcategory:"Roads & Transport",subject:"Pothole on Main Street",location:"Main Street near Barangay Hall",description:"Large pothole causing traffic buildup and potential accidents.",anonymous:true,name:"",email:"",phone:"",files:[]},
    {id:"GOV-2025-0002",date:"2025-01-10",status:"Resolved",category:"Government Service & Governance",subcategory:"Personnel Misconduct",subject:"Rude staff at front desk",location:"Municipal Hall Front Desk",description:"Staff member spoke rudely to a senior citizen while processing documents.",anonymous:false,name:"Juan Dela Cruz",email:"juan@example.com",phone:"+63 912 345 6789",files:[]}
  ]

  var catSel=$('#cmp-category'),subSel=$('#cmp-subcategory'),wrapSub=$('#wrap-subcategory')
  var catRoot=document.querySelector('.ui-select[data-name="cmp-category"]')
  var subRoot=document.querySelector('.ui-select[data-name="cmp-subcategory"]')
  var cmpList=$('#cmp-list'),cmpDetail=$('#cmp-detail')

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

  function updateSubCategories(){
    subSel.innerHTML=''
    if(!catSel.value){
      wrapSub.style.display='none'
      if(uiSub)uiSub.buildMenu()
      return
    }
    var subs=categories[catSel.value]||[]
    subs.forEach(function(s){
      var o=document.createElement('option')
      o.value=s
      o.textContent=s
      subSel.appendChild(o)
    })
    if(subSel.options.length)subSel.value=subSel.options[0].value
    wrapSub.style.display=subSel.options.length?'grid':'none'
    if(uiSub)uiSub.buildMenu()
  }

  catSel.addEventListener('change',function(){
    updateSubCategories()
  })

  if(catSel.options.length){
    catSel.value=catSel.options[0].value
  }
  updateSubCategories()
  if(uiCat)uiCat.buildMenu()

  var subj=$('#cmp-subject'),subjCount=$('#cmp-subj-count')
  subj.addEventListener('input',function(){subjCount.textContent=String(subj.value.length)})

  var anon=$('#cmp-anon'),ident=$('#cmp-ident')
  anon.addEventListener('change',function(){ident.style.display=anon.checked?'none':'grid'})

  var fileInput=$('#cmp-files'),fileList=$('#cmp-filelist')
  var currentFiles=[]
  var maxBytes=10*1024*1024

  function formatSize(bytes){
    var kb=bytes/1024
    if(kb<1000)return Math.round(kb)+' KB'
    var mb=kb/1024
    return mb.toFixed(1)+' MB'
  }

  function badgeFor(status){
    var s=String(status||'').toLowerCase()
    var el=document.createElement('span')
    el.className='badge'
    el.textContent=status
    if(s==='in progress')el.classList.add('badge--warn')
    if(s==='approved'||s==='resolved'||s==='submitted')el.classList.add('badge--ok')
    return el
  }

  function renderFileList(){
    fileList.innerHTML=''
    currentFiles.forEach(function(f,i){
      var row=document.createElement('div')
      row.className='file-pill'
      var nm=document.createElement('span')
      nm.className='name'
      nm.innerHTML=f.name+' <span class="filesize">('+formatSize(f.size)+')</span>'
      var rm=document.createElement('button')
      rm.type='button'
      rm.className='file-remove'
      rm.innerHTML='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 -960 960 960" aria-hidden="true" class="icon-trash"><path d="M280-120q-33 0-56.5-23.5T200-200v-520h-40v-80h200v-40h240v40h200v80h-40v520q0 33-23.5 56.5T680-120H280Zm400-600H280v520h400v-520ZM360-280h80v-360h-80v360Zm160 0h80v-360h-80v360ZM280-720v520-520Z" fill="currentColor"/></svg><span>Remove</span>'
      rm.addEventListener('click',function(){
        currentFiles.splice(i,1)
        syncFiles()
      })
      row.appendChild(nm)
      row.appendChild(rm)
      fileList.appendChild(row)
    })
  }

  function syncFiles(){
    var dt=new DataTransfer()
    currentFiles.forEach(function(f){dt.items.add(f)})
    fileInput.files=dt.files
    renderFileList()
  }

  fileInput.addEventListener('change',function(){
    var files=Array.from(fileInput.files||[])
    if(!files.length)return
    var tooLarge=false
    files.forEach(function(f){
      if(f.size>maxBytes){
        tooLarge=true
        return
      }
      currentFiles.push(f)
    })
    if(tooLarge)alert('Each file must be 10MB or smaller.')
    syncFiles()
  })

  // function renderComplaintDetail(c){
  //   if(!cmpDetail)return
  //   var filesHtml=''
  //   if(c.files&&c.files.length){
  //     filesHtml='<div class="cmp-files">'
  //     c.files.forEach(function(f){
  //       filesHtml+='<div class="file-pill"><span class="name">'+f.name+' <span class="filesize">('+formatSize(f.size)+')</span></span></div>'
  //     })
  //     filesHtml+='</div>'
  //   }else{
  //     filesHtml='<p class="tiny muted">No attachments for this complaint.</p>'
  //   }
  //   var dateText=''
  //   if(c.date){
  //     var d=new Date(c.date)
  //     if(!isNaN(d.getTime()))dateText=d.toLocaleDateString()
  //   }
  //   cmpDetail.innerHTML=
  //     '<div class="cmp-detail-header">'+
  //       '<p class="tiny muted">'+c.id+'</p>'+
  //       '<h4 class="cmp-detail-title">'+c.subject+'</h4>'+
  //     '</div>'+
  //     '<div class="cmp-meta-grid">'+
  //       '<div><p class="tiny muted">Status</p>'+badgeFor(c.status).outerHTML+'</div>'+
  //       '<div><p class="tiny muted">Date Submitted</p><p class="strong">'+(dateText||'-')+'</p></div>'+
  //       '<div><p class="tiny muted">Category</p><p class="strong">'+c.category+'</p></div>'+
  //       '<div><p class="tiny muted">Sub-Category</p><p class="strong">'+(c.subcategory||'-')+'</p></div>'+
  //     '</div>'+
  //     '<div class="cmp-section"><p class="tiny muted">Location</p><p class="strong">'+c.location+'</p></div>'+
  //     '<div class="cmp-section"><p class="tiny muted">Description</p><p>'+c.description+'</p></div>'+
  //     '<div class="cmp-section"><p class="tiny muted">Attachments</p>'+filesHtml+'</div>'+
  //     (c.anonymous?'':'<div class="cmp-section"><p class="tiny muted">Submitted By</p><p class="strong">'+(c.name||'-')+'</p><p class="tiny muted">'+(c.email||'')+(c.phone?' • '+c.phone:'')+'</p></div>')
  // }

  // function renderComplaintsList(){
  //   if(!cmpList)return
  //   cmpList.innerHTML=''
  //   complaints.forEach(function(c){
  //     var item=document.createElement('button')
  //     item.type='button'
  //     item.className='list-item cmp-item'
  //     var left=document.createElement('div')
  //     left.innerHTML='<p class="tiny muted">'+c.id+'</p><p class="list-title">'+c.subject+'</p><p class="tiny muted">'+c.category+(c.subcategory?' • '+c.subcategory:'')+'</p>'
  //     var badge=badgeFor(c.status)
  //     item.appendChild(left)
  //     item.appendChild(badge)
  //     item.addEventListener('click',function(){renderComplaintDetail(c)})
  //     cmpList.appendChild(item)
  //   })
  //   if(complaints.length&&cmpDetail&&cmpDetail.querySelector('.cmp-detail-empty'))renderComplaintDetail(complaints[0])
  // }

  // renderComplaintsList()

  btnNew.addEventListener('click',function(){
    form.reset()
    currentFiles=[]
    fileInput.value=''
    fileList.innerHTML=''
    subjCount.textContent='0'
    wrapSub.style.display='none'
    ident.style.display=anon.checked?'none':'grid'
    form.style.display='grid'
    success.style.display='none'
    if(uiCat)uiCat.buildMenu()
    if(uiSub)uiSub.buildMenu()
    if(catSel.options.length){
      catSel.value=catSel.options[0].value
      updateSubCategories()
      if(uiCat)uiCat.buildMenu()
    }
  })
})();
