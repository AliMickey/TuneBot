def format_duration(seconds):
    """Formats duration in seconds to days, hours, minutes, seconds format."""
    if seconds is None:
        return "Unknown"

    seconds = int(seconds)
    days, remainder = divmod(seconds, 86400)  # 86400 seconds in a day
    hours, remainder = divmod(remainder, 3600)  # 3600 seconds in an hour
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if seconds > 0 or not parts:  # Show seconds if less than a minute or no other parts
        parts.append(f"{seconds}s")

    return " ".join(parts)
  