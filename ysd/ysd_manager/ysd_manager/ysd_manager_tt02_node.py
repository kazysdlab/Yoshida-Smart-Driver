# ROS2 コア
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node

# ROS2
from std_msgs.msg import String
from ysd_msgs.msg import NormalizedDriveCommandTT02 as NormalizedDriveCommand
from ysd_msgs.srv import SetControlMode

class YSDManagerTT02(Node):
    """

    このノードは, 自動運転とマニュアル運転を切り替え, 適切なメッセージを通す MUX です.

    """

    def __init__(self):
        super().__init__("ysd_manager_tt02_node")

        # パラメータ定義
        self.declare_parameter("interface.topic.control_manual", "/control/manual")
        self.declare_parameter("interface.topic.control_auto", "/control/auto")
        self.declare_parameter("interface.topic.control_select", "/control/select")
        self.declare_parameter("interface.topic.control_mode", "/control/mode")
        self.declare_parameter("interface.service.set_control_mode", "/set/control_mode")
        self.declare_parameter("control.init_control_mode", "manual")
        self.declare_parameter("control.publish_control_select_hz", 20.0)
        self.declare_parameter("control.publish_control_mode_hz", 20.0)
        self.declare_parameter("verbose", 2)

        # パラメータ参照
        self.topic_control_manual = self.get_parameter("interface.topic.control_manual").get_parameter_value().string_value
        self.topic_control_auto = self.get_parameter("interface.topic.control_auto").get_parameter_value().string_value
        self.topic_control_select = self.get_parameter("interface.topic.control_select").get_parameter_value().string_value
        self.topic_control_mode = self.get_parameter("interface.topic.control_mode").get_parameter_value().string_value
        self.service_set_control_mode = self.get_parameter("interface.service.set_control_mode").get_parameter_value().string_value
        self.init_control_mode = self.get_parameter("control.init_control_mode").get_parameter_value().string_value
        self.publish_control_select_hz = self.get_parameter("control.publish_control_select_hz").get_parameter_value().double_value
        self.publish_control_mode_hz = self.get_parameter("control.publish_control_mode_hz").get_parameter_value().double_value
        self.verbose = self.get_parameter("verbose").get_parameter_value().integer_value

        # 受け取ったメッセージの一時的な保管場所
        self.command_msg_manual: NormalizedDriveCommand|None = None
        self.command_msg_auto: NormalizedDriveCommand|None = None

        # パブリッシャー 
        self.publisher_control_select = self.create_publisher(NormalizedDriveCommand, self.topic_control_select, 10)
        self.publish_control_select_timer = self.create_timer(1/self.publish_control_select_hz, self._publish_control_select)

        self.publisher_control_mode = self.create_publisher(String, self.topic_control_mode, 10)
        self.publish_control_mode_timer = self.create_timer(1/self.publish_control_mode_hz, self._publish_control_mode)

        # サブスクリプション
        self.subscription_control_manual = self.create_subscription(NormalizedDriveCommand, self.topic_control_manual, self._update_command_manual, 10)
        self.subscription_control_auto = self.create_subscription(NormalizedDriveCommand, self.topic_control_auto, self._update_command_auto, 10)

        # サーバー
        self.service = self.create_service(SetControlMode, self.service_set_control_mode, self._set_command_mode_callback)

        # CLI ログ出力用ロガー
        self.logger = self.get_logger()

        # モードの保管場所の定義と初期値の反映
        if self.init_control_mode not in ("manual", "auto"):
            self.logger.warn(f"control.init_control_mode = {self.init_control_mode} は無効です.")
            self.logger.warn(f"初期モードとして manual が使用されます.")
            self.control_mode = "manual"
        else:
            self.logger.info(f"初期モードとして {self.init_control_mode} が使用されます.")
            self.control_mode = self.init_control_mode

        # CLI ログ出力
        if self.verbose >= 2:
            self.logger.info(f"Parameters:")
            self.logger.info(f"  interface:")
            self.logger.info(f"    topic:")
            self.logger.info(f"      control_manual {self.topic_control_manual}")
            self.logger.info(f"      control_auto: {self.topic_control_auto}")
            self.logger.info(f"      control_select: {self.topic_control_select}")
            self.logger.info(f"      control_mode: {self.topic_control_mode}")
            self.logger.info(f"    service:")
            self.logger.info(f"      set_control_mode: {self.service_set_control_mode}")
            self.logger.info(f"  control:")
            self.logger.info(f"    init_control_mode: {self.init_control_mode}")
            self.logger.info(f"    publish_control_select_hz: {self.publish_control_select_hz}")
            self.logger.info(f"    publish_control_mode_hz: {self.publish_control_mode_hz}")
            self.logger.info(f"  verbose: {self.verbose}")

    def _update_command_manual(self, msg: NormalizedDriveCommand):
        """
        
        受け取った手動運転指令を保存する.

        Args:
            msg (NormalizedDriveCommand): 手動運転指令
        
        """

        self.command_msg_manual = msg

    def _update_command_auto(self, msg: NormalizedDriveCommand):
        """
        
        受け取った自動運転指令を保存する.

        Args:
            msg (NormalizedDriveCommand): 自動運転指令
        
        """
        
        self.command_msg_auto = msg

    def _set_command_mode_callback(self, req: SetControlMode.Request, res: SetControlMode.Response):
        """
        
        操作モード変更の要求を処理するためのコールバック関数.

        Args:
            req (SetControlMode.Request): 受け取った要求
            res (SetControlMode.Response): 送信する応答
        
        """

        # 変更フラグが立っていない場合は何もしない.
        if not req.change:
            # 応答メッセージを整える
            res.accepted = False
            res.mode = self.control_mode
            res.message = "change = False のためモード変更操作が無効です."

            # ログ出力
            if self.verbose >= 2:
                self.logger.info(res.message)

            return res

        # 変更前のモードを一時的に保存
        prev_mode = self.control_mode

        # 制御モードを変更する
        if self.control_mode == "manual":
            self.control_mode = "auto"
        else:
            self.control_mode = "manual"

        # 応答メッセージを整える
        res.accepted = True
        res.mode = self.control_mode
        res.message = f"操作モードを {self.control_mode} に変更しました."

        # 現在の制御モードを送信する. (モード変更を素早く伝えるために独立して送信)
        self._publish_control_mode()

        # ログ出力
        if self.verbose >= 3:
            self.logger.info(res.message)

        return res

    def _publish_control_select(self):
        """
        
        現在の操作モードに一致する操作信号を送信する.
        
        """

        # メッセージの選択
        if self.control_mode == "manual":
            select_msg = self.command_msg_manual
        else:
            select_msg = self.command_msg_auto

        # 選択されたメッセージの受信がされていない場合, スキップする.
        if select_msg is None:
            # ログ出力
            if self.verbose >= 2:
                self.logger.warning(f"{self.control_mode} モードの指令をまだ受信していません.")
            return

        # タイムスタンプの追加
        select_msg.header.stamp = self.get_clock().now().to_msg()

        # 選択されたメッセージを送信
        self.publisher_control_select.publish(select_msg)

        # ログ出力
        if self.verbose >= 3:
            self.logger.info(f"Selected command: mode={self.control_mode}, steering={select_msg.steering:.3f}, throttle={select_msg.throttle:.3f}")

    def _publish_control_mode(self):
        """
        
        操作モードを送信する.
        
        """

        # 送信メッセージの型
        pub_msg = String()

        # 操作モードのセット
        pub_msg.data = self.control_mode

        # パブリッシュ
        self.publisher_control_mode.publish(pub_msg)

def main(args=None) -> None:
    rclpy.init(args=args)

    node = YSDManagerTT02()

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