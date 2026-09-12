# 型
from typing import cast, Callable, TypedDict
from dataclasses import dataclass
from collections import defaultdict

# 外部パッケージ
from evdev import InputDevice, ecodes, list_devices, AbsInfo, InputEvent

# 独自型の定義
AbsEventMap = dict[int, tuple[str, list[str]]]
KeyEventMap = dict[int, str]

@dataclass
class Maps:
    axis: AbsEventMap
    button: KeyEventMap

class State(TypedDict):
    axis: defaultdict[str, float]
    button: defaultdict[str, bool]

# !!!!! ゲームパッドごとのイベントコード・キーマップをここに追加する !!!!!
KEY_MAPS: dict[str, Maps] = {
    "dualsense": Maps(
        axis = {
            0: ("lx", ["scale_center", "deadzone"]),
            1: ("ly", ["scale_center", "invert", "deadzone"]),
            2: ("rx", ["scale_center", "deadzone"]),
            5: ("ry", ["scale_center", "invert", "deadzone"]),
            3: ("l2", ["normalize"]),
            4: ("r2", ["normalize"]),
            16: ("dpx", ["invert", "clamp"]),
            17: ("dpy", ["invert", "clamp"])
        },
        button = {
            304: "square",
            305: "cross",
            306: "circle",
            307: "triangle",
            308: "l1",
            310: "l2",
            314: "l3",
            309: "r1",
            311: "r2",
            315: "r3",
            317: "touch",
            312: "share",
            313: "option",
            316: "ps"
        }
    )
}

class Gamepad:
    """

    このクラスは USB, Bluetooth を問わず, 接続されたゲームパッド入力デバイスを扱うためのクラスです.

    """

    def __init__(
        self,
        gamepad_type: str,
        gamepad_path: str = "",
        gamepad_search_words: list[str] = [],
        deadzone: float = 0.05
    ):
        """

        Args:
            gamepad_type (Literal["dualsense"]): ゲームパッドの名称 (キーマップ辞書の参照キー)
            gamepad_path (str|None): ゲームパッドのパス
            gamepad_search_words (list[str]): ゲームパッドのパスが見つからない場合に検索するための文字列のリスト
            deadzone (float): アナログ入力の不感帯の絶対値

        """

        # 変数の保存
        self.deadzone = deadzone

        # ゲームパッドの取得
        self.path = gamepad_path if gamepad_path != "" else self._find_gamepad_path(search_words=gamepad_search_words)
        self.gamepad = InputDevice(self.path)

        # ゲームパッドのキーと値のマップ
        self.keymaps = KEY_MAPS[gamepad_type]
        self.state: State = {
            "axis": defaultdict(lambda: 0.0),
            "button": defaultdict(lambda: False)
        }

        # 辞書のリセット
        for (_, (name, _)) in self.keymaps.axis.items():
            self.state["axis"][name]
        for (_, name) in self.keymaps.button.items():
            self.state["button"][name]

        # 値の前処理の辞書
        self.preprocess_dict: dict[str, Callable[[int, float], float]] = {
            "invert": self._invert,
            "scale_center": self._scale_center,
            "deadzone": self._apply_deadzone,
            "normalize": self._normalize,
            "clamp": self._clamp
        }

        # 軸レンジの取得
        abs_caps = cast(
            list[tuple[int, AbsInfo]],
            self.gamepad.capabilities(absinfo=True).get(ecodes.EV_ABS, [])
        )
        self.abs_info: dict[int, AbsInfo] = dict(abs_caps)

    def _find_gamepad_path(self, search_words: list[str] = []) -> str:
        """

        ゲームパッドのパスを取得する.
        使用可能なゲームパッドが見つからない場合, RuntimeError よりプログラムを終了する.

        Args:
            search_words (list[str]): ゲームパッドを探すにあたって使用する検索文字列

        Returns:
            path (str): 取得したゲームパッドのパス

        """

        for path in list_devices():
            device = InputDevice(path)
            name = (device.name or "").lower()
            for search_word in search_words:
                if search_word in name:
                    return path

        raise RuntimeError("使用可能なゲームパッドが見つかりませんでした.")

    def read(self) -> State:
        """

        前回の self.read() から今までに発生したゲームパッドのイベントを全て消化し, 状態の更新をする.

        Returns:
            state (State): ゲームパッドの状態の辞書

        """

        while True:
            # 未消化のイベントを一つ読み取る
            event = cast(InputEvent|None, self.gamepad.read_one())

            # 無ければループ終了
            if event is None:
                break

            # 値の読み取り
            code = event.code
            value = event.value

            # 軸操作イベントの処理 (連続値)
            if event.type == ecodes.EV_ABS:
                keymap = self.keymaps.axis
                key, preprocess = keymap[code]

                # 事前にマップに設定された前処理を全て適用する
                for proc_key in preprocess:
                    value = self.preprocess_dict[proc_key](code, float(value))

                # 型変換
                value = float(value)

                self.state["axis"][key] = value

            # ボタン操作イベント (離散値)
            elif event.type == ecodes.EV_KEY:
                keymap = self.keymaps.button
                key = keymap[code]

                #型変換
                value = bool(value)

                # ゲームパッド状態の更新
                self.state["button"][key] = value

            else:
                continue

        return self.state

    def _invert(self, code: int, value: float) -> float:
        """

        値を -1 倍して反転する.

        Args:
            code (int): イベントコード
            value (float): 値

        Returns:
            (float): 変換後の値

        """

        return -1 * value

    def _scale_center(self, code: int, value: float) -> float:
        """

        スティック状態のスケールを 0.0 センターに変換する.

        Args:
            code (int): イベントコード
            value (float): 値

        Returns:
            (float): 変換後の値

        """

        info = self.abs_info[code]

        min_value, max_value = info.min, info.max
        mid_value = (min_value + max_value) / 2.0

        value_range = max(max_value - mid_value, mid_value - min_value) or 1.0

        return max(-1.0, min(1.0, (value - mid_value) / value_range))

    def _apply_deadzone(self, code: int, value: float) -> float:
        """

        デッドゾーンを適用する.

        Args:
            code (int): イベントコード
            value (float): 値

        Returns:
            (float): 適用後の値

        """

        return 0.0 if abs(value) < self.deadzone else value

    def _normalize(self, code: int, value: float) -> float:
        """

        値を[0, 1]の範囲に変換する.

        Args:
            code (int): イベントコード
            value (float): 値

        Returns:
            (float): 変換後の値

        """

        info = self.abs_info[code]

        rng = (info.max - info.min) or 1.0

        return max(0.0, min(1.0, (value - info.min) / rng))

    def _clamp(self, code: int, value: float) -> float:
        """

        値を [-1, 1] の範囲にクランプする.

        Args:
            code (int): イベントコード
            value (float): 値

        Returns:
            (float): 変換後の値

        """

        return int(max(-1.0, min(1.0, value)))
