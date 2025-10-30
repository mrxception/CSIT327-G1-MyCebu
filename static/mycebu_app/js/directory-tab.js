(function () {
    const qs = (s, r = document) => r.querySelector(s);
    const qsa = (s, r = document) => Array.from(r.querySelectorAll(s));
    const nav = qs('.tabs--bar');
    const url = new URL(window.location);
    const initialTab = url.searchParams.get('t') || 'officials';
    function moveIndicator(btn) { if (!nav || !btn) return; const br = btn.getBoundingClientRect(); const nr = nav.getBoundingClientRect(); const x = (br.left - nr.left) + nav.scrollLeft; nav.style.setProperty('--tab-x', `${x}px`); nav.style.setProperty('--tab-w', `${br.width}px`); }
    function currentActiveBtn() { return nav?.querySelector('.tab-btn.is-active') || nav?.querySelector('.tab-btn'); }
    function setTab(id) { qsa('.tab-btn').forEach(b => { const on = b.dataset.tab === id; b.classList.toggle('is-active', on); b.setAttribute('aria-selected', on ? 'true' : 'false'); }); qsa('.tab-panel').forEach(p => { p.style.display = (p.dataset.panel === id ? 'block' : 'none'); }); url.searchParams.set('t', id); history.replaceState(null, '', url); requestAnimationFrame(() => moveIndicator(currentActiveBtn())); }
    qsa('.tab-btn').forEach(b => b.addEventListener('click', () => setTab(b.dataset.tab)));
    setTab(initialTab);
    window.addEventListener('resize', () => moveIndicator(currentActiveBtn()));
    nav && nav.addEventListener('scroll', () => moveIndicator(currentActiveBtn()));
    requestAnimationFrame(() => moveIndicator(currentActiveBtn()));
    function initUiSelect(root, onChange) { if (!root) return; const trigger = qs('[data-trigger]', root); const menu = qs('[data-menu]', root); const native = qs('select.native-select', root); function reflect() { const opt = native.options[native.selectedIndex]; trigger.textContent = opt ? opt.textContent : ''; onChange && onChange(native.value); } function open() { root.setAttribute('aria-expanded', 'true'); } function close() { root.setAttribute('aria-expanded', 'false'); } trigger.addEventListener('click', e => { e.stopPropagation(); const isOpen = root.getAttribute('aria-expanded') === 'true'; isOpen ? close() : open(); }); document.addEventListener('click', () => close()); qsa('.ui-select__option', menu).forEach(li => { li.addEventListener('click', e => { e.stopPropagation(); const val = li.getAttribute('data-value'); native.value = val; qsa('.ui-select__option', menu).forEach(x => x.classList.toggle('is-selected', x === li)); reflect(); close(); }); }); native.addEventListener('change', reflect); reflect(); }
    const oGrid = qs('#grid-officials');
    const oQ = qs('#q-officials');
    const oPos = qs('#pos-officials');
    const oDist = qs('#dist-officials');
    function filterOfficials() { const q = (oQ?.value || '').toLowerCase(); const pos = (oPos?.value || 'all').toLowerCase(); const dist = (oDist?.value || 'all').toLowerCase(); qsa('.card', oGrid).forEach(card => { const name = (card.dataset.name || '').toLowerCase(); const position = (card.dataset.position || '').toLowerCase(); const office = (card.dataset.office || '').toLowerCase(); const district = (card.dataset.district || '').toLowerCase(); const textMatch = !q || name.includes(q) || position.includes(q) || office.includes(q); const posMatch = (pos === 'all') || position === pos; const distMatch = (dist === 'all') || district === dist; card.style.display = (textMatch && posMatch && distMatch) ? '' : 'none'; }); }
    oQ && oQ.addEventListener('input', filterOfficials);
    oPos && oPos.addEventListener('change', filterOfficials);
    oDist && oDist.addEventListener('change', filterOfficials);
    initUiSelect(qs('.ui-select[data-name="position"]'), () => filterOfficials());
    initUiSelect(qs('.ui-select[data-name="district"]'), () => filterOfficials());
    filterOfficials();
    const offGrid = qs('#grid-offices');
    const offQ = qs('#q-offices');
    function filterOffices() { const q = (offQ?.value || '').toLowerCase(); qsa('.card', offGrid).forEach(card => { const name = (card.dataset.name || '').toLowerCase(); const head = (card.dataset.head || '').toLowerCase(); card.style.display = (!q || name.includes(q) || head.includes(q)) ? '' : 'none'; }); }
    offQ && offQ.addEventListener('input', filterOffices);
    filterOffices();
    const hGrid = qs('#grid-hotlines');
    const hQ = qs('#q-hotlines');
    function filterHotlines() { const q = (hQ?.value || '').toLowerCase(); qsa('.card', hGrid).forEach(card => { const service = (card.dataset.service || '').toLowerCase(); const numbers = (card.dataset.numbers || '').toLowerCase(); card.style.display = (!q || service.includes(q) || numbers.includes(q)) ? '' : 'none'; }); }
    hQ && hQ.addEventListener('input', filterHotlines);
    filterHotlines();
})();
