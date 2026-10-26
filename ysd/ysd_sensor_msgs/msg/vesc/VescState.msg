std_msgs/Header header

# VESC生値
float32 erpm  # [rpm]
float32 duty_cycle  # [-1.0, 1.0]
float32 v_in  # Voltage In [V]
float32 motor_current  # [A]
float32 temp_fet  # [deg C]
int32   tachometer  # 積算 (ERPM換算の電気角カウント)
int32   fault_code

# 換算値 (ノード側で計算)
float32 speed           # 車体前進速度 [m/s]