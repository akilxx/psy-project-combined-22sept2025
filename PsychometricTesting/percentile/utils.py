# percentile/utils.py
from .models import VariableDistribution

def compute_percentile(variable: str, score: float) -> float | None:
    """
    Return the percentile (0-100) or None if var not found
    or distribution empty.
    """
    try:
        dist_obj = VariableDistribution.objects.get(name=variable)
    except VariableDistribution.DoesNotExist:
        return None

    distribution = dist_obj.distribution
    total_freq = sum(d.get("frequency", 0) for d in distribution)
    if total_freq == 0:
        return None

    cumulative = sum(d.get("frequency", 0)
                     for d in distribution
                     if d.get("score") < score)

    return round((cumulative / total_freq) * 100, 2)
