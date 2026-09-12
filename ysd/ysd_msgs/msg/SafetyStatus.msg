std_msgs/Header header

uint8 REASON_NONE=0
uint8 REASON_EMERGENCY_STOP=1
uint8 REASON_COMMAND_TIMEOUT=2
uint8 REASON_GAMEPAD_TIMEOUT=3
uint8 REASON_INFERENCE_TIMEOUT=4
uint8 REASON_CAMERA_TIMEOUT=5
uint8 REASON_INVALID_COMMAND=6

bool safe
bool output_enabled
uint8 reason_code
string message