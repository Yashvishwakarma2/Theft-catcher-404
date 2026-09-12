# modals.py
# This file demonstrates how the logic from `modals.js` would translate into Python.
# If you were building the backend of this dashboard in Python (using Flask, FastAPI, or Django),
# you would generate and inject the HTML from the server rather than using client-side JavaScript.

# 1. The HTML String
MODALS_HTML = """
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
            </div>
        </div>
    </div>
"""

def get_modals_html():
    """
    Returns the raw HTML for the modals.
    In a framework like Flask, you might inject this into your main template.
    """
    return MODALS_HTML

def generate_history_html(history_list):
    """
    This is the Python equivalent of `populateHistoryModal()` in `modals.js`.
    It takes a list of Python dictionaries (representing detected objects) 
    and generates the dynamic HTML to display them.
    """
    if not history_list:
        return '<div class="no-results">No history available yet.</div>'
        
    html_items = []
    
    # Loop over the history list (similar to appHistory.map in JavaScript)
    for item in history_list:
        # We use Python f-strings to inject the variables into the HTML
        html_string = f"""
        <div class="history-item">
            <span><strong>{item['class'].upper()}</strong> detected ({int(item['confidence'] * 100)}%)</span>
            <span style="color: var(--text-muted); font-size: 0.85rem;">{item['timestamp']}</span>
        </div>"""
        
        html_items.append(html_string)
        
    # Join the list into one giant string
    return "".join(html_items)

# ==========================================
# EXAMPLE USAGE
# ==========================================
if __name__ == "__main__":
    print("--- Translating JS appHistory to Python ---")
    
    # In Python, our appHistory is a List of Dictionaries
    app_history_mock = [
        {"class": "person", "confidence": 0.92, "timestamp": "11:05:00 AM"},
        {"class": "person", "confidence": 0.88, "timestamp": "11:05:12 AM"},
        {"class": "knife",  "confidence": 0.75, "timestamp": "11:06:00 AM"}
    ]
    
    # Generate the HTML
    history_html_output = generate_history_html(app_history_mock)
    
    print("\n[Generated HTML Output]:")
    print(history_html_output)
