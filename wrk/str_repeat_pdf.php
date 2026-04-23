<?php
$handler = static function (): void {
    header('content-type: application/pdf');
    $str = str_repeat('x', 1023) . "\n";
    echo str_repeat($str, 50);
};

if (isset($_SERVER['FRANKENPHP_WORKER'])) {
    while (frankenphp_handle_request($handler)) { }
} else {
    $handler();
}
