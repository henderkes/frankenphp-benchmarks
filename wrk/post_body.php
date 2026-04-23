<?php
// Exercises go_read_post: PHP reads the request body.
$handler = static function (): void {
    header('Content-Type: text/plain');
    $body = file_get_contents('php://input');
    echo "len=" . strlen($body);
};

if (isset($_SERVER['FRANKENPHP_WORKER'])) {
    while (frankenphp_handle_request($handler)) { }
} else {
    $handler();
}
