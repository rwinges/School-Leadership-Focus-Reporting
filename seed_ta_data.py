"""
seed_ta_data.py
---------------
Generates synthetic time-and-attendance (T&A) leave data for the School Leadership
Focus Reporting project and loads it into IBM Db2.

Leave year definition:
  - Starts on the first Sunday of the calendar year
  - Ends on the Saturday ending the last full week (last Sunday) of the year
  - Weeks straddling Dec 31 belong entirely to the year in which they start

Leave rules:
  - 160 hrs PTO + 40 hrs sick per leave year per employee (fully consumed)
  - Federal holidays + Christmas week are additive (do not reduce PTO/sick budget)
  - total_leave_hours (all types combined) cannot exceed 40 hrs in any week
  - Holiday hours fill a week first; PTO/sick may only use remaining headroom

Usage:
    pip install ibm_db python-dotenv pandas
    python seed_ta_data.py

.env file (same directory):
    DB2_HOSTNAME=...
    DB2_PORT=50001
    DB2_DATABASE=...
    DB2_USERNAME=...
    DB2_PASSWORD=...
"""

import os
import random
from datetime import date, timedelta

import pandas as pd
from dotenv import load_dotenv
import ibm_db

# ── Configuration ─────────────────────────────────────────────────────────────

load_dotenv()

EMPLOYEES = [
    "ryan@crps.co.us",
    "barbara@crps.co.us",
    "ava@crps.co.us",
    "jacob@crps.co.us",
]

CALENDAR_YEARS = [2024, 2025, 2026]

PTO_BUDGET_PER_YEAR  = 160   # hours
SICK_BUDGET_PER_YEAR =  40   # hours
HOURS_PER_DAY        =   8
HOURS_PER_WEEK       =  40

# US federal holidays within seeding range (date → holiday_hours)
FEDERAL_HOLIDAYS: dict[date, int] = {
    # 2024
    date(2024,  1, 15): 8,   # MLK Day
    date(2024,  2, 19): 8,   # Presidents Day
    date(2024,  5, 27): 8,   # Memorial Day
    date(2024,  6, 19): 8,   # Juneteenth
    date(2024,  7,  4): 8,   # Independence Day
    date(2024,  9,  2): 8,   # Labor Day
    date(2024, 10, 14): 8,   # Columbus Day (2024)
    date(2024, 11, 11): 8,   # Veterans Day
    date(2024, 11, 28): 8,   # Thanksgiving
    # 2025
    date(2025,  1, 20): 8,   # MLK Day
    date(2025,  2, 17): 8,   # Presidents Day
    date(2025,  5, 26): 8,   # Memorial Day
    date(2025,  6, 19): 8,   # Juneteenth
    date(2025,  7,  4): 8,   # Independence Day
    date(2025,  9,  1): 8,   # Labor Day
    date(2025, 10, 13): 8,   # Columbus Day
    date(2025, 11, 11): 8,   # Veterans Day
    date(2025, 11, 27): 8,   # Thanksgiving
    # 2026
    date(2026,  1, 19): 8,   # MLK Day
    date(2026,  2, 16): 8,   # Presidents Day
    date(2026,  5, 25): 8,   # Memorial Day
    date(2026,  6, 19): 8,   # Juneteenth
    date(2026,  7,  3): 8,   # Independence Day (observed)
    date(2026,  9,  7): 8,   # Labor Day
    date(2026, 10, 12): 8,   # Columbus Day
    date(2026, 11, 11): 8,   # Veterans Day
    date(2026, 11, 26): 8,   # Thanksgiving
}

# Christmas-to-New-Year paid holiday blocks.
# Key = week_ending (Saturday). Value = holiday hours for that week.
# The district gives the full week between Christmas and New Year's Day.
# We assign hours to the two Saturdays that bound that period.
CHRISTMAS_BLOCKS: dict[date, int] = {
    date(2024, 12, 28): 40,  # week Dec 23–28: full week holiday
    date(2025,  1,  4): 24,  # week Dec 29–Jan 4: Mon Dec 30–Wed Jan 1 = 3 days
    date(2025, 12, 27): 40,  # week Dec 22–27: full week holiday
    date(2026,  1,  3): 24,  # week Dec 28–Jan 3: Mon Dec 29–Wed Dec 31 = 3 days
    date(2026, 12, 26): 40,  # week Dec 21–26 (belongs to 2026 leave year)
    date(2027,  1,  1): 16,  # week Dec 27–Jan 1: Mon Dec 28–Thu Dec 31 = 4 days
                              # (this week starts Dec 27 2026 → 2026 leave year)
}


