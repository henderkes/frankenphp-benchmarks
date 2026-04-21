#!/usr/bin/env python3

import json
import re
from pathlib import Path


JSON_DIR = Path(__file__).parent / "json"
DEFAULT_OUT_FILE = Path(__file__).parent / "benchmark-wrk.html"

# Baseline engine used for Δ% comparisons. First engine listed is used as baseline.
BASELINE = "nginx"

# Preferred column ordering; any engines not in this list are appended alphabetically.
PREFERRED_ORDER = ["nginx", "frankenphp", "frankenrpm", "turbine-nts", "turbine-zts"]


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
    engines = set()
    if not JSON_DIR.exists():
        return data, engines
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
        if docker:
            engines.add(docker)
    return data, engines


def order_engines(engines):
    seen = []
    for e in PREFERRED_ORDER:
        if e in engines:
            seen.append(e)
    for e in sorted(engines):
        if e not in seen:
            seen.append(e)
    return seen


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


def fmt_val(v, unit):
    if v != v:
        return "N/A"
    if unit == "ms":
        return f"{v:.2f} ms"
    return f"{v:,.2f}"


def generate_html(data, engines):
    scripts = sorted(data.keys())
    n = len(engines)

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
""")
    html.append(f"    <p>Baseline: <b>{BASELINE}</b>. Green percentage = improvement vs baseline. Red = regression vs baseline.</p>")

    html.append("<h2>All metrics</h2>")
    html.append("<table>")
    # Header row 1: grouped by metric
    html.append(
        "<tr>"
        f"<th class=\"label\" rowspan=\"2\">Script</th>"
        f"<th colspan=\"{n}\">Requests/sec (higher is better)</th>"
        f"<th colspan=\"{n}\">Avg latency ms (lower is better)</th>"
        f"<th colspan=\"{n}\">p50 ms (lower is better)</th>"
        f"<th colspan=\"{n}\">p99 ms (lower is better)</th>"
        "</tr>"
    )
    # Header row 2: engines x 4 metrics
    engine_headers = "".join(f"<th>{e}</th>" for e in engines)
    html.append("<tr>" + engine_headers * 4 + "</tr>")

    def metric_cells(row, engines, key, better_when_higher):
        vals = [(e, row.get(e, {}).get(key, float("nan"))) for e in engines]
        classes = best_worst_classes(vals, better_when_higher=better_when_higher)
        baseline_val = row.get(BASELINE, {}).get(key, float("nan"))
        unit = "ms" if key != "rps" else "rps"
        cells = []
        for e, v in vals:
            cls = classes[e]
            if e == BASELINE or baseline_val != baseline_val:
                cells.append(f"<td class=\"{cls}\">{fmt_val(v, unit)}</td>")
            else:
                d = delta_percent(v, baseline_val)
                col = color_for_delta(d, better_when_higher)
                cells.append(
                    f"<td class=\"{cls}\">{fmt_val(v, unit)}\n"
                    f"<span class=\"delta\" style=\"color:{col}\">{fmt_delta(d)}</span></td>"
                )
        return "".join(cells)

    for script in scripts:
        row = data.get(script, {})
        html.append("<tr>")
        html.append(f"<td class=\"label\">{script}</td>")
        html.append(metric_cells(row, engines, "rps", better_when_higher=True))
        html.append(metric_cells(row, engines, "avg_ms", better_when_higher=False))
        html.append(metric_cells(row, engines, "p50_ms", better_when_higher=False))
        html.append(metric_cells(row, engines, "p99_ms", better_when_higher=False))
        html.append("</tr>")

    html.append("</table>")

    html.append("""
  </body>
  </html>
""")
    return "\n".join(html)


def main():
    data, engine_set = load_results()
    engines = order_engines(engine_set)
    html = generate_html(data, engines)

    threads, connections = detect_threads_connections()
    if threads is not None and connections is not None:
        out_file = Path(__file__).parent / f"benchmark-{threads}-{connections}.html"
    else:
        out_file = DEFAULT_OUT_FILE

    out_file.write_text(html, encoding="utf-8")
    print(f"Wrote {out_file}")


if __name__ == "__main__":
    main()
