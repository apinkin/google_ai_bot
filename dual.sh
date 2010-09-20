#!/bin/bash
# pass map # as a parameter, for instance dual.sh 1
java -jar tools/PlayGame.jar maps/map$1.txt 200 200 log.txt "java -jar example_bots/DualBot.jar" "python MyBot.py --log 1.log" | python visualizer/visualize_localy.py 
