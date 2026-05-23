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
  for($i=0; $i -lt 6; $i++){
    & node $tv ui eval "document.querySelector('button.dropdownButton-dm1wtgNn').click();'opened'" | Out-Null
    & node $tv ui eval "(function(){var d=document.querySelectorAll('div.middle-RDCgMoEQ.hasTitle-RDCgMoEQ');for(var i=0;i<d.length;i++){if(d[i].textContent.trim()==='$name'){d[i].click();return 'clicked';}}return 'nf';})()" | Out-Null
    Start-Sleep -Milliseconds 500
    $btn = & node $tv ui eval "(function(){var x=document.querySelector('button.dropdownButton-dm1wtgNn');return x?x.textContent.trim():'none';})()"
    if (($btn | Out-String) -like "*$name*") { return $true }
    Start-Sleep -Seconds 1
  }
  return $false
}

function Set-TpSl {
  param([string]$tp,[string]$sl)
  & node $tv ui eval "(function(){var sw=document.querySelectorAll('[role=""switch""]');for(var i=0;i<sw.length;i++){if(sw[i].offsetParent&&sw[i].getAttribute('aria-checked')==='false'){sw[i].click();}}return 'switch_ok';})()" | Out-Null
  & node $tv ui eval "(function(){var n=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;var inp=document.querySelectorAll('input');var v=[];for(var i=0;i<inp.length;i++){if(inp[i].offsetParent!==null&&inp[i].id!=='quantity-field')v.push(inp[i]);}if(v.length<4)return 'tpsl_nf_'+v.length;n.call(v[1],'$tp');v[1].dispatchEvent(new Event('input',{bubbles:true}));v[1].dispatchEvent(new Event('change',{bubbles:true}));n.call(v[3],'$sl');v[3].dispatchEvent(new Event('input',{bubbles:true}));v[3].dispatchEvent(new Event('change',{bubbles:true}));return 'tpsl_ok';})()" | Out-Null
}

function Set-PercentSize {
  param([string]$pct)
  # keep % balance mode; set very low percent for controlled sizing
  & node $tv ui eval "(function(){var q=document.getElementById('quantity-field');if(!q)return 'qty_nf';var s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;q.focus();s.call(q,'$pct');q.dispatchEvent(new Event('input',{bubbles:true}));q.dispatchEvent(new Event('change',{bubbles:true}));return 'qty='+q.value;})()" | Out-Null
}

function Execute-Order {
  param([string]$expectWord)
  $r = & node $tv ui eval "(function(){var b=document.querySelectorAll('button');for(var i=0;i<b.length;i++){var t=(b[i].textContent||'').trim();if(t.includes('Buy')&&t.includes('$expectWord')){b[i].click();return 'executed:'+t;}}return 'exec_nf';})()"
  $txt = ($r | Out-String).Trim()
  # Handle delayed-data modal if it appears.
  & node $tv ui eval "(function(){var body=document.body.innerText||'';if(body.indexOf('Send order without real-time data?')>-1){var nodes=document.querySelectorAll('*');for(var i=0;i<nodes.length;i++){var t=(nodes[i].textContent||'').trim();if(t==='Don\\'t ask again'){nodes[i].click();break;}}var btns=document.querySelectorAll('button');for(var j=0;j<btns.length;j++){var s=(btns[j].textContent||'').trim();if(s==='Send'){btns[j].click();return 'modal_send';}}return 'modal_no_send';}return 'modal_absent';})()" | Out-Null
  return $txt
}

function Verify-Ticker {
  param([string]$ticker)
  $p = & node $tv ui eval "(function(){var rows=document.querySelectorAll('table tr');for(var i=0;i<rows.length;i++){var c=rows[i].querySelectorAll('td');if(c.length>5){var s=(c[0]&&c[0].textContent||'').trim();if(s.indexOf('$ticker')!==-1){return 'POS:'+s;}}}return 'POS_NF';})()"
  $pt = ($p | Out-String).Trim()
  if ($pt -like "*POS:*") { return $pt }
  & node $tv ui eval "(function(){var e=document.querySelectorAll('button,div,[role=tab]');for(var i=0;i<e.length;i++){var t=(e[i].textContent||'').trim();if(t.startsWith('Orders')){e[i].click();return 'orders';}}return 'orders_nf';})()" | Out-Null
  $o = & node $tv ui eval "(function(){var rows=document.querySelectorAll('table tr');for(var i=0;i<rows.length;i++){var c=rows[i].querySelectorAll('td');if(c.length>=3){var s=(c[0]&&c[0].textContent||'').trim();if(s.indexOf('$ticker')!==-1){return 'ORD:'+s;}}}return 'ORD_NF';})()"
  return ($o | Out-String).Trim()
}

function Place-One {
  param(
    [string]$symbol,
    [string]$orderType,  # Market or Limit
    [string]$tp,
    [string]$sl,
    [string]$ticker
  )
  & node $tv symbol $symbol | Out-Null
  Start-Sleep -Milliseconds 400
  & node $tv ui click -b text -v Trade | Out-Null
  & node $tv ui click -b text -v $orderType | Out-Null
  & node $tv ui click -b data-name -v side-control-buy | Out-Null
  Set-PercentSize "1"
  Set-TpSl $tp $sl
  $exec = Execute-Order $orderType.ToUpper()
  Start-Sleep -Seconds 12
  $ver = Verify-Ticker $ticker
  Write-Output ("ORDER|$symbol|$orderType|$exec|$ver")
}

foreach($a in $accounts){
  Write-Output ("ACCOUNT_START|$a")
  if(-not (Switch-Account $a)){
    Write-Output ("SWITCH_FAIL|$a")
    continue
  }

  # 1) Forex (24h): Market
  Place-One "OANDA:EURUSD" "Market" "1.1735" "1.1665" "EURUSD"

  # 2) ETF: try Market then fallback Limit if not visible in pos/orders
  Place-One "AMEX:GLD" "Market" "446.0" "432.0" "GLD"

  # 3) Futures: try Market then fallback Limit
  Place-One "NYMEX:NG1!" "Market" "2.75" "2.61" "NG1!"

  Write-Output ("ACCOUNT_DONE|$a")
}
