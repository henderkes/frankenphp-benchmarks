#!/usr/bin/env python3

import json
import re
from pathlib import Path


JSON_DIR = Path(__file__).parent / "json"
DEFAULT_OUT_FILE = Path(__file__).parent / "benchmark-wrk.html"


def parse_number(value: str) -> float:
    """Parse a numeric string that may contain units (e.g., '2.05ms', '850us', '1.2s'). Return milliseconds for time.
    For plain numbers like requests_per_sec, just return float(value).
    """
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    # If it's a plain float (RPS etc.)
    try:
        return float(s)
    except ValueError:
        pass

    m = re.fullmatch(r"([0-9]*\.?[0-9]+)\s*(us|µs|ms|s)", s, flags=re.IGNORECASE)
    if not m:
        # Unknown format; attempt to extract numeric prefix
        num = re.match(r"([0-9]*\.?[0-9]+)", s)
        return float(num.group(1)) if num else float("nan")

    val = float(m.group(1))
    unit = m.group(2).lower()
    if unit in ("us", "µs"):
        return val / 1000.0  # microseconds to ms
    if unit == "ms":
        return val
    if unit == "s":
        return val * 1000.0
    return val


def load_results():
    data = {}
    if not JSON_DIR.exists():
        return data
    for p in sorted(JSON_DIR.glob("*.json")):
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        script = Path(obj.get("script", "")).name or p.stem
        docker = obj.get("docker", "")
        metrics = obj.get("metrics", {})
        rps = parse_number(metrics.get("requests_per_sec", "nan"))
        avg_ms = parse_number(metrics.get("latency_avg", "nan"))
        p50_ms = parse_number(metrics.get("p50", "nan"))
        p99_ms = parse_number(metrics.get("p99", "nan"))
        if script not in data:
            data[script] = {}
        data[script][docker] = {
            "rps": rps,
            "avg_ms": avg_ms,
            "p50_ms": p50_ms,
            "p99_ms": p99_ms,
        }
    return data


def detect_threads_connections():
    """Try to detect the WRK threads and connections from any JSON file.
    Returns a tuple (threads, connections) as ints if found, else (None, None).
    """
    if not JSON_DIR.exists():
        return (None, None)
    for p in sorted(JSON_DIR.glob("*.json")):
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        t = obj.get("threads")
        c = obj.get("connections")
        if isinstance(t, (int, float)) and isinstance(c, (int, float)):
            try:
                return (int(t), int(c))
            except Exception:
                pass
    return (None, None)


def delta_percent(current: float, baseline: float) -> float:
    if baseline == 0 or baseline != baseline:  # nan check
        return float("nan")
    return (current - baseline) / baseline * 100.0


def color_for_delta(delta: float, better_when_higher: bool) -> str:
    if delta != delta:  # NaN
        return ""
    if better_when_higher:
        return "#0a0" if delta >= 0 else "#c00"
    else:
        return "#0a0" if delta <= 0 else "#c00"


def best_worst_classes(values, better_when_higher: bool):
    # values: list of (name, value)
    present = [(n, v) for n, v in values if v == v]  # drop NaN
    if not present:
        return {n: "" for n, _ in values}
    if better_when_higher:
        best_val = max(v for _, v in present)
        worst_val = min(v for _, v in present)
    else:
        best_val = min(v for _, v in present)
        worst_val = max(v for _, v in present)
    classes = {}
    for n, v in values:
        cls = []
        if v == v:  # not NaN
            if v == best_val:
                cls.append("best")
            if v == worst_val:
                cls.append("worst")
        classes[n] = " ".join(cls)
    return classes


def fmt_delta(delta: float) -> str:
    if delta != delta:
        return ""
    sign = "+" if delta >= 0 else ""
    return f"{sign}{delta:.1f}%"


