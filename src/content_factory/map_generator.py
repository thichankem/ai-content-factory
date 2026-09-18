"""Procedural SVG generator for historical routes, nautical maps, and infographics.

Zero external dependencies: generates crisp, responsive SVG vector graphics
that can be previewed directly, layered into video scenes, or loaded into Photo Lab.
"""

from __future__ import annotations

import html

from .models import InfographicSpec, MapRouteSpec


def generate_route_map_svg(spec: MapRouteSpec) -> str:
    """Generate an animated dark-glassmorphism SVG map showing a trajectory."""
    width = 960
    height = 540

    points = spec.points
    if not points:
        # Default Southampton to North Atlantic Titanic route
        from .models import MapRoutePoint

        points = [
            MapRoutePoint(label="Southampton (Khởi hành)", x=80.0, y=30.0),
            MapRoutePoint(label="Cherbourg (Đón khách)", x=76.0, y=38.0),
            MapRoutePoint(label="Queenstown (Cảng cuối)", x=70.0, y=34.0),
            MapRoutePoint(label="Vùng Băng Trôi (41°43'N 49°56'W)", x=35.0, y=65.0),
        ]

    # Convert normalized percentage points (0..100) to svg pixel coords
    svg_coords = [(p.x * width / 100.0, p.y * height / 100.0) for p in points]

    # Build smooth path d string
    path_d = ""
    if len(svg_coords) == 1:
        path_d = f"M {svg_coords[0][0]},{svg_coords[0][1]}"
    elif len(svg_coords) > 1:
        path_d = f"M {svg_coords[0][0]},{svg_coords[0][1]}"
        for i in range(1, len(svg_coords)):
            x0, y0 = svg_coords[i - 1]
            x1, y1 = svg_coords[i]
            cx = (x0 + x1) / 2
            cy = (y0 + y1) / 2
            path_d += f" Q {x0},{y0} {cx},{cy} T {x1},{y1}"

    title_safe = html.escape(spec.title or "Historical Route Map")
    danger_safe = html.escape(spec.danger_label or "Vị trí va chạm")

    danger_px_x = spec.danger_x * width / 100.0
    danger_px_y = spec.danger_y * height / 100.0

    # Build waypoint circles and text tags
    waypoints_svg = []
    for p, (px, py) in zip(points, svg_coords, strict=True):
        label = html.escape(p.label)
        waypoints_svg.append(
            f'<g class="waypoint" transform="translate({px:.1f},{py:.1f})">\n'
            f'<circle r="6" fill="#6366f1" stroke="#ffffff" stroke-width="2"/>\n'
            f'<circle r="12" fill="none" stroke="#818cf8" stroke-width="1" '
            f'opacity="0.4"/>\n'
            f'<text x="14" y="4" fill="#f8fafc" font-size="12" '
            f'font-family="sans-serif" font-weight="600" '
            f'filter="drop-shadow(0 2px 4px rgba(0,0,0,0.8))">'
            f"{label}</text>\n"
            f"</g>"
        )

    danger_svg = ""
    if spec.show_danger_zone:
        danger_svg = (
            f'<g transform="translate({danger_px_x:.1f},{danger_px_y:.1f})">'
            f'<circle r="20" fill="#ef4444" opacity="0.25">'
            f'<animate attributeName="r" values="16;28;16" dur="2.4s" '
            f'repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values="0.4;0.1;0.4" dur="2.4s" '
            f'repeatCount="indefinite"/>'
            f"</circle>"
            f'<circle r="8" fill="#ef4444" stroke="#ffffff" stroke-width="2"/>'
            f'<polygon points="0,-16 14,12 -14,12" fill="#ef4444" opacity="0.9"/>'
            f'<text x="0" y="8" fill="#ffffff" font-size="10" font-weight="bold" '
            f'text-anchor="middle">!</text>'
            f'<text x="0" y="32" fill="#fca5a5" font-size="13" font-weight="bold" '
            f'text-anchor="middle" font-family="sans-serif">'
            f"{danger_safe}</text>"
            f"</g>"
        )

    waypoints_str = "\n".join(waypoints_svg)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}"
     width="100%" height="100%" style="background:#070b14; display:block;">
  <defs>
    <linearGradient id="routeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#38bdf8"/>
      <stop offset="50%" stop-color="#818cf8"/>
      <stop offset="100%" stop-color="#f43f5e"/>
    </linearGradient>
    <radialGradient id="oceanGrad" cx="50%" cy="50%" r="60%">
      <stop offset="0%" stop-color="#0f172a"/>
      <stop offset="100%" stop-color="#020617"/>
    </radialGradient>
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="3" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>

  <!-- Ocean Background -->
  <rect width="{width}" height="{height}" fill="url(#oceanGrad)"/>

  <!-- Nautical Coordinate Grid -->
  <g stroke="rgba(255,255,255,0.06)" stroke-width="1">
    <line x1="160" y1="0" x2="160" y2="{height}"/>
    <line x1="320" y1="0" x2="320" y2="{height}"/>
    <line x1="480" y1="0" x2="480" y2="{height}"/>
    <line x1="640" y1="0" x2="640" y2="{height}"/>
    <line x1="800" y1="0" x2="800" y2="{height}"/>
    <line x1="0" y1="135" x2="{width}" y2="135"/>
    <line x1="0" y1="270" x2="{width}" y2="270"/>
    <line x1="0" y1="405" x2="{width}" y2="405"/>
  </g>

  <!-- Title & Compass Annotations -->
  <text x="36" y="44" fill="#ffffff" font-size="20" font-weight="700"
        font-family="sans-serif">{title_safe}</text>
  <text x="36" y="66" fill="#94a3b8" font-size="12" font-family="sans-serif">
    HẢI TRÌNH ĐỊNH MỆNH &amp; TỌA ĐỘ VÙNG THẢM HỌA
  </text>

  <!-- Trajectory Path -->
  <path d="{path_d}" fill="none" stroke="url(#routeGrad)" stroke-width="4"
        stroke-dasharray="8 6" filter="url(#glow)"/>

  <!-- Danger Zone -->
  {danger_svg}

  <!-- Waypoints -->
  {waypoints_str}
