"""运行时路径解析：三域分离后的**唯一真相来源**。

**容器根是可选的。** 本技能装到任何宿主的任何工作目录下都能直接跑：

```text
① 容器布局生效（存在标记，且你就在该容器内工作）——沿用容器布局：
<home>/
├── skill/       本仓库：代码与文档（CLI、生成器、脚本）
├── omni-media/  另一个仓库：两个音视频 MCP 服务
│   ├── mcp/         宿主原生听音版（read_audio，零凭证）
│   └── mcp-ext/     外部模型代读版（read_media，配置驱动）
└── output/      产物根：各任务工作区 + 运行时状态文件

② 其余情况（没有标记，或把技能软链到平台技能目录后在别的目录干活）——产物落在**当前工作目录**下：
<你干活的那个目录>/output/
```

两个 MCP 曾是容器根下平级的两个目录，现已收进**同一个** `omni-media/` 仓库；
`mcp_repo()` / `mcp_ext_repo()` 负责**实际探查**它们的位置（见 `mcp_candidate_bases()`），
并兼容迁移前的旧布局——**但听音通道是否可用，由 Agent 在用时按自己的工具列表判定**
（见 SKILL §4.2），与这两个目录是否存在无关；它们只影响 `info` 里的位置提示。

为什么需要这个模块：拆分之前，仓库根、代码根、产物根是**同一个目录**，于是 4 个地方各自
用 `parents[2]` / `Path.cwd()` 猜路径。三域分离后三者不再相同，必须集中解析一次：

- **container_home()**：**只认显式信号** —— `$BVB_HOME`，或代码根任一层祖先里的 `.bvb-home` 标记；
  都没有时返回 `None`（这正是「新装即用、无需配置」的默认情形）。
- **home_root()**：`container_home()` → 向上找含同级 `output/` 的祖先 → 兜底**剥离连续的
  `skill`/`skills` 包裹层**后取父目录。它只用于 MCP 仓库位置提示与容器布局判定，
  **不再决定产物落在哪**。（`TaskWorkspace` 的相对路径基准已改为 `products_root().parent`，
  不再依赖这个可能取不到真值的兜底。）
- **products_root()**：① `$BVB_OUTPUT_DIR`（绝对路径，或相对容器根/工作目录的名字）
  → ② 有容器标记**且当前工作目录在该容器内**时的 `<home>/output`
  → ③ **否则 `<当前工作目录>/output`**（默认语义）。
  判据里带上 cwd，是因为标记是从**代码位置**向上找的：技能被软链进平台技能目录后代码位置
  仍指向原容器，只认标记会把产物写回原容器，而不是使用者当前干活的目录。

环境变量必须在进程启动前设置（`TaskWorkspace` 会在导入时把 `products_root()` 固化一次作为
相对路径基准，与拆分前 `REPO_ROOT` 的语义一致）。
"""

import os
from pathlib import Path
from typing import List, Optional, Union

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


def container_home() -> Optional[Path]:
    """**显式**容器根的信号：`$BVB_HOME`，或代码根任一层祖先里的 `.bvb-home` 标记。

    都没有时返回 `None`——这就是「新装即用」的默认情形：不配置任何东西，
    产物落在当前工作目录下（见 `products_root()`）。
    """
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
    return None


def home_root() -> Path:
    """容器根（`skill/`、`omni-media/`、`output/` 的共同父目录）。

    只用于容器布局判定，以及作为 `mcp_candidate_bases()` 的**候选之一**；
    **产物根与 manifest 相对路径基准都不由它决定**（前者走 `products_root()`，
    后者走 `products_root().parent`），`mcp_repo()` 也不再直接拼它而是实际探查
    ——没有显式容器信号时它只是个**尽力而为的提示值**，取不到真容器根是正常情形，
    调用方不得把它当作事实判据。
    """
    explicit = container_home()
    if explicit is not None:
        return explicit

    # 其次：同级已存在 output/ 的祖先（排除代码根自身，避免 skill/output 被误判为容器根）
    for ancestor in CODE_ROOT.parents:
        try:
            if (ancestor / DEFAULT_PRODUCTS_DIRNAME).is_dir():
                return ancestor
        except OSError:
            continue

    # 兜底（没有任何显式信号时）：**剥离包裹技能的连续 `skill` / `skills` 层**，取其父目录。
    # 包裹层的个数随安装方式而变，因此必须逐层剥离，**不能写死层数**：
    #   <容器根>/skill/skills/video2book    （本仓库的容器布局，两层）→ <容器根>
    #   ~/.workbuddy/skills/video2book      （平台用户级安装，一层）  → ~/.workbuddy
    #   ~/.claude/skills/video2book         （同上）                  → ~/.claude
    # 旧实现写死「退 3 层」，只对两层布局成立；遇到单层布局会**多退一层**，把锚点抛到
    # 用户主目录（实测 Windows 上即 `C:\Users\<name>`），连带 manifest 的相对路径基准
    # 一起错位——产物在别的盘符时会令 `relative_to` / `relpath` 双双失败，
    # 最终把本应是 `output/<task>/...` 的相对路径降级写成了绝对路径。
    anchor = CODE_ROOT
    while anchor.parent != anchor and anchor.parent.name in ("skill", "skills"):
        anchor = anchor.parent
    父目录 = anchor.parent
    if 父目录 != anchor:  # 别一路退到文件系统根
        return 父目录
    return CODE_ROOT.parent


