q#!/bin/bash
# pass map # as a parameter, for instance dual.sh 1
rm current.log
java -jar tools/PlayGame.jar maps/map$1.txt 1000 200 log.txt "java -jar example_bots/RageBot.jar" "python MyBot.py --log current.log" | python visualizer/visualize_localy.py 