</svg>"""


def generate_infographic_svg(spec: InfographicSpec) -> str:
    """Generate a high-contrast comparison infographic SVG (casualties, metrics)."""
    width = 960
    height = 540

    labels = spec.labels or ["Tồn tại", "Mất tích / Thiệt mạng"]
    values = spec.values or [710.0, 1517.0]
    unit = html.escape(spec.unit or "")
    title = html.escape(spec.title or "Số liệu thống kê thảm họa")
    subtitle = html.escape(spec.subtitle or "Nguồn đối soát chính thức")

    max_val = max(values) if values else 1.0
    if max_val == 0:
        max_val = 1.0

    bar_x = 180
    bar_max_w = 600
    bar_h = 36
    spacing = 64
    start_y = 140

    bars_svg = []
    colors = ["#38bdf8", "#ef4444", "#f59e0b", "#10b981", "#a855f7"]

    for i, (label, val) in enumerate(zip(labels, values, strict=False)):
        y = start_y + i * spacing
        w = (val / max_val) * bar_max_w
        color = colors[i % len(colors)]
        label_safe = html.escape(str(label))
        val_str = f"{int(val):,}" if val.is_integer() else f"{val:.1f}"

        bars_svg.append(
            f'<g transform="translate(0, {y})">'
            f'<text x="{bar_x - 16}" y="24" fill="#cbd5e1" font-size="14" '
            f'font-weight="600" text-anchor="end" font-family="sans-serif">'
            f"{label_safe}</text>"
            f'<rect x="{bar_x}" y="0" width="{bar_max_w}" height="{bar_h}" rx="6" '
            f'fill="rgba(255,255,255,0.05)"/>'
            f'<rect x="{bar_x}" y="0" width="{w:.1f}" height="{bar_h}" rx="6" '
            f'fill="{color}">'
            f'<animate attributeName="width" from="0" to="{w:.1f}" dur="1.2s" '
            f'calcMode="spline" keySplines="0.4 0 0.2 1"/>'
            f"</rect>"
            f'<text x="{bar_x + w + 16}" y="24" fill="#ffffff" font-size="16" '
            f'font-weight="bold" font-family="sans-serif">'
            f"{val_str} {unit}</text>"
            f"</g>"
        )

    bars_str = "\n".join(bars_svg)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}"
     width="100%" height="100%" style="background:#0b0f19; display:block;">
  <!-- Background Glow -->
  <rect width="{width}" height="{height}" fill="#090d16"/>

  <!-- Card Frame -->
  <rect x="24" y="24" width="{width - 48}" height="{height - 48}" rx="16"
        fill="rgba(255,255,255,0.02)" stroke="rgba(255,255,255,0.08)" stroke-width="1"/>

  <!-- Header -->
  <text x="48" y="68" fill="#ffffff" font-size="22" font-weight="bold"
        font-family="sans-serif">{title}</text>
  <text x="48" y="92" fill="#94a3b8" font-size="13" font-family="sans-serif">
    {subtitle}
  </text>

  <!-- Bars Group -->
  {bars_str}
</svg>"""
