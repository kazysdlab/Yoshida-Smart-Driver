# システム・前提
from typing import Optional
import time

# 外部
from smbus2 import SMBus

# ハイパーパラメータ
# PCA9685データシートより (https://cdn-shop.adafruit.com/datasheets/PCA9685.pdf)
# レジスタ
MODE1 = 0x00
PRESCALE = 0xFE
LED0_ON_L = 0x06

# 値
RESTART = 1 << 7
AI = 1 << 5
SLEEP = 1 << 4

class PCA9685:
    """

    PCA9685 のデータ書き込み操作を簡単化するクラス.

    """

    def __init__(self, bus_num: int = 1, address: int = 0x40, osc_freq_hz: float = 25_000_000, freq_hz: Optional[float] = None):
        self.bus_num = bus_num
        self.address = address
        self.osc_freq_hz = osc_freq_hz

        self.bus = SMBus(bus_num)

        mode1 = self._read8(MODE1)
        self._write8(MODE1, (mode1 | AI) & ~SLEEP)  # AI(Auto Increment)有効化
        time.sleep(0.005)  # 動作の安定化

        if freq_hz is not None:
            self.set_pwm_freq(freq_hz)

    def set_pwm_freq(self, freq_hz: float = 50.0):
        """
        
        動作周波数を設定

        Args:
            freq_hz (float, optional): 動作周波数.

        """
        # データシートからPRESCALEを計算
        prescale = int(round(self.osc_freq_hz / (4096.0 * freq_hz)) - 1)
        prescale = max(3, min(prescale, 255))

        old_mode = self._read8(MODE1)  # 現在の設定を読み込み
        self._write8(MODE1, (old_mode & ~RESTART) | SLEEP | AI)  # SLEEP有効化
        self._write8(PRESCALE, prescale)  # PRESCALE書き込み
        self._write8(MODE1, (old_mode | AI) & ~SLEEP)  # SLEEP解除
        time.sleep(0.005)  # 動作の安定化
        self._write8(MODE1, (old_mode | AI | RESTART) & ~SLEEP)  # RESTART有効化

        self.current_freq_hz = freq_hz

    def _set_pwm(self, ch: int, on_count: int, off_count: int):
        """
        
        特定チャンネルにデータを書き込み

        Args:
            ch (int): チャンネル
            on_count (int): ONタイミング
            off_count (int): OFFタイミング

        """
        base = LED0_ON_L + 4 * ch  # 書き込み開始アドレス
        data = [
            on_count & 0xFF,  # ONタイミング (下位8bit)
            (on_count >> 8) & 0x0F,  # ONタイミング (上位4bit)
            off_count & 0XFF,  # OFFタイミング (下位8bit)
            (off_count >> 8) & 0x0F  # OFFタイミング (上位4bit)
        ]
        self.bus.write_i2c_block_data(self.address, base, data)

    def set_pwm_us(self, ch: int, pulse_us: float):
        """
        
        パルス幅を利用してデータを書き込み

        Args:
            ch (int): チャンネル
            pulse_us (float): パルス幅

        """

        # 1カウント当たりのusを計算
        period_us = 1_000_000.0 / self.current_freq_hz
        us_per_count = period_us / 4096.0

        # パルス幅の計算
        counts = int(round(pulse_us / us_per_count))
        counts = max(0, min(counts, 4095))

        # データ書き込み
        self._set_pwm(ch, 0, counts)

    def close(self):
        """
        
        バスを閉じる

        """

        try:
            self.bus.close()
        except Exception:
            pass

    def _read8(self, reg: int) -> int:
        """
        
        レジスタのバイトデータを読み込む.

        Args:
            reg (int): レジスタ

        Returns:
            int: バイトデータ
        """

        return self.bus.read_byte_data(self.address, reg)

    def _write8(self, reg: int, val: int):
        """
        
        レジスタにバイトデータを書き込む.

        Args:
            reg (int): レジスタ
            val (int): データ
        """

        self.bus.write_byte_data(self.address, reg, val & 0xFF)  # 8ビットにマスクしてから書き込み
