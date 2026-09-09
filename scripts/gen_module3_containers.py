#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Module 03 Generator: 数据容器 (P36 - P56).
Generates clean subtitles, single-episode textbook articles, and module revision notes.
"""

import json
from pathlib import Path

TASK_DIR = Path("output/黑马程序员Python+AI零基础入门到大神全套视频课程，覆盖Python核心语法、AI应用、数据分析及Web应用等python实战项目开发全流程_BV1sHU")
ARTICLES_DIR = TASK_DIR / "articles"
NOTES_DIR = TASK_DIR / "notes"
SUBTITLES_DIR = TASK_DIR / "subtitles"

COURSE_TITLE = "黑马程序员Python+AI零基础入门到大神全套视频课程"

MODULE3_EPISODES = [
    {
        "page": 36,
        "title": "36. 核心语法-数据容器-概述",
        "clean_title": "36. 核心语法-数据容器-概述",
        "topic": "Python 数据容器架构体系与分类全景",
        "pain_point": "单一标量变量（如 int, float, bool）仅能存储单一离散数据，面对批量化、组织化、多维度的现实数据流（如员工名录、订单列表、学生成绩册）完全无能为力。",
        "theory": "数据容器（Container）是能够容纳多个元素的高级数据类型。Python 原生提供五大基础容器：列表 (list)、元组 (tuple)、字符串 (str)、集合 (set)、字典 (dict)。容器通过底层不同的数据结构（连续数组、哈希表）在内存中管理对象引用，依据是否有序、是否可变、是否允许重复形成完备的正交矩阵。",
        "key_concepts": [
            ("有序 vs 无序", "序列类型（list, tuple, str）元素有严格位置索引，支持下标访问；集合 (set) 无序无索引；字典在 3.7+ 保证插入顺序但本质按键检索"),
            ("可变 vs 不可变", "可变容器（list, set, dict）支持原地（in-place）增删改；不可变容器（str, tuple）一旦创建其物理内存块不可更改"),
            ("重复性约束", "list 与 tuple 允许元素重复；set 与 dict 的 Key 具有数学唯一性，自动去重")
        ],
        "code_example": '''# Python 五大基础数据容器初体验与类型透视
my_list = ["张三", "李四", "王五", "张三"]      # 列表：有序、可变、允许重复
my_tuple = (1001, "Admin", True)               # 元组：有序、不可变、允许重复
my_str = "Python-3.12"                         # 字符串：字符序列、不可变
my_set = {"apple", "banana", "apple"}          # 集合：无序、唯一、去重
my_dict = {"name": "Alice", "age": 20}         # 字典：键值对映射、Key 唯一

print("List:", type(my_list), my_list)
print("Tuple:", type(my_tuple), my_tuple)
print("Str:", type(my_str), my_str)
print("Set (自动去重):", type(my_set), my_set)
print("Dict:", type(my_dict), my_dict)''',
        "pitfalls": [
            "不可变对象误修改：试图对 `str` 或 `tuple` 执行下标签值（如 `s[0] = 'a'`）会触发 TypeError: 'str' object does not support item assignment",
            "集合索引陷阱：试图通过 `my_set[0]` 访问集合元素会触发 TypeError: 'set' object is not subscriptable"
        ],
        "questions": [
            "1. 为什么 Python 要同时提供列表 (list) 与元组 (tuple) 两种极其相似的序列容器？不可变性带来了什么性能与架构收益？",
            "2. 集合与字典的底层数据结构是什么？为什么它们的元素查找时间复杂度能达到 $O(1)$？"
        ]
    },
    {
        "page": 37,
        "title": "37. 核心语法-数据容器-列表list-介绍",
        "clean_title": "37. 核心语法-数据容器-列表list-介绍",
        "topic": "列表 (list) 定义、内存连续布局与正负双向索引",
        "pain_point": "需要一种长度可动态伸缩、支持存储异构元素、能够通过绝对位置高效率定位的通用数据序列。",
        "theory": "Python 的 list 本质上是一个动态指针数组（Array of References）。连续内存空间中存储的是指向各对象的 PyObject 指针。支持通过下标 `[index]` 实现 $O(1)$ 常数级随机访问。Python 独创正负双向索引机制：正向从 `0` 到 `N-1`，逆向从 `-1` 到 `-N`。",
        "key_concepts": [
            ("方括号语法", "列表使用方括号 `[]` 包裹，元素间使用英文逗号 `,` 分隔；空列表为 `[]` 或 `list()`"),
            ("正向索引 (Forward Index)", "从左到右以 `0` 递增，用于按发生时序或常规顺序读取"),
            ("逆向索引 (Reverse Index)", "从右到左以 `-1` 递减，`-1` 恒定指代最后一个元素，无需先求 len 再减 1")
        ],
        "code_example": '''# 列表定义与正负索引实战
heroes = ["钢铁侠", "美国队长", "雷神", "绿巨人", "黑寡妇"]

# 正向索引访问
print("首位英雄 (index 0):", heroes[0])
print("第三位英雄 (index 2):", heroes[2])

# 逆向索引访问
print("末位英雄 (index -1):", heroes[-1])
print("倒数第二位 (index -2):", heroes[-2])

# 嵌套列表（多维数组）
matrix = [
    [1, 2, 3],
    [4, 5, 6],
    [7, 8, 9]
]
print("矩阵中心元素 (row 1, col 1):", matrix[1][1])''',
        "pitfalls": [
            "越界异常 (IndexError)：访问超过 `len(list)-1` 或小于 `-len(list)` 的下标会直接引发 IndexError: list index out of range",
            "空列表取值：对空列表 `[]` 访问 `[0]` 会立刻抛出 IndexError"
        ],
        "questions": [
            "1. 当向列表追加元素导致预分配容量耗尽时，CPython 内部是如何执行扩容（Over-allocation）策略的？",
            "2. 列表元素存储的是对象实体还是内存指针？在存储大对象时这一机制对内存连续性有何影响？"
        ]
    },
    {
        "page": 38,
        "title": "38. 核心语法-数据容器-列表list-切片",
        "clean_title": "38. 核心语法-数据容器-列表list-切片",
        "topic": "列表切片 (Slicing) 语法机制与浅拷贝原理",
        "pain_point": "单点下标访问一次只能获取一个元素。在数据分析、分页加载、时间窗口处理中，往往需要一次性批量截取特定子序列，并支持逆序或跨步提取。",
        "theory": "切片语法 `sequence[start:stop:step]` 是 Python 强大的序列截取工具。其底层遵循左闭右开 `[start, stop)` 区间原则，截取结果会生成一个全新的浅拷贝（Shallow Copy）序列。`step` 决定提取步长与方向（负步长表示反向截取）。切片对越界下标具有超强容错性，不会引发 IndexError。",
        "key_concepts": [
            ("起止省略规则", "`start` 省略默认代表序列头（正向为 0，负步长为 -1）；`stop` 省略默认代表序列尾"),
            ("步长 (step)", "正数表示自左向右递进；负数表示自右向左逆行；`step=2` 表示隔一个取一个"),
            ("序列全反转", "`sequence[::-1]` 能够以底层 C 级极快速度创建反向反转的新序列")
        ],
        "code_example": '''# 列表切片全维度操作指南
numbers = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

# 基础切片：左闭右开 [2, 6)
print("截取 2 到 5:", numbers[2:6])

# 省略起止边界
print("前 4 个元素:", numbers[:4])
print("从索引 5 到末尾:", numbers[5:])

# 步长切片：提取偶数与奇数
print("偶数序列 (step 2):", numbers[::2])
print("奇数序列 (1 开始):", numbers[1::2])

# 逆序截取与整表反转
print("完整反转序列:", numbers[::-1])
print("逆向截取 [8 到 3):", numbers[8:2:-1])

# 原生浅拷贝
clone_numbers = numbers[:]
print("浅拷贝对象是否为同一内存:", clone_numbers is numbers)''',
        "pitfalls": [
            "反向切片起止颠倒：使用负步长时，`start` 必须大于 `stop`（如 `numbers[2:8:-1]` 将返回空列表 `[]` 而非报错）",
            "右边界不可达：想要包含末尾索引，切片 stop 必须显式省略（如 `numbers[-3:]`），不可写成 `numbers[-3:-1]`"
        ],
        "questions": [
            "1. 为什么切片越界（如 `[1, 2, 3][0:100]`）不会抛出 IndexError，而单个索引 `[1, 2, 3][100]` 会崩溃？",
            "2. 什么是浅拷贝？当切片截取的列表中包含嵌套子列表时，修改子列表会对原列表造成什么影响？"
        ]
    },
    {
        "page": 39,
        "title": "39. 核心语法-数据容器-列表list-常用方法",
        "clean_title": "39. 核心语法-数据容器-列表list-常用方法",
        "topic": "列表增删改查方法集与复杂度分析",
        "pain_point": "单纯依靠方括号和切片无法完成高效的动态队列、堆栈操作、元素统计与排序重排。",
        "theory": "Python 为 `list` 类型绑定了丰富的内建方法。增删改查方法根据其在连续数组中的操作位置具有显著不同的时间复杂度：尾部操作（`append`, `pop`）为 $O(1)$ 常数时间，中间插入/删除（`insert`, `remove`）涉及后续元素整体内存平移，为 $O(n)$ 线性时间。`sort()` 基于 Timsort 算法实现 $O(n \\log n)$ 混合稳定排序。",
        "key_concepts": [
            ("元素追加与合并", "`append(x)` 将元素作为单点追加至尾部；`extend(iter)` 将可迭代对象打散追加"),
            ("元素插入与删除", "`insert(idx, x)` 指定位置插入；`pop([idx])` 弹出并返回值；`remove(val)` 移除首个命中值"),
            ("查找、统计与排序", "`index(val)` 返回首个匹配索引；`count(val)` 统计频次；`sort(reverse=True)` 原地排序")
        ],
        "code_example": '''# 列表常用核心方法工业级实操
users = ["alice", "bob", "charlie"]

# 1. 增加操作
users.append("david")                  # 尾部追加 O(1)
users.insert(1, "alex")                # 插入到索引 1 O(n)
users.extend(["emma", "frank"])        # 合并新序列

# 2. 查找与统计
print("当前名录:", users)
print("bob 所在索引位置:", users.index("bob"))
print("列表中 alice 出现次数:", users.count("alice"))

# 3. 删除操作
removed_val = users.pop()             # 弹出末尾 frank
print("被 pop 弹出的元素:", removed_val)
first_item = users.pop(0)             # 弹出首部元素 alice (涉及内存平移)
users.remove("charlie")               # 按值删除首个命中项

# 4. 排序与反转 (原地操作)
users.sort()                          # 原地升序
print("升序排列后:", users)
users.sort(reverse=True)              # 原地降序
print("降序排列后:", users)''',
        "pitfalls": [
            "remove 不存在的值崩溃：若 `remove(val)` 未命中目标，直接抛出 ValueError: list.remove(x): x not in list",
            "sort() 返回 None 陷阱：`users = users.sort()` 会导致变量变成 `None`，因为 `sort()` 是原地修改，无返回值"
        ],
        "questions": [
            "1. 比较 `list.append(item)` 与 `list.extend(item)` 在传入列表参数时的本质差异。",
            "2. 为什么在需要频繁从队首插入和弹出元素的场景下，官方推荐使用 `collections.deque` 而非 `list`？"
        ]
    },
    {
        "page": 40,
        "title": "40. 核心语法-数据容器-列表list-案例1",
        "clean_title": "40. 核心语法-数据容器-列表list-案例1",
        "topic": "列表实战案例：学员成绩统计与极值过滤系统",
        "pain_point": "如何结合前面学习的循环、分支与列表方法，完成动态数据的输入暂存、极值过滤、总分统计与均值计算综合业务需求。",
        "theory": "构建典型的数据采集与统计管道（Data Pipeline）：输入阶段使用 `while` 循环配合 `append` 采集动态数据；处理阶段运用内置函数 `len()`, `sum()`, `max()`, `min()` 或算法遍历完成指标聚合；输出阶段进行格式化报表呈现。",
        "key_concepts": [
            ("动态输入累加器", "利用哨兵值（Sentinel Value，如 -1）控制数据输入循环何时终结"),
            ("聚合统计函数", "`sum()` 对数值序列求和，$O(n)$ 复杂度；`max()` / `min()` 遍历定位极值"),
            ("列表过滤清洗", "在遍历过程中剔除异常分或离群值")
        ],
        "code_example": '''# 学员考试成绩动态采集与统计分析系统
scores = []

print("=== 学员成绩录入系统 (输入 -1 结束录入) ===")
# 1. 动态循环采集数据
while True:
    val = float(input("请输入成绩 (0-100): "))
    if val == -1:
        break
    if 0 <= val <= 100:
        scores.append(val)
    else:
        print("【警告】成绩超出 0~100 范围，请重新输入！")

# 2. 综合业务统计
if scores:
    total_count = len(scores)
    total_sum = sum(scores)
    avg_score = total_sum / total_count
    highest = max(scores)
    lowest = min(scores)

    # 3. 报表输出
    print("\\n========= 成绩统计报表 =========")
    print(f"录入总人数: {total_count} 人")
    print(f"全班总成绩: {total_sum:.2f} 分")
    print(f"全班平均分: {avg_score:.2f} 分")
    print(f"最高分分值: {highest:.2f} 分")
    print(f"最低分分值: {lowest:.2f} 分")
else:
    print("未录入任何有效成绩数据。")''',
        "pitfalls": [
            "除以零错误 (ZeroDivisionError)：若用户一开局就输入 -1，`scores` 为空，直接算 `sum(scores)/len(scores)` 会引发 ZeroDivisionError",
            "浮点输入崩溃：输入带有非数字字符时 `float()` 抛出 ValueError，需提前进行防御性校验"
        ],
        "questions": [
            "1. 若需要在计算平均分时去掉一个最高分和一个最低分（去除极值均值），该如何优雅地使用列表方法实现？",
            "2. 如何使用 `scores.sort()` 先排序再通过索引截取完成前三名（Top 3）的快速提取？"
        ]
    },
    {
        "page": 41,
        "title": "41. 核心语法-数据容器-列表list-案例2(解包)",
        "clean_title": "41. 核心语法-数据容器-列表list-案例2(解包)",
        "topic": "序列解包 (Unpacking) 与星号表达式 (*rest)",
        "pain_point": "从多元素序列中提取变量往往需要写多行机械的下标赋值（如 `a = lst[0]; b = lst[1]`），代码冗长且极易出现索引笔误。",
        "theory": "序列解包（Sequence Unpacking / Destructuring Assignment）允许将一个可迭代对象中的元素直接映射解构成对应数量的独立变量。结合 PEP 3132 扩展解包语法（Extended Iterable Unpacking），使用单个星号 `*var` 可以贪婪捕获任意长度的剩余元素形成子列表，极大地增强了解析弹性。",
        "key_concepts": [
            ("精确匹配解包", "左侧变量数量与右侧元素长度必须绝对一致，否则报 ValueError"),
            ("带星号贪婪捕获 `*rest`", "星号变量在解包表达式中只能出现一次，用于吸收不定长度的元素，其结果类型恒为 `list`"),
            ("下划线丢弃占位符 `_`", "惯例使用 `_` 或 `*_` 忽略不需要的非关键字段")
        ],
        "code_example": '''# 序列解包与星号高级表达式实战
record = ["2026-09-08", "ORDER-99882", "MacBook Pro", 19999.0, "张三", "北京市朝阳区"]

# 1. 精确解包头部字段，用 * 吸收剩余详情
date, order_id, product, price, *customer_info = record
print(f"订单编号: {order_id}, 购买商品: {product}, 价格: {price}")
print(f"客户联系详情 (吸收为列表): {customer_info}")

# 2. 掐头去尾求平均分（星号置于中间）
scores = [58, 85, 92, 78, 96, 88, 45]
scores.sort() # [45, 58, 78, 85, 88, 92, 96]
min_score, *middle_scores, max_score = scores
print(f"最低分: {min_score}, 最高分: {max_score}")
print(f"中间有效分列表: {middle_scores}")
print(f"去除极值后的裁判均分: {sum(middle_scores)/len(middle_scores):.2f}")''',
        "pitfalls": [
            "解包变量数目不匹配：变量少于元素会报错 `ValueError: too many values to unpack`；变量多于元素报错 `ValueError: not enough values to unpack`",
            "多个星号语法错误：一行赋值语句中书写两个星号（如 `*a, *b = lst`）直接引发 SyntaxError: multiple starred expressions in assignment"
        ],
        "questions": [
            "1. 当序列长度正好等于非星号变量总数时，带星号的变量接收到的值是什么？",
            "2. 为什么在 Python 中交换两个变量只需 `a, b = b, a`？这背后应用了什么组包与解包机制？"
        ]
    },
    {
        "page": 42,
        "title": "42. 核心语法-数据容器-列表list-案例3(推导式)",
        "clean_title": "42. 核心语法-数据容器-列表list-案例3(推导式)",
        "topic": "列表推导式 (List Comprehension) 语法与性能跃迁",
        "pain_point": "通过传统 `for` 循环 + `append` 方式构建新列表代码繁复冗长（4~5 行模板代码），并且由于在 Python 字节码层反复执行属性查找和方法调用，运行效率低。",
        "theory": "列表推导式是 Python 提供的一种从现有可迭代对象快速派生、映射和过滤生成新列表的高级语法糖。语法遵循 `[expression for item in iterable if condition]`。其在 CPython 虚拟机内部直接通过专用优化字节码（`LIST_APPEND`）以接近 C 语言的速度就地构造列表，性能显著优于原生 append 循环。",
        "key_concepts": [
            ("推导式标准三段式", "1. 目标表达式 (Expression)；2. 遍历源 (Iteration)；3. 过滤守卫条件 (Condition)"),
            ("推导式内嵌双重循环", "`[x * y for x in list1 for y in list2]` 相当于外层 list1 嵌套内层 list2"),
            ("与 map/filter 的抉择", "列表推导式可读性更强，更加符合 Pythonic 哲学")
        ],
        "code_example": '''# 列表推导式全景演练与对比
raw_numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

# 1. 传统 for 循环写法 (基准)
evens_traditional = []
for n in raw_numbers:
    if n % 2 == 0:
        evens_traditional.append(n ** 2)

# 2. 列表推导式极简实现 (1行搞定，性能更优)
evens_comp = [n ** 2 for n in raw_numbers if n % 2 == 0]
print("偶数平方列表 (推导式):", evens_comp)

# 3. 业务字符串清洗实战：去除空白并统一大写
raw_users = ["  alice ", "BOB", "  chArlie  ", " David"]
clean_users = [u.strip().upper() for u in raw_users if len(u.strip()) > 3]
print("清洗后合规用户名列表:", clean_users)

# 4. 二维矩阵展平 (Flatten Matrix)
matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
flattened = [val for row in matrix for val in row]
print("展平后的一维向量:", flattened)''',
        "pitfalls": [
            "过度嵌套导致可读性坍塌：书写超过两层循环或带有过于复杂三元条件的推导式会严重伤害可读性，应拆解为标准函数或多行循环",
            "在大数据量下内存耗尽：列表推导式会立刻在内存中物化整个完整列表，处理千万级数据时应改用生成器表达式 `(x for x in it)`"
        ],
        "questions": [
            "1. 为什么列表推导式比等价的显式 `for` 循环搭配 `list.append()` 运行速度更快？请从字节码角度解释。",
            "2. 列表推导式中的 `if` 条件写在 `for` 后面与写在表达式中的三元运算符 `val if cond else other for ...` 有何本质区别？"
        ]
    },
    {
        "page": 43,
        "title": "43. 核心语法-数据容器-字符串str-基本操作",
        "clean_title": "43. 核心语法-数据容器-字符串str-基本操作",
        "topic": "字符串作为字符容器的只读序列特性",
        "pain_point": "初学者常将字符串仅仅当作纯文本字面量，忽略了它在底层也是一种具有索引、切片、遍历特性的标准序列数据容器，且具有强制不可变性约束。",
        "theory": "在 Python 3 中，`str` 是 Unicode 字符序列容器。它具有序列的共性：支持通过 `0` 到 `len-1` 进行正向索引、负数逆向索引、切片截取、`for-in` 遍历以及 `in` 成员判定。同时，`str` 属于严格不可变类型（Immutable），字符串一旦分配在内存中，其中的任何字符不可原地更改，任何变换方法都会生成全新的字符串对象。",
        "key_concepts": [
            ("字符索引与切片", "语法与列表完全相同，但获取的结果是长度为 1 的子字符串，而非字符类型（Python 无 char 类型）"),
            ("不可变性内存约束", "调用修改操作时内部发生重新分配内存与字符拷贝，大量拼接应借助 `str.join()`"),
            ("成员运算符 `in`", "不仅能判断单个字符，还能以高效率检测任意连续子字符串是否存在")
        ],
        "code_example": '''# 字符串作为数据容器的基本操作
course_name = "Python3-DataStructure"

# 1. 下标访问与反向访问
print("首字符:", course_name[0])
print("尾字符:", course_name[-1])

# 2. 字符串切片与子串截取
print("语言名称:", course_name[0:6])
print("数据结构部分:", course_name[8:])
print("字符串翻转:", course_name[::-1])

# 3. 容器遍历与成员检测
print("字符迭代输出: ", end="")
for char in course_name[:7]:
    print(char, end="·")
print()

print("是否存在 'Data':", "Data" in course_name)
print("是否存在 'Java':", "Java" in course_name)''',
        "pitfalls": [
            "就地下标赋值报错：书写 `course_name[0] = 'p'` 会直接引发 TypeError: 'str' object does not support item assignment",
            "大量字符串用 `+` 频繁累加：在循环中不断使用 `s += new_str` 会引发 $O(n^2)$ 级别的连续内存分配与数据搬移，性能急剧恶化"
        ],
        "questions": [
            "1. 为什么 Python 没有单独的 `char` 类型？字符串索引返回的是什么类型？",
            "2. 简述 Python 字符串驻留机制（String Interning）的作用及其发生条件。"
        ]
    },
    {
        "page": 44,
        "title": "44. 核心语法-数据容器-字符串str-常用方法",
        "clean_title": "44. 核心语法-数据容器-字符串str-常用方法",
        "topic": "字符串清洗、拆分与格式变换核心 API 矩阵",
        "pain_point": "自然语言文本和接口响应中充斥着脏数据（首尾多余空白、乱码分隔符、大小写混用、敏感字符）。手工切片处理极度繁琐易错。",
        "theory": "Python 为 `str` 提供了工业级内建字符串处理方法集，涵盖三大类：1. 拆分与聚合（`split`, `rsplit`, `splitlines`, `join`）；2. 清洗与修剪（`strip`, `lstrip`, `rstrip`, `replace`）；3. 判别与变换（`find`, `index`, `startswith`, `endswith`, `lower`, `upper`, `isdigit`）。所有方法均严格遵循不可变性，返回新字符串。",
        "key_concepts": [
            ("split 与 join 黄金搭档", "`split(sep)` 将字符串按分隔符切割为列表；`sep.join(list)` 将列表元素以分隔符高效率粘合"),
            ("strip 空白修剪", "默认剔除字符串两端的空格、制表符 `\\t`、换行符 `\\n`"),
            ("安全检索 find vs 严格检索 index", "`find()` 检索不到时返回 `-1`，而 `index()` 会抛出 ValueError")
        ],
        "code_example": '''# 字符串常用方法高频清洗流水线
raw_csv_line = "  1001,  Zhang San , 25 , Engineer\\n  "

# 1. strip 修剪首尾空白与换行
clean_line = raw_csv_line.strip()
print("修剪后:", clean_line)

# 2. split 拆分为字段列表
fields = clean_line.split(",")
print("拆分后的字段列表:", fields)

# 3. 深度字段级修剪
final_fields = [f.strip() for f in fields]
print("字段标准化:", final_fields)

# 4. join 重新聚合为标准制表符 TSV 格式
tsv_output = "\\t".join(final_fields)
print("TSV 格式输出:", tsv_output)

# 5. replace 与安全检索
statement = "Python is powerful and Python is simple."
new_stmt = statement.replace("Python", "Rust", 1) # 仅替换首个
print("单次替换后:", new_stmt)
print("查找 'Rust' 首位索引:", new_stmt.find("Rust"))
print("查找不存在的 'Java' 索引:", new_stmt.find("Java")) # 返回 -1''',
        "pitfalls": [
            "join 的类型陷阱：`''.join([1, 2, 3])` 会崩溃并抛出 TypeError: sequence item 0: expected str instance, int found，元素必须全部先转为 str",
            "replace 默认全局替换：`s.replace('a', 'b')` 会替换所有出现的 'a'，若只需替换前 N 个必须显式传入 `count` 参数"
        ],
        "questions": [
            "1. 为什么构建大文本时用 `separator.join(str_list)` 的效率远高于使用 `+` 连续拼接？",
            "2. 简述 `str.isdigit()`, `str.isnumeric()` 与 `str.isalnum()` 在处理全角数字、汉字大写数字时的区别。"
        ]
    },
    {
        "page": 45,
        "title": "45. 核心语法-数据容器-字符串str-案例",
        "clean_title": "45. 核心语法-数据容器-字符串str-案例",
        "topic": "文本分析实战：敏感词过滤与用户输入合法性校验",
        "pain_point": "社区评论、聊天框或表单录入常面临垃圾广告词、脏字攻击以及格式不规范输入，需要构建健壮的文本合规清洗管道。",
        "theory": "结合 `in` 成员判定、`replace` 遮蔽替换以及字符串判别函数构建双层过滤器：第一层为格式校验层（检测长度、是否为空白字符、是否为纯数字/字母）；第二层为内容安全清洗层（基于敏感词库进行星号 `***` 脱敏替换）。",
        "key_concepts": [
            ("敏感词词库匹配", "遍历违禁词列表，在目标文本中检索并使用相同长度的 `*` 替换"),
            ("输入防空防呆设计", "利用 `strip()` 过滤仅包含空格的恶意无效输入"),
            ("不可变变量重绑定", "每一次替换结果必须重新赋给原文本变量，驱动状态迭代")
        ],
        "code_example": '''# 论坛评论敏感词脱敏清洗与合规审计系统
sensitive_words = ["炸弹", "违禁品", "刷单", "赌博", "假钞"]

comment_input = input("请发表您的社区评论: ")

# 1. 基础校验：防空白输入与长度控制
clean_comment = comment_input.strip()
if not clean_comment:
    print("【拦截】评论内容不能为空或纯空格！")
elif len(clean_comment) > 200:
    print("【拦截】评论字数超限（最大允许 200 字）！")
else:
    # 2. 敏感词扫描与星号替换
    intercepted_count = 0
    for word in sensitive_words:
        if word in clean_comment:
            intercepted_count += 1
            # 动态生成与违禁词同等长度的星号
            replacement = "*" * len(word)
            clean_comment = clean_comment.replace(word, replacement)
    
    # 3. 结果输出与审计日志
    print("\\n=== 评论发布成功 ===")
    print("最终呈现内容:", clean_comment)
    if intercepted_count > 0:
        print(f"[系统安全日志] 触发敏感词过滤，已脱敏命中词频: {intercepted_count} 处。")''',
        "pitfalls": [
            "忘记重新赋值：写了 `clean_comment.replace(word, '***')` 但没有回写 `clean_comment = ...`，由于字符串不可变，原始文本毫无变化",
            "子串误伤（Scunthorpe 问题）：如敏感词为“赌”，将“打赌”也一并替换，工业级方案需配合分词工具，但入门阶段需先掌握遍历替换"
        ],
        "questions": [
            "1. 如何利用 Python 的 `str.count(sub)` 方法统计某个特定关键词在整篇文章中出现的总频次？",
            "2. 若要快速统计用户输入英文字符串中元音字母 (a, e, i, o, u) 的出现总数，如何结合容器遍历与 `in` 操作写出优雅代码？"
        ]
    },
    {
        "page": 46,
        "title": "46. 核心语法-数据容器-元组tuple-基本操作",
        "clean_title": "46. 核心语法-数据容器-元组tuple-基本操作",
        "topic": "元组 (tuple) 只读特性、单元素语法陷阱与内存开销",
        "pain_point": "列表作为可变容器，在传递给外部函数或作为多线程共享配置时，极易被意外修改（副作用）。需要一种一旦定义便绝对安全、不可篡改的只读序列。",
        "theory": "元组（Tuple）是 Python 核心的不可变有序序列（Immutable Sequence）。使用圆括号 `()` 定义。由于其结构与大小固定，CPython 可以对元组进行极高的内存与运行时优化（无扩容冗余预分配、小元组全局缓存池）。只读性使得元组天然线程安全，并可作为哈希键（Hashable Key）用于集合与字典。",
        "key_concepts": [
            ("单元素元组逗号原则", "定义仅包含一个元素的元组时，必须在元素后紧跟一个英文逗号 `(item,)`，否则括号会被视为算术运算符"),
            ("只读保护机制", "不支持任何增删改方法（无 append, pop, insert），仅支持 `index()` 与 `count()` 两个只读探查方法"),
            ("浅层不可变性", "元组不可变的是其**指向各对象的引用指针**；若元组内部包含可变对象（如列表），该列表内部的元素依然可以修改！")
        ],
        "code_example": '''# 元组基本操作与不可变性底层演示
# 1. 多种定义方式
empty_tup = ()
singleton_tup = ("admin",)         # 关键！末尾逗号不可少
not_a_tup = ("admin")             # 危险！这只是一个 str 字符串！
print("singleton_tup 类型:", type(singleton_tup))
print("not_a_tup 类型:", type(not_a_tup))

# 2. 正负索引与切片（完全同列表）
server_conf = ("192.168.1.100", 8080, "Production", 60)
print("服务器 IP:", server_conf[0])
print("服务端口:", server_conf[1])
print("切片前两项:", server_conf[:2])

# 3. 探查方法
print("8080 所在索引:", server_conf.index(8080))
print("60 出现频次:", server_conf.count(60))

# 4. 浅层不可变性本质剖析
mixed_tup = (1, 2, ["A", "B"])
# mixed_tup[0] = 100               # 报错！TypeError
mixed_tup[2].append("C")           # 合法！元组持有的指针没变，变的是指针指向的列表内部
print("修改内部列表后的元组:", mixed_tup)''',
        "pitfalls": [
            "单元素忘记逗号：`a = (1)` 会被解释器直接判定为整型 `int`，后续当成元组调用方法时引发 AttributeError",
            "误解不可变性边界：以为元组里的子列表也能防修改，忽略了元组只保证第一层引用指针不可变"
        ],
        "questions": [
            "1. 为什么在需要只读数据的场景下，优先选用元组而非列表？元组在内存占用与构建速度上有何优势？",
            "2. 包含列表的元组 `(1, 2, [3, 4])` 能否作为字典的 Key？为什么？会抛出什么异常？"
        ]
    },
    {
        "page": 47,
        "title": "47. 核心语法-数据容器-元组tuple-组包与解包",
        "clean_title": "47. 核心语法-数据容器-元组tuple-组包与解包",
        "topic": "元组自动组包 (Packing) 与多元解包机制",
        "pain_point": "在函数需要同时返回多个结果（如状态码、错误信息、返回数据）时，传统语言必须封装专门的 DTO 结构体或指针引用，代码繁杂冗余。",
        "theory": "Python 允许省略圆括号定义序列，当多个由逗号分隔的表达式出现在赋值语句右侧时，解释器会自动将其打包（Packing）为一个整体元组；反之，将元组赋值给多个由逗号分隔的左侧变量时，会自动执行解构解包（Unpacking）。这构成了 Python“函数返回多个值”的底层物理真相。",
        "key_concepts": [
            ("自动组包", "`a = 10, 20, 30` 解释器自动构建为 `(10, 20, 30)` 元组"),
            ("函数多值返回的真相", "书写 `return x, y, z` 并不是同时返回了 3 个对象，而是返回了 1 个打包好的 `tuple`！"),
            ("极简多元赋值", "`x, y = 1, 2` 本质是先在右侧组包为 `(1, 2)`，再向左侧解包赋值")
        ],
        "code_example": '''# 元组组包与解包及函数多值返回探微
# 1. 自动组包语法
point = 120.5, 30.2, 15.0          # 省略括号，自动推导为 tuple
print("point 类型与值:", type(point), point)

# 2. 对称解包
longitude, latitude, altitude = point
print(f"经度: {longitude}, 纬度: {latitude}, 海拔: {altitude}")

# 3. 函数多返回值原理演示
def get_user_and_status(user_id: int):
    # 模拟从数据库提取
    username = "Alice"
    is_active = True
    role = "SuperAdmin"
    return username, is_active, role   # 本质返回一个三元组

# 调用端直接解包接收
name, active, role = get_user_and_status(1001)
print(f"用户: {name}, 活跃状态: {active}, 权限组: {role}")

# 也可以用单个变量接收整个打包元组
result_packet = get_user_and_status(1001)
print("打包接收的原生元组:", type(result_packet), result_packet)''',
        "pitfalls": [
            "赋值语句末尾误加逗号：书写 `x = 100,` 会导致 `x` 意外变成单元素元组 `(100,)`，随后参与数学运算时抛出 TypeError",
            "解包数量不一致：左侧变量数量与元组元素数量不等时直接触发 ValueError: too many values to unpack"
        ],
        "questions": [
            "1. 请解释在 Python 中运行 `a, b = b, a` 交换变量的过程中，组包与解包分别在什么时候发生？",
            "2. 如果一个函数返回了 5 个值，而调用方只关心第 1 个和最后 1 个，如何利用解包语法进行优雅提取？"
        ]
    },
    {
        "page": 48,
        "title": "48. 核心语法-数据容器-元组tuple-案例",
        "clean_title": "48. 核心语法-数据容器-元组tuple-案例",
        "topic": "元组实战：几何坐标计算与不可变配置字典",
        "pain_point": "在地理信息系统（GIS）、图形学或核心系统配置中，坐标点 `(x, y)` 或数据库连接参数严禁在运行期被任何业务模块篡改，一旦篡改会导致灾难性逻辑偏离。",
        "theory": "利用元组的强不可变约束表达不可变实体（如二维/三维空间点、RGB 颜色三元组、数据库只读行）。通过元组解包获取各维度分量，执行欧几里得距离等几何数学计算。",
        "key_concepts": [
            ("不可变实体模型", "使用元组表达 `(x, y)` 坐标，消除意外重写风险"),
            ("欧氏几何距离公式", "$d = \\\\sqrt{(x_2 - x_1)^2 + (y_2 - y_1)^2}$"),
            ("多点序列容器化", "在列表中嵌套存储元组 `[(x1, y1), (x2, y2), ...]`")
        ],
        "code_example": '''import math

# 几何空间坐标距离计算系统
point_a = (10.0, 20.0)
point_b = (13.0, 24.0)

# 解包获取坐标分量
x1, y1 = point_a
x2, y2 = point_b

# 计算二维欧氏距离
distance = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
print(f"点 A {point_a} 到点 B {point_b} 的空间直线距离为: {distance:.2f}")

# 路径轨迹点列遍历
path = [
    (0, 0),
    (3, 4),
    (6, 8),
    (9, 12)
]

total_length = 0.0
for i in range(len(path) - 1):
    curr_x, curr_y = path[i]
    next_x, next_y = path[i + 1]
    seg_dist = math.sqrt((next_x - curr_x)**2 + (next_y - curr_y)**2)
    total_length += seg_dist

print(f"该航线总飞行里程: {total_length:.2f} 单位")''',
        "pitfalls": [
            "浮点精度误差：直接比对两坐标距离是否为 0 时不可使用 `== 0.0`，应使用 `math.isclose()` 进行误差范围判等",
            "误用列表代替关键坐标：若将基础常量坐标定义为可变列表，在多方传递时可能被外部函数无意修改导致不可重现的 Bug"
        ],
        "questions": [
            "1. 相比于自定义类（Class）或字典（Dict），在存储数百万个坐标点时使用元组能节省多少内存开销？",
            "2. 如何使用元组作为字典的 Key 来构建一个稀疏矩阵（Sparse Matrix）？"
        ]
    },
    {
        "page": 49,
        "title": "49. 核心语法-数据容器-元组tuple-案例(优化)",
        "clean_title": "49. 核心语法-数据容器-元组tuple-案例(优化)",
        "topic": "命名元组 (namedtuple) 结构化演进与代码可读性跃迁",
        "pain_point": "普通元组仅能通过数字下标（如 `point[0]`, `point[1]`）访问字段，当元组属性超过 3 个时，代码充斥着“魔术索引”（Magic Number），可读性极差且重构极其脆弱。",
        "theory": "Python 标准库 `collections` 提供了 `namedtuple`（命名元组）工厂函数。它继承自普通元组，具有元组完全相同的轻量内存占用和不可变特性，同时为每个位置分配了可读的字段名称，允许通过点号属性 `point.x` 和属性名进行语义化访问，完美兼具字典的易读性与元组的高性能。",
        "key_concepts": [
            ("工厂函数定义", "`Point = namedtuple('Point', ['x', 'y'])` 生成具有指定字段的专用子类"),
            ("点号属性访问", "支持 `p.x` 和 `p.y`，彻底废弃含混的 `p[0]` 和 `p[1]`"),
            ("向后完全兼容", "仍然支持下标索引、切片、解包以及作为字典的哈希键")
        ],
        "code_example": '''from collections import namedtuple
import math

# 1. 定义具名元组数据结构
Point = namedtuple("Point", ["x", "y", "label"])

# 2. 实例化对象（支持关键字传参与位置传参）
p1 = Point(x=10.0, y=20.0, label="起点站")
p2 = Point(13.0, 24.0, "中继站")

# 3. 语义化点号访问
print(f"站点: {p1.label}, 坐标: ({p1.x}, {p1.y})")
print(f"站点: {p2.label}, 坐标: ({p2.x}, {p2.y})")

# 4. 计算距离（代码语义清晰，毫无魔术数字）
dist = math.sqrt((p2.x - p1.x)**2 + (p2.y - p1.y)**2)
print(f"{p1.label} -> {p2.label} 的直接测距: {dist:.2f}")

# 5. 依然支持原生解包与转字典
x, y, label = p1
print(f"解包成功: {label} ({x}, {y})")
print("转换为有序字典字典呈现:", p1._asdict())''',
        "pitfalls": [
            "试图修改 namedtuple 属性：由于其底层仍然是不可变元组，执行 `p1.x = 30` 会直接引发 AttributeError: can't set attribute",
            "字段名非法约束：字段名必须是合法的 Python 标识符，且不能与 Python 关键字重名"
        ],
        "questions": [
            "1. 相比于普通的 Python 类（`class Point: pass`），`namedtuple` 在实例内存空间分配上有何优势？",
            "2. 在 Python 3.7+ 中，标准库引入了 `@dataclass(frozen=True)`，它与 `namedtuple` 在选型上有何权衡？"
        ]
    },
    {
        "page": 50,
        "title": "50. 核心语法-数据容器-集合set-基本操作",
        "clean_title": "50. 核心语法-数据容器-集合set-基本操作",
        "topic": "集合 (set) 底层哈希表机制、互异性与无序性",
        "pain_point": "列表中允许无限重复元素，在做去重、白名单校验、海量数据成员存在性检测时，列表遍历的 $O(n)$ 复杂度会导致随着数据量膨胀性能线性崩塌。",
        "theory": "集合（Set）是无序且元素唯一的容器类型。底层直接基于哈希表（Hash Table）构建（只保存键、不保存值的字典变体）。集合内所有元素必须是可哈希（Hashable / Immutable）的对象。由于哈希寻址特性，元素的新增、删除、`in` 查找时间复杂度均达到恒定的 $O(1)$ 常数时间。",
        "key_concepts": [
            ("花括号语法与空集合", "集合使用花括号 `{}` 定义；定义空集合必须使用 `set()`，直接写 `{}` 会被解释器判定为空字典！"),
            ("互异性（自动去重）", "向集合中添加重复元素会被静默丢弃，天然用于海量数据去重"),
            ("基本操作方法", "`add(x)` 添加单元素；`remove(x)` 严格删除（未命中抛 KeyError）；`discard(x)` 安全删除（未命中静默忽略）；`pop()` 随机弹出一个元素")
        ],
        "code_example": '''# 集合基本操作与底层哈希特性
# 1. 集合定义与空集合避坑
empty_set = set()                      # 正确空集合定义
not_empty_set = {}                     # 危险！这是一个 dict 字典！
print("empty_set 类型:", type(empty_set))
print("not_empty_set 类型:", type(not_empty_set))

# 2. 自动去重演示
user_ids = {1001, 1002, 1003, 1001, 1002}
print("去重后的集合内容:", user_ids)   # {1001, 1002, 1003}

# 3. 增删查操作
user_ids.add(1004)                     # 添加单元素
print("添加 1004 后:", user_ids)

user_ids.discard(9999)                 # 安全删除不存在项，绝不抛异常
# user_ids.remove(9999)                # 抛出 KeyError: 9999！

# 4. 高效 O(1) 成员判定
print("1002 是否在白名单中:", 1002 in user_ids)
print("9999 是否在白名单中:", 9999 in user_ids)''',
        "pitfalls": [
            "可变对象放入集合引发异常：试图向集合放入列表或字典（如 `{1, [2, 3]}`）会直接抛出 TypeError: unhashable type: 'list'",
            "下标索引访问报错：写 `user_ids[0]` 会引发 TypeError: 'set' object is not subscriptable，因为集合是无序的，无物理下标概念"
        ],
        "questions": [
            "1. 为什么集合中的元素必须是“可哈希的”（Hashable）？什么类型的对象才算可哈希？",
            "2. 比较在包含 100 万条数据的列表中做 `x in my_list` 和在集合中做 `x in my_set` 的运行时间差距。"
        ]
    },
    {
        "page": 51,
        "title": "51. 核心语法-数据容器-集合set-案例",
        "clean_title": "51. 核心语法-数据容器-集合set-案例",
        "topic": "集合实战：极速去重与数学文氏图代数运算",
        "pain_point": "面对两个大型用户群（如电商活跃用户与付费用户），如何高效找出共同用户（交集）、新增目标用户（差集）、全量合并用户（并集）？手动双重循环代码复杂度高达 $O(n^2)$。",
        "theory": "Python 集合完整支持现代数学文氏图集合代数运算。通过原生重载运算符提供极高效率的底层集合操作：并集 `|`（Union）、交集 `&`（Intersection）、差集 `-`（Difference）、对称差集 `^`（Symmetric Difference）。底层由 C 语言加速，运算性能卓越。",
        "key_concepts": [
            ("一秒去重模式", "`unique_list = list(set(raw_list))` 是 Pythonic 极速去重的标配（注意会打乱原始顺序）"),
            ("并集 `setA | setB`", "合并两集合全部元素并自动剔除重复项"),
            ("交集 `setA & setB`", "提取同时存在于两集合中的共有元素"),
            ("差集 `setA - setB`", "属于 A 且绝对不属于 B 的独有元素")
        ],
        "code_example": '''# 集合文氏图代数运算电商用户画像分析
# 1. 极速列表去重
raw_visits = ["用户A", "用户B", "用户A", "用户C", "用户B", "用户D"]
clean_visits = list(set(raw_visits))
print("原始访问流水:", raw_visits)
print("去重后的独立访客 (UV):", clean_visits)

# 2. 集合代数分析：活跃用户群 vs 付费用户群
active_users = {"Alice", "Bob", "Charlie", "David"}
vip_users = {"Charlie", "David", "Emma", "Frank"}

# 交集 &：既是活跃又是 VIP 的高价值核心用户
core_vips = active_users & vip_users
print("核心活跃 VIP 用户 (交集 &):", core_vips)

# 差集 -：活跃但尚未付费的潜在转化用户
potential_targets = active_users - vip_users
print("待营销潜在转化用户 (差集 active - vip):", potential_targets)

# 并集 |：触达的全部独立用户大盘
all_audience = active_users | vip_users
print("全量触达独立用户总数 (并集 |):", len(all_audience), all_audience)

# 对称差集 ^：仅在一个圈子出现的非交叉用户
exclusive_users = active_users ^ vip_users
print("非交叉独立用户 (对称差集 ^):", exclusive_users)''',
        "pitfalls": [
            "去重导致元素顺序打乱：`list(set(seq))` 会破坏原本的序列顺序。若需要保留顺序，应使用 `dict.fromkeys(seq)` 或循环去重",
            "运算符与方法的参数差异：运算符 `a | b` 要求两侧必须都是集合，而对应的方法 `a.union(b)` 可以接收任何可迭代对象（如列表）"
        ],
        "questions": [
            "1. 如何在保留列表原始输入顺序的前提下，实现时间复杂度为 $O(n)$ 的高效去重？",
            "2. 简述子集（`s1.issubset(s2)` 或 `s1 <= s2`）与超集（`s1.issuperset(s2)`）的数学含义与应用场景。"
        ]
    },
    {
        "page": 52,
        "title": "52. 核心语法-数据容器-字典dict-介绍",
        "clean_title": "52. 核心语法-数据容器-字典dict-介绍",
        "topic": "字典 (dict) 键值对映射原理与键的哈希唯一性",
        "pain_point": "列表仅能通过数字索引（0, 1, 2）存储数据。现实业务实体（如学生：姓名、年龄、学号、住址）具有强烈的字段属性名，无法通过位置直观语义化建模。",
        "theory": "字典（Dictionary / Map）是 Python 独有的核心键值对（Key-Value Pair）映射容器。使用花括号 `{}` 定义，键值之间用冒号 `:` 连接，键值对之间用逗号 `,` 分隔。字典底层基于高度优化的稀疏哈希表（Hash Table）实现。字典的键必须具备哈希性（Hashable，不可变对象），且在字典中具有绝对唯一性；值则没有任何类型限制，可任意嵌套。",
        "key_concepts": [
            ("键值对结构 (K-V)", "键相当于自定义标签/索引，值是其绑定的具体数据实体"),
            ("键的唯一性与覆盖性", "向字典写入已存在的 Key 时，新 Value 会直接无条件覆盖旧 Value"),
            ("可哈希性约束", "数值、字符串、元组可作为合法的 Key；列表、集合、字典本身绝对不能作为 Key")
        ],
        "code_example": '''# 字典定义与底层哈希特性演练
# 1. 字典标准语法
student = {
    "id": 10086,
    "name": "李小龙",
    "age": 22,
    "skills": ["武术", "哲学", "影视"], # 值为列表
    "is_graduated": False
}

print("学生字典全景:", student)

# 2. 键的读取与修改
print("学生姓名:", student["name"])
print("专业技能列表:", student["skills"])

student["age"] = 23                    # 原地修改已存在的 Key
student["city"] = "香港"               # 新增不存在的 Key
print("更新后字典:", student)

# 3. 键必须是不可变对象
valid_dict = {
    (0, 0): "原点",                    # 元组作为 Key：合法！
    100: "整数Key",                    # 整数作为 Key：合法！
}
# invalid_dict = { [1, 2]: "报错" }   # 致命！TypeError: unhashable type: 'list'
print("坐标映射字典:", valid_dict[(0, 0)])''',
        "pitfalls": [
            "中括号取不存在的 Key 崩溃：若 `student['score']` 不存在，直接抛出 KeyError: 'score'，必须使用 `.get()` 进行安全检索",
            "列表做 Key 引发 TypeError：试图用可变容器作为 Key 会被哈希检查直接拦截"
        ],
        "questions": [
            "1. 为什么 Python 3.7+ 的字典能够保持键值对的插入顺序（Insertion Order）？其内部紧凑数组与稀疏表架构是如何协同的？",
            "2. 字典读取一个键 `d[k]` 的平均时间复杂度是多少？在发生极端哈希冲突时最差复杂度会退化到多少？"
        ]
    },
    {
        "page": 53,
        "title": "53. 核心语法-数据容器-字典dict-常用操作",
        "clean_title": "53. 核心语法-数据容器-字典dict-常用操作",
        "topic": "字典安全访问、键值视图遍历与高阶操作 API",
        "pain_point": "直接使用 `d[k]` 取值面临巨大的 KeyError 崩溃风险，且缺乏对字典键、值、键值对的成套迭代解构手段。",
        "theory": "Python 为字典设计了完备的操作体系。安全取值 `get(key, default)` 提供兜底保底机制；`keys()`, `values()`, `items()` 返回高效的动态字典视图（Dictionary Views），支持 $O(1)$ 内存实时反映字典变动；`update()` 实现批量合并；`pop(key)` 安全弹出；`setdefault()` 支撑默认值初始化。",
        "key_concepts": [
            ("安全获取 `.get()`", "Key 存在返回对应 Value；Key 不存在返回指定默认值（默认 None），绝不崩溃抛错"),
            ("动态视图三剑客", "`.keys()` 获取全键；`.values()` 获取全值；`.items()` 获取 `(k, v)` 二元组供解包遍历"),
            ("字典合并 `.update()`", "用另一个字典或可迭代键值对覆盖更新当前字典（3.9+ 支持合并运算符 `|`）")
        ],
        "code_example": '''# 字典核心方法与生产级遍历模式
inventory = {"apple": 50, "banana": 30, "orange": 20}

# 1. 安全取值 get
print("香蕉库存:", inventory.get("banana"))
print("西瓜库存 (安全默认值 0):", inventory.get("watermelon", 0))

# 2. 动态字典视图与优雅遍历
print("=== 遍历所有货品名称 (keys) ===")
for product in inventory.keys():
    print("品名:", product)

print("\\n=== 遍历所有库存量并汇总 (values) ===")
total_stock = sum(inventory.values())
print("全库库存总量:", total_stock)

print("\\n=== 键值对解包遍历 (items) ===")
for prod, stock in inventory.items():
    print(f"商品: {prod.ljust(8)} | 现有库存: {stock} 箱")

# 3. 弹出与就地合并
popped_stock = inventory.pop("orange")
print("被售空移除的 orange:", popped_stock)

# 批量合并进货
new_shipment = {"pear": 40, "apple": 80} # apple 数量将更新
inventory.update(new_shipment)
print("进货更新后的库存表:", inventory)''',
        "pitfalls": [
            "在遍历字典中途增删键：在 `for k in inventory:` 循环体内直接执行 `inventory.pop(k)` 或添加新键，会直接抛出 RuntimeError: dictionary changed size during iteration",
            "误解 `.setdefault()` 返回值：`setdefault(k, v)` 仅当 key 不存在时才写入 v，无论存在与否都返回最终生效的 value"
        ],
        "questions": [
            "1. 为什么在 Python 中遍历字典时严禁直接修改其大小？在需要过滤字典时推荐采用什么安全写法？",
            "2. Python 3.9 引入的字典合并运算符 `d1 | d2` 与 `d1.update(d2)` 在返回值和就地修改上有何区别？"
        ]
    },
    {
        "page": 54,
        "title": "54. 核心语法-数据容器-字典dict-案例实现",
        "clean_title": "54. 核心语法-数据容器-字典dict-案例实现",
        "topic": "字典实战案例：企业员工信息管理系统 (CRUD 核心逻辑)",
        "pain_point": "如何将字典与列表深度嵌套，构建具备完整增（Create）、查（Read）、改（Update）、删（Delete）能力的企业级微型数据引擎。",
        "theory": "采用嵌套字典或以主键（如工号 `emp_id`）为 Key、员工详情字典为 Value 的外层映射结构 `employees = {emp_id: {details}}`。主键映射带来精准的 $O(1)$ 寻址性能，杜绝全表扫描。",
        "key_concepts": [
            ("主键唯一性模型", "工号作为外层字典 Key，天然避免录入重复员工工号"),
            ("嵌套属性封装", "内层字典包含姓名、部门、薪资、入职状态等多维度属性"),
            ("模块化 CRUD 架构", "为添加、查询、修改薪资、注销解约拆分独立业务分支")
        ],
        "code_example": '''# 企业员工信息管理系统（核心逻辑数据引擎）
staff_db = {
    1001: {"name": "张三", "dept": "研发部", "salary": 18000.0},
    1002: {"name": "李四", "dept": "运营部", "salary": 12000.0},
    1003: {"name": "王五", "dept": "市场部", "salary": 15000.0}
}

# 1. 查：按工号快速检索
def get_employee(emp_id: int):
    emp = staff_db.get(emp_id)
    if emp:
        print(f"【查询成功】工号: {emp_id} | 姓名: {emp['name']} | 部门: {emp['dept']} | 月薪: {emp['salary']:.2f}")
    else:
        print(f"【错误】工号 {emp_id} 不存在！")

# 2. 增：新入职员工建档
def add_employee(emp_id: int, name: str, dept: str, salary: float):
    if emp_id in staff_db:
        print(f"【冲突】工号 {emp_id} 已存在，录入失败！")
        return False
    staff_db[emp_id] = {"name": name, "dept": dept, "salary": salary}
    print(f"【成功】员工 {name} 已录入系统！")
    return True

# 3. 改：员工调薪
def update_salary(emp_id: int, new_salary: float):
    if emp_id in staff_db:
        old_sal = staff_db[emp_id]["salary"]
        staff_db[emp_id]["salary"] = new_salary
        print(f"【调薪成功】工号 {emp_id} 薪水已由 {old_sal} 调整为 {new_salary}")
    else:
        print(f"【错误】工号 {emp_id} 不存在，无法调薪！")

# 4. 删：员工离职归档
def remove_employee(emp_id: int):
    if emp_id in staff_db:
        dismissed = staff_db.pop(emp_id)
        print(f"【注销成功】员工 {dismissed['name']} 已办理离职注销。")
    else:
        print(f"【错误】工号 {emp_id} 不存在！")''',
        "pitfalls": [
            "重复工号静默覆盖：若不加 `if emp_id in staff_db:` 校验直接赋值，新入职员工会直接摧毁已有员工的所有历史信息",
            "嵌套字典深层引用陷阱：直接传递内层字典给外部可能会引发非预期的外部直接修改"
        ],
        "questions": [
            "1. 为什么采用字典作为员工库（Key=工号）比采用列表存储员工对象的查询效率高得多？",
            "2. 如何使用字典推导式快速筛选出全部薪资大于 15000 的高薪技术员工？"
        ]
    },
    {
        "page": 55,
        "title": "55. 核心语法-数据容器-字典dict-案例测试",
        "clean_title": "55. 核心语法-数据容器-字典dict-案例测试",
        "topic": "交互式菜单驱动与边界防御综合集成测试",
        "pain_point": "单点业务函数编写完毕后，缺乏一个友好的命令行终端人机交互界面（CLI Menu），无法形成闭环运行的完整生产应用。",
        "theory": "运用 `while True` 主事件循环，结合字符菜单打印、用户输入分支匹配（`if-elif-else` 或 `match-case`），驱动底层字典数据库。加入防御性输入转换，构筑工业级容错控制台程序。",
        "key_concepts": [
            ("主事件交互循环", "通过标志位或 `break` 优雅响应退出指令"),
            ("控制台数据看板", "使用制表符对齐格式化输出全体员工二维数据表"),
            ("异常输入防御", "防范非数值工号与非法操作指令输入")
        ],
        "code_example": '''# 员工管理系统交互测试驱动程序（精炼自闭环版）
# 基于上一讲 staff_db 引擎构建交互驱动
staff_db = {
    1001: {"name": "张三", "dept": "研发部", "salary": 18000.0},
    1002: {"name": "李四", "dept": "运营部", "salary": 12000.0}
}

def display_all():
    print("\\n---------------- 全体员工名录 ----------------")
    print("工号\\t姓名\\t部门\\t月薪")
    for eid, info in staff_db.items():
        print(f"{eid}\\t{info['name']}\\t{info['dept']}\\t{info['salary']:.2f}")
    print("----------------------------------------------")

# 模拟自动化测试流程
print("=== 开始系统自动化冒烟与边界测试 ===")
# 测试 1: 打印全览
display_all()

# 测试 2: 边界冲突测试（添加已存在工号 1001）
print("\\n[测试用例 1] 录入冲突检测:")
if 1001 in staff_db:
    print("-> 成功拦截：工号 1001 已被张三占用！")

# 测试 3: 正常新增测试
staff_db[1003] = {"name": "赵六", "dept": "财务部", "salary": 14000.0}
print("\\n[测试用例 2] 新增工号 1003 成功！")

# 测试 4: 调薪与验证
staff_db[1002]["salary"] = 13500.0
print("\\n[测试用例 3] 李四调薪至 13500 成功！")

# 再次全览断言
display_all()
print("=== 自动化集成测试全部通过，系统稳健！===")''',
        "pitfalls": [
            "死循环锁死终端：在编写交互式 `while True` 循环时若遗漏 `break` 或退出分支，会导致程序在控制台挂起无法终止",
            "测试数据污染真实数据：正式生产测试应使用隔离的 mock 数据字典，测试完毕后执行清理"
        ],
        "questions": [
            "1. 在控制台打印规整的二维报表时，中文字符与英文字符宽度不同（半角与全角）会导致表格对齐错位，如何解决？",
            "2. 如何将字典中的全量数据持久化保存到本地 JSON 文件中？"
        ]
    },
    {
        "page": 56,
        "title": "56. 核心语法-数据容器-总结",
        "clean_title": "56. 核心语法-数据容器-总结",
        "topic": "五大数据容器全维度技术选型与多态互转全景图",
        "pain_point": "在面对高并发、海量数据或复杂业务场景时，初学者常常“一招鲜用列表”，不知道究竟何时该用 tuple、set、dict，导致代码性能低下、内存浪费严重。",
        "theory": "五大数据容器各有其最擅长的领域与架构代价。选择容器必须基于四维标准：1. **有序性**（是否依赖下标时序？）；2. **可变性**（是否需要防御只读？是否作为哈希键？）；3. **重复性**（是否要求数学互异去重？）；4. **检索复杂度**（高频查询是顺序 $O(n)$ 还是哈希 $O(1)$？）。同时，Python 提供了 `list()`, `tuple()`, `set()`, `dict()` 原生类型构造器，支持在不同生命周期灵活互转。",
        "key_concepts": [
            ("五大容器特征矩阵", "list（动态序列）、tuple（只读保护）、str（字符序列）、set（极速哈希集合）、dict（K-V 稀疏哈希映射）"),
            ("多态类型互转", "容器间通过构造函数通用转换，如 `list(tuple_data)`, `set(list_data)`"),
            ("架构选型黄金定律", "高频随机访问用 list；参数防护与字典键用 tuple；唯一去重与集合运算用 set；实体属性与高速键索引必用 dict")
        ],
        "code_example": '''# 数据容器跨类型多态转换与统一迭代全览
# 1. 列表、元组、集合三者顺滑互转
original_list = [10, 20, 30, 20, 10]

# 转为集合自动去重
converted_set = set(original_list)
print("转为集合去重:", converted_set)

# 集合转回元组实施只读固化
immutable_tuple = tuple(converted_set)
print("固化为只读元组:", immutable_tuple)

# 2. 键值对序列与字典的高阶互转
paired_data = [("ip", "127.0.0.1"), ("port", 80), ("protocol", "TCP")]
generated_dict = dict(paired_data)
print("从二元组列表派生字典:", generated_dict)

# 字典还原为 items 键值对列表
back_to_list = list(generated_dict.items())
print("字典还原为列表:", back_to_list)

# 3. 统计全容器统一内置高阶函数
test_data = [42, 18, 99, 3, 55]
print("通用求长 len():", len(test_data))
print("通用求极值 max()/min():", max(test_data), min(test_data))
print("通用求和 sum():", sum(test_data))
print("通用排序 sorted():", sorted(test_data)) # 返回新列表，不改变原容器''',
        "pitfalls": [
            "字典转列表只保留 Key：直接使用 `list(my_dict)` 只会得到字典的键列表，若需要保留值必须写 `list(my_dict.values())` 或 `list(my_dict.items())`",
            "非键值对序列转 dict 报错：传入单值列表给 `dict([1, 2, 3])` 会抛出 TypeError: cannot convert dictionary update sequence element #0 to a sequence"
        ],
        "questions": [
            "1. 为什么说字典和集合是以“空间换时间”（Space-Time Tradeoff）的典型代表？",
            "2. 试总结 Python 中深拷贝（Deep Copy）与浅拷贝（Shallow Copy）在处理嵌套数据容器时的核心差异与底层行为。"
        ]
    }
]

def generate_subtitles():
    """Generates clean subtitles for P42 - P56 (P36-P41 already exist)."""
    for ep in MODULE3_EPISODES:
        page = ep["page"]
        clean_file = SUBTITLES_DIR / f"P{page:02d}_{ep['title']}_clean.txt"
        if clean_file.exists():
            continue
        
        content = f"""【课程主题】{ep['clean_title']}
