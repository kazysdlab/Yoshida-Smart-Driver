# 型
from typing import cast

# ROS2 コア
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node

# ROS2
from ysd_msgs.msg import NormalizedDriveCommandTT02 as NormalizedDriveCommand
from ysd_msgs.msg import PWMDriveCommandTT02 as PWMDriveCommand

class YSDPWMMapperTT02(Node):
    """

    このノードは, YSD 固有の正規化された操作信号を PWM 信号に変換するノードです.

    """

    def __init__(self):
        super().__init__("ysd_pwm_mapper_tt02_node")

        # パラメータ定義
        self.declare_parameter("interface.topic.control_select", "/control/select")
        self.declare_parameter("interface.topic.control_pwm", "/control/pwm")
        self.declare_parameter("map.steering.input", [-1.0, 1.0])
        self.declare_parameter("map.throttle.input", [-1.0, 1.0])
        self.declare_parameter("map.steering.output", [1500, 2500])
        self.declare_parameter("map.throttle.output", [1500, 2500])
        self.declare_parameter("verbose", 2)

        # パラメータ参照
        self.topic_control_select = self.get_parameter("interface.topic.control_select").get_parameter_value().string_value
        self.topic_control_pwm = self.get_parameter("interface.topic.control_pwm").get_parameter_value().string_value
        self.map_steering_input_raw = self.get_parameter("map.steering.input").get_parameter_value().double_array_value
        self.map_throttle_input_raw = self.get_parameter("map.throttle.input").get_parameter_value().double_array_value        
        self.map_steering_output_raw = self.get_parameter("map.steering.output").get_parameter_value().integer_array_value
        self.map_throttle_output_raw = self.get_parameter("map.throttle.output").get_parameter_value().integer_array_value
        self.verbose = self.get_parameter("verbose").get_parameter_value().integer_value

        # 型の強制キャスト
        self.map_steering_input = list(self.map_steering_input_raw)
        self.map_throttle_input = list(self.map_throttle_input_raw)
        self.map_steering_output = list(self.map_steering_output_raw)
        self.map_throttle_output = list(self.map_throttle_output_raw)

        # パブリッシャー 
        self.publisher_control_select = self.create_publisher(PWMDriveCommand, self.topic_control_pwm, 10)

        # サブスクリプション
        self.subscription_control_manual = self.create_subscription(NormalizedDriveCommand, self.topic_control_select, self._convert_normalized_to_pwm, 10)

        # CLI ログ出力用ロガー
        self.logger = self.get_logger()

        # CLI ログ出力
        if self.verbose >= 2:
            self.logger.info(f"Parameters:")
            self.logger.info(f"  interface:")
            self.logger.info(f"    topic:")
            self.logger.info(f"      control_select: {self.topic_control_select}")
            self.logger.info(f"      control_pwm: {self.topic_control_pwm}")
            self.logger.info(f"  map:")
            self.logger.info(f"    steering_input: {self.map_steering_input}")
            self.logger.info(f"    throttle_input: {self.map_throttle_input}")
            self.logger.info(f"    steering_output: {self.map_steering_output}")
            self.logger.info(f"    throttle_output: {self.map_throttle_output}")
            self.logger.info(f"  verbose: {self.verbose}")

    def _convert_normalized_to_pwm(self, sub_msg: NormalizedDriveCommand):
        """
        
        受け取った正規化済み信号を PWM の区間に写して送信する.

        Args:
            sub_msg (NormalizedDriveCommand): 手動運転指令
        
        """

        # 送信するメッセージの型
        pub_msg = PWMDriveCommand()

        # マッピング
        pub_msg.steering = self._mapping_linear(sub_msg.steering, self.map_steering_input, self.map_steering_output)
        pub_msg.throttle = self._mapping_linear(sub_msg.throttle, self.map_throttle_input, self.map_throttle_output)

        # タイムスタンプの追加
        pub_msg.header.stamp = self.get_clock().now().to_msg()

        # 選択されたメッセージを送信
        self.publisher_control_select.publish(pub_msg)

        # ログ出力
        if self.verbose >= 3:
            self.logger.info(f"Mapped command: steering={pub_msg.steering:.3f}, throttle={pub_msg.throttle:.3f}")

    def _mapping_linear(self, value: float, input_range: list[float], output_range: list[int]) -> float:
        """

        受け取った [-1, +1] 範囲の正規化済み信号を別の区間に写す.

        Args:
            value (float): [-1, +1] 範囲の正規化済み信号
            input_range (list[float]): 写す元の区間 [min, max]
            output_range (list[int]): 写す先の区間 [min, max]
        
        Returns:
            (float): 写された先の信号
        
        """

        input_min, input_max = input_range
        output_min, output_max = output_range

        # 入力区間を [0, 1] に正規化
        ratio = (value - input_min) / (input_max - input_min)
        
        return output_min + ratio * (output_max - output_min)

def main(args=None) -> None:
    rclpy.init(args=args)

    node = YSDPWMMapperTT02()

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