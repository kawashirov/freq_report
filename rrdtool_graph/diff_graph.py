#!/usr/bin/env python3
from lib import *

class DiffGraph(FloatingPeriodGraph):

	def mk_cmdline(self):
		period = self.get_period_length()
		trend_window = self.get_trend_window()
		trend_humanized = humanize_time(trend_window)
		return self.base_cmdline() + [
			'--title', 'Изменение частоты в сети, <b>{}</b>, Hz/sec'.format(humanize_time(period)),
			
			'DEF:r_min={}:freq:MIN'.format(self.arg_rrd),
			'DEF:r_max={}:freq:MAX'.format(self.arg_rrd),
			'DEF:r_avg={}:freq:AVERAGE'.format(self.arg_rrd),
			
			'VDEF:g_min=r_min,{},PERCENTNAN'.format(self.arg_error),
			'VDEF:g_max=r_max,{},PERCENTNAN'.format(100 - self.arg_error),
			
			# cdef_drop('f_min', 'r_min', 'g_min', 'g_max'),
			# cdef_drop('f_max', 'r_max', 'g_min', 'g_max'),
			cdef_drop('f_avg', 'r_avg', 'g_min', 'g_max'),

			'CDEF:r_diff=r_avg,PREV(r_avg),-',
			'CDEF:f_diff=f_avg,PREV(f_avg),-',
			'VDEF:g_diff_min=f_diff,MINIMUM',
			'VDEF:g_diff_max=f_diff,MAXIMUM',

			cdef_trend('t_diff', 'f_diff', trend_window),
			'VDEF:g_last=f_diff,LAST',
			'VDEF:g_stdev=f_diff,STDEV',

			'CDEF:e_avg_min=r_min,g_min,LT',
			'CDEF:e_avg_max=r_max,g_max,GT',
			'CDEF:e_miss=r_avg,UN',
			cdef_0tick('ztick', period, 'r_avg'),

			'TEXTALIGN:left',

			comment('Маркеры:'),
			tick('ztick', '#FFFF00', fraction=1),
			tick('e_miss', '#770077', fraction=-0.02),
				tick('e_miss', '#770077', fraction=0.02, legend='  Нет данных'),
			tick('e_avg_min', '#0000FF', fraction=0.02, legend='  Возм. ошибки вниз'),
			tick('e_avg_max', '#FF0000', fraction=-0.02, legend='  Возм. ошибки вверх\\n'),
			'HRULE:0#007700::dashes',
			
			comment_header(
				'Измерения:',
				extra_text='(Бледные - исходные данные, Яркие - тренд за {})'.format(trend_humanized)
			),
			comment_notice_errors(self.arg_error),
			
			'LINE1:r_diff#00FF0033::skipscale',
			# 'LINE1:f_diff#00FF00',
			'LINE1:t_diff#337733',
			
			'LINE1:g_diff_min#000077:Наиб. падение\\t:dashes',
			'LINE1:g_diff_max#770000:Наиб. рост\\t:dashes',
			comment('Последний\\t'),
			comment('Станд. откл.\\n'),
			
			'GPRINT:g_diff_min:%2.4lf %sHz/sec\\t',
			'GPRINT:g_diff_max:%2.4lf %sHz/sec\\t',
			'GPRINT:g_last:%2.4lf %sHz\\t',
			'GPRINT:g_stdev:%2.4lf %sHz\\n',
		]


if __name__ == '__main__':
	DiffGraph().run()
