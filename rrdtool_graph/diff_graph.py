#!/usr/bin/env python3
from lib import *

class DiffGraph(FloatingPeriodGraph):
	def __init__(self):
		super().__init__()
		self.detect_min_max = True

	def mk_cmdline(self):
		period = self.get_period_length()
		trend_window = self.get_trend_window()
		trend_humanized = humanize_time(trend_window)
		return super().mk_cmdline() + [
			'--title', 'Изменение частоты в сети, <b>{}</b>, Hz/sec'.format(humanize_time(period)),
			
			'DEF:r_min={}:freq:MIN'.format(self.arg_rrd),
			'DEF:r_max={}:freq:MAX'.format(self.arg_rrd),
			'DEF:r_avg={}:freq:AVERAGE'.format(self.arg_rrd),
			
			'VDEF:g_min=r_min,{},PERCENTNAN'.format(self.arg_error),
			'VDEF:g_max=r_max,{},PERCENTNAN'.format(100 - self.arg_error),
			
			cdef('f_min', expr_drop('r_min', 'g_min', 'g_max')),
			cdef('f_max', expr_drop('r_max', 'g_min', 'g_max')),
			cdef('f_avg', expr_drop('r_avg', 'g_min', 'g_max')),

			cdef('r_diff_min', 'r_min,PREV(r_max),-,STEPWIDTH,/'),
			cdef('r_diff_max', 'r_max,PREV(r_min),-,STEPWIDTH,/'),
			cdef('r_diff_avg', 'r_avg,PREV(r_avg),-,STEPWIDTH,/'),

			cdef('f_diff_min', 'f_min,PREV(f_max),-,STEPWIDTH,/'),
			cdef('f_diff_max', 'f_max,PREV(f_min),-,STEPWIDTH,/'),
			cdef('f_diff_avg', 'f_avg,PREV(f_avg),-,STEPWIDTH,/'),

			'VDEF:g_diff_min=f_diff_min,MINIMUM',
			'VDEF:g_diff_max=f_diff_max,MAXIMUM',

			cdef_trend('t_diff_min', 'f_diff_min', trend_window),
			cdef_trend('t_diff_max', 'f_diff_max', trend_window),
			cdef_trend('t_diff_avg', 'f_diff_avg', trend_window),

			'VDEF:g_last_min=f_diff_min,LAST',
			'VDEF:g_last_max=f_diff_max,LAST',
			'VDEF:g_last_avg=f_diff_max,LAST',

			cdef('e_min', 'r_min,g_min,LT'),
			cdef('e_max', 'r_max,g_max,GT'),
			cdef('e_miss', 'r_avg,UN'),
			cdef('ztick', expr_0tick(period, 'r_avg')),

			'TEXTALIGN:left',

			comment('Маркеры:'),
			tick('e_miss', '#BFBFBF', fraction=1, legend='  Нет данных'),
			tick('ztick', '#FFFF00', fraction=1),
			tick('e_min', '#0000FF', fraction=0.02, legend='  Возм. ошибки вниз'),
			tick('e_max', '#FF0000', fraction=-0.02, legend='  Возм. ошибки вверх\\n'),
			'HRULE:0#7F007F::dashes',
			
			comment_header(
				'Пределы возможных изменений:',
				extra_text='(Бледные - исходные данные, Яркие - тренд за {}, пунктир - за весь период)'.format(trend_humanized)
			),
			
			'LINE1:r_diff_min#0000FF33::skipscale',
			'LINE1:r_diff_max#FF000033::skipscale',
			'LINE1:r_diff_avg#00FF0033::skipscale',

			'LINE1:t_diff_min#3F3FFF:Наим. возможное изменение',
			'LINE1:t_diff_max#FF3F3F:Наиб. возможное изменение',
			'LINE1:t_diff_avg#3F7F3F:Изменение среднего\\n',
			
			'LINE1:g_diff_min#00007F:↓Абс. нижний\\t:dashes',
			'LINE1:g_diff_max#7F0000:↓Абс. верхний\\t:dashes',
			comment('↓Последний сред.\\n'),
			
			'GPRINT:g_diff_min:%2.4lf %sHz/sec\\t',
			'GPRINT:g_diff_max:%2.4lf %sHz/sec\\t',
			'GPRINT:g_last_avg:%2.4lf %sHz/sec\\n',

			comment_notice_errors(self.arg_error),

			print_min('g_diff_min'),
			print_max('g_diff_max'),
		]


if __name__ == '__main__':
	DiffGraph().run()
