"""运行时路径解析：三域分离后的**唯一真相来源**。

三域布局（容器根 = home）：

```text
<home>/
├── skill/       本仓库：代码与文档（CLI、生成器、脚本）
├── omni-media/  另一个仓库：两个音视频 MCP 服务
│   ├── mcp/         宿主原生听音版（read_audio，零凭证）
│   └── mcp-ext/     外部模型代读版（read_media，配置驱动）
└── output/      产物根：各任务工作区 + 运行时状态文件
```

两个 MCP 曾是容器根下平级的两个目录，现已收进**同一个** `omni-media/` 仓库；
`mcp_repo()` / `mcp_ext_repo()` 负责解析它们的位置，并兼容迁移前的旧布局。

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

# 本文件位于 <技能根>/src/core/paths.py，向上两级即**代码根**（= 技能根 = 安装单元）
CODE_ROOT = Path(__file__).resolve().parents[2]

# home 锚点标记文件名（放在容器根，0 字节即可）
HOME_MARKER = ".bvb-home"
ENV_HOME = "BVB_HOME"
ENV_OUTPUT_DIR = "BVB_OUTPUT_DIR"
DEFAULT_PRODUCTS_DIRNAME = "output"

# 两个 MCP 服务所在仓库与子目录名（三域中的第二域）
DEFAULT_MCP_REPO_DIRNAME = "omni-media"
DEFAULT_MCP_DIRNAME = "mcp"
DEFAULT_MCP_EXT_DIRNAME = "mcp-ext"
ENV_MCP_DIR = "OMNI_MEDIA_MCP_DIR"


def code_root() -> Path:
    """代码根 = 本 **skill 根**（`SKILL.md` 所在的安装单元目录，`src/` 与 `scripts/` 都在其下）。

    注意它不是「仓库根」：仓库根是插件/分发单元（含 README、平台声明），技能根在它下面一层或两层。
    """
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
    """容器根（`skill/`、`omni-media/`、`output/` 的共同父目录）。"""
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

    # 兜底（没有任何显式信号时）：技能位于 <X>/skills/<name>/ 是标准布局，
    # 此时取 <X> 的上一级——与拆分前「仓库的父目录」等价，保证默认产物根**不在技能/仓库目录内**。
    # 若直接取 CODE_ROOT.parent，搬进 skills/ 之后会变成 <仓库>/skills（落在仓库工作树里）。
    if CODE_ROOT.parent.name == "skills":
        上一级 = CODE_ROOT.parent.parent.parent
        if 上一级 != 上一级.parent:  # 别一路退到文件系统根
            return 上一级
    return CODE_ROOT.parent


def is_container_layout() -> bool:
    """当前是否处于**容器布局**（`skill/` 与 `omni-media/`、`output/` 平级的 home 目录）。

    判定只看两个**显式**信号：`$BVB_HOME`，或代码根任一层祖先里的 `.bvb-home` 标记。

    为什么要单独判：全新克隆（裸 clone / zip 解压）通常两者都没有，此时 `home_root()`
    会落到「代码根的父目录」这个兜底值，产物根也随之落到别处。自检据此把「容器专属」
    断言（容器根不得是 git 仓库、omni-media/ 必须是独立仓库等）降级为提示，
    而不是把一次正常的独立使用判成错误。
    """
    if _env_path(ENV_HOME) is not None:
        return True
    for ancestor in (CODE_ROOT, *CODE_ROOT.parents):
        try:
            if (ancestor / HOME_MARKER).exists():
                return True
        except OSError:
            continue
    return False


def mcp_repo() -> Path:
    """宿主原生听音版（`read_audio`）的目录。

    解析顺序：① `$OMNI_MEDIA_MCP_DIR`（显式覆盖，绝对路径或相对 home 的路径）
    → ② `<home>/omni-media/mcp`（迁移后的新布局）→ ③ `<home>/mcp`（迁移前的旧布局兜底）
    → ④ 都不存在时仍返回新布局路径，让调用方的报错指向**预期位置**而不是一个空值。
    """
    env_dir = _env_path(ENV_MCP_DIR, base=home_root())
    if env_dir is not None:
        return env_dir
    new_layout = home_root() / DEFAULT_MCP_REPO_DIRNAME / DEFAULT_MCP_DIRNAME
    if new_layout.exists():
        return new_layout
    legacy = home_root() / DEFAULT_MCP_DIRNAME
    if legacy.exists():
        return legacy
    return new_layout


def mcp_ext_repo() -> Path:
    """外部模型代读版（`read_media`）的目录。

    布局规则与 `mcp_repo()` 一致，但**不受** `$OMNI_MEDIA_MCP_DIR` 影响：那个变量只针对原生听音版
    （两个服务是各自独立的包，用一个变量同时改两个位置只会造成误配）。
    """
    new_layout = home_root() / DEFAULT_MCP_REPO_DIRNAME / DEFAULT_MCP_EXT_DIRNAME
    if new_layout.exists():
        return new_layout
    legacy = home_root() / DEFAULT_MCP_EXT_DIRNAME
    if legacy.exists():
        return legacy
    return new_layout


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
        "mcp_repo": str(mcp_repo()),
        "mcp_ext_repo": str(mcp_ext_repo()),
        "mcp_from_env": _env_path(ENV_MCP_DIR, base=home_root()) is not None,
    }
