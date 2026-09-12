# 型
from collections import deque
from cv2.typing import MatLike

# ROS2 コア
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node

# ROS2 メッセージ型
from sensor_msgs.msg import Image
from ysd_msgs.msg import NormalizedDriveCommandTT02 as NormalizedDriveCommand

# 外部ライブラリ
import torch
import numpy as np

# 自作ライブラリ
from .msg_matlike_converter import convert_msg_to_matlike

class YSDTorchInferenceTT02(Node):
    """

    このノードは, YSD 固有の操作信号

    """

    def __init__(self):
        super().__init__("ysd_torch_inference_tt02_node")

        # パラメータ定義
        self.declare_parameter("interface.topic.camera_image", "/camera/image_raw")
        self.declare_parameter("interface.topic.control_auto", "/control/auto")
        self.declare_parameter("network.inference_hz", 1.0)
        self.declare_parameter("network.observation.num_stacks", 4)
        self.declare_parameter("network.device", "cuda")
        self.declare_parameter("verbose", 2)

        # パラメータ参照
        self.topic_camera_image = self.get_parameter("interface.topic.camera_image").get_parameter_value().string_value
        self.topic_control_auto = self.get_parameter("interface.topic.control_auto").get_parameter_value().string_value
        self.inference_hz = self.get_parameter("network.inference_hz").get_parameter_value().double_value
        self.num_stacks = self.get_parameter("network.observation.num_stacks").get_parameter_value().integer_value
        self.device_str = self.get_parameter("network.device").get_parameter_value().string_value
        self.verbose = self.get_parameter("verbose").get_parameter_value().integer_value

        # 受け取ったメッセージの一時的な保管場所
        self.obs_buffer: deque[MatLike] = deque(maxlen=self.num_stacks)
        self.init_stack_buffer_frame = True

        # パブリッシャー 
        self.publisher_control_auto = self.create_publisher(NormalizedDriveCommand, self.topic_control_auto, 10)

        # サブスクリプション
        self.subscription_camera_image = self.create_subscription(Image, self.topic_camera_image, self._update_camera_image, 10)

        # 推論用タイマー
        self.inference_timer = self.create_timer(1/self.inference_hz, self._inference)

        # CLI ログ出力用ロガー
        self.logger = self.get_logger()

        # 推論デバイス
        self.device = torch.device(self.device_str)

        # CLI ログ出力
        if self.verbose >= 2:
            self.logger.info(f"Parameters:")
            self.logger.info(f"  interface:")
            self.logger.info(f"    topic:")
            self.logger.info(f"      camera_image {self.topic_camera_image}")
            self.logger.info(f"      control_auto: {self.topic_control_auto}")
            self.logger.info(f"  network:")
            self.logger.info(f"    num_stacks: {self.num_stacks}")
            self.logger.info(f"    device: {self.device.type}")
            self.logger.info(f"  verbose: {self.verbose}")

    def _update_camera_image(self, sub_msg: Image):
        """
        
        受け取ったカメラ画像をバッファーに格納する.

        Args:
            sub_msg (Image): カメラ画像
        
        """

        frame = convert_msg_to_matlike(sub_msg)

        # スタック用フレームが足りてない場合に同一フレームで埋める
        if self.init_stack_buffer_frame:
            self.init_stack_buffer_frame = False
            for _ in range(self.num_stacks):
                self.obs_buffer.append(frame)
        else:
            self.obs_buffer.append(frame)

    def _inference(self):
        """
        
        推論して, 結果を送信する.
        
        """

        # まだフレームが送られていない場合, 推論・送信を行わない.
        if self.init_stack_buffer_frame:
            if self.verbose >= 2:
                self.logger.warn(f"まだ観測が送られていないため, 推論は行いません.")
            return None

        # ===== 機械学習モデルを用いて推論を実行 =====
        # 観測のテンソルを作成
        obs_np = np.array(self.obs_buffer, dtype=np.float32) / 255.0
        obs = torch.from_numpy(obs_np).permute(0, 3, 1, 2).contiguous()
        obs = obs.reshape(1, -1, obs.shape[2], obs.shape[3]).to(self.device)

        # !!!!! 推論 (未実装) !!!!!

        # ===== メッセージを作成 =====
        # 送信メッセージの型
        pub_msg = NormalizedDriveCommand()

        # タイムスタンプの追加
        pub_msg.header.stamp = self.get_clock().now().to_msg()

        # !!!!! 目標値のセット (自身の機械学習モデルの出力形式に合わせる) !!!!!
        pub_msg.steering = 0.0
        pub_msg.throttle = 0.0

        # パブリッシュ
        self.publisher_control_auto.publish(pub_msg)

def main(args=None) -> None:
    rclpy.init(args=args)

    node = YSDTorchInferenceTT02()

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