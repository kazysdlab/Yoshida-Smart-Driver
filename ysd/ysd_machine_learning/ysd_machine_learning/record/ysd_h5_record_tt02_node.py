# 型
from collections import deque

# ROS2 コア
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node

# ROS2 メッセージ型
from sensor_msgs.msg import Image
from ysd_msgs.msg import NormalizedDriveCommandTT02 as NormalizedDriveCommand
from rclpy.time import Time

# 外部ライブラリ
import torch
import numpy as np

# 自作ライブラリ
from ..msg_ndarray_converter import convert_msg_to_ndarray
from h5_writer import H5Writer

class YSDH5RecordTT02(Node):
    """

    このノードは, 教師データを収集するノードです.

    """

    def __init__(self):
        super().__init__("ysd_h5_record_tt02_node")

        # パラメータ定義
        self.declare_parameter("interface.topic.camera_image", "/camera/image_raw")
        self.declare_parameter("interface.topic.control_manual", "/control/manual")
        self.declare_parameter("record.output_dir", "./data")
        self.declare_parameter("record.record_hz", 10.0)
        self.declare_parameter("record.max_abs_delta_t", 0.1)
        self.declare_parameter("verbose", 2)

        # パラメータ参照
        self.topic_camera_image = self.get_parameter("interface.topic.camera_image").get_parameter_value().string_value
        self.topic_control_manual = self.get_parameter("interface.topic.control_manual").get_parameter_value().string_value
        self.output_dir = self.get_parameter("record.output_dir").get_parameter_value().string_value
        self.record_hz = self.get_parameter("record.record_hz").get_parameter_value().double_value
        self.max_abs_delta_t = self.get_parameter("record.max_abs_delta_t").get_parameter_value().double_value
        self.verbose = self.get_parameter("verbose").get_parameter_value().integer_value

        # 受け取ったメッセージの一時的な保管場所
        self.obs_buffer: Image|None = None
        self.control_manual_buffer: NormalizedDriveCommand|None = None

        # サブスクリプション
        self.subscription_camera_image = self.create_subscription(Image, self.topic_camera_image, self._update_camera_image, 10)
        self.subscription_control_manual = self.create_subscription(NormalizedDriveCommand, self.topic_control_manual, self._update_control_manual, 10)

        # データ収集タイマー
        self.record_timer = self.create_timer(1/self.record_hz, self._record)

        # H5Writer のインスタンス化
        self.writer = H5Writer(
            self.output_dir,
            attrs={
                "record_hz": self.record_hz,
                "topic_camera_image": self.topic_camera_image,
                "topic_control_manual": self.topic_control_manual,
                "max_abs_delta_t": self.max_abs_delta_t,
            }
        )

        # CLI ログ出力用ロガー
        self.logger = self.get_logger()

        # CLI ログ出力
        if self.verbose >= 2:
            self.logger.info(f"Parameters:")
            self.logger.info(f"  interface:")
            self.logger.info(f"    topic:")
            self.logger.info(f"      camera_image {self.topic_camera_image}")
            self.logger.info(f"      control_manual: {self.topic_control_manual}")
            self.logger.info(f"  record:")
            self.logger.info(f"    output_dir: {self.output_dir}")
            self.logger.info(f"    record_hz: {self.record_hz}")
            self.logger.info(f"    max_abs_delta_t: {self.max_abs_delta_t}")
            self.logger.info(f"  verbose: {self.verbose}")

    def _update_camera_image(self, sub_msg: Image):
        """
        
        受け取ったカメラ画像をバッファーに格納する.

        Args:
            sub_msg (Image): カメラ画像
        
        """

        self.obs_buffer = sub_msg

    def _update_control_manual(self, sub_msg: NormalizedDriveCommand):
        """
        
        受け取ったマニュアル操作信号をバッファーに格納する.

        Args:
            sub_msg (NormalizedDriveCommand): マニュアル操作信号
        
        """

        self.control_manual_buffer = sub_msg

    def _record(self):
        """
        
        入出力のペアを記録する.
        
        """

        obs = self.obs_buffer
        act = self.control_manual_buffer

        # まだフレームが送られていない場合, 記録を行わない.
        if obs == None or act == None:
            if self.verbose >= 2:
                self.logger.warn(f"まだ観測・目標値が送られていないため, 推論は行いません.")
            return None

        t_obs = Time.from_msg(obs.header.stamp)
        t_act = Time.from_msg(act.header.stamp)
        delta_t = (t_act - t_obs).nanoseconds * 1e-9

        if abs(delta_t) > self.max_abs_delta_t:
            self.logger.warn(f"stamp差が大きいためスキップ: {delta_t*1000:.1f} ms")
            return None

        image = convert_msg_to_ndarray(obs)
        action = np.array([act.steering, act.throttle], dtype=np.float32)

        self.writer.append(image, action, t_obs.nanoseconds, t_act.nanoseconds)

        if self.verbose >= 2:
            self.logger.info(f"[{self.writer.n}] delta_t={delta_t*1000:.1f} ms")

def main(args=None) -> None:
    rclpy.init(args=args)

    node = YSDH5RecordTT02()

    try:
        rclpy.spin(node)
        
    except (KeyboardInterrupt, ExternalShutdownException):
        pass

    except RuntimeError as e:
        shutdown_conversion_error = ("Unable to convert call argument to Python object" in str(e) and not rclpy.ok())
        if not shutdown_conversion_error:
            raise

    finally:
        node.writer.close()  # HDF5 を閉じる
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == "__main__":
    main()