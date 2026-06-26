void setup() {
  // Initialize digital pin LED_BUILTIN as an output.
  pinMode(LED_BUILTIN, OUTPUT);
  // Initialize serial communication at 9600 bits per second.
  Serial.begin(9600);
  while (!Serial) {
    ; // Wait for serial port to connect.
  }
  Serial.println("Arduino Uno R3 SMD Test Initialized.");
}

void loop() {
  Serial.println("--- Starting Blink Cycle ---");
  for (int i = 0; i < 5; i++) {
    Serial.print("Blink ");
    Serial.println(i + 1);
    
    digitalWrite(LED_BUILTIN, HIGH);
    Serial.println("LED ON");
    delay(500); // Turn LED on for 500ms
    
    digitalWrite(LED_BUILTIN, LOW);
    Serial.println("LED OFF");
    delay(500); // Turn LED off for 500ms
  }
  
  Serial.println("Pausing for 30 seconds...");
  // 30,000 milliseconds = 30 seconds
  delay(30000);
}

