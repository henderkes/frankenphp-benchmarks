#!/usr/bin/env python3

import json
import subprocess
import sys
from pathlib import Path
from collections import defaultdict

def get_metrics(vegeta_bin):
    """Extract metrics from vegeta binary file"""
    result = subprocess.run(
        ['vegeta', 'report', '-type=json', vegeta_bin],
        capture_output=True,
        text=True
    )
    report = json.loads(result.stdout)

    return {
        'latency_mean': round(report['latencies']['mean'] / 1_000_000, 2),
        'latency_50': round(report['latencies']['50th'] / 1_000_000, 2),
        'latency_99': round(report['latencies']['99th'] / 1_000_000, 2),
        'latency_max': round(report['latencies']['max'] / 1_000_000, 2),
        'rps': round(report['rate'], 2),
        'success': round(report['success'] * 100),
        'total_requests': report['requests']
    }

def main():
    vegeta_dir = Path('vegeta')
    if not vegeta_dir.exists():
        print("Error: vegeta directory not found")
        sys.exit(1)

    # Organize data by test and server
    data = defaultdict(dict)

    for bin_file in vegeta_dir.glob('*.bin'):
        # Parse filename: code1-nginx.bin -> test=code1, server=nginx
        parts = bin_file.stem.split('-')
        if len(parts) >= 2:
            test = parts[0]
            server = '-'.join(parts[1:])

            print(f"Processing {test} - {server}...")
            data[test][server] = get_metrics(str(bin_file))

    if not data:
        print("Error: No benchmark data found")
        sys.exit(1)

    # Get list of all servers (sorted for consistent order)
    all_servers = sorted(set(server for test_data in data.values() for server in test_data.keys()))

    # Generate HTML
    html = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Benchmark Comparison - All Servers</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1600px; margin: 0 auto; }
        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
        table { width: 100%; background: white; border-collapse: collapse; margin-bottom: 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ecf0f1; }
        th { background: #2c3e50; color: white; font-weight: 600; position: sticky; top: 0; }
        tr:hover { background: #f8f9fa; }
        .test-header { background: #34495e; color: white; font-weight: bold; font-size: 1.1em; }
        .metric-label { font-weight: 600; color: #555; background: #ecf0f1; }
        .baseline { background: #e8f4f8; font-weight: 600; }
        .positive { color: #27ae60; font-weight: 600; }
        .negative { color: #e74c3c; font-weight: 600; }
        .value { font-family: 'Courier New', monospace; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Benchmark Comparison - All Servers</h1>
            <p>First server listed for each test is used as baseline (100%). Percentages show relative performance.</p>
        </div>

        <table>
            <thead>
                <tr>
                    <th>Test / Metric</th>
'''

    for server in all_servers:
        html += f'                    <th>{server}</th>\n'

    html += '''                </tr>
            </thead>
            <tbody>
'''

    # Generate rows for each test
    for test in sorted(data.keys()):
        test_data = data[test]

        # Determine baseline (first server that has data for this test)
        baseline_server = None
        for server in all_servers:
            if server in test_data:
                baseline_server = server
                break

        if not baseline_server:
            continue

        baseline = test_data[baseline_server]

        # Test header row
        html += f'''                <tr class="test-header">
                    <td colspan="{len(all_servers) + 1}">{test}.php</td>
                </tr>
'''

        # RPS row
        html += '                <tr>\n                    <td class="metric-label">Requests/sec</td>\n'
        for server in all_servers:
            if server in test_data:
                rps = test_data[server]['rps']
                if server == baseline_server:
                    html += f'                    <td class="baseline value">{rps:,.2f}</td>\n'
                else:
                    pct = ((rps - baseline['rps']) / baseline['rps']) * 100
                    pct_class = 'positive' if pct > 0 else 'negative'
                    html += f'                    <td class="value">{rps:,.2f} <span class="{pct_class}">({pct:+.1f}%)</span></td>\n'
            else:
                html += '                    <td>-</td>\n'
        html += '                </tr>\n'

        # Mean Latency row
        html += '                <tr>\n                    <td class="metric-label">Mean Latency</td>\n'
        for server in all_servers:
            if server in test_data:
                lat = test_data[server]['latency_mean']
                if server == baseline_server:
                    html += f'                    <td class="baseline value">{lat:.2f} ms</td>\n'
                else:
                    pct = ((lat - baseline['latency_mean']) / baseline['latency_mean']) * 100
                    pct_class = 'negative' if pct > 0 else 'positive'  # Lower is better
                    html += f'                    <td class="value">{lat:.2f} ms <span class="{pct_class}">({pct:+.1f}%)</span></td>\n'
            else:
                html += '                    <td>-</td>\n'
        html += '                </tr>\n'

        # 50th Percentile row
        html += '                <tr>\n                    <td class="metric-label">50th Percentile</td>\n'
        for server in all_servers:
            if server in test_data:
                lat = test_data[server]['latency_50']
                if server == baseline_server:
                    html += f'                    <td class="baseline value">{lat:.2f} ms</td>\n'
                else:
                    pct = ((lat - baseline['latency_50']) / baseline['latency_50']) * 100
                    pct_class = 'negative' if pct > 0 else 'positive'
                    html += f'                    <td class="value">{lat:.2f} ms <span class="{pct_class}">({pct:+.1f}%)</span></td>\n'
            else:
                html += '                    <td>-</td>\n'
        html += '                </tr>\n'

        # 99th Percentile row
        html += '                <tr>\n                    <td class="metric-label">99th Percentile</td>\n'
        for server in all_servers:
            if server in test_data:
                lat = test_data[server]['latency_99']
                if server == baseline_server:
                    html += f'                    <td class="baseline value">{lat:.2f} ms</td>\n'
                else:
                    pct = ((lat - baseline['latency_99']) / baseline['latency_99']) * 100
                    pct_class = 'negative' if pct > 0 else 'positive'
                    html += f'                    <td class="value">{lat:.2f} ms <span class="{pct_class}">({pct:+.1f}%)</span></td>\n'
            else:
                html += '                    <td>-</td>\n'
        html += '                </tr>\n'

        # Success Rate row
        html += '                <tr>\n                    <td class="metric-label">Success Rate</td>\n'
        for server in all_servers:
            if server in test_data:
                success = test_data[server]['success']
                if server == baseline_server:
                    html += f'                    <td class="baseline value">{success}%</td>\n'
                else:
                    diff = success - baseline['success']
                    if diff == 0:
                        html += f'                    <td class="value">{success}%</td>\n'
                    else:
                        pct_class = 'positive' if diff > 0 else 'negative'
                        html += f'                    <td class="value">{success}% <span class="{pct_class}">({diff:+.0f}pp)</span></td>\n'
            else:
                html += '                    <td>-</td>\n'
        html += '                </tr>\n'

    html += '''            </tbody>
        </table>
    </div>
</body>
</html>'''

    output_file = 'comparison-table.html'
    with open(output_file, 'w') as f:
        f.write(html)

    Path(output_file).chmod(0o666)
    print(f"\nGenerated {output_file}")

if __name__ == '__main__':
    main()