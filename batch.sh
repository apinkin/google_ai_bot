#!/bin/bash
    for file in example_bots/Du*Bot.jar

    do
       player_1_counter=0
       player_1_turn_counter=0
       
       player_2_counter=0
       player_2_turn_counter=0
       
       maps_played=0
       
       echo "Bot: $file"
       for i in {1..10}
       do
          RES=`java -jar tools/PlayGame.jar maps/map$i.txt 200 200 log.txt "java -jar $file" "python MyBot.py --log 1.log" 2>&1 | tail -n 3 | grep "Turn\|Player"`

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
          echo "map: $i - Winner: $RES2 - Turns: $TURN"
       done
       if [ "$player_2_counter" != "0" ] ; then
	  avg_player_2_turn_counter=`expr $player_2_turn_counter / $player_2_counter`
       fi
       if [ "$player_1_counter" != "0" ] ; then
	  avg_player_1_turn_counter=`expr $player_1_turn_counter / $player_1_counter`
       fi

       
       echo "won against $file : $player_2_counter/$maps_played, avg turns: $avg_player_2_turn_counter"
       echo "lost against $file lost : $player_1_counter/$maps_played, avg turns: $avg_player_1_turn_counter"
    done
