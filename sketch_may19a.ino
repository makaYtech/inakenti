#include <LiquidCrystal.h>

LiquidCrystal lcd(13, 12, 11, 10, 9, 8);
String buffer = "";

// --- Пины ---
const int BTN_NEXT = 7;
const int BTN_PREV = 6;
const int BTN_PLAY = 5;
const int BTN_VOL = 4;

// --- Состояния кнопок ---
bool lastNext = HIGH, lastPrev = HIGH, lastPlay = HIGH, lastVol = HIGH;
unsigned long playPressTime = 0;
bool longPressSent = false;
const unsigned long LONG_PRESS_MS = 800;
const unsigned long DEBOUNCE_MS = 50;
unsigned long lastDebounce = 0;

// --- Состояние рукопожатия
bool pcReady = false;
unsigned long lastInitSend = 0;

void setup() {
  Serial.begin(115200);
  lcd.begin(16, 2);
  lcd.print("Waiting PC...");
  pinMode(BTN_NEXT, INPUT_PULLUP);
  pinMode(BTN_PREV, INPUT_PULLUP);
  pinMode(BTN_PLAY, INPUT_PULLUP);
  pinMode(BTN_VOL, INPUT_PULLUP);
}

void loop() {
  if (!pcReady) {
    if (millis() - lastInitSend > 300) {
      Serial.println("INITED");
      lastInitSend = millis();
    }
    if (Serial.available() > 0) {
      while (Serial.available()) Serial.read();
      pcReady = true;
      lcd.clear();
      lcd.setCursor(0, 0); lcd.print("PC Connected!");
      delay(1000);
      lcd.clear();
    }
    return;
  }
  handleSerial();
  handleInputs();
}

// 🔹 Чтение и отображение данных от ПК
void handleSerial() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (buffer == "EXIT") {
        pcReady = false;
        lcd.clear();
        lcd.setCursor(0, 0); lcd.print("Waiting PC...");
        buffer = "";
        return;
      }
      if (buffer.length() > 0) displayLCD(buffer);
      buffer = "";
    } else {
      buffer += c;
    }
  }
}

void displayLCD(String buf) {
  int sep = buf.indexOf('|');
  String l0 = "", l1 = "";
  if (sep != -1) { l0 = buf.substring(0, sep); l1 = buf.substring(sep + 1); }
  else { l0 = buf; }

  if (l0.length() > 16) l0 = l0.substring(0, 16);
  if (l1.length() > 16) l1 = l1.substring(0, 16);

  lcd.clear();
  lcd.setCursor(0, 0); lcd.print(l0);
  lcd.setCursor(0, 1); lcd.print(l1);
}

// 🔹 Опрос кнопок и потенциометра
void handleInputs() {
  unsigned long now = millis();
  if (now - lastDebounce < DEBOUNCE_MS) return;

  int n = digitalRead(BTN_NEXT);
  int p = digitalRead(BTN_PREV);
  int c = digitalRead(BTN_PLAY);
  int v = digitalRead(BTN_VOL);

  // Кнопки NEXT / PREV
  if (n == LOW && lastNext == HIGH) Serial.println("N");
  if (p == LOW && lastPrev == HIGH) Serial.println("P");
  if (v == LOW && lastVol == HIGH) Serial.println("V");

  // PLAY: короткое = C, долгое = MODE
  if (c == LOW) {
    if (playPressTime == 0) playPressTime = now;
    else if (!longPressSent && now - playPressTime >= LONG_PRESS_MS) {
      Serial.println("MODE");
      longPressSent = true;
    }
  } else {
    if (playPressTime > 0 && !longPressSent && now - playPressTime >= 50) {
      Serial.println("C");
    }
    playPressTime = 0;
    longPressSent = false;
  }

  lastNext = n; lastPrev = p; lastPlay = c; lastVol = v;
  lastDebounce = now;
}