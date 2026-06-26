# Board Specifications: Arduino Uno R3 SMD

This document details the specifications of the micro-controller board currently connected to your laptop, its port configurations, and its capabilities within the **Family Companion Robot** project.

---

## 1. Connected Device Overview

* **Board Type:** Arduino Uno R3 (SMD Edition Clone)
* **USB-to-Serial Chip:** FTDI FT232R (identified by Hardware ID `VID_0403+PID_6001`)
* **Connection Port:** `COM3` (Serial protocol over USB)
* **Status:** Connected and successfully tested (uploaded idle stop sketch, built-in LED turned OFF).

---

## 2. Technical Specifications

| Parameter | Specification / Value |
| :--- | :--- |
| **Microcontroller** | Microchip ATmega328P (8-bit AVR) |
| **Package Type** | Surface Mount Device (SMD / TQFP-32) |
| **Operating Voltage** | 5V |
| **Input Voltage (Recommended)** | 7V to 12V (via DC barrel jack) |
| **Input Voltage (Limits)** | 6V to 20V |
| **Digital I/O Pins** | **14** (Pins D0 to D13) |
| **PWM Digital I/O Pins** | **6** (Pins D3, D5, D6, D9, D10, D11) |
| **Analog Input Pins** | **6** (Pins A0 to A5) |
| **DC Current per I/O Pin** | 20 mA (Recommended), 40 mA (Absolute Maximum) |
| **DC Current for 3.3V Pin** | 50 mA |
| **Flash Memory** | 32 KB (of which 0.5 KB is used by the bootloader) |
| **SRAM** | 2 KB |
| **EEPROM** | 1 KB |
| **Clock Speed** | 16 MHz (External crystal oscillator) |
| **Built-in LED** | Connected to Digital Pin 13 |

---

## 3. Capabilities & Use Cases

The Arduino Uno R3 SMD is a versatile micro-controller. In the context of your **Family Companion + Home-Automation Robot**, it can serve as a hardware bridge between the high-level brain (Raspberry Pi 5 / Laptop) and the physical world.

### A. Home Automation (Appliance Control)
* **Relay Toggling:** Can drive 5V relay modules (4-channel, 8-channel) using digital pins to switch household appliances (lights, fans, water pump, geyser) on and off.
* **AC Fan Dimming:** Can be paired with an AC dimmer module using zero-crossing detection (Interrupt pins D2/D3) to control ceiling fan speeds.
* **IR Blasting:** Can interface with an infrared LED and receiver to emulate remote controls for legacy TVs, ACs, and set-top boxes.

### B. Sensor Interfacing (Environmental Awareness)
* **Analog Sensors:** Can read analog sensors directly (e.g., LDR for room brightness, soil moisture sensors, analog sound sensors).
* **Digital & Protocol Sensors:** Read temperature/humidity (DHT11, DHT22, AM2302) or ultrasonic rangefinders (HC-SR04) for obstacle/movement detection.

### C. Visual Feedback & Indicators
* **RGB LED Ring Control:** Control Neopixel (WS2812B) addressable LED rings to act as the listening/speaking state indicator ring (like the Alexa blue ring).
* **Display Output:** Drive small I2C OLED (SSD1306) displays or character LCD screens to show the robot's expression, time, or current status.

### D. Primary System Integration
* **Serial Bridge:** The board communicates with your laptop/Raspberry Pi over USB Serial at standard baud rates (e.g., 9600 or 115200).
* **Python Control:** You can use the python library `pyserial` on the primary brain to send commands (e.g., `"TURN_ON_LIGHT_1"`) or poll sensor states (e.g., `"TEMP?"`) from the Arduino.
