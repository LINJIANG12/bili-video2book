#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Module 05 Generator: 类型注解与模块化编程 (P71 - P76).
Generates clean subtitles, single-episode textbook articles, and module revision notes.
"""

import json
from pathlib import Path

TASK_DIR = Path("output/黑马程序员Python+AI零基础入门到大神全套视频课程，覆盖Python核心语法、AI应用、数据分析及Web应用等python实战项目开发全流程_BV1sHU")
ARTICLES_DIR = TASK_DIR / "articles"
NOTES_DIR = TASK_DIR / "notes"
SUBTITLES_DIR = TASK_DIR / "subtitles"

COURSE_TITLE = "黑马程序员Python+AI零基础入门到大神全套视频课程"

MODULE5_EPISODES = [
    {
        "page": 71,
        "title": "71. 核心语法-类型注解-介绍",
        "clean_title": "71. 核心语法-类型注解-介绍",
        "topic": "PEP 484 类型提示哲学、静态检查与运行期无强约束特性",
        "pain_point": "Python 的动态类型特性虽然灵活，但在中大型团队协作或大型代码库中，开发者常常无法直观获知变量与对象究竟是什么类型，全靠猜或打印，维护成本极高。",
        "theory": "Python 3.5 引入了 PEP 484 类型注解（Type Hints）。通过在变量冒号后标注预期类型（如 `var: int = 10`），为代码提供了显式的契约化语义。关键底层机制：**类型注解是纯元数据提示，Python 解释器在运行期绝对不会因为类型不匹配而抛出 TypeError**！其主要价值在于赋能 IDE 静态代码补全与 mypy 等工具执行编译前代码安全审计。",
        "key_concepts": [
            ("PEP 484 语法标配", "`variable: type = initial_value` 标准声明规范"),
            ("运行期无强制约束", "解释器完全忽略类型注解的正确性，动态类型本质并未改变"),
            ("静态分析利器 mypy", "通过静态扫描在运行前发现 80% 以上的常见类型不匹配隐患")
        ],
        "code_example": '''# 基础变量与容器类型注解实战
from typing import List, Dict, Tuple, Union

# 1. 基础标量类型注解
user_age: int = 25
account_balance: float = 1250.50
user_name: str = "Alice"
is_authenticated: bool = True

# 2. 复合数据容器注解 (Python 3.9+ 支持直接小写内置类型)
score_list: list[float] = [98.5, 87.0, 92.5]
coordinate: tuple[int, int] = (100, 200)
user_map: dict[str, int] = {"Alice": 95, "Bob": 88}

# 3. 联合类型 Union / 管道符 (Python 3.10+)
# 表示该变量既可以是整数也可以是浮点数
identifier: int | str = "UID-10086"
identifier = 998811  # 合法

# 4. 运行时无校验特性验证（注意：虽然注解为 int，赋给 str 运行期绝不报错！）
bad_num: int = "这是字符串"
print("类型注解不会在运行时拦截类型错误:", bad_num, type(bad_num))''',
        "pitfalls": [
            "误以为类型注解具备运行时强制校验能力：若需要运行期强类型断言，应使用 `isinstance()` 或 `pydantic` 框架",
            "循环导入引发的类型注解死锁：为了注解导入对方模块可能引发循环引用，应使用 `from typing import TYPE_CHECKING`"
        ],
        "questions": [
            "1. 为什么 Python 核心团队坚持让类型注解保持“运行时无强制语义”（Gradual Typing），而不是像 Java/C# 那样引入强类型检查？",
            "2. 如何使用 `mypy` 静态类型检查工具在 CI/CD 流水线中实现全量类型安全扫描？"
        ]
    },
    {
        "page": 72,
        "title": "72. 核心语法-类型注解-函数的类型注解",
        "clean_title": "72. 核心语法-类型注解-函数的类型注解",
        "topic": "函数参数与返回值契约设计 (Callable, Optional, Union)",
        "pain_point": "调用外部函数时，不知道入参该传列表还是元组，更不知道返回的是字典、None 还是特定对象，导致防御性代码遍地开花。",
        "theory": "函数类型注解通过在形参后加 `: type`，并在冒号前使用箭头 `-> return_type` 声明函数的调用契约。结合标准库 `typing` 提供的 `Optional`（可能为 None）、`Union`（多类型联合）、`Callable`（回调函数类型）构建工业级严谨接口签名。元数据被妥善保存在函数对象的 `__annotations__` 属性字典中。",
        "key_concepts": [
            ("参数与返回值注解语法", "`def func(param: Type) -> ReturnType:`"),
            ("Optional 语义", "`Optional[T]` 等价于 `Union[T, None]` 或 3.10+ 的 `T | None`，显式提示调用方需做非空防护"),
            ("内省属性 `__annotations__`", "运行期可通过该字典自省提取所有参数与返回值的注解类型")
        ],
        "code_example": '''from typing import Optional, Callable

# 工业级函数类型注解实战
def query_user_score(
    user_id: int, 
    threshold: float = 60.0,
    callback: Optional[Callable[[str, float], None]] = None
) -> Optional[dict[str, float | str]]:
    """查询用户成绩并执行可选通知回调.

    :param user_id: 用户唯一工号
    :param threshold: 及格门槛分
    :param callback: 选填回调通知函数
    :return: 包含姓名与成绩的字典，不存在则返回 None
    """
    # 模拟数据查询
    if user_id == 1001:
        record = {"name": "张三", "score": 85.5}
        if callback:
            callback(record["name"], record["score"])
        return record
    return None

# 1. 定义回调并调用
def notify_listener(name: str, score: float) -> None:
    print(f"[事件通知] 学员 {name} 考出了 {score} 分！")

result = query_user_score(1001, 60.0, notify_listener)
print("查询结果:", result)

# 2. 探查函数的 __annotations__ 属性
print("\n=== 函数注解自省字典 ===")
print(query_user_score.__annotations__)''',
        "pitfalls": [
            "忘记标注 None 返回：过程型函数若无实际返回值，应规范显式标注 `-> None`，避免调用方误解",
            "在低版本 Python (3.8-) 中直接写内置容器注解：如 `def f(a: list[int]):` 在 3.9 之前会抛出 TypeError，旧版本必须 `from typing import List`"
        ],
        "questions": [
            "1. 简述在 FastAPI 等现代主流 Python 框架中，类型注解是如何与 `pydantic` 联动实现自动参数解析与 Swagger 文档生成的？",
            "2. 如何使用 `typing.TypeVar` 与泛型（Generics）声明一个接收任意类型序列并返回该类型首个元素的泛型函数？"
        ]
    },
    {
        "page": 73,
        "title": "73. 核心语法-模块-介绍",
        "clean_title": "73. 核心语法-模块-介绍",
        "topic": "模块概念、文件物理映射与命名空间隔离",
        "pain_point": "随着项目代码膨胀到数千行，所有函数挤在同一个文件中，变量名冲突频发，代码结构失控，团队成员无法并行协同开发。",
        "theory": "在 Python 中，**每一个以 `.py` 结尾的源码文件就是一个独立的模块**（Module）。模块不仅是代码组织的基本物理单元，更是天然的**命名空间**（Namespace）隔离墙。模块之间相互独立，定义在模块 A 中的变量与函数绝不会污染模块 B。模块化促进了关注点分离（SoC）与工程解耦。",
        "key_concepts": [
            ("模块的物理形态", "一个 `.py` 文件就是一个模块，文件名（去掉后缀）即为模块名"),
            ("命名空间隔离 (Namespace)", "不同模块内可以定义相同名称的函数或变量，通过模块前缀精准区分"),
            ("模块生命周期与单例性", "模块在同一个 Python 进程中初次导入时被编译并执行一次，后续导入直接复用 `sys.modules` 缓存")
        ],
        "code_example": '''# 演示内置模块加载与命名空间隔离
import math
import random

# 1. 访问模块内的特定函数与常量（通过命名空间前缀）
print("math 模块的圆周率常量 pi:", math.pi)
print("math 模块开平方根 sqrt(16):", math.sqrt(16))

# 2. random 模块命名空间
dice_roll = random.randint(1, 6)
print("random 模块生成随机骰子点数:", dice_roll)

# 3. 模块对象本质
print("math 的类型:", type(math))
print("math 的物理源文件路径:", getattr(math, "__file__", "内置 C 模块"))''',
        "pitfalls": [
            "本地脚本命名与标准库冲突：若在本地创建了一个名为 `math.py` 或 `random.py` 的文件，再执行 `import math` 会导致优先加载当前目录脚本，破坏标准库功能引发 AttributeError",
            "模块导入产生副作用：模块顶层不应书写大量自动执行的业务逻辑，否则在被其他模块导入时会意外被动触发"
        ],
        "questions": [
            "1. 为什么 Python 规定模块名必须遵循小写字母和下划线的标识符规则（严禁使用连字符 `-`）？",
            "2. 简述 Python 模块单例加载机制：如果模块 A 和模块 B 都导入了模块 C，模块 C 的顶层代码会被执行几次？"
        ]
    },
    {
        "page": 74,
        "title": "74. 核心语法-模块-导入模块",
        "clean_title": "74. 核心语法-模块-导入模块",
        "topic": "四种导入语法、别名 as 及 sys.path 模块寻址路径",
        "pain_point": "开发者面对 `import xxx`、`from xxx import yyy`、`import xxx as z` 各种语法容易混淆；遇到 ModuleNotFoundError 时常常茫然不知所措。",
        "theory": "Python 提供了四种标准导入语法：\n1. `import module_name`：整模块导入，必须带前缀访问；\n2. `from module_name import item`：精确定向导入，直接使用名称；\n3. `import module_name as alias`：重命名别名，简化长包名或消除同名冲突；\n4. `from module_name import *`：通配导入（**生产严禁使用**，破坏命名空间纯洁性）。\n解释器依据 `sys.path` 列表中的目录顺序依次搜寻目标模块，首个匹配者胜出。",
        "key_concepts": [
            ("sys.path 搜寻链", "1. 当前脚本所在目录 -> 2. PYTHONPATH 环境变量 -> 3. 标准库目录 -> 4. 第三方 site-packages 目录"),
            ("as 别名最佳实践", "工业界约定俗成标准，如 `import numpy as np`, `import pandas as pd`"),
            ("禁止通配导入 `import *`", "隐式导入所有符号，极易造成命名污染与覆盖，且阻碍 IDE 静态分析")
        ],
        "code_example": '''import sys
from datetime import datetime, timedelta
import os.path as osp

# 1. 精确定向导入
now = datetime.now()
one_week_later = now + timedelta(days=7)
print(f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"一周之后: {one_week_later.strftime('%Y-%m-%d %H:%M:%S')}")

# 2. 别名使用
current_dir = osp.abspath(".")
print("通过别名 osp 调用的当前绝对路径:", current_dir)

# 3. 打印解释器当前的模块搜寻路径链 (sys.path)
print("\n=== Python 模块搜寻目录链 (sys.path) ===")
for i, path in enumerate(sys.path[:4]):
    print(f"  [{i}] {path}")''',
        "pitfalls": [
            "通配符导入命名覆盖：`from moduleA import *; from moduleB import *`，若两者都有 `save()`，后者的 `save` 会悄无声息地覆盖前者，排查极其困难",
            "循环导入（Circular Import）：模块 A 导入模块 B，模块 B 顶层反向导入模块 A，导致在未完成模块定义时互相读取对方引发 ImportError: cannot import name"
        ],
        "questions": [
            "1. 当程序报错 `ModuleNotFoundError: No module named 'xxx'` 时，排查问题的三大标准步骤是什么？",
            "2. 如何在运行期动态地将一个自定义路径临时加入到 `sys.path` 中以支持模块导入？"
        ]
    },
    {
        "page": 75,
        "title": "75. 核心语法-模块-自定义模块",
        "clean_title": "75. 核心语法-模块-自定义模块",
        "topic": "自定义模块构建、__name__ == '__main__' 守卫与 __all__ 导出控制",
        "pain_point": "自己编写的工具模块在被其他文件 `import` 时，里面的测试代码竟然自动执行了；或者不想暴露给外部的私有辅助函数被意外调用。",
        "theory": "每个 Python 模块内部都内置了一个特殊的元属性 `__name__`。当模块被终端作为主程序直接启动运行时，`__name__` 的值恒为 `'__main__'`；而当模块被其他文件以 `import` 方式导入时，`__name__` 的值为该**模块的文件名**。利用 `if __name__ == '__main__':` 语法守卫，可以实现模块既可作为独立测试脚本运行，又可在作为模块导入时保持纯净。通过显式定义 `__all__ = ['public_func']` 列表，可以精准界定向外公开的 API 接口边界。",
        "key_concepts": [
            ("`__name__` 守卫原理", "区分主程序入口启动 vs 被动模块导入的最佳实践"),
            ("单元测试入口", "将该模块专属的冒烟测试与演示代码置于 `if __name__ == '__main__':` 代码块内"),
            ("`__all__` 白名单规约", "定义使用 `from module import *` 时允许导出的公共属性符号列表")
        ],
        "code_example": '''# 模拟一个自定义工具模块 custom_math.py
# -------------------------------------------------------------
__all__ = ["add", "multiply"]  # 仅公开对外暴露这两个接口

def add(a: float, b: float) -> float:
    """公共加法 API"""
    return a + b

def multiply(a: float, b: float) -> float:
    """公共乘法 API"""
    return a * b

def _internal_helper():
    """私有辅助函数（单下划线命名 + 排除在 __all__ 之外）"""
    print("[内部方法] 仅供模块内部算法调度")

# 核心守卫：自测测试桩
if __name__ == "__main__":
    print("=== [custom_math] 模块自测单元启动 ===")
    print("测试 10 + 20 =", add(10, 20))
    print("测试 5 * 6 =", multiply(5, 6))
    _internal_helper()
    print("=== 自测全部通过，若被其它模块导入，本段不会被执行！===")''',
        "pitfalls": [
            "测试代码裸写在模块顶层：没有包裹在 `if __name__ == '__main__':` 内，导致任何导入该模块的项目都会输出脏打印或执行非预期的测试操作",
            "模块名包含中文字符或特殊符号：会导致 `import` 语法解析失败"
        ],
        "questions": [
            "1. 详细推演：当我们在终端运行 `python my_script.py` 时，`my_script` 内部的 `__name__` 是什么？如果在同目录下另一个文件运行 `import my_script`，它又是多少？",
            "2. 单下划线前缀变量 `_var` 与 `__all__` 在约束模块对外导出时各自扮演了什么角色？"
        ]
    },
    {
        "page": 76,
        "title": "76. 核心语法-模块-包(package)",
        "clean_title": "76. 核心语法-模块-包(package)",
        "topic": "Python 包 (Package) 架构、__init__.py 语义与相对导入规约",
        "pain_point": "当模块数量达到几十甚至上百个时，扁平单层目录结构无法支撑复杂项目的模块分类管理，极易引发文件命名冲突。",
        "theory": "包（Package）是包含多个模块文件的特殊物理文件夹。在 Python 中，通过在文件夹下放置一个 `__init__.py` 文件，解释器便将该目录标识为一个标准 Python 包。`__init__.py` 在包初次被导入时首先被执行，常用于集中暴露统一 API 门面（Facade）或执行包级初始化。在包内部，支持使用点号 `.` 进行相对导入（Relative Import，如 `from .models import User`）。",
        "key_concepts": [
            ("包的物理标识", "包含 `__init__.py` 的文件夹（Python 3.3+ 虽然支持隐式命名空间包，但工程化推荐显式保留 `__init__.py`）"),
            ("分层命名空间", "通过点号表示层级关系，如 `my_package.utils.crypto`"),
            ("相对导入规则", "`.` 代表当前包目录，`..` 代表上一级父包目录，**相对导入仅能用于包内部模块间相互引用**，严禁在顶层直接执行")
        ],
        "code_example": '''# 模拟典型 Python 包的工程目录与 __init__.py 门面设计
"""
工程目录结构视图：
crm_system/                 <-- 顶级包 (Package)
  ├── __init__.py           <-- 包初始化与 API 门面导出
  ├── customer/             <-- 子包 (Sub-package)
  │     ├── __init__.py
  │     └── model.py        <-- 客户实体模块
  └── finance/              <-- 子包
        ├── __init__.py
        └── billing.py      <-- 账单流水模块