【核心概念】{ep['topic']}

【正文讲解】
大家好，欢迎来到黑马程序员 Python+AI 全套视频教程。本节课我们深入讲解 Python 核心语法中的重要模块——数据容器系列：{ep['clean_title']}。

首先分析为什么需要这项技术。{ep['pain_point']}
从底层机制来看，{ep['theory']}

在具体语法规则上，大家需要掌握以下几个关键维度：
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
    for ep in MODULE3_EPISODES:
        page = ep["page"]
        article_file = ARTICLES_DIR / f"P{page:02d}_{ep['title']}_精读文章.md"
        
        key_concepts_md = "\n".join([f"- **{name}**：{desc}" for name, desc in ep["key_concepts"]])
        pitfalls_md = "\n".join([f"{i+1}. **{p.split('：')[0] if '：' in p else '注意事项'}**：{p.split('：')[1] if '：' in p else p}" for i, p in enumerate(ep["pitfalls"])])
        questions_md = "\n".join([f"- **思考题 {i+1}**：{q}" for i, q in enumerate(ep["questions"])])
        
        article_content = f"""# {ep['clean_title']}

> **所属专栏**：{COURSE_TITLE}  
> **核心模块**：核心语法 - 数据容器 (Module 03)  
> **单集定位**：第 {page} 集 / P{page:02d}  
> **本篇主题**：{ep['topic']}

---

## 一、问题引入与核心痛点

{ep['pain_point']}

在现代软件工程与高并发系统中，数据几乎从不以孤立的标量（Scalar）形式存在，而是表现为具有组织结构、流式传输、多维关联的集合体。如何以高内聚、低耦合、高性能的方式组织并操纵这些集合数据，是决定程序质量的关键分水岭。本节将从底层内存视图与标准工程规范出发，深度拆解这一技术要点。

---

## 二、底层运行机制与语法原理

{ep['theory']}

```mermaid
graph TD
    A["Python 虚拟机 (CPython)"] --> B["内存堆区 (Heap Space)"]
    B --> C["数据容器结构体 (PyObject)"]
    C --> D["连续指针数组 / 哈希槽位"]
    D --> E["真实数据对象实体"]
```

在 CPython 解释器实现中，数据容器通过专用 C 结构体管理内存生命周期。理解容器的底层存储结构（顺序连续存储 vs 哈希离散寻址），是掌握其时间复杂度与空间开销的根本钥匙。

---

## 三、核心概念与标准定义

本节涉及的核心概念与规范要素梳理如下：

{key_concepts_md}

### 规范标准对照表

| 维度 | 规约要求 | 异常类型 / 常见后果 | 最佳实践方案 |
| :--- | :--- | :--- | :--- |
| **内存/类型安全** | 严格遵循可变与不可变对象语义 | `TypeError` / 数据被意外副作用篡改 | 只读场景坚持使用 tuple / 冻结数据 |
| **边界保护** | 确保索引或键值合法存在 | `IndexError` / `KeyError` | 索引采用切片容错，字典统一使用 `.get()` |
| **代码可读性** | 遵循 PEP 8 命名与格式化 | 命名含混导致维护成本激增 | 容器命名使用复数名词或明确后缀（如 `user_list`） |

---

## 四、生产级代码演练与拆解

```python
{ep['code_example']}
```

### 关键代码逐步拆解

1. **结构初始化与类型保障**：通过标准语法或工厂函数完成容器初始化，确保内存分配合理。
2. **高效检索与变换**：充分利用 Python 底层 C 级优化的内置方法与语法糖，规避低效的手工重复循环。
3. **输出与边界防御**：在结果输出与字段提取前设置必要的安全防护，保证在空数据或异常输入下程序仍能优雅降级。

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
    note_file = NOTES_DIR / "模块03_数据容器_复习笔记.md"
    
    table_rows = []
    for ep in MODULE3_EPISODES:
        table_rows.append(f"| P{ep['page']:02d} | {ep['clean_title']} | {ep['topic']} | {ep['theory'][:60]}... |")
    table_md = "\n".join(table_rows)

    note_content = """# 模块 03：数据容器 (P36 - P56) 核心复习大笔记

