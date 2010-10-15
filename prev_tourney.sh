#!/bin/bash
    for file in MyBot_111_*.py

    do
       player_1_counter=0
       player_1_turn_counter=0
       
       player_2_counter=0
       player_2_turn_counter=0

       draw_counter=0
       
       maps_played=0
       
       echo "Bot: $file"
       for i in {1..100}
       do
          RES=`java -jar tools/PlayGame.jar maps/map$i.txt 10000 200 log$i.txt "python MyBot_105.py" "python $file" 2>&1 | tail -n 3 | grep "Turn\|Player"`

          TURN=`echo $RES | grep -i turn | sed 's/.*urn \([0-9]*\).*/\1/'`

          RES2=`echo $RES | grep -i player | sed 's/.*ayer \([0-9]*\).*/\1/'`

          if [ "$RES2" = "1" ] ; then
             player_1_counter=`expr $player_1_counter + 1`
             player_1_turn_counter=`expr $player_1_turn_counter + $TURN`
          else 
             if [ "$RES2" = "2" ] ; then
                player_2_counter=`expr $player_2_counter + 1`
                player_2_turn_counter=`expr $player_2_turn_counter + $TURN`
             else
                draw_counter=`expr $draw_counter + 1`
             fi
          fi
          
          maps_played=`expr $maps_played + 1`
          echo "map: $i - Winner: $RES2 - Turns: $TURN"
          sleep 1
       done
       if [ "$player_2_counter" != "0" ] ; then
	  avg_player_2_turn_counter=`expr $player_2_turn_counter / $player_2_counter`
       fi
       if [ "$player_1_counter" != "0" ] ; then
	  avg_player_1_turn_counter=`expr $player_1_turn_counter / $player_1_counter`
       fi

       
       echo "won against $file : $player_2_counter/$maps_played, avg turns: $avg_player_2_turn_counter"
       echo "lost against $file : $player_1_counter/$maps_played, avg turns: $avg_player_1_turn_counter"
       echo "tied against $file : $draw_counter/$maps_played"
    done