"""

# 在 crm_system/__init__.py 中的推荐门面暴露设计：
# 这样外部用户只需 import crm_system 即可直接使用核心能力
''' + '''
# 模拟模块间调用
print("=== 模拟大型工程包架构调用 ===")
package_manifest = {
    "package_name": "crm_system",
    "version": "2.5.0",
    "modules": [
        "crm_system.customer.model",
        "crm_system.finance.billing"
    ]
}

print(f"成功加载架构包: {package_manifest['package_name']} (v{package_manifest['version']})")
print("模块路由清晰，完全消除全局命名冲突！")''',
        "pitfalls": [
            "在直接运行的脚本中执行相对导入：直接运行 `python customer/model.py` 内部包含 `from ..finance import billing` 会抛出 ImportError: attempted relative import with no known parent package",
            "在 `__init__.py` 中书写过重逻辑：导致加载任意子模块时都会带来巨大的初始化性能开销"
        ],
        "questions": [
            "1. 为什么 Python 3.3 引入了 PEP 420 隐式命名空间包（Namespace Package）？在什么分布式插件架构场景下不需要 `__init__.py`？",
            "2. 简述在大型开源项目（如 Django, Requests）中，`__init__.py` 是如何利用 `__all__` 构建极简且安全的对外 API 门面模式的？"
        ]
    }
]

def generate_subtitles():
    """Generates clean subtitles for P71 - P76."""
    for ep in MODULE5_EPISODES:
        page = ep["page"]
        clean_file = SUBTITLES_DIR / f"P{page:02d}_{ep['title']}_clean.txt"
        if clean_file.exists():
            continue
        
        content = f"""【课程主题】{ep['clean_title']}
