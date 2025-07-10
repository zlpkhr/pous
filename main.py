import pandas as pd

mogul_owned_clubs = [
    "Arsenal",
    "Aston Villa",
    "Blackburn",
    "Chelsea",
    "Everton",
    "Fulham",
    "Liverpool",
    "Man City",
    "Man Utd",
    "Newcastle",
    "Tottenham",
    "West Ham",
]


df = pd.read_csv("transfers.csv")

df.columns = df.columns.str.strip()

df["is_owner_mogul"] = df["to_club_name"].isin(mogul_owned_clubs).astype(int)

df.to_csv("transfers.csv", index=False)
