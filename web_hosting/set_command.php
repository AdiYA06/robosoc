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

$clientId = substr(trim((string)($payload['client_id'] ?? '')), 0, 128);
if ($clientId === '') {
    json_response(400, ['ok' => false, 'error' => 'missing_client_id']);
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

$pdo = db();
$timeout = lock_timeout_seconds();

try {
    $pdo->beginTransaction();

    $ensureStmt = $pdo->prepare(
        'INSERT INTO hexapod_command (id, mode, vx, vy, turn_rate, speed, height, client_id, lock_owner_id, lock_seen_at)
         VALUES (1, "stop", 0, 0, 0, 0.4, 0, "", "", NULL)
         ON DUPLICATE KEY UPDATE id = id'
    );
    $ensureStmt->execute();

    $rowStmt = $pdo->query(
        'SELECT mode, vx, vy, turn_rate, speed, height, client_id, lock_owner_id,
                UNIX_TIMESTAMP(lock_seen_at) AS lock_seen_unix
         FROM hexapod_command
         WHERE id = 1
         LIMIT 1
         FOR UPDATE'
    );
    $row = $rowStmt->fetch();
    if (!$row) {
        throw new RuntimeException('missing_row_after_insert');
    }

    $currentOwner = (string)($row['lock_owner_id'] ?? '');
    $lockSeenUnix = isset($row['lock_seen_unix']) ? (float)$row['lock_seen_unix'] : 0.0;
    $lockActive = $currentOwner !== '' && $lockSeenUnix > 0 && (microtime(true) - $lockSeenUnix) <= $timeout;

    if ($lockActive && $currentOwner !== $clientId) {
        $pdo->rollBack();
        json_response(409, [
            'ok' => false,
            'error' => 'locked',
            'lock' => [
                'active' => true,
                'owner_id' => $currentOwner,
                'timeout_s' => $timeout,
            ],
        ]);
    }

    $updateStmt = $pdo->prepare(
        'UPDATE hexapod_command
         SET mode = :mode,
             vx = :vx,
             vy = :vy,
             turn_rate = :turn_rate,
             speed = :speed,
             height = :height,
             client_id = :client_id,
             lock_owner_id = :lock_owner_id,
             lock_seen_at = CURRENT_TIMESTAMP(6),
             updated_at = CURRENT_TIMESTAMP(6)
         WHERE id = 1'
    );
    $updateStmt->execute([
        ':mode' => $mode,
        ':vx' => $vx,
        ':vy' => $vy,
        ':turn_rate' => $turnRate,
        ':speed' => $speed,
        ':height' => $height,
        ':client_id' => $clientId,
        ':lock_owner_id' => $clientId,
    ]);

    $pdo->commit();
} catch (Throwable $e) {
    if ($pdo->inTransaction()) {
        $pdo->rollBack();
    }
    $payload = ['ok' => false, 'error' => 'db_query_failed'];
    if (defined('DEBUG_ERRORS') && DEBUG_ERRORS === true) {
        $payload['detail'] = $e->getMessage();
    }
    json_response(500, $payload);
}

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
    'lock' => [
        'active' => true,
        'owner_id' => $clientId,
        'timeout_s' => $timeout,
    ],
]);
