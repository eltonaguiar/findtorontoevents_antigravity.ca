// Salary Insights App

let allJobs = [];
let filteredJobs = [];
let currentFilter = 'all';
let charts = {};

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
  await loadJobData();
  setupEventListeners();
  renderDashboard();
});

async function loadJobData() {
  try {
    const response = await fetch('/gotjob/jobs.json');
    const data = await response.json();
    allJobs = (data.jobs || []).filter(job => job.salary && (job.salary.min || job.salary.max));
    filteredJobs = allJobs;
    console.log(`Loaded ${allJobs.length} jobs with salary data`);
  } catch (error) {
    console.error('Error loading job data:', error);
    allJobs = [];
    filteredJobs = [];
  }
}

function setupEventListeners() {
  // Filter buttons
  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentFilter = btn.dataset.filter;
      applyFilter();
    });
  });

  // Table search
  const searchInput = document.getElementById('tableSearch');
  searchInput.addEventListener('input', debounce(renderTable, 300));

  // Table sort
  document.getElementById('sortBy').addEventListener('change', renderTable);

  // Calculator
  document.getElementById('calculateBtn').addEventListener('click', calculateSalary);
}

function applyFilter() {
  if (currentFilter === 'all') {
    filteredJobs = allJobs;
  } else {
    filteredJobs = allJobs.filter(job =>
      job.title.toLowerCase().includes(currentFilter.toLowerCase())
    );
  }
  renderDashboard();
}

function renderDashboard() {
  updateStats();
  renderCharts();
  renderTable();
  updateInsights();
}

function updateStats() {
  const jobs = filteredJobs;

  if (jobs.length === 0) {
    document.getElementById('avgSalary').textContent = '$0';
    document.getElementById('totalJobs').textContent = '0';
    document.getElementById('totalCompanies').textContent = '0';
    document.getElementById('salaryRange').textContent = '$0 - $0';
    return;
  }

  // Calculate average salary
  const salaries = jobs.map(j => (j.salary.min + j.salary.max) / 2).filter(s => s > 0);
  const avgSalary = salaries.reduce((a, b) => a + b, 0) / salaries.length;

  // Get salary range
  const minSalary = Math.min(...jobs.map(j => j.salary.min || j.salary.max));
  const maxSalary = Math.max(...jobs.map(j => j.salary.max || j.salary.min));

  // Count unique companies
  const companies = new Set(jobs.map(j => j.company).filter(Boolean));

  document.getElementById('avgSalary').textContent = formatCurrency(avgSalary);
  document.getElementById('totalJobs').textContent = jobs.length.toLocaleString();
  document.getElementById('totalCompanies').textContent = companies.size.toLocaleString();
  document.getElementById('salaryRange').textContent = `${formatCurrency(minSalary)} - ${formatCurrency(maxSalary)}`;
}

function renderCharts() {
  renderSalaryDistribution();
  renderRoleComparison();
  renderCompanyChart();
}

function renderSalaryDistribution() {
  const ctx = document.getElementById('salaryDistChart');
  if (!ctx) return;

  // Destroy existing chart
  if (charts.salaryDist) charts.salaryDist.destroy();

  // Create salary buckets
  const buckets = {
    '< $80K': 0,
    '$80K - $100K': 0,
    '$100K - $120K': 0,
    '$120K - $150K': 0,
    '$150K - $200K': 0,
    '$200K+': 0
  };

  filteredJobs.forEach(job => {
    const avg = (job.salary.min + job.salary.max) / 2;
    if (avg < 80000) buckets['< $80K']++;
    else if (avg < 100000) buckets['$80K - $100K']++;
    else if (avg < 120000) buckets['$100K - $120K']++;
    else if (avg < 150000) buckets['$120K - $150K']++;
    else if (avg < 200000) buckets['$150K - $200K']++;
    else buckets['$200K+']++;
  });

  charts.salaryDist = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: Object.keys(buckets),
      datasets: [{
        label: 'Number of Jobs',
        data: Object.values(buckets),
        backgroundColor: 'rgba(102, 126, 234, 0.6)',
        borderColor: 'rgba(102, 126, 234, 1)',
        borderWidth: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(15, 15, 35, 0.9)',
          titleColor: '#fff',
          bodyColor: '#fff',
          borderColor: 'rgba(102, 126, 234, 0.5)',
          borderWidth: 1
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: { color: 'rgba(255, 255, 255, 0.7)' },
          grid: { color: 'rgba(255, 255, 255, 0.1)' }
        },
        x: {
          ticks: { color: 'rgba(255, 255, 255, 0.7)' },
          grid: { display: false }
        }
      }
    }
  });
}

