<?php
$handler = static function (): void {
    echo "Hello World!";
};

if (isset($_SERVER['FRANKENPHP_WORKER'])) {
    while (frankenphp_handle_request($handler)) { }
} else {
    $handler();
}
