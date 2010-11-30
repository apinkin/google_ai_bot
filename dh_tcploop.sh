#!/bin/bash
for i in {1..1000}
do
  java TCP 72.44.46.68 995 "rebelxt$1" "python MyBot_$1.py --log MyBot_$1_dh.log" "10000"
  sleep $(( $RANDOM % 31 ))
done

