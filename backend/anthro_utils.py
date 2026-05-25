import logging
import math
import json
import os

logger = logging.getLogger(__name__)

# Load Consolidated WHO LMS data
WHO_DATA = {}
try:
    data_path = os.path.join(
        os.path.dirname(__file__), "data", "who_standards_lms.json"
    )
    with open(data_path, "r") as f:
        WHO_DATA = json.load(f)
except Exception as e:
    logger.warning("Could not load WHO Standards data: %s", e)


def get_lms(indicator, gender, x_val):
    """
    Retrieves interpolated L, M, S values for a given indicator (wfa, hfa, bmifa)
    at a specific age (months) or height (wfh).
    """
    indices = WHO_DATA.get(indicator, {}).get(gender, {})
    if not indices:
        return None

    sorted_keys = sorted([int(k) for k in indices.keys()])
    if not sorted_keys:
        return None

    x = float(x_val)
    # Exact match or out of bounds
    if str(int(x)) in indices:
        dat = indices[str(int(x))]
        return float(dat["L"]), float(dat["M"]), float(dat["S"])

    if x <= sorted_keys[0]:
        dat = indices[str(sorted_keys[0])]
        return float(dat["L"]), float(dat["M"]), float(dat["S"])
    if x >= sorted_keys[-1]:
        dat = indices[str(sorted_keys[-1])]
        return float(dat["L"]), float(dat["M"]), float(dat["S"])

    # Linear Interpolation
    for i in range(len(sorted_keys) - 1):
        x1, x2 = sorted_keys[i], sorted_keys[i + 1]
        if x1 <= x <= x2:
            d1, d2 = indices[str(x1)], indices[str(x2)]
            f = (x - x1) / (x2 - x1)
            L = float(d1["L"]) + f * (float(d2["L"]) - float(d1["L"]))
            M = float(d1["M"]) + f * (float(d2["M"]) - float(d1["M"]))
            S = float(d1["S"]) + f * (float(d2["S"]) - float(d1["S"]))
            return L, M, S
    return None


def compute_z_score(val, L, M, S):
    if abs(L) < 0.0001:
        z = math.log(val / M) / S
    else:
        z = (math.pow(val / M, L) - 1) / (L * S)

    # Adjust for extreme Z-scores (WHO recommendation)
    if z > 3 or z < -3:
        try:
            # We approximate the SD units at the boundaries
            sd3pos = M * math.pow(1 + L * S * 3, 1 / L)
            sd2pos = M * math.pow(1 + L * S * 2, 1 / L)
            sd3neg = M * math.pow(1 + L * S * (-3), 1 / L)
            sd2neg = M * math.pow(1 + L * S * (-2), 1 / L)

            if z > 3:
                z = 3 + (val - sd3pos) / (sd3pos - sd2pos)
            elif z < -3:
                z = -3 + (val - sd3neg) / (sd2neg - sd3neg)
        except (ValueError, TypeError, ZeroDivisionError):
            pass
    return z


def calculate_anthro_stats(age_in_months, gender_str, weight, height):
    is_boy = gender_str.upper() == "BOY"
    gender_key = "boys" if is_boy else "girls"

    res = {
        "wfh_figure": None,
        "wfh_status": None,
        "wfa_figure": None,
        "wfa_status": None,
        "hfa_figure": None,
        "hfa_status": None,
        "bmifa_figure": None,
        "bmifa_status": None,
    }

    if weight <= 0 or height <= 0 or age_in_months < 0:
        return res

    # 1. WFA
    lms = get_lms("wfa", gender_key, age_in_months)
    if lms:
        z = compute_z_score(float(weight), *lms)
        res["wfa_figure"] = round(z, 2)
        if z > 2:
            res["wfa_status"] = "OVERWEIGHT"
        elif z < -3:
            res["wfa_status"] = "SEVERELY UNDERWEIGHT"
        elif z < -2:
            res["wfa_status"] = "UNDERWEIGHT"
        else:
            res["wfa_status"] = "NORMAL"

    # 2. HFA
    lms = get_lms("hfa", gender_key, age_in_months)
    if lms:
        z = compute_z_score(float(height), *lms)
        res["hfa_figure"] = round(z, 2)
        if z < -3:
            res["hfa_status"] = "SEVERELY STUNTED"
        elif z < -2:
            res["hfa_status"] = "STUNTED"
        elif z > 3:
            res["hfa_status"] = "TALL"
        else:
            res["hfa_status"] = "NORMAL"

    # 3. BMIFA
    bmi = float(weight) / ((float(height) / 100) ** 2)
    lms = get_lms("bmifa", gender_key, age_in_months)
    if lms:
        z = compute_z_score(bmi, *lms)
        res["bmifa_figure"] = round(bmi, 2)
        # WHO standard classification
        if z > 2:
            res["bmifa_status"] = "OBESE"
        elif z > 1:
            res["bmifa_status"] = "OVERWEIGHT"
        elif z < -3:
            res["bmifa_status"] = "SEVERELY WASTED"
        elif z < -2:
            res["bmifa_status"] = "WASTED"
        else:
            res["bmifa_status"] = "NORMAL"
    else:
        # Fallback for adults
        res["bmifa_figure"] = round(bmi, 2)
        if bmi < 18.5:
            res["bmifa_status"] = "UNDERWEIGHT"
        elif bmi < 24.9:
            res["bmifa_status"] = "NORMAL"
        elif bmi < 29.9:
            res["bmifa_status"] = "OVERWEIGHT"
        else:
            res["bmifa_status"] = "OBESE"

    # 4. WFH (Only for < 5 years usually)
    # For now, placeholder or uses Height as x_val if data exists
    # WHO data for WFH usually uses Length/Height
    return res
