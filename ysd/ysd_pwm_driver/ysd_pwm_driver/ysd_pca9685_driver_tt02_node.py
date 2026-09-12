# ROS2 コア
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node

# ROS2
from ysd_msgs.msg import PWMDriveCommandTT02 as PWMDriveCommand

# 自作
from .pca9685 import PCA9685

class YSDPCA9685DriverTT02Node(Node):
    def __init__(self):
        """

        PWM 信号を受け取って PCA9685 を操作するノードです.

        """
        super().__init__("ysd_pca9685_driver_tt02_node")

        # パラメータ定義
        self.declare_parameter("interface.topic.control_pwm", "/control/pwm")
        self.declare_parameter("driver.bus_num", 7)
        self.declare_parameter("driver.address", 0x40)
        self.declare_parameter("driver.osc_freq_hz", 25_000_000)
        self.declare_parameter("driver.read_hz", 50.0)
        self.declare_parameter("channels.steering", 0)
        self.declare_parameter("channels.throttle", 1)
        self.declare_parameter("verbose", 1)

        # パラメータ参照
        self.topic_control_pwm = self.get_parameter("interface.topic.control_pwm").get_parameter_value().string_value
        self.bus_num = self.get_parameter("driver.bus_num").get_parameter_value().integer_value
        self.address = self.get_parameter("driver.address").get_parameter_value().integer_value
        self.osc_freq_hz = self.get_parameter("driver.osc_freq_hz").get_parameter_value().integer_value
        self.read_hz = self.get_parameter("driver.read_hz").get_parameter_value().double_value
        self.channel_steering = self.get_parameter("channels.steering").get_parameter_value().integer_value
        self.channel_throttle = self.get_parameter("channels.throttle").get_parameter_value().integer_value
        self.verbose = self.get_parameter("verbose").get_parameter_value().integer_value

        # サブスクリプション
        self.subscription = self.create_subscription(PWMDriveCommand, self.topic_control_pwm, self._on_pwm, 10)

        # PCA9685
        self.pca = PCA9685(bus_num=self.bus_num, address=self.address, osc_freq_hz=self.osc_freq_hz, freq_hz=self.read_hz)

        # CLI ログ出力用ロガー
        self.logger = self.get_logger()

        # CLI ログ出力
        if self.verbose >= 2:
            self.logger.info(f"Parameters:")
            self.logger.info(f"  interface:")
            self.logger.info(f"    topic:")
            self.logger.info(f"      control_pwm: {self.topic_control_pwm}")
            self.logger.info(f"  driver:")
            self.logger.info(f"    bus_num: {self.bus_num}")
            self.logger.info(f"    address: {self.address}")
            self.logger.info(f"    osc_freq_hz: {self.osc_freq_hz}")
            self.logger.info(f"    read_hz: {self.read_hz}")
            self.logger.info(f"  channels:")
            self.logger.info(f"    steering: {self.channel_steering}")
            self.logger.info(f"    throttle: {self.channel_throttle}")
            self.logger.info(f"  verbose: {self.verbose}")

    def _on_pwm(self, sub_msg: PWMDriveCommand):
        """

        受け取ったPWMのパルス幅を使用してPCA9685に信号を送信する。

        Args:
            msg (PWMDriveCommand): PWM信号のパルス幅

        """
        # ログ出力
        if self.verbose >= 2:
            self.logger.info(f"Mapped command: steering={sub_msg.steering:.3f}, throttle={sub_msg.throttle:.3f}")

        # ドライバに入力された PWM 幅を変更
        self.pca.set_pwm_us(self.channel_steering, sub_msg.steering)
        self.pca.set_pwm_us(self.channel_throttle, sub_msg.throttle)

def main(args=None) -> None:
    rclpy.init(args=args)

    node = YSDPCA9685DriverTT02Node()

    try:
        rclpy.spin(node)
        
    except (KeyboardInterrupt, ExternalShutdownException):
        pass

    except RuntimeError as e:
        shutdown_conversion_error = ("Unable to convert call argument to Python object" in str(e) and not rclpy.ok())
        if not shutdown_conversion_error:
            raise

    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == "__main__":
    main()