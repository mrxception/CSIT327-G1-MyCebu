document.addEventListener('DOMContentLoaded', function() {
    
    const backButton = document.getElementById('back-button');
    const tabLinks = document.querySelectorAll('.tab-link:not(.logout-btn)');
    const tabContents = document.querySelectorAll('.tab-content');
    const profileForm = document.getElementById('profile-form');
    const toast = document.getElementById('toast');
    
    
    const sidebarAvatar = document.getElementById('sidebar-avatar');
    const mainAvatar = document.getElementById('main-avatar');
    const avatarUpload = document.getElementById('avatar-upload');
    const avatarLabel = document.getElementById('avatar-label');
    const sidebarName = document.getElementById('sidebar-name');
    const sidebarEmail = document.getElementById('sidebar-email');

    
    const editButton = document.getElementById('edit-button');
    const saveButton = document.getElementById('save-button');
    const cancelButton = document.getElementById('cancel-button');
    const logoutButton = document.querySelector('.logout-btn');
    
    
    const viewFields = document.querySelectorAll('.profile-view-field');
    const editFields = document.querySelectorAll('.profile-edit-field');

    
    let originalValues = {};

    

    function toggleEditMode(isEditing) {
        viewFields.forEach(field => field.classList.toggle('hidden', isEditing));
        editFields.forEach(field => field.classList.toggle('hidden', !isEditing));

        editButton.classList.toggle('hidden', isEditing);
        saveButton.classList.toggle('hidden', !isEditing);
        cancelButton.classList.toggle('hidden', !isEditing);
        avatarLabel.classList.toggle('hidden', !isEditing);
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
            
            if (fullNameInput && lastNameInput) {
                sidebarName.textContent = `${fullNameInput.value} ${lastNameInput.value}`.trim();
            }
            if (emailInput) {
                sidebarEmail.textContent = emailInput.value;
            }

            
            toast.classList.remove('opacity-0', 'translate-y-10');
            toast.classList.add('opacity-100', 'translate-y-0');
            setTimeout(() => {
                toast.classList.remove('opacity-100', 'translate-y-0');
                toast.classList.add('opacity-0', 'translate-y-10');
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

    
    if (logoutButton) {
        logoutButton.addEventListener('click', function(e) {
            console.log('Logout button clicked, submitting form');
            const form = logoutButton.closest('form');
            if (form) {
                form.submit();
            } else {
                console.error('Logout form not found');
            }
        });
    }

    
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
                sidebarAvatar.src = imageUrl;
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

    const style = document.createElement('style');
    style.innerHTML = `
        .toggle-checkbox:checked { right: 0; border-color: #0D9488; }
        .toggle-checkbox:checked + .toggle-label { background-color: #0D9488; }
    `;
    document.head.appendChild(style);
});