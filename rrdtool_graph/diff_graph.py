#!/usr/bin/env python3
from lib import *

class DiffGraph(FloatingPeriodGraph):
	def __init__(self):
		super().__init__()
		self.detect_min_max = True
		self.force_min = 0

	def mk_cmdline(self):
		period = self.get_period_length()
		trend_window = self.get_trend_window()
		trend_humanized = humanize_time(trend_window)
		return super().mk_cmdline() + [
			'--title', 'Интенсивность изменения частоты в сети, <b>{}</b>, Hz/sec'.format(humanize_time(period)),
			
			'DEF:r_min={}:freq_var:MAX'.format(self.arg_rrd),
			'DEF:r_max={}:freq_var:MAX'.format(self.arg_rrd),
			'DEF:r_avg={}:freq_var:AVERAGE'.format(self.arg_rrd),
			
			'VDEF:g_max=r_max,{},PERCENTNAN'.format(100 - self.arg_error),
			
			cdef('f_min', expr_drop('r_min', '0', 'g_max')),
			cdef('f_max', expr_drop('r_max', '0', 'g_max')),
			cdef('f_avg', expr_drop('r_avg', '0', 'g_max')),

			'VDEF:g_avg=f_avg,AVERAGE',

			cdef_trend('t_min', 'f_min', trend_window),
			cdef_trend('t_max', 'f_max', trend_window),
			cdef_trend('t_avg', 'f_avg', trend_window),

			'VDEF:g_last_min=f_min,LAST',
			'VDEF:g_last_max=f_max,LAST',
			'VDEF:g_last_avg=f_avg,LAST',

			cdef('e_max', 'r_max,g_max,GT'),
			cdef('e_miss', 'r_avg,UN'),
			cdef('ztick', expr_0tick(period, 'r_avg')),

			'TEXTALIGN:left',

			comment('Маркеры:'),
			tick('e_miss', '#BFBFBF', fraction=1, legend='  Нет данных'),
			tick('ztick', '#FFFF00', fraction=1),
			tick('e_max', '#FF0000', fraction=-0.02, legend='  Возм. ошибки\\n'),
			'HRULE:0#7F007F::dashes',
			
			comment_header(
				'Измерения:',
				extra_text='(Бледные - исходные данные, Яркие - тренд за {}, пунктир - за весь период)'.format(trend_humanized)
			),
			
			'LINE1:r_min#0000FF1F::skipscale',
			'LINE1:r_max#FF00001F::skipscale',
			'LINE1:r_avg#00FF001F::skipscale',

			'LINE1:t_min#3F3FFF',
			'LINE1:t_max#FF3F3F',
			'LINE1:t_avg#3F7F3F',
			
			'LINE1:g_max#7F0000:↓Общий наиб.\\t:dashes',
			'LINE1:g_avg#007F00:↓Общий сред.\\t:dashes',
			comment('↓Послед. наим.\\t'),
			comment('↓Послед. наиб.\\t'),
			comment('↓Послед. сред.\\n'),

			'GPRINT:g_max:%2.4lf %sHz/sec\\t',
			'GPRINT:g_avg:%2.4lf %sHz/sec\\t',
			'GPRINT:g_last_min:%2.4lf %sHz/sec\\t',
			'GPRINT:g_last_max:%2.4lf %sHz/sec\\t',
			'GPRINT:g_last_avg:%2.4lf %sHz/sec\\n',

			comment_notice_errors(self.arg_error),

			print_max('g_max'),
		]


if __name__ == '__main__':
	DiffGraph().run()
