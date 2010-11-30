#!/bin/bash

rm current.log
java -jar tools/PlayGame.jar maps/map_finals-2_$1.txt 10000 200 log.txt "antimatroid/antima" "python MyBot_218.py" | python visualizer/visualize_localy.py 
