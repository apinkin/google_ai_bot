#!/bin/bash
for i in {1..1000}
do
  java TCP zeroviz.us 995 "rebelxt$1" "python MyBot_$1.py --log MyBot_$1.log" "10000"
  sleep $(( $RANDOM % 15 ))
done
