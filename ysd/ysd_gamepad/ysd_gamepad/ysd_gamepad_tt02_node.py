# 型
from typing import cast

# ROS2 コア
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node

# ROS2 自作メッセージ・サービス型
from gamepad_msgs.msg import GamepadState, GamepadAxisState, GamepadButtonState
from ysd_msgs.msg import NormalizedDriveCommandTT02 as NormalizedDriveCommand
from ysd_msgs.srv import SetControlMode

class YSDGamepadTT02Node(Node):
    """

    このノードでは受け取った GamepadState メッセージを YSD 固有の操作信号 NormalizedDriveCommand に変換して送信します.
    注: Tamiya TT-02 ベースの車両用のノードです.

    """

    def __init__(self) -> None:
        super().__init__("ysd_gamepad_tt02_node")

        # パラメータ定義
        self.declare_parameter("interface.topic.gamepad_state", "/gamepad/state")
        self.declare_parameter("interface.topic.control_manual", "/control/manual")
        self.declare_parameter("interface.service.set_control_mode", "/set/control_mode")

        self.declare_parameter("keybind.axis.steering", "lx")
        self.declare_parameter("keybind.axis.throttle", "ry")
        self.declare_parameter("keybind.button.mode", "l1")
        self.declare_parameter("keybind.button.record_mode", "r1")

        self.declare_parameter("verbose", 2)

        # パラメータ参照
        self.topic_gamepad_state = self.get_parameter("interface.topic.gamepad_state").get_parameter_value().string_value
        self.topic_control_manual = self.get_parameter("interface.topic.control_manual").get_parameter_value().string_value
        self.service_set_control_mode = self.get_parameter("interface.service.set_control_mode").get_parameter_value().string_value

        self.keybind_axis_steering = self.get_parameter("keybind.axis.steering").get_parameter_value().string_value
        self.keybind_axis_throttle = self.get_parameter("keybind.axis.throttle").get_parameter_value().string_value
        self.keybind_button_mode = self.get_parameter("keybind.button.mode").get_parameter_value().string_value
        self.keybind_recorde_mode = self.get_parameter("keybind.button.record_mode").get_parameter_value().string_value

        self.verbose = self.get_parameter("verbose").get_parameter_value().integer_value

        # パブリッシャー
        self.publisher = self.create_publisher(NormalizedDriveCommand, self.topic_control_manual, 10)

        # サブスクリプション
        self.subscription = self.create_subscription(GamepadState, self.topic_gamepad_state, self._subscribe, 10)

        # クライアント
        self.client = self.create_client(SetControlMode, self.service_set_control_mode)

        # モード切り替えエッジ検出用
        self.prev_state_mode_button = False

        # CLI ログ出力用ロガー
        self.logger = self.get_logger()

        # CLI ログ出力
        if self.verbose >= 2:
            self.logger.info(f"Parameters:")
            self.logger.info(f"  interface:")
            self.logger.info(f"    topic:")
            self.logger.info(f"      gamepad_state: {self.topic_gamepad_state}")
            self.logger.info(f"      control_manual: {self.topic_control_manual}")
            self.logger.info(f"    service:")
            self.logger.info(f"      set_control_mode: {self.service_set_control_mode}")
            self.logger.info(f"  keybind:")
            self.logger.info(f"    axis:")
            self.logger.info(f"      steering: {self.keybind_axis_steering}")
            self.logger.info(f"      throttle: {self.keybind_axis_throttle}")
            self.logger.info(f"    button:")
            self.logger.info(f"      mode: {self.keybind_button_mode}")
            self.logger.info(f"      recorde_mode: {self.keybind_recorde_mode}")
            self.logger.info(f"  verbose: {self.verbose}")

    def _subscribe(self, sub_msg: GamepadState) -> None:
        """

        受け取ったゲームパッドの状態を YSD 固有の操作信号に変換して送信する.

        Args:
            sub_msg (GamepadState): 受け取ったゲームパッドの状態メッセージ.

        """

        # 送信メッセージの型
        pub_msg = NormalizedDriveCommand()

        # タイムスタンプの追加
        pub_msg.header.stamp = self.get_clock().now().to_msg()

        # 操作信号の抽出
        for state in cast(list[GamepadAxisState], sub_msg.axis):

            # ステアリング
            if state.name == self.keybind_axis_steering:
                pub_msg.steering = state.value

            # スロットル
            elif state.name == self.keybind_axis_throttle:
                pub_msg.throttle = state.value

        # データの送信
        self.publisher.publish(pub_msg)

        # イベント信号の抽出
        for state in cast(list[GamepadButtonState], sub_msg.button):

            # マニュアル・自動運転切り替え
            if state.name == self.keybind_button_mode:

                # モード切り替えフラグの立ち上がりを検出する.
                current = bool(state.value)
                pressed = current and not self.prev_state_mode_button
                self.prev_state_mode_button = current

                if pressed:
                    self._request_mode_change()

        # ログ出力
        if self.verbose >= 3:
            self.logger.info(f"メッセージを送信しました. ({pub_msg.steering}, {pub_msg.throttle})")

    def _request_mode_change(self) -> None:
        """

        マニュアル・自動運転モードの切り替えをサービスに要請する.
        
        """

        if not self.client.service_is_ready():
            if self.verbose >= 1:
                self.logger.warn(f"{self.service_set_control_mode} が利用できません.")
            return

        # リクエストの型
        req = SetControlMode.Request()

        # モード変更フラグを立てる
        req.change = True

        # 非同期でコールバック関数を実行する
        future = self.client.call_async(req)
        future.add_done_callback(self._set_mode_respose_callback)

    def _set_mode_respose_callback(self, future) -> None:
        """
        
        モード切り替え要請のレスポンスに対するコールバック関数. レスポンスの内容をログに出力する.
        
        """

        try:
            res = cast(SetControlMode.Response, future.result())
        except Exception as e:
            if self.verbose >= 1:
                self.logger.error(f"モード切り替えサービスの呼び出しに失敗しました: {e}")
            return

        if res.accepted:
            if self.verbose >= 2:
                self.logger.info(res.message)
        else:
            if self.verbose >= 1:
                self.logger.warn(res.message)

def main(args=None) -> None:
    rclpy.init(args=args)

    node = YSDGamepadTT02Node()

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