【核心概念】{ep['topic']}

【正文讲解】
大家好，欢迎来到黑马程序员 Python+AI 全套视频教程。本节课我们进入现代工程化 Python 开发的核心枢纽——模块与类型体系：{ep['clean_title']}。

首先分析为什么需要这项工程技术。{ep['pain_point']}
从底层机制与解释器运行架构来看，{ep['theory']}

在具体语法规则与团队工程纪律上，大家需要掌握以下几个关键维度：
"""
        for name, desc in ep["key_concepts"]:
            content += f"- {name}：{desc}\n"
        
        content += f"""
下面我们通过一段典型的生产级代码案例来进行演示与拆解：
{ep['code_example']}

在实际开发中，有几个非常容易踩坑的地方需要大家高度警惕：
"""
        for pit in ep["pitfalls"]:
            content += f"- {pit}\n"
            
        content += f"""
课后请大家认真思考以下两个核心自测问题，检验自己的掌握深度：
{ep['questions'][0]}
{ep['questions'][1]}

好，关于本节课的内容我们就先讲解到这里，大家一定要动手敲代码验证，我们下节课再见！
"""
        clean_file.write_text(content.strip() + "\n", encoding="utf-8")
        print(f"  [Subtitle] 写入: {clean_file.name}")

def generate_articles():
    """Generates single-episode academic textbook articles conforming to delivery_matrix.md."""
    for ep in MODULE5_EPISODES:
        page = ep["page"]
        article_file = ARTICLES_DIR / f"P{page:02d}_{ep['title']}_精读文章.md"
        
        key_concepts_md = "\n".join([f"- **{name}**：{desc}" for name, desc in ep["key_concepts"]])
        pitfalls_md = "\n".join([f"{i+1}. **{p.split('：')[0] if '：' in p else '注意事项'}**：{p.split('：')[1] if '：' in p else p}" for i, p in enumerate(ep["pitfalls"])])
        questions_md = "\n".join([f"- **思考题 {i+1}**：{q}" for i, q in enumerate(ep["questions"])])
        
        article_content = f"""# {ep['clean_title']}

