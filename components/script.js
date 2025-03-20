// Simple navigation and sidebar toggle functionality

// Wait for DOM content to be loaded
document.addEventListener('DOMContentLoaded', function() {
  // Get references to elements
  const sidebar = document.querySelector('.sidebar');
  const sidebarToggle = document.querySelector('.sidebar-toggle');
  const sidebarItems = document.querySelectorAll('.sidebar-item');

  // Toggle sidebar when the button is clicked
  sidebarToggle.addEventListener('click', function() {
    sidebar.classList.toggle('collapsed');
    
    // If sidebar is collapsed, hide text elements
    if (sidebar.classList.contains('collapsed')) {
      sidebar.style.width = '4rem';
      document.querySelectorAll('.sidebar-text, .menu-text, .footer-text').forEach(el => {
        el.style.display = 'none';
      });
    } else {
      sidebar.style.width = '16rem';
      document.querySelectorAll('.sidebar-text, .menu-text, .footer-text').forEach(el => {
        el.style.display = 'block';
      });
    }
  });

  // Handle active state for sidebar items
  const currentPage = window.location.pathname.split('/').pop() || 'dashboard.html';
  sidebarItems.forEach(item => {
    if (item.getAttribute('href') === currentPage) {
      item.classList.add('active');
    } else {
      item.classList.remove('active');
    }
  });

  // Filter toggle (only on database page)
  const filterBtn = document.querySelector('.filter-header .btn-secondary');
  const filterContent = document.querySelector('.filter-content');
  
  if (filterBtn && filterContent) {
    // Initially hide filter content
    filterContent.style.display = 'none';
    
    filterBtn.addEventListener('click', function() {
      const isVisible = filterContent.style.display === 'block';
      filterContent.style.display = isVisible ? 'none' : 'block';
    });
  }

  // Handle form submission (only on dashboard page)
  const entryForm = document.querySelector('.entry-form');
  if (entryForm) {
    entryForm.addEventListener('submit', function(e) {
      e.preventDefault();
      // Add your form submission logic here
      console.log('Form submitted');
    });
  }

  // Handle search functionality (only on accounts page)
  const searchInput = document.querySelector('.search-input');
  if (searchInput) {
    searchInput.addEventListener('input', function(e) {
      const searchTerm = e.target.value.toLowerCase();
      const tableRows = document.querySelectorAll('.data-table tbody tr');
      
      tableRows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(searchTerm) ? '' : 'none';
      });
    });
  }
});
