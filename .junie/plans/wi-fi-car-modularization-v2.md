---
sessionId: session-260718-111704-npfp
---

# Requirements

### Overview and goals
The goal is to turn existing `motor-test.py` and `speed-pwm-test.py` scripts into a modular web application with advanced control. A key requirement is to migrate current functionality into a new structure (`app.py`, `motor_driver.py`) initially, and then implement a multi-level architecture: a low-level driver for direct PWM control and a high-level controller for logical speed management with encoder-based correction.

**Process Features:**
- **Iterative:** Development is strictly one function/method at a time. Each change is accompanied by a code snippet that the user can run for verification.
- **Test Preservation:** All existing tests are integrated into `app.py`. Launch via command line arguments (CLI). The application outputs results to stdout and exits.
- **Correction Logic:** When deviating from a straight line (based on encoder data), the power of the "leading" motor is reduced and then gradually "grown" back to the calculated level as it levels out.

### Scope
- **Included in the project:**
    - Initial migration: creating `app.py` and `motor_driver.py` while preserving current test logic.
    - Separation of logic into `MotorDriver` (low level) and `CarController` (high level).
    - Implementation of quadrature encoder decoding (based on `motor-test.py`).
    - Implementation of a calibration system (based on `SPEED.MD`) and feedback loop (PID-like correction for straight-line movement).
    - Integration of tests into `app.py` (`--test-motor-speed` flag).
    - Web interface (Flask) and video streaming.
- **Not included in the project:**
    - Hardware changes.
    - Complex navigation algorithms (SLAM, etc.).

### Functional Requirements
- **Two-level control:** 
    - Low level (`MotorDriver`): Direct PWM control and encoder reading.
    - High level (`CarController`): User sets speed in %, the system selects PWM based on calibration.
- **Course Stability:** Automatic correction during straight-line movement: if one side is faster, its PWM is reduced and then gradually returned to the calculated level.
- **Unified CLI tests:** The `--test-motor-speed` command combines motor testing and speed characterization. Supports PWM discretization (step) parameter.
- **Test Autonomy:** Test modes output data to the console and automatically terminate the process.

# Technical Design

### Current Situation
The project contains fragmented testing scripts that work directly with GPIO. This makes it difficult to reuse them in the web application.

### Proposed Architecture
The project will be divided into the following components:
1.  **`motor_driver.py` (`MotorDriver`)**: 
    - Direct work with GPIO and PWM.
    - Quadrature encoder decoding (logic from `motor-test.py`).
    - API: `set_pwm(left, right)`, `get_encoders()`, `stop()`.
2.  **`car_controller.py` (`CarController`)**:
    - Uses `MotorDriver` to execute high-level commands.
    - Mapping `% speed` -> `PWM` (based on `SPEED.MD` data).
    - Feedback algorithm: 
        - If `Enc_Left > Enc_Right`: `L_pwm--` (decrease left power).
        - If `Enc_Right > Enc_Left`: `R_pwm--` (decrease right power).
        - Gradual return to target PWM when leveling.
3.  **`camera_driver.py`**: Video capture.
4.  **`app.py`**: Main entry point.
    - CLI mode: Processing the `--test-motor-speed [STEP]` key. Performs motor checks and TPS measurement with a given PWM step. Results are output to stdout, after which the application terminates.
    - Server mode: Launching Flask.

### Development Process
Strict adherence to "one function at a time":
1.  Agent proposes an implementation of a specific method/code block.
2.  Agent provides a code snippet that the user can run to verify this specific function (without creating many separate files).
3.  Proceeding to the next step only after user approval.

### File Structure
```text
wi-fi-car/
├── app.py              # Entry point (CLI + Flask)
├── motor_driver.py     # Low-level driver (MotorDriver)
├── car_controller.py   # High-level controller (CarController)
├── camera_driver.py    # Camera driver
├── templates/
│   └── index.html      # UI
└── static/
    ├── css/style.css
    └── js/control.js
```

# Delivery Steps

### ✓ Step 1: Base Structure and Current Implementation
Creating the project skeleton with current functionality.

- Creating `app.py` and `motor_driver.py` based on existing code.
- Moving constants and base control functions (`setup`, `run`, `stop`) and encoders from `motor-test.py`.
- Implementing CLI parser in `app.py` with `--test-motor-speed` support.
- Result: The application starts, initializes hardware, and can perform a basic test.

### ✓ Step 2: Refactoring MotorDriver into a Class
Converting procedural code to object-oriented.

- Iteration 1.1: `__init__` method (GPIO initialization).
- Iteration 1.2: `set_pwm(left, right)` method for direct control.
- Iteration 1.3: `get_encoders()` and `reset_encoders()` methods.
- Result: A clean object-oriented interface for working with hardware.

### ✓ Step 3: Creating CarController and Calibration
- Implementing high-level logic based on `MotorDriver`.
- Iteration 2.1: Mapping "Desired speed %" -> "Left PWM" and "Right PWM" (based on `SPEED.MD`).
- Iteration 2.2: `drive(speed_pct, direction)` method.
- Result: The robot drives at a given speed using preset calibration values.

### ✓ Step 4: Straight-line Maintenance Algorithm (Feedback Loop)
- Iteration 3.1: Implementing a loop for monitoring encoder difference during movement.
- Iteration 3.2: Dynamic correction: temporary PWM reduction for the "leading" (faster) motor.
- Iteration 3.3: Gradual "growing" of PWM back to the calculated level.
- Result: Stable straight-line movement with compensation for physical motor differences.

### ✓ Step 5: Implementation of Extended Test --test-motor-speed
- Implementing characterization measurement logic with discretization support.
- Iteration 4.1: Implementing the TPS measurement loop with a step specified via CLI argument (e.g., `--test-motor-speed 10`).
- Iteration 4.2: Formatted output of the results table to stdout and process termination.
- Result: A unified tool for testing motors and obtaining calibration data.

### ✓ Step 6: Web Interface and Video
- Iteration 5.1: Camera driver `camera_driver.py`.
- Iteration 5.2: Flask routes for control and streaming.
- Iteration 5.3: UI (HTML/JS) for remote control.
- Result: A completed modular application.
