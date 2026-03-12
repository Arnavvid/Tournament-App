# Tournament Management App

A desktop **Tournament Management Application** built with **Python, CustomTkinter, and Tkinter** for managing teams, players, matches, and tournament standings.

The application allows organizers to track teams, record matches with detailed sub-match results, generate standings, and maintain player leaderboards.

---

# Features

## Team Management
- Create teams
- Assign teams to **Group A or Group B**
- Edit team name or group
- Delete teams and associated matches
- View all teams in a structured table

## Player Management
- Add players to teams
- Assign skill levels
- Edit player information
- Remove players from teams
- Prevent duplicate players within the same team

## Skill Level System
- Create custom skill levels
- Remove skill levels
- Prevent deletion if players use that skill

## Match Recording
- Record matches between two teams
- Supports **sub-matches**
- Track individual player participation
- Record scores for each sub-match
- Automatically determine match winner

### Match Types
- Singles
- Doubles

## Google Sheets Integration

The application supports syncing tournament data with **Google Sheets** using the `gspread` library and a Google Service Account.

This allows tournament results and leaderboards to be exported to a shared spreadsheet for easier viewing and sharing.

### Features

- Push tournament standings to Google Sheets
- Push player leaderboard data
- Automatically update spreadsheet data
- Clear spreadsheet data directly from the app

### Setup

1. Create a **Google Cloud Project**
2. Enable the **Google Sheets API**
3. Create a **Service Account**
4. Download the **credentials JSON file**

Example file:

```
credentials.json
```

5. Share your Google Sheet with the service account email.

Example:

```
my-service-account@project-id.iam.gserviceaccount.com
```

6. Add the configuration in `config.json`

```
{
  "google_sheet_id": "YOUR_GOOGLE_SHEET_ID",
  "credentials_file": "credentials.json"
}
```

### Required Libraries

```
pip install gspread
pip install oauth2client
```

### Clearing Sheet Data

The **Settings tab** includes an option to:

```
Clear Google Sheet Data
```

This clears the following worksheets:

- `Sheet1`
- `Player Leaderboard`



## Leaderboards

### Team Standings
Automatically calculated based on:
- Wins
- Losses
- Draws
- Matches played

### Player Leaderboard
Tracks individual player statistics:
- Wins
- Losses

Supports filtering by:
- Skill level
- Group

## Match History
- View all previous matches
- Filter matches by group
- Double-click to view **detailed match breakdown**
- Shows sub-match results and player winners

## Data Persistence
Tournament data is stored in:

```
tournament_data.json
```

Includes:
- Teams
- Players
- Matches
- Skill levels

## Import / Export
- Export tournament data to JSON
- Import tournament data from JSON
- Reset tournament data

## Google Sheets Integration
Supports clearing leaderboard data from Google Sheets using:

- `gspread`
- `Google Service Account Credentials`

---

# Tech Stack

- **Python**
- **CustomTkinter** (modern Tkinter UI)
- **Tkinter**
- **gspread**
- **OAuth2Client**
- **JSON data storage**

---

# Installation

## 1. Clone the Repository

```bash
git clone https://github.com/yourusername/tournament-management-app.git
cd tournament-management-app
```

## 2. Install Dependencies

```bash
pip install customtkinter
pip install gspread
pip install oauth2client
```

---

# Running the Application

```bash
python tttourney_app.py
```

---

### Important Files

| File | Purpose |
|-----|------|
| `tttourney_app.py` | Main application |
| `tournament_data.json` | Stores teams, players, matches |
| `config.json` | Stores Google Sheets configuration |
| `credentials.json` | Google API service account credentials |

---

# Application Tabs

## Teams
Manage:
- Teams
- Players
- Skill levels

## Tournament
Record matches and sub-matches.

## Leaderboards
Displays:
- Team standings
- Player rankings

## History
Shows:
- Match history
- Detailed match statistics

## Settings
Includes:
- Export tournament data
- Import tournament data
- Reset tournament
- Clear Google Sheets data

---

# Data Model

## Teams

```
Team
 ├── id
 ├── name
 ├── group
 └── players
```

## Players

```
Player
 ├── id
 ├── name
 └── skill_level
```

## Matches

```
Match
 ├── team1_id
 ├── team2_id
 ├── sub_matches
 ├── timestamp
 ├── winner
 └── scores
```

---

# Requirements

- Python 3.9+
- customtkinter
- gspread
- oauth2client

---

# License

MIT License
