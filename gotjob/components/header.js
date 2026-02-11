// BESTIEJOB Shared Header Component

function createHeader(activePage = '') {
  const nav = document.createElement('nav');
  nav.className = 'nav-menu';
  
  const links = [
    { href: '/', label: 'Home', page: 'home' },
    { href: '/findjobs/', label: 'Find Jobs', page: 'findjobs' },
    { href: '/resources/', label: 'Career Resources', page: 'resources' },
    { href: '/salary-insights/', label: 'Salary Insights', page: 'salary' },
    { href: '/companies/', label: 'Companies', page: 'companies' },
    { href: '/resume-builder/', label: 'Resume Builder', page: 'resume' },
    { href: '/interview-prep/', label: 'Interview Prep', page: 'interview' },
    { href: '/my-jobs/', label: 'My Jobs', page: 'myjobs' }
  ];
  
  links.forEach(link => {
    const a = document.createElement('a');
    a.href = link.href;
    a.textContent = link.label;
    if (link.page === activePage) {
      a.className = 'active';
    }
    nav.appendChild(a);
  });
  
  return nav;
}

function createFooter() {
  const footer = document.createElement('footer');
  footer.className = 'footer';
  
  footer.innerHTML = `
    <div class="footer-content">
      <div class="footer-section">
        <h4>BESTIEJOB</h4>
        <p>Toronto's premier job board for creative and technology professionals seeking $100K+ manager roles.</p>
      </div>
      
      <div class="footer-section">
        <h4>Job Search</h4>
        <ul>
          <li><a href="/findjobs/">Find Jobs</a></li>
          <li><a href="/companies/">Browse Companies</a></li>
          <li><a href="/salary-insights/">Salary Insights</a></li>
          <li><a href="/my-jobs/">My Saved Jobs</a></li>
        </ul>
      </div>
      
      <div class="footer-section">
        <h4>Career Resources</h4>
        <ul>
          <li><a href="/resources/">Career Hub</a></li>
          <li><a href="/resume-builder/">Resume Builder</a></li>
          <li><a href="/interview-prep/">Interview Prep</a></li>
          <li><a href="/resources/#guides">Career Guides</a></li>
        </ul>
      </div>
      
      <div class="footer-section">
        <h4>About</h4>
        <ul>
          <li><a href="/#about">About BESTIEJOB</a></li>
          <li><a href="mailto:contact@bestiejob.com">Contact Us</a></li>
          <li><a href="/#privacy">Privacy Policy</a></li>
          <li><a href="/#terms">Terms of Service</a></li>
        </ul>
      </div>
    </div>
    
    <div class="footer-bottom">
      <p>&copy; ${new Date().getFullYear()} BESTIEJOB. All rights reserved. Made with ❤️ in Toronto.</p>
    </div>
  `;
  
  return footer;
}

// Initialize header and footer on page load
function initializeLayout(activePage = '') {
  // Add header if not exists
  if (!document.querySelector('.nav-menu')) {
    const header = createHeader(activePage);
    document.body.insertBefore(header, document.body.firstChild);
  }
  
  // Add footer if not exists
  if (!document.querySelector('.footer')) {
    const footer = createFooter();
    document.body.appendChild(footer);
  }
}

// Export for use in other pages
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { createHeader, createFooter, initializeLayout };
}
