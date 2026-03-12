#Requirements
#pip install customtkinter
#pip install gspread oauth2client
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
import uuid
from datetime import datetime
import customtkinter as ctk
from tkinter import messagebox, filedialog
from tkinter import StringVar, Toplevel, Listbox, ttk
import sys
import tkinter as tk

# Set default appearance mode and color theme for customtkinter
ctk.set_appearance_mode("Dark")  # Options: "Light", "Dark", "System"
ctk.set_default_color_theme("blue")  # Options: "blue", "green", "dark-blue"

DATA_FILE = 'tournament_data.json'


class TournamentManager:
    """Manages tournament data including teams, players, matches, and skill levels."""

    def __init__(self):
        self.data = self._load_data()
        self.group_a_sub_matches = []
        self.group_b_sub_matches = []


    def find_match_id(self, date, team1_name, team2_name):
        for match_id, match in self.data['matches'].items():
            if 'timestamp' not in match:
                continue
            match_time = datetime.fromisoformat(match['timestamp']).strftime('%Y-%m-%d %H:%M')
            if match_time == date and (
                (match['team1_name'] == team1_name and match['team2_name'] == team2_name) or
                (match['team1_name'] == team2_name and match['team2_name'] == team1_name)
            ):
                return match_id
        return None


    def _load_data(self):
        """Loads tournament data from a JSON file."""
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                messagebox.showerror("Error",
                                     "Could not load data from file. File might be corrupted. Starting with new data.")
                os.remove(DATA_FILE)  # Optionally remove corrupted file
                return self._default_data()
        return self._default_data()

    def update_team_group(self, team_id, new_group):
        if new_group not in ["A", "B"]:
            messagebox.showerror("Input Error", "Group must be 'A' or 'B'.")
            return False, "error"
        if team_id not in self.data['teams']:
            messagebox.showerror("Error", "Team not found.")
            return False, "error"

        self.data['teams'][team_id]['group'] = new_group
        self._save_data()
        return True, f"Team moved to Group {new_group}."


    def _default_data(self):
        """Returns the default structure for new tournament data."""
        return {
            'teams': {},
            'matches': {},
            'skill_levels': ['Beginner', 'Intermediate', 'Advanced', 'Expert']
        }

    def _save_data(self):
        """Saves current tournament data to a JSON file."""
        try:
            with open(DATA_FILE, 'w') as f:
                json.dump(self.data, f, indent=4)
        except IOError as e:
            messagebox.showerror("Save Error", f"Could not save data: {e}")

    # --- Team Management ---
    def create_team(self, team_name, group):
        """Creates a new team with a unique ID and group."""
        if not team_name:
            messagebox.showerror("Input Error", "Team name cannot be empty.")
            return None, "error"

        if group not in ["A", "B"]:
            messagebox.showerror("Input Error", "Group must be 'A' or 'B'.")
            return None, "error"

        # Check for duplicate team name
        for team_id, team in self.data['teams'].items():
            if team['name'].lower() == team_name.lower():
                messagebox.showerror("Duplicate Team", f"Team '{team_name}' already exists.")
                return None, "error"

        team_id = str(uuid.uuid4())
        self.data['teams'][team_id] = {
            'name': team_name,
            'group': group,
            'players': {}
        }
        self._save_data()
        return team_id, f"Team '{team_name}' (Group {group}) created successfully!"
    

    def get_team(self, team_id):
        """Retrieves a team by its ID."""
        return self.data['teams'].get(team_id)

    def get_all_teams(self):
        """Returns a list of all teams with their IDs and names."""
        return [(team_id, team['name']) for team_id, team in self.data['teams'].items()]

    def update_team_name(self, team_id, new_name):
        """Updates the name of an existing team."""
        if not new_name:
            messagebox.showerror("Input Error", "New team name cannot be empty.")
            return False, "error"
        if team_id not in self.data['teams']:
            messagebox.showerror("Error", "Team not found.")
            return False, "error"

        # Check for duplicate name among other teams
        for existing_id, team in self.data['teams'].items():
            if existing_id != team_id and team['name'].lower() == new_name.lower():
                messagebox.showerror("Duplicate Name", f"Another team with name '{new_name}' already exists.")
                return False, "error"

        old_name = self.data['teams'][team_id]['name']
        self.data['teams'][team_id]['name'] = new_name
        self._save_data()
        return True, f"Team '{old_name}' renamed to '{new_name}' successfully!"

    def delete_team(self, team_id):
        """Deletes a team and associated match records."""
        if team_id not in self.data['teams']:
            messagebox.showerror("Error", "Team not found.")
            return False, "error"

        team_name = self.data['teams'][team_id]['name']

        if not messagebox.askyesno("Confirm Deletion",
                                   f"Are you sure you want to delete '{team_name}' and ALL its players and associated match records? This action cannot be undone."):
            return False, "cancelled"

        del self.data['teams'][team_id]

        # Remove matches involving this team
        matches_to_remove = [match_id for match_id, match in self.data['matches'].items()
                             if match['team1_id'] == team_id or match['team2_id'] == team_id]
        for match_id in matches_to_remove:
            del self.data['matches'][match_id]

        self._save_data()
        return True, f"Team '{team_name}' and its associated data deleted successfully!"

    # --- Player Management ---
    def add_player(self, team_id, player_name, skill_level):
        """Adds a player to a team."""
        if not player_name:
            messagebox.showerror("Input Error", "Player name cannot be empty.")
            return False, "error"
        if not skill_level:
            messagebox.showerror("Input Error", "Skill level cannot be empty.")
            return False, "error"
        if team_id not in self.data['teams']:
            messagebox.showerror("Error", "Team not found.")
            return False, "error"
        if skill_level not in self.data['skill_levels']:
            messagebox.showerror("Invalid Skill",
                                 f"Skill level '{skill_level}' is not recognized. Please add it first in Team Management.")
            return False, "error"

        team = self.data['teams'][team_id]
        # Check for duplicate player name within the same team
        for player_id, player in team['players'].items():
            if player['name'].lower() == player_name.lower():
                messagebox.showerror("Duplicate Player", f"Player '{player_name}' already exists in '{team['name']}'.")
                return False, "error"

        player_id = str(uuid.uuid4())
        team['players'][player_id] = {'name': player_name, 'skill': skill_level}
        self._save_data()
        return True, f"Player '{player_name}' added to '{team['name']}' successfully!"

    def update_player(self, team_id, player_id, new_name, new_skill):
        """Edits an existing player's name and/or skill level."""
        if not new_name:
            messagebox.showerror("Input Error", "New player name cannot be empty.")
            return False, "error"
        if not new_skill:
            messagebox.showerror("Input Error", "New skill level cannot be empty.")
            return False, "error"
        if team_id not in self.data['teams']:
            messagebox.showerror("Error", "Team not found.")
            return False, "error"
        if player_id not in self.data['teams'][team_id]['players']:
            messagebox.showerror("Error", "Player not found in this team.")
            return False, "error"
        if new_skill not in self.data['skill_levels']:
            messagebox.showerror("Invalid Skill",
                                 f"Skill level '{new_skill}' is not recognized. Please add it first in Team Management.")
            return False, "error"

        team = self.data['teams'][team_id]
        old_player_name = team['players'][player_id]['name']

        # Check for duplicate player name in the same team, excluding the player being updated
        for existing_player_id, player in team['players'].items():
            if existing_player_id != player_id and player['name'].lower() == new_name.lower():
                messagebox.showerror("Duplicate Player",
                                     f"Another player with name '{new_name}' already exists in '{team['name']}'.")
                return False, "error"

        team['players'][player_id]['name'] = new_name
        team['players'][player_id]['skill'] = new_skill
        self._save_data()
        return True, f"Player '{old_player_name}' updated to '{new_name}' with skill '{new_skill}' successfully!"

    def remove_player(self, team_id, player_id):
        """Removes a player from a team."""
        if team_id not in self.data['teams']:
            messagebox.showerror("Error", "Team not found.")
            return False, "error"
        if player_id not in self.data['teams'][team_id]['players']:
            messagebox.showerror("Error", "Player not found in this team.")
            return False, "error"

        player_name = self.data['teams'][team_id]['players'][player_id]['name']
        if not messagebox.askyesno("Confirm Removal",
                                   f"Are you sure you want to remove '{player_name}' from '{self.data['teams'][team_id]['name']}'?"):
            return False, "cancelled"

        del self.data['teams'][team_id]['players'][player_id]
        self._save_data()
        return True, f"Player '{player_name}' removed successfully!"

    def get_players_for_team(self, team_id):
        """Returns a list of players for a given team."""
        if team_id not in self.data['teams']:
            return []
        return [(player_id, player['name'], player['skill']) for player_id, player in
                self.data['teams'][team_id]['players'].items()]
    
    def get_player_name(self, player_id):
        """Returns the name of a player given their ID."""
        for team_id, team_data in self.data['teams'].items():
            if player_id in team_data['players']:
                return team_data['players'][player_id]['name']
        return "Unknown Player"

    # --- Skill Level Management ---
    def get_skill_levels(self):
        """Returns the list of predefined skill levels."""
        return self.data['skill_levels']

    def add_skill_level(self, skill):
        """Adds a new skill level to the predefined list."""
        if not skill:
            messagebox.showerror("Input Error", "Skill level name cannot be empty.")
            return False, "error"
        if skill.lower() in [s.lower() for s in self.data['skill_levels']]:
            messagebox.showerror("Duplicate Skill", f"Skill level '{skill}' already exists.")
            return False, "error"
        self.data['skill_levels'].append(skill)
        self._save_data()
        return True, f"Skill level '{skill}' added successfully!"

    def remove_skill_level(self, skill):
        """Removes a skill level from the predefined list."""
        if skill not in self.data['skill_levels']:
            messagebox.showerror("Error", f"Skill level '{skill}' not found.")
            return False, "error"

        # Check if any player uses this skill level before removing
        for team_id, team in self.data['teams'].items():
            for player_id, player in team['players'].items():
                if player['skill'] == skill:
                    messagebox.showerror("Cannot Remove",
                                         f"Cannot remove skill level '{skill}' because player '{player['name']}' in team '{team['name']}' uses it. Please update or remove affected players first.")
                    return False, "error"

        if not messagebox.askyesno("Confirm Removal", f"Are you sure you want to remove skill level '{skill}'?"):
            return False, "cancelled"

        self.data['skill_levels'].remove(skill)
        self._save_data()
        return True, f"Skill level '{skill}' removed successfully!"

    # --- Tournament Mode ---
    def record_match(self, team1_id, team2_id, sub_matches_data):
        """Records a match between two teams, including detailed sub-matches."""
        if team1_id == team2_id:
            messagebox.showerror("Invalid Match", "Cannot record a match between the same team.")
            return False, "error"
        if team1_id not in self.data['teams'] or team2_id not in self.data['teams']:
            messagebox.showerror("Error", "One or both selected teams not found.")
            return False, "error"
        if not sub_matches_data:
            messagebox.showerror("Input Error", "Cannot record a match with no sub-matches.")
            return False, "error"

        team1_sub_match_wins = 0
        team2_sub_match_wins = 0
        
        # Determine overall team winner based on sub-match wins
        for sub_match in sub_matches_data:
            score1 = sub_match.get('team1_score', 0)
            score2 = sub_match.get('team2_score', 0)

            if score1 > score2:
                sub_match['winner_player_ids'] = sub_match.get('team1_player_ids', [])
                team1_sub_match_wins += 1
            elif score2 > score1:
                sub_match['winner_player_ids'] = sub_match.get('team2_player_ids', [])
                team2_sub_match_wins += 1
            else:
                sub_match['winner_player_ids'] = []
                

        winner_id = None
        if team1_sub_match_wins > team2_sub_match_wins:
            winner_id = team1_id
        elif team2_sub_match_wins > team1_sub_match_wins:
            winner_id = team2_id

        match_id = str(uuid.uuid4())
        self.data['matches'][match_id] = {
            'team1_id': team1_id,
            'team2_id': team2_id,
            'team1_name': self.data['teams'][team1_id]['name'],
            'team2_name': self.data['teams'][team2_id]['name'],
            'sub_matches': sub_matches_data,
            'timestamp': datetime.now().isoformat(),
            'winner_name': self.data['teams'][winner_id]['name'] if winner_id else 'Draw',
            'winner_id': winner_id,
            'team1_sub_match_wins': team1_sub_match_wins,
            'team2_sub_match_wins': team2_sub_match_wins
        }
        self._save_data()
        team1_name = self.data['teams'][team1_id]['name']
        team2_name = self.data['teams'][team2_id]['name']
        winner_display = self.data['teams'][winner_id]['name'] if winner_id else 'Draw'
        return True, f"Match between {team1_name} and {team2_name} recorded. Team Winner: {winner_display} ({team1_sub_match_wins}-{team2_sub_match_wins} sub-matches)."

    def delete_match(self, match_id):
        """Deletes a match by its ID."""
        if match_id not in self.data['matches']:
            return False, "Match not found."
    
        del self.data['matches'][match_id]
        self._save_data()
        return True, "Match deleted successfully."

    def update_match(self, match_id, new_sub_matches):
        """Updates the sub-matches of an existing match."""
        if match_id not in self.data['matches']:
            return False, "Match not found."

        match = self.data['matches'][match_id]
        team1_id = match['team1_id']
        team2_id = match['team2_id']

        # Recalculate wins
        team1_sub_match_wins = 0
        team2_sub_match_wins = 0

        for sub_match in new_sub_matches:
            if not sub_match.get('winner_player_ids'):
                continue
            team1_player_in_winners = any(pid in self.data['teams'][team1_id]['players'] for pid in sub_match['winner_player_ids'])
            team2_player_in_winners = any(pid in self.data['teams'][team2_id]['players'] for pid in sub_match['winner_player_ids'])

            if team1_player_in_winners and not team2_player_in_winners:
                team1_sub_match_wins += 1
            elif team2_player_in_winners and not team1_player_in_winners:
                team2_sub_match_wins += 1

        winner_id = None
        if team1_sub_match_wins > team2_sub_match_wins:
            winner_id = team1_id
        elif team2_sub_match_wins > team1_sub_match_wins:
            winner_id = team2_id

        match['sub_matches'] = new_sub_matches
        match['team1_sub_match_wins'] = team1_sub_match_wins
        match['team2_sub_match_wins'] = team2_sub_match_wins
        match['winner_id'] = winner_id

        self._save_data()
        return True, "Match updated successfully."
    
    def calculate_standings(self):
        """Calculates and returns current tournament standings."""
        standings = {}
        for team_id, team in self.data['teams'].items():
            standings[team_id] = {
                'name': team['name'],
                'wins': 0,
                'losses': 0,
                'draws': 0,
                'matches_played': 0
            }

        for match_id, match in self.data['matches'].items():
            t1_id = match['team1_id']
            t2_id = match['team2_id']

            if t1_id in standings:
                standings[t1_id]['matches_played'] += 1
            if t2_id in standings:
                standings[t2_id]['matches_played'] += 1

            winner_id = match['winner_id']
            if winner_id == t1_id and t1_id in standings:
                standings[t1_id]['wins'] += 1
                if t2_id in standings: standings[t2_id]['losses'] += 1
            elif winner_id == t2_id and t2_id in standings:
                standings[t2_id]['wins'] += 1
                if t1_id in standings: standings[t1_id]['losses'] += 1
            elif winner_id is None and t1_id in standings and t2_id in standings:  # Draw
                standings[t1_id]['draws'] += 1
                standings[t2_id]['draws'] += 1

        sorted_standings = sorted(standings.values(), key=lambda x: x['wins'], reverse=True)
        return sorted_standings

    def calculate_player_points(self):
        """Calculates and returns individual player stats: points (wins) and losses based on sub-match results."""
        player_points = {}
        for team_id, team_data in self.data['teams'].items():
            for player_id, player_data in team_data['players'].items():
                player_points[player_id] = {
                    'name': player_data['name'],
                    'team_name': team_data['name'],
                    'wins': 0,
                    'losses': 0
                }

        for match_data in self.data['matches'].values():
            for sub_match in match_data.get('sub_matches', []):
                team1_ids = sub_match.get('team1_player_ids', [])
                team2_ids = sub_match.get('team2_player_ids', [])
                winner_ids = sub_match.get('winner_player_ids', [])

                for pid in team1_ids + team2_ids:
                    if pid in player_points:
                        if pid in winner_ids:
                            player_points[pid]['wins'] += 1
                        else:
                            player_points[pid]['losses'] += 1

        sorted_player_points = sorted(
            player_points.values(),
            key=lambda x: (-x['wins'], x['losses'])
        )
        return sorted_player_points

    def get_match_history(self):
        """Returns a list of all recorded matches."""
        all_matches_with_ids = [(match_id, match_data) for match_id, match_data in self.data['matches'].items()]

        sorted_matches = sorted(all_matches_with_ids, key=lambda x: x[1]['timestamp'], reverse=True)
    
        display_matches = []
        for match_id, match in sorted_matches:
            team1_name = self.data['teams'].get(match['team1_id'], {}).get('name', 'Unknown Team 1')
            team2_name = self.data['teams'].get(match['team2_id'], {}).get('name', 'Unknown Team 2')
            
            winner_name = 'Draw'
            if match.get('winner_id'): # Use .get for robustness
                winner_name = self.data['teams'].get(match['winner_id'], {}).get('name', 'Unknown Winner') 
            
            # Display overall sub-match score for the team match
            sub_match_score = f"{match.get('team1_sub_match_wins', 0)}-{match.get('team2_sub_match_wins', 0)}"
            
            match_date = datetime.fromisoformat(match['timestamp']).strftime('%Y-%m-%d %H:%M')
            display_matches.append({
                'date': match_date,
                'team1_name': team1_name,
                'score': sub_match_score, # Now shows sub-match score
                'team2_name': team2_name,
                'winner_name': winner_name,
                'id': match_id
            })
        return display_matches


