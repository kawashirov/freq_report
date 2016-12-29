#!/usr/bin/env python3
import sys, os, io, re, pathlib, subprocess, argparse

LENGTH_MINUTE = 60
LENGTH_HOUR = LENGTH_MINUTE * 60
LENGTH_DAY = LENGTH_HOUR * 24
LENGTH_WEEK = LENGTH_DAY * 7
LENGTH_MONTH = LENGTH_DAY * 31
LENGTH_YEAR = LENGTH_DAY * 365


def assert_t(arg, t):
	assert isinstance(arg, t)
	return arg

def humanize_time(time):
	humanized = list()
	if time >= LENGTH_YEAR:
		humanized.append(str(time // LENGTH_YEAR) + 'г.')
		time %= LENGTH_YEAR
	if time >= LENGTH_DAY:
		humanized.append(str(time // LENGTH_DAY) + 'д.')
		time %= LENGTH_DAY
	if time >= LENGTH_HOUR:
		humanized.append(str(time // LENGTH_HOUR) + 'ч.')
		time %= LENGTH_HOUR
	if time >= LENGTH_MINUTE:
		humanized.append(str(time // LENGTH_MINUTE) + 'м.')
		time %= LENGTH_MINUTE
	if time > 0:
		humanized.append(str(time) + 'с.')
	return ' '.join(humanized)

def esc_colon(text):
	return text.replace(':', '\\:')

def comment(text):
	return 'COMMENT:' + esc_colon(text)

def comment_header(text, bold=True, extra_text=None, endline=True):
	s = ''
	if bold: s += '<b>'
	s += '# ' + str(text)
	if bold: s += '</b>'
	if extra_text: s += ' ' + str(extra_text)
	if endline: s += '\\n'
	return comment(s)

def comment_notice_errors(errors_percent):
	return comment(
		'{}% наименьших и наибольших значений считаются ошибками и шумом, они отбрасываются и не учитваются.\\n'
			.format(errors_percent)
	),

def cdef_avg(to_vname, expr_list):
	assert isinstance(expr_list, list)
	assert len(expr_list) > 0
	return 'CDEF:{0}='.format(to_vname) + ','.join(expr_list + [str(len(expr_list)), 'AVG'])

# Делает цепочку: expr,expr,f,expr,f, ..., expr,f
def cdef_f_chain(to_vname, function, expr_list):
	l = len(expr_list)
	assert isinstance(expr_list, list)
	assert l > 0
	if l == 1: return expr_list[0]
	expr = 'CDEF:' + to_vname + '=' + str(expr_list.pop(0))
	for var in expr_list:
		expr += ',' + str(var) + ',' + function
	return expr

def cdef_fit(to_vname, from_vname, mn, mx, nan=False):
	return 'CDEF:{0}={1},{3},MIN{4},{2},MAX{4}'.format(to_vname, from_vname, mn, mx, 'NAN' if nan else '')

def cdef_trend(to_vname, from_vname, trend_window):
	return [
		'CDEF:{0}={1},{2},TRENDNAN'.format(to_vname, from_vname, trend_window),
		'SHIFT:{0}:{1}'.format(to_vname, trend_window // -2),
	]

def cdef_0tick(to_vname, function, dummy_vname):
	if isinstance(function, int):
		if function >= LENGTH_YEAR: function = 'NEWYEAR'
		elif function >= LENGTH_MONTH: function = 'NEWMONTH'
		elif function >= LENGTH_WEEK: function = 'NEWWEEK'
		else: function = 'NEWDAY'
	assert isinstance(function, str), function
	return 'CDEF:{0}={1},{2},POP'.format(to_vname, function, dummy_vname)

def tick(from_vname, color, fraction=None, legend=None):
	s = 'TICK:' + from_vname + color
	if fraction is not None or legend is not None:
		s += ':'
		if fraction is not None: s += str(fraction)
		if legend is not None: s += ':' + esc_colon(legend)
	return s

def __color_unpack(color):
	assert color.startswith('#'), color
	assert len(color) in (7, 9), color
	return (
		int(color[1:3], 16), # R
		int(color[3:5], 16), # G
		int(color[5:7], 16), # B
		int(color[7:9], 16) if len(color) == 9 else 255 # A
	)

def __color_pack(r, g, b, a):
	return '#{0:02X}{1:02X}{2:02X}{3:02X}'.format(r, g, b, a)

def __float_grad(a, b, scale):
	return a * scale + b * (1.0 - scale)

def color_grad_rgb(color_0, color_1, scale):
	tuple_0 = __color_unpack(color_0)
	tuple_1 = __color_unpack(color_1)
	return __color_pack(
		round(__float_grad(tuple_0[0], tuple_1[0], scale)),
		round(__float_grad(tuple_0[1], tuple_1[1], scale)),
		round(__float_grad(tuple_0[2], tuple_1[2], scale)),
		round(__float_grad(tuple_0[3], tuple_1[3], scale)),
	)
	

def unpack_list(l, to=None):
	if to is None: to = list()
	for item in l:
		if isinstance(item, list) or isinstance(item, tuple): unpack_list(item, to=to)
		else: to.append(item)
	return to

def argtype_file(str_path):
	path = pathlib.Path(str_path).resolve()
	if not path.exists(): raise argparse.ArgumentTypeError('{!r} не существует.'.format(str(path)))
	if not path.is_file(): raise argparse.ArgumentTypeError('{!r} не файл.'.format(str(path)))
	# if not os.access(path, os.R_OK): raise argparse.ArgumentTypeError('Нет права на чтение {!r}.'.format(str(path)))
	return str(path)

def detect_length(arg_rrd, arg_start, arg_end):
	cmdline = [
		'rrdtool', 'graphv', os.devnull,
		'--start', arg_start, '--end', arg_end,
		'--width', '256', '--height', '128', '--full-size-mode',
		'DEF:dummy={}:freq:AVERAGE'.format(arg_rrd),
		'VDEF:global_dummy=dummy,AVERAGE',
		'GPRINT:global_dummy:%3.4lf'
	]
	process = subprocess.Popen(cmdline, stdout=subprocess.PIPE, stderr=sys.stdout)

	time_start = -1
	time_end = -1

	stdout = io.TextIOWrapper(process.stdout)
	while True:
		line = stdout.readline().strip()
		if len(line) == 0: break
		try:
			time_start = int(re.match(r'graph_start = ([0-9]+)', line).group(1))
		except Exception: pass
		try:
			time_end = int(re.match(r'graph_end = ([0-9]+)', line).group(1))
		except Exception: pass

	if time_start < 0: raise Exception('Не обнаружен \'graph_start\' в \'{!r}\'.'.format(cmdline))
	if time_end < 0: raise Exception('Не обнаружен \'graph_end\' в \'{!r}\'.'.format(cmdline))

	time = time_end - time_start
	if time < 0: raise Exception('\'graph_end\' ({}) < \'graph_start\' ({})!'.format(time_end, time_start))

	print('Обнаружена длина периода: {} сек'.format(time))
	return time


class AbstractGraph(object):
	def __init__(self):
		super(AbstractGraph, self).__init__()
		self._period_length = -1
		self.argparse = argparse.ArgumentParser()

	def init_argparse(self):
		self.argparse.add_argument('rrd', type=argtype_file,
			help='Путь к RRD-файлу.')
		self.argparse.add_argument('image', type=str,
			help='Путь к целевому изображению (не проверяется).')

		group = self.argparse.add_argument_group('Базовые опции')
		group.add_argument('--trend', dest='trend', type=int, default=-1,
			help='Ширина окна в секундах для расчета trend, значения <0 означают "автоматически", по умолчанию = -1')
		group.add_argument('--error', dest='error', type=float, default=0.5,
			help='Какой объем в %% минимальных и максимальных данных считать ошибочными, по умолчанию = 0.5')
		group.add_argument('--cmd', dest='cmd', action='store_true',
			help='Собрать команду, но не выполнять её, а вывести.')
		group.add_argument('--compat', dest='compat', action='store_true',
			help='Собрать команду, но не выполнять её, а вывести.')

	def init_args(self):
		self.arg_rrd = assert_t(self.raw_args.rrd, str)
		self.arg_image = assert_t(self.raw_args.image, str)
		self.arg_cmd = assert_t(self.raw_args.cmd, bool)
		self.arg_trend = assert_t(self.raw_args.trend, int)
		self.arg_error = assert_t(self.raw_args.error, float)

	def run(self):
		self.init_argparse()
		self.raw_args = self.argparse.parse_args()
		self.init_args()

		cmdline = self.mk_cmdline()
		cmdline = unpack_list(cmdline)

		if self.arg_cmd:
			final_cmd = ''
			for cmd_part in cmdline: final_cmd += '\'' + cmd_part.replace('\'','\'\\\'\'') + '\' '
			print(final_cmd)
		else:
			status = subprocess.run(cmdline, stdout=sys.stdout, stderr=sys.stderr)
			print(status)


	def base_cmdline(self):
		return [
			'rrdtool', 'graph', self.arg_image,
			'--width', '960', '--height', '384', #'--full-size-mode',
			'--pango-markup', '--tabwidth', '100',
			'--alt-autoscale',
			'--alt-y-grid',
		]

	def mk_cmdline(self):
		raise Exception('ABSTRACT')


class FloatingPeriodGraph(AbstractGraph):
	def __init__(self):
		self.__period_length = -1
		self.__trend_window = -1
		super().__init__()

	def init_argparse(self):
		super().init_argparse()
		group = self.argparse.add_argument_group('Опции выбора интервала')
		group.add_argument('--start', dest='start', type=str, default='end-24h',
			help='Аналогичен --start из rrdtool, по умолчанию = end-24h')
		group.add_argument('--end', dest='end', type=str, default='now',
			help='Аналогичен --end из rrdtool, по умолчанию = now')

	def init_args(self):
		super().init_args()
		self.arg_start = assert_t(self.raw_args.start, str)
		self.arg_end = assert_t(self.raw_args.end, str)

	def base_cmdline(self):
		return super().base_cmdline() + [ '--start', self.arg_start, '--end', self.arg_end ]

	def get_period_length(self):
		if self.__period_length < 0: self.__period_length = detect_length(self.arg_rrd, self.arg_start, self.arg_end)
		return self.__period_length

	def get_trend_window(self):
		if self.__trend_window < 0: self.__trend_window = self.get_period_length() // 100
		return self.__trend_window
