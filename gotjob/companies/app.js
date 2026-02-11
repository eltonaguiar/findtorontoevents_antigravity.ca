let allJobs = [];
let companies = [];
let displayCount = 30;

function el(id) { return document.getElementById(id); }

function formatK(n) {
  if (n >= 1000) return `$${Math.round(n / 1000)}K`;
  return `$${Math.round(n).toLocaleString()}`;
}

function getAnnualSalary(job) {
  if (!job.salary) return null;
  const s = job.salary;
  if (s.type === 'hourly') return s.min ? s.min * 2080 : null;
  return s.max || s.min || null;
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  if (isNaN(d)) return '';
  const now = new Date();
  const diffDays = Math.floor((now - d) / (1000 * 60 * 60 * 24));
  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays}d ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
  return d.toLocaleDateString('en-CA', { month: 'short', day: 'numeric' });
}

function detectWorkArrangement(job) {
  const text = `${job.title} ${job.location} ${job.excerpt || ''}`.toLowerCase();
  if (text.includes('remote') || text.includes('work from home') || text.includes('wfh')) return 'remote';
  if (text.includes('hybrid')) return 'hybrid';
  return 'onsite';
}

function classifyIndustry(company, jobs) {
  const c = company.toLowerCase();
  const allText = jobs.map(j => `${j.title} ${j.source || ''}`).join(' ').toLowerCase();

  if (/\b(rbc|td|scotiabank|bmo|cibc|royal bank|toronto.dominion|bank of montreal)\b/i.test(c)) return 'finance';
  if (/\b(manulife|sun life|sunlife|intact|great.west|canada life)\b/i.test(c)) return 'insurance';
  if (/\b(rogers|bell|telus|shaw|videotron|cogeco)\b/i.test(c)) return 'telecom';
  if (/\b(deloitte|kpmg|pwc|ey|ernst|accenture|mckinsey|bain|bcg|capgemini)\b/i.test(c)) return 'consulting';
  if (/\b(robert half|teksystems|randstad|hays|procom|s\.i\. systems|adecco|manpower)\b/i.test(c)) return 'staffing';
  if (/\b(shopify|wealthsimple|1password|lightspeed|hootsuite|clio|ada|google|microsoft|amazon|meta|apple|salesforce)\b/i.test(c)) return 'tech';
  if (allText.includes('greenhouse') || allText.includes('lever') || allText.includes('ashby')) return 'tech';

  return 'other';
}

function getTopRoles(jobs, limit) {
  limit = limit || 5;
  const roleMap = {};
  for (const j of jobs) {
    const title = j.title.replace(/\s*(sr\.?|senior|junior|jr\.?|lead|principal|staff)\s*/gi, ' ').trim().substring(0, 40);
    roleMap[title] = (roleMap[title] || 0) + 1;
  }
  return Object.entries(roleMap).sort((a, b) => b[1] - a[1]).slice(0, limit).map(function(e) { return e[0]; });
}

async function loadJobs() {
  const res = await fetch('/gotjob/jobs.json?t=' + Date.now());
  if (!res.ok) throw new Error('Failed to load jobs');
  const data = await res.json();
  allJobs = Array.isArray(data.jobs) ? data.jobs : (Array.isArray(data) ? data : []);
}

function buildCompanyData() {
  const companyMap = {};

  for (var i = 0; i < allJobs.length; i++) {
    const j = allJobs[i];
    const name = (j.company || '').trim();
    if (!name || name.length < 2) continue;

    if (!companyMap[name]) {
      companyMap[name] = {
        name: name,
        jobs: [],
        salaries: [],
        remoteCount: 0,
        latestDate: null,
      };
    }

    const entry = companyMap[name];
    entry.jobs.push(j);

    const salary = getAnnualSalary(j);
    if (salary && salary > 20000 && salary < 500000) entry.salaries.push(salary);

    if (detectWorkArrangement(j) === 'remote') entry.remoteCount++;

    const date = j.postedDate || j.scrapedAt;
    if (date && (!entry.latestDate || date > entry.latestDate)) {
      entry.latestDate = date;
    }
  }

  companies = Object.values(companyMap).map(function(c) {
    return {
      name: c.name,
      jobs: c.jobs,
      salaries: c.salaries,
      remoteCount: c.remoteCount,
      latestDate: c.latestDate,
      jobCount: c.jobs.length,
      avgSalary: c.salaries.length ? Math.round(c.salaries.reduce(function(a, b) { return a + b; }, 0) / c.salaries.length) : 0,
      hasSalary: c.salaries.length > 0,
      industry: classifyIndustry(c.name, c.jobs),
      topRoles: getTopRoles(c.jobs),
    };
  });
}

