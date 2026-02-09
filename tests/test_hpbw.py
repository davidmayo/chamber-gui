"""Tests for HPBW computation and overlay trace generation."""

from __future__ import annotations

import math

import plotly.graph_objects as go

from chamber_gui.hpbw import HpbwResult, build_hpbw_traces, compute_hpbw


def test_compute_hpbw_normal_case() -> None:
    """Peak in the middle with clear -3dB crossings on both sides."""
    thetas = [-30.0, -20.0, -10.0, 0.0, 10.0, 20.0, 30.0]
    rs = [-25.0, -22.0, -19.0, -18.0, -19.0, -22.0, -25.0]
    result = compute_hpbw(thetas, rs)
    assert result is not None
    assert result.max_r == -18.0
    assert result.max_theta == 0.0
    assert result.half_power == -18.0 - 3.01
    # -10 and 10 are both above half_power (-21.01), -20 and 20 are below
    assert result.left_theta == -10.0
    assert result.right_theta == 10.0
    assert result.beam_width == 20.0
    assert "HPBW: 20.0" in result.label
    assert "-10.0" in result.label
    assert "10.0" in result.label


def test_compute_hpbw_tied_max_uses_median_theta() -> None:
    """Two adjacent points at the same max power; median theta is chosen."""
    thetas = [-10.0, 0.0, 10.0, 20.0, 30.0]
    rs = [-25.0, -18.0, -18.0, -18.0, -25.0]
    result = compute_hpbw(thetas, rs)
    assert result is not None
    assert result.max_r == -18.0
    # Three tied values at indices 1,2,3 → median index is 2 → theta=10.0
    assert result.max_theta == 10.0


def test_compute_hpbw_all_above_half_power() -> None:
    """All points within 3dB of max; endpoints are at data edges."""
    thetas = [-20.0, -10.0, 0.0, 10.0, 20.0]
    rs = [-18.0, -17.5, -17.0, -17.5, -18.0]
    result = compute_hpbw(thetas, rs)
    assert result is not None
    # No point drops below half_power (-20.01), so endpoints are at edges.
    assert result.left_theta == -20.0
    assert result.right_theta == 20.0
    assert result.beam_width == 40.0


def test_compute_hpbw_insufficient_data_returns_none() -> None:
    """Fewer than 3 data points returns None."""
    assert compute_hpbw([], []) is None
    assert compute_hpbw([0.0], [-18.0]) is None
    assert compute_hpbw([0.0, 10.0], [-18.0, -20.0]) is None


def test_compute_hpbw_nan_values_are_dropped() -> None:
    """NaN values are excluded before computation."""
    thetas = [float("nan"), -10.0, 0.0, 10.0, float("nan")]
    rs = [-20.0, -22.0, -18.0, -22.0, -20.0]
    result = compute_hpbw(thetas, rs)
    assert result is not None
    assert result.max_theta == 0.0


def test_compute_hpbw_peak_at_left_edge() -> None:
    """Peak at the leftmost point; left endpoint defaults to edge."""
    thetas = [0.0, 10.0, 20.0, 30.0]
    rs = [-10.0, -14.0, -18.0, -22.0]
    result = compute_hpbw(thetas, rs)
    assert result is not None
    assert result.max_theta == 0.0
    assert result.left_theta == 0.0
    # -14 is above half_power (-13.01), -18 is below
    assert result.right_theta == 10.0


def test_compute_hpbw_peak_at_right_edge() -> None:
    """Peak at the rightmost point; right endpoint defaults to edge."""
    thetas = [0.0, 10.0, 20.0, 30.0]
    rs = [-22.0, -18.0, -14.0, -10.0]
    result = compute_hpbw(thetas, rs)
    assert result is not None
    assert result.max_theta == 30.0
    assert result.right_theta == 30.0
    # -14 is above half_power (-13.01), -18 is below
    assert result.left_theta == 20.0


def test_compute_hpbw_unsorted_input() -> None:
    """Input theta values need not be sorted."""
    thetas = [10.0, -10.0, 0.0, 30.0, -30.0, 20.0, -20.0]
    rs = [-19.0, -19.0, -18.0, -25.0, -25.0, -22.0, -22.0]
    result = compute_hpbw(thetas, rs)
    assert result is not None
    assert result.max_theta == 0.0
    assert result.left_theta == -10.0
    assert result.right_theta == 10.0


def test_build_hpbw_traces_returns_five_scatterpolar_traces() -> None:
    """build_hpbw_traces returns exactly 5 traces."""
    result = HpbwResult(
        max_r=-18.0,
        max_theta=0.0,
        half_power=-21.01,
        left_theta=-10.0,
        right_theta=10.0,
        beam_width=20.0,
        label="HPBW: 20.0\u00b0 (-10.0\u00b0 to 10.0\u00b0)",
    )
    traces = build_hpbw_traces(result, r_min=-25.0)
    assert len(traces) == 5
    for trace in traces:
        assert isinstance(trace, go.Scatterpolar)


def test_build_hpbw_traces_circle_traces_have_361_points() -> None:
    result = HpbwResult(
        max_r=-18.0,
        max_theta=0.0,
        half_power=-21.01,
        left_theta=-10.0,
        right_theta=10.0,
        beam_width=20.0,
        label="test",
    )
    traces = build_hpbw_traces(result, r_min=-25.0)
    # First two traces are circles.
    assert len(traces[0].r) == 361
    assert len(traces[1].r) == 361


def test_build_hpbw_traces_radial_lines_have_two_points() -> None:
    result = HpbwResult(
        max_r=-18.0,
        max_theta=0.0,
        half_power=-21.01,
        left_theta=-10.0,
        right_theta=10.0,
        beam_width=20.0,
        label="test",
    )
    traces = build_hpbw_traces(result, r_min=-25.0)
    # Traces 2-4 are radial lines.
    for trace in traces[2:]:
        assert len(trace.r) == 2


def test_build_hpbw_traces_line_styles() -> None:
    result = HpbwResult(
        max_r=-18.0,
        max_theta=0.0,
        half_power=-21.01,
        left_theta=-10.0,
        right_theta=10.0,
        beam_width=20.0,
        label="test",
    )
    traces = build_hpbw_traces(result, r_min=-25.0)
    # Max power circle: thick solid black.
    assert traces[0].line.color == "black"
    assert traces[0].line.width == 3
    # Half power circle: thin dashed black.
    assert traces[1].line.color == "black"
    assert traces[1].line.width == 1
    assert traces[1].line.dash == "dash"
    # Left/right radial lines: thick solid black.
    assert traces[2].line.width == 3
    assert traces[3].line.width == 3
    # Max theta radial line: thin dashed black.
    assert traces[4].line.width == 1
    assert traces[4].line.dash == "dash"


def test_build_hpbw_traces_legend_on_first_trace_only() -> None:
    result = HpbwResult(
        max_r=-18.0,
        max_theta=0.0,
        half_power=-21.01,
        left_theta=-10.0,
        right_theta=10.0,
        beam_width=20.0,
        label="HPBW: 20.0\u00b0 (-10.0\u00b0 to 10.0\u00b0)",
    )
    traces = build_hpbw_traces(result, r_min=-25.0)
    assert traces[0].showlegend is True
    assert traces[0].name == result.label
    for trace in traces[1:]:
        assert trace.showlegend is False
