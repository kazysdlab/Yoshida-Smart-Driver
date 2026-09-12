# 型
from typing import cast

# ROS2 コア
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node

# ROS2 自作メッセージ型
from gamepad_msgs.msg import GamepadState, GamepadAxisState, GamepadButtonState

# 自作パッケージ
from .gamepad import Gamepad

class GamepadNode(Node):
    """

    このノードでは USB, Bluetooth を問わず, 接続されたゲームパッド入力デバイスの状態を送信します.

    """

    def __init__(self) -> None:
        super().__init__("gamepad_node")

        # パラメータ定義
        self.declare_parameter("interface.topic.gamepad_state", "/gamepad/state")
        self.declare_parameter("publish_hz", 10.0)

        self.declare_parameter("gamepad.type", "dualsense")
        self.declare_parameter("gamepad.path", "")
        self.declare_parameter("gamepad.search_words", ["dualsense", "wireless controller"])
        self.declare_parameter("gamepad.deadzone", 0.02)
        self.declare_parameter("gamepad.read_hz", 30.0)

        self.declare_parameter("verbose", 2)

        # パラメータ参照
        self.topic_gamepad_state = self.get_parameter("interface.topic.gamepad_state").get_parameter_value().string_value
        self.publish_hz = self.get_parameter("publish_hz").get_parameter_value().double_value

        self.gamepad_type = self.get_parameter("gamepad.type").get_parameter_value().string_value
        self.gamepad_path = self.get_parameter("gamepad.path").get_parameter_value().string_value
        self.gamepad_search_words = cast(
            list[str],
            self.get_parameter("gamepad.search_words").get_parameter_value().string_array_value
        )
        self.deadzone = self.get_parameter("gamepad.deadzone").get_parameter_value().double_value
        self.read_hz = self.get_parameter("gamepad.read_hz").get_parameter_value().double_value

        self.verbose = self.get_parameter("verbose").get_parameter_value().integer_value

        # パブリッシャー
        self.publisher = self.create_publisher(GamepadState, self.topic_gamepad_state, 10)
        self.publish_timer = self.create_timer(1/self.publish_hz, self._publish)

        # ゲームパッド
        self.gamepad = Gamepad(self.gamepad_type, self.gamepad_path, self.gamepad_search_words, self.deadzone)
        self.state = self.gamepad.read()  # 初期値の読み込み
        self.read_timer = self.create_timer(1/self.read_hz, self._read)

        # CLI ログ出力用ロガー
        self.logger = self.get_logger()

        # CLI ログ出力
        if self.verbose >= 2:
            self.logger.info(f"Parameters:")
            self.logger.info(f"  interface:")
            self.logger.info(f"    topic:")
            self.logger.info(f"      gamepad_state: {self.topic_gamepad_state}")
            self.logger.info(f"  publish_hz: {self.publish_hz}")
            self.logger.info(f"  gamepad:")
            self.logger.info(f"    gamepad_type: {self.gamepad_type}")
            self.logger.info(f"    gamepad_path: {self.gamepad_path}")
            self.logger.info(f"    gamepad_search_words: {self.gamepad_search_words}")
            self.logger.info(f"    deadzone: {self.deadzone}")
            self.logger.info(f"    read_hz: {self.read_hz}")
            self.logger.info(f"  verbose: {self.verbose}")

    def _read(self) -> None:
        """

        ゲームパッドの状態を更新する.

        """

        self.state = self.gamepad.read()

    def _publish(self) -> None:
        """

        ゲームパッドの状態をメッセージとして送信する.

        """

        self.pub_msg = GamepadState()

        # データの格納
        for (name, value) in self.state["axis"].items():
            self.pub_msg.axis.append(GamepadAxisState(name=name, value=value))  # type: ignore

        for (name, value) in self.state["button"].items():
            self.pub_msg.button.append(GamepadButtonState(name=name, value=value))  # type: ignore

        # データの送信
        self.publisher.publish(self.pub_msg)

        # ログ出力
        if self.verbose >= 3:
            self.logger.info(f"メッセージを送信しました.")

def main(args=None) -> None:
    rclpy.init(args=args)

    node = GamepadNode()

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
