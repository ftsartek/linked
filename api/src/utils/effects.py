"""Wormhole effect calculation utilities."""

from __future__ import annotations


def apply_class_multiplier(
    effects: dict[str, int | float] | None,
    wh_class: int | None,
) -> dict[str, int | float] | None:
    """Apply wormhole class multiplier to effect values.

    Args:
        effects: List of effect dicts like [{"Damage modifier": 30}, ...]
        wh_class: Wormhole class (1-6), or None for K-space

    Returns:
        Effects with multiplied values, or None if no effects
    """
    if effects is None or wh_class is None:
        return effects

    if wh_class not in range(1, 7):
        wh_class = 1

    multiplied_effect = {}
    for effect, value in effects.items():
        multiplied_effect[effect] = calculate_effect(value, wh_class)

    return multiplied_effect


def calculate_effect(effect: int | float, wh_class: int) -> float:
    """
    A C6 is always 10/3 (3.333...) * the base value of the effect (C1 value = base effect)
    Extrapolating to C1 = 15/15 (1) and C6 = 50/15, each interim class is represented by a step of 7 to the numerator
    over the base fraction, therefore C2 is 22/15, C5 is 43/15.

    :param effect:
    :param wh_class:
    :return:
    """
    return effect * (7 * wh_class + 8) / 15
