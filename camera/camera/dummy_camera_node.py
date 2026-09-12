# ROS2 コア
import rclpy
from rclpy.node import Node

# ROS2 メッセージ型
from sensor_msgs.msg import Image

# 自作パッケージ
from .camera import DummyCamera
from .msg_matlike_converter import convert_matlike_to_msg

class DummyCameraNode(Node):
    """

    カメラ画像のダミーを送信するテスト用ノード

    """

    def __init__(self) -> None:
        super().__init__("dummy_camera_node")

        # パラメータ定義
        self.declare_parameter("interface.topic.camera_image", "/camera/image_raw")
        self.declare_parameter("frame_publish_hz", 10.0)

        self.declare_parameter("camera.frame_id", "dummy_frame")
        self.declare_parameter("camera.sensor_id", 0)
        self.declare_parameter("camera.capture_size", [1280, 720])
        self.declare_parameter("camera.capture_hz", 30)
        self.declare_parameter("camera.resize", [84, 84])
        self.declare_parameter("camera.flip_method", 0)
        self.declare_parameter("camera.patient", 0)
        self.declare_parameter("camera.read_hz", 30.0)

        self.declare_parameter("verbose", 2)

        # パラメータ参照
        self.topic_camera = self.get_parameter("interface.topic.camera").get_parameter_value().string_value
        self.frame_publish_hz = self.get_parameter("frame_publish_hz").get_parameter_value().double_value

        self.frame_id = self.get_parameter("camera.frame_id").get_parameter_value().string_value
        self.sensor_id = self.get_parameter("camera.sensor_id").get_parameter_value().integer_value
        self.capture_size = self.get_parameter("camera.capture_size").get_parameter_value().integer_array_value
        self.capture_hz = self.get_parameter("camera.capture_hz").get_parameter_value().integer_value
        self.resize = self.get_parameter("camera.resize").get_parameter_value().integer_array_value
        self.flip_method = self.get_parameter("camera.flip_method").get_parameter_value().integer_value
        self.patient = self.get_parameter("camera.patient").get_parameter_value().integer_value
        self.read_hz = self.get_parameter("camera.read_hz").get_parameter_value().double_value

        self.verbose = self.get_parameter("verbose").get_parameter_value().integer_value

        # パブリッシャー
        self.publisher = self.create_publisher(Image, self.topic_camera, 10)
        self.publish_timer = self.create_timer(1/self.frame_publish_hz, self._publish)

        # パラメータ整形
        self.capture_size = (self.capture_size[0], self.capture_size[1])
        self.resize = (self.resize[0], self.resize[1])

        # カメラ
        self.camera = DummyCamera(
            sensor_id=self.sensor_id,
            capture_size=self.capture_size,
            capture_hz=self.capture_hz,
            resize=self.resize,
            flip_method=self.flip_method,
            patient=self.patient
        )
        self.read_timer = self.create_timer(1/self.read_hz, self._read)

        self.frame = None

        # CLI ログ出力用ロガー
        self.logger = self.get_logger()

        # CLI ログ出力
        if self.verbose >= 2:
            self.logger.info(f"Parameters:")
            self.logger.info(f"  interface:")
            self.logger.info(f"    topic:")
            self.logger.info(f"      control_manual: {self.topic_camera}")
            self.logger.info(f"  frame_publish_hz: {self.frame_publish_hz}")
            self.logger.info(f"  camera:")
            self.logger.info(f"    frame_id: {self.frame_id}")
            self.logger.info(f"    sensor_id: {self.sensor_id}")
            self.logger.info(f"    capture_size: {self.capture_size}")
            self.logger.info(f"    capture_hz: {self.capture_hz}")
            self.logger.info(f"    resize: {self.resize}")
            self.logger.info(f"    flip_method: {self.flip_method}")
            self.logger.info(f"    patient: {self.patient}")
            self.logger.info(f"    read_hz: {self.read_hz}")
            self.logger.info(f"  verbose: {self.verbose}")

    def _read(self) -> None:
        """

        カメラから画像を取得して一時的に保存する.

        """

        self.frame = self.camera.read()

        # ログ出力
        if self.verbose >= 3:
            self.logger.info("フレームを読み込みました.")

    def _publish(self) -> None:
        """

        カメラから取得した画像を送信する.

        """

        if self.frame is None:
            return

        # メッセージへの変換
        msg = convert_matlike_to_msg(
            frame=self.frame,
            time_stamp=self.get_clock().now().to_msg(),
            frame_id=self.frame_id
        )

        # 送信
        self.publisher.publish(msg)

        # ログ出力
        if self.verbose >= 3:
            self.logger.info("フレームを送信しました.")

    def release(self) -> None:
        self.camera.release()

def main(args=None) -> None:
    rclpy.init(args=args)

    node = DummyCameraNode()

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
