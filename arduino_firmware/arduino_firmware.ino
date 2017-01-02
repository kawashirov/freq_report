
const int PIN_LED_SYS = 13;
const int PIN_LED_INFO_COMMON = 3;
const int PIN_LED_INFO_HI = 4;
const int PIN_LED_INFO_LOW = 5;
const int PIN_FREQ = 12;
const unsigned int FREQ_TARGET = 50;
const unsigned int FREQ_COUNTS = 1000;

void setup() {
	pinMode(PIN_FREQ, INPUT_PULLUP);
	pinMode(PIN_LED_SYS, OUTPUT);
	pinMode(PIN_LED_INFO_COMMON, OUTPUT);
	pinMode(PIN_LED_INFO_HI, OUTPUT);
	pinMode(PIN_LED_INFO_LOW, OUTPUT);
	
	digitalWrite(PIN_LED_SYS, LOW);
	digitalWrite(PIN_LED_INFO_COMMON, LOW);
	digitalWrite(PIN_LED_INFO_HI, LOW);
	digitalWrite(PIN_LED_INFO_LOW, LOW);

	Serial.begin(9600);
	// Ожидаем порт
	while(!Serial);
	// Ожидаем первого переключения - ждем пока прибор включат в розетку и ждем еще 100 мс, прежде чем начать.
	digitalWrite(PIN_LED_SYS, HIGH);
	int state = digitalRead(PIN_FREQ);
	while(state == digitalRead(PIN_FREQ));
	delay(100);
	digitalWrite(PIN_LED_SYS, LOW);
}

void loop() {
	// Не обходимо подсчитывать до n+1-ого переключения
	unsigned int switch_counter = FREQ_COUNTS + 1;
	unsigned long start, elapsed;
	boolean started = false;
	// Цикл подсчета переключений
	while(switch_counter > 0) {
		int state = digitalRead(PIN_FREQ);
		// Ждем преключения стостояния
		while(state == digitalRead(PIN_FREQ));
		// При первом переключении начинаем отсчет
		if (!started) {
			start = micros();
			started = true;
		}
		--switch_counter;
	}
	// Должно быть корректное время даже если micros < start, но не более раза.
	elapsed =	micros() - start; 
	
	// Вывод данных, подсвечивается.
	digitalWrite(PIN_LED_SYS, HIGH);
	
	// Частота. Деление на два т.к. в одном периоде два переключения состояния. Умножение на 1M - перевод в секунды.
	double freq = ((double) 1000000) * FREQ_COUNTS / 2.0 / elapsed;

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
