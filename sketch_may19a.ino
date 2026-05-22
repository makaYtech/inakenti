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
unsigned long volPressTime = 0;
bool longPressSent = false;
bool longPressSentVol = false;
const unsigned long LONG_PRESS_MS = 800;
const unsigned long DEBOUNCE_MS = 50;
unsigned long lastDebounce = 0;

enum LinkState {
  WAIT_SYN,
  WAIT_ACK,
  CONNECTED
};
LinkState linkState = WAIT_SYN;

const unsigned long CONNECTION_TIMEOUT = 3000;
unsigned long lastRecvTime = 0;

void setup() {
  Serial.begin(115200);
  lcd.begin(16, 2);
  lcd.print("Waiting PC...");
  pinMode(BTN_NEXT, INPUT_PULLUP);
  pinMode(BTN_PREV, INPUT_PULLUP);
  pinMode(BTN_PLAY, INPUT_PULLUP);
  pinMode(BTN_VOL, INPUT_PULLUP);
  lastRecvTime = millis();
}

void loop() {
  while (Serial.available()) {
    char c = Serial.read();
    lastRecvTime = millis();   // фиксируем активность

    if (c == '\n' || c == '\r') {
      if (buffer.length() == 0) continue;

      String cmd = buffer;
      buffer = "";

      // Обработка в зависимости от состояния
      switch (linkState) {
        case WAIT_SYN:
          if (cmd == "SYN") {
            Serial.println("SYN_ACK");
            linkState = WAIT_ACK;
            lcd.clear();
            lcd.print("Handshaking...");
          }
          break;

        case WAIT_ACK:
          if (cmd == "ACK") {
            linkState = CONNECTED;
            lcd.clear();
            lcd.print("Connected");
            delay(500);
            lcd.clear();
          }
          // Если не ACK, остаёмся в WAIT_ACK (ждём ещё)
          break;

        case CONNECTED:
          if (cmd == "PING") {
            Serial.println("PONG");
          } else if (cmd == "EXIT") {
            // ПК вежливо отключается
            linkState = WAIT_SYN;
            lcd.clear();
            lcd.print("Waiting PC...");
          } else {
            // Обычные данные дисплея
            displayLCD(cmd);
          }
          break;
      }
    } else {
      buffer += c;
    }
  }
  if (linkState == WAIT_ACK || linkState == CONNECTED) {
    if (millis() - lastRecvTime > CONNECTION_TIMEOUT) {
      // Таймаут – возвращаемся в начальное состояние
      linkState = WAIT_SYN;
      lcd.clear();
      lcd.print("Waiting PC...");
    }
  }

  // 3. Обработка кнопок (только когда связь установлена)
  if (linkState == CONNECTED) {
    handleInputs();
  }
}

// 🔹 Чтение и отображение данных от ПК
// void handleSerial() {
//   while (Serial.available()) {
//     char c = Serial.read();
//     if (c == '\n' || c == '\r') {
//       if (buffer == "EXIT") {
//         pcReady = false;
//         lcd.clear();
//         lcd.setCursor(0, 0); lcd.print("Waiting PC...");
//         buffer = "";
//         return;
//       }
//       if (buffer.length() > 0) displayLCD(buffer);
//       buffer = "";
//     } else {
//       buffer += c;
//     }
//   }
// }

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
  // if (v == LOW && lastVol == HIGH) Serial.println("V");

  if (v == LOW) {
    if (volPressTime == 0) volPressTime = now;
    else if (!longPressSentVol && now - volPressTime >= LONG_PRESS_MS) {
      Serial.println("LIKE");
      longPressSentVol = true;
    }
  } else {
    if (volPressTime > 0 && !longPressSentVol && now - volPressTime >= 50) {
      Serial.println("V");
    }
    volPressTime = 0;
    longPressSentVol = false;
  }
  
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