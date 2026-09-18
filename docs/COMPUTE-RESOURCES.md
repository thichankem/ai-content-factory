# Compute resources — using the GPU, and staying alive while it runs

Everything here is measured on the reference machine (a laptop with an **RTX 4060
Laptop 8 GB**, driver **566.24**, 16 threads, 16 GB RAM) rather than quoted from a
benchmark chart. Numbers from another machine will differ; the *decision procedure*
is what transfers, and it is implemented in
[`resources.py`](../src/content_factory/resources.py) and
[`hardware.py`](../src/content_factory/hardware.py).

Three questions, answered in order:

1. [Which encoder, and on which ffmpeg build?](#1-an-encoder-is-a-property-of-a-build)
2. [Should this job use the GPU right now?](#2-admission-when-a-job-may-start)
3. [What if the machine gets into trouble mid-job?](#3-abort-when-a-job-must-stop)

---

## 1. An encoder is a property of a *build*

The single most useful fact discovered here: **`h264_nvenc` is not a capability, it
is a *(binary, encoder)* pair.** ffmpeg is compiled against a specific NVENC API
version, and a driver that is older than that refuses to open the encoder even
though the build lists it.

On the reference machine:

```
ffmpeg 9.0.1 (system, winget)  →  h264_nvenc  ✗  Driver does not support the
                                                  required nvenc API version.
                                                  Required: 13.1  Found: 12.2
ffmpeg 7.1  (bundled, in .venv) →  h264_nvenc  ✓  encodes on the GPU
```

So the GPU is usable **with nothing installed**, because a Python package that was
already in the environment (`imageio-ffmpeg`) shipped a build compiled against the
older API.

`probe()` therefore discovers *every* candidate and the governor opens each
*(build, encoder)* pair for real — one frame, cached for the process life:

| Order | Source | Why |
|---|---|---|
| 1 | `CONTENT_FACTORY_FFMPEG_BINARY` | an explicit operator choice wins |
| 2 | `ffmpeg` on `PATH` | the machine's own build; never silently bypassed |
| 3 | `CONTENT_FACTORY_FFMPEG_EXTRA_BINARIES` | `os.pathsep`-separated escape hatch |
| 4 | a bundled build (`imageio-ffmpeg`) | present only if the package is installed |

A working primary build is **never** redirected to another binary. The override only
happens when the primary cannot start the encoder, and `GET /resources` reports both
the encoder and the binary that will run it:

```json
"hardware_encoder": {
  "encoder": "h264_nvenc",
  "binary": "…\\.venv\\Lib\\site-packages\\imageio_ffmpeg\\binaries\\ffmpeg-win-x86_64-v7.1.exe"
}
```

### Why bother, when x264 is already fast?

Because the point on a laptop is not peak speed, it is **where the work happens**.
The pipeline renders with `render_threads = 1` by default so the machine stays
responsive; measured at that setting (600 frames, 1080×1920):

| Encoder | Time | CPU used |
|---|---|---|
| libx264 `-threads 1` | 4791 ms | all of it |
| **h264_nvenc `-threads 1`** | **3095 ms** | almost none |
| libx264 with `-filter_threads 1` | 4697 ms | all of it |
| **nvenc with `-filter_threads 1`** | **2072 ms** | almost none |

With all 16 threads free, software wins at this resolution (libx264 `veryfast`
1108 ms) — and that is the trade being made: an NVENC export is *faster than the
single-threaded default* **and** leaves the cores available. Raise
`CONTENT_FACTORY_RENDER_THREADS` if you would rather have raw speed and a busy
machine.

Pure encode throughput, for when the encoder really is the bottleneck:

| Output | libx264 veryfast | h264_nvenc p4 | h264_nvenc p1 |
|---|---|---|---|
| 1080×1920 | 541 fps | 291 fps | 795 fps |
| 4K | 17.6 fps | 42.5 fps | 93.6 fps |

Hardware encode pays at high resolution and does not at 1080p with a free CPU —
which is exactly why the choice is made from a real probe rather than a rule.

### Hardware decode is off, and that is deliberate

`render_hwaccel: "auto"` means **off**. Decode acceleration only pays when the
decoded frames stay on the GPU; this project's filter graph (`scale`, `crop`,
`drawtext`) and its software encoder both run on the CPU, so frames are uploaded
and downloaded again — a full PCIe round trip per frame for nothing. Reading one
clip and discarding it:

| Source | software | `-hwaccel cuda` | `-hwaccel d3d11va` |
|---|---|---|---|
| 3 s 720p | **120 ms** | 955 ms | 273 ms |
| 60 s 1080p | **626 ms** | 1914 ms | 2139 ms |
| 20 s 4K | **812 ms** | 2292 ms | 2604 ms |

Hardware decode loses at every size. Set an explicit name
(`CONTENT_FACTORY_RENDER_HWACCEL=cuda`) only for a GPU-resident graph; the render
still retries in software if it fails.

---

## 2. Admission: when a job may start

`ResourceGovernor.begin()` serializes heavy work and then walks a ladder:

1. **No GPU, or `compute_policy: "cpu"`** → CPU. Not degraded, just configured.
2. **Another heavy job running** → wait for the slot (bounded by
   `heavy_wait_seconds`), so two exports never fight on one laptop.
3. **GPU hot, saturated, or short of VRAM** → poll with backoff until it cools or
   frees, up to `gpu_wait_seconds`.
4. **Still busy** → run on CPU and record *why*, rather than blocking forever.

Ask before committing:

```bash
curl localhost:8000/resources/explain?kind=render
curl localhost:8000/resources
```

Every decision lands in `stats` (`gpu_jobs`, `cpu_jobs`, `degraded_jobs`,
`serialized_jobs`, `longest_wait_seconds`, `encoder_fallbacks`) and the last one in
`last_decision`, so "why was that export slow?" has an answer.

---

## 3. Abort: when a job must stop

A deadline catches a hang. The failure that actually matters is the opposite: a
render working perfectly while it drags the machine down. So the process is watched
while it runs, and terminated if the machine is in real trouble.

| Setting | Default | Meaning |
|---|---|---|
| `RAM_ABORT_MB` | `350` | free RAM below this aborts (the box is about to swap) |
| `GPU_ABORT_TEMPERATURE_C` | `90` | GPU at or above this aborts |
| `RENDER_MONITOR_SECONDS` | `3.0` | how often pressure is re-read |
| `RENDER_TIMEOUT_SECONDS` | `1800` | the hard deadline, still there |

These sit **well outside** the admission thresholds (`ram_min_available_mb = 700`,
`gpu_max_temperature_c = 82`) on purpose: ordinary load must never kill work, only a
machine genuinely in trouble. An aborted render raises a `RenderError` naming the
reason, so the failure is diagnosable rather than mysterious. The monitor reads RAM
and a GPU temperature only — no ffmpeg subprocesses — so watching costs nothing on
the machine being watched.

Both are covered by tests that abort a real process
(`tests/test_resources.py::test_the_watchdog_kills_a_long_render_under_pressure`)
and by `scripts/qa_nvenc_path.py`.

---

## 4. Unlocking the GPU for *models* (torch)

The 4060 currently does video encoding only. Anything torch-based — OCR,
background removal, upscaling, `faster-whisper` — still runs on the CPU, because
the installed torch is a CPU-only build:

```
torch 2.14.0+cpu     torch.cuda.is_available() == False
onnxruntime          providers: ('AzureExecutionProvider', 'CPUExecutionProvider')
```

Nothing in the code needs changing: `model_device()` already returns `cuda` the
moment `torch.cuda.is_available()` is true, and `ONNX Runtime GPU provider
available` appears in `GET /resources` when the runtime exposes one. What is
missing is the build itself:

```bash
# CUDA 12.6 wheels; ~2.5 GB download. Match the index URL to your driver:
# sm_89 (Ada, RTX 40-series) needs CUDA 11.8+.
.venv/Scripts/python.exe -m pip install --index-url https://download.pytorch.org/whl/cu126 torch
```

Then confirm rather than assume:

```bash
.venv/Scripts/python.exe -c "import torch; print(torch.cuda.is_available(), torch.__version__)"
curl localhost:8000/resources | python -m json.tool | grep -i cuda
```

`GET /resources → advice` stops saying *"torch is CPU-only"* once it is true.

---

## 5. Tuning a different laptop

Every threshold is a setting, so nothing needs editing:

| Knob | When to touch it |
|---|---|
| `COMPUTE_POLICY=cpu` | you want the GPU left entirely alone |
| `RENDER_THREADS=4` | raw export speed matters more than a responsive machine |
| `RENDER_ENCODER=cpu` \| `nvenc` \| `qsv` \| `amf` | pin the encoder; `amf`/`qsv` are iGPU encoders (fast, much bigger files) and are opt-in, never automatic |
| `MAX_HEAVY_JOBS=2` | a workstation with cores to spare |
| `GPU_MAX_TEMPERATURE_C` | your chassis runs hotter or cooler than this one |
| `RAM_ABORT_MB` | the floor is wrong for your total RAM |
| `PROFILE_TTL_SECONDS` | how long a hardware reading is trusted |
