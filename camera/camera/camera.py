# 型
from abc import ABC
from typing import Literal
from cv2.typing import MatLike

# 外部パッケージ
import atexit
import cv2
import numpy as np

class DummyVideoCapture:
    def __init__(
        self,
        dummy_capture_size: tuple[int, int]
    ):
        self.dummy_frame_shape = (*dummy_capture_size, 3)

    def isOpened(self):
        return True

    def read(self):
        ret = True
        frame: MatLike = np.zeros(self.dummy_frame_shape, dtype=np.uint8)
        return ret, frame

    def release(self):
        pass

class Camera(ABC):
    """

    このクラスは, 様々なカメラを扱うための汎用的な処理を記述した抽象基底クラスです.

    """

    def __init__(
        self,
        camera_type: Literal["csi", "usb", "dummy"],
        sensor_id: int = 0,
        pipeline: str|None = None,
        patient: int = 0,
        dummy_capture_size: tuple[int, int] = (84, 84),
    ) -> None:
        """

        Args:
            camera_type (Literam["csi", "usb", "dummy"]): カメラの種別
            sensor_id (int): カメラ番号
            patient (int): カメラ画像の取得に連続で失敗した際に強制終了する回数

        """

        self.camera_type = camera_type
        self.sensor_id = sensor_id
        self.pipeline = pipeline
        self.patient = patient
        self.dummy_capture_size = dummy_capture_size

        self.n_fail = 0

        self.cap: cv2.VideoCapture|DummyVideoCapture|None = self._get_capture(
            camera_type=camera_type,
            sensor_id=sensor_id,
            pipeline=pipeline,
            dummy_capture_size=dummy_capture_size
        )

    def _get_capture(
            self,
            camera_type: Literal["csi", "usb", "dummy"],
            sensor_id: int,
            pipeline: str|None = None,
            dummy_capture_size: tuple[int, int]|None = None
        ) -> cv2.VideoCapture|DummyVideoCapture:
        """

        カメラを取得する.

        Args:
            camera_type (Literal["csi", "usb"]): カメラの種別
            sensor_id (int): カメラ番号
            pipeline (str|None): CSIカメラを使用する場合のパイプライン
            dummy_capture_size: (tuple[int, int]) = ダミー画像生成時のサイズ

        Returns:
            cap (cv2.VideoCapture|DummyVideoCapture): カメラ

        """

        if camera_type == "csi":
            if pipeline is None:
                raise ValueError("CSI カメラ起動用のパイプラインが指定されていません.")

            cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)

        elif camera_type == "usb":
            cap = cv2.VideoCapture(sensor_id)

        elif camera_type == "dummy":
            if dummy_capture_size is None:
                raise ValueError(f"ダミー画像のサイズ dummy_capture_size が指定されていません.")
            cap = DummyVideoCapture(dummy_capture_size)

        else:
            raise ValueError(f"カメラ種別 '{camera_type}' は想定された形式ではありません.")

        # カメラが開けなかった場合にエラーを出力して終了する
        if not cap.isOpened():
            raise RuntimeError("GStreamer を通して CSI カメラ を開くことができませんでした.")

        # 何らかの事由で想定外のエラーが発生した場合もカメラを必ずリリースする
        atexit.register(cap.release)

        return cap

    def preprocess(self, frame: MatLike) -> MatLike:
        """
        
        画像に前処理を行う.

        Args:
            frame (MatLike): 対象フレーム

        Returns:
            frame (MatLike): 前処理後のフレーム
        
        """

        return frame

    def read(self) -> MatLike:
        """

        事前に設定されたカメラから画像を取得する.

        Returns:
            frame (str)

        """

        # カメラが取得されていない状態で実行されたとき, 強制終了する.
        if self.cap is None:
            raise RuntimeError("カメラが取得されていない状態で画像の取得を試みました. 最初に self.get_capture() を実行してください.")

        # カメラ画像の取得
        while True:
            self.ret, self.frame = self.cap.read()

            # カメラ画像の取得に成功した場合は連続失敗回数をリセットして画像を返す
            if self.ret:
                self.n_fail = 0
                return self.preprocess(self.frame)

            # 連続失敗回数を追加
            self.n_fail += 1

            if self.n_fail > self.patient:
                raise RuntimeError(f"カメラからの画像の取得に {self.patient} 回連続で失敗しました.")

    def release(self):
        """

        カメラを開放する.

        """

        if self.cap is not None:
            self.cap.release()

