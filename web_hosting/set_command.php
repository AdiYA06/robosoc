<?php

declare(strict_types=1);

require_once __DIR__ . '/bootstrap.php';

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    json_response(405, ['ok' => false, 'error' => 'method_not_allowed']);
}
require_api_token();

$raw = file_get_contents('php://input') ?: '';
$payload = json_decode($raw, true);
if (!is_array($payload)) {
    json_response(400, ['ok' => false, 'error' => 'invalid_json']);
}

$mode = strtolower(trim((string)($payload['mode'] ?? 'stop')));
$allowedModes = ['stop', 'walk', 'turn', 'stance'];
if (!in_array($mode, $allowedModes, true)) {
    $mode = 'stop';
}

$vx = clamp_float($payload['vx'] ?? null, -1.0, 1.0, 0.0);
$vy = clamp_float($payload['vy'] ?? null, -1.0, 1.0, 0.0);
$turnRate = clamp_float($payload['turn'] ?? null, -1.0, 1.0, 0.0);
$speed = clamp_float($payload['speed'] ?? null, 0.0, 1.0, 0.4);
$height = clamp_float($payload['height'] ?? null, -1.0, 1.0, 0.0);
$clientId = substr(trim((string)($payload['client_id'] ?? '')), 0, 128);

$pdo = db();
$stmt = $pdo->prepare(
    'INSERT INTO hexapod_command (id, mode, vx, vy, turn_rate, speed, height, client_id)
     VALUES (1, :mode, :vx, :vy, :turn_rate, :speed, :height, :client_id)
     ON DUPLICATE KEY UPDATE
       mode = VALUES(mode),
       vx = VALUES(vx),
       vy = VALUES(vy),
       turn_rate = VALUES(turn_rate),
       speed = VALUES(speed),
       height = VALUES(height),
       client_id = VALUES(client_id),
       updated_at = CURRENT_TIMESTAMP'
);
$stmt->execute([
    ':mode' => $mode,
    ':vx' => $vx,
    ':vy' => $vy,
    ':turn_rate' => $turnRate,
    ':speed' => $speed,
    ':height' => $height,
    ':client_id' => $clientId,
]);

json_response(200, [
    'ok' => true,
    'state' => [
        'mode' => $mode,
        'vx' => $vx,
        'vy' => $vy,
        'turn' => $turnRate,
        'speed' => $speed,
        'height' => $height,
        'client_id' => $clientId,
    ],
]);
