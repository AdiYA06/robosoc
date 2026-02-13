<?php

declare(strict_types=1);

require_once __DIR__ . '/bootstrap.php';

if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
    json_response(405, ['ok' => false, 'error' => 'method_not_allowed']);
}
require_api_token();

$pdo = db();
$stmt = $pdo->query(
    'SELECT id, mode, vx, vy, turn_rate, speed, height, client_id, UNIX_TIMESTAMP(updated_at) AS updated_unix
     FROM hexapod_command
     WHERE id = 1
     LIMIT 1'
);
$row = $stmt->fetch();

if (!$row) {
    json_response(404, ['ok' => false, 'error' => 'command_not_initialized']);
}

$updatedUnix = (float)$row['updated_unix'];
$now = microtime(true);
$age = max(0.0, $now - $updatedUnix);

json_response(200, [
    'ok' => true,
    'state' => [
        'mode' => (string)$row['mode'],
        'vx' => (float)$row['vx'],
        'vy' => (float)$row['vy'],
        'turn' => (float)$row['turn_rate'],
        'speed' => (float)$row['speed'],
        'height' => (float)$row['height'],
        'client_id' => (string)$row['client_id'],
        'updated_unix' => $updatedUnix,
        'age_s' => $age,
    ],
]);
