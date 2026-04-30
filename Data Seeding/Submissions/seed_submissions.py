"""
seed_submission_v6.py
----------------------
Usage:
    Place ta_leave_data.csv in same directory, then:
    python seed_submissions_v6.py
"""

import pandas as pd
import numpy as np
import random
import math
from datetime import date, timedelta

RANDOM_SEED = 42

EMPLOYEES = {
    "barbara":  "barbara@crps.co.us",
    "jacob": "jacob@crps.co.us",
    "ava":   "ava@crps.co.us",
}

SCHOOL_YEARS = {
    "2024-2025": (date(2024, 9,  7), date(2025, 8, 30)),
    "2025-2026": (date(2025, 9,  6), date(2026, 8, 29)),
}
SCHOOL_IN_SESSION = {
    "2024-2025": (date(2024, 9,  7), date(2025, 5, 17)),
    "2025-2026": (date(2025, 9,  6), date(2026, 5, 16)),
}
GRADUATION = {
    "2024-2025": (date(2025, 5, 24), date(2025, 6,  7)),
    "2025-2026": (date(2026, 5, 23), date(2026, 6,  6)),
}
SUMMER = {
    "2024-2025": (date(2025, 6, 14), date(2025, 8, 30)),
    "2025-2026": (date(2026, 6, 13), date(2026, 8, 29)),
}
SPRING_HIRING = {
    "2024-2025": (date(2025, 2,  8), date(2025, 3, 29)),
    "2025-2026": (date(2026, 2,  7), date(2026, 3, 28)),
}
RETREAT_WEEK = {
    "2024-2025": date(2025, 8, 30),
    "2025-2026": date(2026, 8, 29),
}
BARBARA_CRISIS = {
    "2025-2026": (date(2026, 1, 10), date(2026, 1, 31)),
}

