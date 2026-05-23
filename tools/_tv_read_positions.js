(function() {
  var tables = document.querySelectorAll('table');
  var out = [];
  for (var ti = 0; ti < tables.length; ti++) {
    var rows = tables[ti].querySelectorAll('tr');
    for (var i = 0; i < rows.length; i++) {
      var cells = rows[i].querySelectorAll('td');
      if (cells.length > 5) {
        var sym = cells[0] ? cells[0].textContent.trim() : '';
        if (sym && sym.indexOf(':') > -1) {
          var row = [];
          for (var c = 0; c < cells.length; c++) {
            row.push(cells[c].textContent.trim());
          }
          out.push(row.join(' | '));
        }
      }
    }
  }
  // Also pull balance from accountInfo
  var bal = '';
  var balEl = document.querySelector('[class*="balance"]') || document.querySelector('[class*="Balance"]');
  if (balEl) bal = balEl.textContent.trim();
  return JSON.stringify({ account: (document.querySelector('span.accountName-dm1wtgNn')||{}).textContent || '?',
                          balance: bal,
                          rows: out });
})()