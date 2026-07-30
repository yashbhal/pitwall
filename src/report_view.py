"""Presentation layer for :func:`src.session_analyzer.analyze_session` output.

Pure formatting only. No metric is computed, re-derived or re-ranked here: the
analyzer owns the numbers, this module decides how they read on a page. Keeping
it free of Flask makes it directly unit-testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Shown wherever the analyzer returned None because fewer than two valid
# attempts existed. It must never render as blank or as 0.
NOT_MEASURED = "n/a (needs 2+ valid attempts)"

# Neither gear_analyzer nor rpm_analyzer is wired into analyze_session(): its
# output contains no gear or RPM keys at all. So this is a static note about
# scope, not a conditional on missing data.
UNAVAILABLE_METRICS = (
    "Gear consistency",
    "RPM limiter dwell",
)
UNAVAILABLE_METRICS_NOTE = (
    "Not applicable to this report. These metrics are only meaningful with a "
    "manual gearbox, so they are not part of the session analysis output yet."
)


def format_metres(value: float | None, decimals: int = 1) -> str:
    """Format a distance in metres, distinguishing None from 0."""
    if value is None:
        return NOT_MEASURED
    return f"{value:.{decimals}f} m"


def format_speed(value: float | None) -> str:
    if value is None:
        return NOT_MEASURED
    return f"{value:.0f} km/h"


@dataclass(frozen=True)
class CornerView:
    """One corner row, pre-formatted for display."""

    name: str
    status: str
    is_priority: bool
    valid_attempts: int
    is_measured: bool
    onset_variation: str
    onset_stdev: str
    onset_distance: str
    onset_speed: str
    reapplication_count: int
    reapplication_total: int
    rejected_count: int
    feedback: str | None
    drill: str | None

    @property
    def has_data(self) -> bool:
        return self.status == "ok"


@dataclass(frozen=True)
class SessionView:
    """Everything one report page needs."""

    session_name: str
    track_name: str
    priority_corner: str | None
    priority_reason: str
    priority_feedback: str
    priority_drill: str
    corners: list[CornerView] = field(default_factory=list)
    unavailable_metrics: tuple[str, ...] = UNAVAILABLE_METRICS
    unavailable_metrics_note: str = UNAVAILABLE_METRICS_NOTE


def _priority_reason(corner: dict | None) -> str:
    """Explain the pick using only the fields the analyzer ranked on.

    session_analyzer ranks corners by, in order: whether onset variation could
    be measured, the variation itself, then reapplication_count, then
    onset_delta_abs. This restates that decision for the corner that won; it
    does not recompute the ranking.
    """
    if corner is None:
        return "No corner had a detectable brake onset, so nothing was ranked."

    variation = corner.get("onset_variation_m")
    attempts = corner.get("valid_attempts", 0)

    if variation is not None:
        return (
            f"Widest brake onset variation in the session: "
            f"{format_metres(variation)} across {attempts} valid attempt(s). "
            f"Onset variation is the primary ranking signal."
        )

    return (
        f"Onset variation could not be measured ({attempts} valid attempt(s), "
        f"2 are needed), so this corner was ranked on brake reapplications "
        f"({corner.get('reapplication_count', 0)}) and its onset distance "
        f"deviation from the configured reference "
        f"({format_metres(corner.get('onset_delta_abs'))})."
    )


def build_corner_view(
    name: str, data: dict, is_priority: bool
) -> CornerView:
    variation = data.get("onset_variation_m")

    return CornerView(
        name=name,
        status=data.get("status", "unknown"),
        is_priority=is_priority,
        valid_attempts=data.get("valid_attempts", 0),
        is_measured=variation is not None,
        onset_variation=format_metres(variation),
        onset_stdev=format_metres(data.get("onset_stdev_m")),
        onset_distance=format_metres(data.get("onset_distance_m")),
        onset_speed=format_speed(data.get("onset_speed_kmh")),
        reapplication_count=data.get("reapplication_count", 0),
        reapplication_total=data.get("reapplication_total", 0),
        rejected_count=len(data.get("rejected_attempts") or ()),
        feedback=data.get("feedback"),
        drill=data.get("drill"),
    )


def build_session_view(
    report: dict, session_name: str, track_name: str
) -> SessionView:
    """Turn an analyze_session() return value into a SessionView.

    Corners keep the order the analyzer returned them in (which is the track
    config order). Re-sorting them here would mean duplicating the analyzer's
    ranking rules in the view layer, and only the single priority corner is
    exposed in the output today.
    """
    all_corners = report.get("all_corners") or {}
    priority_corner = report.get("priority_corner")

    corners = [
        build_corner_view(name, data, is_priority=(name == priority_corner))
        for name, data in all_corners.items()
    ]

    return SessionView(
        session_name=session_name,
        track_name=track_name,
        priority_corner=priority_corner,
        priority_reason=_priority_reason(all_corners.get(priority_corner)),
        priority_feedback=report.get("priority_feedback") or "",
        priority_drill=report.get("priority_drill") or "",
        corners=corners,
    )
