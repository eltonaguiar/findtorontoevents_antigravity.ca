// Market Report App
// Handles any interactive elements on the market report page

document.addEventListener('DOMContentLoaded', () => {
  // Animate metrics on load
  const metrics = document.querySelectorAll('.metric-value');
  metrics.forEach(metric => {
    const finalValue = metric.textContent;
    
    // Skip if it's text like "Strong"
    if (isNaN(parseInt(finalValue))) return;
    
    const numericValue = parseInt(finalValue.replace(/[^0-9]/g, ''));
    const suffix = finalValue.replace(/[0-9]/g, '');
    let current = 0;
    const increment = Math.ceil(numericValue / 30);
    
    metric.textContent = '0' + suffix;
    
    const timer = setInterval(() => {
      current += increment;
      if (current >= numericValue) {
        current = numericValue;
        clearInterval(timer);
      }
      metric.textContent = current.toLocaleString() + suffix;
    }, 30);
  });

  // Add hover effect to trend items
  document.querySelectorAll('.trend-item').forEach(item => {
    item.style.cursor = 'pointer';
    item.addEventListener('click', () => {
      // Toggle expanded view (could show more details in a modal)
      item.style.background = item.style.background === 'rgba(124, 92, 255, 0.1)' 
        ? 'rgba(0, 0, 0, 0.2)' 
        : 'rgba(124, 92, 255, 0.1)';
    });
  });

  // Skill tag click - filter jobs (placeholder functionality)
  document.querySelectorAll('.skill-tag').forEach(tag => {
    tag.style.cursor = 'pointer';
    tag.addEventListener('click', () => {
      const skill = tag.textContent;
      // In a real implementation, this would redirect to job search with filter
      alert(`Search for "${skill}" jobs on the Find Jobs page!`);
    });
  });

  // Company hiring click
  document.querySelectorAll('.company-hiring').forEach(company => {
    company.style.cursor = 'pointer';
    company.addEventListener('click', () => {
      const companyName = company.querySelector('.company-name').textContent;
      // In a real implementation, this would search for that company
      alert(`Search for jobs at ${companyName} on the Find Jobs page!`);
    });
  });

  // Last updated timestamp
  const now = new Date();
  const options = { year: 'numeric', month: 'long', day: 'numeric' };
  const dateStr = now.toLocaleDateString('en-CA', options);
  
  // Update any elements with data-timestamp
  document.querySelectorAll('[data-timestamp]').forEach(el => {
    el.textContent = dateStr;
  });
});
