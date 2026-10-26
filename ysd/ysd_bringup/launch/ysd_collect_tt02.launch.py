import os
from launch import LaunchDescription
from launch.actions import SetEnvironmentVariable, DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    pkg_share = get_package_share_directory("ysd_bringup")
    config = os.path.join(pkg_share, "config", "ysd_auto_tt02.yaml")

    return LaunchDescription([
        # ログスタイル
        SetEnvironmentVariable(
            name="RCUTILS_CONSOLE_OUTPUT_FORMAT",
            value="[{severity}]: {message}"
        ),

        # ===== Args =====
        DeclareLaunchArgument(
            "model_path",
            default_value="model.onnx",
            description="Path to ONNX model"
        ),

        # ===== IO =====
        # ゲームパッド
        Node(
            package="gamepad",
            executable="gamepad_node",
            name="gamepad",
            parameters=[config],
            output="screen"
        ),
        Node(
            package="ysd_gamepad",
            executable="ysd_gamepad_tt02_node",
            name="ysd_gamepad",
            parameters=[config],
            output="screen"
        ),

        # カメラ
        Node(
            package="camera",
            executable="csi_camera_node",
            name="camera",
            parameters=[config],
            output="screen"
        ),

        # PWM ドライバ
        Node(
            package="ysd_pwm_driver",
            executable="ysd_pca9685_driver_tt02_node",
            name="ysd_pwm_driver",
            parameters=[config],
            output="screen"
        ),

        # ===== 機械学習 =====
        # 推論
        Node(
            package="ysd_machine_learning",
            executable="ysd_torch_inference_tt02_node",
            name="inference",
            parameters=[
                config,
                {"network.model_path": LaunchConfiguration("model_path")}
            ],
            output="screen"
        ),
        
        # ===== 制御 =====
        # マネージャー
        Node(
            package="ysd_manager",
            executable="ysd_manager_tt02_node",
            name="ysd_manager",
            parameters=[config],
            output="screen"
        ),

        # PWM 範囲マッピング
        Node(
            package="ysd_pwm_mapper",
            executable="ysd_pwm_mapper_tt02_node",
            name="ysd_mapper",
            parameters=[config],
            output="screen"
        ),
    ])
