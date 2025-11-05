import pandas as pd
import os
from shiny import App, ui, render, reactive, req
from thefuzz import fuzz
from matplotlib import pyplot as plt
import numpy as np


# Paths
games_folder = "Output/Games"
season_folder = "Output/Season"


# Game labels and player list
game_labels = sorted([
  "ALBERTUS_WBB", "AMHERST_WBB", "ANNA_MARIA_WBB", "COLBY_SAWYER_WBB", "Dean", "Emerson", "Emmanuel",
  "EMMANUEL_WBB", "Fitchburg State", "Gordon", "JWU_PROVIDENCE_WBB", "JWU_PROVIDENCE_WBB2",
  "LASELL_WBB", "LASELL_WBB2", "MITCHELL_WBB", "NAZARETH", "NEC_WBB", "REGIS_BB",
  "RIVIER", "Salem State", "ST_JOSEPH_S(ME)_WBB", "USJ CT", "VSU Lyndon", "WBB NORWICH AT ELMS 2024-25",
  "Wellesley", "Wentworth", "Westfield", "WPI"
])


player_names = [
  "SMITH,HEAVEN", "GUERRIER,PHONIA", "PACHECO,MIA", "TURCO,MARY", "WASIEWICZ,GABBY", "LEWIS,JADE","URIBE,TALIA","GORSKI,JENNY","BARRON,SHEA","LEBEL,KELLY","ASFAW,SOLIYANA","JOHNSTON,RAHMIA","GRAHAM,PIPER","ANDRADE,SOPHIA","MILDNER,STEPHANIE"
]


# UI
app_ui = ui.page_navbar(
    ui.nav_panel(
        "Home",
        ui.h1("Elms Basketball Analytics", class_="text-center"),
        ui.div(
            ui.img(src="https://www.elms.edu/wp-content/uploads/2022/12/blazer-ec-logo.png", height="150px"),
            class_="text-center"
        )
    ),


  ui.nav_panel("Game-by-Game Analysis",
      ui.row(
          ui.column(4, ""),
          ui.column(4,
              ui.input_select("selected_game", "Choose a Game", choices=game_labels),
              ui.input_select("second_dropdown", "Select a File", choices={})
          ),
          ui.column(4, "")
      ),
      ui.output_table("game_table")
  ),


  ui.nav_panel("Season-Long Analysis",
      ui.row(
          ui.column(4, ""),
          ui.column(4,
              ui.input_select("season_file", "Select Season Summary File", choices={})
          ),
          ui.column(4, "")
      ),
      ui.output_table("season_table")
  ),


  ui.nav_panel("Lineup Explorer",
      ui.row(
          ui.column(3, ""),
          ui.column(6,
              ui.input_slider("pm_range", "Filter Plus/Minus (from -9 to 9):", min=-9, max=9, value=[-9, 9]),
              ui.input_checkbox_group("pm_extremes", "Include:", choices=["Lower than -9", "Higher than 9"]),
              ui.input_text("player_filter", "Search for a Lineup", placeholder="e.g. GORSKI,TURCO"),
              ui.input_action_button("go_button", "Go", class_="btn-primary")
          ),
          ui.column(3, "")
      ),
      ui.output_ui("lineup_table_output")
  ),


  ui.nav_panel("Player Dashboard",
      ui.row(
          ui.column(4, ""),
          ui.column(4,
              ui.input_text("two_player_input", "Enter 2 Players (comma-separated)", placeholder="e.g. GORSKI, TURCO"),
              ui.input_action_button("two_player_go", "Search Season Totals", class_="btn-primary"),
              ui.hr(),
              ui.input_text("combo_input", "Enter 2 Players to See Each Game", placeholder="e.g. GORSKI, TURCO"),
              ui.input_action_button("combo_go", "Search Game-by-Game", class_="btn-secondary")
          ),
          ui.column(4, "")
      ),
      ui.output_table("two_player_table"),
      ui.output_table("combo_table")
  ),


  ui.nav_panel("Insights",
      ui.h3("Insights Coming Soon", class_="text-center")),

 ui.nav_panel("Final Project part 2 graphs",
  
)


)

