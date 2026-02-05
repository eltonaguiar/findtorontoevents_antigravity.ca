$filePath = 'E:\findtorontoevents_antigravity.ca\favcreators\src\App.tsx'
$lines = Get-Content $filePath

for ($i = 747; $i -le 760; $i++) {
    if ($lines[$i] -match '^  // ') {
        $lines[$i] = $lines[$i] -replace '^  // ', '  '
    }
}

$lines | Set-Content $filePath
Write-Host "Uncommented lines 748-761"
