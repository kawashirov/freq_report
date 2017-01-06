#!/usr/bin/env python3
from lib import *

class NormalGraph(FloatingPeriodGraph):
	def __init__(self):
		super().__init__()
		self.detect_min_max = True

	def mk_cmdline(self):
		period = self.get_period_length()
		trend_window = self.get_trend_window()
		trend_humanized = humanize_time(trend_window)
		return super().mk_cmdline() + [
			'--title', 'Частота в сети, <b>{}</b>, Hz'.format(humanize_time(period)),
			
			'DEF:r_min={}:freq:MIN'.format(self.arg_rrd),
			'DEF:r_max={}:freq:MAX'.format(self.arg_rrd),
			'DEF:r_avg={}:freq:AVERAGE'.format(self.arg_rrd),
			
			'VDEF:g_min=r_min,{},PERCENTNAN'.format(self.arg_error),
			'VDEF:g_max=r_max,{},PERCENTNAN'.format(100 - self.arg_error),
			
			cdef('f_min', expr_drop('r_min', 'g_min', 'g_max')),
			cdef('f_max', expr_drop('r_max', 'g_min', 'g_max')),
			cdef('f_avg', expr_drop('r_avg', 'g_min', 'g_max')),
			
			cdef_trend('t_min', 'f_min', trend_window),
			cdef_trend('t_max', 'f_max', trend_window),
			cdef_trend('t_avg', 'f_avg', trend_window),
			
			'VDEF:g_avg=f_avg,AVERAGE',
			'VDEF:g_last=f_avg,LAST',
			'VDEF:g_stdev=f_avg,STDEV',
			
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
			
			'LINE1:r_min#0000FF3F::skipscale',
			'LINE1:r_max#FF00003F::skipscale',
			'LINE1:r_avg#00FF003F::skipscale',
			'LINE1:t_min#3F3FFF',
			'LINE1:t_max#FF3F3F',
			'LINE1:t_avg#3F773F',
			
			'LINE1:g_min#00007F:↓Наим.\\t:dashes',
			'LINE1:g_max#7F0000:↓Наиб.\\t:dashes',
			'LINE1:g_avg#007F00:↓Сред.\\t:dashes:dash-offset=5',
			'COMMENT:↓Последний\\t',
			'COMMENT:↓Станд. откл.\\n',
			
			'GPRINT:g_min:%2.4lf %sHz\\t',
			'GPRINT:g_max:%2.4lf %sHz\\t',
			'GPRINT:g_avg:%2.4lf %sHz\\t',
			'GPRINT:g_last:%2.4lf %sHz\\t',
			'GPRINT:g_stdev:%2.4lf %sHz\\n',

			comment_notice_errors(self.arg_error),

			print_min('g_min'),
			print_max('g_max'),
		]


if __name__ == '__main__':
	NormalGraph().run()
