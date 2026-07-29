from __future__ import annotations

# How many laps a drill asks for. Not in the plan's threshold list, so it stays
# a coaching constant rather than an invented config key.
DEFAULT_DRILL_LAP_COUNT = 5


def generate_corner_feedback(
    corner_name: str,
    onset: dict,
    reapplications: list,
    reference: dict | None = None,
) -> str:
    """Generate human-readable brake feedback for a corner.

    This function is corner-agnostic and must not contain any track-specific or
    corner-specific literals. It only accepts already-extracted onset and
    reapplication data structures and returns a formatted string.
    """
    if onset is None:
        return f"No brake event found for {corner_name}."

    lines = [
        f"{corner_name}: brake onset at {onset['distance_m']:.1f} m, "
        f"speed {onset['speed_kmh']:.0f} km/h."
    ]

    if reapplications:
        distances = ", ".join(
            f"{event['distance_m']:.1f} m" for event in reapplications
        )
        lines.append(
            f"Detected {len(reapplications)} reapplication(s): at {distances}."
        )
    else:
        lines.append("Braking was clean with no reapplications.")

    if reference is not None:
        # Positive delta means the driver braked later; negative means earlier.
        delta = onset["distance_m"] - reference["distance_m"]
        lines.append(
            f"Comparison vs reference: onset delta {delta:+.1f} m "
            f"(positive = braked later, negative = braked earlier)."
        )

    return "\n".join(lines)


def generate_drill(
    corner_name: str,
    metrics: dict,
    minimum_valid_attempts: int,
    variation_warning_m: float,
    lap_count: int = DEFAULT_DRILL_LAP_COUNT,
) -> str:
    """Turn one corner's metrics into a single actionable practice drill.

    Follows the fixed templates in pitwall-plan.md section 12: no free-form
    text, no LLM. Thresholds arrive as plain scalars because this module must
    not read config directly.

    Selection order matches the session ranking: brake reapplication first,
    then onset variation. Below *minimum_valid_attempts* no drill is issued at
    all, since the plan warns against drawing conclusions from too little data.
    """
    attempts = metrics.get("valid_attempts") or 0

    if attempts < minimum_valid_attempts:
        return (
            f"Not enough data for a {corner_name} drill yet.\n"
            f"You have {attempts} valid attempt(s); "
            f"{minimum_valid_attempts} are needed before drawing a conclusion.\n"
            f"Next step: drive more clean laps through {corner_name}, "
            f"then re-run the analysis."
        )

    reapplication_total = metrics.get("reapplication_total") or 0
    if reapplication_total > 0:
        return (
            f"Focus: {corner_name} brake release.\n"
            f"You reapplied the brake {reapplication_total} time(s) "
            f"across {attempts} attempts.\n"
            f"Drill: Brake once in a straight line. As steering increases, "
            f"release brake pressure smoothly.\n"
            f"Target: zero brake reapplications over the next "
            f"{lap_count} laps."
        )

    variation_m = metrics.get("onset_variation_m")
    if variation_m is not None and variation_m > variation_warning_m:
        return (
            f"Focus: {corner_name} brake consistency.\n"
            f"Your brake start varied by {variation_m:.1f} m "
            f"across {attempts} valid entries.\n"
            f"Drill: Choose one visual braking marker. For the next "
            f"{lap_count} laps, begin braking within the same target window. "
            f"Do not chase lap time. Prioritize repeatability.\n"
            f"Target: brake onset variation below "
            f"{variation_warning_m:.0f} m."
        )

    if variation_m is None:
        return (
            f"{corner_name}: braking was clean with no reapplications, but "
            f"onset variation could not be measured.\n"
            f"Next step: drive more clean laps through {corner_name} to "
            f"establish a consistency baseline."
        )

    return (
        f"{corner_name}: no brake drill needed.\n"
        f"Brake start varied by {variation_m:.1f} m across {attempts} valid "
        f"entries, within the {variation_warning_m:.0f} m target, with no "
        f"brake reapplications.\n"
        f"Next step: keep this marker and move focus to another corner."
    )


if __name__ == "__main__":
    clean_onset = {"distance_m": 786.5, "speed_kmh": 327}
    messy_reapplications = [{"distance_m": 921.5}]

    print(generate_corner_feedback("Turn 1", clean_onset, []))
    print()
    print(
        generate_corner_feedback(
            "Turn 1", clean_onset, messy_reapplications
        )
    )
    print()
    print(
        generate_corner_feedback(
            "Turn 1",
            clean_onset,
            messy_reapplications,
            reference=clean_onset,
        )
    )
    print()
    later_reference = {"distance_m": 800.0, "speed_kmh": 320}
    print(
        generate_corner_feedback(
            "Turn 1",
            clean_onset,
            [],
            reference=later_reference,
        )
    )

    print()
    print("--- drills ---")
    for label, metrics in [
        ("too little data", {"valid_attempts": 2, "onset_variation_m": 26.9}),
        (
            "reapplication",
            {
                "valid_attempts": 5,
                "reapplication_total": 3,
                "onset_variation_m": 8.0,
            },
        ),
        (
            "variation",
            {
                "valid_attempts": 5,
                "reapplication_total": 0,
                "onset_variation_m": 26.9,
            },
        ),
        (
            "all clear",
            {
                "valid_attempts": 5,
                "reapplication_total": 0,
                "onset_variation_m": 8.0,
            },
        ),
    ]:
        print()
        print(f"[{label}]")
        print(
            generate_drill(
                "Turn 1",
                metrics,
                minimum_valid_attempts=5,
                variation_warning_m=15.0,
            )
        )