# ── Leave year helpers ────────────────────────────────────────────────────────

def first_sunday_of_year(year: int) -> date:
    """Return the first Sunday of the given calendar year."""
    d = date(year, 1, 1)
    # weekday(): Monday=0 ... Sunday=6
    days_until_sunday = (6 - d.weekday()) % 7
    return d + timedelta(days=days_until_sunday)


def last_sunday_of_year(year: int) -> date:
    """Return the last Sunday of the given calendar year."""
    d = date(year, 12, 31)
    days_back = d.weekday() + 1  # days back to Sunday (Sunday=6 → 1 day back... )
    # weekday() Sun=6, so days back to Sunday = (weekday+1) % 7
    days_back = (d.weekday() + 1) % 7
    return d - timedelta(days=days_back)


def get_leave_year_weeks(year: int) -> list[date]:
    """
    Return all week-ending Saturdays for the leave year.
    Leave year: first Sunday of year → Saturday ending the last Sunday of year.
    """
    start_sunday = first_sunday_of_year(year)
    last_sunday  = last_sunday_of_year(year)
    weeks = []
    sunday = start_sunday
    while sunday <= last_sunday:
        saturday = sunday + timedelta(days=6)
        weeks.append(saturday)
        sunday += timedelta(weeks=1)
    return weeks


def holiday_hours_for_week(week_ending: date) -> int:
    """
    Total holiday hours for the week ending on week_ending (Mon–Sat window).
    Christmas blocks take precedence. Federal holidays: 8 hrs each working day.
    Result capped at HOURS_PER_WEEK (40).
    """
    if week_ending in CHRISTMAS_BLOCKS:
        return min(CHRISTMAS_BLOCKS[week_ending], HOURS_PER_WEEK)

    monday = week_ending - timedelta(days=5)
    total = sum(
        FEDERAL_HOLIDAYS.get(monday + timedelta(days=i), 0)
        for i in range(5)   # Mon–Fri
    )
    return min(total, HOURS_PER_WEEK)


# ── Leave allocation ──────────────────────────────────────────────────────────

