"""运行时路径解析：三域分离后的**唯一真相来源**。

三域布局（容器根 = home）：

```text
<home>/
├── skill/    本仓库：代码与文档（CLI、生成器、脚本）
├── mcp/      独立仓库：omni-media（宿主原生听音版，read_audio）
├── mcp-ext/  独立目录：omni-media-ext（外部模型代读版，read_media）
└── output/   产物根：各任务工作区 + 运行时状态文件
```

为什么需要这个模块：拆分之前，仓库根、代码根、产物根是**同一个目录**，于是 4 个地方各自
用 `parents[2]` / `Path.cwd()` 猜路径。三域分离后三者不再相同，必须集中解析一次：

- **home_root()**：① `$BVB_HOME` → ② 从代码根向上找 `.bvb-home` 标记 → ③ 向上找含同级 `output/` 的祖先
  → ④ 兜底：代码根的父目录（即 `skill/` 的上一级）。
- **products_root()**：① `$BVB_OUTPUT_DIR`（绝对路径，或相对 home 的名字）→ ② `<home>/output`。

环境变量必须在进程启动前设置（`home_root()` 的结果会被 `TaskWorkspace` 在导入时固化一次，
与拆分前 `REPO_ROOT` 的语义一致）。
"""

import os
from pathlib import Path
from typing import Optional, Union

# 本文件位于 <skill>/src/core/paths.py，向上两级即**代码根**（skill/）
CODE_ROOT = Path(__file__).resolve().parents[2]

# home 锚点标记文件名（放在容器根，0 字节即可）
HOME_MARKER = ".bvb-home"
ENV_HOME = "BVB_HOME"
ENV_OUTPUT_DIR = "BVB_OUTPUT_DIR"
DEFAULT_PRODUCTS_DIRNAME = "output"


def code_root() -> Path:
    """代码根（本仓库根，即 `skill/`）。"""
    return CODE_ROOT


def _env_path(name: str, base: Optional[Path] = None) -> Optional[Path]:
    """读取路径类环境变量（相对路径按 base 或 cwd 解析）。"""
    raw = os.environ.get(name, "").strip()
    if not raw:
        return None
    path = Path(raw).expanduser()
    if path.is_absolute():
        return path
    return ((base or Path.cwd()) / path).resolve()


def home_root() -> Path:
    """容器根（`skill/`、`mcp/`、`output/` 的共同父目录）。"""
    env_home = _env_path(ENV_HOME)
    if env_home is not None:
        return env_home

    # 标记文件优先：容器根放一个 .bvb-home，重命名/搬迁后依然能定位
    for ancestor in (CODE_ROOT, *CODE_ROOT.parents):
        try:
            if (ancestor / HOME_MARKER).exists():
                return ancestor
        except OSError:
            continue

    # 其次：同级已存在 output/ 的祖先（排除代码根自身，避免 skill/output 被误判为容器根）
    for ancestor in CODE_ROOT.parents:
        try:
            if (ancestor / DEFAULT_PRODUCTS_DIRNAME).is_dir():
                return ancestor
        except OSError:
            continue

    # 兜底：代码根的父目录
    return CODE_ROOT.parent


def products_root() -> Path:
    """产物根（工作区与 .sessdata.json / .wbi_keys.json / .cli_status.json 的所在地）。"""
    env_output = _env_path(ENV_OUTPUT_DIR, base=home_root())
    if env_output is not None:
        return env_output
    return home_root() / DEFAULT_PRODUCTS_DIRNAME


def default_base_dir() -> str:
    """CLI / 脚本 `--base-dir` 的缺省值（绝对路径，不随当前工作目录漂移）。"""
    return str(products_root())


def resolve_base_dir(value: Union[str, Path, None] = None) -> Path:
    """解析 `--base-dir`：空 → 产物根；绝对路径 → 原样；相对路径 → cwd 优先，其次产物根下同名目录。

    相对路径的两级回退是为了兼容拆分前的用法（`--base-dir output` 在任意目录下依然能找到产物根）。
    """
    if value is None or not str(value).strip():
        return products_root()

    path = Path(str(value)).expanduser()
    if path.is_absolute():
        return path.resolve()

    cwd_candidate = Path.cwd() / path
    if cwd_candidate.exists():
        return cwd_candidate.resolve()

    under_products = products_root() / path
    if under_products.exists():
        return under_products.resolve()

    return cwd_candidate.resolve()


def describe() -> dict:
    """供 `cli.py info` / 自检展示的三域路径摘要。"""
    return {
        "code_root": str(code_root()),
        "home_root": str(home_root()),
        "products_root": str(products_root()),
        "home_env": ENV_HOME,
        "output_env": ENV_OUTPUT_DIR,
        "home_from_env": _env_path(ENV_HOME) is not None,
        "products_from_env": _env_path(ENV_OUTPUT_DIR, base=home_root()) is not None,
    }