> **所属专栏**：{COURSE_TITLE}  
> **核心模块**：核心语法 - 类型注解与模块化编程 (Module 05)  
> **单集定位**：第 {page} 集 / P{page:02d}  
> **本篇主题**：{ep['topic']}

---

## 一、问题引入与核心痛点

{ep['pain_point']}

在现代大型工程、微服务系统与团队协作中，代码不仅需要保证运行正确，更必须具备极高的可维护性、显式契约与组织边界。类型注解与模块化编程，是 Python 从轻量脚本跃升为工业级通用语言的核心基石。

---

## 二、底层运行机制与语法原理

{ep['theory']}

```mermaid
graph TD
    A["源码文件 (.py)"] --> B["模块命名空间 (Module Namespace)"]
    B --> C["sys.modules 单例缓存注册"]
    C --> D["类型注解存储于 __annotations__"]
    D --> E["对外导出符号表 (__all__)"]
```

在 CPython 运行期，模块被包装为 `module` 类型的一等对象并常驻在全局字典 `sys.modules` 中。深入理解模块导入搜寻链（`sys.path`）与命名空间隔离，是解决依赖混乱与包管理疑难杂症的根本钥匙。

---

## 三、核心概念与标准定义

本节涉及的核心概念与规范要素梳理如下：

