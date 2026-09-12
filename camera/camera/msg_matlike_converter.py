# 型
from cv2.typing import MatLike

# ROS2 メッセージ型
from sensor_msgs.msg import Image

# 外部ライブラリ
import numpy as np

def convert_matlike_to_msg(frame: MatLike, time_stamp, frame_id) -> Image:
    """

    カメラ画像のをImageメッセージに変換する。

    Args:
        frame (MatLike): 画像

    Returns:
        msg (Image): 画像のメッセージ

    """

    # メッセージ作成
    msg = Image()

    # データ挿入
    h, w, c = frame.shape
    msg.header.stamp = time_stamp
    msg.header.frame_id = frame_id
    msg.height = h
    msg.width = w
    msg.encoding = 'bgr8'
    msg.is_bigendian = 0
    msg.step = int(frame.strides[0])
    msg.data = frame.tobytes()

    return msg

def convert_msg_to_matlike(msg: Image) -> MatLike:
    """

    バイト列を画像に変換する。

    Args:
        msg (Image): メッセージ

    Returns:
        frame (MatLike): 画像

    """
    # 情報の取得
    h, w, c = msg.height, msg.width, 3
    enc = msg.encoding.lower()
    step = int(msg.step)

    # 変換
    buf = np.frombuffer(msg.data, dtype=np.uint8)
    bytes_per_pixel = np.dtype(np.uint8).itemsize * c
    if step == w * bytes_per_pixel:
        frame = buf.reshape((h, w, c))
    else:
        row_view = buf.reshape((h, step // np.dtype(np.uint8).itemsize))
        useful = row_view[:, : (w * c)]
        frame = useful.reshape((h, w, c))

    return frame