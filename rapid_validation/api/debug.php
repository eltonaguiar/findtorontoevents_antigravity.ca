<?php
header('Content-Type: text/plain');

$base_path = dirname(__DIR__);
$real_base_path = realpath(dirname(__DIR__));
echo "Base path: $base_path\n";
echo "Real base path: $real_base_path\n\n";
echo "Absolute base path:\n";
echo shell_exec("cd " . escapeshellarg($real_base_path) . " && pwd");
echo "\n\nTest Python command:\n";
$test_cmd = "cd " . escapeshellarg($real_base_path) . " && ls -la fast_validator_CLAUDECODE_Feb152026.py";
echo "Command: $test_cmd\n";
echo shell_exec($test_cmd);
echo "\n\nParent directory contents:\n";
echo shell_exec("ls -la ../");
echo "\n\nPython files check:\n";
echo shell_exec("ls -la ../*.py");
echo "\n\nPython location:\n";
echo shell_exec("which python3");
echo "\n\nCurrent directory:\n";
echo shell_exec("pwd");
