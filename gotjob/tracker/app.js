let applications = JSON.parse(localStorage.getItem('jobApplications') || '[]');
let currentFilter = 'all';

function init() {
  renderApplications();
  updateStats();
  renderUpcoming();
  renderResponseStats();
  renderFollowups();
  
  // Event listeners
  document.getElementById('addAppBtn')?.addEventListener('click', showAddModal);
  document.getElementById('appForm')?.addEventListener('submit', saveApplication);
  document.querySelector('.modal-close')?.addEventListener('click', closeModal);
  
  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentFilter = btn.dataset.filter;
      renderApplications();
    });
  });
}

function showAddModal() {
  document.getElementById('appId').value = '';
  document.getElementById('appForm').reset();
  document.getElementById('appDate').valueAsDate = new Date();
  document.getElementById('modalTitle').textContent = 'Add Application';
  document.getElementById('appModal').style.display = 'flex';
}

function showEditModal(id) {
  const app = applications.find(a => a.id === id);
  if (!app) return;
  
  document.getElementById('appId').value = app.id;
  document.getElementById('appCompany').value = app.company;
  document.getElementById('appPosition').value = app.position;
  document.getElementById('appStatus').value = app.status;
  document.getElementById('appDate').value = app.date;
  document.getElementById('appUrl').value = app.url || '';
  document.getElementById('appSalary').value = app.salary || '';
  document.getElementById('appContact').value = app.contact || '';
  document.getElementById('appNextInterview').value = app.nextInterview || '';
  document.getElementById('appNotes').value = app.notes || '';
  
  document.getElementById('modalTitle').textContent = 'Edit Application';
  document.getElementById('appModal').style.display = 'flex';
}

function closeModal() {
  document.getElementById('appModal').style.display = 'none';
}

function saveApplication(e) {
  e.preventDefault();
  
  const id = document.getElementById('appId').value;
  const app = {
    id: id || Date.now().toString(),
    company: document.getElementById('appCompany').value,
    position: document.getElementById('appPosition').value,
    status: document.getElementById('appStatus').value,
    date: document.getElementById('appDate').value,
    url: document.getElementById('appUrl').value,
    salary: document.getElementById('appSalary').value,
    contact: document.getElementById('appContact').value,
    nextInterview: document.getElementById('appNextInterview').value,
    notes: document.getElementById('appNotes').value,
    updatedAt: new Date().toISOString()
  };
  
  if (id) {
    const index = applications.findIndex(a => a.id === id);
    if (index >= 0) applications[index] = app;
  } else {
    applications.push(app);
  }
  
  localStorage.setItem('jobApplications', JSON.stringify(applications));
  closeModal();
  renderApplications();
  updateStats();
  renderUpcoming();
  renderResponseStats();
  renderFollowups();
}

function deleteApplication(id) {
  if (!confirm('Delete this application?')) return;
  applications = applications.filter(a => a.id !== id);
  localStorage.setItem('jobApplications', JSON.stringify(applications));
  renderApplications();
  updateStats();
  renderUpcoming();
  renderResponseStats();
  renderFollowups();
}