function renderRoleComparison() {
  const ctx = document.getElementById('roleComparisonChart');
  if (!ctx) return;

  if (charts.roleComparison) charts.roleComparison.destroy();

  const roles = ['creative', 'technology', 'manager', 'management'];
  const roleData = roles.map(role => {
    const roleJobs = allJobs.filter(j => j.title.toLowerCase().includes(role));
    if (roleJobs.length === 0) return 0;
    const salaries = roleJobs.map(j => (j.salary.min + j.salary.max) / 2);
    return salaries.reduce((a, b) => a + b, 0) / salaries.length;
  });

  charts.roleComparison = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: roles.map(r => r.charAt(0).toUpperCase() + r.slice(1)),
      datasets: [{
        label: 'Average Salary',
        data: roleData,
        backgroundColor: [
          'rgba(102, 126, 234, 0.6)',
          'rgba(0, 210, 255, 0.6)',
          'rgba(17, 153, 142, 0.6)',
          'rgba(240, 147, 251, 0.6)'
        ],
        borderColor: [
          'rgba(102, 126, 234, 1)',
          'rgba(0, 210, 255, 1)',
          'rgba(17, 153, 142, 1)',
          'rgba(240, 147, 251, 1)'
        ],
        borderWidth: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(15, 15, 35, 0.9)',
          callbacks: {
            label: (context) => `Avg Salary: ${formatCurrency(context.parsed.y)}`
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            color: 'rgba(255, 255, 255, 0.7)',
            callback: (value) => formatCurrency(value)
          },
          grid: { color: 'rgba(255, 255, 255, 0.1)' }
        },
        x: {
          ticks: { color: 'rgba(255, 255, 255, 0.7)' },
          grid: { display: false }
        }
      }
    }
  });
}

function renderCompanyChart() {
  const ctx = document.getElementById('companyChart');
  if (!ctx) return;

  if (charts.company) charts.company.destroy();

  // Get top 10 companies by job count
  const companyCounts = {};
  filteredJobs.forEach(job => {
    if (job.company) {
      if (!companyCounts[job.company]) {
        companyCounts[job.company] = { count: 0, salaries: [] };
      }
      companyCounts[job.company].count++;
      companyCounts[job.company].salaries.push((job.salary.min + job.salary.max) / 2);
    }
  });

  const topCompanies = Object.entries(companyCounts)
    .sort((a, b) => b[1].count - a[1].count)
    .slice(0, 10);

  const labels = topCompanies.map(([company]) => company);
  const avgSalaries = topCompanies.map(([, data]) =>
    data.salaries.reduce((a, b) => a + b, 0) / data.salaries.length
  );

  charts.company = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Average Salary',
        data: avgSalaries,
        backgroundColor: 'rgba(0, 210, 255, 0.6)',
        borderColor: 'rgba(0, 210, 255, 1)',
        borderWidth: 2
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(15, 15, 35, 0.9)',
          callbacks: {
            label: (context) => `Avg Salary: ${formatCurrency(context.parsed.x)}`
          }
        }
      },
      scales: {
        x: {
          beginAtZero: true,
          ticks: {
            color: 'rgba(255, 255, 255, 0.7)',
            callback: (value) => formatCurrency(value)
          },
          grid: { color: 'rgba(255, 255, 255, 0.1)' }
        },
        y: {
          ticks: { color: 'rgba(255, 255, 255, 0.7)' },
          grid: { display: false }
        }
      }
    }
  });
}