function filterAndSort() {
  const search = el('companySearch').value.toLowerCase().trim();
  const industry = el('industryFilter').value;
  const sortBy = el('sortBy').value;

  var filtered = companies.filter(function(c) {
    if (search && !c.name.toLowerCase().includes(search)) return false;
    if (industry !== 'all' && c.industry !== industry) return false;
    return true;
  });

  filtered.sort(function(a, b) {
    switch (sortBy) {
      case 'jobs': return b.jobCount - a.jobCount;
      case 'salary': return b.avgSalary - a.avgSalary;
      case 'name': return a.name.localeCompare(b.name);
      case 'fresh': return (b.latestDate || '').localeCompare(a.latestDate || '');
      default: return 0;
    }
  });

  return filtered;
}

function renderStats(filtered) {
  el('statCompanies').textContent = filtered.length.toLocaleString();
  el('statOpenRoles').textContent = filtered.reduce(function(s, c) { return s + c.jobCount; }, 0).toLocaleString();

  const avgJobs = filtered.length ? Math.round(filtered.reduce(function(s, c) { return s + c.jobCount; }, 0) / filtered.length) : 0;
  el('statAvgJobs').textContent = avgJobs;

  const withSalary = filtered.filter(function(c) { return c.hasSalary; }).length;
  el('statWithSalary').textContent = filtered.length ? Math.round(withSalary / filtered.length * 100) + '%' : '-';
}

function renderCompanies(filtered) {
  const grid = el('companyGrid');
  grid.innerHTML = '';

  const display = filtered.slice(0, displayCount);

  el('resultsMeta').innerHTML = '<strong>' + filtered.length + '</strong> companies found';

  if (!display.length) {
    grid.innerHTML = '<div class="loading">No companies match your search</div>';
    el('loadMore').style.display = 'none';
    return;
  }

  const industryLabels = {
    tech: 'Technology', finance: 'Banking', consulting: 'Consulting',
    telecom: 'Telecom', insurance: 'Insurance', staffing: 'Staffing', other: 'Other'
  };

  for (var i = 0; i < display.length; i++) {
    const c = display[i];
    const card = document.createElement('div');
    card.className = 'company-card';
    card.dataset.companyIndex = i;

    var html = '<div class="company-top">' +
      '<div class="company-name">' + c.name + '</div>' +
      '<div class="company-badge">' + c.jobCount + ' jobs</div>' +
      '</div>' +
      '<div class="company-meta">' +
      '<span class="company-tag industry">' + (industryLabels[c.industry] || 'Other') + '</span>';

    if (c.avgSalary) html += '<span class="company-tag salary">Avg ' + formatK(c.avgSalary) + '</span>';
    if (c.remoteCount > 0) html += '<span class="company-tag remote">' + c.remoteCount + ' remote</span>';

    html += '</div>' +
      '<div class="company-stats">' +
      '<div class="company-stat"><div class="cs-value">' + c.jobCount + '</div><div class="cs-label">Open roles</div></div>' +
      '<div class="company-stat"><div class="cs-value">' + (c.avgSalary ? formatK(c.avgSalary) : 'N/A') + '</div><div class="cs-label">Avg salary</div></div>' +
      '<div class="company-stat"><div class="cs-value">' + (c.latestDate ? formatDate(c.latestDate) : '-') + '</div><div class="cs-label">Latest post</div></div>' +
      '</div>';

    if (c.topRoles.length) {
      html += '<div class="company-roles">';
      for (var r = 0; r < c.topRoles.length; r++) {
        html += '<span class="role-pill">' + c.topRoles[r] + '</span>';
      }
      html += '</div>';
    }

    card.innerHTML = html;

    // Closure to capture company reference
    (function(company) {
      card.addEventListener('click', function() { showCompanyModal(company); });
    })(c);

    grid.appendChild(card);
  }

  el('loadMore').style.display = displayCount < filtered.length ? 'inline-block' : 'none';
}

