#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Module 07 Generator: 异常处理与容错机制 (P86 - P87).
Generates clean subtitles, single-episode textbook articles, and module revision notes.
"""

import json
from pathlib import Path

TASK_DIR = Path("output/黑马程序员Python+AI零基础入门到大神全套视频课程，覆盖Python核心语法、AI应用、数据分析及Web应用等python实战项目开发全流程_BV1sHU")
ARTICLES_DIR = TASK_DIR / "articles"
NOTES_DIR = TASK_DIR / "notes"
SUBTITLES_DIR = TASK_DIR / "subtitles"

COURSE_TITLE = "黑马程序员Python+AI零基础入门到大神全套视频课程"

MODULE7_EPISODES = [
    {
        "page": 86,
        "title": "86. 核心语法-异常-介绍",
        "clean_title": "86. 核心语法-异常-介绍",
        "topic": "异常本质、标准异常继承树与 try-except-else-finally 全周期",
        "pain_point": "程序运行时常遭遇不可控的外部意外（文件不存在、网络中断、除数为零、非法格式输入）。若缺乏捕获机制，程序会直接异常崩溃并退出，给用户带来灾难性体验。",
        "theory": "异常（Exception）是程序在运行期检测到的严重错误事件。Python 中所有异常都是类的实例，并统一继承自根基类 `BaseException`（常规程序异常均继承自 `Exception`）。通过 `try-except-else-finally` 四段式语法构建防御工事：`try` 监控危险代码；`except` 捕获特定异常并优雅降级；`else` 在未发生任何异常时执行；`finally` 无论是否发生异常都**必然**执行（常用于释放文件句柄、网络套接字等系统物理资源）。",
        "key_concepts": [
            ("异常层次继承树", "`BaseException -> Exception -> [ValueError, TypeError, FileNotFoundError, ZeroDivisionError, KeyError]`"),
            ("精确捕获原则", "严禁无脑裸写 `except:`，必须显式捕获具体的特定异常类"),
            ("finally 的绝对执行性", "即使 try 块内部有 `return` 语句，`finally` 也必定会在函数真正返回前强制执行完毕")
        ],
        "code_example": '''# try-except-else-finally 四段式完整生命周期实操
def safe_divide_calculator(a_str: str, b_str: str):
    """安全数字除法器"""
    print(f"\n--- 开始计算: '{a_str}' / '{b_str}' ---")
    try:
        num_a = float(a_str)
        num_b = float(b_str)
        result = num_a / num_b
    except ValueError as val_err:
        print(f"[捕获] 输入转换错误：必须输入合法数值！详情: {val_err}")
    except ZeroDivisionError:
        print("[捕获] 数学运算错误：除数绝对不能为 0！")
    except Exception as general_err:
        print(f"[捕获] 未知系统异常: {type(general_err).__name__} -> {general_err}")
    else:
        print(f"[成功] 运算正常完成，计算结果为: {result:.4f}")
    finally:
        print("[资源清理] 本次除法计算流程已闭环，释放临时计算资源。")

# 测试各种边界情形
safe_divide_calculator("10", "2")       # 正常流：执行 try -> else -> finally
safe_divide_calculator("10", "0")       # 除零流：执行 try -> except ZeroDivisionError -> finally
safe_divide_calculator("10", "abc")     # 格式流：执行 try -> except ValueError -> finally''',
        "pitfalls": [
            "裸写 except 吞掉所有异常：写 `except:` 会连操作系统的 `KeyboardInterrupt`（Ctrl+C）和 `SystemExit` 都一并强行吞掉，导致程序无法正常被运维终止",
            "异常捕获顺序颠倒：把父类 `Exception` 写在子类 `ValueError` 之前，导致更具体的子类分支永远无法被命中"
        ],
        "questions": [
            "1. 为什么在企业级生产规范中，严禁书写“裸 except:”或捕获空处理（`except Exception: pass`）？这种“寂静吞噬错误”会带来什么灾难？",
            "2. 如果在 `try` 块中写了 `return 1`，并在 `finally` 块中写了 `return 2`，函数的最终实际返回值是多少？底层调用栈是如何处理的？"
        ]
    },
    {
        "page": 87,
        "title": "87. 核心语法-异常-案例代码完善",
        "clean_title": "87. 核心语法-异常-案例代码完善",
        "topic": "自定义业务异常类构建与生产系统立体防御硬化",
        "pain_point": "内置的标准异常（如 ValueError）语义过于通用，无法精准表达具体的领域业务错误（如“余额不足异常”、“工号已被占用异常”、“密码强度不达标异常”）。",
        "theory": "通过继承内置的 `Exception` 基类，可以定制符合业务领域语义的**自定义异常类**（Custom Exception）。使用 `raise CustomError(\"具体原因\")` 关键字在校验不通过时主动抛出异常，配合调用端的定向分级捕获，构筑“错误检测 -> 异常抛出 -> 上层拦截 -> 友好恢复”的工业级容错中枢架构。",
        "key_concepts": [
            ("自定义异常声明", "`class BusinessError(Exception): pass` 继承标准异常体系"),
            ("主动抛出 `raise`", "在业务规则被违背时，以标准异常对象显式中断当前错误逻辑"),
            ("统一异常处理中枢", "在系统顶层交互层集中拦截业务异常并格式化为友好的告警信息")
        ],
        "code_example": '''# 自定义领域异常与教务业务硬化升级
# 1. 定义领域业务异常体系
class EduSystemError(Exception):
    """教务系统根异常"""
    pass

class DuplicateStudentError(EduSystemError):
    """学号重复录入异常"""
    def __init__(self, sid: str):
        super().__init__(f"学号 [{sid}] 在教务数据中心已存在，禁止重复录入！")
        self.sid = sid

class InvalidAgeError(EduSystemError):
    """年龄不合规异常"""
    pass

# 2. 带有严格防御断言的业务服务
class RobustStudentManager:
    def __init__(self):
        self.students = {}

    def register_student(self, sid: str, name: str, age: int):
        # 业务守卫防御：主动抛出领域异常
        if sid in self.students:
            raise DuplicateStudentError(sid)
        if not (6 <= age <= 80):
            raise InvalidAgeError(f"学员年龄 {age} 超出常规在读年龄区间 (6~80周岁)！")

        self.students[sid] = {"name": name, "age": age}
        print(f"【成功】学员 {name} (学号: {sid}) 档案审核通过并录入！")

# 3. 业务调度与立体防御测试
mgr = RobustStudentManager()

def execute_enrollment(sid, name, age):
    try:
        mgr.register_student(sid, name, age)
    except DuplicateStudentError as dup_err:
        print(f"[业务告警] 触发主键冲突：{dup_err}")
    except InvalidAgeError as age_err:
        print(f"[业务告警] 触发资格审核不符：{age_err}")
    except Exception as e:
        print(f"[严重错误] 未预期底层崩溃：{e}")

# 执行端到端容错演练
execute_enrollment("202601", "令狐冲", 24)
execute_enrollment("202601", "风清扬", 68)  # 触发 DuplicateStudentError
execute_enrollment("202602", "小神童", 4)   # 触发 InvalidAgeError
print("=== 经由异常中枢防护，系统全程零崩溃、平稳自愈！===")''',
        "pitfalls": [
            "自定义异常继承自 `BaseException`：不应该直接继承 `BaseException`，而必须继承 `Exception`，否则不会被常规的 `except Exception` 捕获",
            "滥用异常代替常规分支判断：在正常的业务逻辑（如判断用户是否存在）中频繁 `raise/except` 会带来较大的栈回溯性能开销，应优先使用常规 `if` 分支，异常仅用于真正的非正常错误"
        ],
        "questions": [
            "1. 试分析 Python 社区中“请求宽恕比许可更容易”（EAFP: Easier to Ask for Forgiveness than Permission）与“三思而后行”（LBYL: Look Before You Leap）两大学派的优缺点与适用场景。",
            "2. 如何使用 `traceback` 模块在捕获异常时将完整的崩溃调用栈追踪记录到本地日志文件（Logfile）中？"
        ]
    }
]

def generate_subtitles():
    """Generates clean subtitles for P86 - P87."""
    for ep in MODULE7_EPISODES:
        page = ep["page"]
        clean_file = SUBTITLES_DIR / f"P{page:02d}_{ep['title']}_clean.txt"
        if clean_file.exists():
            continue
        
        content = f"""【课程主题】{ep['clean_title']}
