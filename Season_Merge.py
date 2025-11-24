import pandas as pd
import os

# Paths
output_folder = "Output/Games"
season_folder = "Output/Season"

# Make sure season folder exists
os.makedirs(season_folder, exist_ok=True)

# Choose two games to merge
games_to_merge = [ "ALBERTUS_WBB", "AMHERST_WBB", "ANNA_MARIA_WBB", "COLBY_SAWYER_WBB", "Dean", "Emerson", "Emmanuel",
  "EMMANUEL_WBB", "Fitchburg State", "Gordon", "JWU_PROVIDENCE_WBB", "JWU_PROVIDENCE_WBB2",
  "LASELL_WBB", "LASELL_WBB2", "MITCHELL_WBB", "NAZARETH", "NEC_WBB", "REGIS_WBB",
  "RIVIER", "Salem State", "ST_JOSEPH_S(ME)_WBB", "USJ CT", "VSU Lyndon", "WBB NORWICH AT ELMS 2024-25",
  "Wellesley", "Wentworth", "Westfield", "WPI" ]


# ---- 1. Player Plus-Minus ----
plus_minus_files = [os.path.join(output_folder, f"{game}_plus_minus.csv") for game in games_to_merge]
plus_minus_dfs = [pd.read_csv(file) for file in plus_minus_files]
season_plus_minus_df = pd.concat(plus_minus_dfs, ignore_index=True)
season_plus_minus_df.to_csv(os.path.join(season_folder, "season_plus_minus.csv"), index=False)
print("✅ Merged player plus-minus for selected games.")

# Season total plus-minus
season_total_df = season_plus_minus_df.groupby("Player", as_index=False)["Plus/Minus"].sum()
season_total_df = season_total_df.sort_values("Plus/Minus", ascending=False)
season_total_df.to_csv(os.path.join(season_folder, "season_plus_minus_totals.csv"), index=False)
print("✅ Created season total player plus-minus file.")

# ---- 2. Boxscore ----
boxscore_files = [os.path.join(output_folder, f"{game}_boxscore.csv") for game in games_to_merge]
boxscore_dfs = [pd.read_csv(file) for file in boxscore_files]
season_boxscore_df = pd.concat(boxscore_dfs, ignore_index=True)
season_boxscore_df.to_csv(os.path.join(season_folder, "season_boxscore.csv"), index=False)
print("✅ Merged boxscores for selected games.")

# ---- 3. Four Factors Summary ----
four_factors_files = [os.path.join(output_folder, f"{game}_four_factors_summary.csv") for game in games_to_merge]
four_factors_dfs = [pd.read_csv(file) for file in four_factors_files]
season_four_factors_df = pd.concat(four_factors_dfs, ignore_index=True)
season_four_factors_df.to_csv(os.path.join(season_folder, "season_four_factors_summary.csv"), index=False)
print("✅ Merged four factors summaries for selected games.")

# ---- 4. Lineup Plus-Minus ----
lineup_pm_files = [os.path.join(output_folder, f"{game}_lineup_pm.csv") for game in games_to_merge]
lineup_pm_dfs = [pd.read_csv(file) for file in lineup_pm_files]
season_lineup_pm_df = pd.concat(lineup_pm_dfs, ignore_index=True)
season_lineup_pm_df.to_csv(os.path.join(season_folder, "season_lineup_pm.csv"), index=False)
print("✅ Merged lineup plus-minus for selected games.")

def sum_total_time(series):
    total_seconds = 0
    for time_str in series:
        try:
            parts = time_str.strip().split(":")
            if len(parts) >= 2:
                # Only use the last two parts as MM:SS
                minutes, seconds = map(int, parts[-2:])
                total_seconds += minutes * 60 + seconds
        except:
            continue
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02d}:{seconds:02d}"

# Season total lineup plus-minus with total time and game appearances
season_lineup_totals_df = season_lineup_pm_df.groupby("Lineup").agg({
    "Plus/Minus": "sum",
    "Total Time": sum_total_time,
    "Game": lambda games: ", ".join(sorted(set(games)))
}).reset_index()

season_lineup_totals_df = season_lineup_totals_df.sort_values("Plus/Minus", ascending=False)
season_lineup_totals_df.to_csv(os.path.join(season_folder, "season_lineup_pm_totals.csv"), index=False)
print("✅ Created season total lineup plus-minus file with total time and game appearances.")

# ---- 5. Merged Lineups ----
merged_lineups_files = [os.path.join(output_folder, f"{game}_merged_lineups.csv") for game in games_to_merge]
merged_lineups_dfs = [pd.read_csv(file) for file in merged_lineups_files]
season_merged_lineups_df = pd.concat(merged_lineups_dfs, ignore_index=True)
season_merged_lineups_df.to_csv(os.path.join(season_folder, "season_merged_lineups.csv"), index=False)
print("✅ Merged merged lineups for selected games.")

# ---- 6. Two-Player Combinations ----
two_player_files = [os.path.join(output_folder, f"{game}_two_player_combinations.csv") for game in games_to_merge]
two_player_dfs = [pd.read_csv(file) for file in two_player_files]
season_two_player_df = pd.concat(two_player_dfs, ignore_index=True)
season_two_player_df.to_csv(os.path.join(season_folder, "season_two_player_combinations.csv"), index=False)
print("✅ Merged two-player combinations for selected games.")