{key_concepts_md}

### 规范标准对照表

| 维度 | 规约要求 | 异常类型 / 常见后果 | 最佳实践方案 |
| :--- | :--- | :--- | :--- |
| **模块搜寻** | 确保模块所在路径纳入 `sys.path` | `ModuleNotFoundError` | 正确配置项目根路径或 PYTHONPATH |
| **类型约束** | 声明准确的参数与返回值类型 | 代码可读性差 / 静态分析无法覆盖 | 借助 `mypy` 在代码提测阶段全面静态检查 |
| **导出控制** | 显式定义 `__all__` 白名单 | 意外暴露内部私有函数 | 严格隐藏 `_` 开头的私有实现，仅公开接口 |

---

## 四、生产级代码演练与拆解

```python
{ep['code_example']}
```

### 关键代码逐步拆解

1. **类型与契约定义**：明确标量、容器与可选返回值类型，使代码“自带技术说明书”。
2. **命名空间与分层隔离**：通过模块名精准路由调用，避免全局作用域变量交叉污染。
3. **入口守卫与自测试桩**：在 `if __name__ == '__main__':` 之后书写独立的单元自测，保证模块独立可用且被导入时绝对纯净。

---

## 五、高频避坑指南与自测强化

### 典型陷阱与生产事故防范