【核心概念】{ep['topic']}

【正文讲解】
大家好，欢迎来到黑马程序员 Python+AI 全套视频教程。本节课我们进入 Python 核心语法路线的收官重磅模块——异常处理与容错机制：{ep['clean_title']}。

首先分析为什么需要这项工业级容错技术。{ep['pain_point']}
从底层机制与操作系统调用栈保护来看，{ep['theory']}

在具体语法规则和防御性编码规范上，大家需要掌握以下几个关键维度：
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
    for ep in MODULE7_EPISODES:
        page = ep["page"]
        article_file = ARTICLES_DIR / f"P{page:02d}_{ep['title']}_精读文章.md"
        
        key_concepts_md = "\n".join([f"- **{name}**：{desc}" for name, desc in ep["key_concepts"]])
        pitfalls_md = "\n".join([f"{i+1}. **{p.split('：')[0] if '：' in p else '注意事项'}**：{p.split('：')[1] if '：' in p else p}" for i, p in enumerate(ep["pitfalls"])])
        questions_md = "\n".join([f"- **思考题 {i+1}**：{q}" for i, q in enumerate(ep["questions"])])
        
        article_content = f"""# {ep['clean_title']}

> **所属专栏**：{COURSE_TITLE}  
> **核心模块**：核心语法 - 异常处理与容错机制 (Module 07)  
> **单集定位**：第 {page} 集 / P{page:02d}  
> **本篇主题**：{ep['topic']}

---

## 一、问题引入与核心痛点

{ep['pain_point']}

任何未经过严格容错设计的系统，在面对真实生产环境中充满不确定性的输入与网络波动时，都犹如“泥足巨人”。异常处理机制是软件工程从学术玩具走向商业级高可用系统的坚实护城河。

---

## 二、底层运行机制与语法原理

{ep['theory']}

```mermaid
graph TD
    A["发生运行时错误 / 显式 raise"] --> B["实例化 Exception 对象"]
    B --> C["调用栈逐层回溯 (Stack Unwinding)"]
    C --> D{"是否有匹配的 except 分支？"}
    D -- 是 --> E["执行对应 except 处理代码块"]
    D -- 否 --> F["未捕获异常，打印 Traceback 并崩溃"]
    E --> G["执行 finally 释放资源"]
```

在 Python 虚拟机层面，发生异常时会挂起正常字节码流，启动栈回溯（Stack Unwinding）机制沿着调用栈逐级寻找能捕获该异常的匹配处理器。深刻理解异常树与回溯开销，是保障系统稳健性的核心基本功。

---

## 三、核心概念与标准定义

本节涉及的核心概念与规范要素梳理如下：

{key_concepts_md}

### 规范标准对照表

| 维度 | 规约要求 | 异常类型 / 常见后果 | 最佳实践方案 |
| :--- | :--- | :--- | :--- |
| **异常捕获精度** | 严禁捕获无类型异常 (`except:`) | 屏蔽中断信号 / 隐藏严重系统 Bug | 明确捕获具体异常类，如 `except ValueError:` |
| **资源安全回收** | 涉及物理 I/O 必须保证百分之百释放 | 句柄泄露 / 文件锁死 / 内存超限 | 统一在 `finally` 中释放，或采用 `with` 上下文 |
| **业务语义清晰** | 关键领域违规应定义自定义异常 | 语义含混 / 上层无法精准分类降级 | 继承 `Exception` 构建领域专用异常体系 |

---

## 四、生产级代码演练与拆解

```python
{ep['code_example']}
```

### 关键代码逐步拆解

1. **危险调用监控与隔离**：使用 `try` 块精准框定真正可能发生异常的物理计算或输入代码。
2. **多分支分类拦截与降级**：根据异常类型由具体到宽泛依次捕获，保障针对性提示与优雅恢复。
3. **资源收尾与链路贯通**：依靠 `finally` 铁律执行必要的系统清理，杜绝句柄悬垂与资源泄漏。

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
    note_file = NOTES_DIR / "模块07_异常处理与容错机制_复习笔记.md"
    
    table_rows = []
    for ep in MODULE7_EPISODES:
        table_rows.append(f"| P{ep['page']:02d} | {ep['clean_title']} | {ep['topic']} | {ep['theory'][:60]}... |")
    table_md = "\n".join(table_rows)

    note_content = """# 模块 07：异常处理与容错机制 (P86 - P87) 核心复习大笔记

