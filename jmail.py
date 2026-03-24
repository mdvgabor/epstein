from __future__ import annotations

from pathlib import Path
from typing import Literal

import requests
from tqdm import tqdm

BASE_URL = "https://data.jmail.world/v1"

DatasetName = Literal[
    "emails",
    "emails-slim",
    "documents",
    "documents-full/VOL00009",
    "documents-full/VOL00010",
    "documents-full/DataSet11",
    "documents-full/VOL00008",
    "documents-full/other",
    "photos",
    "people",
    "photo_faces",
    "star_counts",
    "release_batches",
    "imessage_conversations",
    "imessage_messages",
]


def jmail(dataset: DatasetName, data_dir: str | Path = "data") -> Path:
    target = Path(data_dir) / f"{dataset}.parquet"
    if target.exists():
        return target

    target.parent.mkdir(parents=True, exist_ok=True)
    url = f"{BASE_URL}/{dataset}.parquet"

    with requests.get(url, stream=True) as response:
        response.raise_for_status()
        total = int(response.headers.get("content-length") or 0)

        with (
            target.open("wb") as handle,
            tqdm(
                total=total,
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
                desc=f"Downloading {dataset}",
            ) as progress,
        ):
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                handle.write(chunk)
                progress.update(len(chunk))

    return target
