<?php
$handler = static function (): void {
    header('content-type: text/html; charset=utf-8');
    $str = str_repeat('x', 1023) . "\n";
    for ($i = 0; $i < 50; $i++) {
        echo $str;
    }
};

if (isset($_SERVER['FRANKENPHP_WORKER'])) {
    while (frankenphp_handle_request($handler)) { }
} else {
    $handler();
}