def generate_html(data):
    scripts = sorted(data.keys())
    html = []
    html.append("""
<!DOCTYPE html>
<html>
<head>
  <meta charset=\"UTF-8\">
  <title>wrk Benchmarks</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 20px; }
    table { border-collapse: collapse; margin-bottom: 28px; min-width: 760px; }
    th, td { border: 1px solid #ccc; padding: 8px 10px; text-align: right; }
    th { background: #f0f0f0; }
    td.label, th.label { text-align: left; }
    .delta { font-size: 0.9em; display: block; }
    .best { background: #d8f5d0; }        /* light green */
    .worst { background: #ffd8d6; }       /* light red */
  </style>
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  </head>
  <body>
    <h1>wrk Benchmark Comparison</h1>
    <p>Baseline: nginx. Green percentage = improvement vs baseline. Red = regression vs baseline.</p>
""")

    # Build a single comprehensive table
    html.append("<h2>All metrics</h2>")
    html.append("<table>")
    # Header row 1: grouped by metric
    html.append(
        "<tr>"
        "<th class=\"label\" rowspan=\"2\">Script</th>"
        "<th colspan=\"3\">Requests/sec (higher is better)</th>"
        "<th colspan=\"3\">Avg latency ms (lower is better)</th>"
        "<th colspan=\"3\">p50 ms (lower is better)</th>"
        "<th colspan=\"3\">p99 ms (lower is better)</th>"
        "</tr>"
    )
    # Header row 2: engines
    html.append(
        "<tr>"
        "<th>nginx</th><th>frankenphp</th><th>frankenrpm</th>"
        "<th>nginx</th><th>frankenphp</th><th>frankenrpm</th>"
        "<th>nginx</th><th>frankenphp</th><th>frankenrpm</th>"
        "<th>nginx</th><th>frankenphp</th><th>frankenrpm</th>"
        "</tr>"
    )

    def fmt_val(v, unit):
        if v != v:
            return "N/A"
        if unit == "ms":
            return f"{v:.2f} {unit}"
        return f"{v:,.2f}"

    for script in scripts:
        row = data.get(script, {})

        # Extract metrics per engine
        nginx_rps = row.get("nginx", {}).get("rps", float("nan"))
        fphp_rps = row.get("frankenphp", {}).get("rps", float("nan"))
        frpm_rps = row.get("frankenrpm", {}).get("rps", float("nan"))

        nginx_avg = row.get("nginx", {}).get("avg_ms", float("nan"))
        fphp_avg = row.get("frankenphp", {}).get("avg_ms", float("nan"))
        frpm_avg = row.get("frankenrpm", {}).get("avg_ms", float("nan"))

        nginx_p50 = row.get("nginx", {}).get("p50_ms", float("nan"))
        fphp_p50 = row.get("frankenphp", {}).get("p50_ms", float("nan"))
        frpm_p50 = row.get("frankenrpm", {}).get("p50_ms", float("nan"))

        nginx_p99 = row.get("nginx", {}).get("p99_ms", float("nan"))
        fphp_p99 = row.get("frankenphp", {}).get("p99_ms", float("nan"))
        frpm_p99 = row.get("frankenrpm", {}).get("p99_ms", float("nan"))

        # Compute classes per metric
        classes_rps = best_worst_classes([
            ("nginx", nginx_rps), ("frankenphp", fphp_rps), ("frankenrpm", frpm_rps)
        ], better_when_higher=True)
        classes_avg = best_worst_classes([
            ("nginx", nginx_avg), ("frankenphp", fphp_avg), ("frankenrpm", frpm_avg)
        ], better_when_higher=False)
        classes_p50 = best_worst_classes([
            ("nginx", nginx_p50), ("frankenphp", fphp_p50), ("frankenrpm", frpm_p50)
        ], better_when_higher=False)
        classes_p99 = best_worst_classes([
            ("nginx", nginx_p99), ("frankenphp", fphp_p99), ("frankenrpm", frpm_p99)
        ], better_when_higher=False)

        # Deltas vs nginx baseline
        d_rps_fphp = delta_percent(fphp_rps, nginx_rps)
        d_rps_frpm = delta_percent(frpm_rps, nginx_rps)
        d_avg_fphp = delta_percent(fphp_avg, nginx_avg)
        d_avg_frpm = delta_percent(frpm_avg, nginx_avg)
        d_p50_fphp = delta_percent(fphp_p50, nginx_p50)
        d_p50_frpm = delta_percent(frpm_p50, nginx_p50)
        d_p99_fphp = delta_percent(fphp_p99, nginx_p99)
        d_p99_frpm = delta_percent(frpm_p99, nginx_p99)

        # Colors for deltas
        col_rps_fphp = color_for_delta(d_rps_fphp, True)
        col_rps_frpm = color_for_delta(d_rps_frpm, True)
        col_avg_fphp = color_for_delta(d_avg_fphp, False)
        col_avg_frpm = color_for_delta(d_avg_frpm, False)
        col_p50_fphp = color_for_delta(d_p50_fphp, False)
        col_p50_frpm = color_for_delta(d_p50_frpm, False)
        col_p99_fphp = color_for_delta(d_p99_fphp, False)
        col_p99_frpm = color_for_delta(d_p99_frpm, False)

        html.append("<tr>")
        html.append(f"<td class=\"label\">{script}</td>")

        # RPS
        html.append(f"<td class=\"{classes_rps['nginx']}\">{fmt_val(nginx_rps, 'rps')}</td>")
        html.append(
            f"<td class=\"{classes_rps['frankenphp']}\">{fmt_val(fphp_rps, 'rps')}\n"
            f"<span class=\"delta\" style=\"color:{col_rps_fphp}\">{fmt_delta(d_rps_fphp)}</span></td>"
        )
        html.append(
            f"<td class=\"{classes_rps['frankenrpm']}\">{fmt_val(frpm_rps, 'rps')}\n"
            f"<span class=\"delta\" style=\"color:{col_rps_frpm}\">{fmt_delta(d_rps_frpm)}</span></td>"
        )

        # Avg latency
        html.append(f"<td class=\"{classes_avg['nginx']}\">{fmt_val(nginx_avg, 'ms')}</td>")
        html.append(
            f"<td class=\"{classes_avg['frankenphp']}\">{fmt_val(fphp_avg, 'ms')}\n"
            f"<span class=\"delta\" style=\"color:{col_avg_fphp}\">{fmt_delta(d_avg_fphp)}</span></td>"
        )
        html.append(
            f"<td class=\"{classes_avg['frankenrpm']}\">{fmt_val(frpm_avg, 'ms')}\n"
            f"<span class=\"delta\" style=\"color:{col_avg_frpm}\">{fmt_delta(d_avg_frpm)}</span></td>"
        )

        # p50
        html.append(f"<td class=\"{classes_p50['nginx']}\">{fmt_val(nginx_p50, 'ms')}</td>")
        html.append(
            f"<td class=\"{classes_p50['frankenphp']}\">{fmt_val(fphp_p50, 'ms')}\n"
            f"<span class=\"delta\" style=\"color:{col_p50_fphp}\">{fmt_delta(d_p50_fphp)}</span></td>"
        )
        html.append(
            f"<td class=\"{classes_p50['frankenrpm']}\">{fmt_val(frpm_p50, 'ms')}\n"
            f"<span class=\"delta\" style=\"color:{col_p50_frpm}\">{fmt_delta(d_p50_frpm)}</span></td>"
        )

        # p99
        html.append(f"<td class=\"{classes_p99['nginx']}\">{fmt_val(nginx_p99, 'ms')}</td>")
        html.append(
            f"<td class=\"{classes_p99['frankenphp']}\">{fmt_val(fphp_p99, 'ms')}\n"
            f"<span class=\"delta\" style=\"color:{col_p99_fphp}\">{fmt_delta(d_p99_fphp)}</span></td>"
        )
        html.append(
            f"<td class=\"{classes_p99['frankenrpm']}\">{fmt_val(frpm_p99, 'ms')}\n"
            f"<span class=\"delta\" style=\"color:{col_p99_frpm}\">{fmt_delta(d_p99_frpm)}</span></td>"
        )

        html.append("</tr>")

    html.append("</table>")

    html.append("""
  </body>
  </html>
""")
    return "\n".join(html)


def main():
    data = load_results()
    html = generate_html(data)

    threads, connections = detect_threads_connections()
    if threads is not None and connections is not None:
        out_file = Path(__file__).parent / f"benchmark-{threads}-{connections}.html"
    else:
        out_file = DEFAULT_OUT_FILE

    out_file.write_text(html, encoding="utf-8")
    print(f"Wrote {out_file}")


if __name__ == "__main__":
    main()
