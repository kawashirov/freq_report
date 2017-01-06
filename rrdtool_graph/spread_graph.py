#!/usr/bin/env python3
from lib import *

class SpreadGraph(FloatingPeriodGraph):
	def __init__(self):
		super().__init__()
		self.detect_min_max = True

	def mk_cmdline(self):
		period = self.get_period_length()
		trend_window = self.get_trend_window()
		trend_humanized = humanize_time(trend_window)
		return super().mk_cmdline() + [
			'--lower-limit',' 0', '--alt-autoscale-max',
			'--title', 'Разброс частоты в сети, <b>{}</b>, Hz'.format(humanize_time(period)),
			
			'DEF:r_min={}:freq:MIN'.format(self.arg_rrd),
			'DEF:r_max={}:freq:MAX'.format(self.arg_rrd),
			
			'VDEF:g_min=r_min,{},PERCENTNAN'.format(self.arg_error),
			'VDEF:g_max=r_max,{},PERCENTNAN'.format(100 - self.arg_error),
			
			cdef('f_min', expr_drop('r_min', 'g_min', 'g_max')),
			cdef('f_max', expr_drop('r_max', 'g_min', 'g_max')),

			cdef('r_diff', 'f_max,f_min,-'),
			'VDEF:g_diff_min=r_diff,MINIMUM',
			'VDEF:g_diff_max=r_diff,MAXIMUM',

			cdef_trend('t_diff', 'r_diff', trend_window),
			'VDEF:g_last=r_diff,LAST',

			cdef('e_avg_min', 'r_min,g_min,LT'),
			cdef('e_avg_max', 'r_max,g_max,GT'),
			cdef('e_miss', 'r_min,UN'),
			cdef('ztick', expr_0tick(period, 'r_min')),

			'TEXTALIGN:left',

			comment('Маркеры:'),
			tick('e_miss', '#BFBFBF', fraction=1, legend='  Нет данных'),
			tick('ztick', '#FFFF00', fraction=1),
			tick('e_avg_min', '#0000FF', fraction=0.02, legend='  Возм. ошибки вниз'),
			tick('e_avg_max', '#FF0000', fraction=-0.02, legend='  Возм. ошибки вверх\\n'),
			
			comment_header(
				'Разброс измерений:',
				extra_text='(Бледные - исходные данные, яркие - тренд за {}, пунктир - за весь период)'.format(trend_humanized)
			),
			
			'LINE1:r_diff#00FF007F::skipscale',
			'LINE1:t_diff#3F7F3F',
			
			'LINE1:g_diff_min#00007F:↓Наим.\\t:dashes', 
			'LINE1:g_diff_max#7F0000:↓Наиб.\\t:dashes', 
			comment('↓Последний\\n'), 

			'GPRINT:g_diff_min:%3.4lf %sHz\\t',
			'GPRINT:g_diff_max:%3.4lf %sHz\\t',
			'GPRINT:g_last:%2.4lf %sHz\\n',

			comment_notice_errors(self.arg_error),

			# print_min('g_diff_min'),
			print_max('g_diff_max'),
		]


if __name__ == '__main__':
	SpreadGraph().run()