# Server
def server(input, output, session):


  @reactive.Calc
  def matching_files():
      selected = input.selected_game()
      all_files = os.listdir(games_folder)
      csv_files = [f for f in all_files if f.endswith(".csv")]
      matched = [f for f in csv_files if fuzz.partial_ratio(selected.lower(), f.lower()) > 70]
      display_map = {f.replace("_", " ").replace(".csv", "").title(): f for f in matched}
      return display_map


  @reactive.Effect
  def update_file_dropdown():
      ui.update_select("second_dropdown", choices=matching_files())


  @reactive.Calc
  def load_game_data():
      selected_file = input.second_dropdown()
      if selected_file:
          file_map = matching_files()
          actual_file = file_map.get(selected_file, selected_file)
          file_path = os.path.join(games_folder, actual_file)
          df = pd.read_csv(file_path)
          if "Game" in df.columns:
              df = df.drop(columns=["Game"])
          return df
      return pd.DataFrame()


  @reactive.Calc
  def season_file_choices():
      files = [f for f in os.listdir(season_folder) if f.endswith(".csv")]
      filtered = [
          f for f in files
          if ("totals" in f.lower() or "four_factor" in f.lower())
          and "boxscore" not in f.lower()
          and "season_merged_lineup_totals" not in f.lower()
      ]
      return {f.replace("_", " ").replace(".csv", "").title(): f for f in filtered}


  @reactive.Effect
  def update_season_dropdown():
      ui.update_select("season_file", choices=season_file_choices())


  @reactive.Calc
  def load_season_data():
      selected = input.season_file()
      if selected:
          file_map = season_file_choices()
          actual_file = file_map.get(selected, selected)
          file_path = os.path.join(season_folder, actual_file)
          return pd.read_csv(file_path)
      return pd.DataFrame()


  @reactive.Calc
  def lineup_df():
      file_path = os.path.join(season_folder, "season_lineup_pm_totals.csv")
      if os.path.exists(file_path):
          return pd.read_csv(file_path)
      return pd.DataFrame()


  @reactive.event(input.go_button)
  def filtered_lineups():
      df = lineup_df()
      if df.empty or "Plus/Minus" not in df.columns:
          return pd.DataFrame({"Message": ["No data or Plus/Minus column missing"]})


      pm_min, pm_max = input.pm_range()
      extremes = input.pm_extremes()
      player_input = input.player_filter().strip()
      player_parts = [p.strip().upper() for p in player_input.split(",") if p.strip()]


      if len(player_parts) > 5:
          return pd.DataFrame({"Message": ["Please enter up to 5 player names only"]})


      within_range = df[(df["Plus/Minus"] >= pm_min) & (df["Plus/Minus"] <= pm_max)]
      lower_extreme = df[df["Plus/Minus"] < -9] if "Lower than -9" in extremes else pd.DataFrame()
      upper_extreme = df[df["Plus/Minus"] > 9] if "Higher than 9" in extremes else pd.DataFrame()


      combined = pd.concat([upper_extreme, within_range, lower_extreme ], ignore_index=True).drop_duplicates()


      if player_parts:
          def contains_all(lineup):
              return all(any(part in player for player in lineup.split(",")) for part in player_parts)
          combined = combined[combined["Lineup"].apply(contains_all)]


      return combined if not combined.empty else pd.DataFrame({"Message": ["No matching lineups found"]})


  @reactive.Calc
  def two_player_df():
      file_path = os.path.join(season_folder, "season_two_player_totals.csv")
      if os.path.exists(file_path):
          return pd.read_csv(file_path)
      return pd.DataFrame()


  @reactive.event(input.two_player_go)
  def filtered_two_player_data():
      df = two_player_df()
      if df.empty or "Player 1" not in df.columns or "Player 2" not in df.columns:
          return pd.DataFrame({"Message": ["No data or required columns missing"]})


      text_input = input.two_player_input().strip()
      players = [p.strip().upper() for p in text_input.split(",") if p.strip()]


      if len(players) != 2:
          return pd.DataFrame()


      p1_input, p2_input = players


      def fuzzy_match(p_input, name):
          return fuzz.partial_ratio(p_input, name.upper()) >= 80


      def row_matches(row):
          p1_row = row["Player 1"]
          p2_row = row["Player 2"]
          return (
              (fuzzy_match(p1_input, p1_row) and fuzzy_match(p2_input, p2_row)) or
              (fuzzy_match(p1_input, p2_row) and fuzzy_match(p2_input, p1_row))
          )


      result = df[df.apply(row_matches, axis=1)].reset_index(drop=True)


      return result if not result.empty else pd.DataFrame({"Message": ["No matching combination found"]})


  @reactive.event(input.combo_go)
  def combo_data():
      file_path = os.path.join(season_folder, "season_two_player_combinations.csv")
      if not os.path.exists(file_path):
          return pd.DataFrame({"Message": ["Game-by-game combo file not found"]})


      df = pd.read_csv(file_path)
      if df.empty or "Player 1" not in df.columns or "Player 2" not in df.columns:
          return pd.DataFrame({"Message": ["Required columns missing"]})


      text_input = input.combo_input().strip()
      players = [p.strip().upper() for p in text_input.split(",") if p.strip()]


      if len(players) != 2:
          return pd.DataFrame({"Message": ["Please enter exactly 2 player names."]})


      p1_input, p2_input = players


      def fuzzy_match(p_input, name):
          return fuzz.partial_ratio(p_input, name.upper()) >= 80


      def row_matches(row):
          p1_row = row["Player 1"]
          p2_row = row["Player 2"]
          return (
              (fuzzy_match(p1_input, p1_row) and fuzzy_match(p2_input, p2_row)) or
              (fuzzy_match(p1_input, p2_row) and fuzzy_match(p2_input, p1_row))
          )


      result = df[df.apply(row_matches, axis=1)].reset_index(drop=True)


      return result if not result.empty else pd.DataFrame({"Message": ["No matching combinations found"]})


  @output
  @render.table
  def game_table():
      return load_game_data()


  @output
  @render.table
  def season_table():
      return load_season_data()


  @output
  @render.ui
  def lineup_table_output():
      df = filtered_lineups()
      return ui.output_table("lineup_filtered_table") if not df.empty else ui.p("No matching lineups found.")


  @output
  @render.table
  def lineup_filtered_table():
      return filtered_lineups()


  @output
  @render.table
  def two_player_table():
      return filtered_two_player_data()


  @output
  @render.table
  def combo_table():
      return combo_data()


app = App(app_ui, server)

if __name__ == "__main__":
    app.run()