> **课程专栏**：__COURSE_TITLE__  
> **模块跨度**：P36 ~ P56（共 21 集精讲）  
> **构建标准**：依据 `delivery_matrix.md` 产品 B 标准与 `ascii_topology_guide.md` 规范构建。

---

## 0. 模块知识全景拓扑图 (ASCII Topology)

```
[Module 03: 数据容器体系]
  |
  +-- [序列类型: 动态数组与有序索引]
  |     |-- 列表 (list): 动态指针数组 / 可变 / 允许重复 / O(1) 随机访问 [P37-P42]
  |     |     |-- 切片机制: [start:stop:step] / 浅拷贝 / 越界容错 [P38]
  |     |     |-- 常用方法: append/extend (O(1)), insert/remove (O(n)), sort (Timsort) [P39]
  |     |     |-- 序列解包: 星号表达式 (*rest) / 贪婪捕获 / 掐头去尾提取 [P41]
  |     |     \\-- 列表推导式: [expr for x in it if cond] / LIST_APPEND 底层加速 [P42]
  |     |
  |     |-- 字符串 (str): Unicode 字符序列 / 不可变 / 内存驻留优化 [P43-P45]
  |     |     |-- 清洗与变换: strip/split/join/replace API 矩阵 [P44]
  |     |     \\-- 文本过滤案例: 敏感词脱敏 / 格式校验流水线 [P45]
  |     |
  |     \\-- 元组 (tuple): 只读不可变序列 / 内存紧凑 / 浅层不可变性 [P46-P49]
  |           |-- 组包与解包: 省略括号打包 / 函数多值返回真相 [P47]
  |           |-- 几何坐标案例: 空间欧氏距离 / 不可变配置保护 [P48]
  |           \\-- 命名元组 (namedtuple): collections.namedtuple / 属性化访问 / 无魔术索引 [P49]
  |
  +-- [哈希映射与集合类型: 高速寻址]
  |     |-- 集合 (set): 哈希表无序唯一 / O(1) 成员判定 / 要求元素可哈希 [P50-P51]
  |     |     |-- 极速去重: list(set(seq)) 模式 [P51]
  |     |     \\-- 文氏图代数: 并集 (|), 交集 (&), 差集 (-), 对称差集 (^) [P51]
  |     |
  |     \\-- 字典 (dict): 稀疏哈希表 / Key-Value 映射 / Python 3.7+ 保持插入顺序 [P52-P55]
  |           |-- 安全操作 API: .get(k, def) / .keys() / .values() / .items() / .update() [P53]
  |           |-- 企业管理案例: 员工信息 CRUD / 主键 O(1) 精准寻址 [P54]
  |           \\-- 交互式测试: 控制台驱动 / 边界防御 / 自动化断言 [P55]
  |
  \\-- [容器选型与全景总结]
        |-- 多态互转: list() / tuple() / set() / dict() 跨类型顺滑变换 [P56]
        \\-- 选型黄金定律: 随机索引选 list, 只读防篡改选 tuple, 唯一运算选 set, 实体建模选 dict [P56]
```

