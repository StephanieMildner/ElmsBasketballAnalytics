import pandas as pd
import xml.etree.ElementTree as ET
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
pd.set_option('display.width', 200)
pd.set_option('display.max_colwidth', 50)

def parse_xml_to_df(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()

    plays_data = []
    for play in root.findall(".//play"):
        play_info = {
            "team": play.get("team"),
            "player": play.get("checkname"),
            "action": play.get("action"),
            "type": play.get("type", ""),
            "time": play.get("time"),
            "score_v": play.get("vscore", ""),
            "score_h": play.get("hscore", "")
        }
        plays_data.append(play_info)

    df = pd.DataFrame(plays_data)

    # Convert scores to numeric
    df['score_v'] = pd.to_numeric(df['score_v'], errors='coerce').ffill().fillna(0).astype(int)
    df['score_h'] = pd.to_numeric(df['score_h'], errors='coerce').ffill().fillna(0).astype(int)

    # Calculate lead
    venue = root.find(".//venue")
    homename = venue.get("homename")

    if "elm" in homename.lower():
        df['lead'] = df['score_h'] - df['score_v']
    else:
        df['lead'] = df['score_v'] - df['score_h']

    return df, root


from thefuzz import process

def match_player_names(df, player_names):
    for column in ['player']:
        for index, row in df.iterrows():
            closest_match = process.extractOne(str(row[column]), player_names, scorer=process.fuzz.token_sort_ratio)
            if closest_match and closest_match[1] >= 70:
                df.loc[index, column] = closest_match[0]
    return df


def find_starters(df, player_names):
    starters = []
    starter_count = 0  # Initialize a counter for starters

    for player in player_names:
        player_df = df[df['player'].str.contains(player, case=False, na=False)]
        if not player_df.empty:
            first_action = player_df['action'].iloc[0]
            first_type = player_df['type'].iloc[0]
            if not ("sub" in str(first_action).lower() and "in" in str(first_type).lower()):
                starters.append(player)
                starter_count += 1  # Increment starter count
                if starter_count == 5:  # Break if we've found 5 starters
                    break

    print("✅ Starters identified:", starters)
    return starters



def update_lineup(df, player_names, starters):
    from thefuzz import process
    current_lineup = set(starters)
    df['lineup'] = ''

    for index, row in df.iterrows():
        df.loc[index, 'lineup'] = str(list(current_lineup))
        if "sub" in str(row['action']).lower():
            if "in" in str(row['type']).lower():
                closest_match = process.extractOne(str(row['player']), player_names, scorer=process.fuzz.token_set_ratio)
                if closest_match and closest_match[1] >= 80:
                    current_lineup.add(closest_match[0])
            elif "out" in str(row['type']).lower():
                closest_match = process.extractOne(str(row['player']), player_names, scorer=process.fuzz.token_set_ratio)
                if closest_match and closest_match[1] >= 80:
                    current_lineup.discard(closest_match[0])
    return df


def calculate_plus_minus(df):
    plus_minus_data = []
    player_stints = {}

    for index, row in df.iterrows():
        current_lineup = eval(row['lineup'])
        previous_lead = df.loc[index - 1, 'lead'] if index > 0 else 0
        lead_change = row['lead'] - previous_lead
        for player in current_lineup:
            player_stints[player] = player_stints.get(player, 0) + lead_change

    for player, plus_minus in player_stints.items():
        plus_minus_data.append({'Player': player, 'Plus/Minus': plus_minus})

    return pd.DataFrame(plus_minus_data)


def generate_lineup_plus_minus(df):
    """
    Calculates plus-minus and total time for each unique 5-player lineup.
    Returns a DataFrame with Lineup, Plus/Minus, and Total Time.
    """
    from collections import defaultdict

    lineup_data = defaultdict(lambda: {"plus_minus": 0, "total_seconds": 0})
    current_lineup = None
    start_time = None
    start_lead = None
    previous_seconds = None
    start_half = '1st Half'

    def time_to_seconds(time_str):
        minutes, seconds = map(int, time_str.split(':'))
        return minutes * 60 + seconds

    def calculate_time_diff_seconds(start, end):
        return abs(time_to_seconds(end) - time_to_seconds(start))

    for index, row in df.iterrows():
        lineup = tuple(sorted(eval(row['lineup'])))
        if len(lineup) != 5:
            continue

        minutes, seconds = map(int, row['time'].split(':'))
        current_seconds = minutes * 60 + seconds

        # Detect half switch (clock reset)
        if previous_seconds is not None and current_seconds > previous_seconds:
            start_half = '2nd Half'

        previous_seconds = current_seconds

        if lineup != current_lineup:
            if current_lineup:
                end_time = row['time']
                plus_minus = row['lead'] - start_lead
                time_spent = calculate_time_diff_seconds(start_time, end_time)

                lineup_data[current_lineup]["plus_minus"] += plus_minus
                lineup_data[current_lineup]["total_seconds"] += time_spent

            current_lineup = lineup
            start_time = row['time']
            start_lead = row['lead']

    # Final stint
    if current_lineup:
        end_time = df['time'].iloc[-1]
        plus_minus = df['lead'].iloc[-1] - start_lead
        time_spent = calculate_time_diff_seconds(start_time, end_time)

        lineup_data[current_lineup]["plus_minus"] += plus_minus
        lineup_data[current_lineup]["total_seconds"] += time_spent

    # Build output DataFrame
    output_rows = []
    for lineup, data in lineup_data.items():
        minutes = data["total_seconds"] // 60
        seconds = data["total_seconds"] % 60
        time_str = f"{minutes:02d}:{seconds:02d}"
        output_rows.append({
            "Lineup": lineup,
            "Plus/Minus": data["plus_minus"],
            "Total Time": time_str
        })

    return pd.DataFrame(output_rows)


def calculate_time_difference(start_time, end_time):
    start_minutes, start_seconds = map(int, start_time.split(':'))
    end_minutes, end_seconds = map(int, end_time.split(':'))
    start_total_seconds = start_minutes * 60 + start_seconds
    end_total_seconds = end_minutes * 60 + end_seconds
    time_diff_seconds = end_total_seconds - start_total_seconds
    minutes = abs(time_diff_seconds) // 60
    seconds = abs(time_diff_seconds) % 60
    return f"{minutes:02d}:{seconds:02d}"

def generate_lineup_instances(df):
    lineup_instances = []
    current_lineup = None
    start_time = None
    start_lead = None
    start_half = '1st Half'  # Start assuming 1st Half
    previous_seconds = None

    for index, row in df.iterrows():
        lineup = tuple(eval(row['lineup']))
        if len(lineup) == 5:
            # Calculate current time in seconds
            minutes, seconds = map(int, row['time'].split(':'))
            current_seconds = minutes * 60 + seconds

            # Detect if clock reset (start of second half)
            if previous_seconds is not None and current_seconds > previous_seconds:
                start_half = '2nd Half'

            previous_seconds = current_seconds  # Update for next loop

            if lineup != current_lineup:
                if current_lineup:
                    end_time = row['time']
                    plus_minus = row['lead'] - start_lead
                    total_time = calculate_time_difference(start_time, end_time)
                    lineup_instances.append([current_lineup, start_time, end_time, plus_minus, total_time, start_half])
                current_lineup = lineup
                start_time = row['time']
                start_lead = row['lead']

    # Save the last stint
    if current_lineup:
        end_time = df['time'].iloc[-1]
        plus_minus = df['lead'].iloc[-1] - start_lead
        total_time = calculate_time_difference(start_time, end_time)
        lineup_instances.append([current_lineup, start_time, end_time, plus_minus, total_time, start_half])

    return pd.DataFrame(lineup_instances, columns=['Lineup', 'Start Time', 'End Time', 'Plus/Minus', 'Total Time', 'Half'])


def calculate_metrics(lineup_instances_df):
    """
    Calculates plus-minus per minute and per 25 minutes for each 5-player lineup instance.
    """

    # Helper to convert 'MM:SS' format to total minutes as float
    def time_to_minutes(time_str):
        minutes, seconds = map(int, time_str.split(':'))
        return minutes + seconds / 60

    # 1. Convert Total Time to Minutes
    lineup_instances_df['Total Time (Minutes)'] = lineup_instances_df['Total Time'].apply(time_to_minutes)

    # 2. Calculate Plus-Minus Per Minute
    lineup_instances_df['Plus/Minus Per Minute'] = (lineup_instances_df['Plus/Minus'] / lineup_instances_df['Total Time (Minutes)']).round(2)

    # 3. Calculate Plus-Minus Per 25 Minutes
    lineup_instances_df['Plus/Minus Per 25 Minutes'] = (lineup_instances_df['Plus/Minus Per Minute'] * 25).round(2)

    # 4. Return Final Clean DataFrame
    return lineup_instances_df[['Lineup', 'Plus/Minus Per 25 Minutes', 'Plus/Minus Per Minute', 'Total Time']]

import pandas as pd

def merge_lineups(result_df):
    """
    Merges duplicate lineups in result_df by:
    - Adding Plus/Minus Per Minute
    - Adding Plus/Minus Per 25 Minutes
    - Summing Total Time correctly
    """

    merged_lineups = {}

    for _, row in result_df.iterrows():
        # Force Lineup into a sorted tuple to ensure consistent matching
        lineup = tuple(sorted(row['Lineup']))

        if lineup not in merged_lineups:
            merged_lineups[lineup] = {
                'Plus/Minus Per 25 Minutes': 0,
                'Plus/Minus Per Minute': 0,
                'Total Seconds': 0  # Track total time cleanly
            }

        # Add Plus/Minus values
        merged_lineups[lineup]['Plus/Minus Per 25 Minutes'] += row['Plus/Minus Per 25 Minutes']
        merged_lineups[lineup]['Plus/Minus Per Minute'] += row['Plus/Minus Per Minute']

        # Convert Total Time to seconds and add
        minutes, seconds = map(int, row['Total Time'].split(":"))
        total_seconds = minutes * 60 + seconds
        merged_lineups[lineup]['Total Seconds'] += total_seconds

    # Now build a clean DataFrame
    merged_rows = []
    for lineup, metrics in merged_lineups.items():
        minutes = metrics['Total Seconds'] // 60
        seconds = metrics['Total Seconds'] % 60
        total_time_str = f"{minutes:02d}:{seconds:02d}"

        merged_rows.append({
            'Lineup': lineup,
            'Plus/Minus Per 25 Minutes': round(metrics['Plus/Minus Per 25 Minutes'], 2),
            'Plus/Minus Per Minute': round(metrics['Plus/Minus Per Minute'], 2),
            'Total Time': total_time_str
        })

    merged_df = pd.DataFrame(merged_rows)

    return merged_df
import pandas as pd
from itertools import combinations

def calculate_plus_minus_combinations(lineup_pm_df):
    """
    Calculates plus-minus for all two-player combinations from a lineup plus-minus DataFrame.
    """
    two_player_combinations = {}
    
    for _, row in lineup_pm_df.iterrows():
        lineup = row['Lineup']
        plus_minus = row['Plus/Minus']
        
        # Ensure lineup is a list
        if isinstance(lineup, str):
            import ast
            try:
                lineup = ast.literal_eval(lineup)
            except:
                continue

        for combo in combinations(lineup, 2):  # Generate all 2-player combinations
            combo = tuple(sorted(combo))  # Ensure consistent order
            if combo not in two_player_combinations:
                two_player_combinations[combo] = 0
            two_player_combinations[combo] += plus_minus
    
    # Convert to DataFrame
    combinations_df = pd.DataFrame([(p1, p2, pm) for (p1, p2), pm in two_player_combinations.items()],
    columns=['Player 1', 'Player 2', 'Plus/Minus']
)

    
    return combinations_df



def generate_boxscore_from_xml(file_path):
    """Parses an XML file and generates the player-level boxscore DataFrame."""
    tree = ET.parse(file_path)
    root = tree.getroot()

    player_stats_data = []

    for team in root.findall(".//team"):
        for player in team.findall(".//player"):
            stats = player.find(".//stats")
            if stats is not None:
                player_stats_data.append({
                    "Team": team.get("name"),
                    "Player": player.get("name"),
                    "No.": player.get("uni"),
                    "MIN": stats.get("min"),
                    "FGM": stats.get("fgm"),
                    "FGA": stats.get("fga"),
                    "FG%": stats.get("fgpct"),
                    "3PM": stats.get("fgm3"),
                    "3PA": stats.get("fga3"),
                    "3P%": stats.get("fg3pct"),
                    "FTM": stats.get("ftm"),
                    "FTA": stats.get("fta"),
                    "FT%": stats.get("ftpct"),
                    "OREB": stats.get("oreb"),
                    "DREB": stats.get("dreb"),
                    "REB": stats.get("treb"),
                    "AST": stats.get("ast"),
                    "STL": stats.get("stl"),
                    "BLK": stats.get("blk"),
                    "TO": stats.get("to"),
                    "PF": stats.get("pf"),
                    "PTS": stats.get("tp"),
                })

    boxscore_df = pd.DataFrame(player_stats_data)

    boxscore_df = boxscore_df[[
        "Team", "No.", "Player", "MIN", "FGM", "FGA", "FG%", "3PM", "3PA", "3P%",
        "FTM", "FTA", "FT%", "OREB", "DREB", "REB", "AST", "STL", "BLK", "TO", "PF", "PTS"
    ]]

    return boxscore_df

def generate_team_stats_from_xml(file_path):
    """Parses an XML file and generates the team-level totals DataFrame."""
    tree = ET.parse(file_path)
    root = tree.getroot()

    team_stats_data = []

    for team_element in root.findall(".//team"):
        team_name = team_element.get("name")
        team_data = {
            "Team": team_name,
            "MIN": 0, "FGM": 0, "FGA": 0, "3PM": 0, "3PA": 0, "FTM": 0, "FTA": 0,
            "OREB": 0, "DREB": 0, "REB": 0, "AST": 0, "STL": 0, "BLK": 0,
            "TO": 0, "PF": 0, "PTS": 0
        }

        for player in team_element.findall(".//player"):
            stats = player.find(".//stats")
            if stats is not None:
                team_data["MIN"] += int(stats.get("min", 0)) if stats.get("min") else 0
                team_data["FGM"] += int(stats.get("fgm", 0)) if stats.get("fgm") else 0
                team_data["FGA"] += int(stats.get("fga", 0)) if stats.get("fga") else 0
                team_data["3PM"] += int(stats.get("fgm3", 0)) if stats.get("fgm3") else 0
                team_data["3PA"] += int(stats.get("fga3", 0)) if stats.get("fga3") else 0
                team_data["FTM"] += int(stats.get("ftm", 0)) if stats.get("ftm") else 0
                team_data["FTA"] += int(stats.get("fta", 0)) if stats.get("fta") else 0
                team_data["OREB"] += int(stats.get("oreb", 0)) if stats.get("oreb") else 0
                team_data["DREB"] += int(stats.get("dreb", 0)) if stats.get("dreb") else 0
                team_data["REB"] += int(stats.get("treb", 0)) if stats.get("treb") else 0
                team_data["AST"] += int(stats.get("ast", 0)) if stats.get("ast") else 0
                team_data["STL"] += int(stats.get("stl", 0)) if stats.get("stl") else 0
                team_data["BLK"] += int(stats.get("blk", 0)) if stats.get("blk") else 0
                team_data["TO"] += int(stats.get("to", 0)) if stats.get("to") else 0
                team_data["PF"] += int(stats.get("pf", 0)) if stats.get("pf") else 0
                team_data["PTS"] += int(stats.get("tp", 0)) if stats.get("tp") else 0

        # Calculate team shooting percentages
        team_data["FG%"] = round((team_data["FGM"] / team_data["FGA"]) * 100, 2) if team_data["FGA"] != 0 else 0
        team_data["3P%"] = round((team_data["3PM"] / team_data["3PA"]) * 100, 2) if team_data["3PA"] != 0 else 0
        team_data["FT%"] = round((team_data["FTM"] / team_data["FTA"]) * 100, 2) if team_data["FTA"] != 0 else 0

        team_stats_data.append(team_data)

    team_stats_df = pd.DataFrame(team_stats_data)

    team_stats_df = team_stats_df[[
        "Team", "MIN", "FGM", "FGA", "FG%", "3PM", "3PA", "3P%", "FTM", "FTA", "FT%",
        "OREB", "DREB", "REB", "AST", "STL", "BLK", "TO", "PF", "PTS"
    ]]

    return team_stats_df


def calculate_oreb_rate(df, team_stats_df):
    """Calculates the Offensive Rebound Rate (OREB%) for players/teams."""

    def get_opponent_dreb(row):
        current_team = row['Team']
        opponent_team = [team for team in team_stats_df['Team'] if team != current_team]
        if opponent_team:
            opponent_dreb = team_stats_df[team_stats_df['Team'] == opponent_team[0]]['DREB'].iloc[0]
            return float(opponent_dreb)
        return 0

    df['Opponent DREB'] = df.apply(get_opponent_dreb, axis=1)

    # Calculate OREB%
    df['OREB'] = pd.to_numeric(df['OREB'], errors='coerce').fillna(0)
    df['OREB%'] = (df['OREB'] / (df['OREB'] + df['Opponent DREB']) * 100).round(2)

    df = df.drop('Opponent DREB', axis=1)
    return df

def calculate_tov_rate(df):
    """Calculates the Turnover Rate (TOV%)."""
    
    df['TO'] = pd.to_numeric(df['TO'], errors='coerce').fillna(0)
    df['FGA'] = pd.to_numeric(df['FGA'], errors='coerce').fillna(0)
    df['FTA'] = pd.to_numeric(df['FTA'], errors='coerce').fillna(0)

    df['TOV%'] = (df['TO'] / (df['FGA'] + 0.44 * df['FTA'] + df['TO']) * 100).round(2)
    return df

def calculate_efg_percentage(df):
    """Calculates Effective Field Goal Percentage (EFG%)."""
    
    df['FGM'] = pd.to_numeric(df['FGM'], errors='coerce').fillna(0)
    df['3PM'] = pd.to_numeric(df['3PM'], errors='coerce').fillna(0)
    df['FGA'] = pd.to_numeric(df['FGA'], errors='coerce').fillna(0)

    df['EFG%'] = (((df['FGM'] + 0.5 * df['3PM']) / df['FGA']) * 100).round(2)
    return df

def calculate_ftr(df):
    """Calculates Free Throw Rate (FTR)."""

    df['FTA'] = pd.to_numeric(df['FTA'], errors='coerce').fillna(0)
    df['FGA'] = pd.to_numeric(df['FGA'], errors='coerce').fillna(0)

    df['FTR'] = (df['FTA'] / df['FGA'] * 100).round(2)
    return df

def create_four_factors_summary(final_boxscore_df):
    """
    Creates a Four Factors summary DataFrame:
    - Only includes Elms players (case-insensitive match)
    - Drops any players with missing Four Factors
    - No rankings included
    """

    # Step 1: Filter for Elms players (case insensitive)
    elms_df = final_boxscore_df[final_boxscore_df['Team'].str.contains('elms', case=False, na=False)].copy()

    # Step 2: Select only Player and Four Factors
    four_factors_summary_df = elms_df[['Player', 'OREB%', 'TOV%', 'EFG%', 'FTR']].copy()

    # Step 3: Drop any rows where Four Factors are missing
    four_factors_summary_df = four_factors_summary_df.dropna(subset=['OREB%', 'TOV%', 'EFG%', 'FTR'])

    return four_factors_summary_df





# Path to your XML file
# 
import os
print(os.getcwd())

if __name__ == "__main__":
    folder_path = "Games/"  # Folder containing XML files
    output_folder = "Output/Games/"  # Folder to save CSVs

    os.makedirs(output_folder, exist_ok=True)

    for filename in os.listdir(folder_path):
        if filename.endswith(".xml") or filename.endswith(".XML"):
            file_path = os.path.join(folder_path, filename)
            base_name = os.path.splitext(filename)[0]  # filename without .xml

            # 1. Parse XML
            df, root = parse_xml_to_df(file_path)

            # 2. Define player names (this could eventually be smarter, but use static list for now)
            player_names = ["SMITH,HEAVEN", "GUERRIER,PHONIA", "PACHECO,MIA", "TURCO,MARY", "WASIEWICZ,GABBY",
                            "LEWIS,JADE","URIBE,TALIA","GORSKI,JENNY","BARRON,SHEA","LEBEL,KELLY","ASFAW,SOLIYANA",
                            "JOHNSTON,RAHMIA","GRAHAM,PIPER","ANDRADE,SOPHIA","MILDNER,STEPHANIE"]

            # 3. Process
            df = match_player_names(df, player_names)
            starters = find_starters(df, player_names)
            df = update_lineup(df, player_names, starters)

            plus_minus_df = calculate_plus_minus(df)
            lineup_pm_df = generate_lineup_plus_minus(df)
            lineup_instances_df = generate_lineup_instances(df)
            result_df = calculate_metrics(lineup_instances_df)
            merged_results_df = merge_lineups(result_df)
            combinations_df = calculate_plus_minus_combinations(lineup_pm_df)

            final_boxscore_df = generate_boxscore_from_xml(file_path)
            team_stats_df = generate_team_stats_from_xml(file_path)

            final_boxscore_df = calculate_oreb_rate(final_boxscore_df, team_stats_df)
            final_boxscore_df = calculate_tov_rate(final_boxscore_df)
            final_boxscore_df = calculate_efg_percentage(final_boxscore_df)
            final_boxscore_df = calculate_ftr(final_boxscore_df)

            four_factors_summary_df = create_four_factors_summary(final_boxscore_df)

            game_name = base_name  # Extracted from filename (Dean, Anna_Maria, etc.)

# Add "Game" column to each relevant DataFrame
            plus_minus_df["Game"] = game_name
            lineup_pm_df["Game"] = game_name
            lineup_instances_df["Game"] = game_name
            result_df["Game"] = game_name
            merged_results_df["Game"] = game_name
            combinations_df["Game"] = game_name
            final_boxscore_df["Game"] = game_name
            four_factors_summary_df["Game"] = game_name


            # 4. Save all outputs
            plus_minus_df.to_csv(os.path.join(output_folder, f"{base_name}_plus_minus.csv"), index=False)
            lineup_pm_df.to_csv(os.path.join(output_folder, f"{base_name}_lineup_pm.csv"), index=False)
            lineup_instances_df.to_csv(os.path.join(output_folder, f"{base_name}_lineup_instances.csv"), index=False)
            result_df.to_csv(os.path.join(output_folder, f"{base_name}_result_metrics.csv"), index=False)
            merged_results_df.to_csv(os.path.join(output_folder, f"{base_name}_merged_lineups.csv"), index=False)
            combinations_df.to_csv(os.path.join(output_folder, f"{base_name}_two_player_combinations.csv"), index=False)
            final_boxscore_df.to_csv(os.path.join(output_folder, f"{base_name}_boxscore.csv"), index=False)
            four_factors_summary_df.to_csv(os.path.join(output_folder, f"{base_name}_four_factors_summary.csv"), index=False)

            print(f"✅ Finished processing {filename}")
