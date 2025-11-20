### Test Scripts

- **code1.php**: Simple HTML output (50 iterations of 1KB string)
- **code2.php**: PDF content-type output (50 iterations of 1KB string)
- **code3.php**: Random string generation using Xoshiro256StarStar
- **code4.php**: Hello World

## Hardware Configurations

<summary><b>AMD Ryzen 7 3700X - 8 cores, 32 GB RAM</b></summary>

### Results

8 threads, 20 connections, 15 seconds:

| Test | Metric | Nginx+PHP-FPM<br>(Baseline) | FrankenPHP Docker<br>(Δ%) | FrankenPHP RPM<br>(Δ%) |
|------|--------|---------------------------|--------------------------|----------------------|
| **code1.php** | Avg Latency | 0.93ms | 788.15µs **(-15.3%)** | 792.65µs **(-14.8%)** |
| | 50% | 835.00µs | 690.00µs | 697.00µs |
| | 99% | 2.48ms | 2.36ms | 2.38ms |
| | RPS | 21,366 | 25,419 **(+19.0%)** | 25,309 **(+18.5%)** |
| **code2.php** | Avg Latency | 0.95ms | 827.58µs **(-12.9%)** | 786.00µs **(-17.3%)** |
| | 50% | 0.86ms | 727.00µs | 690.00µs |
| | 99% | 2.50ms | 2.47ms | 2.36ms |
| | RPS | 20,787 | 24,219 **(+16.5%)** | 25,531 **(+22.8%)** |
| **code3.php** | Avg Latency | 1.09ms | 1.11ms **(-1.8%)** | 0.99ms **(+9.2%)** |
| | 50% | 1.00ms | 0.99ms | 0.88ms |
| | 99% | 2.69ms | 3.10ms | 2.74ms |
| | RPS | 18,012 | 17,986 **(-0.1%)** | 20,146 **(+11.8%)** |
| **code4.php** | Avg Latency | 625.62µs | 448.52µs **(-28.3%)** | 451.87µs **(-27.8%)** |
| | 50% | 569.00µs | 367.00µs | 371.00µs |
| | 99% | 1.81ms | 1.69ms | 1.68ms |
| | RPS | 32,371 | 46,988 **(+45.2%)** | 46,575 **(+43.9%)** |

## Running the Benchmarks

```bash
./run.sh 8 100 60
# runs wrk with 8 threads, 100 connections and for 60 seconds per script
```