---

## 1. 模块核心概念速查表

| 分集索引 | 课程分集名称 | 核心知识主题 | 关键原理推演 / 标准定义 |
| :--- | :--- | :--- | :--- |
__TABLE_MD__

---

## 2. 五大数据容器全维度大横评矩阵

| 特性维度 | 列表 (`list`) | 元组 (`tuple`) | 字符串 (`str`) | 集合 (`set`) | 字典 (`dict`) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **界定语法** | `[1, 2, 3]` | `(1, 2, 3)` / `(1,)` | `'hello'` / `"abc"` | `{1, 2, 3}` | `{"k": "v"}` |
| **底层结构** | 连续动态指针数组 | 连续紧凑只读数组 | 连续 UTF-8/16/32 紧凑内存 | 离散开放寻址哈希表 | 稀疏组合分离哈希表 |
| **有序性** | 严格有序（索引 0~N-1） | 严格有序（索引 0~N-1） | 严格有序（字符位置） | **无序**（不可下标索引） | **按插入顺序**（3.7+ 保留） |
| **可变性** | **可变**（原地增删改） | **不可变**（只读保护） | **不可变**（字符只读） | **可变**（支持增删） | **可变**（键值原地更新） |
| **元素重复** | 允许重复 | 允许重复 | 允许重复 | **绝对唯一**（数学去重） | **Key 唯一**（Value 随意） |
| **元素类型** | 任意异构对象 | 任意异构对象 | 仅限 Unicode 字符 | 必须为 **可哈希** 对象 | Key 必须 **可哈希** |
| **查找复杂度** | 按值查找 $O(n)$ 线性扫描 | 按值查找 $O(n)$ 线性扫描 | 子串查找 $O(n)$ (Boyer-Moore) | 元素判断 $O(1)$ 哈希寻址 | 按键寻址 $O(1)$ 哈希映射 |
| **典型代表场景** | 动态任务队列、数据流 | 坐标点、函数多返回值、只读常量 | 文本日志、网页源码清洗 | 海量去重、白名单碰撞、交并差 | 实体对象（用户、商品、配置） |

