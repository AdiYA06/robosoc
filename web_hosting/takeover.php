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

$pdo = db();
$timeout = lock_timeout_seconds();

try {
    $pdo->beginTransaction();

    $ensureStmt = $pdo->prepare(
        'INSERT INTO hexapod_command (id, mode, vx, vy, turn_rate, speed, height, client_id, lock_owner_id, lock_seen_at)
         VALUES (1, "init", 0, 0, 0, 0.4, 0, "", "", NULL)
         ON DUPLICATE KEY UPDATE id = id'
    );
    $ensureStmt->execute();

    $takeStmt = $pdo->prepare(
        'UPDATE hexapod_command
         SET lock_owner_id = :client_id,
             lock_seen_at = CURRENT_TIMESTAMP(6)
         WHERE id = 1'
    );
    $takeStmt->execute([':client_id' => $clientId]);

    $pdo->commit();
} catch (Throwable $e) {
    if ($pdo->inTransaction()) {
        $pdo->rollBack();
    }
    $out = ['ok' => false, 'error' => 'db_query_failed'];
    if (defined('DEBUG_ERRORS') && DEBUG_ERRORS === true) {
        $out['detail'] = $e->getMessage();
    }
    json_response(500, $out);
}

json_response(200, [
    'ok' => true,
    'lock' => [
        'active' => true,
        'owner_id' => $clientId,
        'timeout_s' => $timeout,
    ],
]);
