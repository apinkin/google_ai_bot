#!/bin/bash
# this scripts runs your bot using TCP server
# change your nickname - i.e. testbot123
java TCP "213.3.30.106" "9999" "testbot123" "python MyBot.py --log MyBot.log" "10000"
killall python