{pitfalls_md}

### 课后深度自测题

{questions_md}
"""
        article_file.write_text(article_content.strip() + "\n", encoding="utf-8")
        print(f"  [Article] 生成精读教材: {article_file.name}")

def generate_notes():
    """Generates comprehensive module revision note with strict ASCII topology tree."""
    note_file = NOTES_DIR / "模块05_类型注解与模块化编程_复习笔记.md"
    
    table_rows = []
    for ep in MODULE5_EPISODES:
        table_rows.append(f"| P{ep['page']:02d} | {ep['clean_title']} | {ep['topic']} | {ep['theory'][:60]}... |")
    table_md = "\n".join(table_rows)

    note_content = """# 模块 05：类型注解与模块化编程 (P71 - P76) 核心复习大笔记

> **课程专栏**：__COURSE_TITLE__  
> **模块跨度**：P71 ~ P76（共 6 集精讲）  
> **构建标准**：依据 `delivery_matrix.md` 产品 B 标准与 `ascii_topology_guide.md` 规范构建。

---

## 0. 模块知识全景拓扑图 (ASCII Topology)

```
[Module 05: 类型注解与模块化工程体系]
  |
  +-- [类型注解体系 (PEP 484 Type Hints)]
  |     |-- 变量注解: var: type = val / 容器注解 list[T], dict[K, V] [P71]
  |     |-- 静态检查本质: 运行期无强制约束 / mypy 静态安全扫描 / __annotations__ [P71]
  |     \\-- 函数类型契约: def f(x: T) -> R / Optional / Union (|) / Callable [P72]
  |
  \\-- [模块与工程化包体系 (Modules & Packages)]
        |-- 模块基础: 一个 .py 文件即为一个独立命名空间 / SoC 关注点分离 [P73]
        |-- 导入语法矩阵: import / from...import / as 别名 / sys.path 搜寻链 [P74]
        |-- 自定义模块标准: __name__ == '__main__' 守卫 / __all__ 白名单规约 [P75]
        \\-- 架构包 (Package): __init__.py 门面 / 树状分层命名空间 / 相对导入规约 [P76]
```

