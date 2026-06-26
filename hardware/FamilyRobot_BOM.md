# Bill of Materials (BOM) – Family Companion Robot

> Prices are **indicative retail in INR (mid-2026)** and vary ±15% by seller/stock. Links are **search/category links** on trusted Indian sources so they stay valid even when individual listings change. Always verify **BIS / ISI marking** on any mains-voltage item before buying.
>
> Trusted Indian sources used: **Amazon.in**, **Robu.in**, **Robocraze**, **Crazypi**, **ThingBits**, **ElectronicsComp**, **Silverline Components**.

## How to read this
- **Tier** column: `L` = Lean MVP, `R` = Recommended, `P` = Premium/Future-proof.
- Buy all `L` items for the cheapest working robot; add `R` for the full Alexa-class experience; add `P` for best longevity.

---

## A. Core Compute & Power
> **Chosen board:** **Raspberry Pi 5 (8 GB)** (row A1+). The project is **"not Pi-only"** – see `docs/specification.md` and the alternatives note below. Use A1 (Pi 4) only for the Lean tier.
>
> **SBC alternatives (if not Pi 5):** Orange Pi 5 / 5 Plus (RK3588, 6 TOPS NPU, ~₹9,000-14,000) = best value AI; Radxa Rock 5B (~₹12,000+); NVIDIA Jetson Orin Nano (CUDA, ~₹35,000+) = premium vision. Avoid weak boards (Le Potato/Banana Pi).

