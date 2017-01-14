#!/usr/bin/env python3
import sys, os, io, re, pathlib, subprocess, argparse

LENGTH_MINUTE = 60
LENGTH_HOUR = LENGTH_MINUTE * 60
LENGTH_DAY = LENGTH_HOUR * 24
LENGTH_WEEK = LENGTH_DAY * 7
LENGTH_MONTH = LENGTH_DAY * 31
LENGTH_YEAR = LENGTH_DAY * 365

def is_list_or_tuple(obj):
	return isinstance(obj, list) or isinstance(obj, tuple)

def assert_t(arg, t):
	assert isinstance(arg, t), (arg, t)
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



def expr_join(*expr_list):
	return ','.join([ (
		expr_join(*expr) if is_list_or_tuple(expr) else str(expr)
	) for expr in expr_list ])

def expr_avg(expr_list):
	assert isinstance(expr_list, list)
	assert len(expr_list) > 0
	return expr_join(expr_list + [str(len(expr_list)), 'AVG'])

# Делает цепочку: f(expr, f(expr, ... f(expr, expr) ... ))
# Функция должна быть ассоциотивна
def expr_f_chain(function, expr_list):
	l = len(expr_list)
	assert isinstance(expr_list, list)
	assert l > 0
	if l == 1: return expr_list[0]
	expr = str(expr_list.pop(0))
	for var in expr_list:
		expr += ',' + str(var) + ',' + function
	return expr

# Вписать значение в перделы
def expr_fit(from_vname, mn, mx, nan=False):
	return expr_join(from_vname, mx, ('MINNAN' if nan else 'MIN'), mn, ('MAXNAN' if nan else 'MAX'))

# Отбросить значение, если оно не вписывается в пределы
def expr_drop(from_vname, mn, mx):
	return expr_join(( str(from_vname), str(mn), str(mx), 'LIMIT' ))

# (1 == UN) != (2 == UN)
def expr_unknowness_ne(to_vname, expr_1, expr_2):
	return expr_join(expr_1, 'UN', expr_2, 'UN', 'NE')

def expr_0tick(function, dummy_vname):
	if isinstance(function, int):
		if function >= LENGTH_YEAR: function = 'NEWYEAR'
		elif function >= LENGTH_MONTH: function = 'NEWMONTH'
		elif function >= LENGTH_WEEK: function = 'NEWWEEK'
		elif function >= LENGTH_DAY: function = 'NEWDAY'
		else: function = 'LTIME,' + str(LENGTH_HOUR) + ',%,0,EQ' # NEWHOUR
	assert isinstance(function, str), function
	return expr_join(function, dummy_vname, 'POP')

def cdef(to_vname, from_expr):
	return 'CDEF:' + str(to_vname) + '=' + (expr_join(*from_expr) if is_list_or_tuple(from_expr) else str(from_expr))

def vdef(to_vname, from_expr):
	return 'VDEF:' + str(to_vname) + '=' + (expr_join(*from_expr) if is_list_or_tuple(from_expr) else str(from_expr))
	
