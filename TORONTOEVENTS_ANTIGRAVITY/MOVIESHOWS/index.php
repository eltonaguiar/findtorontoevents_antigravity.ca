<?php
/**
 * MS1 Wrapper — Serves the existing index.html with upgrade toast injected.
 * When Apache serves /MOVIESHOWS/, DirectoryIndex prefers index.php over index.html.
 * This reads the original HTML and injects the upgrade toast script before </body>.
 */
$htmlFile = __DIR__ . '/index.html';
if (!file_exists($htmlFile)) {
    // Fallback: redirect to MS2 if original HTML is missing
    header('Location: ../MOVIESHOWS2/');
    exit;
}

$html = file_get_contents($htmlFile);

// Inject upgrade toast script before closing </body>
$inject = '<script src="ms1-upgrade-toast.js?v=20260219a"></script>';
$html = str_replace('</body>', $inject . '</body>', $html);

echo $html;
