$ErrorActionPreference = "Continue"
$tv = "node_modules/tradingview-mcp/src/cli/index.js"

$accounts = @(
  "HYROTRADER",
  "AG_PROVENEDGETEST",
  "HYROTRADER2",
  "TESTER",
  "BROKIE",
  "zerounderscore",
  "XIAOMI MIMO",
  "SCALPER",
  "CURSORTEST",
  "TRUSTOURSCORE",
  "THEWINNERS"
)

function Switch-Account {
  param([string]$name)
  for($i=0; $i -lt 4; $i++){
    & node $tv ui eval "document.querySelector('button.dropdownButton-dm1wtgNn').click();'opened'" | Out-Null
    & node $tv ui eval "(function(){var d=document.querySelectorAll('div.middle-RDCgMoEQ.hasTitle-RDCgMoEQ');for(var i=0;i<d.length;i++){if(d[i].textContent.trim()==='$name'){d[i].click();return 'clicked';}}return 'nf';})()" | Out-Null
    Start-Sleep -Milliseconds 250
    $b = & node $tv ui eval "(function(){var x=document.querySelector('button.dropdownButton-dm1wtgNn');return x?x.textContent.trim():'none';})()"
    if (($b | Out-String) -like "*$name*") { return $true }
  }
  return $false
}

function Verify-Ticker {
  param([string]$ticker)
  $v1 = & node $tv ui eval "(function(){var rows=document.querySelectorAll('table tr');for(var i=0;i<rows.length;i++){var c=rows[i].querySelectorAll('td');if(c.length>5){var s=(c[0]&&c[0].textContent||'').trim();if(s.indexOf('$ticker')!==-1){return 'POS:'+s;}}}return 'POS_NF';})()"
  if (($v1 | Out-String) -like "*POS:*") { return ($v1 | Out-String).Trim() }
  & node $tv ui eval "(function(){var e=document.querySelectorAll('button,div,[role=tab]');for(var i=0;i<e.length;i++){var t=(e[i].textContent||'').trim();if(t.startsWith('Orders')){e[i].click();return 'orders';}}return 'nf';})()" | Out-Null
  $v2 = & node $tv ui eval "(function(){var rows=document.querySelectorAll('table tr');for(var i=0;i<rows.length;i++){var c=rows[i].querySelectorAll('td');if(c.length>=3){var s=(c[0]&&c[0].textContent||'').trim();if(s.indexOf('$ticker')!==-1){return 'ORD:'+s;}}}return 'ORD_NF';})()"
  return ($v2 | Out-String).Trim()
}

function Place-Long {
  param(
    [string]$symbol,
    [string]$qty,
    [string]$tp,
    [string]$sl
  )
  & node $tv symbol $symbol | Out-Null
  Start-Sleep -Milliseconds 250
  & node $tv ui click -b text -v Trade | Out-Null
  & node $tv ui click -b text -v Market | Out-Null
  & node $tv ui click -b data-name -v side-control-buy | Out-Null
  & node $tv ui eval "(function(){var q=document.getElementById('quantity-field');if(!q)return 'qty_nf';var s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;q.focus();s.call(q,'$qty');q.dispatchEvent(new Event('input',{bubbles:true}));q.dispatchEvent(new Event('change',{bubbles:true}));return 'ok';})()" | Out-Null
  & node $tv ui eval "(function(){var sw=document.querySelectorAll('[role=""switch""]');for(var i=0;i<sw.length;i++){if(sw[i].offsetParent&&sw[i].getAttribute('aria-checked')==='false'){sw[i].click();}}return 'ok';})()" | Out-Null
  & node $tv ui eval "(function(){var n=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;var inp=document.querySelectorAll('input');var v=[];for(var i=0;i<inp.length;i++){if(inp[i].offsetParent!==null&&inp[i].id!=='quantity-field')v.push(inp[i]);}if(v.length<4)return 'tpsl_nf';n.call(v[1],'$tp');v[1].dispatchEvent(new Event('input',{bubbles:true}));v[1].dispatchEvent(new Event('change',{bubbles:true}));n.call(v[3],'$sl');v[3].dispatchEvent(new Event('input',{bubbles:true}));v[3].dispatchEvent(new Event('change',{bubbles:true}));return 'tpsl_ok';})()" | Out-Null
  $exec = & node $tv ui eval "(function(){var b=document.querySelectorAll('button');for(var i=0;i<b.length;i++){var t=b[i].textContent.trim();if((t.includes('Buy')||t.includes('Sell'))&&t.includes('MARKET')){b[i].click();return t;}}return 'exec_nf';})()"
  $execTxt = ($exec | Out-String).Trim()
  if ($execTxt -like "* 0 *") { return "ZERO|$execTxt" }
  return "OK|$execTxt"
}

foreach($a in $accounts){
  Write-Output ("ACCOUNT_START|$a")
  if(-not (Switch-Account $a)){
    Write-Output ("SWITCH_FAIL|$a")
    continue
  }

  $gld = Place-Long "AMEX:GLD" "120" "446.50" "432.00"
  $gldV = Verify-Ticker "GLD"
  Write-Output ("GLD|$a|$gld|$gldV")

  $ng = Place-Long "NYMEX:NG1!" "120" "2.75" "2.61"
  $ngV = Verify-Ticker "NG1!"
  Write-Output ("NG1|$a|$ng|$ngV")

  Write-Output ("ACCOUNT_DONE|$a")
}
