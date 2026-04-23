<?php
$handler = static function (): void {
    $random = new \Random\Randomizer(new \Random\Engine\Xoshiro256StarStar());
    for ($i = 0; $i < 50; $i++) {
        echo $random->getBytesFromString("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/", 1023), "\n";
    }
};

if (isset($_SERVER['FRANKENPHP_WORKER'])) {
    while (frankenphp_handle_request($handler)) { }
} else {
    $handler();
}
