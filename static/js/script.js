document.addEventListener('DOMContentLoaded', function() {
    // Logout button functionality
    const logoutBtn = document.querySelector('.logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function() {
            window.location.href = '/logout';
        });
    }

    // Sidebar toggle functionality
    const sidebarToggle = document.querySelector('.sidebar-toggle');
    const sidebar = document.querySelector('.sidebar');
    const mainContainer = document.querySelector('.main-container');

    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function() {
            sidebar.classList.toggle('collapsed');
            mainContainer.classList.toggle('expanded');
        });
    }

    // Filter toggle
    const toggleFilters = document.getElementById('toggleFilters');
    const filterContent = document.getElementById('filterContent');
    const filterField = document.getElementById('filterField');
    const filterValue = document.getElementById('filterValue');
    const clearFilters = document.getElementById('clearFilters');
    
    toggleFilters.addEventListener('click', () => {
        filterContent.style.display = filterContent.style.display === 'none' ? 'block' : 'none';
    });

    // Filter functionality
    function filterEntries() {
        const rows = document.querySelectorAll('#entriesTableBody tr');
        const field = filterField.value;
        const value = filterValue.value.toLowerCase();

        rows.forEach(row => {
            if (field === 'all') {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(value) ? '' : 'none';
            } else {
                const cell = row.querySelector(`td:nth-child(${getColumnIndex(field)})`);
                const text = cell.textContent.toLowerCase();
                row.style.display = text.includes(value) ? '' : 'none';
            }
        });
    }

    function getColumnIndex(field) {
        const mapping = {
            'jev': 1,
            'particulars': 2,
            'amount': 3,
            'entryDate': 4,
            'receivedDate': 5
        };
        return mapping[field] || 1;
    }

    filterField.addEventListener('change', filterEntries);
    filterValue.addEventListener('input', filterEntries);
    clearFilters.addEventListener('click', () => {
        filterField.value = 'all';
        filterValue.value = '';
        filterEntries();
    });

    // Modal functionality
    const entryDetailsModal = document.getElementById('entryDetailsModal');
    const editEntryModal = document.getElementById('editEntryModal');
    const editEntryForm = document.getElementById('editEntryForm');

    // Close modals when clicking outside
    window.addEventListener('click', (e) => {
        if (e.target === entryDetailsModal || e.target === editEntryModal) {
            entryDetailsModal.style.display = 'none';
            editEntryModal.style.display = 'none';
        }
    });

    // Close buttons
    document.querySelectorAll('.close, .close-modal').forEach(button => {
        button.addEventListener('click', () => {
            entryDetailsModal.style.display = 'none';
            editEntryModal.style.display = 'none';
        });
    });

    // Row click for details
    document.querySelectorAll('#entriesTableBody tr').forEach(row => {
        row.addEventListener('click', (e) => {
            if (!e.target.closest('.btn-icon')) {
                const entry = JSON.parse(row.dataset.entry);
                const content = `
                    <div class="entry-details">
                        <p><strong>JEV:</strong> ${entry.JEV}</p>
                        <p><strong>Particulars:</strong> ${entry.Particulars}</p>
                        <p><strong>Amount:</strong> ₱${parseFloat(entry.Amount).toLocaleString('en-US', {minimumFractionDigits: 2})}</p>
                        <p><strong>Date Entry:</strong> ${entry['Date Entry']}</p>
                        <p><strong>Date Received:</strong> ${entry['Date Received'] || 'Not set'}</p>
                    </div>
                `;
                document.getElementById('entryDetailsContent').innerHTML = content;
                entryDetailsModal.style.display = 'block';
            }
        });
    });

    // Edit button click
    document.querySelectorAll('.edit-entry').forEach(button => {
        button.addEventListener('click', (e) => {
            e.stopPropagation();
            const row = button.closest('tr');
            const entry = JSON.parse(row.dataset.entry);
            
            document.getElementById('editJEV').value = entry.JEV;
            document.getElementById('editParticulars').value = entry.Particulars;
            document.getElementById('editAmount').value = entry.Amount;
            document.getElementById('editDateReceived').value = entry['Date Received'] || '';
            
            editEntryModal.style.display = 'block';
        });
    });

    // Handle form submission
    editEntryForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const formData = {
            jev: document.getElementById('editJEV').value,
            particulars: document.getElementById('editParticulars').value,
            amount: document.getElementById('editAmount').value,
            dateReceived: document.getElementById('editDateReceived').value
        };

        try {
            const response = await fetch('/update_entry', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });

            if (response.ok) {
                window.location.reload();
            } else {
                const data = await response.json();
                alert('Error updating entry: ' + data.error);
            }
        } catch (error) {
            alert('Error updating entry: ' + error);
        }
    });
}); 