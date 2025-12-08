document.addEventListener('DOMContentLoaded', function() {
    
    const backButton = document.getElementById('back-button');
    const tabLinks = document.querySelectorAll('.tab-link:not(.logout-btn)');
    const tabContents = document.querySelectorAll('.tab-content');
    const profileForm = document.getElementById('profile-form');
    const toast = document.getElementById('toast');
    
    
    const mainAvatar = document.getElementById('main-avatar');
    const avatarUpload = document.getElementById('avatar-upload');

    
    const editButton = document.getElementById('edit-button');
    const saveButton = document.getElementById('save-button');
    const cancelButton = document.getElementById('cancel-button');
    
    
    const viewFields = document.querySelectorAll('.profile-view-field');
    const editFields = document.querySelectorAll('.profile-edit-field');

    
    let originalValues = {};

    // Initialize to view mode (not editing)
    toggleEditMode(false);

    function toggleEditMode(isEditing) {
        viewFields.forEach(field => field.classList.toggle('hidden', isEditing));
        editFields.forEach(field => field.classList.toggle('hidden', !isEditing));

        editButton.classList.toggle('hidden', isEditing);
        saveButton.classList.toggle('hidden', !isEditing);
        cancelButton.classList.toggle('hidden', !isEditing);
    }

    function enterEditMode() {
        
        originalValues = {};
        
        editFields.forEach(input => {
            const fieldName = input.name || input.id;
            
            
            const label = input.previousElementSibling;
            let viewField = null;
            
            if (label && label.tagName === 'LABEL') {
                
                viewField = label.nextElementSibling;
                if (viewField && viewField.classList.contains('profile-view-field')) {
                    
                    if (input.tagName === 'SELECT') {
                        const currentText = viewField.textContent.trim();
                        if (currentText !== 'Not set') {
                            
                            for (let option of input.options) {
                                if (option.text === currentText || option.value === currentText) {
                                    input.value = option.value;
                                    break;
                                }
                            }
                        }
                    } else {
                        
                        const value = viewField.dataset.value || viewField.textContent.trim();
                        if (value !== 'Not set') {
                            input.value = value;
                        }
                    }
                    originalValues[fieldName] = input.value;
                }
            }
        });
        
        toggleEditMode(true);
    }

    function exitEditMode(saveChanges) {
        if (saveChanges) {
            
            editFields.forEach(input => {
                const label = input.previousElementSibling;
                
                if (label && label.tagName === 'LABEL') {
                    const viewField = label.nextElementSibling;
                    
                    if (viewField && viewField.classList.contains('profile-view-field')) {
                        let displayValue = input.value;
                        
                        
                        if (input.tagName === 'SELECT') {
                            const selectedOption = input.options[input.selectedIndex];
                            displayValue = selectedOption ? selectedOption.text : input.value;
                        }
                        
                        
                        viewField.textContent = displayValue || 'Not set';
                        viewField.dataset.value = input.value;
                    }
                }
            });
            
            
            const fullNameInput = document.querySelector('input[name="first_name"]');
            const lastNameInput = document.querySelector('input[name="last_name"]');
            const emailInput = document.querySelector('input[name="email"]');
            

            
            const toast = document.getElementById('toast');
            toast.style.display = 'block';
            toast.classList.add('show');
            toast.classList.remove('hide');

            setTimeout(() => {
                toast.classList.add('hide');
                toast.classList.remove('show');
                setTimeout(() => {
                    toast.style.display = 'none';
                }, 300);
            }, 3000);
        } else {
            
            editFields.forEach(input => {
                const fieldName = input.name || input.id;
                if (originalValues.hasOwnProperty(fieldName)) {
                    input.value = originalValues[fieldName];
                }
            });
        }
        
        toggleEditMode(false);
    }
    
    

    
    backButton.addEventListener('click', function (e) {
        e.preventDefault();
        window.history.back();
    });

    
    tabLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const tabId = this.dataset.tab;
            if (!tabId) return;

            tabLinks.forEach(l => l.classList.remove('active-tab', 'bg-teal-100'));
            this.classList.add('active-tab', 'bg-teal-100');

            tabContents.forEach(content => {
                content.classList.remove('active');
                if (content.id === tabId) content.classList.add('active');
            });
        });
    });

    

    
    editButton.addEventListener('click', enterEditMode);
    cancelButton.addEventListener('click', () => exitEditMode(false));
    
    
    saveButton.addEventListener('click', function(e) {
        e.preventDefault();
        
        profileForm.submit();
    });

    
    avatarUpload.addEventListener('change', function(event) {
        const file = event.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                const imageUrl = e.target.result;
                mainAvatar.src = imageUrl;
            };
            reader.readAsDataURL(file);
        }
    });
    
    viewFields.forEach(field => {
        if (!field.dataset.value) {
            const text = field.textContent.trim();
            field.dataset.value = text !== 'Not set' ? text : '';
        }
    });

    // Barangay data
    const barangays = {
        "Cebu City": [
            "Adlaon", "Agsungot", "Apas", "Babag", "Bacayan", "Banilad", "Basilica", "Binaliw", "Bonbon", "Budlaan",
            "Buhisan", "Bulacao", "Busay", "Camputhaw", "Capitol Site", "Carreta", "Central", "Cogon", "Day-as", "Duljo",
            "Ermita", "Guba", "Hipodromo", "Kalubihan", "Kalunasan", "Kamagayan", "Kasambagan", "Lahug", "Lorega", "Lusaran",
            "Mabini", "Mabolo", "Malubog", "Mambaling", "Pahina Central", "Pahina San Nicolas", "Pamutan", "Pardo", "Poblacion Pardo", "Pulangbato",
            "Sambag I", "Sambag II", "San Antonio", "San Jose", "San Nicolas Proper", "San Roque", "Santa Cruz", "Sawang Calero", "Sinsin", "Sirao",
            "T. Padilla", "Talamban", "Taptap", "Tejero", "Tinago", "Tisa", "Toong", "Zapatera"
        ],
        "Mandaue City": [
            "Alang-alang", "Bakilid", "Banilad", "Basak", "Cabancalan", "Cambaro", "Canduman", "Casuntingan", "Centro", "Cubacub",
            "Guizo", "Ibabao-Estancia", "Jagobiao", "Labogon", "Looc", "Mabolo", "Mantuyong", "Opao", "Pakna-an", "Pagsabungan",
            "Subangdaku", "Tabok", "Tawason", "Tingub", "Tipolo", "Umapad"
        ],
        "Lapu-Lapu City": [
            "Agus", "Babag", "Bankal", "Baring", "Basak", "Buaya", "Calawisan", "Canjulao", "Caubian", "Caw-oy",
            "Cawhagan", "Cañas", "Coong", "Gun-ob", "Ibo", "Looc", "Mactan", "Maribago", "Marigondon", "Pajac",
            "Pajo", "Pangan-an", "Poblacion", "Punta Engaño", "Pusok", "Sabang", "San Vicente", "Santa Rosa", "Subabasbas", "Talima",
            "Tingo", "Tungasan"
        ],
        "Talisay City": [
            "Biasong", "Bulacao", "Cadulawan", "Camp 4", "Candulawan", "Cangag", "Dumlog", "Jaclupan", "Lawaan", "Linao",
            "Maghaway", "Manipis", "Mohon", "Poblacion", "Poog", "San Isidro", "San Roque", "Tabunok", "Tangke", "Tapul"
        ],
        "Consolacion": [
            "Cabangahan", "Cansaga", "Casili", "Danglag", "Garing", "Jugan", "Lamac", "Lanipga", "Nangka", "Panas",
            "Panoypoy", "Pitogo", "Poblacion Occidental", "Poblacion Oriental", "Pulangbato", "Sacsac", "Tayud"
        ],
        "Cordova": [
            "Alegria", "Bangbang", "Buagsong", "Catarman", "Cogon", "Dapitan", "Day-as", "Gabi", "Gilutongan", "Ibabao",
            "Pilipog", "Poblacion", "San Miguel"
        ],
        "Compostela": [
            "Bagalnga", "Basak", "Buluang", "Cabadiangan", "Cambayog", "Canamucan", "Cogon", "Dapdap", "Estaca", "Lupa",
            "Magay", "Mulao", "Panangban", "Poblacion", "Tag-ubi", "Tamiao", "Tandoc"
        ],
        "Daanbantayan": [
            "Agujo", "Bagay", "Bakhawan", "Bateria", "Bitoon", "Calape", "Carnaza", "Daanbantayan", "Guinsay", "Lambug",
            "Logon", "Malbago", "Malingin", "Maya", "Pajo", "Paypay", "Poblacion", "Suba", "Talisay", "Tapilon",
            "Tinubdan"
        ]
    };

    // City and Barangay functionality
    const citySelect = document.getElementById('city');
    const purokSelect = document.getElementById('purok');

    function updateBarangayOptions(selectedCity) {
        purokSelect.innerHTML = '<option value="">Select Barangay</option>';

        if (selectedCity && barangays[selectedCity]) {
            barangays[selectedCity].forEach(barangay => {
                const option = document.createElement('option');
                option.value = barangay;
                option.textContent = barangay;
                purokSelect.appendChild(option);
            });
            purokSelect.disabled = false;
        } else {
            purokSelect.innerHTML = '<option value="">Select Barangay (Choose city first)</option>';
            purokSelect.disabled = true;
        }
    }

    if (citySelect && purokSelect) {
        citySelect.addEventListener('change', function() {
            const selectedCity = this.value;
            updateBarangayOptions(selectedCity);

            // Reset barangay selection when city changes
            purokSelect.value = '';
        });

        // Initialize barangay options based on current city value
        updateBarangayOptions(citySelect.value);
    }

    // Contact number validation
    const contactInput = document.getElementById('contact_number');
    if (contactInput) {
        contactInput.addEventListener('input', function(e) {
            // Remove any non-digit characters
            let value = this.value.replace(/\D/g, '');

            // Ensure it doesn't start with 0 and limit to 10 digits
            if (value.startsWith('0')) {
                value = value.substring(1);
            }
            if (value.length > 10) {
                value = value.substring(0, 10);
            }

            this.value = value;
        });

        // Prevent entering 0 at the beginning
        contactInput.addEventListener('keydown', function(e) {
            if (this.selectionStart === 0 && e.key === '0') {
                e.preventDefault();
            }
        });
    }

    const style = document.createElement('style');
    style.innerHTML = `
        .toggle-checkbox:checked { right: 0; border-color: #0D9488; }
        .toggle-checkbox:checked + .toggle-label { background-color: #0D9488; }
    `;
    document.head.appendChild(style);
});