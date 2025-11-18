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
        pdfUrl = filename;
        frame.src = pdfUrl;
        // For external URLs, set download link to the URL (may not work for all)
        downloadLink.href = pdfUrl;
        downloadLink.style.display = 'inline-block';
    } else {
        pdfUrl = PDF_BASE_PATH + filename;
        frame.src = pdfUrl;
        downloadLink.href = pdfUrl;
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

// Print the PDF by opening it in a new window
function printPdf() {
    const frame = document.getElementById('pdfViewerFrame');
    if (frame.src) {
        window.open(frame.src, '_blank');
    }
}

// Close modal if clicking outside the white box
window.onclick = function(event) {
    const modal = document.getElementById('pdfModal');
    if (event.target == modal) {
        closePdfPreview();
    }
}