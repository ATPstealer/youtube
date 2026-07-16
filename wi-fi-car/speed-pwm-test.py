#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time
import logging
import csv

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# =================================================================
# ОПРЕДЕЛЕНИЕ ПИНОВ (BCM нумерация согласно SCHEME.MD)
# =================================================================

# ЛЕВЫЙ МОТОР
L_ENA = 12  # PWM
L_IN1 = 20
L_IN2 = 21

# ПРАВЫЙ МОТОР
R_ENB = 13  # PWM
R_IN3 = 19
R_IN4 = 26

# ЭНКОДЕРЫ
L_ENC_A = 14
L_ENC_B = 15
R_ENC_A = 17
R_ENC_B = 27

# =================================================================
# ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
# =================================================================

left_counter = 0
right_counter = 0
p_left = None
p_right = None

# =================================================================
# ОБРАБОТЧИКИ ПРЕРЫВАНИЙ
# =================================================================

def left_encoder_callback(channel):
    global left_counter
    left_counter += 1

def right_encoder_callback(channel):
    global right_counter
    right_counter += 1

# =================================================================
# УПРАВЛЕНИЕ GPIO
# =================================================================

def setup():
    global p_left, p_right
    
    logging.info("Инициализация GPIO...")
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    # Моторы
    motor_pins = [L_ENA, L_IN1, L_IN2, R_ENB, R_IN3, R_IN4]
    for pin in motor_pins:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)

    # ШИМ
    p_left = GPIO.PWM(L_ENA, 1000)
    p_right = GPIO.PWM(R_ENB, 1000)
    p_left.start(0)
    p_right.start(0)

    # Энкодеры
    encoder_pins = [L_ENC_A, L_ENC_B, R_ENC_A, R_ENC_B]
    for pin in encoder_pins:
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    # Регистрация прерываний (для максимальной точности на оба канала и оба фронта)
    GPIO.add_event_detect(L_ENC_A, GPIO.BOTH, callback=left_encoder_callback)
    GPIO.add_event_detect(L_ENC_B, GPIO.BOTH, callback=left_encoder_callback)
    GPIO.add_event_detect(R_ENC_A, GPIO.BOTH, callback=right_encoder_callback)
    GPIO.add_event_detect(R_ENC_B, GPIO.BOTH, callback=right_encoder_callback)
    
    logging.info("Инициализация завершена.")

def run_motors(speed):
    """Запуск обоих моторов вперед с заданной скоростью ШИМ"""
    speed = max(0, min(100, speed))
    
    # Левый вперед
    GPIO.output(L_IN1, GPIO.HIGH)
    GPIO.output(L_IN2, GPIO.LOW)
    p_left.ChangeDutyCycle(speed)
    
    # Правый вперед
    GPIO.output(R_IN3, GPIO.HIGH)
    GPIO.output(R_IN4, GPIO.LOW)
    p_right.ChangeDutyCycle(speed)

def stop_motors():
    p_left.ChangeDutyCycle(0)
    p_right.ChangeDutyCycle(0)
    GPIO.output(L_IN1, GPIO.LOW)
    GPIO.output(L_IN2, GPIO.LOW)
    GPIO.output(R_IN3, GPIO.LOW)
    GPIO.output(R_IN4, GPIO.LOW)

# =================================================================
# ТЕСТ СКОРОСТИ
# =================================================================

def measure_speed(pwm_value, duration=2.0):
    global left_counter, right_counter
    
    logging.info(f"Тестирование ШИМ: {pwm_value}%")
    
    # Сброс и разгон
    stop_motors()
    time.sleep(0.5)
    run_motors(pwm_value)
    
    # Даем 1 секунду на стабилизацию скорости
    time.sleep(1.0)
    
    # Начало измерения
    left_counter = 0
    right_counter = 0
    start_time = time.time()
    
    time.sleep(duration)
    
    end_time = time.time()
    stop_motors()
    
    dt = end_time - start_time
    # Вычисляем скорость в тиках в секунду
    l_speed = left_counter / dt
    r_speed = right_counter / dt
    
    logging.info(f"Результаты для {pwm_value}%: Левый={l_speed:.1f} tps, Правый={r_speed:.1f} tps")
    return l_speed, r_speed

def main():
    setup()
    results = []
    # Диапазон ШИМ: от 0 до 100 с шагом 5 для более плавного графика
    pwm_values = range(1, 101, 1)
    
    try:
        logging.info("Начало серии тестов...")
        for pwm in pwm_values:
            l_s, r_s = measure_speed(pwm)
            results.append({
                'pwm': pwm,
                'left_speed': round(l_s, 2),
                'right_speed': round(r_s, 2)
            })
            time.sleep(0.5) # Небольшой отдых для моторов
            
        # Запись результатов в CSV
        filename = 'motor_speed_curve.csv'
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['pwm', 'left_speed', 'right_speed'])
            writer.writeheader()
            writer.writerows(results)
            
        logging.info(f"Тестирование завершено. Данные сохранены в {filename}")
        
        print("\nИтоговая таблица:")
        print("PWM (%) | Левый (tps) | Правый (tps)")
        print("-" * 36)
        for res in results:
            print(f"{res['pwm']:7} | {res['left_speed']:11} | {res['right_speed']:12}")

    except KeyboardInterrupt:
        logging.info("Тест прерван пользователем.")
    finally:
        stop_motors()
        GPIO.cleanup()
        logging.info("GPIO очищен.")

if __name__ == "__main__":
    main()
