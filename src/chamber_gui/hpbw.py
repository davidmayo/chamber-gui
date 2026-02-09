"""Half Power Beam Width (HPBW) computation and overlay generation."""

from __future__ import annotations

import math
from dataclasses import dataclass
from collections.abc import Sequence

import plotly.graph_objects as go


@dataclass(frozen=True)
class HpbwResult:
    """Result of a half-power beam width computation."""

    max_r: float
    max_theta: float
    half_power: float
    left_theta: float
    right_theta: float
    beam_width: float
    label: str


def compute_hpbw(
    thetas: Sequence[float],
    rs: Sequence[float],
) -> HpbwResult | None:
    """Computes Half Power Beam Width from theta/r arrays.

    Args:
        thetas: Angle values in degrees.
        rs: Power values (e.g. dBm).

    Returns:
        An HpbwResult, or None if fewer than 3 valid data points.
    """
    pairs = [
        (t, r)
        for t, r in zip(thetas, rs)
        if not (math.isnan(t) or math.isnan(r))
    ]
    if len(pairs) < 3:
        return None

    pairs.sort(key=lambda p: p[0])
    sorted_thetas = [p[0] for p in pairs]
    sorted_rs = [p[1] for p in pairs]

    max_r = max(sorted_rs)
    max_indices = [i for i, r in enumerate(sorted_rs) if r == max_r]
    peak_idx = max_indices[len(max_indices) // 2]
    max_theta = sorted_thetas[peak_idx]

    half_power = max_r - 3.01

    # Walk left from peak to find the -3dB boundary.
    left_theta = sorted_thetas[0]
    for i in range(peak_idx - 1, -1, -1):
        if sorted_rs[i] < half_power:
            left_theta = sorted_thetas[i + 1]
            break

    # Walk right from peak to find the -3dB boundary.
    right_theta = sorted_thetas[-1]
    for i in range(peak_idx + 1, len(sorted_rs)):
        if sorted_rs[i] < half_power:
            right_theta = sorted_thetas[i - 1]
            break

    beam_width = right_theta - left_theta
    label = f"HPBW: {beam_width:.1f}\u00b0 ({left_theta:.1f}\u00b0 to {right_theta:.1f}\u00b0)"

    return HpbwResult(
        max_r=max_r,
        max_theta=max_theta,
        half_power=half_power,
        left_theta=left_theta,
        right_theta=right_theta,
        beam_width=beam_width,
        label=label,
    )


_CIRCLE_THETAS = list(range(0, 361))


def build_hpbw_traces(
    result: HpbwResult,
    r_min: float,
) -> list[go.Scatterpolar]:
    """Builds Plotly overlay traces for an HPBW result.

    Args:
        result: The computed HPBW result.
        r_min: Minimum r value for radial line extent.

    Returns:
        Five Scatterpolar traces: two circles and three radial lines.
    """
    return [
        # Max power circle (thick, solid, black) — carries the legend label.
        go.Scatterpolar(
            theta=_CIRCLE_THETAS,
            r=[result.max_r] * len(_CIRCLE_THETAS),
            mode="lines",
            line={"color": "black", "width": 3},
            name=result.label,
            showlegend=True,
        ),
        # Half power circle (thin, dashed, black).
        go.Scatterpolar(
            theta=_CIRCLE_THETAS,
            r=[result.half_power] * len(_CIRCLE_THETAS),
            mode="lines",
            line={"color": "black", "width": 1, "dash": "dash"},
            name="half-power",
            showlegend=False,
        ),
        # Left endpoint radial line (thick, solid, black).
        go.Scatterpolar(
            theta=[result.left_theta, result.left_theta],
            r=[r_min, result.max_r],
            mode="lines",
            line={"color": "black", "width": 3},
            name="left",
            showlegend=False,
        ),
        # Right endpoint radial line (thick, solid, black).
        go.Scatterpolar(
            theta=[result.right_theta, result.right_theta],
            r=[r_min, result.max_r],
            mode="lines",
            line={"color": "black", "width": 3},
            name="right",
            showlegend=False,
        ),
        # Max theta radial line (thin, dashed, black).
        go.Scatterpolar(
            theta=[result.max_theta, result.max_theta],
            r=[r_min, result.max_r],
            mode="lines",
            line={"color": "black", "width": 1, "dash": "dash"},
            name="max-theta",
            showlegend=False,
        ),
    ]