function renderApplications() {
  const container = document.getElementById('applicationsList');
  
  let filtered = applications;
  if (currentFilter !== 'all') {
    filtered = applications.filter(a => a.status === currentFilter);
  }
  
  // Sort by date (newest first)
  filtered.sort((a, b) => new Date(b.date) - new Date(a.date));
  
  if (filtered.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">📋</div>
        <h3>${currentFilter === 'all' ? 'No applications yet' : 'No ' + currentFilter + ' applications'}</h3>
        <p>${currentFilter === 'all' ? 'Start tracking your job search by adding your first application.' : 'Try a different filter or add a new application.'}</p>
        <button class="add-btn" onclick="showAddModal()">Add Application</button>
      </div>
    `;
    return;
  }
  
  let html = '';
  filtered.forEach(app => {
    const statusConfig = {
      applied: { label: 'Applied', class: 'status-applied', icon: '📤' },
      phone: { label: 'Phone Screen', class: 'status-phone', icon: '📞' },
      technical: { label: 'Technical', class: 'status-technical', icon: '💻' },
      onsite: { label: 'On-site', class: 'status-onsite', icon: '🏢' },
      offer: { label: 'Offer', class: 'status-offer', icon: '🎉' },
      accepted: { label: 'Accepted', class: 'status-accepted', icon: '✅' },
      rejected: { label: 'Rejected', class: 'status-rejected', icon: '❌' },
      withdrawn: { label: 'Withdrawn', class: 'status-withdrawn', icon: '🚫' }
    };
    
    const status = statusConfig[app.status] || statusConfig.applied;
    const dateStr = new Date(app.date).toLocaleDateString('en-CA', { month: 'short', day: 'numeric' });
    
    html += `
      <div class="app-card ${status.class}">
        <div class="app-main">
          <div class="app-status-icon">${status.icon}</div>
          <div class="app-info">
            <h4 class="app-company">${escapeHtml(app.company)}</h4>
            <p class="app-position">${escapeHtml(app.position)}</p>
            <div class="app-meta">
              <span class="app-status">${status.label}</span>
              <span class="app-date">Applied ${dateStr}</span>
              ${app.salary ? `<span class="app-salary">${escapeHtml(app.salary)}</span>` : ''}
            </div>
          </div>
        </div>
        <div class="app-actions">
          <button class="action-btn edit" onclick="showEditModal('${app.id}')" title="Edit">✏️</button>
          <button class="action-btn delete" onclick="deleteApplication('${app.id}')" title="Delete">🗑️</button>
        </div>
      </div>
    `;
  });
  
  container.innerHTML = html;
}

function updateStats() {
  const total = applications.length;
  const applied = applications.filter(a => a.status === 'applied').length;
  const interviewing = applications.filter(a => ['phone', 'technical', 'onsite'].includes(a.status)).length;
  const offers = applications.filter(a => ['offer', 'accepted'].includes(a.status)).length;
  
  document.getElementById('totalApps').textContent = total;
  document.getElementById('appliedCount').textContent = applied;
  document.getElementById('interviewCount').textContent = interviewing;
  document.getElementById('offerCount').textContent = offers;
}

function renderUpcoming() {
  const container = document.getElementById('upcomingList');
  
  const upcoming = applications
    .filter(a => a.nextInterview && new Date(a.nextInterview) > new Date())
    .sort((a, b) => new Date(a.nextInterview) - new Date(b.nextInterview))
    .slice(0, 5);
  
  if (upcoming.length === 0) {
    container.innerHTML = '<p class="empty-text">No upcoming interviews scheduled</p>';
    return;
  }
  
  let html = '';
  upcoming.forEach(app => {
    const date = new Date(app.nextInterview);
    const dateStr = date.toLocaleDateString('en-CA', { month: 'short', day: 'numeric' });
    const timeStr = date.toLocaleTimeString('en-CA', { hour: '2-digit', minute: '2-digit' });
    
    html += `
      <div class="upcoming-item">
        <div class="upcoming-date">
          <span class="upcoming-day">${dateStr}</span>
          <span class="upcoming-time">${timeStr}</span>
        </div>
        <div class="upcoming-info">
          <h4>${escapeHtml(app.company)}</h4>
          <p>${escapeHtml(app.position)}</p>
        </div>
        <button class="action-btn edit" onclick="showEditModal('${app.id}')" title="Edit">✏️</button>
      </div>
    `;
  });
  
  container.innerHTML = html;
}

function renderResponseStats() {
  const applied = applications.filter(a => a.status !== 'withdrawn').length;
  const interviews = applications.filter(a => ['phone', 'technical', 'onsite', 'offer', 'accepted'].includes(a.status)).length;
  const offers = applications.filter(a => ['offer', 'accepted'].includes(a.status)).length;
  
  const appToInterview = applied > 0 ? Math.round((interviews / applied) * 100) : 0;
  const interviewToOffer = interviews > 0 ? Math.round((offers / interviews) * 100) : 0;
  
  document.getElementById('appToInterview').style.width = appToInterview + '%';
  document.getElementById('appToInterviewPct').textContent = appToInterview + '%';
  document.getElementById('interviewToOffer').style.width = interviewToOffer + '%';
  document.getElementById('interviewToOfferPct').textContent = interviewToOffer + '%';
}

function renderFollowups() {
  const container = document.getElementById('followupList');
  
  const needFollowup = applications.filter(a => {
    if (['rejected', 'accepted', 'withdrawn', 'offer'].includes(a.status)) return false;
    const lastUpdate = new Date(a.updatedAt || a.date);
    const daysSince = (new Date() - lastUpdate) / (1000 * 60 * 60 * 24);
    return daysSince > 7;
  }).sort((a, b) => new Date(a.date) - new Date(b.date));
  
  if (needFollowup.length === 0) {
    container.innerHTML = '<p class="empty-text">No follow-ups needed</p>';
    return;
  }
  
  let html = '';
  needFollowup.forEach(app => {
    const daysAgo = Math.floor((new Date() - new Date(app.date)) / (1000 * 60 * 60 * 24));
    
    html += `
      <div class="followup-item">
        <div class="followup-info">
          <h4>${escapeHtml(app.company)}</h4>
          <p>${escapeHtml(app.position)}</p>
        </div>
        <span class="followup-days">${daysAgo} days ago</span>
        <button class="action-btn edit" onclick="showEditModal('${app.id}')" title="Update">✏️</button>
      </div>
    `;
  });
  
  container.innerHTML = html;
}

function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Close modal on outside click
document.getElementById('appModal')?.addEventListener('click', (e) => {
  if (e.target.id === 'appModal') closeModal();
});

// Initialize
init();