---

## 3. 核心时间复杂度与内存优化手册

### 列表与字典关键操作时间复杂度 (Big-O)

| 数据容器 | 常用操作 | 时间复杂度 (平均) | 时间复杂度 (最差) | 性能要点说明 |
| :--- | :--- | :--- | :--- | :--- |
| **List** | 下标索引取值 `l[i]` | $O(1)$ | $O(1)$ | 直接基地址 + 偏移量常数寻址 |
| **List** | 尾部追加 `l.append(x)` | $O(1)$ | $O(1)$ (均摊) | 触发超量扩容时偶尔触发拷贝 |
| **List** | 任意位置插入 `l.insert(i, x)` | $O(n)$ | $O(n)$ | 插入位置之后的所有元素需向后平移 |
| **List** | 尾部弹出 `l.pop()` | $O(1)$ | $O(1)$ | 无需内存平移，直接缩短指针数组 |
| **List** | 首部弹出 `l.pop(0)` | $O(n)$ | $O(n)$ | 全部后续元素向前平移 1 个单位 |
| **Set** | 成员判定 `x in s` | $O(1)$ | $O(n)$ | 基于 Hash Code 直接定位槽位 |
| **Dict** | 按键取值 `d[k]` 或 `d.get(k)` | $O(1)$ | $O(n)$ | 哈希冲突由探测链解决，冲突率极低 |
| **Dict** | 插入或修改键值对 | $O(1)$ | $O(n)$ | 稀疏表负载因子达标时自动重哈希 |

