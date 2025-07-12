from datetime import datetime, timedelta

import pandas as pd

# Columns we want to aggregate from the appearances dataset
AGG_COLS = [
    "yellow_cards",
    "red_cards",
    "goals",
    "assists",
    "minutes_played",
]


def season_start(d: datetime) -> datetime:
    """Return August 1st that marks the beginning of the football season for date *d*.

    Examples
    --------
    >>> season_start(datetime(2025, 2, 3))  # Winter window in season 24/25
    datetime(2024, 8, 1, 0, 0)
    >>> season_start(datetime(2024, 8, 5))  # Summer 24/25 window, season 24/25 start
    datetime(2024, 8, 1, 0, 0)
    """
    year = d.year if d.month >= 8 else d.year - 1
    return datetime(year, 8, 1)


def window_for_transfer(tdate: datetime) -> tuple[datetime, datetime]:
    """Return the (start, end) dates of matches to aggregate for a transfer.

    Assumptions
    ----------
    • Season kickoff is **1 August** every year (pre-season friendlies in July are ignored).

    Month-based rules
    -----------------
    1. **December → May (inclusive)**
       Current season so far.
       Start = 1 Aug of the ongoing season, End = transfer_date – 1 day.

    2. **June → October (inclusive)**
       Full, previous season.
       Start = 1 Aug of previous season, End = 31 Jul of current year (i.e. 1 Aug current season – 1 day).

    3. **November** (or any other month not covered above)
       Defaults to the *current season so far* rule.
    """

    season_kickoff = season_start(tdate)  # Aug 1 of current season context

    # --------------------------- Primary window logic -----------------------
    month = tdate.month

    # Transfers occurring December (12) through May (5)
    # --------------------------------------------------
    if month in (12, 1, 2, 3, 4, 5):
        # Current season to date: Aug 1 of current season → day before transfer
        start = season_kickoff
        end = tdate - timedelta(days=1)

    # Transfers occurring June (6) through October (10)
    # --------------------------------------------------
    elif month in (6, 7, 8, 9, 10):
        # Entire previous season: Aug 1 (prev year) → Jul 31 (current year)
        prev_season_start = season_kickoff - timedelta(days=365)
        start = prev_season_start
        end = season_kickoff - timedelta(days=1)

    # For completeness, default any other month (e.g., November) to current season to date
    else:
        start = season_kickoff
        end = tdate - timedelta(days=1)

    return start, end


def main() -> None:
    # 1. Load datasets ---------------------------------------------------------
    apps = pd.read_csv("appearances.csv", parse_dates=["date"])
    transfers = pd.read_csv("transfers.csv")

    # Parse transfer_date given as MM/DD/YYYY (e.g., 2/3/2025). Raise if any fail.
    try:
        transfers["transfer_date"] = pd.to_datetime(
            transfers["transfer_date"], format="%m/%d/%Y", errors="raise"
        )
    except ValueError as e:
        # Display problematic rows for easier debugging
        failed_mask = pd.to_datetime(
            transfers["transfer_date"], format="%m/%d/%Y", errors="coerce"
        ).isna()
        bad_examples = transfers.loc[failed_mask, "transfer_date"].unique()[:10]
        raise ValueError(
            f"Failed to parse some transfer_date values. Examples: {bad_examples}\nDetails: {e}"
        )

    # 2. Prepare target columns ----------------------------------------------
    for col in AGG_COLS:
        transfers[f"season_{col}"] = 0

    # 3. Aggregate per transfer ----------------------------------------------
    for idx, row in transfers.iterrows():
        start, end = window_for_transfer(row["transfer_date"])
        player_id = row["player_id"]

        mask = (apps["player_id"] == player_id) & (
            (apps["date"] >= start) & (apps["date"] <= end)
        )
        sums = apps.loc[mask, AGG_COLS].sum().fillna(0)

        # Assign the values back to the corresponding season_* columns
        transfers.loc[idx, [f"season_{c}" for c in AGG_COLS]] = sums.values

    # 4. Save enriched dataset ----------------------------------------------
    transfers.to_csv("transfers_enriched.csv", index=False)
    print("Saved transfers_enriched.csv with aggregated season statistics.")


if __name__ == "__main__":
    main()
