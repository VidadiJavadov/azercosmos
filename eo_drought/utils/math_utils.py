def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def scale_0_100(x: float, lo: float, hi: float) -> float:
    if hi <= lo:
        return 0.0
    return clamp((x - lo) / (hi - lo) * 100.0, 0.0, 100.0)
