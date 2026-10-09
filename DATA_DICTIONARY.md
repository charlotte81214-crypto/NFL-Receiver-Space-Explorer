# Data Documentation

> This file contains the original dataset documentation supplied with the
> NFL Big Data Bowl competition. It is reproduced here unchanged so that
> README.md can serve as the project entry point.

## Description

Here, you'll find a summary of each data set for this competition, a list of *key* variables to join on, and a description of each variable. The tracking data is provided by the NFL Next Gen Stats team. The Scouting data is provided by [Pro Football Focus](https://www.pff.com/).

This competition allows participants to use supplemental NFL data as long as it is free and publicly available to all participants. Examples of sources that could be used include [nflverse](https://nflverse.nflverse.com/) and [Pro Football Reference](https://www.pro-football-reference.com/). Please note that the `gameId` and `playId` of the Big Data Bowl data merge with the `old_game_id` and `play_id` of nflverse's play-by-play data.

## File descriptions

Game data: The `games.csv` contains the teams playing in each game. The *key* variable is **`gameId`**.

Play data: The `plays.csv` file contains play-level information from each game. The *key* variables are **`gameId`** and **`playId`**.

Player data: The `players.csv` file contains player-level information from players that participated in any of the tracking data files. The *key* variable is **`nflId`**.

PFF Scouting data: The `pffScoutingData.csv` file contains player-level scouting information for each game and play. The *key* variables are **`gameId`**, **`playId`**, and **`nflId`**.

Tracking data: Files `tracking_[gameId].csv` contain player tracking data from season `[gameId]`. The *key* variables are **`gameId`**, **`playId`**, and **`nflId`**.

## Game data

- **`gameId`**: Game identifier, unique (numeric)
- `season`: Season of game
- `week`: Week of game
- `gameDate`: Game Date (time, mm/dd/yyyy)
- `gameTimeEastern`: Start time of game (time, HH:MM:SS, EST)
- `homeTeamAbbr`: Home team three-letter code (text)
- `visitorTeamAbbr`: Visiting team three-letter code (text)

## Play data

- **`gameId`**: Game identifier, unique (numeric)
- **`playId`**: Play identifier, not unique across games (numeric)
- `playDescription`: Description of play (text)
- `quarter`: Game quarter (numeric)
- `down`: Down (numeric)
- `yardsToGo`: Distance needed for a first down (numeric)
- `possessionTeam`: Team abbr of team on offense with possession of ball (text)
- `defensiveTeam`: Team abbr of team on defense (text)
- `yardlineSide`: 3-letter team code corresponding to line-of-scrimmage (text)
- `yardlineNumber`: Yard line at line-of-scrimmage (numeric)
- `gameClock`: Time on clock of play (MM:SS)
- `preSnapHomeScore`: Home score prior to the play (numeric)
- `preSnapVisitorScore`: Visiting team score prior to the play (numeric)
- `passResult`: Dropback outcome of the play (`C`: Complete pass, `I`: Incomplete pass, `S`: Quarterback sack, `IN`: Intercepted pass, `R`: Scramble, text)
- `penaltyYards`: yards gained by offense by penalty (numeric)
- `prePenaltyPlayResult`: Net yards gained by the offense, before penalty yardage (numeric)
- `playResult`: Net yards gained by the offense, including penalty yardage (numeric)
- `foulName[i]`: Name of the i-th penalty committed during the play. i ranges between 1 and 3 (text)
- `foulNFLId[i]`: `nflId` of the player who committed the i-th penalty during the play. i ranges between 1 and 3 (numeric)
- `absoluteYardlineNumber`: Distance from end zone for possession team (numeric)
- `offenseFormation`: Formation used by possession team (text)
- `personnelO`: Personnel used by offensive team (text)
- `defendersInBox`: Number of defenders in close proximity to line-of-scrimmage (numeric)
- `personnelD`: Personnel used by defensive team (text)
- `dropBackType`: Dropback categorization of quarterback (text)
- `pff_playAction`: indicator for whether offense executes play action fake on the play. Variable provided by PFF (binary)
- `pff_passCoverage`: Coverage scheme of defense. Variable provided by PFF (text)
  - Possible values:
    - `Cover-0`: Man to Man coverage with no deep defenders, typically with a blitz
    - `Cover-1`: Man defense with a single high safety
    - `Cover-2`: Two deep safeties with zone principles
    - `2-Man`: Two deep safeties with man principles
    - `Cover-3`: Three deep, four under concept
    - `Quarters`: Four deep, three under concept
    - `Cover-6`: Quarters on one half, Cover-2 on the other
    - `Bracket`: In/out bracket by two defenders on two offensive players
    - `Goal Line`: Goal line defense
    - `Red Zone`: Red zone specific calls
    - `Prevent`: End-of-half or end-of-game prevent defense
    - `Miscellaneous`: Coverage concepts that do not fit other categories
- `pff_passCoverageType`: Whether defense's coverage type was man, zone or other. Variable provided by PFF (text)

## Player data

- **`nflId`**: Player identification number, unique across players (numeric)
- `height`: Player height (text)
- `weight`: Player weight (numeric)
- `birthDate`: Date of birth (YYYY-MM-DD)
- `collegeName`: Player college (text)
- `officialPosition`: Official player position (text)
- `displayName`: Player name (text)

## PFF Scouting data

- **`gameId`**: Game identifier, unique (numeric)
- **`playId`**: Play identifier, not unique across games (numeric)
- **`nflId`**: Player identification number, unique across players (numeric)
- `pff_role`: The player's role on this play (text)
  - Possible values:
    - `Coverage`: Defensive player in man or zone coverage
    - `Pass`: Offensive player identified as the passer
    - `Pass block`: Offensive player blocking a defender from the QB
    - `Pass route`: Offensive player running a route (not blocker or passer)
    - `Pass rush`: Defensive player whose initial intent is to rush the passer
- `pff_positionLinedUp`: Position aligned at the snap (text)
- `pff_hit`: Defensive player credited with a hit on this play (binary)
- `pff_hurry`: Defensive player credited with a hurry on this play (binary)
- `pff_sack`: Defensive player credited with a sack on this play (binary)
- `pff_beatenByDefender`: Blocking player beaten by a defender without yielding hit/hurry/sack (binary)
- `pff_hitAllowed`: Blocking player responsible for a hit on the QB (binary)
- `pff_hurryAllowed`: Blocking player responsible for a hurry on the QB (binary)
- `pff_sackAllowed`: Blocking player responsible for a sack on the QB (binary)
- `pff_nflIdBlockedPlayer`: nflId of the first defender the offensive player blocked (numeric)
- `pff_blockType`: Type of block executed (text) — values include BH, CH, CL, NB, PA, PP, PR, PT, PU, SR, SW, UP
- `pff_backFieldBlock`: Block occurred in the offensive backfield (binary)

## Tracking data

Files `tracking/tracking_[gameId].csv` contain player and ball tracking data, one file per game (122 games across Weeks 1–8). To filter by week, join `gameId` to `week` in `games.csv`.

- **`gameId`**: Game identifier, unique (numeric)
- **`playId`**: Play identifier, not unique across games (numeric)
- **`nflId`**: Player identification number; NA on ball rows (numeric)
- `frameId`: Frame identifier for each play, starting at 1 (numeric)
- `time`: Time stamp of play (yyyy-mm-dd hh:mm:ss)
- `jerseyNumber`: Jersey number of player (numeric)
- `team`: Team abbreviation; value is `football` on ball rows (text)
- `playDirection`: Direction the offense is moving (left or right)
- `x`: Player position along the long axis of the field, 0–120 yards (numeric)
- `y`: Player position along the short axis of the field, 0–53.3 yards (numeric)
- `s`: Speed in yards/second (numeric)
- `a`: Acceleration in yards/second² (numeric)
- `dis`: Distance traveled from prior time point, in yards (numeric)
- `o`: Player orientation, 0–360 degrees (numeric)
- `dir`: Angle of player motion, 0–360 degrees (numeric)
- `event`: Tagged play event (ball_snap, pass_forward, pass_arrived, etc.) (text)

> **Frame rate:** The dataset README does not document a frame rate (fps).
> Frame numbers are used throughout this project; no conversion to seconds
> is applied.

![Figure 1: Field coordinates, direction, and orientation](https://www.googleapis.com/download/storage/v1/b/kaggle-user-content/o/inbox%2F3258%2F820e86013d48faacf33b7a32a15e814c%2FIncreasing%20Dir%20and%20O.png?generation=1572285857588233&alt=media)