def allocate_leave_for_year(
    week_endings: list[date],
    pto_budget: int,
    sick_budget: int,
    rng: random.Random,
) -> pd.DataFrame:
    """
    Distribute PTO and sick hours across weeks for one employee-year.

    Rules:
    - Holidays fill each week first (up to 40 hrs)
    - PTO/sick may only occupy remaining headroom (40 - holiday_hours)
    - All PTO and sick budgets must be fully consumed
    - PTO is summer-weighted; sick is randomly scattered in 8-hr chunks

    Returns a DataFrame with columns:
        week_ending_date, holiday_hours, pto_hours, sick_hours, total_leave_hours
    """
    df = pd.DataFrame({"week_ending_date": week_endings})
    df["holiday_hours"] = df["week_ending_date"].apply(holiday_hours_for_week)
    df["headroom"]      = (HOURS_PER_WEEK - df["holiday_hours"]).clip(lower=0)
    df["pto_hours"]     = 0
    df["sick_hours"]    = 0

    # ── Sick leave: 8-hr chunks on random weeks with headroom ────────────
    sick_eligible_idx = df[df["headroom"] >= HOURS_PER_DAY].index.tolist()
    sick_remaining = sick_budget

    if sick_eligible_idx and sick_remaining > 0:
        num_sick_days = sick_remaining // HOURS_PER_DAY
        chosen = rng.sample(
            sick_eligible_idx,
            min(num_sick_days, len(sick_eligible_idx))
        )
        for idx in chosen:
            if sick_remaining <= 0:
                break
            place = min(HOURS_PER_DAY, sick_remaining, int(df.at[idx, "headroom"]))
            place = (place // HOURS_PER_DAY) * HOURS_PER_DAY
            if place > 0:
                df.at[idx, "sick_hours"] = place
                sick_remaining -= place

        # Safety pass: if hours remain, place on any eligible week
        if sick_remaining > 0:
            for idx in sick_eligible_idx:
                if sick_remaining <= 0:
                    break
                current_sick = int(df.at[idx, "sick_hours"])
                avail = int(df.at[idx, "headroom"]) - current_sick
                if avail >= HOURS_PER_DAY:
                    add = min(avail, sick_remaining)
                    add = (add // HOURS_PER_DAY) * HOURS_PER_DAY
                    df.at[idx, "sick_hours"] += add
                    sick_remaining -= add

    # Update headroom after sick placement
    df["headroom"] = (
        HOURS_PER_WEEK - df["holiday_hours"] - df["sick_hours"]
    ).clip(lower=0)

    # ── PTO: summer-weighted, fill to headroom ───────────────────────────
    # Weight: Jun–Aug = 5x, Dec–Jan = 2x (vacation-adjacent), rest = 1x
    def pto_weight(d: date) -> int:
        if d.month in (6, 7, 8):   return 5
        if d.month in (12, 1):     return 2
        return 1

    pto_eligible = df[df["headroom"] >= HOURS_PER_DAY].copy()
    pto_eligible["weight"] = pto_eligible["week_ending_date"].apply(pto_weight)

    pto_remaining = pto_budget

    # First pass: weighted random allocation in full-day (8 hr) chunks
    if not pto_eligible.empty and pto_remaining > 0:
        indices = pto_eligible.index.tolist()
        weights = pto_eligible["weight"].tolist()

        shuffled = rng.choices(indices, weights=weights, k=len(indices) * 3)
        seen = set()
        ordered = []
        for i in shuffled:
            if i not in seen:
                seen.add(i)
                ordered.append(i)
        # Add any missed indices
        for i in indices:
            if i not in seen:
                ordered.append(i)

        for idx in ordered:
            if pto_remaining <= 0:
                break
            avail = int(df.at[idx, "headroom"])
            if avail < HOURS_PER_DAY:
                continue
            place = min(avail, pto_remaining)
            place = (place // HOURS_PER_DAY) * HOURS_PER_DAY
            if place > 0:
                df.at[idx, "pto_hours"] = place
                df.at[idx, "headroom"]  = avail - place
                pto_remaining -= place

    # Safety pass: redistribute any unplaced PTO hours
    if pto_remaining > 0:
        for idx in df.index:
            if pto_remaining <= 0:
                break
            avail = int(df.at[idx, "headroom"])
            if avail < HOURS_PER_DAY:
                continue
            add = min(avail, pto_remaining)
            add = (add // HOURS_PER_DAY) * HOURS_PER_DAY
            if add > 0:
                df.at[idx, "pto_hours"] += add
                df.at[idx, "headroom"]  -= add
                pto_remaining -= add

    df["total_leave_hours"] = (
        df["holiday_hours"] + df["pto_hours"] + df["sick_hours"]
    ).clip(upper=HOURS_PER_WEEK)

    # Final integrity check
    assert (df["total_leave_hours"] <= HOURS_PER_WEEK).all(), \
        "FAIL: a week exceeds 40 total leave hours"

    return df[[
        "week_ending_date", "holiday_hours",
        "pto_hours", "sick_hours", "total_leave_hours"
    ]]


# ── Generate full dataset ─────────────────────────────────────────────────────

def build_dataset() -> pd.DataFrame:
    all_frames = []

    for year in CALENDAR_YEARS:
        weeks = get_leave_year_weeks(year)
        for email in EMPLOYEES:
            seed = hash(email) ^ (year * 7919)
            rng  = random.Random(seed)
            df   = allocate_leave_for_year(
                weeks, PTO_BUDGET_PER_YEAR, SICK_BUDGET_PER_YEAR, rng
            )
            df.insert(0, "employee_email", email)
            df.insert(1, "leave_year",     year)
            all_frames.append(df)

    full = pd.concat(all_frames, ignore_index=True)
    full["week_ending_date"] = pd.to_datetime(
        full["week_ending_date"]
    ).dt.strftime("%Y-%m-%d")
    return full


# ── Summary ───────────────────────────────────────────────────────────────────

def print_summary(df: pd.DataFrame) -> None:
    print("\nLeave summary (hours per employee per leave year):")
    print(f"  {'Email':<42} {'Year':>5} {'Holiday':>8} "
          f"{'PTO':>6} {'Sick':>6} {'Total':>7} {'Weeks':>6}")
    print("  " + "─" * 80)

    summary = (
        df.groupby(["employee_email", "leave_year"])
        .agg(
            holiday=("holiday_hours",     "sum"),
            pto    =("pto_hours",         "sum"),
            sick   =("sick_hours",        "sum"),
            total  =("total_leave_hours", "sum"),
            weeks  =("week_ending_date",  "count"),
        )
        .reset_index()
    )

    for _, row in summary.iterrows():
        print(
            f"  {row.employee_email:<42} {int(row.leave_year):>5} "
            f"{int(row.holiday):>8} {int(row.pto):>6} "
            f"{int(row.sick):>6} {int(row.total):>7} {int(row.weeks):>6}"
        )

    print(f"\n  Total rows: {len(df)}")

    # Flag any anomalies
    over_40 = df[df["total_leave_hours"] > HOURS_PER_WEEK]
    if not over_40.empty:
        print(f"\n  WARNING: {len(over_40)} rows exceed 40 hrs — investigate.")
    else:
        print("\n  All weeks within 40-hr cap.")

    under_pto = (
        df.groupby(["employee_email", "leave_year"])["pto_hours"]
        .sum()
        .reset_index()
    )
    under_pto = under_pto[under_pto["pto_hours"] < PTO_BUDGET_PER_YEAR]
    if not under_pto.empty:
        print(f"\n  WARNING: {len(under_pto)} employee-years have unspent PTO:")
        for _, r in under_pto.iterrows():
            print(f"    {r.employee_email} {int(r.leave_year)}: "
                  f"{int(r.pto_hours)} hrs (target {PTO_BUDGET_PER_YEAR})")


# ── Database ──────────────────────────────────────────────────────────────────

def get_connection():
    conn_str = (
        f"DATABASE={os.environ['DB2_DATABASE']};"
        f"HOSTNAME={os.environ['DB2_HOSTNAME']};"
        f"PORT={os.environ.get('DB2_PORT', '50001')};"
        f"PROTOCOL=TCPIP;"
        f"UID={os.environ['DB2_USERNAME']};"
        f"PWD={os.environ['DB2_PASSWORD']};"
        f"Security=SSL;"
    )
    conn = ibm_db.connect(conn_str, "", "")
    if not conn:
        raise ConnectionError(
            f"Db2 connection failed: {ibm_db.conn_errormsg()}"
        )
    print("Connected to IBM Db2.")
    return conn


def create_table_if_not_exists(conn) -> None:
    ddl = """
    CREATE TABLE IF NOT EXISTS TA_LEAVE_DATA (
        ID                INTEGER     NOT NULL GENERATED ALWAYS AS IDENTITY,
        EMPLOYEE_EMAIL    VARCHAR(120) NOT NULL,
        LEAVE_YEAR        SMALLINT     NOT NULL,
        WEEK_ENDING_DATE  DATE         NOT NULL,
        HOLIDAY_HOURS     SMALLINT     NOT NULL DEFAULT 0,
        PTO_HOURS         SMALLINT     NOT NULL DEFAULT 0,
        SICK_HOURS        SMALLINT     NOT NULL DEFAULT 0,
        TOTAL_LEAVE_HOURS SMALLINT     NOT NULL DEFAULT 0,
        CREATED_AT        TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (EMPLOYEE_EMAIL, WEEK_ENDING_DATE)
    )
    """
    try:
        ibm_db.exec_immediate(conn, ddl)
        print("Table TA_LEAVE_DATA ready.")
    except Exception as e:
        print(f"Table create note (may already exist): {e}")


def truncate_and_insert(conn, df: pd.DataFrame) -> None:
    # Truncate
    try:
        ibm_db.exec_immediate(conn, "TRUNCATE TABLE TA_LEAVE_DATA IMMEDIATE")
        print("Existing data cleared.")
    except Exception as e:
        print(f"Truncate note: {e}")

    # Prepared insert
    sql = """
    INSERT INTO TA_LEAVE_DATA
        (EMPLOYEE_EMAIL, LEAVE_YEAR, WEEK_ENDING_DATE,
         HOLIDAY_HOURS, PTO_HOURS, SICK_HOURS, TOTAL_LEAVE_HOURS)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    stmt = ibm_db.prepare(conn, sql)
    inserted = 0
    for row in df.itertuples(index=False):
        ibm_db.bind_param(stmt, 1, row.employee_email)
        ibm_db.bind_param(stmt, 2, int(row.leave_year))
        ibm_db.bind_param(stmt, 3, row.week_ending_date)
        ibm_db.bind_param(stmt, 4, int(row.holiday_hours))
        ibm_db.bind_param(stmt, 5, int(row.pto_hours))
        ibm_db.bind_param(stmt, 6, int(row.sick_hours))
        ibm_db.bind_param(stmt, 7, int(row.total_leave_hours))
        ibm_db.execute(stmt)
        inserted += 1

    ibm_db.commit(conn)
    print(f"Inserted and committed {inserted} rows.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Building synthetic T&A dataset...")
    df = build_dataset()
    print_summary(df)

    proceed = input("\nProceed with database load? [y/N]: ").strip().lower()
    if proceed != "y":
        print("Aborted — no data written.")
        return

    conn = get_connection()
    try:
        create_table_if_not_exists(conn)
        truncate_and_insert(conn, df)
        print("\nDone.")
    finally:
        ibm_db.close(conn)
        print("Connection closed.")


if __name__ == "__main__":
    main()
