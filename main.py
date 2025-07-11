import pandas as pd 

tdf = pd.read_csv('transfers.csv')
pdf = pd.read_csv('players.csv')

# Map the 'foot' column from pdf to tdf using 'player_id'
foot_map = pdf.set_index('player_id')['foot']

# Create a new Series in tdf for 'foot'
tdf['foot'] = tdf['player_id'].map(foot_map)

# Define functions to set plays_left_foot and plays_right_foot
def left_foot_val(foot):
    if pd.isna(foot):
        return ''
    return 1 if foot in ['left', 'both'] else 0

def right_foot_val(foot):
    if pd.isna(foot):
        return ''
    return 1 if foot in ['right', 'both'] else 0

tdf['plays_left_foot'] = tdf['foot'].apply(left_foot_val)
tdf['plays_right_foot'] = tdf['foot'].apply(right_foot_val)

# Drop the helper 'foot' column
tdf.drop(columns=['foot'], inplace=True)

# Save the updated DataFrame back to transfers.csv
tdf.to_csv('transfers.csv', index=False)
