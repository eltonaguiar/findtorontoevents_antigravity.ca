<?php
header('Content-Type: text/plain');

$base_path = dirname(__DIR__);
echo "Base path: $base_path\n\n";
echo "Absolute base path:\n";
echo shell_exec("cd " . escapeshellarg($base_path) . " && pwd");
echo "\n\nParent directory contents:\n";
echo shell_exec("ls -la ../");
echo "\n\nPython files check:\n";
echo shell_exec("ls -la ../*.py");
echo "\n\nPython location:\n";
echo shell_exec("which python3");
echo "\n\nCurrent directory:\n";
echo shell_exec("pwd");
