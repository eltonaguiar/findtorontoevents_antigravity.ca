<?php
header('Content-Type: text/plain');

$base_path = dirname(__DIR__);
echo "Base path: $base_path\n\n";
echo "Directory contents:\n";
echo shell_exec("ls -la " . escapeshellarg($base_path));
echo "\n\nPython location:\n";
echo shell_exec("which python3");
echo "\n\nCurrent directory:\n";
echo shell_exec("pwd");