DISTRIBUTIONS = {
    "barbara": {
        "2024-2025": {"IL":0.35,"Ops":0.44,"PD":0.05,"CE":0.09,"Oth":0.07},
        "2025-2026": {"IL":0.46,"Ops":0.37,"PD":0.03,"CE":0.09,"Oth":0.05},
    },
    "jacob": {
        "2024-2025": {"IL":0.34,"Ops":0.42,"PD":0.06,"CE":0.10,"Oth":0.08},
        "2025-2026": {"IL":0.55,"Ops":0.24,"PD":0.05,"CE":0.09,"Oth":0.07},
    },
    "ava": {
        "2024-2025": {"IL":0.32,"Ops":0.40,"PD":0.04,"CE":0.13,"Oth":0.11},
        "2025-2026": {"IL":0.45,"Ops":0.32,"PD":0.05,"CE":0.08,"Oth":0.10},
    },
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def r30(x):
    """Round to nearest 0.5 (30-min increment)."""
    return round(float(x) * 2) / 2

def floor30(x):
    """Floor to nearest 0.5."""
    return math.floor(float(x) * 2) / 2

def get_saturdays(start, end):
    d = start
    while d.weekday() != 5:
        d += timedelta(days=1)
    result = []
    while d <= end:
        result.append(d)
        d += timedelta(weeks=1)
    return result

def in_range(d, period):
    return period[0] <= d <= period[1]

def distribute_cv(total, n, cv, rng, min_val=0.0):
    """Distribute total across n items with approx CV, rounded to 0.5."""
    if n <= 0 or total <= 0:
        return [0.0] * max(n, 0)
    mean = total / n
    std  = mean * cv
    raw  = [max(min_val, rng.gauss(mean, std)) for _ in range(n)]
    s = sum(raw)
    if s <= 0:
        scaled = [total / n] * n
    else:
        scaled = [v * total / s for v in raw]
    rounded = [r30(v) for v in scaled]
    # Absorb rounding residual into a random week
    diff = total - sum(rounded)
    if abs(diff) > 0.01 and rounded:
        idx = rng.randrange(len(rounded))
        rounded[idx] = r30(rounded[idx] + diff)
    return rounded

# ── Leave data ────────────────────────────────────────────────────────────────

def load_leave():
    try:
        df = pd.read_csv("ta_leave_data.csv")
        df.columns = [c.upper().strip() for c in df.columns]
        df["WEEK_ENDING_DATE"] = pd.to_datetime(
            df["WEEK_ENDING_DATE"], format="%m/%d/%Y", errors="coerce"
        ).dt.date
        mask = df["WEEK_ENDING_DATE"].isna()
        if mask.any():
            df.loc[mask, "WEEK_ENDING_DATE"] = pd.to_datetime(
                df.loc[mask, "WEEK_ENDING_DATE"]
            ).dt.date
        print(f"  Loaded {len(df)} leave records.")
        return df
    except FileNotFoundError:
        print("  NOTE: ta_leave_data.csv not found — zero leave assumed.")
        return pd.DataFrame(columns=[
            "EMPLOYEE_EMAIL","WEEK_ENDING_DATE",
            "HOLIDAY_HOURS","PTO_HOURS","SICK_HOURS","TOTAL_LEAVE_HOURS"
        ])

def get_leave(df, email, week):
    row = df[(df["EMPLOYEE_EMAIL"]==email) & (df["WEEK_ENDING_DATE"]==week)]
    if row.empty:
        return {"HL":0,"PL":0,"TL":0}
    r = row.iloc[0]
    hl = float(r.get("HOLIDAY_HOURS", 0))
    pl = float(r.get("PTO_HOURS", 0)) + float(r.get("SICK_HOURS", 0))
    return {"HL":hl, "PL":pl, "TL":hl+pl}

# ── Step 1: Compute exact worked hours per week from scenario tables ───────────

def compute_worked_hours(weeks, emp, sy, leave_df, email, rng):
    """
    Returns worked[w] = exact hours to be worked that week.
    This is the IMMUTABLE per-week total. All category allocations
    must sum to exactly this value.
    """
    result = {}
    crisis_range = BARBARA_CRISIS.get(sy) if emp == "barbara" else None

    for w in weeks:
        lv = get_leave(leave_df, email, w)
        hl, pl = lv["HL"], lv["PL"]
        is_summer = in_range(w, SUMMER[sy])
        is_crisis = (crisis_range and crisis_range[0] <= w <= crisis_range[1])

        # ── Barbara ────────────────────────────────────────────────────────────
        if emp == "barbara":
            if pl >= 40:                              # Scenario C
                result[w] = 0.0
            elif pl > 0:                              # Scenario B / E
                result[w] = r30(max(0, 40 - (hl + pl)))
            elif hl >= 40:                            # Scenario G
                result[w] = r30(rng.uniform(60.5, 65)) if is_crisis else 0.0
            elif hl > 0:                              # Scenario D
                lo = 40 - hl
                if is_crisis:
                    result[w] = r30(rng.uniform(60.5, 65))
                elif is_summer:
                    result[w] = r30(rng.uniform(lo, 45))
                else:
                    result[w] = r30(rng.uniform(lo, 65))
            else:                                     # Scenario A
                if is_crisis:
                    result[w] = r30(rng.uniform(60.5, 65))
                elif is_summer:
                    result[w] = r30(rng.uniform(40, 45))
                else:
                    result[w] = r30(rng.uniform(50, 65))

        # ── Jacob ───────────────────────────────────────────────────────────
        elif emp == "jacob":
            if pl >= 40:                              # Scenario C
                result[w] = 0.0
            elif pl > 0:                              # Scenario B / E
                result[w] = r30(max(0, 40 - (hl + pl)))
            elif hl >= 40:                            # Scenario G
                result[w] = 0.0
            elif hl > 0:                              # Scenario D
                lo = 40 - hl
                hi = 42 if is_summer else 60
                result[w] = r30(rng.uniform(lo, hi))
            else:                                     # Scenario A
                if is_summer:
                    result[w] = r30(rng.uniform(40, 42))
                else:
                    result[w] = r30(rng.uniform(45, 60))

        # ── Ava ─────────────────────────────────────────────────────────────
        elif emp == "ava":
            if pl >= 40:                              # Scenario C
                result[w] = 0.0
            elif pl > 0:                              # Scenario B / E
                result[w] = r30(max(0, 40 - (hl + pl)))
            elif hl >= 40:                            # Scenario G
                result[w] = 0.0
            elif hl > 0:                              # Scenario D — works exactly non-holiday hours
                result[w] = r30(40 - hl)
            else:                                     # Scenario A
                result[w] = 40.0 if is_summer else r30(rng.uniform(40, 42))

    return result

# ── Step 2: Classify weeks ────────────────────────────────────────────────────

def classify_weeks(weeks, sy, emp, worked, leave_df, email):
    """
    Returns dict of week -> classification used for category allocation.
    Classifications: 'zero', 'majority_pl', 'retreat', 'graduation',
                     'spring', 'crisis', 'summer', 'school'
    """
    classes = {}
    grad_s,  grad_e  = GRADUATION[sy]
    sum_s,   sum_e   = SUMMER[sy]
    sis_s,   sis_e   = SCHOOL_IN_SESSION[sy]
    spr_s,   spr_e   = SPRING_HIRING[sy]
    retreat          = RETREAT_WEEK[sy]
    crisis_range     = BARBARA_CRISIS.get(sy) if emp == "barbara" else None

    for w in weeks:
        lv = get_leave(leave_df, email, w)
        pl = lv["PL"]
        wh = worked[w]

        if wh == 0:
            classes[w] = 'zero'
        elif 32 <= pl < 40:
            classes[w] = 'majority_pl'
        elif w == retreat:
            classes[w] = 'retreat'
        elif grad_s <= w <= grad_e:
            classes[w] = 'graduation'
        elif crisis_range and crisis_range[0] <= w <= crisis_range[1]:
            classes[w] = 'crisis'
        elif spr_s <= w <= spr_e:
            classes[w] = 'spring'
        elif sum_s <= w <= sum_e:
            classes[w] = 'summer'
        elif sis_s <= w <= sis_e:
            classes[w] = 'school'
        else:
            classes[w] = 'school'  # fallback

    return classes

# ── Step 3: Initial category allocation per week ──────────────────────────────

def initial_allocation(weeks, worked, classes, dist, rng):
    """
    Assign initial category splits for each week based on classification.
    Returns dict of week -> {IL, Ops, PD, CE, Oth} summing to worked[w].

    These are INITIAL proportions — they will be scaled to hit annual targets.
    """
    alloc = {w: {"IL":0.0,"Ops":0.0,"PD":0.0,"CE":0.0,"Oth":0.0} for w in weeks}

    for w in weeks:
        wh = worked[w]
        cl = classes[w]

        if wh == 0 or cl == 'zero':
            continue

        if cl == 'majority_pl':
            # Framework 3.a: 1 hr Other, rest Ops
            oth = min(1.0, wh)
            ops = r30(max(0, wh - oth))
            alloc[w] = {"IL":0.0,"Ops":ops,"PD":0.0,"CE":0.0,"Oth":oth}

        elif cl == 'retreat':
            # Framework 3.c.i: 32 hrs ProfDev, rest as normal school split
            pd_ = min(32.0, wh)
            remainder = r30(wh - pd_)
            if remainder > 0:
                il_pct  = dist["IL"] / (dist["IL"] + dist["Ops"])
                ops_pct = dist["Ops"] / (dist["IL"] + dist["Ops"])
                il  = r30(remainder * il_pct)
                ops = r30(remainder - il)
            else:
                il = ops = 0.0
            alloc[w] = {"IL":il,"Ops":ops,"PD":pd_,"CE":0.0,"Oth":0.0}

        elif cl == 'graduation':
            # Framework 3.d.i: 75-85% CE of remaining after Other, 0 IL, rest Ops
            oth = r30(min(rng.uniform(1, 3), wh))
            rem = r30(wh - oth)
            if rem > 0:
                ce_pct = rng.uniform(0.75, 0.85)
                ce  = r30(rem * ce_pct)
                ops = r30(rem - ce)
            else:
                ce = ops = 0.0
            alloc[w] = {"IL":0.0,"Ops":ops,"PD":0.0,"CE":ce,"Oth":oth}

        elif cl == 'crisis':
            # Framework 4.a.ii.1: crisis uses spring hiring split (70-90% Ops)
            oth = r30(min(rng.uniform(1, 3), wh * 0.05))
            rem = r30(wh - oth)
            if rem > 0:
                ops_pct = rng.uniform(0.70, 0.90)
                ops = r30(rem * ops_pct)
                il  = r30(rem - ops)
            else:
                il = ops = 0.0
            alloc[w] = {"IL":il,"Ops":ops,"PD":0.0,"CE":0.0,"Oth":oth}

        elif cl == 'spring':
            # Framework 3.e.ii: 70-90% Ops
            oth = r30(min(rng.uniform(1, 3), wh * 0.05))
            rem = r30(wh - oth)
            if rem > 0:
                ops_pct = rng.uniform(0.70, 0.90)
                ops = r30(rem * ops_pct)
                il  = r30(rem - ops)
            else:
                il = ops = 0.0
            alloc[w] = {"IL":il,"Ops":ops,"PD":0.0,"CE":0.0,"Oth":oth}

        elif cl == 'summer':
            # Summer: low CE (0-3 hrs), minimal Other, rest IL+Ops
            oth = r30(min(rng.uniform(1, 3), wh))
            ce  = r30(min(rng.uniform(0, 3), max(0, wh - oth)))
            rem = r30(wh - oth - ce)
            if rem > 0:
                il_pct = dist["IL"] / (dist["IL"] + dist["Ops"])
                il  = r30(rem * il_pct)
                ops = r30(rem - il)
            else:
                il = ops = 0.0
            alloc[w] = {"IL":il,"Ops":ops,"PD":0.0,"CE":ce,"Oth":oth}

        else:  # school
            # Normal school week: use target proportions as initial split
            oth = r30(min(rng.uniform(1, 4), wh * dist["Oth"] * 2))
            rem = r30(wh - oth)
            if rem > 0:
                total_rem_pct = dist["IL"] + dist["Ops"] + dist["PD"] + dist["CE"]
                il  = r30(rem * dist["IL"]  / total_rem_pct)
                ops = r30(rem * dist["Ops"] / total_rem_pct)
                pd_ = r30(rem * dist["PD"]  / total_rem_pct)
                ce  = r30(rem - il - ops - pd_)
            else:
                il = ops = pd_ = ce = 0.0
            alloc[w] = {"IL":il,"Ops":ops,"PD":pd_,"CE":ce,"Oth":oth}

        # Ensure exact sum = worked[w] via adjustment to Ops
        total = sum(alloc[w].values())
        diff  = r30(wh - total)
        if abs(diff) > 0.01:
            alloc[w]["Ops"] = r30(max(0, alloc[w]["Ops"] + diff))
            # Recheck
            total2 = sum(alloc[w].values())
            diff2  = r30(wh - total2)
            if abs(diff2) > 0.01:
                alloc[w]["IL"] = r30(max(0, alloc[w]["IL"] + diff2))

    return alloc

# ── Step 4: Scale to annual targets ──────────────────────────────────────────

def scale_to_targets(weeks, worked, alloc, classes, dist, rng):
    """
    Scale category allocations to hit annual percentage targets,
    while keeping each week's total exactly at worked[w].

    Strategy:
    - Fixed weeks (majority_pl, retreat, graduation, crisis, spring):
      keep as-is, deduct from annual targets
    - Flexible weeks (school, summer):
      redistribute remaining annual target proportionally,
      then enforce per-week total constraint
    """
    hrs_total_annual = sum(worked[w] for w in weeks)
    if hrs_total_annual == 0:
        return alloc

    # Annual targets in hours
    targets = {
        cat: r30(hrs_total_annual * dist[cat])
        for cat in ["IL","Ops","PD","CE","Oth"]
    }

    # Fixed week classifications — keep exactly as allocated
    fixed = {'zero','majority_pl','retreat','graduation','crisis','spring'}
    flexible = [w for w in weeks if classes[w] not in fixed and worked[w] > 0]

    # Deduct fixed weeks from targets
    remaining_targets = {cat: targets[cat] for cat in targets}
    for w in weeks:
        if classes[w] in fixed or worked[w] == 0:
            for cat in ["IL","Ops","PD","CE","Oth"]:
                remaining_targets[cat] = r30(
                    remaining_targets[cat] - alloc[w][cat]
                )

    # Total flexible worked hours
    flex_total = sum(worked[w] for w in flexible)

    if flex_total == 0 or not flexible:
        return alloc

    # For flexible weeks, redistribute each category proportionally
    # First pass: assign proportional share per week
    new_alloc = {w: dict(alloc[w]) for w in weeks}

    for cat in ["IL","Ops","PD","CE","Oth"]:
        cat_target = max(0, remaining_targets[cat])
        if cat_target <= 0:
            for w in flexible:
                new_alloc[w][cat] = 0.0
            continue

        # Distribute with CV 0.3 across flexible weeks
        n = len(flexible)
        vals = distribute_cv(cat_target, n, 0.3, rng)
        for w, v in zip(flexible, vals):
            new_alloc[w][cat] = v

    # Second pass: enforce per-week total constraint
    # For each flexible week, scale all categories so they sum to worked[w]
    for w in flexible:
        wh    = worked[w]
        total = sum(new_alloc[w][cat] for cat in ["IL","Ops","PD","CE","Oth"])
        if total <= 0:
            continue
        if abs(total - wh) > 0.01:
            scale = wh / total
            for cat in ["IL","Ops","PD","CE","Oth"]:
                new_alloc[w][cat] = floor30(new_alloc[w][cat] * scale)
            # Fix any residual in Ops
            total2 = sum(new_alloc[w][cat] for cat in ["IL","Ops","PD","CE","Oth"])
            diff   = r30(wh - total2)
            if abs(diff) > 0.01:
                new_alloc[w]["Ops"] = r30(max(0, new_alloc[w]["Ops"] + diff))

    # Third pass: rebalance to hit annual targets
    # After per-week enforcement, category annual totals may have drifted
    # Rebalance by adbarbarag IL vs Ops (most flexible pair) in flexible weeks
    for cat in ["IL","Ops","PD","CE","Oth"]:
        actual = sum(new_alloc[w][cat] for w in weeks)
        target = targets[cat]
        diff   = r30(target - actual)
        if abs(diff) < 0.5:
            continue
        # Absorb diff into flexible school weeks by adbarbarag IL<->Ops pair
        school_weeks = [w for w in flexible if classes[w] == 'school']
        if not school_weeks:
            school_weeks = flexible
        if cat in ("IL","Ops"):
            opposite = "Ops" if cat == "IL" else "IL"
            per_week = diff / len(school_weeks)
            for w in school_weeks:
                wh = worked[w]
                add = r30(per_week)
                new_val = r30(new_alloc[w][cat] + add)
                opp_val = r30(new_alloc[w][opposite] - add)
                if new_val >= 0 and opp_val >= 0:
                    new_alloc[w][cat]     = new_val
                    new_alloc[w][opposite] = opp_val

    # Final per-week total enforcement after rebalancing
    for w in flexible:
        wh    = worked[w]
        total = sum(new_alloc[w][cat] for cat in ["IL","Ops","PD","CE","Oth"])
        diff  = r30(wh - total)
        if abs(diff) > 0.01:
            new_alloc[w]["Ops"] = r30(max(0, new_alloc[w]["Ops"] + diff))

    return new_alloc

# ── Main allocation ───────────────────────────────────────────────────────────

def allocate_employee_year(emp, email, sy, leave_df, rng):
    sy_start, sy_end = SCHOOL_YEARS[sy]
    weeks = get_saturdays(sy_start, sy_end)
    dist  = DISTRIBUTIONS[emp][sy]

    # Step 1: compute exact worked hours per week
    worked = compute_worked_hours(weeks, emp, sy, leave_df, email, rng)

    # Step 2: classify weeks
    classes = classify_weeks(weeks, sy, emp, worked, leave_df, email)

    # Step 3: initial category allocation
    alloc = initial_allocation(weeks, worked, classes, dist, rng)

    # Step 4: scale to annual targets while preserving per-week totals
    alloc = scale_to_targets(weeks, worked, alloc, classes, dist, rng)

    # Assemble output rows
    rows = []
    for w in weeks:
        il  = alloc[w]["IL"]
        ops = alloc[w]["Ops"]
        pd_ = alloc[w]["PD"]
        ce  = alloc[w]["CE"]
        oth = alloc[w]["Oth"]
        total = r30(il + ops + pd_ + ce + oth)

        rows.append({
            "Title":                       f"{email} - {w.strftime('%Y-%m-%d')}",
            "SubmittedByEmail":            email,
            "WeekEndingDate":              w.strftime("%#m/%#d/%Y"),
            "SchoolYear":                  sy,
            "SubmissionStatus":            "Submitted",
            "hrs_InstructionalLeadership": il,
            "hrs_Operations":              ops,
            "hrs_ProfDev":                 pd_,
            "hrs_CommunityEngagement":     ce,
            "hrs_Other":                   oth,
            "hrs_Total":                   total,
            "Notes":                       "",
        })

    return rows

# ── Summary and validation ────────────────────────────────────────────────────

def print_summary(df, leave_df):
    print("\nAllocation summary:")
    print(f"  {'Emp':<8} {'Year':<12} {'IL%':>6} {'Ops%':>6} "
          f"{'PD%':>5} {'CE%':>5} {'Oth%':>6} {'Total':>7}  Targets")
    print("  " + "─"*72)
    warnings = 0
    for emp in ["barbara","jacob","ava"]:
        email = EMPLOYEES[emp]
        for sy in ["2024-2025","2025-2026"]:
            s = df[(df["SubmittedByEmail"]==email) & (df["SchoolYear"]==sy)]
            t = s["hrs_Total"].sum()
            if t == 0: continue
            d   = DISTRIBUTIONS[emp][sy]
            il  = s["hrs_InstructionalLeadership"].sum()/t
            ops = s["hrs_Operations"].sum()/t
            pd_ = s["hrs_ProfDev"].sum()/t
            ce  = s["hrs_CommunityEngagement"].sum()/t
            oth = s["hrs_Other"].sum()/t
            tgt = (f"IL:{d['IL']:.0%} Op:{d['Ops']:.0%} "
                   f"PD:{d['PD']:.0%} CE:{d['CE']:.0%} Ot:{d['Oth']:.0%}")
            print(f"  {emp:<8} {sy:<12} {il:>6.1%} {ops:>6.1%} "
                  f"{pd_:>5.1%} {ce:>5.1%} {oth:>6.1%} {t:>7.0f}  {tgt}")
            for cat, actual, target in [
                ("IL",il,d["IL"]),("Ops",ops,d["Ops"]),("PD",pd_,d["PD"]),
                ("CE",ce,d["CE"]),("Oth",oth,d["Oth"])
            ]:
                if abs(actual-target) > 0.01:
                    print(f"    ⚠ {emp} {sy} {cat}: {actual:.1%} vs {target:.0%}")
                    warnings += 1

    # Per-week total validation
    df2 = df.copy()
    df2["WeekEndingDate"] = pd.to_datetime(df2["WeekEndingDate"]).dt.date
    merged = df2.merge(
        leave_df[["EMPLOYEE_EMAIL","WEEK_ENDING_DATE","HOLIDAY_HOURS",
                  "PTO_HOURS","SICK_HOURS","TOTAL_LEAVE_HOURS"]],
        left_on=["SubmittedByEmail","WeekEndingDate"],
        right_on=["EMPLOYEE_EMAIL","WEEK_ENDING_DATE"], how="left"
    )
    for c in ["HOLIDAY_HOURS","PTO_HOURS","SICK_HOURS","TOTAL_LEAVE_HOURS"]:
        merged[c] = merged[c].fillna(0)
    merged["PL"] = merged["PTO_HOURS"] + merged["SICK_HOURS"]
    merged["total_weekly"] = merged["TOTAL_LEAVE_HOURS"] + merged["hrs_Total"]
    merged["cat_sum"] = (merged["hrs_InstructionalLeadership"] +
                         merged["hrs_Operations"] + merged["hrs_ProfDev"] +
                         merged["hrs_CommunityEngagement"] + merged["hrs_Other"])

    pl_violations = merged[(merged["PL"]>0) & (merged["total_weekly"]>40)]
    cat_mismatches = merged[abs(merged["cat_sum"]-merged["hrs_Total"])>0.01]

    print(f"\n  Total rows: {len(df)}")
    print(f"  Leave validation violations: {len(pl_violations)}"
          + (" ✓" if pl_violations.empty else " ⚠"))
    print(f"  Category sum mismatches: {len(cat_mismatches)}"
          + (" ✓" if cat_mismatches.empty else " ⚠"))
    if warnings == 0:
        print("  ✓ All distributions within ±1% of target.")
    else:
        print(f"  ⚠ {warnings} distributions outside ±1% tolerance.")

# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    rng = random.Random(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)

    print("Loading T&A leave data...")
    leave_df = load_leave()

    print("\nGenerating submissions...")
    all_rows = []
    for emp, email in EMPLOYEES.items():
        for sy in ["2024-2025","2025-2026"]:
            emp_rng = random.Random(RANDOM_SEED ^ hash(emp) ^ hash(sy))
            rows = allocate_employee_year(emp, email, sy, leave_df, emp_rng)
            all_rows.extend(rows)
            print(f"  {emp} {sy}: {len(rows)} weeks")

    df = pd.DataFrame(all_rows)
    print_summary(df, leave_df)

    out = "submissions_seed.csv"
    df.to_csv(out, index=False)
    print(f"\nOutput written to: {out}")

if __name__ == "__main__":
    main()