def cdef_trend(to_vname, from_vname, trend_window, nan=True):
	return [
		cdef(to_vname, ( from_vname, trend_window, ('TRENDNAN' if nan else 'TREND') )),
		'SHIFT:{0}:{1}'.format(to_vname, trend_window // -2),
	]

def tick(from_vname, color, fraction=None, legend=None):
	s = 'TICK:' + from_vname + color
	if fraction is not None or legend is not None:
		s += ':'
		if fraction is not None: s += str(fraction)
		if legend is not None: s += ':' + esc_colon(legend)
	return s

def print_min(from_vname):
	return 'PRINT:' + str(from_vname) + ':MIN\\:%le'

def print_max(from_vname):
	return 'PRINT:' + str(from_vname) + ':MAX\\:%le'

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

def argtype_value_or_scale(str_arg):
	if str_arg == 'auto':
		return ( 'auto', None )
	if str_arg.endswith('%'):
		return ( 'scale', abs(float(str_arg[:-1])) / 100 )
	else:
		return ( 'value', int(str_arg) )

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

	print('Обнаружена длина периода: {} сек'.format(time), file=sys.stderr)
	return time

def get_trend_window(period_length, trend_type):
	trend_type, trend_value = trend_type
	if trend_type == 'auto': return period_length // 60
	if trend_type == 'scale': return period_length * trend_value
	elif trend_type == 'value': return trend_value
	else: assert False, self.arg_trend

def detect_min_max(cmdline):
	env = os.environ.copy()
	env['LC_NUMERIC'] = 'en_US.UTF-8'
	process = subprocess.Popen(cmdline, stdout=subprocess.PIPE, stderr=sys.stdout, env=env)

	b_min, b_max = None, None

	stdout = io.TextIOWrapper(process.stdout)
	while True:
		line = stdout.readline().strip()
		if len(line) == 0: break
		print('Линия: ', repr(line), file=sys.stderr)
		try:
			b_min = float(re.match(r'MIN:([0-9eE.,+-]+)', line).group(1).replace(',', '.'))
			print('Определен min: ', repr(b_min), file=sys.stderr)
		except Exception: pass
		try:
			b_max = float(re.match(r'MAX:([0-9eE.,+-]+)', line).group(1).replace(',', '.'))
			print('Определен max: ', repr(b_max), file=sys.stderr)
		except Exception: pass

	if b_min is not None and b_max is not None:
		assert b_max > b_min, (b_max, b_min)

	return b_min, b_max

class AbstractGraph(object):
	def __init__(self):
		super(AbstractGraph, self).__init__()
		self._period_length = -1
		self.argparse = argparse.ArgumentParser()
		self.detect_min_max = False

	def init_argparse(self):
		self.argparse.add_argument('rrd', type=argtype_file,
			help='Путь к RRD-файлу.')
		self.argparse.add_argument('image', type=str,
			help='Путь к целевому изображению (не проверяется).')

		group = self.argparse.add_argument_group('Базовые опции')
		group.add_argument('--trend', dest='trend', type=argtype_value_or_scale, default=('auto', None),
			help='Ширина окна в секундах или процентах для расчета trend, по умолчанию = auto')
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
		self.arg_trend = assert_t(self.raw_args.trend, tuple)
		self.arg_error = assert_t(self.raw_args.error, float)

	def run(self):
		self.init_argparse()
		self.raw_args = self.argparse.parse_args()
		self.init_args()

		impl_cmdline = unpack_list(self.mk_cmdline())

		limits_cmdline = []
		if not self.arg_cmd and self.detect_min_max:
			# Определение пределов
			detection_cmdline = [
				'rrdtool', 'graph', os.devnull,
				'--width', '960', '--height', '384',
				# '--pango-markup', '--tabwidth', '100',
				# '--alt-y-grid',
			] + impl_cmdline
			b_min, b_max = detect_min_max(detection_cmdline)


			if b_min is None and b_max is None:
				print('Внимание! Запрошено определение пределов, но они не обнаружены.', file=sys.stderr)
				limits_cmdline.append('--alt-autoscale')
			else:
				spread = 0
				if b_min is not None and b_max is not None:
					spread = (b_max - b_min) / 100.0
					print('Коррекция пределов: ', repr(spread), file=sys.stderr)

				limits_cmdline.append('--rigid')

				if b_min is None: limits_cmdline.append('--alt-autoscale-min')
				else: limits_cmdline += [ '--lower-limit', str(b_min - spread) ]

				if b_max is None: limits_cmdline.append('--alt-autoscale-max')
				else: limits_cmdline += [ '--upper-limit', str(b_max + spread) ]

		production_cmdline = [
			'rrdtool', 'graph', self.arg_image,
			# TODO options
			'--width', '960', '--height', '384', #'--full-size-mode',
			'--pango-markup', '--tabwidth', '100',
			'--alt-y-grid',
			'--color', 'BACK#00000000',
			'--color', 'SHADEA#00000000',
			'--color', 'SHADEB#00000000',
		] + limits_cmdline + impl_cmdline

		if self.arg_cmd:
			final_cmd = ''
			for cmd_part in production_cmdline:
				final_cmd += '\'' + cmd_part.replace('\'','\'\\\'\'') + '\' '
			print(final_cmd, file=sys.stderr)
		else:
			status = subprocess.run(production_cmdline, stdout=sys.stdout, stderr=sys.stderr)
			print(repr(status), file=sys.stderr)

	def mk_cmdline(self):
		return []


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

	def mk_cmdline(self):
		return [ '--start', self.arg_start, '--end', self.arg_end ]

	def get_period_length(self):
		if self.__period_length < 0: self.__period_length = detect_length(self.arg_rrd, self.arg_start, self.arg_end)
		return self.__period_length

	def get_trend_window(self):
		if self.__trend_window < 0:
			self.__trend_window = get_trend_window(self.get_period_length(), self.arg_trend)
		return self.__trend_window
