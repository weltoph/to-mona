#!/bin/bash

monafile=$1

monaoutput=$( { time mona "${monafile}" &>/dev/null; } 2>&1 )
monatime=$(echo ${monaoutput} | awk '{print $2}' | sed "s/0m//")

echo ${monatime}
