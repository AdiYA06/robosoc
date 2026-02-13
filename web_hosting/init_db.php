<?php

declare(strict_types=1);

require_once __DIR__ . '/bootstrap.php';
require_api_token();

$pdo = db();
$pdo->exec(
    'CREATE TABLE IF NOT EXISTS hexapod_command (
        id TINYINT UNSIGNED NOT NULL PRIMARY KEY,
        mode VARCHAR(16) NOT NULL DEFAULT "stop",
        vx FLOAT NOT NULL DEFAULT 0,
        vy FLOAT NOT NULL DEFAULT 0,
        turn_rate FLOAT NOT NULL DEFAULT 0,
        speed FLOAT NOT NULL DEFAULT 0.4,
        height FLOAT NOT NULL DEFAULT 0,
        client_id VARCHAR(128) NOT NULL DEFAULT "",
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4'
);

$stmt = $pdo->prepare(
    'INSERT INTO hexapod_command (id, mode, vx, vy, turn_rate, speed, height, client_id)
     VALUES (1, :mode, 0, 0, 0, 0.4, 0, "")
     ON DUPLICATE KEY UPDATE mode = :mode'
);
$stmt->execute([':mode' => 'stop']);

json_response(200, ['ok' => true, 'message' => 'db_initialized']);
