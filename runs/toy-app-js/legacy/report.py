from legacycorp_normalize import normalize_name
from mathutils import integer_average


def format_report(name, scores):
    display_name = normalize_name(name) if name is not None else None
    avg = integer_average(scores)
    return f"Report for {display_name}: average score = {avg}"