# Season total two-player plus-minus
season_two_player_totals_df = season_two_player_df.groupby(["Player 1", "Player 2"], as_index=False)["Plus/Minus"].sum()
season_two_player_totals_df = season_two_player_totals_df.sort_values("Plus/Minus", ascending=False)
season_two_player_totals_df.to_csv(os.path.join(season_folder, "season_two_player_totals.csv"), index=False)
print("✅ Created season total two-player combinations file.")

# ---- SEASON TOTAL MERGED LINEUPS ----
def sum_time_column(series):
    total_seconds = 0
    for t in series:
        try:
            parts = t.strip().split(":")
            if len(parts) == 2:
                minutes, seconds = map(int, parts)
            elif len(parts) == 3:
                hours, minutes, seconds = map(int, parts)
                minutes += hours * 60
            else:
                continue
            total_seconds += minutes * 60 + seconds
        except:
            continue

    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02d}:{seconds:02d}"

season_merged_lineups_totals_df = season_merged_lineups_df.groupby("Lineup", as_index=False).agg({
    "Plus/Minus Per 25 Minutes": "sum",
    "Plus/Minus Per Minute": "sum",
    "Total Time": sum_time_column
})

season_merged_lineups_totals_df = season_merged_lineups_totals_df.sort_values("Plus/Minus Per 25 Minutes", ascending=False)
season_merged_lineups_totals_df.to_csv(os.path.join(season_folder, "season_merged_lineups_totals.csv"), index=False)
print("✅ Created season total merged lineups file.")

# ---- SEASON AVERAGE BOXSCORE ----
season_boxscore_df_numeric = season_boxscore_df.copy()

for col in ["FGM", "FGA", "3PM", "3PA", "FTM", "FTA", "OREB", "DREB", "REB", "AST", "STL", "BLK", "TO", "PF", "PTS", "MIN"]:
    season_boxscore_df_numeric[col] = pd.to_numeric(season_boxscore_df_numeric[col], errors="coerce").fillna(0)

season_boxscore_totals = season_boxscore_df_numeric.groupby(["Player", "Team"], as_index=False).sum()

season_boxscore_totals["FG%"] = (season_boxscore_totals["FGM"] / season_boxscore_totals["FGA"] * 100).round(2)
season_boxscore_totals["3P%"] = (season_boxscore_totals["3PM"] / season_boxscore_totals["3PA"] * 100).round(2)
season_boxscore_totals["FT%"] = (season_boxscore_totals["FTM"] / season_boxscore_totals["FTA"] * 100).round(2)

ordered_cols = [
    "Team", "Player", "MIN", "FGM", "FGA", "FG%", "3PM", "3PA", "3P%", "FTM", "FTA", "FT%", 
    "OREB", "DREB", "REB", "AST", "STL", "BLK", "TO", "PF", "PTS"
]
season_boxscore_totals = season_boxscore_totals[ordered_cols]

season_boxscore_totals.to_csv(os.path.join(season_folder, "season_boxscore_totals.csv"), index=False)
print("✅ Created season total boxscore file.")

# ---- SEASON AVERAGE FOUR FACTORS ----
# Clean up player names to prevent duplicates caused by extra spaces or casing
season_four_factors_df["Player"] = season_four_factors_df["Player"].str.strip().str.upper()

# Group by cleaned names and average
from thefuzz import process

# ---- SEASON AVERAGE FOUR FACTORS (CLEANED) ----

# Step 0: Official Elms player list
player_names = ["SMITH,HEAVEN", "GUERRIER,PHONIA", "PACHECO,MIA", "TURCO,MARY", "WASIEWICZ,GABBY",
                            "LEWIS,JADE","URIBE,TALIA","GORSKI,JENNY","BARRON,SHEA","LEBEL,KELLY","ASFAW,SOLIYANA",
                            "JOHNSTON,RAHMIA","GRAHAM,PIPER","ANDRADE,SOPHIA","MILDNER,STEPHANIE"]

# Step 1: Normalize player names in the DataFrame
season_four_factors_df["Player"] = season_four_factors_df["Player"].str.strip().str.upper()

# Step 2: Fuzzy match each player to the official list
def match_to_roster(name, roster):
    match, score = process.extractOne(name, roster)
    return match if score >= 80 else None

season_four_factors_df["Matched Player"] = season_four_factors_df["Player"].apply(
    lambda name: match_to_roster(name, player_names)
)

# Step 3: Drop unmatched (non-Elms) players
season_four_factors_df = season_four_factors_df.dropna(subset=["Matched Player"])

# Step 4: Group by matched player name and average stats
season_four_factors_averages_df = (
    season_four_factors_df
    .groupby("Matched Player", as_index=False)[["OREB%", "TOV%", "EFG%", "FTR"]]
    .mean()
    .round(2)
)

# Step 5: Rename column to "Player"
season_four_factors_averages_df.rename(columns={"Matched Player": "Player"}, inplace=True)

# Step 6: Save the output
season_four_factors_averages_df.to_csv(os.path.join(season_folder, "season_four_factors_averages.csv"), index=False)
print("✅ Created cleaned season average four factors summary using official player list.")
from shiny import App, ui, render
import pandas as pd
import os