function renderTable() {
  const tbody = document.getElementById('salaryTableBody');
  const loading = document.getElementById('tableLoading');
  const empty = document.getElementById('tableEmpty');
  const searchQuery = document.getElementById('tableSearch').value.toLowerCase();
  const sortBy = document.getElementById('sortBy').value;

  loading.style.display = 'flex';
  tbody.innerHTML = '';
  empty.style.display = 'none';

  setTimeout(() => {
    let jobs = [...filteredJobs];

    // Apply search
    if (searchQuery) {
      jobs = jobs.filter(job =>
        job.title.toLowerCase().includes(searchQuery) ||
        (job.company && job.company.toLowerCase().includes(searchQuery))
      );
    }

    // Apply sort
    jobs.sort((a, b) => {
      switch (sortBy) {
        case 'salary-desc':
          return (b.salary.max || b.salary.min) - (a.salary.max || a.salary.min);
        case 'salary-asc':
          return (a.salary.min || a.salary.max) - (b.salary.min || b.salary.max);
        case 'company':
          return (a.company || '').localeCompare(b.company || '');
        case 'title':
          return a.title.localeCompare(b.title);
        default:
          return 0;
      }
    });

    // Limit to first 100 for performance
    jobs = jobs.slice(0, 100);

    if (jobs.length === 0) {
      loading.style.display = 'none';
      empty.style.display = 'block';
      return;
    }

    tbody.innerHTML = jobs.map(job => `
      <tr>
        <td>${job.title}</td>
        <td>${job.company || 'N/A'}</td>
        <td class="salary-highlight">
          ${formatCurrency(job.salary.min || job.salary.max)} - ${formatCurrency(job.salary.max || job.salary.min)}
        </td>
        <td>${job.location || 'Toronto, ON'}</td>
        <td><span class="source-badge">${job.source || 'Unknown'}</span></td>
      </tr>
    `).join('');

    loading.style.display = 'none';
  }, 100);
}

function calculateSalary() {
  const role = document.getElementById('calcRole').value;
  const experience = document.getElementById('calcExperience').value;

  // Filter jobs by role
  const roleJobs = allJobs.filter(j => j.title.toLowerCase().includes(role));

  if (roleJobs.length === 0) {
    alert('Not enough data for this role type');
    return;
  }

  // Calculate base range
  const salaries = roleJobs.map(j => (j.salary.min + j.salary.max) / 2).sort((a, b) => a - b);
  const p25 = salaries[Math.floor(salaries.length * 0.25)];
  const p75 = salaries[Math.floor(salaries.length * 0.75)];

  // Adjust for experience
  const multipliers = {
    junior: 0.7,
    mid: 1.0,
    senior: 1.3,
    lead: 1.6
  };

  const multiplier = multipliers[experience] || 1.0;
  const min = Math.round(p25 * multiplier / 1000) * 1000;
  const max = Math.round(p75 * multiplier / 1000) * 1000;

  // Display result
  document.getElementById('calcMin').textContent = formatCurrency(min);
  document.getElementById('calcMax').textContent = formatCurrency(max);
  document.getElementById('calcSampleSize').textContent = roleJobs.length;
  document.getElementById('calcResult').style.display = 'block';
}

function updateInsights() {
  // Most in-demand role
  const roleCounts = {};
  const roles = ['creative', 'technology', 'manager', 'management'];
  roles.forEach(role => {
    roleCounts[role] = allJobs.filter(j => j.title.toLowerCase().includes(role)).length;
  });
  const topRole = Object.entries(roleCounts).sort((a, b) => b[1] - a[1])[0];
  document.getElementById('topRole').textContent =
    `${topRole[0].charAt(0).toUpperCase() + topRole[0].slice(1)} (${topRole[1]} jobs)`;

  // Highest paying
  const highestJob = allJobs.reduce((max, job) =>
    (job.salary.max > (max.salary?.max || 0)) ? job : max
    , {});
  if (highestJob.salary) {
    document.getElementById('highestPaying').textContent =
      `${highestJob.title.substring(0, 30)}... (${formatCurrency(highestJob.salary.max)})`;
  }
}

// Utility functions
function formatCurrency(value) {
  if (!value || value === 0) return '$0';
  return new Intl.NumberFormat('en-CA', {
    style: 'currency',
    currency: 'CAD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(value);
}

function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}