def is_container_layout() -> bool:
    """当前是否处于**容器布局**（`skill/` 与 `omni-media/`、`output/` 平级的 home 目录）。

    判定只看两个**显式**信号：`$BVB_HOME`，或代码根任一层祖先里的 `.bvb-home` 标记。

    为什么要单独判：全新克隆（裸 clone / zip 解压）通常两者都没有，此时产物根按默认语义
    落在**当前工作目录**下；自检据此把「容器专属」断言（容器根不得是 git 仓库、
    omni-media/ 必须是独立仓库等）降级为提示，而不是把一次正常的独立使用判成错误。
    """
    return container_home() is not None


def mcp_candidate_bases() -> List[Path]:
    """寻找 `omni-media/` 仓库时要顺次探查的父目录（去重、保序）。

    顺序反映「用户最可能把它放在哪」：

    1. **产物根的父目录** —— 默认布局下 `output/` 与 `omni-media/` 就是平级的两个域，
       而产物根本身已按「容器内 → `<home>/output`；否则 → `<cwd>/output`」正确解析过，
       所以它的父目录是命中率最高、且与「使用者当前在哪干活」一致的那个候选；
    2. 当前工作目录 —— 覆盖没跑过产物、但就在仓库旁边干活的情形；
    3. `home_root()` —— 容器布局下的规范位置（也是唯一的提示值来源）；
    4. 代码根及其各层祖先 —— 兼容技能被放进容器内、而 `omni-media/` 在上层的布局。

    为什么要「找」而不是「拼」：`home_root()` 在没有容器信号时只是个**尽力而为的提示值**，
    拼出来的路径可能根本不存在（实测平台安装下会指向 `~/.workbuddy/omni-media`，
    而仓库其实就在工作目录里）。拼字符串等于把提示值当成事实，`info` 会被它带偏。
    """
    bases: List[Path] = []
    try:
        bases.append(products_root().parent)
    except Exception:  # noqa: BLE001 - 解析失败不应影响其余候选
        pass
    try:
        bases.append(Path.cwd())
    except OSError:
        pass
    bases.extend([home_root(), CODE_ROOT, *CODE_ROOT.parents])

    seen: set = set()
    out: List[Path] = []
    for base in bases:
        try:
            key = str(Path(base).resolve())
        except OSError:
            continue
        if key not in seen:
            seen.add(key)
            out.append(Path(base))
    return out


def _probe_mcp_dir(subdirname: str) -> Optional[Path]:
    """在候选父目录下寻找 `omni-media/<subdirname>`；找不到返回 None（**不编造路径**）。"""
    for base in mcp_candidate_bases():
        candidate = base / DEFAULT_MCP_REPO_DIRNAME / subdirname
        try:
            if candidate.is_dir():
                return candidate
        except OSError:
            continue
    return None


def mcp_repo() -> Path:
    """宿主原生听音版（`read_audio`）的目录。

    解析顺序：① `$OMNI_MEDIA_MCP_DIR`（显式覆盖，绝对路径或相对 home 的路径）
    → ② **在候选父目录里实际探查** `<base>/omni-media/mcp`（见 `mcp_candidate_bases()`）
    → ③ `<home>/mcp`（迁移前的旧布局兜底）
    → ④ 都没找到时返回**预期位置**，让调用方的报错指向一个具体路径而不是空值。
    """
    env_dir = _env_path(ENV_MCP_DIR, base=home_root())
    if env_dir is not None:
        return env_dir

    found = _probe_mcp_dir(DEFAULT_MCP_DIRNAME)
    if found is not None:
        return found

    legacy = home_root() / DEFAULT_MCP_DIRNAME
    if legacy.is_dir():
        return legacy
    return home_root() / DEFAULT_MCP_REPO_DIRNAME / DEFAULT_MCP_DIRNAME


