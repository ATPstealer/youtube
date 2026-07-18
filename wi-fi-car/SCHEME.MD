### ЛЕВЫЙ МОТОР
- **P4:** OUT1 + OUT2
- **ENA** → pin 32 / GPIO12
- **IN1** → pin 38 / GPIO20
- **IN2** → pin 40 / GPIO21

### ПРАВЫЙ МОТОР
- **P3:** OUT3 + OUT4
- **ENB** → pin 33 / GPIO13
- **IN3** → pin 35 / GPIO19
- **IN4** → pin 37 / GPIO26

### MD ЛОГИКА
- **3.3V** → pin 17
- **GND**  → pin 6

### ПРАВЫЙ ЭНКОДЕР
- **3.3V** → pin 1
- **GND**  → pin 9
- **A**    → pin 11 / GPIO17
- **B**    → pin 13 / GPIO27

### ЛЕВЫЙ ЭНКОДЕР
- **3.3V** → pin 1
- **GND**  → pin 14
- **A**    → pin 8 / GPIO14
- **B**    → pin 10 / GPIO15

### СХЕМА GPIO
```text
[ENC_VCC]     3.3V (1) (2) 5V
             GPIO2 (3) (4) 5V
             GPIO3 (5) (6) GND [MD_GND]
             GPIO4 (7) (8) GPIO14 [L_ENC_A]
 [R_ENC_GND]   GND (9) (10) GPIO15 [L_ENC_B]
 [R_ENC_A]  GPIO17 (11) (12) GPIO18
 [R_ENC_B]  GPIO27 (13) (14) GND [L_ENC_GND]
            GPIO22 (15) (16) GPIO23
 [MD_VCC]     3.3V (17) (18) GPIO24
            GPIO10 (19) (20) GND
             GPIO9 (21) (22) GPIO25
            GPIO11 (23) (24) GPIO8
               GND (25) (26) GPIO7
             ID_SD (27) (28) ID_SC
             GPIO5 (29) (30) GND
             GPIO6 (31) (32) GPIO12 [L_ENA]
 [R_ENB]    GPIO13 (33) (34) GND
 [R_IN3]    GPIO19 (35) (36) GPIO16
 [R_IN4]    GPIO26 (37) (38) GPIO20 [L_IN1]
               GND (39) (40) GPIO21 [L_IN2]
```