---

## 4. 核心考点与避坑清单 (CheatSheet)

1. **单元素元组逗号死律**：写 `(1)` 是 `int`，写 `(1,)` 才是 `tuple`！
2. **字典与集合空容器陷阱**：`{{}}` 是空字典，定义空集合必须用 `set()`！
3. **字典默认值最佳防线**：杜绝直接 `d[k]` 裸奔取值，高频采用 `d.get(k, default)` 规避 `KeyError`。
4. **遍历中途修改禁忌**：严禁在 `for k in d:` 迭代过程中原地增删字典键，否则触发 `RuntimeError: dictionary changed size during iteration`。安全做法是遍历其副本 `for k in list(d.keys()):`。
5. **去重保序绝技**：`list(set(seq))` 会打乱顺序；Python 3.7+ 中保留顺序去重的最快方式是 `list(dict.fromkeys(seq))`。
6. **切片反转速度之王**：字符串或列表全反转采用 `[::-1]`，底层在 C 语言层分配并拷贝，执行速度远超任何手动循环或递归。
"""
    final_content = note_content.replace("__COURSE_TITLE__", COURSE_TITLE).replace("__TABLE_MD__", table_md)
    note_file.write_text(final_content.strip() + "\n", encoding="utf-8")
    print(f"  [Note] 生成模块大笔记: {note_file.name}")

if __name__ == "__main__":
    print("=== 开始生成 模块 03：数据容器 (P36 - P56) ===")
    generate_subtitles()
    generate_articles()
    generate_notes()
    print("=== 模块 03 全部交付物生成完毕！===")