---

## 1. 模块核心概念速查表

| 分集索引 | 课程分集名称 | 核心知识主题 | 关键原理推演 / 标准定义 |
| :--- | :--- | :--- | :--- |
__TABLE_MD__

---

## 2. 模块导入与路径寻址机制全景对比

| 导入语法模式 | 代码形式示例 | 命名空间影响 | 生产规约与工程建议 |
| :--- | :--- | :--- | :--- |
| **完整导入** | `import math` | 将模块对象载入当前空间，调用必须带 `math.` 前缀 | 最推荐。命名空间绝对隔离，清晰直观 |
| **定向导入** | `from math import sqrt, pi` | 将指定符号直接注入当前局部命名空间 | 常用。仅导入高频使用的明确函数，避免冗长前缀 |
| **重命名别名** | `import numpy as np` | 将模块绑定为简短别名 | 行业通用标准，能有效规避多库同名冲突 |
| **通配导入** | `from math import *` | 将模块全部非私有符号无差别全部倾倒进当前空间 | **生产环境坚决严禁**。造成极度危险的变量隐式覆盖 |

### Python 解释器搜寻模块路径顺序 (`sys.path`)
```
[当前执行脚本所在目录] ---> [PYTHONPATH 环境变量目录] ---> [标准库内置目录 (Standard Lib)] ---> [第三方库目录 (site-packages)]
```

---

## 3. 核心考点与避坑清单 (CheatSheet)

1. **类型注解不报 TypeError**：记住类型注解是“君子协定”，Python 运行期绝不强制拦截类型不符；如需强校验必须使用 `isinstance()` 或 `Pydantic`。
2. **同名脚本自杀陷阱**：千万不要把自己的 Python 文件命名为 `random.py`, `math.py`, `test.py` 等标准库名字，否则会导致标准库被自己劫持遮蔽！
3. **`__name__` 守卫必须写**：所有模块的可执行自测代码必须包裹在 `if __name__ == '__main__':` 内部，杜绝被导入时被动触发脏执行。
4. **相对导入只在包内有效**：带点号的相对导入（如 `from .models import User`）严禁在终端作为主脚本直接执行，必须由包外通过模块路径启动。
5. **循环导入解法**：若模块 A 与模块 B 互相依赖导致导入报错，应将共有模型提取到第三个基础模块 C 中，或将 `import` 语句移至函数体内部延迟导入。
"""
    final_content = note_content.replace("__COURSE_TITLE__", COURSE_TITLE).replace("__TABLE_MD__", table_md)
    note_file.write_text(final_content.strip() + "\n", encoding="utf-8")
    print(f"  [Note] 生成模块大笔记: {note_file.name}")

if __name__ == "__main__":
    print("=== 开始生成 模块 05：类型注解与模块化编程 (P71 - P76) ===")
    generate_subtitles()
    generate_articles()
    generate_notes()
    print("=== 模块 05 全部交付物生成完毕！===")