function showCompanyModal(company) {
  const modal = el('companyModal');
  const body = el('modalBody');

  const sortedJobs = company.jobs.slice().sort(function(a, b) {
    const dateA = a.postedDate || a.scrapedAt || '';
    const dateB = b.postedDate || b.scrapedAt || '';
    return dateB.localeCompare(dateA);
  });

  var salaryRange = 'N/A';
  if (company.salaries.length >= 2) {
    salaryRange = formatK(Math.min.apply(null, company.salaries)) + ' - ' + formatK(Math.max.apply(null, company.salaries));
  } else if (company.avgSalary) {
    salaryRange = formatK(company.avgSalary);
  }

  var jobListHtml = '';
  for (var i = 0; i < sortedJobs.length; i++) {
    var j = sortedJobs[i];
    var salary = getAnnualSalary(j);
    jobListHtml += '<div class="modal-job">' +
      '<a href="' + j.url + '" target="_blank" rel="noreferrer">' + j.title + '</a>' +
      (salary ? '<span class="mj-salary">' + formatK(salary) + '</span>' : '') +
      '<span class="mj-date">' + formatDate(j.postedDate || j.scrapedAt) + '</span>' +
      '</div>';
  }

  body.innerHTML = '<div class="modal-header">' +
    '<h2>' + company.name + '</h2>' +
    '<div class="modal-subtitle">' + company.jobCount + ' open positions</div>' +
    '</div>' +
    '<div class="modal-stats">' +
    '<div class="modal-stat"><div class="ms-value">' + company.jobCount + '</div><div class="ms-label">Open Roles</div></div>' +
    '<div class="modal-stat"><div class="ms-value">' + (company.avgSalary ? formatK(company.avgSalary) : 'N/A') + '</div><div class="ms-label">Avg Salary</div></div>' +
    '<div class="modal-stat"><div class="ms-value">' + salaryRange + '</div><div class="ms-label">Salary Range</div></div>' +
    '<div class="modal-stat"><div class="ms-value">' + company.remoteCount + '</div><div class="ms-label">Remote Jobs</div></div>' +
    '</div>' +
    '<div class="modal-section">' +
    '<h3>All Open Positions</h3>' +
    '<div class="modal-job-list">' + jobListHtml + '</div>' +
    '</div>';

  modal.style.display = 'flex';
}

function bindEvents() {
  var refresh = function() {
    displayCount = 30;
    var filtered = filterAndSort();
    renderStats(filtered);
    renderCompanies(filtered);
  };

  el('searchBtn').addEventListener('click', refresh);
  el('companySearch').addEventListener('keypress', function(e) { if (e.key === 'Enter') refresh(); });
  el('industryFilter').addEventListener('change', refresh);
  el('sortBy').addEventListener('change', refresh);

  el('loadMore').addEventListener('click', function() {
    displayCount += 30;
    renderCompanies(filterAndSort());
  });

  el('closeModal').addEventListener('click', function() {
    el('companyModal').style.display = 'none';
  });

  el('companyModal').addEventListener('click', function(e) {
    if (e.target === el('companyModal')) {
      el('companyModal').style.display = 'none';
    }
  });

  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') el('companyModal').style.display = 'none';
  });
}

async function init() {
  try {
    await loadJobs();
    buildCompanyData();
    var filtered = filterAndSort();
    renderStats(filtered);
    renderCompanies(filtered);
    bindEvents();
  } catch (e) {
    el('companyGrid').innerHTML = '<div class="loading">Error loading data: ' + e.message + '</div>';
  }
}

init();
