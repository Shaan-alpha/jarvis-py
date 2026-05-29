from config.settings import (
    HUD_THEME_DAY_START,
    HUD_THEME_EVENING_START,
    HUD_THEME_NIGHT_START,
)


def theme_for_hour(hour):
    """Map a 24h hour (0-23) to a HUD theme name: cyan / gold / frost."""

    if HUD_THEME_DAY_START <= hour < HUD_THEME_EVENING_START:

        return "cyan"

    if HUD_THEME_EVENING_START <= hour < HUD_THEME_NIGHT_START:

        return "gold"

    return "frost"
