        v1 = s.iloc[-1]
        v0 = s.iloc[-LOOKBACK_DAYS]
        if hasattr(v1, "item"):
            v1 = v1.item()
        if hasattr(v0, "item"):
            v0 = v0.item()
        out[sym] = float(v1 / v0 - 1.0)