| # | Item | Tier | Qty | Unit (₹) | Subtotal (₹) | Where to buy (search link) |
|---|---|---|---|---|---|---|
| A1 | Raspberry Pi 4 Model B (4 GB) | L | 1 | 5,500 | 5,500 | - [Robu](https://robu.in/?s=raspberry+pi+4+model+b+4gb)<br>- [Amazon.in](https://www.amazon.in/s?k=raspberry+pi+4+model+b+4gb)<br>- [Crazypi](https://www.crazypi.com/?s=raspberry+pi+4) |
| A1+ | **Raspberry Pi 5 (8 GB)** ☑ *chosen* | R | 1 | 9,000 | 9,000 | - [Robu](https://robu.in/?s=raspberry+pi+5+8gb)<br>- [Robocraze](https://robocraze.com/search?q=raspberry%20pi%205%208gb)<br>- [Amazon.in](https://www.amazon.in/s?k=raspberry+pi+5+8gb) |
| A2 | 27 W USB-C PSU (Pi 5) / 15 W (Pi 4) | L | 1 | 800 | 800 | - [Robu](https://robu.in/?s=raspberry+pi+official+power+supply)<br>- [Amazon.in](https://www.amazon.in/s?k=raspberry+pi+official+power+supply) |
| A3 | 128 GB high-endurance microSD (SanDisk Max Endurance / Samsung PRO Endurance) | L | 1 | 1,800 | 1,800 | - [Amazon.in](https://www.amazon.in/s?k=sandisk+max+endurance+128gb+microsd) |
| A4 | Active-cooling case (heatsink + fan) | L | 1 | 800 | 800 | - [Robu](https://robu.in/?s=raspberry+pi+4+case+fan)<br>- [Amazon.in](https://www.amazon.in/s?k=raspberry+pi+4+case+with+fan) |
| A5 | Waveshare UPS HAT (C) + 2× 18650 cells | R | 1 | 2,500 | 2,500 | - [Robu](https://robu.in/?s=waveshare+ups+hat)<br>- [Robocraze](https://robocraze.com/search?q=ups%20hat) |
| A6 | **Upgrade:** USB 3 SSD 256 GB + SATA-USB enclosure (faster model load, durable) | P | 1 | 2,800 | 2,800 | - [Amazon.in](https://www.amazon.in/s?k=256gb+usb+3+ssd) |

---

## B. Audio (voice in/out)

| # | Item | Tier | Qty | Unit (₹) | Subtotal (₹) | Where to buy (search link) |
|---|---|---|---|---|---|---|
| B1 | ReSpeaker 2-Mic Pi HAT (far-field, RGB ring) | R | 1 | 3,200 | 3,200 | - [Robu](https://robu.in/?s=respeaker+2+mic+hat)<br>- [ThingBits](https://thingbits.in/search?q=respeaker) |
| B1-alt | **Lean:** USB mini omni microphone | L | 1 | 600 | 600 | - [Amazon.in](https://www.amazon.in/s?k=usb+mini+microphone+for+raspberry+pi) |
| B2 | 5 W powered speaker (3.5 mm/USB) | L | 1 | 900 | 900 | - [Amazon.in](https://www.amazon.in/s?k=mini+usb+powered+speaker) |
| B2-alt | **Upgrade:** ReSpeaker 4-Mic Array (best far-field) | P | 1 | 4,500 | 4,500 | - [Robu](https://robu.in/?s=respeaker+4+mic+array) |
| B3 | USB sound card / DAC (if mic HAT not used) | L | 1 | 400 | 400 | - [Amazon.in](https://www.amazon.in/s?k=usb+sound+card+adapter) |

---

## C. Vision

| # | Item | Tier | Qty | Unit (₹) | Subtotal (₹) | Where to buy (search link) |
|---|---|---|---|---|---|---|
| C1 | Raspberry Pi Camera Module 3 (standard) | R | 1 | 2,800 | 2,800 | - [Robu](https://robu.in/?s=raspberry+pi+camera+module+3)<br>- [Robocraze](https://robocraze.com/search?q=pi%20camera%20module%203) |
| C1-alt | **Lean:** USB webcam 1080p | L | 1 | 1,200 | 1,200 | - [Amazon.in](https://www.amazon.in/s?k=1080p+usb+webcam) |
| C2 | Camera ribbon cable (for Pi 5 – different connector) | P | 1 | 250 | 250 | - [Robu](https://robu.in/?s=raspberry+pi+5+camera+cable) |

---

## D. Smart-Home Control (modular – pick per appliance)
> **Safety first:** any load ≥ 6 A (geyser, AC, pump, washing machine, iron) must use a **BIS-marked smart plug** or a properly rated **contactor in an enclosure**, installed by a licensed electrician. Use bare relays only for low-load lighting/fans and **never** for direct mains switching without isolation.

| # | Item | Tier | Qty | Unit (₹) | Subtotal (₹) | Where to buy (search link) |
|---|---|---|---|---|---|---|
| D1 | 8-channel 5 V opto-isolated relay module | L | 1 | 700 | 700 | - [Robu](https://robu.in/?s=8+channel+relay+module)<br>- [Robocraze](https://robocraze.com/search?q=8%20channel%20relay) |
| D2 | Wi-Fi smart plug 16 A (TP-Link Tapo P110 / Wipro / Syska) – geyser, AC, pump, washer | R | 4 | 1,200 | 4,800 | - [Amazon.in](https://www.amazon.in/s?k=tp-link+tapo+p110+16a+smart+plug) |
| D3 | Wi-Fi smart plug 6 A/10 A (lights/fan/charger) | R | 2 | 800 | 1,600 | - [Amazon.in](https://www.amazon.in/s?k=wifi+smart+plug+6a) |
| D4 | IR blaster – Broadlink RM4 Mini / ESP-Tasmota IR (TV, legacy AC, set-top) | R | 1 | 1,500 | 1,500 | - [Amazon.in](https://www.amazon.in/s?k=broadlink+rm4+mini+ir)<br>- [Robu](https://robu.in/?s=ir+transmitter+module) |
| D5 | Wi-Fi smart bulbs (RGB, BIS) | R | 4 | 800 | 3,200 | - [Amazon.in](https://www.amazon.in/s?k=wifi+smart+bulb+rgb+bis) |
| D6 | AC contactor 25 A + enclosure (hard-wired pump/geyser) | P | 1 | 1,500 | 1,500 | - [Amazon.in](https://www.amazon.in/s?k=ac+contactor+25a) |
| D7 | Zigbee USB coordinator (SonOff Zigbee 3.0 dongle) | P | 1 | 1,800 | 1,800 | - [Amazon.in](https://www.amazon.in/s?k=sonoff+zigbee+3.0+usb+dongle)<br>- [Robu](https://robu.in/?s=zigbee+coordinator) |
| D8 | Zigbee smart switches/sensors (door, motion, leak, smoke) | P | 4 | 1,100 | 4,400 | - [Amazon.in](https://www.amazon.in/s?k=zigbee+smart+sensor) |

---

## E. Interface, Display & Indicators

| # | Item | Tier | Qty | Unit (₹) | Subtotal (₹) | Where to buy (search link) |
|---|---|---|---|---|---|---|
| E1 | 1.3" I2C OLED (status/clock/expression) | R | 1 | 450 | 450 | - [Robu](https://robu.in/?s=1.3+inch+oled+i2c)<br>- [Robocraze](https://robocraze.com/search?q=oled%20display) |
| E1+ | **Upgrade:** 3.5" round IPS LCD (animated face) | P | 1 | 1,800 | 1,800 | - [Robu](https://robu.in/?s=round+lcd+display) |
| E2 | WS2812B RGB LED ring (listening/speaking state) | R | 1 | 350 | 350 | - [Robu](https://robu.in/?s=ws2812b+ring) |
| E3 | Hardware mic-mute toggle switch + status LED | R | 1 | 150 | 150 | - [Robu](https://robu.in/?s=toggle+switch) |
| E4 | Momentary push buttons (override/confirm) | L | 4 | 300 | 120 | - [Robu](https://robu.in/?s=push+button+tactile) |

---

## F. Wiring, Prototyping & Enclosure

| # | Item | Tier | Qty | Unit (₹) | Subtotal (₹) | Where to buy (search link) |
|---|---|---|---|---|---|---|
| F1 | Jumper wires (M-M, M-F, F-F) + breadboard | L | 1 | 350 | 350 | - [Robu](https://robu.in/?s=jumper+wires+breadboard) |
| F2 | GPIO 40-pin ribbon + breakout (optional) | L | 1 | 250 | 250 | - [Robu](https://robu.in/?s=gpio+ribbon+cable+breakout) |
| F3 | Enclosure: 3D-print filament **or** ready ABS box + acoustic grille cloth | R | 1 | 1,200 | 1,200 | - [Amazon.in](https://www.amazon.in/s?k=abs+project+enclosure+box)<br>- [Robu](https://robu.in/?s=project+enclosure) |
| F4 | DIN-rail enclosure for mains/relay section (electrician install) | P | 1 | 900 | 900 | - [Amazon.in](https://www.amazon.in/s?k=din+rail+enclosure+box) |
| F5 | Misc (resistors, mic foam, screws, heat-shrink, fuses, terminal blocks) | L | 1 | 500 | 500 | - [Robu](https://robu.in/?s=electronics+component+kit) |

---

## G. Phase 2 – Satellite Units (kitchen / bedrooms)

| # | Item | Tier | Qty | Unit (₹) | Subtotal (₹) | Where to buy (search link) |
|---|---|---|---|---|---|---|
| G1 | Raspberry Pi Zero 2 W | P | 2 | 2,000 | 4,000 | - [Robu](https://robu.in/?s=raspberry+pi+zero+2+w)<br>- [Crazypi](https://www.crazypi.com/?s=pi+zero+2+w) |
| G2 | Mini USB mic + small speaker (per satellite) | P | 2 | 900 | 1,800 | - [Amazon.in](https://www.amazon.in/s?k=mini+usb+microphone+speaker) |
| G3 | microSD 32 GB + PSU (per satellite) | P | 2 | 1,100 | 2,200 | - [Amazon.in](https://www.amazon.in/s?k=raspberry+pi+zero+power+supply) |

---

## Cost Roll-Up

### Lean MVP ('L' items – cheapest working robot)
*Pi 4 + PSU + SD + case + USB mic + speaker + sound card + USB webcam + 8-ch relay + jumpers/breadboard + misc.*

| Bucket | Cost (₹) |
|---|---|
| Compute & power (A1-A4) | 8,900 |
| Audio (B1-alt, B2, B3) | 1,900 |
| Vision (C1-alt) | 1,200 |
| Smart-home (D1) | 700 |
| Interface (E4) | 120 |
| Wiring/enclosure (F1, F2, F5) | 1,350 |
| **Lean subtotal** | **~14,170** |
| +10% contingency | ~1,400 |
| **Lean total** | **~₹15,500** |

---

### Recommended ('L' + 'R' – full Alexa-class experience)
*Adds UPS, ReSpeaker HAT, Pi Camera 3, 4× 16 A + 2× 6 A smart plugs, IR blaster, smart bulbs, OLED, RGB ring, mute switch, proper enclosure.*

| Bucket | Cost (₹) |
|---|---|
| Compute & power (A1-A5) | 11,400 |
| Audio (B1, B2) | 4,100 |
| Vision (C1) | 2,800 |
| Smart-home (D2, D3, D4, D5) | 11,100 |
| Interface (E1, E2, E3, E4) | 1,070 |
| Wiring/enclosure (F1, F2, F3, F5) | 2,550 |
| **Recommended subtotal** | **~33,020** |
| Swap-out savings (USB mic instead of HAT, webcam instead of Pi cam) | -4,800 *if budget-trimming* |
| +10% contingency | ~3,300 |
| **Recommended total** | **~₹33,000-36,000** |

---

### Premium / Future-proof ('L' + 'R' + 'P' – Pi 5, sensors, satellites)
*Adds Pi 5 8 GB (instead of Pi 4), SSD, 4-mic array, round LCD, contactor box, Zigbee hub + 4 sensors, 2 satellite units.*

| Bucket | Cost (₹) |
|---|---|
| Recommended base | 33,000 |
| Pi 5 8 GB upgrade (delta over Pi 4) | +3,500 |
| SSD (A6) | +2,800 |
| 4-mic array (B2-alt) | +4,500 |
| Round LCD (E1+) | +1,800 |
| Contactor box (D6) | +1,500 |
| Zigbee hub + sensors (D7, D8) | +6,200 |
| Satellites (G1-G3) | +8,000 |
| **Premium total** | **~₹61,000** |

---

## Recurring Costs

| Item | Cost |
|---|---|
| All core software (OS, llama.cpp/Ollama, faster-whisper, Piper/Kokoro, openWakeWord, MediaPipe, SQLite, Mosquitto, HA) | **₹0 – open-source** |
| Electricity (Pi 4 ~5 W, Pi 5 ~8 W, 24×7) | ~₹40-70 / month |
| Optional cloud LLM/STT (opt-in, cached) | < ₹500 / month (often near ₹0 with local-first) |
| Music (YouTube / YouTube Music + local MP3 library) | reuse existing access – **₹0 extra** |
| WhatsApp/calls via family Android phone | **₹0** (uses your existing number/plan) |
| **Mandatory recurring total** | **~₹50 / month (electricity only)** |

---

## Buying Tips (India)
- Prefer **Robu.in / Robocraze / ThingBits / Crazypi** for Pi boards, HATs, relays, sensors – genuine stock and GST invoice.
- Prefer **Amazon.in** for smart plugs, bulbs, IR blasters, SD cards, webcams – check for **BIS/ISI mark** and 16 A rating for heavy loads.
- Buy the **official Pi PSU** (cheap clones cause under-voltage/throttling).
- For mains wiring (geyser/pump/AC), **hire a licensed electrician**; do not DIY high-current contactor wiring.
- Keep the **mic-mute** and **manual override** switches – they are cheap and essential for trust and safety.

---

## Selling as a Product (volume path – not needed for personal build)
> This BOM is a **prototype/maker** BOM. To sell the device at volume, plan a separate **manufacturable BOM**:

- **Compute:** swap Pi 5 for **Orange Pi 5 / RK3588 (6 TOPS NPU, ~₹9,000-14,000)** for best AI-cost at scale, or a custom carrier.
- **Custom PCB/HAT** integrating mic AEC front-end, RGB ring, OLED, mute switch (replaces loose modules).
- **Tooled/injection-moulded enclosure** with an enclosed, certified **mains module** (BIS) instead of loose relays.
- **Certification budget:** BIS (electrical), **WPC/ETA** (radio), EMC/EMI – see spec §5.7.
- **Per-unit-at-scale costing, warranty/returns (RMA), and an OTA/provisioning service.**
