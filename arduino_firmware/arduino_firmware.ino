
/* Определения и замечания */

// Состояние I-A - когда PIN_FREQ_A находится в HIGH, а PIN_FREQ_B в LOW.
// Состояние I-B - когда PIN_FREQ_A находится в LOW, а PIN_FREQ_B в HIGH.
// Эти состояния считаются противоположными друг другу.
//
// Состояние II - когда PIN_FREQ_A находится в том же состоянии,
// что и PIN_FREQ_B (оба в HIGH или LOW). Высока вероятность того, что это
// состояние может никогда не произойти в рабочем режиме. Учитывая, что
// оптопары подключаются с подтяжкой, когда нет сети и отопары потушены, оба
// PIN_FREQ должны быть в состоянии HIGH, а состояние LOW крайне маловероятно.
//
// Свечение PIN_LED_INFO_* происходит в состоянии LOW, а не HIGH

const int PIN_LED_SYS = 13;
const int PIN_LED_INFO_COMMON = 3;
const int PIN_LED_INFO_HI = 4;
const int PIN_LED_INFO_LOW = 5;
const int PIN_FREQ_A = 11;
const int PIN_FREQ_B = 12;
const unsigned int FREQ_TARGET = 50;
const unsigned int FREQ_COUNTS = 500;

inline void wait_for_stable() {
	// delay(1); // А надо ли?
}

void setup() {
	pinMode(PIN_LED_SYS, OUTPUT);
	// Сэтап подсвечивается
	digitalWrite(PIN_LED_SYS, HIGH);

	pinMode(PIN_FREQ_A, INPUT_PULLUP);
	pinMode(PIN_FREQ_B, INPUT_PULLUP);

	pinMode(PIN_LED_INFO_COMMON, OUTPUT);
	pinMode(PIN_LED_INFO_HI, OUTPUT);
	pinMode(PIN_LED_INFO_LOW, OUTPUT);
	
	digitalWrite(PIN_LED_INFO_COMMON, LOW);
	digitalWrite(PIN_LED_INFO_HI, LOW);
	digitalWrite(PIN_LED_INFO_LOW, LOW);

	// Ожидаем порт
	Serial.begin(9600);
	while(!Serial);

	// Ждем пока прибор включат в розетку и ждем еще 250 мс, прежде чем начать.
	int a, b;
	do {
		a = digitalRead(PIN_FREQ_A);
		b = digitalRead(PIN_FREQ_B);
		// Необходимо убедиться, что мы не попали в состояние II.
	} while (a == b);
	delay(250);

	digitalWrite(PIN_LED_SYS, LOW);
}

void loop() {
	unsigned int switch_counter = FREQ_COUNTS;
	unsigned long start, elapsed;
	boolean started = false;
	int a, b;

	/* Первый этап: Синхронизация */

	// Захватываем состояние
	do {
		a = digitalRead(PIN_FREQ_A);
		b = digitalRead(PIN_FREQ_B);
		// Необходимо убедиться, что мы не попали в состояние II.
	} while (a == b);
	// Мы в состоянии I, но не знаем: в его начале, либо же где-то в конце.
	// Дожидаемся переключения состояния I на противоположное.
	while (digitalRead(PIN_FREQ_A) == a || digitalRead(PIN_FREQ_B) == b);
	// Ждем стабилизации
	wait_for_stable();
	// Теперь мы совершенно точно в начале стабильного состяния I.
	// Синхронизация завершена. Фиксируем.
	a = !a;
	b = !b;

	/* Второй этап: подсчет */

	start = micros();

	// Цикл подсчета переключений
	while(switch_counter > 0) {
		// Дожидаемся переключения состояния на противоположное.
		while (digitalRead(PIN_FREQ_A) == a || digitalRead(PIN_FREQ_B) == b);
		// Ждем стабилизации
		wait_for_stable();
		// Затем ждем возврата назад.
		while (digitalRead(PIN_FREQ_A) != a || digitalRead(PIN_FREQ_B) != b);
		// Ждем стабилизации
		wait_for_stable();
		// Пройден полный период.
		--switch_counter;
	}
	// Выход как и вход осуществляется в начале состояния I,
	// по этому нет нужды в коррекциях - сразу же снимаем время

	// Должно быть корректное время даже если micros < start, но не более раза.
	elapsed =	micros() - start;

	/* Третий этап: вычисление и отсылка данных */

	// Вывод данных, подсвечивается.
	digitalWrite(PIN_LED_SYS, HIGH);
	
	// Частота. Умножение на 1M - перевод в секунды.
	double freq = ((double) 1000000) * FREQ_COUNTS / elapsed;

	if (freq > FREQ_TARGET) {
		digitalWrite(PIN_LED_INFO_HI, LOW);
		digitalWrite(PIN_LED_INFO_LOW, HIGH);
	} else {
		digitalWrite(PIN_LED_INFO_HI, HIGH);
		digitalWrite(PIN_LED_INFO_LOW, LOW);
	}
	
	Serial.println(freq, 6);
	Serial.flush();
	
	digitalWrite(PIN_LED_SYS, LOW);
}
