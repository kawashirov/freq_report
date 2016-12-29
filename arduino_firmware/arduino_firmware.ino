
const int LED_PIN = 13;
const int FREQ_PIN = 12;
const unsigned int FREQ_COUNTS = 1000;

void setup() {
	Serial.begin(9600);
	pinMode(FREQ_PIN, INPUT_PULLUP);
	pinMode(LED_PIN, OUTPUT);
	digitalWrite(LED_PIN, LOW);
	// Ожидаем порт
	while(!Serial);
	// Ожидаем первого переключения - ждем пока прибор включат в розетку и ждем еще 100 мс, прежде чем начать.
	digitalWrite(LED_PIN, HIGH);
	int state = digitalRead(FREQ_PIN);
	while(state == digitalRead(FREQ_PIN));
	delay(100);
	digitalWrite(LED_PIN, LOW);
}

void loop() {
	// Не обходимо подсчитывать до n+1-ого переключения
	unsigned int switch_counter = FREQ_COUNTS + 1;
	unsigned long start, elapsed;
	boolean started = false;
	// Цикл подсчета переключений
	while(switch_counter > 0) {
		int state = digitalRead(FREQ_PIN);
		// Ждем преключения стостояния
		while(state == digitalRead(FREQ_PIN));
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
	digitalWrite(LED_PIN, HIGH);
	// Частота. Деление на два т.к. в одном периоде два переключения состояния. Умножение на 1M - перевод в секунды.
	double freq = ((double) 1000000) * FREQ_COUNTS / 2.0 / elapsed;
	Serial.println(freq, 6);
	Serial.flush();
	digitalWrite(LED_PIN, LOW);
}
