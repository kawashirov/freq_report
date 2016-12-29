#!/bin/sh

while true; do
	while read line; do
		if [ "x$line" != "x" ]; then
			data="$(date +%s):$line"
			rrdtool update /root/freq_report/freq.rrd "$data"
			echo "$? - $data"
		fi
	done < '/dev/ttyUSB0'
	sleep 10
done
