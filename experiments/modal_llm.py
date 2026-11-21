"""A vLLM server on Modal to try a quantized model (e.g. NVFP4) before it goes on the V100 server.

    uvx modal setup                                         # once: log in
    uvx modal secret create catix-llm-key LLM_API_KEY=$(openssl rand -hex 24)
    uvx modal deploy experiments/modal_llm.py               # prints the URL

Then in .env (LLM_MODEL is the repo id, as served):
    LLM_ROUTE=<url>/v1
    LLM_MODEL=RedHatAI/Qwen3.5-9B-NVFP4
    LLM_API_KEY=<the key from the secret>

After SCALEDOWN seconds without requests the container stops (the next request waits for a cold start of a few minutes);
`uvx modal app stop catix-llm` removes the app. Every setting below can be overridden by an environment variable
at deploy time: `MODEL=Qwen/Qwen3.5-9B GPU=A100 uvx modal deploy experiments/modal_llm.py`.
"""

import os

import modal

MODEL = os.environ.get("MODEL", "RedHatAI/Qwen3.5-9B-NVFP4")
GPU = os.environ.get("GPU", "L40S")  # not B200: there NVFP4 also quantizes the activations; on the V100 only the weights
MAX_LEN = os.environ.get("MAX_LEN", "32768")
SCALEDOWN = int(os.environ.get("SCALEDOWN", "300"))
PORT = 8000

image = (
    modal.Image.from_registry("nvidia/cuda:12.9.0-devel-ubuntu22.04", add_python="3.12")
    .entrypoint([])
    .uv_pip_install("vllm", "transformers")
    .env({"HF_XET_HIGH_PERFORMANCE": "1"})
)
hf_cache = modal.Volume.from_name("huggingface-cache", create_if_missing=True)
vllm_cache = modal.Volume.from_name("vllm-cache", create_if_missing=True)

app = modal.App("catix-llm")


@app.server(
    image=image,
    gpu=GPU,
    scaledown_window=SCALEDOWN,
    startup_timeout=15 * 60,
    volumes={"/root/.cache/huggingface": hf_cache, "/root/.cache/vllm": vllm_cache},
    port=PORT,
    target_concurrency=8,
    unauthenticated=True,  # the endpoint is public, the bearer key below is the lock
    secrets=[modal.Secret.from_name("catix-llm-key")],
)
class Server:
    @modal.enter()
    def start(self):
        import subprocess

        cmd = [
            "vllm", "serve", MODEL,
            "--served-model-name", MODEL,
            "--host", "0.0.0.0", "--port", str(PORT),
            "--api-key", os.environ["LLM_API_KEY"],
            "--max-model-len", MAX_LEN,
            "--enable-auto-tool-choice", "--tool-call-parser", "qwen3_coder",
            "--reasoning-parser", "qwen3",
            "--scheduling-policy", "priority",  # catix sends `priority` with each call (LLM_PRIORITY)
        ]
        self.process = subprocess.Popen(cmd)

    @modal.exit()
    def stop(self):
        self.process.terminate()
