import json
from typing import Any

import curl_cffi as requests
import pandas as pd

#


def tsssy(transfer_season: str) -> str:
    # transfer_season is like "24/25"
    # We want to extract the second part ("25") and return as 2025
    try:
        year = transfer_season.split("/")[1]
        # Assume all years are in 2000s
        return "20" + year
    except (IndexError, ValueError):
        raise ValueError(f"Invalid transfer_season format: {transfer_season}")


df = pd.read_csv("transfers.csv")

transfer_seasons = set(df["transfer_season"])


def ptsorna(overall_ranking: dict[str, str | int]) -> float:
    pts = overall_ranking.get("totalPoints", 0)
    na = overall_ranking.get("nationalAssociationPoints", 0)

    return max(pts, na)


def build_ts_rankings(transfer_seasons: set[str]) -> dict[str, dict[str, float]]:
    def get_sy_coeffs(sy: str) -> dict[Any, Any]:
        members = {}
        for page in range(1, 12):
            url = f"https://comp.uefa.com/v2/coefficients?coefficientRange=OVERALL&coefficientType=MEN_CLUB_TEN_YEARS&language=EN&page={page}&pagesize=50&seasonYear={sy}"
            response = requests.get(url)
            data = response.json()
            ue_members = data["data"]["members"]

            for member in ue_members:
                member_pts = ptsorna(member["overallRanking"])
                members[member["member"]["displayNameShort"]] = member_pts

        return members

    return {ts: get_sy_coeffs(tsssy(ts)) for ts in transfer_seasons}


ts_rankings = build_ts_rankings(transfer_seasons)


with open("ts_rankings.json", "w", encoding="utf-8") as f:
    json.dump(ts_rankings, f, ensure_ascii=False, indent=2)
