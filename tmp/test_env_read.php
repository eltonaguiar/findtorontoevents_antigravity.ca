<?php
header("Content-Type: text/plain");
echo "PHP version: " . phpversion() . "\n";
$f = dirname(__FILE__) . "/.env";
echo "env path: " . $f . "\n";
echo "exists: " . (file_exists($f) ? "yes" : "no") . "\n";
echo "readable: " . (is_readable($f) ? "yes" : "no") . "\n";
if (file_exists($f)) {
    echo "size: " . filesize($f) . "\n";
    $raw = file_get_contents($f);
    echo "content length: " . strlen($raw) . "\n";
    echo "first 100 chars: " . substr($raw, 0, 100) . "\n";
    $lines = preg_split('/\r?\n/', $raw);
    echo "line count: " . count($lines) . "\n";
    foreach ($lines as $i => $line) {
        $line = trim($line);
        if ($line === '' || $line[0] === '#') continue;
        $eq = strpos($line, '=');
        if ($eq === false) continue;
        $k = trim(substr($line, 0, $eq));
        $val = substr($line, $eq + 1);
        echo "  key=$k val_len=" . strlen($val) . "\n";
    }
}
?>