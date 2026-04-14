"""HTML report builder for Project GROOT rollout evaluation."""

from __future__ import annotations

_HTML_CSS = """
    body { font-family: Arial, sans-serif; margin: 40px; }
    h1 { color: #333; }
    h2 { color: #666; margin-top: 30px; }
    table { border-collapse: collapse; margin: 20px 0; }
    th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
    th { background-color: #4CAF50; color: white; }
    .metric { font-size: 24px; font-weight: bold; color: #4CAF50; }
    .plot { margin: 20px 0; }
    .plot img { max-width: 100%; height: auto; border: 1px solid #ddd; }
"""


def _speed_table_rows(cs: dict) -> str:
    """Build HTML rows for the clubhead speed table."""
    speed_range = f"{cs['max_min']:.2f} - {cs['max_max']:.2f} m/s"
    return (
        f"        <tr><td>Mean Max Speed</td>"
        f'<td class="metric">{cs["max_mean"]:.2f} m/s</td></tr>\n'
        f"        <tr><td>Std Dev</td><td>{cs['max_std']:.2f} m/s</td></tr>\n"
        f"        <tr><td>Range</td><td>{speed_range}</td></tr>"
    )


def build_report_html(policy_name: str, summary: dict) -> str:
    """Build HTML evaluation report string from summary metrics.

    Args:
        policy_name: Name of the evaluated policy checkpoint.
        summary: Summary dict produced by compute_summary_metrics().

    Returns:
        Complete HTML report as a string.
    """
    cs = summary["clubhead_speed"]
    sd = summary["swing_duration"]
    ts = summary["trajectory_smoothness"]
    jv = summary["joint_limit_violations"]

    speed_rows = _speed_table_rows(cs)
    duration_cell = f"{sd['mean']:.3f} &plusmn; {sd['std']:.3f} s"
    smoothness_cell = f"{ts['mean']:.3f} &plusmn; {ts['std']:.3f}"

    return (
        "<!DOCTYPE html>\n<html>\n<head>\n"
        "    <title>Project GROOT Evaluation Report</title>\n"
        f"    <style>{_HTML_CSS}    </style>\n"
        "</head>\n<body>\n"
        "    <h1>Project GROOT Evaluation Report</h1>\n"
        f"    <p><strong>Policy:</strong> {policy_name}</p>\n"
        f"    <p><strong>Number of Rollouts:</strong> {summary['num_rollouts']}</p>\n"
        "    <h2>Summary Metrics</h2>\n"
        "    <h3>Clubhead Speed</h3>\n"
        "    <table>\n"
        "        <tr><th>Metric</th><th>Value</th></tr>\n"
        f"{speed_rows}\n"
        "    </table>\n"
        "    <h3>Swing Timing</h3>\n"
        "    <table>\n"
        "        <tr><th>Metric</th><th>Value</th></tr>\n"
        f"        <tr><td>Mean Duration</td><td>{duration_cell}</td></tr>\n"
        "    </table>\n"
        "    <h3>Quality Metrics</h3>\n"
        "    <table>\n"
        "        <tr><th>Metric</th><th>Value</th></tr>\n"
        f"        <tr><td>Trajectory Smoothness</td><td>{smoothness_cell}</td></tr>\n"
        "        <tr><td>Joint Limit Violations</td>"
        f"<td>{jv['percentage']:.1f}% of rollouts</td></tr>\n"
        "    </table>\n"
        "    <h2>Visualizations</h2>\n"
        '    <div class="plot"><h3>Clubhead Speed Distribution</h3>\n'
        '        <img src="plots/clubhead_speed_dist.png" alt="Clubhead Speed">'
        "</div>\n"
        '    <div class="plot"><h3>Swing Duration Distribution</h3>\n'
        '        <img src="plots/swing_duration_dist.png" alt="Swing Duration">'
        "</div>\n"
        '    <div class="plot"><h3>Trajectory Smoothness</h3>\n'
        '        <img src="plots/smoothness.png" alt="Smoothness"></div>\n'
        '    <div class="plot"><h3>Speed vs Duration</h3>\n'
        '        <img src="plots/speed_vs_duration.png" alt="Speed vs Duration">'
        "</div>\n"
        "</body>\n</html>\n"
    )
