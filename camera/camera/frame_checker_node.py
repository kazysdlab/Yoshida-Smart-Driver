# 型
from cv2.typing import MatLike

# ROS2 コア
import rclpy
from rclpy.node import Node

# ROS2 メッセージ型
from sensor_msgs.msg import Image

# 自作パッケージ
from .msg_matlike_converter import convert_msg_to_matlike

class FrameCheckerNode(Node):
    """

    カメラ画像のダミーを送信するテスト用ノード

    """

    def __init__(self) -> None:
        super().__init__("dummy_camera_node")

        # パラメータ定義
        self.declare_parameter("interface.topic.camera_image", "/camera/image_raw")
        self.declare_parameter("logging_hz", 1.0)
        self.declare_parameter("verbose", 2)

        # パラメータ参照
        self.topic_camera_image = self.get_parameter("interface.topic.camera_image").get_parameter_value().string_value
        self.logging_hz = self.get_parameter("logging_hz").get_parameter_value().double_value
        self.verbose = self.get_parameter("verbose").get_parameter_value().integer_value

        # サブスクリプション
        self.subscription_camera_image = self.create_subscription(Image, self.topic_camera_image, self._update_camera_image, 10)

        # CLI ログ出力用ロガー
        self.logger = self.get_logger()
        self.logging_timer = self.create_timer(1/self.logging_hz, self._logging)

        # CLI ログ出力
        if self.verbose >= 2:
            self.logger.info(f"Parameters:")
            self.logger.info(f"  interface:")
            self.logger.info(f"    topic:")
            self.logger.info(f"      camera_image {self.topic_camera_image}")
            self.logger.info(f"  logging_hz: {self.logging_hz}")
            self.logger.info(f"  verbose: {self.verbose}")

    def _update_camera_image(self, msg: Image):
        """
        
        受け取ったカメラ画像をバッファーに格納する.

        Args:
            msg (Image): カメラ画像
        
        """

        frame = convert_msg_to_matlike(msg)

        self.obs_buffer = frame

    def _logging(self) -> None:
        """

        実行時の最新のフレームの情報ログ出力する.

        """

        self.logger.info(f"shape: {self.obs_buffer.shape}")

def main(args=None) -> None:
    rclpy.init(args=args)

    node = FrameCheckerNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == "__main__":
    main()
