(function() {
  // Capture all tabs of the bottom panel: Positions, Orders, Working, Trade History, etc.
  var tabBar = document.querySelectorAll('[role="tab"], button[data-name*="tab"]');
  var tabs = [];
  for (var t = 0; t < tabBar.length; t++) {
    tabs.push((tabBar[t].textContent || '').trim());
  }
  // Capture all visible table rows from any table on the page
  var tables = document.querySelectorAll('table');
  var allRows = [];
  for (var ti = 0; ti < tables.length; ti++) {
    var rows = tables[ti].querySelectorAll('tr');
    for (var i = 0; i < rows.length; i++) {
      var cells = rows[i].querySelectorAll('td');
      if (cells.length > 4) {
        var sym = cells[0] ? cells[0].textContent.trim() : '';
        if (sym && (sym.indexOf(':') > -1 || /^[A-Z]{3,8}$/.test(sym))) {
          var row = [];
          for (var c = 0; c < cells.length; c++) {
            row.push(cells[c].textContent.trim());
          }
          allRows.push('T' + ti + ': ' + row.join(' | '));
        }
      }
    }
  }
  // Try to read account balance from header chips
  var chips = document.querySelectorAll('[class*="value"], [class*="Value"]');
  var bal = '';
  for (var k = 0; k < chips.length; k++) {
    var txt = (chips[k].textContent || '').trim();
    if (/^\$?[\d,.]+\s*(USD|USDT)?$/.test(txt) && txt.length > 5 && txt.length < 25) {
      bal = txt; break;
    }
  }
  return JSON.stringify({
    account: (document.querySelector('span.accountName-dm1wtgNn')||{}).textContent || '?',
    balance: bal,
    tabs: tabs,
    rows: allRows,
  });
})()