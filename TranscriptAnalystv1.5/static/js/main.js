/**
 * Meeting Summarizer Application
 * Main JavaScript functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    if (typeof bootstrap !== 'undefined') {
        tooltipTriggerList.map(function(tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    // Form validation for summary generation
    const summaryForm = document.getElementById('summaryForm');
    if (summaryForm) {
        summaryForm.addEventListener('submit', function(event) {
            const transcript = document.getElementById('transcript').value.trim();
            const transcriptFile = document.getElementById('transcript_file').files[0];

            if (!transcript && !transcriptFile) {
                event.preventDefault();
                alert('Please either upload a transcript file or paste the transcript text.');
                return false;
            }

            // Show loading state
            const generateBtn = document.getElementById('generateBtn');
            showLoadingState(generateBtn, true);
            return true;
        });
    }

    // File input validation - limit file size
    const fileInput = document.getElementById('transcript_file');
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            const maxSize = 32 * 1024 * 1024; // 32MB
            if (this.files[0] && this.files[0].size > maxSize) {
                alert('File is too large! Please upload a file smaller than 32MB.');
                this.value = '';
            }

            // Show file name in a more user-friendly way
            if (this.files[0]) {
                const fileName = this.files[0].name;
                const fileSize = Math.round(this.files[0].size / 1024); // Convert to KB

                // Create or update file info element
                let fileInfo = document.getElementById('file-info');
                if (!fileInfo) {
                    fileInfo = document.createElement('div');
                    fileInfo.id = 'file-info';
                    fileInfo.className = 'mt-2 alert alert-info d-flex align-items-center';
                    this.parentNode.appendChild(fileInfo);
                }

                fileInfo.innerHTML = `
                    <i class="fas fa-file-alt me-2"></i>
                    <div>
                        <strong>${fileName}</strong> (${fileSize} KB)
                        <button type="button" class="btn-close float-end" aria-label="Close"></button>
                    </div>
                `;

                // Add listener to remove button
                const closeBtn = fileInfo.querySelector('.btn-close');
                closeBtn.addEventListener('click', function(e) {
                    e.preventDefault();
                    fileInput.value = '';
                    fileInfo.remove();
                });
            }
        });
    }

    // Textarea character counter
    const transcriptTextarea = document.getElementById('transcript');
    if (transcriptTextarea) {
        transcriptTextarea.addEventListener('input', function() {
            // Create or update character counter
            let charCounter = document.getElementById('char-counter');
            if (!charCounter) {
                charCounter = document.createElement('div');
                charCounter.id = 'char-counter';
                charCounter.className = 'form-text text-end';
                this.parentNode.appendChild(charCounter);
            }

            const charCount = this.value.length;
            const wordCount = this.value.trim().split(/\s+/).length;

            charCounter.textContent = `${charCount} characters, ${wordCount} words`;
        });
    }

    // Enable collapsible sections on summary page
    const collapseButtons = document.querySelectorAll('.collapse-btn');
    collapseButtons.forEach(button => {
        button.addEventListener('click', function() {
            const targetId = this.getAttribute('data-bs-target');
            const icon = this.querySelector('i');

            if (icon) {
                if (icon.classList.contains('fa-chevron-down')) {
                    icon.classList.remove('fa-chevron-down');
                    icon.classList.add('fa-chevron-up');
                } else {
                    icon.classList.remove('fa-chevron-up');
                    icon.classList.add('fa-chevron-down');
                }
            }
        });
    });

    // Add smooth scrolling for anchor links
    const anchorLinks = document.querySelectorAll('a[href^="#"]');
    anchorLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            if (this.getAttribute('href').length > 1) {
                e.preventDefault();

                const targetId = this.getAttribute('href');
                const targetElement = document.querySelector(targetId);

                if (targetElement) {
                    window.scrollTo({
                        top: targetElement.offsetTop - 80,
                        behavior: 'smooth'
                    });
                }
            }
        });
    });

    // Print functionality
    const printButton = document.querySelector('.btn-print');
    if (printButton) {
        printButton.addEventListener('click', function() {
            window.print();
        });
    }

    // Table row highlighting
    const tableCells = document.querySelectorAll('.table td');
    if (tableCells.length > 0) {
        tableCells.forEach(cell => {
            cell.addEventListener('mouseover', function() {
                this.parentElement.classList.add('row-highlight');
            });

            cell.addEventListener('mouseout', function() {
                this.parentElement.classList.remove('row-highlight');
            });
        });
    }
});

/**
 * Show or hide loading state on button and form
 * @param {HTMLElement} button - The button element
 * @param {boolean} isLoading - Whether to show loading state
 */
function showLoadingState(button, isLoading) {
    if (isLoading) {
        button.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Generating...';
        button.disabled = true;

        // Add overlay with loading animation
        const form = button.closest('form');
        const overlay = document.createElement('div');
        overlay.className = 'loading-overlay';
        overlay.innerHTML = `
            <div class="loading-content">
                <div class="spinner-border text-primary" role="status" style="width: 3rem; height: 3rem;">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <h5 class="mt-4">Analyzing transcript...</h5>
                <p class="text-muted">This might take a minute for longer transcripts.</p>
                <div class="progress mt-3" style="height: 10px; width: 250px;">
                    <div class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" style="width: 100%"></div>
                </div>
            </div>
        `;
        form.appendChild(overlay);
    } else {
        button.innerHTML = '<i class="fas fa-magic me-2"></i>Generate Summary';
        button.disabled = false;

        // Remove overlay
        const overlay = document.querySelector('.loading-overlay');
        if (overlay) {
            overlay.remove();
        }
    }
}