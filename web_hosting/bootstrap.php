<?php

declare(strict_types=1);

header('Cache-Control: no-store');

$configPath = __DIR__ . '/config.php';
if (!file_exists($configPath)) {
    http_response_code(500);
    header('Content-Type: application/json');
    echo json_encode(['ok' => false, 'error' => 'missing_config']);
    exit;
}
require_once $configPath;

if (defined('ALLOW_ORIGIN') && ALLOW_ORIGIN !== '') {
    header('Access-Control-Allow-Origin: ' . ALLOW_ORIGIN);
    header('Vary: Origin');
}

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    header('Access-Control-Allow-Headers: Content-Type, X-API-Token');
    header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
    http_response_code(204);
    exit;
}

function json_response(int $status, array $payload): void {
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($payload);
    exit;
}

function db(): PDO {
    static $pdo = null;
    if ($pdo instanceof PDO) {
        return $pdo;
    }

    try {
        $dsn = sprintf('mysql:host=%s;dbname=%s;charset=utf8mb4', DB_HOST, DB_NAME);
        $pdo = new PDO($dsn, DB_USER, DB_PASS, [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES => false,
        ]);
    } catch (Throwable $e) {
        $payload = ['ok' => false, 'error' => 'db_connect_failed'];
        if (defined('DEBUG_ERRORS') && DEBUG_ERRORS === true) {
            $payload['detail'] = $e->getMessage();
        }
        json_response(500, $payload);
    }
    return $pdo;
}

function api_token_from_request(): string {
    $headerToken = $_SERVER['HTTP_X_API_TOKEN'] ?? '';
    if ($headerToken !== '') {
        return trim((string)$headerToken);
    }

    $body = file_get_contents('php://input') ?: '';
    if ($body !== '') {
        $decoded = json_decode($body, true);
        if (is_array($decoded) && isset($decoded['api_token'])) {
            return trim((string)$decoded['api_token']);
        }
    }

    if (isset($_GET['api_token'])) {
        return trim((string)$_GET['api_token']);
    }

    return '';
}

function require_api_token(): void {
    $token = api_token_from_request();
    if ($token === '' || !hash_equals(API_TOKEN, $token)) {
        json_response(401, ['ok' => false, 'error' => 'unauthorized']);
    }
}

function clamp_float(mixed $value, float $lo, float $hi, float $default): float {
    if (!is_numeric($value)) {
        return $default;
    }
    $x = (float)$value;
    if ($x < $lo) {
        return $lo;
    }
    if ($x > $hi) {
        return $hi;
    }
    return $x;
}
