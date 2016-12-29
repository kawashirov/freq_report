#!/usr/bin/env python3
from lib import *

class NormalGraph(FloatingPeriodGraph):

	def mk_cmdline(self):
		period = self.get_period_length()
		trend_window = self.get_trend_window()
		trend_humanized = humanize_time(trend_window)
		return self.base_cmdline() + [
			'--title', 'Частота в сети, <b>{}</b>, Hz'.format(humanize_time(period)),
			
			'DEF:raw_min={}:freq:MIN'.format(self.arg_rrd),
			'DEF:raw_max={}:freq:MAX'.format(self.arg_rrd),
			'DEF:raw_avg={}:freq:AVERAGE'.format(self.arg_rrd),
			
			'VDEF:global_min=raw_min,{},PERCENTNAN'.format(self.arg_error),
			'VDEF:global_max=raw_max,{},PERCENTNAN'.format(100 - self.arg_error),
			
			cdef_fit('filtred_min', 'raw_min', 'global_min', 'global_max'),
			cdef_fit('filtred_max', 'raw_max', 'global_min', 'global_max'),
			cdef_fit('filtred_avg', 'raw_avg', 'global_min', 'global_max'),
			
			cdef_trend('trend_min', 'filtred_min', trend_window),
			cdef_trend('trend_max', 'filtred_max', trend_window),
			cdef_trend('trend_avg', 'filtred_avg', trend_window),
			
			'VDEF:global_avg=filtred_avg,AVERAGE',
			'VDEF:global_last=filtred_avg,LAST',
			'VDEF:global_stdev=filtred_avg,STDEV',
			
			'CDEF:error_min=raw_min,filtred_min,LT',
			'CDEF:error_max=raw_max,filtred_max,GT',
			'CDEF:missing=raw_avg,UN',
			cdef_0tick('ztick', period, 'raw_avg'),
			
			'TEXTALIGN:left',
			
			comment('Маркеры:'),
			tick('ztick', '#FFFF00', fraction=1),
			tick('missing', '#770077', fraction=-0.02), tick('missing', '#770077', fraction=0.02, legend='  Нет данных'),
			tick('error_min', '#0000FF', fraction=0.02, legend='  Возм. ошибки вниз'),
			tick('error_max', '#FF0000', fraction=-0.02, legend='  Возм. ошибки вверх\\n'),
			
			comment_header('Пределы:', extra_text='(ГОСТ 32144-2013 4.2.1)'),
			'HRULE:50#770077:Номинальное (50 Hz);:dashes',
			comment('Допуст. 100% времени (±0.4 Hz) и 95% времени (±0.2 Hz):'),
			'HRULE:49.6#0000FF:Наим.:dashes',
			'HRULE:49.8#0000FF::dashes',
			'HRULE:50.2#FF0000:Наиб.\\n:dashes',
			'HRULE:50.4#FF0000::dashes',
			
			comment_header(
				'Измерения:',
				extra_text='(Бледные - исходные данные, Яркие - тренд за {})'.format(trend_humanized)
			),
			comment_notice_errors(self.arg_error),
			
			'LINE1:raw_min#0000FF33::skipscale',
			'LINE1:raw_max#FF000033::skipscale',
			'LINE1:raw_avg#00FF0033::skipscale',
			'LINE1:trend_min#3333FF:Наим.\\t',
			'LINE1:trend_max#FF3333:Наиб.\\t',
			'LINE1:trend_avg#337733:Сред.\\n',
			
			'LINE1:global_min#0000BB:(за период)\\t:dashes',
			'LINE1:global_max#BB0000:(за период)\\t:dashes',
			'LINE1:global_avg#00BB00:(за период)\\t:dashes:dash-offset=5',
			'COMMENT:Последний\\t',
			'COMMENT:Станд. откл.\\n',
			
			'GPRINT:global_min:%2.4lf %sHz\\t',
			'GPRINT:global_max:%2.4lf %sHz\\t',
			'GPRINT:global_avg:%2.4lf %sHz\\t',
			'GPRINT:global_last:%2.4lf %sHz\\t',
			'GPRINT:global_stdev:%2.4lf %sHz\\n',
		]


if __name__ == '__main__':
	NormalGraph().run()
