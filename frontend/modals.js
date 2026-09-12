// modals.js
// This file injects the Modals HTML into the page and handles their logic.

const modalsHTML = `
    <!-- ===== HISTORY MODAL ===== -->
    <div id="historyModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2>Detection History</h2>
                <span class="close-modal">&times;</span>
            </div>
            <div class="modal-body" id="historyModalBody">
                <!-- History items will be populated here -->
            </div>
        </div>
    </div>

    <!-- ===== ABOUT MODAL ===== -->
    <div id="aboutModal" class="modal">
        <div class="modal-content" style="max-width: 500px;">
            <div class="modal-header">
                <h2>About AI Surveillance</h2>
                <span class="close-modal">&times;</span>
            </div>
            <div class="modal-body" style="color: var(--text-muted); line-height: 1.6; padding: 2rem;">
                <p>Welcome to the <strong>AI Surveillance Dashboard</strong>. This system provides real-time, cutting-edge object detection and monitoring capabilities designed for maximum security.</p>
                
                <h3 style="color: var(--text-main); margin-top: 1.5rem; font-family: 'Outfit', sans-serif;">Key Features</h3>
                <ul style="padding-left: 20px; margin-top: 10px; display: flex; flex-direction: column; gap: 8px;">
                    <li><strong style="color: var(--accent);">Live Camera Feed:</strong> Seamless webcam integration.</li>
                    <li><strong style="color: var(--accent);">Human Detection:</strong> Focused real-time detection of people.</li>
                    <li><strong style="color: var(--accent);">Live Counting:</strong> Instant metrics on people in the frame.</li>
                    <li><strong style="color: var(--accent);">History Logs:</strong> Rolling record of recent detections.</li>
                </ul>
                
                <p style="margin-top: 1.5rem; font-size: 0.9rem; font-style: italic;">Designed with a premium glassmorphic UI for an optimal monitoring experience.</p>
            </div>
        </div>
    </div>
`;

// Inject the HTML into the body dynamically
document.body.insertAdjacentHTML('beforeend', modalsHTML);

// Logic to handle modals (called from script.js)
window.setupDropdownAndModal = function() {
    // Dropdown & History Modal
    const resultsMenuBtn = document.getElementById('resultsMenuBtn');
    const resultsDropdown = document.getElementById('resultsDropdown');
    const viewHistoryBtn = document.getElementById('viewHistoryBtn');
    const historyModal = document.getElementById('historyModal');
    const closeHistoryModal = historyModal.querySelector('.close-modal');

    // About Modal
    const aboutBtn = document.getElementById('aboutBtn');
    const aboutModal = document.getElementById('aboutModal');
    const closeAboutModal = aboutModal.querySelector('.close-modal');

    // Toggle dropdown
    if(resultsMenuBtn) {
        resultsMenuBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            resultsDropdown.classList.toggle('show');
        });
    }

    // Close dropdown on click outside
    window.addEventListener('click', (e) => {
        if (!e.target.closest('.dropdown')) {
            if(resultsDropdown) resultsDropdown.classList.remove('show');
        }
    });

    // Open History Modal
    if(viewHistoryBtn) {
        viewHistoryBtn.addEventListener('click', (e) => {
            e.preventDefault();
            resultsDropdown.classList.remove('show');
            populateHistoryModal();
            historyModal.classList.add('show');
        });
    }

    // Close History Modal
    if(closeHistoryModal) {
        closeHistoryModal.addEventListener('click', () => {
            historyModal.classList.remove('show');
        });
    }

    // Open About Modal
    if(aboutBtn) {
        aboutBtn.addEventListener('click', () => {
            aboutModal.classList.add('show');
        });
    }

    // Close About Modal
    if(closeAboutModal) {
        closeAboutModal.addEventListener('click', () => {
            aboutModal.classList.remove('show');
        });
    }

    // Close Modals on outside click
    window.addEventListener('click', (e) => {
        if (e.target === historyModal) {
            historyModal.classList.remove('show');
        }
        if (e.target === aboutModal) {
            aboutModal.classList.remove('show');
        }
    });
}

window.populateHistoryModal = function() {
    const modalBody = document.getElementById('historyModalBody');
    if (!modalBody) return;
    
    // Relies on global appHistory array defined in script.js
    if (typeof appHistory === 'undefined' || appHistory.length === 0) {
        modalBody.innerHTML = '<div class="no-results">No history available yet.</div>';
        return;
    }

    modalBody.innerHTML = appHistory.map(h => 
        `<div class="history-item">
            <span><strong>${h.class.toUpperCase()}</strong> detected (${(h.confidence * 100).toFixed(0)}%)</span>
            <span style="color: var(--text-muted); font-size: 0.85rem;">${h.timestamp}</span>
        </div>`
    ).join('');
}
