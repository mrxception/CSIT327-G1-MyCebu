document.addEventListener('DOMContentLoaded', function () {
    const cebuBarangays = {
        "Cebu City": ["Adlaon", "Apas", "Babag", "Bacayan", "Banilad", "Basak Pardo", "Basak San Nicolas", "Bonbon", "Budlaan", "Buhisan", "Bulacao", "Busay", "Calamba", "Cambinocot", "Capitol Site", "Carreta", "Cogon Pardo", "Cogon Ramos", "Day-as", "Duljo Fatima", "Ermita", "Guadalupe", "Guba", "Hipodromo", "Inayawan", "Kalubihan", "Kalunasan", "Kamagayan", "Kamputhaw", "Kasambagan", "Kinasang-an Pardo", "Labangon", "Lahug", "Lorega San Miguel", "Lusaran", "Luz", "Mabini", "Mambaling", "Pahina Central", "Pahina San Nicolas", "Pamutan", "Pari-an", "Paril", "Pasil", "Pit-os", "Poblacion Pardo", "Pulangbato", "Pung-ol Sibugay", "Punta Princesa", "Quiot", "Sambag I", "Sambag II", "San Antonio", "San Jose", "San Nicolas Proper", "San Roque", "Santa Cruz", "Santo Niño", "Sapangdaku", "Sawang Calero", "Sinsin", "Sirao", "Suba", "Sudlon I", "Sudlon II", "T. Padilla", "Tabunan", "Tagbao", "Talamban", "Taptap", "Tejero", "Tinago", "Tisa", "Toong", "Zapatera"],
        "Mandaue City": ["Alang-alang", "Bakilid", "Banilad", "Basak", "Cabancalan", "Cambaro", "Canduman", "Casanting", "Centro", "Cubacub", "Guizo", "Ibabao-Estancia", "Jagobiao", "Labogon", "Looc", "Maguikay", "Mantuyong", "Opao", "Paknaan", "Pagsabungan", "Subangdaku", "Tabok", "Tawason", "Tingub", "Tipolo", "Umapad"],
        "Lapu-Lapu City": ["Agus", "Babag", "Bankal", "Baring", "Basak", "Buaya", "Calawisan", "Canjulao", "Caw-oy", "Caubian", "Caohagan", "Gun-ob", "Ibo", "Looc", "Mactan", "Maribago", "Marigondon", "Pajac", "Pajo", "Pangan-an", "Poblacion", "Punta Engaño", "Pusok", "Sabang", "San Vicente", "Santa Rosa", "Subabasbas", "Talima", "Tingo", "Tungasan"],
        "Talisay City": ["Biasong", "Bulacao", "Cadulawan", "Camp IV", "Cansojong", "Dumlog", "Jaclupan", "Lagtang", "Lawaan I", "Lawaan II", "Linao", "Maghaway", "Manipis", "Mohon", "Poblacion", "Pooc", "San Isidro", "San Roque", "Tabunok", "Tangke", "Tapul", "Tubod"],
        "Consolacion": ["Cabangahan", "Cansaga", "Casili", "Danglag", "Garing", "Jugan", "Lamac", "Lanipga", "Nangka", "Panas", "Panoypoy", "Pitogo", "Poblacion Occidental", "Poblacion Oriental", "Polog", "Pulpogan", "Sacsac", "Tayud", "Tolo-tolo", "Tugbongan"],
        "Cordova": ["Alegria", "Bangbang", "Buagsong", "Catarman", "Cogon", "Dapitan", "Day-as", "Gabi", "Gilutongan", "Ibabao", "Pilipog", "Poblacion", "San Miguel"],
        "Other": ["Other"]
    };

    const citySelect = document.getElementById('city');
    const purokSelect = document.getElementById('purok');
    const editBtn = document.getElementById('edit-button');
    const saveBtn = document.getElementById('save-button');
    const cancelBtn = document.getElementById('cancel-button');
    const form = document.getElementById('profile-form');
    const viewFields = document.querySelectorAll('.profile-view-field');
    const editFields = document.querySelectorAll('.profile-edit-field');
    const avatarUpload = document.getElementById('avatar-upload');
    const mainAvatar = document.getElementById('main-avatar');

    function populateBarangays(city, selectedPurok = null) {
        purokSelect.innerHTML = '<option value="">Loading barangays...</option>';
        purokSelect.innerHTML = ''; // Clear

        if (!city || !cebuBarangays[city]) {
            const opt = document.createElement('option');
            opt.value = '';
            opt.textContent = 'Select city first';
            purokSelect.appendChild(opt);
            purokSelect.disabled = true;
            return;
        }

        const barangays = cebuBarangays[city] || [];
        barangays.forEach(brgy => {
            const opt = document.createElement('option');
            opt.value = brgy;
            opt.textContent = brgy;
            if (brgy === selectedPurok) opt.selected = true;
            purokSelect.appendChild(opt);
        });
        purokSelect.disabled = false;
    }

    // Restore saved values on page load
    const savedCity = document.querySelector('[data-value="{{ user.city|default:\'\' }}"]')?.dataset.value ||
                     document.querySelector('span[data-value]').dataset.value || // fallback
                     '{{ user.city|default:"" }}';

    const savedPurok = document.querySelector('span[data-value="{{ user.purok|default:\'\' }}"]')?.dataset.value || '{{ user.purok|default:"" }}';

    if (citySelect && savedCity) {
        citySelect.value = savedCity;
        populateBarangays(savedCity, savedPurok);
    }

    citySelect?.addEventListener('change', function() {
        populateBarangays(this.value);
    });

    function toggleEditMode(editing) {
        viewFields.forEach(el => el.style.display = editing ? 'none' : 'inline-block');
        editFields.forEach(el => el.style.display = editing ? 'block' : 'none');
        editBtn.style.display = editing ? 'none' : 'inline-flex';
        saveBtn.style.display = editing ? 'inline-flex' : 'none';
        cancelBtn.style.display = editing ? 'inline-flex' : 'none';

        if (editing && citySelect.value) {
            purokSelect.disabled = false;
        }
    }

    toggleEditMode(false);

    editBtn?.addEventListener('click', () => toggleEditMode(true));
    cancelBtn?.addEventListener('click', () => location.reload());

    avatarUpload?.addEventListener('change', function() {
        if (this.files[0]) {
            const reader = new FileReader();
            reader.onload = e => mainAvatar.src = e.target.result;
            reader.readAsDataURL(this.files[0]);
            toggleEditMode(true);
        }
    });

    // MOST IMPORTANT: Enable disabled fields BEFORE submit
    form?.addEventListener('submit', function(e) {
        // Remove disabled so values are sent
        purokSelect.disabled = false;
        citySelect.disabled = false;
    });

    // Auto-fade messages
    document.querySelectorAll('.fixed.top-5').forEach(msg => {
        setTimeout(() => msg.style.opacity = '0', 3000);
        setTimeout(() => msg.remove(), 3500);
    });
});