#!/bin/bash
# Re-playes the game by parsing it from a web page such as http://ai-contest.com/visualizer.php?game_id=4607884
# pass game URL as a parameter to this script

python parse_game_state_url.py $1 | python MyBot.py --log MyBot.log