def mcp_ext_repo() -> Path:
    """外部模型代读版（`read_media`）的目录。

    布局规则与 `mcp_repo()` 一致，但**不受** `$OMNI_MEDIA_MCP_DIR` 影响：那个变量只针对原生听音版
    （两个服务是各自独立的包，用一个变量同时改两个位置只会造成误配）。
    """
    found = _probe_mcp_dir(DEFAULT_MCP_EXT_DIRNAME)
    if found is not None:
        return found

    legacy = home_root() / DEFAULT_MCP_EXT_DIRNAME
    if legacy.is_dir():
        return legacy
    return home_root() / DEFAULT_MCP_REPO_DIRNAME / DEFAULT_MCP_EXT_DIRNAME


def products_root_for(home: Optional[Path], cwd: Optional[Path] = None) -> Path:
    """按「容器根 + 当前工作目录」算出产物根（纯函数，便于自检直接断言各分支）。

    * **有容器根、且 cwd 就在该容器内**（含容器根自身）→ `<home>/output`；
    * **其余情况**（没有容器根，或从容器外调用，例如把技能软链到
      `~/.agents/skills/` 后在别的项目里干活）→ **`<cwd>/output`**（默认语义）。

    为什么要求「cwd 在容器内」：容器标记是从**代码位置**向上找的，技能被软链/复制进
    平台技能目录后，代码位置仍指向原容器——若只认标记，就会把产物写回原容器，
    而不是用户当前干活的目录。判定跟着**使用者所在的位置**走才符合直觉。
    """
    here = (cwd or Path.cwd()).resolve()
    if home is not None:
        try:
            root = Path(home).resolve()
        except OSError:
            root = None
        if root is not None and (here == root or root in here.parents):
            return root / DEFAULT_PRODUCTS_DIRNAME
    return here / DEFAULT_PRODUCTS_DIRNAME


def products_root() -> Path:
    """产物根（工作区与 .sessdata.json / .wbi_keys.json / .cli_status.json 的所在地）。

    解析顺序：① `$BVB_OUTPUT_DIR`（显式覆盖）
    → ② 容器根存在**且当前工作目录在该容器内**时的 `<home>/output`
    → ③ **否则当前工作目录下的 `output/`**（默认，不需要任何配置）。
    """
    explicit_home = container_home()
    env_output = _env_path(ENV_OUTPUT_DIR, base=explicit_home)
    if env_output is not None:
        return env_output
    return products_root_for(explicit_home)


def default_base_dir() -> str:
    """CLI / 脚本 `--base-dir` 的缺省值（= 产物根的绝对路径）。

    没有容器标记时它跟随**当前工作目录**——这是默认语义，不是缺陷：
    产物要落在你干活的那个目录下。需要钉死位置时用 `$BVB_OUTPUT_DIR` 或 `--base-dir`。
    """
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
    explicit_home = container_home()
    here = Path.cwd().resolve()
    inside = False
    if explicit_home is not None:
        try:
            root = explicit_home.resolve()
            inside = here == root or root in here.parents
        except OSError:
            inside = False
    return {
        "code_root": str(code_root()),
        "home_root": str(home_root()),
        "products_root": str(products_root()),
        "home_env": ENV_HOME,
        "output_env": ENV_OUTPUT_DIR,
        "home_from_env": _env_path(ENV_HOME) is not None,
        # 有显式容器根（标记或环境变量）时为 True
        "container_pinned": explicit_home is not None,
        # 当前工作目录是否就在容器根之内——决定容器布局是否生效
        "cwd_inside_container": inside,
        "products_from_env": _env_path(ENV_OUTPUT_DIR, base=explicit_home) is not None,
        # 产物根跟随工作目录（默认语义）时为 True
        "products_from_cwd": (
            _env_path(ENV_OUTPUT_DIR, base=explicit_home) is None and not inside
        ),
        "mcp_repo": str(mcp_repo()),
        "mcp_ext_repo": str(mcp_ext_repo()),
        "mcp_from_env": _env_path(ENV_MCP_DIR, base=explicit_home) is not None,
    }
