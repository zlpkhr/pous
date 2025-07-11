# Standard libs
import json
from pathlib import Path

# Third-party libs
import pandas as pd
from rapidfuzz import fuzz, process

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

# Load transfers as DataFrame
df = pd.read_csv(Path("transfers.csv"))

# Load UEFA club coefficients per season as nested mapping:
# {"22/23": {"Real Madrid": 381.0, ...}, ...}
with open(Path("uefa_rankings.json"), "r", encoding="utf-8") as fh:
    uefa_rankings: dict[str, dict[str, float]] = json.load(fh)

# ---------------------------------------------------------------------------
# Manual corrections from human-reviewed fuzzy matches
# ---------------------------------------------------------------------------

MANUAL_MAP: dict[tuple[str, str], str] = {}
corrections_path = Path("fuzzy_corrections.csv")
if corrections_path.exists():
    corrections_df = pd.read_csv(corrections_path)

    # Keep only rows explicitly approved by the user
    for _, row in corrections_df.iterrows():
        try:
            if int(row.get("is_actually_correct", 0)) == 1:
                season_key = str(row["season"])
                club_query = str(row["club_query"])
                mapped_name = str(row["matched_name"])
                MANUAL_MAP[(season_key, club_query)] = mapped_name
        except KeyError:
            # Skip malformed rows
            continue
else:
    # No corrections file present -> empty mapping
    MANUAL_MAP = {}

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

# Cache for already resolved fuzzy matches to avoid redundant computation
_MATCH_CACHE: dict[tuple[str, str], float | None] = {}
# Records of unsuccessful or uncertain matches for debugging
LOG_RECORDS: list[dict[str, str | float | int | None]] = []


# ---------------------------------------------------------------------------
# Core matching helper
# ---------------------------------------------------------------------------

def _get_uefa_coeff(season: str, club: str, *, threshold: int = 90) -> float | None:
    """Return UEFA coefficient for *club* in *season* using fuzzy matching.

    Parameters
    ----------
    season: str
        Season in the format "YY/YY" (e.g. "24/25").
    club: str
        Club name as written in the transfers file.
    threshold: int, default=90
        Minimum similarity score (0-100) required to accept a fuzzy match.

    Returns
    -------
    float | None
        UEFA coefficient if a reliable match is found, otherwise ``None``.
    """
    key = (season, club)
    if key in _MATCH_CACHE:
        return _MATCH_CACHE[key]

    # 0. Manual override (highest priority)
    manual_target = MANUAL_MAP.get(key)
    if manual_target is not None:
        season_table = uefa_rankings.get(season)
        if season_table and manual_target in season_table:
            coeff = season_table[manual_target]
            _MATCH_CACHE[key] = coeff
            return coeff
        # Manual target unavailable in ranking table -> proceed normally but log
        LOG_RECORDS.append(
            {
                "season": season,
                "club_query": club,
                "reason": "manual_target_missing",
                "matched_name": manual_target,
                "score": None,
                "threshold": threshold,
            }
        )

    season_table = uefa_rankings.get(season)
    if season_table is None:
        # Season not present in ranking file
        LOG_RECORDS.append(
            {
                "season": season,
                "club_query": club,
                "reason": "season_missing",
                "matched_name": None,
                "score": None,
                "threshold": threshold,
            }
        )
        _MATCH_CACHE[key] = None
        return None

    # 1. Direct hit
    if club in season_table:
        coeff = season_table[club]
        _MATCH_CACHE[key] = coeff
        return coeff

    # 2. Fuzzy search among club names of that season
    best_match = process.extractOne(
        club,
        season_table.keys(),
        scorer=fuzz.WRatio,  # Use a weighted ratio for better matching on substrings
    )

    if best_match is None:
        LOG_RECORDS.append(
            {
                "season": season,
                "club_query": club,
                "reason": "no_candidate",
                "matched_name": None,
                "score": None,
                "threshold": threshold,
            }
        )
        _MATCH_CACHE[key] = None
        return None

    matched_name, score, _ = best_match  # type: ignore[assignment]

    if score >= threshold:
        coeff = season_table[matched_name]
        _MATCH_CACHE[key] = coeff
        return coeff

    # Similarity not high enough
    LOG_RECORDS.append(
        {
            "season": season,
            "club_query": club,
            "reason": "below_threshold",
            "matched_name": matched_name,
            "score": score,
            "threshold": threshold,
        }
    )
    _MATCH_CACHE[key] = None
    return None


# ---------------------------------------------------------------------------
# Compute and attach new column
# ---------------------------------------------------------------------------

df["from_club_uefa_coeff"] = df.apply(
    lambda row: _get_uefa_coeff(row["transfer_season"], row["from_club_name"]), axis=1
)

# ---------------------------------------------------------------------------
# Output / persistence
# ---------------------------------------------------------------------------

# For demonstration purposes print a preview. In production you might
# write to a new CSV instead:
print(df.head())

# ---------------------------------------------------------------------------
# Write debug log for fuzzy matching
# ---------------------------------------------------------------------------

if LOG_RECORDS:
    log_df = pd.DataFrame(LOG_RECORDS)
    log_path = Path("fuzzy_match_failures.csv")
    log_df.to_csv(log_path, index=False)
    print(
        f"\n[INFO] Wrote {len(LOG_RECORDS)} fuzzy-match debug records to {log_path.resolve()}"
    )

    # ---------------------------------------------------------------------
    # Identify failures that are not yet reviewed in fuzzy_corrections.csv
    # ---------------------------------------------------------------------

    reviewed_keys: set[tuple[str, str]] = set()
    if corrections_path.exists():
        reviewed_keys = {
            (str(row["season"]), str(row["club_query"])) for _, row in corrections_df.iterrows()
        }

    log_keys = {
        (str(row["season"]), str(row["club_query"])) for _, row in log_df.iterrows()
    }

    new_keys = log_keys - reviewed_keys

    if new_keys:
        new_failures_df = log_df[log_df.apply(
            lambda r: (str(r["season"]), str(r["club_query"])) in new_keys, axis=1
        )]

        new_path = Path("fuzzy_match_new_failures.csv")
        new_failures_df.to_csv(new_path, index=False)
        print(
            f"[INFO] Found {len(new_failures_df)} new fuzzy-match issues not yet in corrections. "
            f"They have been written to {new_path.resolve()}"
        )

# ---------------------------------------------------------------------------
# General matching statistics
# ---------------------------------------------------------------------------

missing_count = df["from_club_uefa_coeff"].isna().sum()
total_count = len(df)
print(
    f"\n[STATS] Missing UEFA coefficients: {missing_count}/{total_count} "
    f"({(missing_count/total_count)*100:.2f}%)"
)
