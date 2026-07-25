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