class DummyCamera(Camera):
    """

    このクラスは, カメラを接続していなくてもテスト可能なように, ダミー画像を生成するクラスです.

    """

    def __init__(
        self,
        sensor_id: int,
        capture_size: tuple[int, int] = (1280, 720),
        capture_hz: int = 30,
        resize: tuple[int, int] = (1280, 720),
        flip_method: int = 0,
        patient: int = 0
    ):
        """

        Args:
            sensor_id (int): カメラ番号
            capture_size (tuple[int, int]): 取得するカメラ画像のサイズ
            capture_fps (int): 1秒間にカメラ画像を取得する回数
            resize (tuple[int, int]): 取得したカメラ画像のリサイズ後の大きさ
            flip_method (int): 取得したカメラ画像の回転方向
            patient (int): カメラ画像の取得に連続で失敗した際に強制終了する回数

        """

        # ダミーカメラを作成
        super().__init__(
            camera_type="dummy",
            dummy_capture_size=capture_size
        )

        # 変数の保存
        self.sensor_id = sensor_id
        self.capture_size = capture_size
        self.capture_hz = capture_hz
        self.resize = resize
        self.flip_method = flip_method
        self.patient = patient

class CSICamera(Camera):
    """

    このクラスは, CSIカメラを用いてカメラ画像を取得するためのクラスです.

    """

    def __init__(
        self,
        sensor_id: int = 0,
        capture_size: tuple[int, int] = (1280, 720),
        capture_hz: int = 30,
        resize: tuple[int, int] = (1280, 720),
        flip_method: int = 0,
        patient: int = 0
    ) -> None:
        """

        Args:
            sensor_id (int): カメラ番号
            capture_size (tuple[int, int]): 取得するカメラ画像のサイズ
            capture_fps (int): 1秒間にカメラ画像を取得する回数
            resize (tuple[int, int]): 取得したカメラ画像のリサイズ後の大きさ
            flip_method (int): 取得したカメラ画像の回転方向
            patient (int): カメラ画像の取得に連続で失敗した際に強制終了する回数

        """

        # Gstreamer パイプラインを通してカメラを取得
        super().__init__(
            camera_type="csi",
            sensor_id=sensor_id,
            pipeline=self._create_pipeline(
                sensor_id=sensor_id,
                capture_size=capture_size,
                capture_hz=capture_hz,
                resize=resize,
                flip_method=flip_method
            ),
            patient=patient
        )

        # 変数の保存
        self.sensor_id = sensor_id
        self.capture_size = capture_size
        self.capture_hz = capture_hz
        self.resize = resize
        self.flip_method = flip_method
        self.patient = patient

    def _create_pipeline(self,
        sensor_id: int = 0,
        capture_size: tuple[int, int] = (1280, 720),
        capture_hz: int = 60,
        resize: tuple[int, int] = (1280, 720),
        flip_method: int = 0
    ) -> str:
        """

        Gsgreamer を通して CSI カメラを開くためのパイプラインを作成する.

        Args:
            sensor_id (int): カメラ番号
            capture_size (tuple[int, int]): 取得するカメラ画像のサイズ
            capture_fps (int): 1秒間にカメラ画像を取得する回数
            resize (tuple[int, int]): 取得したカメラ画像のリサイズ後の大きさ
            flip_method (int): 取得したカメラ画像の回転方向

        Returns:
            pipline (str): cv2.VideoCapture() で扱うためのパイプライン

        """

        # 取得する画像サイズとリサイズ後のサイズを決定
        w, h = capture_size
        rw, rh = resize

        return (
            f"nvarguscamerasrc sensor-id={sensor_id} ! video/x-raw(memory:NVMM), width={w}, height={h}, format=NV12, framerate={capture_hz}/1 ! "
            f"nvvidconv flip-method={flip_method} ! video/x-raw, width={rw}, height={rh}, format=BGRx ! "
            f"videoconvert ! video/x-raw, format=BGR ! "
            f"appsink drop=true max-buffers=1 sync=false"
        )
