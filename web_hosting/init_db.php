<?php

declare(strict_types=1);

require_once __DIR__ . '/bootstrap.php';
require_api_token();

try {
    $pdo = db();
    $pdo->exec(
        'CREATE TABLE IF NOT EXISTS hexapod_command (
            id TINYINT UNSIGNED NOT NULL PRIMARY KEY,
            mode VARCHAR(16) NOT NULL DEFAULT "init",
            vx FLOAT NOT NULL DEFAULT 0,
            vy FLOAT NOT NULL DEFAULT 0,
            turn_rate FLOAT NOT NULL DEFAULT 0,
            speed FLOAT NOT NULL DEFAULT 0.4,
            height FLOAT NOT NULL DEFAULT 0,
            client_id VARCHAR(128) NOT NULL DEFAULT "",
            lock_owner_id VARCHAR(128) NOT NULL DEFAULT "",
            lock_seen_at TIMESTAMP(6) NULL DEFAULT NULL,
            updated_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4'
    );

    try {
        $pdo->exec('ALTER TABLE hexapod_command ADD COLUMN lock_owner_id VARCHAR(128) NOT NULL DEFAULT ""');
    } catch (Throwable $e) {
        if (stripos($e->getMessage(), 'Duplicate column name') === false) {
            throw $e;
        }
    }
    try {
        $pdo->exec('ALTER TABLE hexapod_command ADD COLUMN lock_seen_at TIMESTAMP(6) NULL DEFAULT NULL');
    } catch (Throwable $e) {
        if (stripos($e->getMessage(), 'Duplicate column name') === false) {
            throw $e;
        }
    }
    try {
        $pdo->exec('ALTER TABLE hexapod_command MODIFY lock_seen_at TIMESTAMP(6) NULL DEFAULT NULL');
    } catch (Throwable $e) {
        if (defined('DEBUG_ERRORS') && DEBUG_ERRORS === true) {
            throw $e;
        }
    }
    try {
        $pdo->exec('ALTER TABLE hexapod_command MODIFY updated_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)');
    } catch (Throwable $e) {
        if (defined('DEBUG_ERRORS') && DEBUG_ERRORS === true) {
            throw $e;
        }
    }

    $stmt = $pdo->prepare(
        'INSERT INTO hexapod_command (id, mode, vx, vy, turn_rate, speed, height, client_id, lock_owner_id, lock_seen_at)
         VALUES (1, :mode, 0, 0, 0, 0.4, 0, "", "", NULL)
         ON DUPLICATE KEY UPDATE mode = VALUES(mode)'
    );
    $stmt->execute([':mode' => 'init']);
} catch (Throwable $e) {
    $payload = ['ok' => false, 'error' => 'db_query_failed'];
    if (defined('DEBUG_ERRORS') && DEBUG_ERRORS === true) {
        $payload['detail'] = $e->getMessage();
    }
    json_response(500, $payload);
}

json_response(200, ['ok' => true, 'message' => 'db_initialized']);
