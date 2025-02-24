// Toggle password visibility
function togglePasswordVisibility(inputId, buttonId) {
    const input = document.getElementById(inputId);
    const button = document.getElementById(buttonId);
    
    if (input.type === 'password') {
        input.type = 'text';
        button.innerHTML = '👁️';
    } else {
        input.type = 'password';
        button.innerHTML = '👁️‍🗨️';
    }
}

// Auto-refresh status every 30 seconds
function refreshStatus() {
    fetch(window.location.href)
        .then(response => response.text())
        .then(html => {
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            
            // Update status cards
            document.getElementById('telegram-status').innerHTML = 
                doc.getElementById('telegram-status').innerHTML;
            document.getElementById('openai-status').innerHTML = 
                doc.getElementById('openai-status').innerHTML;
            
            // Update message count
            document.getElementById('message-count').innerHTML = 
                doc.getElementById('message-count').innerHTML;
            
            // Update recent messages
            document.getElementById('message-list').innerHTML = 
                doc.getElementById('message-list').innerHTML;
        });
}

// Start auto-refresh
setInterval(refreshStatus, 30000);

// Confirm rule deletion
function confirmRuleDelete(index) {
    return confirm('Are you sure you want to delete this rule?');
}

// Form validation
function validateRuleForm() {
    const text = document.getElementById('rule-text').value;
    const category = document.getElementById('rule-category').value;
    
    if (!text.trim()) {
        alert('Please enter rule text');
        return false;
    }
    if (!category.trim()) {
        alert('Please enter a category');
        return false;
    }
    return true;
}

// Initialize tooltips
document.addEventListener('DOMContentLoaded', function() {
    const tooltips = document.querySelectorAll('[data-tooltip]');
    tooltips.forEach(element => {
        element.addEventListener('mouseover', e => {
            const tooltip = document.createElement('div');
            tooltip.className = 'absolute bg-gray-800 text-white px-2 py-1 rounded text-sm -mt-8';
            tooltip.textContent = element.getAttribute('data-tooltip');
            element.appendChild(tooltip);
        });
        
        element.addEventListener('mouseout', e => {
            const tooltip = element.querySelector('div');
            if (tooltip) {
                tooltip.remove();
            }
        });
    });
}); 