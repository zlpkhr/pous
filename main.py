import pandas as pd

df = pd.read_csv('clean.csv')

blank_stats = {}
blank_player_info = {}

for col in df.columns:
    # Find rows where value is NaN or empty string
    is_blank = df[col].isna() | (df[col] == '')
    num_blank = is_blank.sum()
    if num_blank > 0:
        blank_stats[col] = num_blank
        # Store player_ids and names for rows with blank in this column
        blank_player_info[col] = list(
            zip(
                df.loc[is_blank, 'player_id'].tolist(),
                df.loc[is_blank, 'name'].tolist()
            )
        )

if blank_stats:
    print("Columns with at least one blank value:\n")
    for col, count in blank_stats.items():
        print(f"Column: {col}")
        print(f"  Number of blank values: {count}")
        print(f"  Players with blank values in this column:")
        for pid, name in blank_player_info[col]:
            print(f"    - player_id: {pid}, name: {name}")
        print("-" * 40)
else:
    print("No columns with blank values found.")
