// Defines the base path to your static PDF folder
// Make sure your pdfs are in /static/mycebu_app/pdf/ inside your Django app
const PDF_BASE_PATH = "{% static 'mycebu_app/pdf/' %}";

function openPdfPreview(filename, title) {
    const modal = document.getElementById('pdfModal');
    const frame = document.getElementById('pdfViewerFrame');
    const titleEl = document.getElementById('pdfModalTitle');
    const downloadLink = document.getElementById('downloadLink');

    // 1. Set the title
    titleEl.textContent = title;

    // 2. Construct the URL
    // If the filename is a placeholder, you might want to handle that
    if (filename === "TO BE UPDATED") {
        alert("PDF file not yet available for this ordinance.");
        return;
    }

    let pdfUrl;
    // 3. Set Iframe Source
    // Check if filename is an external URL (starts with http)
    if (filename.startsWith('http')) {
        // Handle Google Drive links
        if (filename.includes('drive.google.com/file/d/')) {
            const idMatch = filename.match(/\/d\/([^\/]+)/);
            if (idMatch) {
                const fileId = idMatch[1];
                pdfUrl = filename; // Keep original /preview for embedding
                frame.src = pdfUrl;
                downloadLink.href = 'https://drive.google.com/uc?export=download&id=' + fileId;
                downloadLink.download = title.replace(/[<>:"/\\|?*]/g, '').replace(/\s+/g, '_') + '.pdf';
                downloadLink.style.display = 'inline-block';
            } else {
                pdfUrl = filename;
                frame.src = pdfUrl;
                downloadLink.href = pdfUrl;
                downloadLink.download = title.replace(/[<>:"/\\|?*]/g, '').replace(/\s+/g, '_') + '.pdf';
                downloadLink.style.display = 'inline-block';
            }
        } else {
            pdfUrl = filename;
            frame.src = pdfUrl;
            // For external URLs, set download link to the URL (may not work for all)
            downloadLink.href = pdfUrl;
            downloadLink.download = title.replace(/[<>:"/\\|?*]/g, '').replace(/\s+/g, '_') + '.pdf';
            downloadLink.style.display = 'inline-block';
        }
    } else {
        pdfUrl = PDF_BASE_PATH + filename;
        frame.src = pdfUrl;
        downloadLink.href = pdfUrl;
        downloadLink.download = title.replace(/[<>:"/\\|?*]/g, '').replace(/\s+/g, '_') + '.pdf';
        downloadLink.style.display = 'inline-block';
    }

    // 4. Show Modal
    modal.style.display = "flex";
    document.body.style.overflow = "hidden"; // Prevent background scrolling
}

function closePdfPreview() {
    const modal = document.getElementById('pdfModal');
    const frame = document.getElementById('pdfViewerFrame');

    // Hide modal
    modal.style.display = "none";
    document.body.style.overflow = "auto"; // Restore scrolling

    // Clear source to stop loading/playing
    frame.src = "";
}

// Print the PDF
function printPdf() {
    const frame = document.getElementById('pdfViewerFrame');
    if (frame.src) {
        // Wait for iframe to load, then print
        setTimeout(() => {
            try {
                frame.contentWindow.print();
            } catch (e) {
                // Fallback: open in new window
                const printWindow = window.open(frame.src, '_blank');
                if (printWindow) {
                    printWindow.onload = function() {
                        printWindow.print();
                        printWindow.close();
                    };
                }
            }
        }, 1000); // 1 second delay
    }
}

// Download the ordinance PDF
function downloadOrdinance(filename, title) {
    if (filename === "TO BE UPDATED") {
        alert("PDF file not yet available for this ordinance.");
        return;
    }

    let downloadUrl;
    if (filename.startsWith('http')) {
        downloadUrl = filename;
    } else {
        downloadUrl = PDF_BASE_PATH + filename;
    }

    // Create a temporary link and trigger download
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = title + '.pdf';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Share the ordinance
function shareOrdinance(filename, title) {
    if (navigator.share) {
        navigator.share({
            title: title,
            text: 'Check out this ordinance: ' + title,
            url: window.location.href
        });
    } else {
        // Fallback: copy link to clipboard
        const url = window.location.href;
        navigator.clipboard.writeText(url).then(() => {
            alert('Link copied to clipboard!');
        });
    }
}

// Close modal if clicking outside the white box
window.onclick = function(event) {
    const modal = document.getElementById('pdfModal');
    if (event.target == modal) {
        closePdfPreview();
    }
}

// View Toggle Functionality
document.addEventListener('DOMContentLoaded', function() {
    const viewToggle = document.getElementById('viewToggle');
    const viewIcon = document.getElementById('viewIcon');

    // Get saved view preference or default to grid
    let viewMode = localStorage.getItem('ordinanceViewMode') || 'grid';
    let isGrid = viewMode === 'grid';

    function updateView() {
        // Get all ordinance containers, both for full view and category groups
        const ordContainers = document.querySelectorAll('.ord-container');
        let isListMode = !isGrid; // isGrid is toggled on click

        // Save preference
        localStorage.setItem('ordinanceViewMode', isGrid ? 'grid' : 'list');

        // Iterate over ALL containers to toggle their class and display property
        ordContainers.forEach(container => {
            if (isGrid) {
                // Switch to Grid View
                container.classList.remove('ord-list');
                container.classList.add('ord-grid');
                container.style.display = 'grid'; // Grid display property
            } else {
                // Switch to List View
                container.classList.remove('ord-grid');
                container.classList.add('ord-list');
                container.style.display = 'flex'; // List display property (column flex)
            }
        });

        // Update the toggle button appearance
        if (isGrid) {
            viewToggle.innerHTML = '<span class="material-symbols-rounded" id="viewIcon">grid_view</span> Grid View';
        } else {
            viewToggle.innerHTML = '<span class="material-symbols-rounded" id="viewIcon">view_list</span> List View';
        }

        // Handle the specific ID containers for the Full View (single list/grid)
        const ordGridFull = document.getElementById('ordContainer'); // Full View Grid
        const ordListFull = document.getElementById('ordListContainer'); // Full View List

        if (ordGridFull && ordListFull) {
            if (isGrid) {
                ordGridFull.style.display = 'grid';
                ordListFull.style.display = 'none';
            } else {
                ordGridFull.style.display = 'none';
                ordListFull.style.display = 'flex';
            }
        }
    }

    if (viewToggle) {
        // Set initial view
        updateView();

        viewToggle.addEventListener('click', function() {
            isGrid = !isGrid;
            updateView();
        });
    }
});
