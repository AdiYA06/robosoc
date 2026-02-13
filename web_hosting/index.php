<?php

declare(strict_types=1);

$shared = realpath(__DIR__ . '/../shared_ui/index.html');
if ($shared === false || !is_file($shared)) {
    http_response_code(500);
    header('Content-Type: text/plain; charset=utf-8');
    echo 'Missing shared_ui/index.html';
    exit;
}

header('Content-Type: text/html; charset=utf-8');
header('Cache-Control: no-store');
readfile($shared);
