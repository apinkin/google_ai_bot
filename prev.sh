#!/bin/bash

java -jar tools/PlayGame.jar maps/map$1.txt 10000 200 log.txt "python MyBot_82.py --log old.log" "python MyBot.py --log current.log" | python visualizer/visualize_localy.py 