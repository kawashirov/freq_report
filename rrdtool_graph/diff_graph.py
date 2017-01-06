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
			
			cdef('f_avg', expr_drop('r_avg', 'g_min', 'g_max')),

			cdef('r_diff', 'r_avg,PREV(r_avg),-'),
			cdef('f_diff', 'f_avg,PREV(f_avg),-'),
			cdef('f_diff_pos', 'f_diff,0,GT,f_diff,UNKN,IF'),
			cdef('f_diff_neg', 'f_diff,0,LT,f_diff,UNKN,IF'),
			'VDEF:g_diff_min=f_diff,MINIMUM',
			'VDEF:g_diff_max=f_diff,MAXIMUM',

			cdef_trend('t_diff', 'f_diff', trend_window),
			cdef_trend('t_diff_pos', 'f_diff_pos', trend_window),
			cdef_trend('t_diff_neg', 'f_diff_neg', trend_window),
			'VDEF:g_last=f_diff,LAST',
			'VDEF:g_stdev=f_diff,STDEV',

			cdef('e_avg_min', 'r_min,g_min,LT'),
			cdef('e_avg_max', 'r_max,g_max,GT'),
			cdef('e_miss', 'r_avg,UN'),
			cdef('ztick', expr_0tick(period, 'r_avg')),

			'TEXTALIGN:left',

			comment('Маркеры:'),
			tick('e_miss', '#BFBFBF', fraction=1, legend='  Нет данных'),
			tick('ztick', '#FFFF00', fraction=1),
			tick('e_avg_min', '#0000FF', fraction=0.02, legend='  Возм. ошибки вниз'),
			tick('e_avg_max', '#FF0000', fraction=-0.02, legend='  Возм. ошибки вверх\\n'),
			'HRULE:0#007700::dashes',
			
			comment_header(
				'Изменения измерений:',
				extra_text='(Бледные - исходные данные, Яркие - тренд за {}, пунктир - за весь период)'.format(trend_humanized)
			),
			
			'LINE1:r_diff#00FF0033::skipscale',

			comment('Тренды:'),
			'LINE1:t_diff_pos#FF3F3F7F:Только полож.',
			'LINE1:t_diff_neg#3F3FFF7F:Только отриц.',
			'LINE1:t_diff#3F7F3F:Общий\\n',
			
			'LINE1:g_diff_min#00007F:↓Наиб. падение\\t:dashes',
			'LINE1:g_diff_max#7F0000:↓Наиб. рост\\t:dashes',
			comment('↓Последний\\t'),
			comment('↓Станд. откл.\\n'),
			
			'GPRINT:g_diff_min:%2.4lf %sHz/sec\\t',
			'GPRINT:g_diff_max:%2.4lf %sHz/sec\\t',
			'GPRINT:g_last:%2.4lf %sHz/sec\\t',
			'GPRINT:g_stdev:%2.4lf %sHz/sec\\n',

			comment_notice_errors(self.arg_error),

			print_min('g_diff_min'),
			print_max('g_diff_max'),
		]


if __name__ == '__main__':
	DiffGraph().run()