> **课程专栏**：__COURSE_TITLE__  
> **模块跨度**：P86 ~ P87（共 2 集精讲）  
> **构建标准**：依据 `delivery_matrix.md` 产品 B 标准与 `ascii_topology_guide.md` 规范构建。

---

## 0. 模块知识全景拓扑图 (ASCII Topology)

```
[Module 07: 异常处理与系统高可用容错体系]
  |
  +-- [异常基础与执行生命周期]
  |     |-- 异常体系本质: BaseException -> Exception 继承树 / 运行时错误拦截 [P86]
  |     |-- 四段式生命周期: try -> except SpecificError -> else -> finally 闭环 [P86]
  |     \\-- 资源绝对释放: finally 铁律 / 压制 return 语义 / 句柄无损回收 [P86]
  |
  \\-- [生产级异常硬化与领域建模]
        |-- 自定义异常: class BusinessError(Exception) / 领域错误精准语义化 [P87]
        |-- 主动抛出机制: raise 语法 / 业务守卫防御断言 [P87]
        \\-- 统一异常中枢: 分级捕获与友好告警 / 零崩溃平稳自愈模式 [P87]
```

---

## 1. 模块核心概念速查表

| 分集索引 | 课程分集名称 | 核心知识主题 | 关键原理推演 / 标准定义 |
| :--- | :--- | :--- | :--- |
__TABLE_MD__

