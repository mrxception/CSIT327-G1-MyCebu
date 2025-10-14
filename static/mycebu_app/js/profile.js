document.addEventListener('DOMContentLoaded', function() {
    // Element selections
    const backButton = document.getElementById('back-button');
    const tabLinks = document.querySelectorAll('.tab-link');
    const tabContents = document.querySelectorAll('.tab-content');
    const profileForm = document.getElementById('profile-form');
    const toast = document.getElementById('toast');
    
    // Avatars and sidebar info
    const sidebarAvatar = document.getElementById('sidebar-avatar');
    const mainAvatar = document.getElementById('main-avatar');
    const avatarUpload = document.getElementById('avatar-upload');
    const avatarLabel = document.getElementById('avatar-label');
    const sidebarName = document.getElementById('sidebar-name');
    const sidebarEmail = document.getElementById('sidebar-email');

    // Buttons
    const editButton = document.getElementById('edit-button');
    const saveButton = document.getElementById('save-button');
    const cancelButton = document.getElementById('cancel-button');
    
    // Profile fields
    const viewFields = document.querySelectorAll('.profile-view-field');
    const editFields = document.querySelectorAll('.profile-edit-field');

    // --- FUNCTIONS ---

    function toggleEditMode(isEditing) {
        viewFields.forEach(field => field.classList.toggle('hidden', isEditing));
        editFields.forEach(field => field.classList.toggle('hidden', !isEditing));

        editButton.classList.toggle('hidden', isEditing);
        saveButton.classList.toggle('hidden', !isEditing);
        cancelButton.classList.toggle('hidden', !isEditing);
        avatarLabel.classList.toggle('hidden', !isEditing);
    }

    function enterEditMode() {
        editFields.forEach(input => {
            const correspondingViewField = document.querySelector(`[data-value][id="${input.id}"]`) || input.previousElementSibling;
            if(correspondingViewField) {
                input.value = correspondingViewField.dataset.value;
            }
        });
        toggleEditMode(true);
    }

    function exitEditMode(saveChanges) {
        if (saveChanges) {
            editFields.forEach(input => {
                  const correspondingViewField = document.querySelector(`[data-value][id="${input.id}"]`) || input.previousElementSibling;
                  if(correspondingViewField) {
                    correspondingViewField.textContent = input.value;
                    correspondingViewField.dataset.value = input.value;
                  }
            });
            
            // Update sidebar info
            sidebarName.textContent = document.getElementById('full_name').value;
            sidebarEmail.textContent = document.getElementById('email').value;

            // Show toast
            toast.classList.remove('opacity-0', 'translate-y-10');
            toast.classList.add('opacity-100', 'translate-y-0');
            setTimeout(() => {
                toast.classList.remove('opacity-100', 'translate-y-0');
                toast.classList.add('opacity-0', 'translate-y-10');
            }, 3000);
        }
        toggleEditMode(false);
    }
    
    // --- EVENT LISTENERS ---

    // Back button listener
    backButton.addEventListener('click', function (e) {
        e.preventDefault();
        window.history.back();
    });

    // Tab switching
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

    // Button clicks
    editButton.addEventListener('click', enterEditMode);
    cancelButton.addEventListener('click', () => exitEditMode(false));
    profileForm.addEventListener('submit', function(e) {
        e.preventDefault();
        exitEditMode(true);
    });

    // Avatar upload
    avatarUpload.addEventListener('change', function(event) {
        const file = event.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                const imageUrl = e.target.result;
                sidebarAvatar.src = imageUrl;
                mainAvatar.src = imageUrl;
            };
            reader.readAsURL(file);
        }
    });
    
      // Initial setup to make sure data-value is set on all view fields
    viewFields.forEach(field => {
        if (!field.dataset.value) {
            field.dataset.value = field.textContent;
        }
    });

    // Custom style for the theme toggle
    const style = document.createElement('style');
    style.innerHTML = `
        .toggle-checkbox:checked { right: 0; border-color: #0D9488; }
        .toggle-checkbox:checked + .toggle-label { background-color: #0D9488; }
    `;
    document.head.appendChild(style);
});