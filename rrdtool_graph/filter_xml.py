#!/usr/bin/env python3
import argparse, re, sys

if __name__ == '__main__':
	args = argparse.ArgumentParser()
	args.add_argument('input_xml', type=argparse.FileType('r'))
	args.add_argument('blacklist', type=argparse.FileType('r'))
	args.add_argument('output_xml', type=argparse.FileType('w'))

	args = args.parse_args()

	blacklist = list()

	while True:
		line = args.blacklist.readline()
		if line == '': break
		try:
			line = re.sub(r'#.*', '', line) # replace #comments
			search = re.search(r'([0-9]+):([0-9]+)', line)
			blacklist.append(( int(search.group(1)), int(search.group(2)) ))
		except Exception as e:
			print(e)

	blacklisted = 0
	while True:
		line = args.input_xml.readline()
		if line == '': break
		try:
			search_time = re.search(r' / ([0-9]+) -->', line)
			if search_time is not None:
				time = int(search_time .group(1))
				time_blacklisted = False
				for begin, end in blacklist:
					if begin <= time and time <= end: 
						# print('Blacklisting {} for {}:{}'.format(time, begin, end))
						time_blacklisted = True
						break
				if time_blacklisted:
					blacklisted += 1
					line = re.sub(r'<v>[^<>]+</v>', r'<v> NaN </v>', line)
		except Exception as e:
			print(e)
		args.output_xml.write(line)

	print('Blacklisted {} lines.'.format(blacklisted), file=sys.stderr)
