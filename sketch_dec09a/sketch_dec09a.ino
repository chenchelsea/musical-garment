void setup() {
  // put your setup code here, to run once:
  Serial.begin(9600);
  pinMode(2, OUTPUT);
  pinMode(3, OUTPUT);
  pinMode(4, OUTPUT);
  pinMode(5, OUTPUT);
  pinMode(6, OUTPUT);
  pinMode(7, OUTPUT);
  pinMode(8, OUTPUT);
  pinMode(9, OUTPUT);
  pinMode(10, OUTPUT);
  pinMode(11, OUTPUT);
  pinMode(12, OUTPUT);
  pinMode(13, OUTPUT);
  pinMode(14, OUTPUT);
  pinMode(15, OUTPUT);
  pinMode(16, OUTPUT);
  pinMode(17, OUTPUT);
  pinMode(18, OUTPUT);
  pinMode(19, OUTPUT);
  pinMode(20, OUTPUT);
  pinMode(21, OUTPUT);
  pinMode(22, OUTPUT);
  pinMode(23, OUTPUT);
  pinMode(24, OUTPUT);
  pinMode(25, OUTPUT);
  pinMode(26, OUTPUT);
  pinMode(27, OUTPUT);
  pinMode(28, OUTPUT);
  pinMode(29, OUTPUT);
  pinMode(30, OUTPUT);
  pinMode(31, OUTPUT);
  pinMode(32, OUTPUT);
  pinMode(33, OUTPUT);
  pinMode(34, OUTPUT);
  pinMode(35, OUTPUT);
  pinMode(36, OUTPUT);
  pinMode(37, OUTPUT);
  pinMode(38, OUTPUT);
  pinMode(39, OUTPUT);
  pinMode(40, OUTPUT);
  pinMode(41, OUTPUT);
  pinMode(42, OUTPUT);
  pinMode(43, OUTPUT);
  pinMode(44, OUTPUT);
  pinMode(45, OUTPUT);
  pinMode(46, OUTPUT);
  pinMode(47, OUTPUT);
  pinMode(48, OUTPUT);

}

void loop() {
  // put your main code here, to run repeatedly:
  while (Serial.available() > 0) {
    int redPin1 = Serial.parseInt();
    int red = Serial.parseInt();
    int greenPin1 = Serial.parseInt();
    int green = Serial.parseInt();
    int bluePin1 = Serial.parseInt();
    int blue = Serial.parseInt();
    /*int redPin2 = Serial.parseInt();
      int greenPin2 = Serial.parseInt();
      int bluePin2 = Serial.parseInt();*/
    if (Serial.read() == '\n') {
      analogWrite(redPin1, red);
      analogWrite(greenPin1, green);
      analogWrite(bluePin1, blue);
      /*analogWrite(redPin2, red);
        analogWrite(greenPin2, green);
        analogWrite(bluePin2, blue);*/
      delay(100);
      /*digitalWrite(redPin1, LOW);
      digitalWrite(greenPin1, LOW);
      digitalWrite(bluePin1, LOW);*/

      /*digitalWrite(redPin2, LOW);
        digitalWrite(greenPin2, LOW);
        digitalWrite(bluePin2, LOW);*/
    }
    else {
      int redPin2 = Serial.parseInt();
      int greenPin2 = Serial.parseInt();
      int bluePin2 = Serial.parseInt();
      if (Serial.read() == '\n') {
        analogWrite(redPin1, red);
        analogWrite(greenPin1, green);
        analogWrite(bluePin1, blue);
        analogWrite(redPin2, red);
        analogWrite(greenPin2, green);
        analogWrite(bluePin2, blue);
        delay(100);
        /*digitalWrite(redPin1, LOW);
        digitalWrite(greenPin1, LOW);
        digitalWrite(bluePin1, LOW);

        digitalWrite(redPin2, LOW);
        digitalWrite(greenPin2, LOW);
        digitalWrite(bluePin2, LOW);*/
      }
    }
  }
  /*while (Serial.available()>0){
    int pin =Serial.parseInt();
    int brightness =Serial.parseInt();
    analogWrite(pin,brightness);
    delay(500);
    digitalWrite(pin,LOW);
    }*/

}
