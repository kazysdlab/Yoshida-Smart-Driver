import os
from datetime import datetime

import h5py
import numpy as np

class H5Writer:
    """

    HDF5 形式でデータを保存するライタ.

    """

    def __init__(
        self,
        output_dir: str,
        prefix: str = "ysd_tt02",
        flush_every: int = 50,
        compression: str|None = "lzf",
        attrs: dict|None = None,
    ):
        os.makedirs(output_dir, exist_ok=True)

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.path = os.path.join(output_dir, f"{prefix}_{stamp}.h5")
        self.file = h5py.File(self.path, "w")

        self.flush_every = flush_every
        self.compression = compression

        self.n = 0
        self._created = False

        for k, v in (attrs or {}).items():
            self.file.attrs[k] = v

    def _create_datasets(self, image: np.ndarray):
        comp = self.compression
        h, w, c = image.shape

        self.file.create_dataset(
            "image", shape=(0, h, w, c), max_shape=(None, h, w, c),
            dtype=np.uint8, chunks=(1, h, w, c), compression=comp
        )
        self.file.create_dataset(
            "action", shape=(0, 2), maxshape=(None, 2),
            dtype=np.float32, chunks=(256, 2)
        )
        self.file.create_dataset(
            "stamp_image_ns", shape=(0,), maxshape=(None,),
            dtype=np.int64, chunks=(256,)
        )
        self.file.create_dataset(
            "stamp_action_ns", shape=(0,), maxshape=(None,),
            dtype=np.int64, chunks=(256,)
        )
        self.file.create_dataset(
            "delta_t", shape=(0,), maxshape=(None,),
            dtype=np.float64, chunks=(256,)
        )

        self._created = True

    def append(
        self,
        image: np.ndarray,
        action: np.ndarray,
        stamp_image_ns: int,
        stamp_action_ns: int,
    ):
        if not self._created:
            self._create_datasets(image)

        i = self.n
        for name in ("image", "action", "stamp_image_ns", "stamp_action_ns", "delta_t"):
            self.file[name].resize(i+1, axis=0)

        self.file["image"][i] = image
        self.file["action"][i] = action
        self.file["stamp_image_ns"][i] = stamp_image_ns
        self.file["stamp_action_ns"][i] = stamp_action_ns
        self.file["delta_t"][i] = (stamp_action_ns - stamp_image_ns) * 1e-9

        self.n += 1
        if self.n % self.flush_every == 0:
            self.file.flush()

    def close(self):
        if self.file:
            self.file.attrs["num_samples"] = self.n
            self.file.flush()
            self.file.close()