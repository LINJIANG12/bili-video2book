# CLI 场景手册

本手册收录按任务目标划分的完整命令清单。README 只给出最常见的四条示例，其余场景在此展开。

## 运行约定

- **工作目录 = 技能目录**（`SKILL.md` 所在目录，即 `skills/bili-video2book/`）。下文所有 `python src/cli.py …` / `python scripts/…` 均以此为当前目录；
- 若已执行 `pip install -e .`，可直接使用 `bili-video2book` 命令，等价于 `python src/cli.py`；
- 产物一律落在**产物根**（默认 `<容器根>/output/`），与代码目录分离；下文示例中的 `output/<task>/…` 均**相对产物根**；
- 换位置部署：`--base-dir <路径>`，或环境变量 `BVB_HOME`（容器根）/ `BVB_OUTPUT_DIR`（产物根）。

---

## 场景一：处理整门课程流水线

```bash
# 处理整门 B 站网课合集（--article-type 必填，不传即 exit 4）
bili-video2book pipeline "https://www.bilibili.com/video/BV14VqVBrEhc" --all --article-type learning

# 处理本地整套视频课程目录
bili-video2book pipeline "D:\courses\software_engineering\" --all --article-type learning

# 处理 YouTube 单视频或播放列表/频道课程
bili-video2book pipeline "https://www.youtube.com/watch?v=kqtD5dpn9C8" --article-type learning
bili-video2book pipeline "https://www.youtube.com/@freecodecamp" --all --article-type learning

# 处理抖音单视频或博主主页合集
bili-video2book pipeline "https://v.douyin.com/xxxx/" --article-type learning
bili-video2book pipeline "https://www.douyin.com/user/MS4wLjAB..." --all --article-type learning
```

## 场景二：处理指定分集或区间

```bash
# 处理第 1 讲
bili-video2book pipeline "https://www.bilibili.com/video/BV14VqVBrEhc" --page 1 --article-type learning

# 处理第 2 讲至第 5 讲
bili-video2book pipeline "https://www.bilibili.com/video/BV14VqVBrEhc" --range 2-5 --article-type learning
```

## 场景三：生成模块合辑教材

在阶段一单集长文生成完毕后，整编生成模块教材：

```bash
bili-video2book cluster-articles "https://www.bilibili.com/video/BV14VqVBrEhc"
```

模块教材默认复用已有 `textbooks/`；需要按最新章节重编时加 `--force`：

```bash
bili-video2book cluster-articles "https://www.bilibili.com/video/BV14VqVBrEhc" --force
```

## 场景四：生成思维导图复习笔记

```bash
# 复习笔记只有一种风格，无需 --style
# 两趟规划（模块划分 ➔ 归并成笔记）都由 Agent 产出；缺规划不会卡住，命令始终正常退出
bili-video2book cluster-notes "https://www.bilibili.com/video/BV14VqVBrEhc"

# --force：强制重导全部笔记任务书（已产出笔记成品的篇默认自动复用）
bili-video2book cluster-notes "https://www.bilibili.com/video/BV14VqVBrEhc" --force

# --force-plan：强制重出两趟规划任务书（忽略盘上旧规划，重新做模块划分与笔记归并）
bili-video2book cluster-notes "https://www.bilibili.com/video/BV14VqVBrEhc" --force-plan
```

## 场景五：查看与监控任务队列状态

```bash
# 查看当前任务工作区的完成进度与阶段判定
python scripts/queue_tracker.py

# 获取待处理队列中接下来的 5 个分集及路径
python scripts/queue_tracker.py --next 5

# 多课程并存时指定工作区（否则取最近活动的那个）
python scripts/queue_tracker.py --pattern "微机原理" --next 5
```

## 场景六：交付前质检与收尾

```bash
# 笔记成色体检（致命项：套话填充 / 空壳标题 / 分集平铺标题 / 行内残缺引用 / 分集口吻；
#              提示项：断句 / 结构缺件——加 --require-structure 才纳入门禁）
python scripts/note_quality_check.py --strict

# 渲染合规体检（致命项：GitHub 告警块 / 围栏外裸字符画 / 围栏配对；
#              提示项：围栏语言标识——加 --require-lang 才纳入门禁）
python scripts/render_compat_check.py --strict

# 任务书回收：成品产出后才回收，每类保留 1 份范本（先 --dry-run 预演）
python src/cli.py cleanup --dry-run
python src/cli.py cleanup

# 账本对账：以磁盘产物为唯一真相回填 manifest.json
python src/cli.py sync
```

> **任务书是临时派发物**：`*_TASK.md` 在成品产出后由 `cleanup`（或 pipeline 收尾）自动回收，
> 每个类别保留编号最小的 1 份作为提示词范本；`topic_plan_TASK.md` / `note_plan_TASK.md`
> 属课程级规划任务书，永不回收。

---

## 环境与凭证

安装前置、平台对照与缺失处理见 [`install.md`](install.md)；
B 站 `SESSDATA` 凭证的两种配置方式与安全须知见 `SKILL.md` §2；
宿主工具名差异见 [`host-tools/`](host-tools/)。
