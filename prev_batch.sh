#!/usr/bin/bash
    for file in MyBot_7.py

    do
       player_1_counter=0
       player_1_turn_counter=0
       
       player_2_counter=0
       player_2_turn_counter=0
       
       maps_played=0
       
       echo "Bot: $file"
       for i in {1..100}
       do
          RES=`java -jar tools/PlayGame.jar maps/map$i.txt 200 200 log.txt "python $file" "python MyBot.py" 2>&1 | tail -n 3 | grep "Turn\|Player"`

          TURN=`echo $RES | grep -i turn | sed 's/.*urn \([0-9]*\).*/\1/'`

          RES2=`echo $RES | grep -i player | sed 's/.*ayer \([0-9]*\).*/\1/'`

          if [ "$RES2" = "1" ] ; then
             player_1_counter=`expr $player_1_counter + 1`
             player_1_turn_counter=`expr $player_1_turn_counter + $TURN`

          else
             player_2_counter=`expr $player_2_counter + 1`
             player_2_turn_counter=`expr $player_2_turn_counter + $TURN`
          fi
          
          maps_played=`expr $maps_played + 1`

          echo "Map played: $i --- Winner: $RES2"
       done
       player_2_turn_counter=`expr $player_2_turn_counter / $maps_played`
       player_1_turn_counter=`expr $player_1_turn_counter / $maps_played`
       
       echo "won against $file : $player_2_counter/$maps_played, avg turns: $player_2_turn_counter"
       echo "lost against $file lost : $player_1_counter/$maps_played, avg turns: $player_1_turn_counter"
    done