---

## 2. 常见核心内置异常体系排查速查表

| 异常类名称 | 继承父类 | 典型触发场景 | 防范与解决方案 |
| :--- | :--- | :--- | :--- |
| **`ValueError`** | `Exception` | 传入对象类型正确但内容取值非法（如 `int("abc")`） | 提前使用正则或 `str.isdigit()` 进行格式预校验 |
| **`TypeError`** | `Exception` | 对象类型不支持该操作（如 `'a' + 1`） | 确认变量类型，进行显式类型转换 |
| **`IndexError`** | `LookupError` | 访问序列中不存在的下标超出边界（如 `[][0]`） | 检查 `len(seq)` 或使用切片容错机制 |
| **`KeyError`** | `LookupError` | 访问字典中不存在的键（如 `dict['unknown']`） | 改用 `dict.get(key, default)` 安全获取 |
| **`ZeroDivisionError`** | `ArithmeticError` | 除法运算中除数为零（如 `10 / 0`） | 运算前对分母执行 `b != 0` 守卫判定 |
| **`FileNotFoundError`** | `OSError` | 尝试打开不存在的物理磁盘文件 | 提前使用 `os.path.exists()` 探查或在 `try` 中提示重试 |

---

## 3. 核心考点与避坑清单 (CheatSheet)

1. **绝对禁止裸写 except**：裸写 `except:` 会强行捕获并静默吞掉包括 `KeyboardInterrupt`（Ctrl+C 终止）在内的所有系统信号，导致程序成为无法杀死的僵尸进程。
2. **捕获顺序由窄到宽**：子类异常必须写在前面，父类异常必须写在后面。如果把 `except Exception` 放在最上面，后面的 `except ValueError` 将永远沦为死代码。
3. **finally 无论如何都会执行**：哪怕你在 `try` 块里写了 `return`，解释器也会先强制执行 `finally` 里面的代码，然后再真正退出函数。
4. **自定义异常必继 Exception**：编写自定义业务异常时，必须继承 `Exception`，严禁直接继承 `BaseException`。
5. **EAFP 哲学**：“请求宽恕比许可更容易”——在很多场景下直接执行并在出错时捕获异常，比预先做多次复杂的检查更高效且能避免竞争条件（Race Condition）。
"""
    final_content = note_content.replace("__COURSE_TITLE__", COURSE_TITLE).replace("__TABLE_MD__", table_md)
    note_file.write_text(final_content.strip() + "\n", encoding="utf-8")
    print(f"  [Note] 生成模块大笔记: {note_file.name}")

if __name__ == "__main__":
    print("=== 开始生成 模块 07：异常处理与容错机制 (P86 - P87) ===")
    generate_subtitles()
    generate_articles()
    generate_notes()
    print("=== 模块 07 全部交付物生成完毕！===")
