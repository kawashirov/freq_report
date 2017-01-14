#!/usr/bin/env python3
from lib import *

DEFAULT_WIDTH = LENGTH_DAY
DEFAULT_DEPTH = 7

class OverlapGraph(AbstractGraph):
	def __init__(self):
		super().__init__()
		self.detect_min_max = True

	def init_argparse(self):
		super().init_argparse()
		group = self.argparse.add_argument_group('Опции выбора интервала')
		group.add_argument('--width', dest='width', type=int, default=DEFAULT_WIDTH,
			help='Ширина анализируемого интервала в секундах, по умолчанию = {}'.format(DEFAULT_WIDTH))
		group.add_argument('--depth', dest='depth', type=int, default=DEFAULT_DEPTH,
			help='Число анализируемых интервалов, по умолчанию = {}'.format(DEFAULT_DEPTH))
		group.add_argument('--end', dest='end', type=str, default='now',
			help='Аналогичен --end из rrdtool, по умолчанию = now')

	def init_args(self):
		super().init_args()
		self.arg_width = assert_t(self.raw_args.width, int)
		self.arg_depth = assert_t(self.raw_args.depth, int)
		self.arg_end = assert_t(self.raw_args.end, str)

	def mk_cmdline(self):
		offset = self.arg_width
		offset_humanized = humanize_time(offset)
		counts = self.arg_depth
		trend_window = get_trend_window(offset, self.arg_trend)
		trend_humanized = humanize_time(trend_window)

		cmdline = super().mk_cmdline() + [
			'--title', 'Cовмещенная частота в сети, <b>{}</b> периодов по <b>{}</b>, Hz'.format(counts, offset_humanized)
		]

		for i in range(0, counts):
			v = dict(arg_rrd=self.arg_rrd, i=i, i1_offset = (i + 1) * offset, i_offset = i * offset)
			cmdline += [
				'DEF:r_i{i}_min={arg_rrd}:freq:MIN:start=now-{i1_offset}:end=now-{i_offset}'.format(**v),
				'DEF:r_i{i}_max={arg_rrd}:freq:MAX:start=now-{i1_offset}:end=now-{i_offset}'.format(**v),
				'DEF:r_i{i}_avg={arg_rrd}:freq:AVERAGE:start=now-{i1_offset}:end=now-{i_offset}'.format(**v),
				'SHIFT:r_i{i}_min:{i_offset}'.format(**v),
				'SHIFT:r_i{i}_max:{i_offset}'.format(**v),
				'SHIFT:r_i{i}_avg:{i_offset}'.format(**v),
			]

		cmdline += [
			cdef('r_min', expr_f_chain('MINNAN', [ 'r_i{}_min'.format(x) for x in range(0, counts) ])),
			cdef('r_max', expr_f_chain('MAXNAN', [ 'r_i{}_max'.format(x) for x in range(0, counts) ])),

			'VDEF:g_min=r_min,{},PERCENTNAN'.format(self.arg_error),
			'VDEF:g_max=r_max,{},PERCENTNAN'.format(100 - self.arg_error),

			[[
				cdef('f_i{}_avg'.format(i), expr_drop('r_i{}_avg'.format(i), 'g_min', 'g_max')),
				cdef_trend('t_i{}_avg'.format(i), 'f_i{}_avg'.format(i), trend_window),
			] for i in range(0, counts) ],

			cdef('r_avg', expr_avg([ 'r_i{}_avg'.format(i) for i in range(0, counts) ])),
			cdef('f_avg', expr_avg([ 'f_i{}_avg'.format(i) for i in range(0, counts) ])),
			cdef('t_avg', expr_avg([ 't_i{}_avg'.format(i) for i in range(0, counts) ])),

			'VDEF:g_avg=f_avg,AVERAGE',

			cdef('e_min', 'r_min,g_min,LT'),
			cdef('e_max', 'r_max,g_max,GT'),
			cdef('e_miss_all', 'r_avg,UN'),
			cdef('e_miss_some', expr_f_chain('+', [ 'r_i{}_avg,UN'.format(x) for x in range(0, counts) ])),
			cdef('ztick', expr_0tick(offset, 'r_i0_avg')),
			
			'TEXTALIGN:left',

			comment('Маркеры:'),
			tick('e_miss_all', '#7F7F7F', fraction=1, legend='  Нет данных вообще'),
			tick('ztick', '#FFFF00', fraction=1),
			tick('e_miss_some', '#BFBFBF', fraction=-0.02),
				tick('e_miss_some', '#BFBFBF', fraction=0.02, legend='  Нет части данных'),
			tick('e_min', '#0000FF', fraction=0.02, legend='  Возм. ошибки вниз'),
			tick('e_max', '#FF0000', fraction=-0.02, legend='  Возм. ошибки вверх\\n'),
			
			comment_header('Пределы:', extra_text='(ГОСТ 32144-2013 4.2.1)'),
			'HRULE:50#7F007F:Номинальное (50 Hz);:dashes',
			comment('Допуст. 100% времени (±0.4 Hz) и 95% времени (±0.2 Hz):'),
			'HRULE:49.6#0000FF:Наим.:dashes',
			'HRULE:49.8#0000FF::dashes',
			'HRULE:50.2#FF0000:Наиб.:dashes',
			'HRULE:50.4#FF0000::dashes',
			comment('(Могут скрыться)\\n'),

			comment_header(
				'Измерения:',
				extra_text='(Бледные - исходные данные, Яркие - тренд за {}, пунктир - за весь период)'.format(trend_humanized)
			),

			# 'LINE1:r_min#0000FF33::skipscale',
			# 'LINE1:r_max#FF000033::skipscale',
			[
				'LINE1:r_i{0}_avg{1}::skipscale'.format(i, color_grad_rgb('#00FFFF7F', '#FFFF007F', i / (counts-1)))
				for i in reversed(range(0, counts))
			],

			'LINE1:g_min#00007F:↓Общ. наим.\\t:dashes',
			'LINE1:g_max#7F0000:↓Общ. наиб.\\t:dashes', 
			'LINE1:g_avg#000000::dashes:dash-offset=5',
			'LINE2:t_avg#000000:↓Общ. сред.\\n', 

			'GPRINT:g_min:%2.4lf %sHz\\t',
			'GPRINT:g_max:%2.4lf %sHz\\t',
			'GPRINT:g_avg:%2.4lf %sHz\\n',

			comment('Глубина ({}):'.format(counts)),
			[
				'LINE1:t_i{0}_avg{1}:-{0},'.format(i, color_grad_rgb('#007F7F', '#7F7F00', i / (counts-1)))
				for i in reversed(range(0, counts))
			],
			comment('\\n'),

			'LINE2:t_avg#0000007F', # Повторное наложение тренда

			comment_notice_errors(self.arg_error),

			print_min('g_min'),
			print_max('g_max'),
		]
		return cmdline


if __name__ == '__main__':
	OverlapGraph().run()
