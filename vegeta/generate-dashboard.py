#!/usr/bin/env python3

import json
import subprocess
import sys
from pathlib import Path

def get_metrics(vegeta_bin):
    """Extract metrics from vegeta binary file"""
    # Get JSON report
    result = subprocess.run(
        ['vegeta', 'report', '-type=json', vegeta_bin],
        capture_output=True,
        text=True
    )
    report = json.loads(result.stdout)

    # Extract metrics
    metrics = {
        'latency_mean': round(report['latencies']['mean'] / 1_000_000, 2),
        'latency_50': round(report['latencies']['50th'] / 1_000_000, 2),
        'latency_99': round(report['latencies']['99th'] / 1_000_000, 2),
        'latency_max': round(report['latencies']['max'] / 1_000_000, 2),
        'rps': round(report['rate'], 2),
        'success': round(report['success'] * 100),
        'total_requests': report['requests']
    }

    # Sample data (max 200 points per test for reasonable file size)
    sample_rate = max(1, metrics['total_requests'] // 200)

    print(f"  Total requests: {metrics['total_requests']}, sampling every {sample_rate} requests")

    # Get sampled data
    result = subprocess.run(
        f"vegeta encode --to json < {vegeta_bin} | awk 'NR % {sample_rate} == 1'",
        shell=True,
        capture_output=True,
        text=True
    )

    results = []
    for line in result.stdout.strip().split('\n'):
        if line:
            results.append(json.loads(line))

    print(f"  Sampled {len(results)} data points")
    metrics['results'] = results
    metrics['sample_rate'] = sample_rate
    return metrics

def main():
    if len(sys.argv) < 3:
        print("Usage: generate-dashboard.py <bench_name> <vegeta_bin1> [vegeta_bin2] ...")
        sys.exit(1)

    bench_name = sys.argv[1]
    vegeta_bins = sys.argv[2:]

    # Collect all metrics
    all_data = {}
    for bin_path in vegeta_bins:
        filename = Path(bin_path).stem
        print(f"Processing {filename}...")
        all_data[filename] = get_metrics(bin_path)

    # Generate colors for each test
    colors = [
        '#3498db', '#e74c3c', '#2ecc71', '#f39c12',
        '#9b59b6', '#1abc9c', '#34495e', '#e67e22'
    ]

    # Build datasets for charts
    filenames = list(all_data.keys())

    # Generate HTML
    html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Benchmark Results - {bench_name}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1600px; margin: 0 auto; }}
        .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 20px; }}
        .test-card {{ background: white; padding: 20px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .test-card h3 {{ margin-top: 0; color: #2c3e50; }}
        .metric-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #ecf0f1; }}
        .metric-label {{ color: #666; }}
        .metric-value {{ font-weight: bold; color: #2c3e50; }}
        .charts {{ display: grid; grid-template-columns: 1fr; gap: 20px; }}
        .chart-container {{ background: white; padding: 20px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        canvas {{ max-height: 400px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Benchmark Comparison - {bench_name}</h1>
        </div>

        <div class="metrics-grid">
'''

    # Add metric cards for each test
    for idx, (filename, data) in enumerate(all_data.items()):
        html += f'''
            <div class="test-card">
                <h3>{filename}.php</h3>
                <div class="metric-row">
                    <span class="metric-label">Requests/sec</span>
                    <span class="metric-value">{data['rps']}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Mean Latency</span>
                    <span class="metric-value">{data['latency_mean']} ms</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">50th Percentile</span>
                    <span class="metric-value">{data['latency_50']} ms</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">99th Percentile</span>
                    <span class="metric-value">{data['latency_99']} ms</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Max Latency</span>
                    <span class="metric-value">{data['latency_max']} ms</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Success Rate</span>
                    <span class="metric-value">{data['success']}%</span>
                </div>
            </div>
'''

    html += '''
        </div>

        <div class="charts">
            <div class="chart-container">
                <h3>Requests Per Second Comparison</h3>
                <canvas id="rpsComparisonChart"></canvas>
            </div>
            <div class="chart-container">
                <h3>Latency Comparison</h3>
                <canvas id="latencyComparisonChart"></canvas>
            </div>
            <div class="chart-container">
                <h3>Latency Over Time (sampled)</h3>
                <canvas id="latencyTimeChart"></canvas>
            </div>
            <div class="chart-container">
                <h3>Throughput Over Time (100ms windows)</h3>
                <canvas id="rpsTimeChart"></canvas>
            </div>
        </div>
    </div>

    <script>
        const data = ''' + json.dumps(all_data) + ''';
        const colors = ''' + json.dumps(colors[:len(filenames)]) + ''';
        const filenames = ''' + json.dumps(filenames) + ''';

        // RPS Comparison
        new Chart(document.getElementById('rpsComparisonChart'), {
            type: 'bar',
            data: {
                labels: filenames,
                datasets: [{
                    label: 'Requests/sec',
                    data: filenames.map(f => data[f].rps),
                    backgroundColor: colors
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    y: { beginAtZero: true, title: { display: true, text: 'Requests/sec' } }
                }
            }
        });

        // Latency Comparison
        new Chart(document.getElementById('latencyComparisonChart'), {
            type: 'bar',
            data: {
                labels: filenames,
                datasets: [
                    {
                        label: 'Mean',
                        data: filenames.map(f => data[f].latency_mean),
                        backgroundColor: 'rgba(52, 152, 219, 0.8)'
                    },
                    {
                        label: '50th %',
                        data: filenames.map(f => data[f].latency_50),
                        backgroundColor: 'rgba(46, 204, 113, 0.8)'
                    },
                    {
                        label: '99th %',
                        data: filenames.map(f => data[f].latency_99),
                        backgroundColor: 'rgba(243, 156, 18, 0.8)'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    y: { beginAtZero: true, title: { display: true, text: 'Latency (ms)' } }
                }
            }
        });

        // Latency Over Time
        const latencyDatasets = filenames.map((filename, idx) => {
            const results = data[filename].results;
            return {
                label: filename,
                data: results.map((r, i) => ({ x: i, y: r.latency / 1000000 })),
                borderColor: colors[idx],
                backgroundColor: colors[idx] + '20',
                borderWidth: 2,
                pointRadius: 0,
                tension: 0.1
            };
        });

        new Chart(document.getElementById('latencyTimeChart'), {
            type: 'line',
            data: { datasets: latencyDatasets },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    y: { beginAtZero: true, title: { display: true, text: 'Latency (ms)' } },
                    x: {
                        type: 'linear',
                        title: { display: true, text: 'Sample Number' }
                    }
                }
            }
        });

        // RPS Over Time (using 100ms buckets)
        const allRpsDatasets = [];

        filenames.forEach((filename, idx) => {
            const results = data[filename].results;
            const startTime = new Date(results[0].timestamp).getTime();
            const bucketSize = 100;
            const rpsBuckets = {};

            results.forEach(r => {
                const elapsed = new Date(r.timestamp).getTime() - startTime;
                const bucket = Math.floor(elapsed / bucketSize);
                rpsBuckets[bucket] = (rpsBuckets[bucket] || 0) + 1;
            });

            // Extrapolate to RPS based on sample rate
            const sampleRate = data[filename].sample_rate;

            const rpsData = Object.keys(rpsBuckets).sort((a, b) => a - b).map(bucket => ({
                x: bucket * bucketSize / 1000,
                y: (rpsBuckets[bucket] * sampleRate / bucketSize) * 1000
            }));

            // Instantaneous data
            allRpsDatasets.push({
                label: filename,
                data: rpsData,
                borderColor: colors[idx],
                backgroundColor: colors[idx] + '20',
                borderWidth: 2,
                pointRadius: 0,
                tension: 0.4
            });

            // Average line
            const avgRps = data[filename].rps;
            const maxTime = Math.max(...rpsData.map(d => d.x), 15);
            allRpsDatasets.push({
                label: filename + ' (avg)',
                data: [
                    { x: 0, y: avgRps },
                    { x: maxTime, y: avgRps }
                ],
                borderColor: colors[idx],
                borderWidth: 2,
                borderDash: [5, 5],
                pointRadius: 0,
                fill: false
            });
        });

        new Chart(document.getElementById('rpsTimeChart'), {
            type: 'line',
            data: { datasets: allRpsDatasets },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    y: { beginAtZero: true, title: { display: true, text: 'Requests/sec' } },
                    x: {
                        type: 'linear',
                        title: { display: true, text: 'Time (seconds)' }
                    }
                }
            }
        });
    </script>
</body>
</html>'''

    output_file = f"benchmark-{bench_name}.html"
    with open(output_file, 'w') as f:
        f.write(html)

    Path(output_file).chmod(0o666)
    print(f"Generated {output_file}")

if __name__ == '__main__':
    main()