class TournamentApp:
    def __init__(self, master):
        self.manager = TournamentManager()
        self.master = master
        master.title("Tournament Management App")
        master.geometry("1100x800")  # Adjusted window size for more content

        style = ttk.Style()
        style.theme_use("default")

        self.group_a_sub_matches = []
        self.group_b_sub_matches = []
        self.current_sub_matches = []

        # Treeview main body
        style.configure("Treeview",
            background="#1e1e1e",
            foreground="#eaeaea",
            rowheight=30,
            fieldbackground="#1e1e1e",
            bordercolor="#333333",
            borderwidth=0,
            font=('Segoe UI', 11)
        )

        # Treeview headers
        style.configure("Treeview.Heading",
            background="#292929",
            foreground="#ffffff",
            font=('Segoe UI', 12, 'bold'),
            borderwidth=0
        )

        # Selection color
        style.map("Treeview",
            background=[("selected", "#3a86ff")],
            foreground=[("selected", "#ffffff")]
        )

        # Status Bar
        self.status_label = ctk.CTkLabel(master, text="", anchor="w", text_color="gray", font=ctk.CTkFont(size=12, weight="bold"))
        self.status_label.pack(side="bottom", fill="x", padx=10, pady=5)
        self.status_timeout_id = None

        # Main Notebook (Tabs)
        self.notebook = ctk.CTkTabview(master)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=10)

        # Teams Tab
        self.teams_frame = self.notebook.add("Teams")
        self._setup_teams_tab()

        # Tournament Tab
        self.tournament_frame = self.notebook.add("Tournament")
        self._setup_tournament_tab()

        self._setup_leaderboards_tab()
        
        # Initial data load and UI update
        self.update_teams_treeview()
        self.update_players_treeview()
        self.update_skill_levels_listbox()
        self.update_tournament_tab()
        self.update_leaderboards_tab()
        self._setup_history_tab()
        self._setup_settings_tab()

        self.notebook.configure(command=self._on_tab_change)
        self._update_latest_match_display()

    def clear_google_sheet(self, sheet_id: str, credentials_file: str):
        """Clears both Standings and Player Leaderboard worksheets in the Google Sheet."""
        try:
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)
            client = gspread.authorize(creds)

            spreadsheet = client.open_by_key(sheet_id)

            # Clear Sheet1 if it exists
            try:
                sheet1 = spreadsheet.worksheet("Sheet1")
                sheet1.clear()
            except gspread.exceptions.WorksheetNotFound:
                pass

            # Clear Player Leaderboard tab if it exists
            try:
                player_sheet = spreadsheet.worksheet("Player Leaderboard")
                player_sheet.clear()
            except gspread.exceptions.WorksheetNotFound:
                pass


            self.show_status_message("Google Sheet data cleared", color="green")

        except Exception as e:
            self.show_status_message(f"Failed to clear Google Sheet: {e}", color="red")


    def _refresh_submatch_tree(self, treeview, submatch_list):
        for i in treeview.get_children():
            treeview.delete(i)

        for sm in submatch_list:
            team1_names = ", ".join([self.manager.get_player_name(pid) for pid in sm.get('team1_player_ids', [])])
            team2_names = ", ".join([self.manager.get_player_name(pid) for pid in sm.get('team2_player_ids', [])])
            winner_names = ", ".join([self.manager.get_player_name(pid) for pid in sm.get('winner_player_ids', [])])
            players = f"{team1_names} vs {team2_names}"
            score = f"{sm.get('team1_score', 0)} - {sm.get('team2_score', 0)}"
            treeview.insert("", "end", values=(sm['type'], players, score, winner_names))


    def _update_latest_match_display(self):
        history = self.manager.get_match_history()
        if not history:
            self.latest_match_label.configure(text="No matches yet.")
            return

        latest = history[0]
        display_text = (
            f"{latest['date']}\n"
            f"{latest['team1_name']} {latest['score']} {latest['team2_name']}\n"
            f"Winner: {latest['winner_name']}"
        )
        self.latest_match_label.configure(text=display_text)

    def _reset_tournament_data(self):
        # Ask if they want to import first
        if messagebox.askyesno("Import Tournament?", "Would you like to export the tournament file before resetting?"):
            self._import_tournament_data()

        # Confirm actual reset
        if messagebox.askyesno("Confirm Reset", "This will delete all tournament data — teams, players, matches. Are you sure?"):
            self.manager.data = self.manager._default_data()
            self.manager._save_data()
            self.update_teams_treeview()
            self.update_players_treeview()
            self.update_tournament_tab()
            self.update_leaderboards_tab()
            self.show_status_message("Tournament reset successfully", duration_ms = 1500, color = 'red')

        

    def _setup_settings_tab(self):
        self.settings_frame = self.notebook.add("Settings")

        ctk.CTkLabel(self.settings_frame, text="App Settings", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=10)

        # Export Button
        ctk.CTkButton(self.settings_frame, text="Export Tournament Data", command=self._export_tournament_data).pack(pady=10)

        # Import Button
        ctk.CTkButton(self.settings_frame, text="Import Tournament Data", command=self._import_tournament_data).pack(pady=10)
        
        # reset Tournament
        ctk.CTkButton(self.settings_frame, text="Reset Tournament", command=self._reset_tournament_data).pack(pady=10)
        ctk.CTkButton(
            self.settings_frame,
            text="Clear Google Sheet Data",
            command=lambda: self.clear_google_sheet(
                sheet_id="1MPAoCUNEgWIK9M7kGDWbcQsU_jp4OFaTb2m6XLm2IRg",
                credentials_file= "google-credentials.json"
            )
        ).pack(pady=10)


    def _export_tournament_data(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if file_path:
            with open(file_path, 'w') as f:
                json.dump(self.manager.data, f, indent=4)
            self.show_status_message("Tournament data exported.")

    def _import_tournament_data(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    imported_data = json.load(f)
            except (json.JSONDecodeError, IOError):
                messagebox.showerror("Invalid File", "Could not read or parse the selected file.")
                return

            required_keys = ['teams', 'matches', 'skill_levels']
            if not all(k in imported_data for k in required_keys):
                messagebox.showerror("Invalid File", f"Selected file is missing required tournament data keys: {required_keys}")
                return
            self.manager.data = imported_data
            self.manager._save_data()
            self.update_teams_treeview()
            self.update_players_treeview()
            self.update_tournament_tab()
            self.update_leaderboards_tab()
            self.show_status_message("Tournament data imported.")
            self.show_status_message("Tournament Imported Successfully", duration_ms=1500, color="green")

    def _on_history_double_click(self, event):
        item = self.history_treeview.identify_row(event.y)
        if not item:
            return

        match_date = self.history_treeview.item(item, "values")[0]
        team1 = self.history_treeview.item(item, "values")[1]
        team2 = self.history_treeview.item(item, "values")[3]

        match_id = self.manager.find_match_id(match_date, team1, team2)
        if match_id is None:
            messagebox.showerror("Not Found", "Match data not found.")
            return

        self._show_match_details(match_id)

    def _on_standings_double_click(self, event):
        item = self.big_standings_treeview.identify_row(event.y)
        if not item:
            return

        team_name = self.big_standings_treeview.item(item, "values")[0]
        self._show_team_match_history_details(team_name)


    def _show_match_details(self, match_id):
        match = self.manager.data['matches'].get(match_id)
        if not match:
            messagebox.showerror("Not Found", "Match record not found.")
            return

        dialog = ctk.CTkToplevel(self.master)
        dialog.title(f"Match Details: {match['team1_name']} vs {match['team2_name']}")
        dialog.geometry("1000x550")

        match_date = datetime.fromisoformat(match['timestamp']).strftime('%d/%m/%Y\n%H:%M')

        ctk.CTkLabel(dialog, text=f"{match['team1_name']}  vs  {match['team2_name']}",
                     font=("Helvetica", 20, "bold")).pack(pady=(10, 5))

        ctk.CTkLabel(dialog, text=f"Winner: {match['winner_name']}",
                     font=("Helvetica", 18, "bold")).pack(pady=(0, 10))

        ctk.CTkLabel(dialog, text=f"{match_date}",
             font=("Helvetica", 16)).pack(pady=(0, 5))

        tree = ttk.Treeview(dialog, columns=("Type", "Player1", "Player2", "Score", "Winner"), show="headings")
        for col in ("Type", "Player1", "Player2", "Score", "Winner"):
            tree.heading(col, text=col)
            tree.column(col, anchor="center")
        tree.pack(pady=5)

        for sm in match['sub_matches']:
            team1_names = ", ".join([self.manager.get_player_name(pid) for pid in sm.get('team1_player_ids', [])])
            team2_names = ", ".join([self.manager.get_player_name(pid) for pid in sm.get('team2_player_ids', [])])
            winner_names = ", ".join([self.manager.get_player_name(pid) for pid in sm.get('winner_player_ids', [])])
            
            score = f"{sm.get('team1_score', 0)} - {sm.get('team2_score', 0)}"

            tree.insert("", "end", values=(sm['type'], team1_names, team2_names, score, winner_names))

        ctk.CTkButton(dialog, text="Close", command=dialog.destroy).pack(pady=5)


    def _show_team_match_history_details(self, team_name):
        history = self.manager.get_match_history()
        matches_for_team = [m for m in history if m['team1_name'] == team_name or m['team2_name'] == team_name]

        if not matches_for_team:
            messagebox.showinfo("No Matches", f"No matches found for team '{team_name}'.")
            return

        dialog = ctk.CTkToplevel(self.master)
        dialog.title(f"All Matches for {team_name}")
        dialog.geometry("1000x500")

        tree = ttk.Treeview(dialog, columns=("Date", "Opponent", "Score", "Winner"), show="headings")
        for col in ("Date", "Opponent", "Score", "Winner"):
            tree.heading(col, text=col)
            tree.column(col, anchor="center")
        tree.pack(fill="both", expand=True, padx=10, pady=10)

        for match in matches_for_team:
            opponent = match['team2_name'] if match['team1_name'] == team_name else match['team1_name']
            tree.insert("", "end", values=(match['date'], opponent, match['score'], match['winner_name']))

        ctk.CTkButton(dialog, text="Close", command=dialog.destroy).pack(pady=5)


    def _setup_history_tab(self):
        self.history_frame = self.notebook.add("History")

        ctk.CTkLabel(self.history_frame, text="Match History", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)

        filter_frame = ctk.CTkFrame(self.history_frame, fg_color="transparent")
        filter_frame.pack(pady=5)

        ctk.CTkLabel(filter_frame, text="Filter by Group:").pack(side="left", padx=5)

        self.history_group_filter_cb = ctk.CTkComboBox(
            filter_frame,
            values=["All", "A", "B"],
            state="readonly",
            width=150,
            command=lambda _: self.update_history_tab()
        )
        self.history_group_filter_cb.set("All")
        self.history_group_filter_cb.pack(side="left", padx=5)


        self.history_treeview = ttk.Treeview(self.history_frame,
                                             columns=("Date", "Team1", "Score", "Team2", "Winner"),
                                             show="headings")

        for col in ("Date", "Team1", "Score", "Team2", "Winner"):
            self.history_treeview.heading(col, text=col)
            self.history_treeview.column(col, anchor="center")

        self.history_treeview.pack(fill="both", expand=True, padx=10, pady=10)
        self.history_treeview.bind("<Double-1>", self._on_history_double_click)
        
        scroll = ttk.Scrollbar(self.history_frame, orient="vertical", command=self.history_treeview.yview)
        scroll.pack(side="right", fill="y")
        self.history_treeview.configure(yscrollcommand=scroll.set)
        
    def update_history_tab(self):
        for i in self.history_treeview.get_children():
            self.history_treeview.delete(i)

        history = self.manager.get_match_history()
        selected_group = self.history_group_filter_cb.get()
        if selected_group != "All":
            history = [
                h for h in history 
                if self.manager.get_team(
                    self.manager.data["matches"][h['id']]['team1_id']
                )['group'] == selected_group
            ]

        if not history:
            self.history_treeview.insert("", "end", values=("No matches yet", "", "", "", ""))
            return

        for match in history:
            self.history_treeview.insert("", "end", values=(
                match['date'],
                match['team1_name'],
                match['score'],
                match['team2_name'],
                match['winner_name']
            ))

    def update_leaderboards_tab(self):
        """Updates the Team Standings and Player Leaderboard in the Leaderboards tab."""

        # Update Team Standings
        for i in self.big_standings_treeview.get_children():
            self.big_standings_treeview.delete(i)

        standings_data = self.manager.calculate_standings()
        selected_group = self.standings_group_filter_cb.get()

        if selected_group != "All":
            valid_team_ids = [tid for tid, t in self.manager.data['teams'].items() if t['group'] == selected_group]
            standings_data = [
                s for s in standings_data
                if any(self.manager.data['teams'][tid]['name'] == s['name'] for tid in valid_team_ids)
            ]

        if not standings_data:
            self.big_standings_treeview.insert("", "end", values=("No teams/matches yet", "", "", "", ""))
        else:
            for team_stats in standings_data:
                self.big_standings_treeview.insert("", "end", iid=team_stats['name'], values=(
                    team_stats['name'],
                    team_stats['wins'],
                    team_stats['losses'],
                    team_stats['draws'],
                    team_stats['matches_played']
                ))

        # Update Player Leaderboard
        for i in self.big_player_treeview.get_children():
            self.big_player_treeview.delete(i)

        player_data = self.manager.calculate_player_points()

        # Apply skill filter if combobox exists
        selected_skill = self.skill_filter_combobox.get() if hasattr(self, 'skill_filter_combobox') else "All"
        if selected_skill != "All":
            filtered_player_data = []
            for team_id, team in self.manager.data['teams'].items():
                for player_id, player_info in team['players'].items():
                    if player_info['skill'] == selected_skill:
                        matching_player = next((p for p in player_data if p['name'] == player_info['name']), None)
                        if matching_player:
                            filtered_player_data.append(matching_player)
            player_data = filtered_player_data

        # Apply group filter if combobox exists
        selected_group_player = self.group_filter_combobox.get() if hasattr(self, 'group_filter_combobox') else "All"
        if selected_group_player != "All":
            valid_team_ids = [tid for tid, t in self.manager.data['teams'].items() if t['group'] == selected_group_player]
            player_data = [
                p for p in player_data
                if any(self.manager.data['teams'][tid]['name'] == p['team_name'] for tid in valid_team_ids)
            ]

        #Re-sort after all filtering
        player_data = sorted(player_data, key=lambda x: (-x['wins'], x['losses']))

        if not player_data:
            self.big_player_treeview.insert("", "end", values=("No players yet", "", ""))
        else:
            for player in player_data:
                self.big_player_treeview.insert("", "end", values=(
                    player['name'],
                    player['team_name'],
                    player['wins'],
                    player['losses']
                ))

    def _setup_leaderboards_tab(self):
        self.leaderboards_frame = self.notebook.add("Leaderboards")

        # Team Standings Frame
        standings_frame = ctk.CTkFrame(self.leaderboards_frame)
        standings_frame.pack(side="top", fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(standings_frame, text="Team Standings", font=ctk.CTkFont(size=15, weight="bold")).pack(pady=5)
        standings_filter_frame = ctk.CTkFrame(standings_frame, fg_color="transparent")
        standings_filter_frame.pack(pady=5)

        ctk.CTkLabel(standings_filter_frame, text="Filter by Group:").pack(side="left", padx=5)

        self.standings_group_filter_cb = ctk.CTkComboBox(
            standings_filter_frame,
            values=["All", "A", "B"],
            state="readonly",
            width=120,
            command=lambda _: self.update_leaderboards_tab()
        )

        self.standings_group_filter_cb.pack(side="left", padx=5)
        self.standings_group_filter_cb.set("All")

        self.big_standings_treeview = ttk.Treeview(standings_frame,
                                                   columns=("Team", "Wins", "Losses", "Draws", "Played"),
                                                   show="headings",
                                                   height = 8)
        for col in ("Team", "Wins", "Losses", "Draws", "Played"):
            self.big_standings_treeview.heading(col, text=col)
            self.big_standings_treeview.column(col, anchor="center")
        self.big_standings_treeview.pack(fill="both", expand=True)
        self.big_standings_treeview.bind("<Double-1>", self._on_standings_double_click)

        # Player Leaderboard Frame
        players_frame = ctk.CTkFrame(self.leaderboards_frame)
        players_frame.pack(side="top", fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(players_frame, text="Player Leaderboard", font=ctk.CTkFont(size=15, weight="bold")).pack(pady=5)
        filter_frame = ctk.CTkFrame(players_frame, fg_color="transparent")
        filter_frame.pack(pady=5)

        ctk.CTkLabel(filter_frame, text="Filter by Skill:").pack(side="left", padx=5)

        self.skill_filter_combobox = ctk.CTkComboBox(
            filter_frame,
            values=["All"] + self.manager.get_skill_levels(),
            state="readonly",
            width=150,
            command=lambda _: self.update_leaderboards_tab()
        )
        self.skill_filter_combobox.pack(side="left", padx=5)
        self.skill_filter_combobox.set("All")

        ctk.CTkLabel(filter_frame, text=" | Group:").pack(side="left", padx=5)

        self.group_filter_combobox = ctk.CTkComboBox(
            filter_frame,
            values=["All", "A", "B"],
            state="readonly",
            width=100,
            command=lambda _: self.update_leaderboards_tab()
        )
        self.group_filter_combobox.pack(side="left", padx=5)
        self.group_filter_combobox.set("All")


        
        self.big_player_treeview = ttk.Treeview(players_frame,
                                                columns=("Player", "Team", "Wins", "Losses"),
                                                show="headings")
        for col in ("Player", "Team", "Wins", "Losses"):
            self.big_player_treeview.heading(col, text=col)
            self.big_player_treeview.column(col, anchor = "center")
        self.big_player_treeview.pack(fill="both", expand=True)

    
    def _on_team_right_click(self, event):
        selected_item = self.teams_treeview.identify_row(event.y)
        if not selected_item:
            return

        menu = tk.Menu(self.master, tearoff=0)
        menu.add_command(label="Delete Team", command=lambda: self._delete_selected_team_from_id(selected_item))
        menu.post(event.x_root, event.y_root)

    def _delete_selected_team_from_id(self, team_id):
        if team_id:
            success, message = self.manager.delete_team(team_id)
            if success:
                self.show_status_message(message)
                self.update_teams_treeview()
                self.update_players_treeview()
                self.update_tournament_tab()
            elif message != "cancelled":
                self.show_status_message(message, color="red")
    
    def show_status_message(self, message, duration_ms=1500, color="green"):
        """Displays a message in the status bar for a given duration."""
        if self.status_timeout_id:
            self.master.after_cancel(self.status_timeout_id)

        self.status_label.configure(text=message, text_color=color)
        self.status_timeout_id = self.master.after(duration_ms, self._clear_status_message)

    def _clear_status_message(self):
        """Clears the message from the status bar."""
        self.status_label.configure(text="", text_color="gray")
        self.status_timeout_id = None

    def _on_tab_change(self):
        """Updates the content of the currently selected tab."""
        
        selected_tab_text = self.notebook.get()

        if selected_tab_text == "Teams":
            self.update_teams_treeview()
            self.update_players_treeview()
            self.update_skill_levels_listbox()
            self.selected_team_id = None
        elif selected_tab_text == "Tournament":
            self.update_tournament_tab()
            self.refresh_team_comboboxes()
        elif selected_tab_text == "Leaderboards":
            self.update_leaderboards_tab()
        elif selected_tab_text == "History":
            self.update_history_tab()
            
    # --- Teams Tab Setup ---
    def _setup_teams_tab(self):
        # Frame for Team List
        team_list_frame = ctk.CTkFrame(self.teams_frame)
        team_list_frame.pack(side="left", fill="both", expand=True, padx=10, pady=5)

        ctk.CTkLabel(team_list_frame, text="Teams", font=ctk.CTkFont(size=15, weight="bold")).pack(pady=5)

        self.teams_treeview = ttk.Treeview(team_list_frame, columns=("Name", "Group"), show="headings")
        self.teams_treeview.heading("Name", text="Team Name")
        self.teams_treeview.heading("Group", text="Group")

        self.teams_treeview.column("Name", width=150, anchor="w")
        self.teams_treeview.column("Group", width=50, anchor="center")

        self.teams_treeview.heading("Name", text="Team Name")
        self.teams_treeview.column("Name", width=150, anchor="w")
        self.teams_treeview.pack(side="top", fill="both", expand=True, padx=5, pady=5)
        self.teams_treeview.bind("<<TreeviewSelect>>", self._on_team_select)
        self.teams_treeview.bind("<Button-3>", self._on_team_right_click)

        team_scroll = ttk.Scrollbar(team_list_frame, orient="vertical", command=self.teams_treeview.yview)
        team_scroll.pack(side="right", fill="y")
        self.teams_treeview.configure(yscrollcommand=team_scroll.set)

        team_buttons_frame = ctk.CTkFrame(team_list_frame, fg_color="transparent")
        team_buttons_frame.pack(side="bottom", fill="x", pady=5)

        ctk.CTkButton(team_buttons_frame, text="Add Team", command=self._open_add_team_dialog).pack(side="left", expand=True, padx=2)
        ctk.CTkButton(team_buttons_frame, text="Edit Team", command=self._open_edit_team_dialog).pack(side="left", expand=True, padx=2)
        ctk.CTkButton(team_buttons_frame, text="Delete Team", command=self._delete_selected_team).pack(side="left", expand=True, padx=2)

        player_skill_frame = ctk.CTkFrame(self.teams_frame, fg_color="transparent")
        player_skill_frame.pack(side="right", fill="both", expand=True, padx=10, pady=5)

        player_list_frame = ctk.CTkFrame(player_skill_frame)
        player_list_frame.pack(side="top", fill="both", expand=True, pady=5)

        self.players_label = ctk.CTkLabel(player_list_frame, text="Players (Select a Team)", font=ctk.CTkFont(size=15, weight="bold"))
        self.players_label.pack(pady=5)

        self.players_treeview = ttk.Treeview(player_list_frame, columns=("Name", "Skill"), show="headings", height = 7)
        self.players_treeview.heading("Name", text="Player Name")
        self.players_treeview.heading("Skill", text="Skill Level")
        self.players_treeview.column("Name", width=100, anchor="w")
        self.players_treeview.column("Skill", width=80, anchor="w")
        self.players_treeview.pack(side="top", fill="both", expand=True, padx=5, pady=5)
        self.players_treeview.bind("<<TreeviewSelect>>", self._on_player_select)

        player_scroll = ttk.Scrollbar(player_list_frame, orient="vertical", command=self.players_treeview.yview)
        player_scroll.pack(side="right", fill="y")
        self.players_treeview.configure(yscrollcommand=player_scroll.set)

        player_buttons_frame = ctk.CTkFrame(player_list_frame, fg_color="transparent")
        player_buttons_frame.pack(side="bottom", fill="x", pady=5)

        ctk.CTkButton(player_buttons_frame, text="Add Player", command=self._open_add_player_dialog).pack(side="left", expand=True, padx=2)
        ctk.CTkButton(player_buttons_frame, text="Edit Player", command=self._open_edit_player_dialog).pack(side="left", expand=True, padx=2)
        ctk.CTkButton(player_buttons_frame, text="Remove Player", command=self._remove_selected_player).pack(side="left", expand=True, padx=2)

        self.selected_team_id = None
        self.selected_player_id = None

        skill_level_frame = ctk.CTkFrame(player_skill_frame)
        skill_level_frame.pack(side="bottom", fill="x", pady=10)

        ctk.CTkLabel(skill_level_frame, text="Manage Skill Levels", font=ctk.CTkFont(size=15, weight="bold")).pack(pady=5)

        self.skill_levels_listbox = Listbox(skill_level_frame, height=5, font=('Arial', 10), selectmode="browse", borderwidth=0, highlightthickness=0)
        self.skill_levels_listbox.pack(fill="x", expand=False, padx=5, pady=5)

        self.skill_levels_listbox.config(
            bg=self.master._apply_appearance_mode(ctk.ThemeManager.theme["CTkFrame"]["fg_color"][0]),
            fg=self.master._apply_appearance_mode(ctk.ThemeManager.theme["CTkLabel"]["text_color"][0]),
            selectbackground=self.master._apply_appearance_mode(ctk.ThemeManager.theme["CTkButton"]["fg_color"][0]),
            selectforeground=self.master._apply_appearance_mode(ctk.ThemeManager.theme["CTkButton"]["text_color"][0]))

        skill_entry_frame = ctk.CTkFrame(skill_level_frame, fg_color="transparent")
        skill_entry_frame.pack(fill="x", pady=5)

        self.new_skill_entry = ctk.CTkEntry(skill_entry_frame, width=200)
        self.new_skill_entry.pack(side="left", expand=True, padx=2)
        ctk.CTkButton(skill_entry_frame, text="Add Skill", command=self._add_skill_level).pack(side="left", padx=2)
        ctk.CTkButton(skill_entry_frame, text="Remove Skill", command=self._remove_skill_level).pack(side="left", padx=2)

    def update_teams_treeview(self):
        """Updates the teams Treeview with current data."""
        for i in self.teams_treeview.get_children():
            self.teams_treeview.delete(i)
        for team_id, team_name in self.manager.get_all_teams():
            group = self.manager.get_team(team_id).get("group", "N/A")
            self.teams_treeview.insert("", "end", iid=team_id, values=(team_name, group))


    def _on_team_select(self, event):
        """Handles team selection in the Treeview."""
        selected_item = self.teams_treeview.focus()
        if selected_item:
            self.selected_team_id = selected_item
            team_name = self.teams_treeview.item(selected_item, 'values')[0]
            self.players_label.configure(text=f"Players for {team_name}")
            self.update_players_treeview()
        else:
            self.selected_team_id = None
            self.players_label.configure(text="Players (Select a Team)")
            self.update_players_treeview()

    def _delete_selected_team(self):
        """Deletes the currently selected team."""
        if self.selected_team_id:
            success, message = self.manager.delete_team(self.selected_team_id)
            if success:
                self.show_status_message(message)
                self.update_teams_treeview()
                self.update_players_treeview()
                self.update_tournament_tab()
                self.update_leaderboards_tab() 
            elif message != "cancelled":
                self.show_status_message(message, color="red")
        else:
            messagebox.showwarning("No Selection", "Please select a team to delete.")

    def update_players_treeview(self):
        """Updates the players Treeview for the selected team."""
        for i in self.players_treeview.get_children():
            self.players_treeview.delete(i)
        if self.selected_team_id:
            players = self.manager.get_players_for_team(self.selected_team_id)
            for player_id, name, skill in players:
                self.players_treeview.insert("", "end", iid=player_id, values=(name, skill))
        self.selected_player_id = None

    def _on_player_select(self, event):
        """Handles player selection in the Treeview."""
        selected_item = self.players_treeview.focus()
        if selected_item:
            self.selected_player_id = selected_item
        else:
            self.selected_player_id = None

    def _remove_selected_player(self):
        """Removes the currently selected player."""
        if self.selected_team_id and self.selected_player_id:
            success, message = self.manager.remove_player(self.selected_team_id, self.selected_player_id)
            if success:
                self.show_status_message(message)
                self.update_players_treeview()
                self.update_tournament_tab() # Player points might change
                self.update_leaderboards_tab() 
            elif message != "cancelled":
                self.show_status_message(message, color="red")
        else:
            messagebox.showwarning("No Selection", "Please select a player to remove.")

    def update_skill_levels_listbox(self):
        """Updates the skill levels Listbox."""
        self.skill_levels_listbox.delete(0, "end")
        for skill in self.manager.get_skill_levels():
            self.skill_levels_listbox.insert("end", skill)

    def _add_skill_level(self):
        """Adds a new skill level."""
        skill = self.new_skill_entry.get().strip()
        success, message = self.manager.add_skill_level(skill)
        if success:
            self.show_status_message(message)
            self.new_skill_entry.delete(0, "end")
            self.update_skill_levels_listbox()
        else:
            self.show_status_message(message, color="red")

    def _remove_skill_level(self):
        """Removes a selected skill level."""
        selected_indices = self.skill_levels_listbox.curselection()
        if selected_indices:
            selected_skill = self.skill_levels_listbox.get(selected_indices[0])
            success, message = self.manager.remove_skill_level(selected_skill)
            if success:
                self.show_status_message(message)
                self.update_skill_levels_listbox()
            elif message != "cancelled":
                self.show_status_message(message, color="red")
        else:
            messagebox.showwarning("No Selection", "Please select a skill level to remove.")

    def update_player_skill_comboboxes(self):
        """Helper to update skill level dropdowns in open dialogs."""
        self.update_skill_levels_listbox()

    # --- Dialogs for Team/Player Management ---
    def _open_add_team_dialog(self):
        """Opens a dialog to add a new team."""
        dialog = ctk.CTkToplevel(self.master)
        dialog.title("Add New Team")
        dialog.transient(self.master)
        dialog.grab_set()
        dialog.focus_set()
        dialog.resizable(False, False)

        frame = ctk.CTkFrame(dialog, corner_radius=10)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(frame, text="Team Name:", font=ctk.CTkFont(size=13, weight="bold")).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ctk.CTkLabel(frame, text="Group:", font=ctk.CTkFont(size=13, weight="bold")).grid(row=1, column=0, padx=5, pady=5, sticky="w")
        group_combobox = ctk.CTkComboBox(frame, values=["A", "B"], state="readonly", width=250)
        group_combobox.grid(row=1, column=1, padx=5, pady=5)
        group_combobox.set("A")

        team_name_entry = ctk.CTkEntry(frame, width=250)
        team_name_entry.grid(row=0, column=1, padx=5, pady=5)
        team_name_entry.focus_set()

        def add_team_action():
            name = team_name_entry.get().strip()
            group = group_combobox.get()
            team_id, message = self.manager.create_team(name, group)

            if team_id:
                self.show_status_message(message)
                self.update_teams_treeview()
                self.update_tournament_tab()
                self.refresh_team_comboboxes()
                self.update_leaderboards_tab() 
                dialog.destroy()
            else:
                self.show_status_message(message, color="red")

        ctk.CTkButton(frame, text="Create Team", command=add_team_action).grid(row=2, column=0, columnspan=2, pady=15)
        dialog.bind("<Return>", lambda event: add_team_action())

    def _open_edit_team_dialog(self):
        if not self.selected_team_id:
            messagebox.showwarning("No Selection", "Please select a team to edit.")
            return

        current_name = self.teams_treeview.item(self.selected_team_id, 'values')[0]
        current_group = self.manager.get_team(self.selected_team_id).get("group", "A")

        dialog = ctk.CTkToplevel(self.master)
        dialog.title(f"Edit Team: {current_name}")
        dialog.transient(self.master)
        dialog.grab_set()
        dialog.focus_set()
        dialog.resizable(False, False)

        frame = ctk.CTkFrame(dialog, corner_radius=10)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Team name
        ctk.CTkLabel(frame, text="New Team Name:", font=ctk.CTkFont(size=13, weight="bold")).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        new_name_entry = ctk.CTkEntry(frame, width=250)
        new_name_entry.insert(0, current_name)
        new_name_entry.grid(row=0, column=1, padx=5, pady=5)
        new_name_entry.focus_set()
        new_name_entry.select_range(0, "end")

        # Group
        ctk.CTkLabel(frame, text="Group:", font=ctk.CTkFont(size=13, weight="bold")).grid(row=1, column=0, padx=5, pady=5, sticky="w")
        group_combobox = ctk.CTkComboBox(frame, values=["A", "B"], state="readonly", width=250)
        group_combobox.set(current_group)
        group_combobox.grid(row=1, column=1, padx=5, pady=5)

        def update_team_action():
            new_name = new_name_entry.get().strip()
            new_group = group_combobox.get()

            name_success, name_msg = self.manager.update_team_name(self.selected_team_id, new_name)
            group_success, group_msg = self.manager.update_team_group(self.selected_team_id, new_group)

            if name_success or group_success:
                self.show_status_message("Team updated.")
                self.update_teams_treeview()
                self.update_tournament_tab()
                self.update_leaderboards_tab()
                dialog.destroy()
            else:
                self.show_status_message(name_msg if not name_success else group_msg, color="red")

        ctk.CTkButton(frame, text="Update Team", command=update_team_action).grid(row=2, column=0, columnspan=2, pady=15)
        dialog.bind("<Return>", lambda event: update_team_action())


    def _open_add_player_dialog(self):
        """Opens a dialog to add a new player to the selected team."""
        if not self.selected_team_id:
            messagebox.showwarning("No Team Selected", "Please select a team first to add a player.")
            return

        team_name = self.teams_treeview.item(self.selected_team_id, 'values')[0]
        skill_levels = self.manager.get_skill_levels()

        if not skill_levels:
            messagebox.showwarning("No Skill Levels",
                                   "Please add skill levels first in the 'Manage Skill Levels' section.")
            return

        dialog = ctk.CTkToplevel(self.master)
        dialog.title(f"Add Player to {team_name}")
        dialog.transient(self.master)
        dialog.grab_set()
        dialog.focus_set()
        dialog.resizable(False, False)

        frame = ctk.CTkFrame(dialog, corner_radius=10)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(frame, text="Player Name:", font=ctk.CTkFont(size=13, weight="bold")).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        player_name_entry = ctk.CTkEntry(frame, width=250)
        player_name_entry.grid(row=0, column=1, padx=5, pady=5)
        player_name_entry.focus_set()

        ctk.CTkLabel(frame, text="Skill Level:", font=ctk.CTkFont(size=13, weight="bold")).grid(row=1, column=0, padx=5, pady=5, sticky="w")

        skill_combobox = ctk.CTkComboBox(frame, values=skill_levels, state="readonly", width=250)
        skill_combobox.grid(row=1, column=1, padx=5, pady=5)
        skill_combobox.set(skill_levels[0])

        def add_player_action():
            name = player_name_entry.get().strip()
            skill = skill_combobox.get()
            success, message = self.manager.add_player(self.selected_team_id, name, skill)
            if success:
                self.show_status_message(message)
                self.update_players_treeview()
                self.update_tournament_tab() # Player points might change due to new player availability
                self.update_leaderboards_tab() 
                dialog.destroy()
            else:
                self.show_status_message(message, color="red")

        ctk.CTkButton(frame, text="Add Player", command=add_player_action).grid(row=2, column=0, columnspan=2, pady=15)
        dialog.bind("<Return>", lambda event: add_player_action())

    def _open_edit_player_dialog(self):
        """Opens a dialog to edit the selected player."""
        if not self.selected_team_id:
            messagebox.showwarning("No Team Selected", "Please select a team first.")
            return
        if not self.selected_player_id:
            messagebox.showwarning("No Player Selected", "Please select a player to edit.")
            return

        player_data = self.players_treeview.item(self.selected_player_id, 'values')
        current_name = player_data[0]
        current_skill = player_data[1]

        skill_levels = self.manager.get_skill_levels()
        if not skill_levels:
            messagebox.showwarning("No Skill Levels",
                                   "Please add skill levels first in the 'Manage Skill Levels' section.")
            return

        dialog = ctk.CTkToplevel(self.master)
        dialog.title(f"Edit Player: {current_name}")
        dialog.transient(self.master)
        dialog.grab_set()
        dialog.focus_set()
        dialog.resizable(False, False)

        frame = ctk.CTkFrame(dialog, corner_radius=10)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(frame, text="New Player Name:", font=ctk.CTkFont(size=13, weight="bold")).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        new_name_entry = ctk.CTkEntry(frame, width=250)
        new_name_entry.insert(0, current_name)
        new_name_entry.grid(row=0, column=1, padx=5, pady=5)
        new_name_entry.focus_set()
        new_name_entry.select_range(0, "end")

        ctk.CTkLabel(frame, text="New Skill Level:", font=ctk.CTkFont(size=13, weight="bold")).grid(row=1, column=0, padx=5, pady=5, sticky="w")

        skill_combobox = ctk.CTkComboBox(frame, values=skill_levels, state="readonly", width=250)
        skill_combobox.grid(row=1, column=1, padx=5, pady=5)
        skill_combobox.set(current_skill)

        def update_player_action():
            name = new_name_entry.get().strip()
            skill = skill_combobox.get()
            success, message = self.manager.update_player(self.selected_team_id, self.selected_player_id, name, skill)
            if success:
                self.show_status_message(message)
                self.update_players_treeview()
                self.update_tournament_tab() # Player points might change
                self.update_leaderboards_tab() 
                dialog.destroy()
            else:
                self.show_status_message(message, color="red")

        ctk.CTkButton(frame, text="Update Player", command=update_player_action).grid(row=2, column=0, columnspan=2, pady=15)
        dialog.bind("<Return>", lambda event: update_player_action())

    def refresh_team_comboboxes(self):
        teams = self.manager.get_all_teams()
        team_names_a = [t[1] for t in teams if self.manager.get_team(t[0]).get("group") == "A"]
        team_names_b = [t[1] for t in teams if self.manager.get_team(t[0]).get("group") == "B"]
        team_names_all = [t[1] for t in teams]

        if hasattr(self, 'group_a_team1_cb'):
            self.group_a_team1_cb.configure(values=team_names_a)
            self.group_a_team2_cb.configure(values=team_names_a)
        if hasattr(self, 'group_b_team1_cb'):
            self.group_b_team1_cb.configure(values=team_names_b)
            self.group_b_team2_cb.configure(values=team_names_b)
        if hasattr(self, 'mixed_team1_cb'):
            self.mixed_team1_cb.configure(values=team_names_all)
            self.mixed_team2_cb.configure(values=team_names_all)

    def _edit_selected_submatch(self, event, submatch_list, treeview):
        selected_item = treeview.identify_row(event.y)
        if not selected_item:
            return

        index = treeview.index(selected_item)
        submatch = submatch_list[index]

        # Simple edit dialog for scores
        dialog = ctk.CTkToplevel(self.master)
        dialog.title("Edit Sub Match")
        dialog.geometry("350x200")
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="Team 1 Score:").pack(pady=5)
        t1_entry = ctk.CTkEntry(dialog)
        t1_entry.insert(0, str(submatch.get("team1_score", 0)))
        t1_entry.pack(pady=5)

        ctk.CTkLabel(dialog, text="Team 2 Score:").pack(pady=5)
        t2_entry = ctk.CTkEntry(dialog)
        t2_entry.insert(0, str(submatch.get("team2_score", 0)))
        t2_entry.pack(pady=5)

        def save_changes():
            try:
                submatch["team1_score"] = int(t1_entry.get())
                submatch["team2_score"] = int(t2_entry.get())
            except ValueError:
                messagebox.showerror("Invalid Input", "Scores must be integers.")
                return

            # Reset winner_player_ids
            submatch["winner_player_ids"] = []

            if submatch["team1_score"] > submatch["team2_score"]:
                submatch["winner_player_ids"] = submatch.get("team1_player_ids", [])
            elif submatch["team2_score"] > submatch["team1_score"]:
                submatch["winner_player_ids"] = submatch.get("team2_player_ids", [])
            # Else it stays an empty list for a draw
            self._refresh_submatch_tree(treeview, submatch_list)
            dialog.destroy()


        ctk.CTkButton(dialog, text="Save", command=save_changes).pack(pady=10)

    def _on_submatch_right_click(self, event, submatch_list, treeview):
        selected_item = treeview.identify_row(event.y)
        if not selected_item:
            return

        menu = tk.Menu(self.master, tearoff=0)
        menu.add_command(label="Delete Sub Match", command=lambda: self._delete_submatch_from_tree(selected_item, submatch_list, treeview))
        menu.post(event.x_root, event.y_root)

    def _delete_submatch_from_tree(self, item, submatch_list, treeview):
        index = treeview.index(item)
        confirm = messagebox.askyesno("Confirm", "Delete this sub-match?")
        if confirm:
            del submatch_list[index]
            self._refresh_submatch_tree(treeview, submatch_list)


    def _create_group_submatch_section(self, parent_frame, group_name):
        section = ctk.CTkFrame(parent_frame)
        section.pack(fill="both", expand = True, padx=10, pady=15)
        section.grid_columnconfigure((0, 1, 2, 3), weight=1)
        section.grid_rowconfigure(3, weight=1)  # Make treeview row expand vertically too


        ctk.CTkLabel(section, text=f"Record Match - Group {group_name}", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, columnspan=4, pady=(5, 10))

        # Get teams in this group
        teams = [t for t in self.manager.get_all_teams() if self.manager.get_team(t[0]).get("group") == group_name]
        team_names = [t[1] for t in teams]
        team_id_map = {t[1]: t[0] for t in teams}

        # Team 1 selection
        ctk.CTkLabel(section, text="Team 1:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        if group_name == "A":
            self.group_a_team1_cb = ctk.CTkComboBox(section, values=team_names, state="readonly", width=200)
            team1_cb = self.group_a_team1_cb
        elif group_name == "B":
            self.group_b_team1_cb = ctk.CTkComboBox(section, values=team_names, state="readonly", width=200)
            team1_cb = self.group_b_team1_cb
        else:  # Mixed
            self.mixed_team1_cb = ctk.CTkComboBox(section, values=team_names, state="readonly", width=200)
            team1_cb = self.mixed_team1_cb
        team1_cb.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # Team 2 selection
        ctk.CTkLabel(section, text="Team 2:").grid(row=1, column=2, padx=5, pady=5, sticky="e")
        if group_name == "A":
            self.group_a_team2_cb = ctk.CTkComboBox(section, values=team_names, state="readonly", width=200)
            team2_cb = self.group_a_team2_cb
        elif group_name == "B":
            self.group_b_team2_cb = ctk.CTkComboBox(section, values=team_names, state="readonly", width=200)
            team2_cb = self.group_b_team2_cb
        else:  # Mixed
            self.mixed_team2_cb = ctk.CTkComboBox(section, values=team_names, state="readonly", width=200)
            team2_cb = self.mixed_team2_cb
        team2_cb.grid(row=1, column=3, padx=5, pady=5, sticky="w")


        # Buttons for adding sub-matches
        btn_frame = ctk.CTkFrame(section, fg_color="transparent")
        btn_frame.grid(row=2, column=0, columnspan=4, pady=10)

        def launch(match_type):
            if not team1_cb.get() or not team2_cb.get():
                messagebox.showerror("Missing Teams", "Please select both teams.")
                return
            if team1_cb.get() == team2_cb.get():
                messagebox.showerror("Invalid Match", "Teams must be different.")
                return

            self.temp_team1 = team1_cb.get()
            self.temp_team2 = team2_cb.get()
            teams = self.manager.get_all_teams()
            self.team_ids_map = {name: tid for tid, name in teams}

            if group_name == "A":
                self.active_submatch_list = self.group_a_sub_matches
                self.active_treeview = self.group_a_submatch_tree
            elif group_name == "B":
                self.active_submatch_list = self.group_b_sub_matches
                self.active_treeview = self.group_b_submatch_tree
            else:  # Mixed
                self.active_submatch_list = self.current_sub_matches
                self.active_treeview = self.current_sub_matches_treeview


            if match_type == "singles":
                self._open_add_singles_match_dialog()
            else:
                self._open_add_doubles_match_dialog()

        ctk.CTkButton(btn_frame, text="Add Singles Match", command=lambda: launch("singles")).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Add Doubles Match", command=lambda: launch("doubles")).pack(side="left", padx=10)

        # Treeview for current sub-matches
        tree = ttk.Treeview(section, columns=("Type", "Players", "Score", "Winner(s)"), show="headings")
        for col in ("Type", "Players", "Score", "Winner(s)"):
            tree.heading(col, text=col)
            tree.column(col, anchor="center")
        tree.grid(row=3, column=0, columnspan=4, sticky="nsew", padx=10, pady=10)

        if group_name == "A":
            self.group_a_submatch_tree = tree
        elif group_name == "B":
            self.group_b_submatch_tree = tree
        else:  # Mixed tab
            self.current_sub_matches_treeview = tree

        # Finalize & Clear buttons
        finalize_frame = ctk.CTkFrame(section, fg_color="transparent")
        finalize_frame.grid(row=4, column=0, columnspan=4, pady=5)

        if group_name == "A":
            self.group_a_submatch_tree = tree
            submatch_list = self.group_a_sub_matches
        elif group_name == "B":
            self.group_b_submatch_tree = tree
            submatch_list = self.group_b_sub_matches
        else:
            self.current_sub_matches_treeview = tree
            submatch_list = self.current_sub_matches

        tree.bind("<Button-3>", lambda event, sm_list=submatch_list, trv=tree: self._on_submatch_right_click(event, sm_list, trv))
        tree.bind("<Double-1>", lambda event, sm_list=submatch_list, trv=tree: self._edit_selected_submatch(event, sm_list, trv))
        def finalize():
            confirm = messagebox.askyesno("Confirm Finalization", "Are you sure you want to finalize this match? This action cannot be undone.")
            if not confirm:
                return
            t1 = team1_cb.get()
            t2 = team2_cb.get()
            submatches = (
                self.group_a_sub_matches if group_name == "A"
                else self.group_b_sub_matches if group_name == "B"
                else self.current_sub_matches
            )
            if group_name == "A":
                self.group_a_sub_matches = []
                self._refresh_submatch_tree(self.group_a_submatch_tree, [])
            elif group_name == "B":
                self.group_b_sub_matches = []
                self._refresh_submatch_tree(self.group_b_submatch_tree, [])
            else:
                self.current_sub_matches = []
                self._refresh_submatch_tree(self.current_sub_matches_treeview, [])


            if not t1 or not t2 or not submatches:
                messagebox.showwarning("Incomplete", "Please select teams and add at least one sub-match.")
                return

            teams = self.manager.get_all_teams()
            team_id_map = {name: tid for tid, name in teams}
            t1_id = team_id_map[t1]
            t2_id = team_id_map[t2]
            
            success, msg = self.manager.record_match(t1_id, t2_id, submatches)
            if success:
                self.push_player_leaderboards_to_google_sheet(
                    sheet_id="1MPAoCUNEgWIK9M7kGDWbcQsU_jp4OFaTb2m6XLm2IRg",
                    credentials_file="google-credentials.json"
                )
                self.push_data_to_google_sheet(
                    sheet_id="1MPAoCUNEgWIK9M7kGDWbcQsU_jp4OFaTb2m6XLm2IRg",
                    credentials_file="google-credentials.json"
                )

                self.show_status_message(msg)
                self.update_tournament_tab()

                if group_name == "A":
                    self.group_a_sub_matches = []
                    self._refresh_submatch_tree(self.group_a_submatch_tree, [])
                else:
                    self.group_b_sub_matches = []
                    self._refresh_submatch_tree(self.group_b_submatch_tree, [])
            else:
                self.show_status_message(msg, color="red")

        def clear():
            if group_name == "A":
                self.group_a_sub_matches = []
                self._refresh_submatch_tree(self.group_a_submatch_tree, [])
            else:
                self.group_b_sub_matches = []
                self._refresh_submatch_tree(self.group_b_submatch_tree, [])

        ctk.CTkButton(finalize_frame, text="Finalize Match", command=finalize).pack(side="left", padx=10)
        def clear_action():

            submatch_list = (
                self.group_a_sub_matches if group_name == "A"
                else self.group_b_sub_matches if group_name == "B"
                else self.current_sub_matches
            )
            if messagebox.askyesno("Confirm", "Are you sure you want to clear all sub-matches?"):
                submatch_list.clear()
                self._refresh_submatch_tree(tree, [])

        ctk.CTkButton(finalize_frame, text="Clear Sub Matches", command=clear_action).pack(side="left", padx=10)

    # --- Tournament Tab Setup ---
    def _setup_tournament_tab(self):
        # Create tab view inside Tournament Tab
        self.group_tabs = ctk.CTkTabview(self.tournament_frame)
        self.group_tabs.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_group_a = self.group_tabs.add("Group A")
        self.tab_group_b = self.group_tabs.add("Group B")
        self.tab_mixed = self.group_tabs.add("Mixed")

        self._create_group_submatch_section(self.tab_mixed, "Mixed")

        # Main Layout: Three columns for Standings, Player Leaderboard, Match History
        main_display_frame = ctk.CTkFrame(self.tab_mixed, fg_color="transparent")
        main_display_frame.pack(fill="both", expand=True, padx=10, pady=10)
        main_display_frame.grid_columnconfigure(0, weight=1)
        main_display_frame.grid_columnconfigure(1, weight=1)
        
        latest_match_frame = ctk.CTkFrame(main_display_frame)
        latest_match_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(latest_match_frame, text="Latest Recorded Match", font=ctk.CTkFont(size=15, weight="bold")).pack(pady=5)

        self.latest_match_label = ctk.CTkLabel(latest_match_frame, text="No matches yet.")
        self.latest_match_label.pack(pady=10)

                

        # Frame for Match History (now below Standings and Leaderboard)
        match_history_frame = ctk.CTkFrame(self.tournament_frame)
        match_history_frame.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(match_history_frame, text="Match History (Overall Team Results)", font=ctk.CTkFont(size=15, weight="bold")).pack(pady=5)

        self.match_history_treeview = ttk.Treeview(match_history_frame,
                                                   columns=("Date", "Team1", "Sub-Match Score", "Team2", "Overall Winner"),
                                                   show="headings")
        self.match_history_treeview.heading("Date", text="Date")
        self.match_history_treeview.heading("Team1", text="Team 1")
        self.match_history_treeview.heading("Sub-Match Score", text="Sub-Match Score")
        self.match_history_treeview.heading("Team2", text="Team 2")
        self.match_history_treeview.heading("Overall Winner", text="Overall Winner")

        self.match_history_treeview.column("Date", width=120, anchor="w")
        self.match_history_treeview.column("Team1", width=120, anchor="w")
        self.match_history_treeview.column("Sub-Match Score", width=100, anchor="center")
        self.match_history_treeview.column("Team2", width=120, anchor="w")
        self.match_history_treeview.column("Overall Winner", width=120, anchor="w")
        self.match_history_treeview.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        self.match_history_treeview.bind("<Button-3>", self._on_match_right_click)
        
        match_history_scroll = ttk.Scrollbar(match_history_frame, orient="vertical", command=self.match_history_treeview.yview)
        match_history_scroll.pack(side="right", fill="y")
        self.match_history_treeview.configure(yscrollcommand=match_history_scroll.set)

        

        self._create_group_submatch_section(self.tab_group_a, "A")
        self._create_group_submatch_section(self.tab_group_b, "B")


    def update_tournament_tab(self):
        self._update_match_history_treeview()
        self._update_current_sub_matches_treeview() # Clear pending sub-matches

    def _open_add_singles_match_dialog(self):
        self._open_sub_match_dialog("singles")

    def _open_add_doubles_match_dialog(self):
        self._open_sub_match_dialog("doubles")

    def push_data_to_google_sheet(self, sheet_id, credentials_file):
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(sheet_id)

        # Write to 'Sheet1'
        try:
            sheet = spreadsheet.worksheet("Sheet1")
        except gspread.exceptions.WorksheetNotFound:
            sheet = spreadsheet.add_worksheet(title="Sheet1", rows="100", cols="10")

        sheet.clear()

        standings_data = self.manager.calculate_standings()

        headers = ["Team", "Wins", "Losses", "Draws", "Played"]
        values = [headers] + [
            [team['name'], team['wins'], team['losses'], team['draws'], team['matches_played']]
            for team in standings_data
        ]
        sheet.update(values=values, range_name="A1")

    def push_player_leaderboards_to_google_sheet(self, sheet_id: str, credentials_file: str):
        """Exports the player leaderboards (with skill categories) into a single Google Sheet."""
        try:
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)
            client = gspread.authorize(creds)

            spreadsheet = client.open_by_key(sheet_id)
            try:
                sheet = spreadsheet.worksheet("Player Leaderboard")
            except gspread.exceptions.WorksheetNotFound:
                sheet = spreadsheet.add_worksheet(title="Player Leaderboard", rows="100", cols="10")
            sheet.clear()
            skill_levels = self.manager.get_skill_levels()
            if not skill_levels:
                self.show_status_message("No skill levels defined.", color="red")
                return

            player_data = self.manager.calculate_player_points()
            row_cursor = 1

            for skill in skill_levels:
                sheet.update(range_name=f"A{row_cursor}", values=[[f"----- {skill} -----"]])
                row_cursor += 1

                sheet.update(range_name=f"A{row_cursor}:E{row_cursor}", values=[["Player", "Team", "Wins", "Losses", "Played"]])
                row_cursor += 1

                filtered_players = []
                for team_id, team in self.manager.data['teams'].items():
                    for player_id, player in team['players'].items():
                        if player['skill'] == skill:
                            pdata = next((p for p in player_data if p['name'] == player['name']), {})
                            wins = pdata.get('wins', 0)
                            losses = pdata.get('losses', 0)
                            played = wins + losses
                            filtered_players.append([player['name'], team['name'], wins, losses, played])


                filtered_players.sort(key=lambda x: x[2], reverse=True)

                if filtered_players:
                    sheet.update(range_name=f"A{row_cursor}:E{row_cursor + len(filtered_players) - 1}", values=filtered_players)
                    row_cursor += len(filtered_players)
                else:
                    sheet.update(range_name=f"A{row_cursor}", values=[["No players."]])
                    row_cursor += 1

                row_cursor += 1  # spacing

            self.show_status_message("Player leaderboards pushed to Google Sheets")

        except Exception as e:
            self.show_status_message(f"Google Sheets leaderboard push failed: {e}", color="red")


    def _open_sub_match_dialog(self, match_type):
        """Opens a dialog to add a new singles or doubles sub-match."""
        selected_team1_name = self.temp_team1
        selected_team2_name = self.temp_team2   

        if not selected_team1_name or not selected_team2_name:
            messagebox.showwarning("Selection Error", "Please select both Team 1 and Team 2 first for the tournament match.")
            return
        if selected_team1_name == selected_team2_name:
            messagebox.showwarning("Invalid Teams", "Please select two different teams for the tournament match.")
            return

        team1_id = self.team_ids_map[selected_team1_name]
        team2_id = self.team_ids_map[selected_team2_name]
        
        team1_players = self.manager.get_players_for_team(team1_id)
        team2_players = self.manager.get_players_for_team(team2_id)

        if not team1_players:
            messagebox.showwarning("No Players", f"Team '{selected_team1_name}' has no players. Please add players first.")
            return
        if not team2_players:
            messagebox.showwarning("No Players", f"Team '{selected_team2_name}' has no players. Please add players first.")
            return
        if match_type == "doubles" and (len(team1_players) < 2 or len(team2_players) < 2):
            messagebox.showwarning("Not Enough Players", "Both teams need at least 2 players for a doubles match.")
            return

        player_options_t1 = [p[1] for p in team1_players] # (id, name, skill) -> name
        player_ids_map_t1 = {p[1]: p[0] for p in team1_players}

        player_options_t2 = [p[1] for p in team2_players]
        player_ids_map_t2 = {p[1]: p[0] for p in team2_players}

        dialog = ctk.CTkToplevel(self.master)
        dialog.title(f"Add {match_type.capitalize()} Sub-Match")
        dialog.transient(self.master)
        dialog.grab_set()
        dialog.focus_set()
        dialog.resizable(False, False)

        frame = ctk.CTkFrame(dialog, corner_radius=10)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Team 1 Players
        ctk.CTkLabel(frame, text=f"{selected_team1_name} Player(s):", font=ctk.CTkFont(size=13, weight="bold")).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        player1_t1_cb = ctk.CTkComboBox(frame, values=player_options_t1, state="readonly", width=180)
        player1_t1_cb.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        player1_t1_cb.set(player_options_t1[0])

        player2_t1_cb = None
        if match_type == "doubles":
            player2_t1_cb = ctk.CTkComboBox(frame, values=player_options_t1, state="readonly", width=180)
            player2_t1_cb.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
            player2_t1_cb.set(player_options_t1[1] if len(player_options_t1) > 1 else player_options_t1[0]) # Default to second player if exists


        # Team 2 Players (Opponents)
        ctk.CTkLabel(frame, text=f"{selected_team2_name} Opponent(s):", font=ctk.CTkFont(size=13, weight="bold")).grid(row=0, column=2, padx=5, pady=5, sticky="w")
        player1_t2_cb = ctk.CTkComboBox(frame, values=player_options_t2, state="readonly", width=180)
        player1_t2_cb.grid(row=0, column=3, padx=5, pady=5, sticky="ew")
        player1_t2_cb.set(player_options_t2[0])

        player2_t2_cb = None
        if match_type == "doubles":
            player2_t2_cb = ctk.CTkComboBox(frame, values=player_options_t2, state="readonly", width=180)
            player2_t2_cb.grid(row=1, column=3, padx=5, pady=5, sticky="ew")
            player2_t2_cb.set(player_options_t2[1] if len(player_options_t2) > 1 else player_options_t2[0])


        # Winner Selection
        
        def add_sub_match_action():
            try:
                score1 = int(team1_score_entry.get())
                score2 = int(team2_score_entry.get())
            except ValueError:
                messagebox.showerror("Invalid Input", "Scores must be integers.")
                return
            
            # Determine winner player IDs
            score1 = int(team1_score_entry.get())
            score2 = int(team2_score_entry.get())

            team1_ids = [player_ids_map_t1[player1_t1_cb.get()]]
            if match_type == "doubles":
                team1_ids.append(player_ids_map_t1[player2_t1_cb.get()])

            team2_ids = [player_ids_map_t2[player1_t2_cb.get()]]
            if match_type == "doubles":
                team2_ids.append(player_ids_map_t2[player2_t2_cb.get()])

            # Determine winner
            if score1 > score2:
                winner_ids = team1_ids
            elif score2 > score1:
                winner_ids = team2_ids
            else:
                winner_ids = []

            sub_match_data = {
                'type': match_type,
                'team1_player_ids': team1_ids,
                'team2_player_ids': team2_ids,
                'team1_score': score1,
                'team2_score': score2,
                'winner_player_ids': winner_ids
            }


            if hasattr(self, "active_submatch_list") and hasattr(self, "active_treeview"):
                self.active_submatch_list.append(sub_match_data)
                self._refresh_submatch_tree(self.active_treeview, self.active_submatch_list)
            else:
                self.current_sub_matches.append(sub_match_data)
                self._refresh_submatch_tree(self.current_sub_matches_treeview, self.current_sub_matches)

            self.show_status_message(f"{match_type.capitalize()} match added to current tournament match!", color="orange")
            dialog.destroy()

            
        # Score inputs
        score_row = 3 if match_type == "doubles" else 2

        ctk.CTkLabel(frame, text="Team 1 Score:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        team1_score_entry = ctk.CTkEntry(frame, width=100)
        team1_score_entry.grid(row=score_row, column=1, padx=5, pady=5)

        ctk.CTkLabel(frame, text="Team 2 Score:").grid(row=2, column=2, padx=5, pady=5, sticky="w")
        team2_score_entry = ctk.CTkEntry(frame, width=100)
        team2_score_entry.grid(row=score_row, column=3, padx=5, pady=5)

        ctk.CTkButton(frame, text="Add Sub-Match", command=add_sub_match_action).grid(row=4, column=0, columnspan=4, pady=15)

        # Update combobox options dynamically when other comboboxes change for doubles
        if match_type == "doubles":
            def update_player_comboboxes(event=None):
                selected_p1_t1 = player1_t1_cb.get()
                selected_p2_t1 = player2_t1_cb.get()
                selected_p1_t2 = player1_t2_cb.get()
                selected_p2_t2 = player2_t2_cb.get()

                # Update Team 1 secondary player options
                temp_options_t1 = [p for p in player_options_t1 if p != selected_p1_t1]
                player2_t1_cb.configure(values=temp_options_t1)
                if selected_p2_t1 == selected_p1_t1 and temp_options_t1: # If duplicate, reset to first available non-duplicate
                    player2_t1_cb.set(temp_options_t1[0])
                elif not temp_options_t1: # If only one player left, clear secondary combobox
                    player2_t1_cb.set('')

                # Update Team 2 secondary player options
                temp_options_t2 = [p for p in player_options_t2 if p != selected_p1_t2]
                player2_t2_cb.configure(values=temp_options_t2)
                if selected_p2_t2 == selected_p1_t2 and temp_options_t2:
                    player2_t2_cb.set(temp_options_t2[0])
                elif not temp_options_t2:
                    player2_t2_cb.set('')


            player1_t1_cb.bind("<<ComboboxSelected>>", update_player_comboboxes)
            player2_t1_cb.bind("<<ComboboxSelected>>", update_player_comboboxes)
            player1_t2_cb.bind("<<ComboboxSelected>>", update_player_comboboxes)
            player2_t2_cb.bind("<<ComboboxSelected>>", update_player_comboboxes)
            update_player_comboboxes() # Initial call to set correct values

    def _update_current_sub_matches_treeview(self):
        for i in self.current_sub_matches_treeview.get_children():
            self.current_sub_matches_treeview.delete(i)

        if not self.current_sub_matches:
            self.current_sub_matches_treeview.insert("", "end", values=("", "No sub-matches added yet", "", ""))
            return

        for idx, sub_match in enumerate(self.current_sub_matches):
            team1_players_names = [self.manager.get_player_name(pid) for pid in sub_match['team1_player_ids']]
            team2_players_names = [self.manager.get_player_name(pid) for pid in sub_match['team2_player_ids']]
            
            participants_str = f"{', '.join(team1_players_names)} vs {', '.join(team2_players_names)}"

            # New: score display
            score_str = f"{sub_match.get('team1_score', 0)} - {sub_match.get('team2_score', 0)}"

            winner_names = [self.manager.get_player_name(pid) for pid in sub_match['winner_player_ids']]
            winner_str = ', '.join(winner_names) if winner_names else 'Draw'

            self.current_sub_matches_treeview.insert(
                "", "end", iid=f"sub_match_{idx}",
                values=(sub_match['type'].capitalize(), participants_str, score_str, winner_str)
            )


    def _clear_current_sub_matches(self):
        """Clears the list of sub-matches being assembled."""
        if messagebox.askyesno("Confirm Clear", "Are you sure you want to clear all pending sub-matches?"):
            self._update_current_sub_matches_treeview()
            self.show_status_message("Pending sub-matches cleared.", color="orange")

    def _on_match_right_click(self, event):
        selected_item = self.match_history_treeview.identify_row(event.y)
        if not selected_item:
            return

        menu = tk.Menu(self.master, tearoff=0)
        menu.add_command(label="Delete Match", command=lambda: self._delete_match(selected_item))
        menu.post(event.x_root, event.y_root)
        
    def _delete_match(self, match_id):
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this match? This cannot be undone."):
            success, message = self.manager.delete_match(match_id)
            if success:
                self.show_status_message(message)
                self.update_tournament_tab()
                self.update_leaderboards_tab() 
            else:
                self.show_status_message(message, color="red")

    def _update_match_history_treeview(self):
        """Updates the match history Treeview with current data."""
        for i in self.match_history_treeview.get_children():
            self.match_history_treeview.delete(i)

        match_history_data = self.manager.get_match_history()
        if not match_history_data:
            self.match_history_treeview.insert("", "end", values=("", "No matches recorded yet", "", "", ""))
            return

        for match in match_history_data:
            self.match_history_treeview.insert("", "end", iid=match['id'], values=(
                match['date'],
                match['team1_name'],
                match['score'], # This is now sub-match score (e.g., "3-2")
                match['team2_name'],
                match['winner_name'] # Overall team winner
            ))


# --- Main Application Execution ---
if __name__ == "__main__":
    root = ctk.CTk()
    app = TournamentApp(root)
    root.mainloop()