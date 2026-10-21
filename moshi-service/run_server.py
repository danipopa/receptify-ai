import os
import runpy
import sys

os.environ.setdefault("NO_TORCH_COMPILE", "1")

import torch

if not torch.cuda.is_available():
    torch.cuda.synchronize = lambda *_args, **_kwargs: None

torch.set_num_threads(max(1, int(os.getenv("MOSHI_CPU_THREADS", "4"))))

sys.argv = [
    "moshi.server",
    "--device",
    os.getenv("MOSHI_DEVICE", "cpu"),
    "--host",
    os.getenv("MOSHI_HOST", "0.0.0.0"),
    "--port",
    os.getenv("MOSHI_SERVER_PORT", "8998"),
]
runpy.run_module("moshi.server", run_name="__main__")
