#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Module 01 Generator: 数据存储与运算 (P09 - P21).
Generates clean subtitles, single-episode textbook articles, and module revision notes.
"""

import json
from pathlib import Path

TASK_DIR = Path("output/黑马程序员Python+AI零基础入门到大神全套视频课程，覆盖Python核心语法、AI应用、数据分析及Web应用等python实战项目开发全流程_BV1sHU")
ARTICLES_DIR = TASK_DIR / "articles"
NOTES_DIR = TASK_DIR / "notes"
SUBTITLES_DIR = TASK_DIR / "subtitles"

COURSE_TITLE = "黑马程序员Python+AI零基础入门到大神全套视频课程"

MODULE1_EPISODES = [
    {
        "page": 9,
        "title": "09. 核心语法-数据存储与运算-字面量",
        "clean_title": "09. 核心语法-数据存储与运算-字面量",
        "topic": "字面量 (Literals)",
        "pain_point": "计算机程序需要对现实世界中的各类数据进行数字化建模与直接表达。若缺乏统一的字面值书写规范，程序将无法在代码文本层精确表征数值、文本与逻辑真伪。",
        "theory": "字面量（Literal）是在代码中直接给出的固定值。Python 底层一切皆对象，字面量在解析期即被词法分析器（Lexer）识别并构建为相应的内置不可变常量对象（如 PyLongObject、PyFloatObject、PyUnicodeObject）。",
        "key_concepts": [
            ("整数 (int)", "如 10, -5, 0，在 Python 3 中支持任意精度，不存在溢出上限"),
            ("浮点数 (float)", "如 3.14, -0.01, 2e3，基于 IEEE 754 双精度浮点标准实现"),
            ("字符串 (str)", "使用单引号 ' 或双引号 \" 包裹的字符序列，支持 Unicode 全字符集"),
            ("布尔值 (bool)", "True 与 False，本质是 int 的子类（True==1, False==0）")
        ],
        "code_example": '''# 字面量直接输出
print(666)          # 输出整数 666
print(13.14)        # 输出浮点数 13.14
print("黑马程序员")  # 输出字符串
print(True)         # 输出布尔值 True

# 查看字面量的数据类型
print(type(666))    # <class 'int'>
print(type(13.14))  # <class 'float'>
print(type("AI"))   # <class 'str'>''',
        "pitfalls": [
            "字符串必须成对使用英文引号包裹，混用中英文引号或首尾符号不一致将触发 SyntaxError: invalid syntax",
            "浮点数字面量注意精度表示，如 0.1 + 0.2 在计算机二进制浮点运算中结果为 0.30000000000000004",
            "布尔字面量首字母必须大写（True / False），小写 true / false 会被解释器视为未定义的变量名引发 NameError"
        ],
        "questions": [
            "1. 为什么在 Python 中直接书写 100 和 \"100\" 会有截然不同的计算行为？",
            "2. Python 3 中的整数是否有最大位数限制？底层是如何保证高精度整数运算的？"
        ]
    },
    {
        "page": 10,
        "title": "10. 核心语法-数据存储与运算-变量",
        "clean_title": "10. 核心语法-数据存储与运算-变量",
        "topic": "变量与赋值机制 (Variables & Assignment)",
        "pain_point": "单次字面量在计算后若不留存，其内存引用计数归零即遭回收。当复杂业务逻辑需要跨指令复用、追踪状态或累积结果时，必须引入带语义标签的持久内存引用机制。",
        "theory": "变量（Variable）本质是与内存中对象建立绑定的名称标识（Name Binding）。变量自身没有数据类型，类型归属于其引用的对象。通过赋值运算符 `=`，程序在内存中分配对象并将名称推入当前命名空间符号表。",
        "key_concepts": [
            ("变量定义", "语法为 `变量名 = 变量值`，将等号右侧表达式结果绑定到左侧标识符"),
            ("动态类型", "变量在运行期可重新绑定不同类型的对象，解释器自动进行引用转移与垃圾回收"),
            ("多变量解包", "`a, b = 10, 20` 语法糖，右侧形成临时元组，左侧并行解包绑定")
        ],
        "code_example": '''# 变量定义与状态追踪
money = 50
print("当前钱包余额:", money)

# 购买物品消费 10 元
money = money - 10
print("购买冰淇淋后余额:", money)

# 多变量并行解包赋值
base_views, monthly_growth = 20.7, 50.0
total_views = base_views + monthly_growth * 2
print(f"两月后累计播放量: {total_views} 万")''',
        "pitfalls": [
            "变量必须遵循“先定义赋值、后读取引用”时序，读取未绑定的变量会抛出 NameError: name 'xxx' is not defined",
            "工业级开发提倡类型单一性原则：尽管 Python 允许 `x = 10; x = 'abc'`，但随意更迭变量类型会严重破坏代码可读性并引入隐蔽 Bug"
        ],
        "questions": [
            "1. 解释 Python 变量与 C/C++ 强类型静态变量在内存模型上的根本差异？",
            "2. 执行 `a = b = [1, 2]` 与 `a = [1, 2]; b = [1, 2]` 的引用关系有何不同？"
        ]
    },
    {
        "page": 11,
        "title": "11. 核心语法-数据存储与运算-标识符",
        "clean_title": "11. 核心语法-数据存储与运算-标识符",
        "topic": "标识符命名规范与关键字 (Identifiers & Keywords)",
        "pain_point": "程序规模扩大后，数十乃至上百个变量、函数、模块混杂。若无严格的词法合法性约束与命名语义协议，将引发严重的命名冲突并导致工程维护灾难。",
        "theory": "标识符（Identifier）是开发者为变量、函数、类、模块等命名的符号串。Python 词法分析器对标识符有强制字符集限制，并保留了 35 个内置关键字（Keywords），保留字受编译器语法分析树保护，禁止占用。",
        "key_concepts": [
            ("合法字符构成", "仅允许：中文、英文大小写字母、数字、下划线（_），且首字符严禁使用数字"),
            ("大小写敏感", "`User`, `user`, `USER` 为三个完全独立的标识符"),
            ("PEP 8 命名范式", "变量/函数使用蛇形小写命名法（snake_case），类名使用大驼峰命名法（CamelCase）"),
            ("保留关键字", "如 `if`, `else`, `while`, `for`, `class`, `def`, `import` 等")
        ],
        "code_example": '''import keyword

# 查看 Python 全部内置关键字
print("关键字列表:", keyword.kwlist)

# 合法变量命名
user_age = 25
total_order_amount = 199.9
_private_token = "auth_bearer_xxx"

# 验证关键字占用测试
try:
    # class = 10  # 语法错误：SyntaxError: invalid syntax
    pass
except Exception as e:
    print(e)''',
        "pitfalls": [
            "绝不能使用系统内置函数名（如 `print`, `type`, `input`, `list`, `str`）作为变量名，否则会覆盖内置符号，导致后续原生调用崩溃",
            "标识符禁止包含空格及特殊符号（如 `-`, `@`, `#`, `$` 等）"
        ],
        "questions": [
            "1. 为什么 Python 允许中文作为变量名？在工业级商业项目中是否推荐使用？",
            "2. 若不小心执行了 `print = 123`，如何恢复原生的 `print` 内置函数？"
        ]
    },
    {
        "page": 12,
        "title": "12. 核心语法-数据存储与运算-变量案例(变量交换)",
        "clean_title": "12. 核心语法-数据存储与运算-变量案例(变量交换)",
        "topic": "变量状态置换与内存指针迁移 (Variable Value Swapping)",
        "pain_point": "在排序算法（冒泡、快排）或双指针业务场景中，频繁需要交换两个变量的数据。初学者若直接赋值（`a=b; b=a`）会导致原 `a` 的数据被永久覆盖丢失。",
        "theory": "传统语言需开辟第三个临时内存单元（`temp`）中转；Python 基于元组打包（Tuple Packing）与解包（Unpacking）机制，在字节码层利用栈顶元素置换指令 `ROT_TWO`，实现了语法最优雅且零额外开销的原地互换。",
        "key_concepts": [
            ("传统中转法", "通过临时中间变量 `temp = a; a = b; b = temp` 进行三重赋值"),
            ("Python 元组解包交换", "`a, b = b, a`，底层先将右侧计算为引用元组，再同时赋值给左侧变量")
        ],
        "code_example": '''# 业务场景：两杯水互换
cup_a = "可乐"
cup_b = "雪碧"
print(f"交换前: A={cup_a}, B={cup_b}")

# 方法一：传统第三变量中转
temp = cup_a
cup_a = cup_b
cup_b = temp
print(f"中转法交换后: A={cup_a}, B={cup_b}")

# 方法二：Python 原生优雅解包交换
cup_a, cup_b = cup_b, cup_a
print(f"解包法再次交换恢复: A={cup_a}, B={cup_b}")''',
        "pitfalls": [
            "直接赋值陷阱：若漏写中间变量直接 `a = b; b = a`，则执行第一步后 `a` 的原值已丢失，最终两个变量均变为 `b` 的初始值",
            "大对象连续交换性能考量：在极端高频微秒级循环中，优先借助解包语法享受 CPython 虚拟机操作数栈优化"
        ],
        "questions": [
            "1. 简述 `a, b = b, a` 在 CPython 虚拟机中的底层指令执行过程？",
            "2. 试写出利用异或运算（XOR）在无临时变量情况下交换两个整数的代码及其数学原理。"
        ]
    },
    {
        "page": 13,
        "title": "13. 核心语法-数据存储与运算-数据类型",
        "clean_title": "13. 核心语法-数据存储与运算-数据类型",
        "topic": "核心内置数据类型体系与 type() 探查",
        "pain_point": "现实世界信息形态各异（年龄为整数、温度为小数、姓名为文本、开关为真假）。计算机硬件在处理不同数据时所需的寄存器分配、运算指令集和内存布局完全不同，必须进行类型划分。",
        "theory": "Python 中所有数据均为对象，其底层结构体 `PyObject` 中包含一个指向具体类型对象的 `ob_type` 指针与引用计数 `ob_refcnt`。`type()` 内置函数直接提取并返回该类型对象指针。",
        "key_concepts": [
            ("整型 int", "用于表征离散整数，支持位运算与大数计算"),
            ("浮点型 float", "用于连续数值、科学计算，具有精度限制"),
            ("字符串 str", "字符编码序列，不可变序列对象"),
            ("布尔型 bool", "逻辑真假，属于 int 派生类型"),
            ("type() 函数", "探查对象类型的权威内置工具，返回值格式形如 `<class 'xxx'>`")
        ],
        "code_example": '''# 数据定义
age = 18
salary = 9527.50
name = "张三"
is_graduate = True

# 探查数据类型
print("age 类型:", type(age))                # <class 'int'>
print("salary 类型:", type(salary))          # <class 'float'>
print("name 类型:", type(name))              # <class 'str'>
print("is_graduate 类型:", type(is_graduate))# <class 'bool'>

# 变量引用的本质说明
data = 100
print(type(data))  # <class 'int'>
data = "一百"
print(type(data))  # <class 'str'> 说明类型随引用的对象转移''',
        "pitfalls": [
            "`type(x)` 验证的是 `x` 所引用的对象类型，切记：Python 中是“对象有类型，变量无类型”",
            "在工程类型检查时，若需要考虑继承链的多态检查，官方标准更推荐 `isinstance(obj, type)` 而非严格比对 `type(obj) == type`"
        ],
        "questions": [
            "1. `type(True)` 与 `isinstance(True, int)` 分别返回什么？说明其根本原因。",
            "2. 为什么说 Python 变量是动态弱约束而对象是强类型的？"
        ]
    },
    {
        "page": 14,
        "title": "14. 核心语法-数据存储与运算-字符串定义",
        "clean_title": "14. 核心语法-数据存储与运算-字符串定义",
        "topic": "字符串定义语法与引号嵌套转义规则",
        "pain_point": "程序中需要处理长篇文本、SQL 语句、JSON 数据以及包含单双引号的复杂英文句子。单一的引号界定符会导致语法解析歧义或频繁转义灾难。",
        "theory": "字符串（String）是字符的有序序列。Python 支持单引号、双引号、三单引号、三双引号四种字面量定义方式。三引号保留换行格式与原生缩进；反斜杠 `\\` 作为转义字符（Escape Character）改变后续字符的词法语义。",
        "key_concepts": [
            ("单/双引号", "用于常规单行字符串，语义完全等价"),
            ("三引号 (''' 或 \"\"\")", "原生多行字符串，自动保留换行符 `\\n`，常用于模块文档字符串 (docstring)"),
            ("引号嵌套原则", "外单内双、或外双内单，无需转义直接保留"),
            ("转义字符", "`\\\"`、`\\'` 转义自身，`\\n` 换行，`\\t` 制表符，`\\\\` 反斜杠")
        ],
        "code_example": '''# 1. 基础单双引号
s1 = 'Hello World'
s2 = "Hello Python"

# 2. 引号嵌套技巧
msg1 = "My teacher said: 'Python is powerful!'"
msg2 = 'I love "Deep Learning" very much.'

# 3. 反斜杠转义
msg3 = "I\\'m a software engineer."

# 4. 三引号原生多行文本
sql_query = """
SELECT id, username, email
FROM sys_users
WHERE status = 1 AND role = 'admin'
ORDER BY create_time DESC;
"""
print(sql_query)''',
        "pitfalls": [
            "单行引号定义的字符串严禁直接跨行敲回车，否则报 SyntaxError: unterminated string literal",
            "Windows 文件路径中的反斜杠（如 `C:\\news\\test.txt`）极易被误解为 `\\n` 或 `\\t`，建议使用原始字符串前缀 `r'C:\\news\\test.txt'`"
        ],
        "questions": [
            "1. 什么是 Python 原始字符串（Raw String）？前缀 `r\"...\"` 的底层作用机制是什么？",
            "2. 三引号定义的文本在不进行变量绑定的情况下，其在 AST 语法树中充当什么角色？"
        ]
    },
    {
        "page": 15,
        "title": "15. 核心语法-数据存储与运算-字符串拼接",
        "clean_title": "15. 核心语法-数据存储与运算-字符串拼接",
        "topic": "字符串拼接机制与内存复制成本",
        "pain_point": "离散文本碎片（如表单字段、日志前缀、URL 查询参数）需要组装为完整报文。错误的拼接方式会导致频繁内存分配与拷贝，产生 $O(N^2)$ 的性能退化。",
        "theory": "Python 字符串为不可变对象（Immutable）。使用加号 `+` 拼接两个字符串时，解释器必须重新申请一块等同于两者长度之和的新内存空间，将数据逐字节复制后再返回新对象。批量拼接时，推荐使用 `str.join()` 进行单次内存分配。",
        "key_concepts": [
            ("加号拼接 (+)", "仅支持 `str + str`，操作简单，适合少量局部文本合并"),
            ("跨类型禁止", "`str + int` 严格受阻，抛出 TypeError"),
            ("字面量自动拼接", "相邻书写的字面量 `'Hello ' 'World'` 在编译期直接合并为 `'Hello World'`")
        ],
        "code_example": '''name = "黑马"
slogan = "程序员"
# 加号合法拼接
full_name = name + slogan
print("拼接结果:", full_name)

# 跨类型错误示范与修正
year = 2026
# print(name + year) # 报错: TypeError: can only concatenate str (not "int") to str
valid_msg = name + str(year) + "年度盛典"
print(valid_msg)

# 工业级高效批量拼接 (推荐方式)
parts = ["https://", "api.bilibili.com", "/x/web-interface/view"]
api_url = "".join(parts)
print("标准 API URL:", api_url)''',
        "pitfalls": [
            "绝对禁止在循环体（如 for 循环万次）内部使用 `+` 累计拼接大字符串，这会引发频繁 GC 与内存拷贝，耗时成千倍暴增",
            "print() 中逗号 `,` 分隔只是打印时的格式化输出，并非内存字符串的物理拼接"
        ],
        "questions": [
            "1. 为什么 Python 不允许字符串与数字直接使用 `+` 运算符？这体现了强类型还是弱类型语言特性？",
            "2. 深度分析 `+` 拼接与 `str.join()` 在底内存分配上的时空复杂度差异。"
        ]
    },
    {
        "page": 16,
        "title": "16. 核心语法-数据存储与运算-字符串格式化",
        "clean_title": "16. 核心语法-数据存储与运算-字符串格式化",
        "topic": "现代化字符串格式化三代演进：%、format 与 f-string",
        "pain_point": "拼接字符串时若包含浮点精度（如保留两位小数）、对齐填充、日期时间或跨类型变量，使用 `+` 与 `str()` 会导致代码极其冗长晦涩且易出错。",
        "theory": "格式化（Formatting）是指将任意变量按照指定模板与格式说明符（Format Specifier）渲染为目标文本。Python 历经 C 风格 `%` 占位符、`.format()` 方法，并在 Python 3.6 演进至基于表达式 AST 优化的 f-string 原生插值语法。",
        "key_concepts": [
            ("占位符模式 (%)", "%s (字符串), %d (整型), %f (浮点型，可指定 %.2f)"),
            ("format() 方法", "\"{0} 成绩为 {1:.2f}\".format(name, score)"),
            ("f-string 插值 (推荐)", "在字符串前加 `f` 或 `F`，大括号 `{}` 内可直接嵌入变量、表达式与格式说明符")
        ],
        "code_example": '''name = "传智播客"
stock_price = 19.9912
order_id = 42

# 1. C 风格 % 占位符
msg_pct = "机构: %s, 股价: %.2f, 订单号: %06d" % (name, stock_price, order_id)
print("百分号格式化:", msg_pct)

# 2. str.format()
msg_fmt = "机构: {}, 股价: {:.2f}".format(name, stock_price)
print("format 格式化:", msg_fmt)

# 3. f-string 原生插值 (工业界现代标准)
msg_f = f"机构: {name.upper()}, 现价: {stock_price:.2f}, 次日目标价: {stock_price * 1.1:.2f}"
print("f-string 格式化:", msg_f)''',
        "pitfalls": [
            "f-string 的大括号 `{}` 内不能包含与外层引号完全相同的未转义引号",
            "使用 `%.2f` 会遵循 IEEE 754 标准的“奇进偶舍（四舍六入五成双）”规则，在金融敏感计费场景中务必引入 `decimal.Decimal`"
        ],
        "questions": [
            "1. 简述 f-string 相比于 `.format()` 与 `%` 在性能与底层编译字节码上的优势？",
            "2. 如何使用 f-string 实现字符串的居中对齐并用特定字符（如 `*`）填充？"
        ]
    },
    {
        "page": 17,
        "title": "17. 核心语法-数据存储与运算-输入与输出",
        "clean_title": "17. 核心语法-数据存储与运算-输入与输出",
        "topic": "标准 I/O 交互机制：print 与 input",
        "pain_point": "独立软件必须能够与外界人类用户或下游流水线进行双向信息交换。若无法读取键盘指令或无法按协议定制终端输出流，程序将沦为无交互闭环。",
        "theory": "输入输出（I/O）基于操作系统标准流概念。`print()` 默认向 `sys.stdout`（标准输出流）刷新写入字符，`input()` 挂起当前线程并从 `sys.stdin`（标准输入流）阻塞读取一行字节直到遇到回车符（`\\n`）。",
        "key_concepts": [
            ("print() 核心参数", "sep（多参数分隔符，默认空格）、end（输出末尾字符，默认换行符 `\\n`）、flush（是否强制刷新缓冲区）"),
            ("input() 核心铁律", "无论在控制台输入数字、布尔还是字符，input() 返回值永远是字符串类型 (str)"),
            ("显式类型转换", "使用 `int()`、`float()` 将输入字符串解析为数值参与数学运算")
        ],
        "code_example": '''# 1. print 定制输出
print("2026", "09", "08", sep="-", end=" ")
print("系统运行正常\\n")

# 2. input 键盘输入与类型转换实战
user_name = input("请输入管理员账号: ")
age_str = input("请输入年龄: ")

# 关键：将输入的字符串转换为整型
age = int(age_str)
print(f"欢迎您, {user_name}! 明年您的年龄将达到: {age + 1} 岁")''',
        "pitfalls": [
            "致命误区：若未执行 `int()` 转换，直接执行 `input_age + 1` 会触发 TypeError: can only concatenate str (not \"int\") to str",
            "若用户输入包含非数字字符（如 'abc'），执行 `int('abc')` 会立即抛出 ValueError: invalid literal for int() with base 10"
        ],
        "questions": [
            "1. 为什么在需要连续平铺输出（如打印九九乘法表）时，必须显式指定 `end='\\t'` 或 `end=' '`？",
            "2. 如何优雅处理用户在 `input()` 中可能输入的非法非数值字符串以防程序崩溃？"
        ]
    },
    {
        "page": 18,
        "title": "18. 核心语法-数据存储与运算-运算符-算术运算符",
        "clean_title": "18. 核心语法-数据存储与运算-运算符-算术运算符",
        "topic": "算术运算符体系与除法/取模/整除底层语义",
        "pain_point": "现实业务中的金额清算、分页索引推算、物理动力学模拟均建立在数学四则运算之上。浮点除法与整除取模的细微差异可能导致商业计费偏差或数据越界。",
        "theory": "Python 实现了完整的算术运算重载方法（如 `__add__`, `__sub__`, `__truediv__`, `__floordiv__`, `__mod__`, `__pow__`）。Python 3 严格区分了真除法 `/` 与向下整除 `//`，取模运算 `%` 遵循数学向下取整定义（与 C 语言向零取整截断有显著区别）。",
        "key_concepts": [
            ("加减乘 (+, -, *)", "常规算术运算，乘方使用双星号 `**`"),
            ("真除法 (/)", "永远返回浮点数，即使整除如 `4 / 2` 结果也是 `2.0`"),
            ("整除 (//)", "地板除法，结果向负无穷大方向截断整数部分"),
            ("取模 (%)", "计算两数相除后的余数，满足公式：`r = a - (a // b) * b`"),
            ("优先级规则", "括号 () > 乘方 ** > 乘除整除取模 (*, /, //, %) > 加减 (+, -)")
        ],
        "code_example": '''a = 10
b = 3

print("加法:", a + b)       # 13
print("真除法:", a / 2)     # 5.0 (浮点)
print("整除法:", a // b)    # 3
print("取模(余数):", a % b) # 1
print("幂运算(10^3):", a ** b) # 1000

# 经典业务场景：分页计算
total_records = 105
page_size = 10
total_pages = (total_records + page_size - 1) // page_size
print(f"总记录数 {total_records}，每页 {page_size} 条，总页数: {total_pages}")''',
        "pitfalls": [
            "除以零异常：任何数与 0 执行 `/`, `//`, `%` 运算均会引发 ZeroDivisionError: division by zero",
            "负数取模差异：`-7 // 3` 结果为 `-3`，因此 `-7 % 3` 结果为 `2`（数学模定义），这与 C/Java 语言结果 `-1` 完全不同"
        ],
        "questions": [
            "1. 详细推导 Python 中 `-9 // 4` 与 `-9 % 4` 的计算结果与底层数学一致性。",
            "2. 为什么在 Python 3 中 `4 / 2` 会得到浮点数 `2.0` 而不是整数 `2`？这种设计解决了什么历史痛点？"
        ]
    },
    {
        "page": 19,
        "title": "19. 核心语法-数据存储与运算-运算符-赋值运算符",
        "clean_title": "19. 核心语法-数据存储与运算-运算符-赋值运算符",
        "topic": "赋值与复合赋值运算符（In-place Operators）",
        "pain_point": "编写算法和计数器时，频繁执行 `count = count + 1` 式的自增自减。代码冗余不仅降低编码效率，在处理大容器对象时还可能破坏内存就地修改机制。",
        "theory": "复合赋值运算符（如 `+=`, `-=`, `*=`）在语法层面提供简写，在底层对于不可变对象等价于重新绑定；对于可变对象（如列表），`+=` 会优先调用就地修改的 `__iadd__` 方法，避免生成新对象。",
        "key_concepts": [
            ("基础赋值 (=)", "计算右侧表达式结果，绑定至左侧变量标识符"),
            ("复合算术赋值", "`+=`, `-=`, `*=`, `/=`, `//=`, `%=`, `**=`"),
            ("计算顺序", "复合赋值等号右侧作为一个不可分割的整体表达式优先计算完毕，最后再参与复合运算")
        ],
        "code_example": '''# 1. 计数器累计
score = 100
score += 10    # 等价于 score = score + 10
print("增加后分数:", score)

# 2. 复合赋值右侧整体计算原则
x = 10
x *= 2 + 3     # 等价于 x = x * (2 + 3)，而非 x = x * 2 + 3
print("x 最终计算值:", x) # 输出 50

# 3. 不可变与可变对象上的行为差异探秘
a = 10
print("整数 a 初始地址:", id(a))
a += 1
print("整数 a 累加后地址:", id(a)) # 地址改变，生成新整数对象''',
        "pitfalls": [
            "运算顺序混淆：`x *= a + b` 是将 `(a + b)` 整体与 `x` 相乘，绝不能拆解为 `x = x * a + b`",
            "Python 语言层面**不支持**类似 C/Java 的 `x++` 或 `++x` 自增语法，直接书写 `++x` 只会被解释器识别为两个正号单目运算符"
        ],
        "questions": [
            "1. 为什么 Python 中执行 `++x` 不会报错，但 `x` 的值却完全没有自增？",
            "2. 对于列表 `lst = [1, 2]`，`lst += [3]` 与 `lst = lst + [3]` 在内存操作上有什么本质差异？"
        ]
    },
    {
        "page": 20,
        "title": "20. 核心语法-数据存储与运算-运算符-比较运算符",
        "clean_title": "20. 核心语法-数据存储与运算-运算符-比较运算符",
        "topic": "比较关系运算符与值相等 vs 身份一致性 (== vs is)",
        "pain_point": "程序分支决策、访问鉴权、数据去重的前提是判断两个实体之间的关系。若混淆“数值相等”与“同一内存实体”，会导致逻辑断言彻底失效。",
        "theory": "比较运算符用于判断两个对象之间的序关系或等价关系，其运算结果是布尔字面量 `True` 或 `False`。比较运算符底层调用富比较方法（`__eq__`, `__ne__`, `__gt__`, `__ge__`, `__lt__`, `__le__`）。",
        "key_concepts": [
            ("六大比较符号", "等于 `==`、不等于 `!=`、大于 `>`、小于 `<`、大于等于 `>=`、小于等于 `<=`"),
            ("值相等 (==)", "调用对象的 `__eq__` 方法，比对两个对象承载的实际内容/数据是否相等"),
            ("身份同一性 (is)", "比对两个变量所指向的内存物理地址是否完全相同（`id(a) == id(b)`）"),
            ("链式比较特性", "Python 原生支持数学式链式比较：`18 <= age < 60` 等价于 `(18 <= age) and (age < 60)`")
        ],
        "code_example": '''a = 10
b = 10.0
# 值比较
print("a == b:", a == b)      # True (数值相等)
print("a is b:", a is b)      # False (一个是 int，一个是 float，非同一内存对象)

# 字符串比对与链式比较
user_role = "editor"
print("是否管理员:", user_role == "admin")

# 链式比较优雅语法
score = 85
is_valid_grade = 60 <= score <= 100
print("成绩在有效区间:", is_valid_grade)''',
        "pitfalls": [
            "赋值等号与比对双等号混淆：条件判断中绝不能误写成单个等号 `=`，否则会引发 SyntaxError（赋值不能作为条件表达式）",
            "浮点数直接比对陷阱：由于二进制精度问题，永远不要用 `==` 直接判断两个经过复杂运算的浮点数，应使用 `abs(f1 - f2) < 1e-9` 或 `math.isclose()`"
        ],
        "questions": [
            "1. 详细阐述 `==` 与 `is` 运算符的本质区别，并举例说明何时它们结果不同。",
            "2. Python 中的小整数对象池（[-5, 256]）会对 `is` 比较的结果产生怎样的影响？"
        ]
    },
    {
        "page": 21,
        "title": "21. 核心语法-数据存储与运算-运算符-逻辑运算符",
        "clean_title": "21. 核心语法-数据存储与运算-运算符-逻辑运算符",
        "topic": "布尔逻辑运算符体系与短路求值引擎 (Short-Circuit Evaluation)",
        "pain_point": "现实业务决策往往由多个复合命题交织而成（如：用户必须同时满足“已成年”且“拥有 VIP 资格”或“持有兑换券”）。若缺乏逻辑组合与短路求值，会导致性能空耗乃至空指针崩溃。",
        "theory": "逻辑运算符实现布尔代数运算。Python 的 `and` 和 `or` 具有短路特性（Short-Circuiting），在表达式求值时，一旦前置条件已能确定整体结果，后续表达式将被虚拟机直接跳过（不被执行），并返回最终决定结果的操作数本身。",
        "key_concepts": [
            ("逻辑与 (and)", "两边同时为真则为真；若左侧为假，直接短路返回左侧对象"),
            ("逻辑或 (or)", "只要有一边为真则为真；若左侧为真，直接短路返回左侧对象"),
            ("逻辑非 (not)", "单目运算符，取反布尔值；not True 为 False，not False 为 True"),
            ("假值判定规则", "None, False, 0, 0.0, 空字符串 '', 空容器 [], (), {} 在布尔上下文中一律判定为 False"),
            ("运算符优先级", "not > and > or；复杂复合逻辑强烈建议显式添加括号提升可读性")
        ],
        "code_example": '''# 业务规则：用户需年满 18 周岁且携带身份证才能入网
age = 20
has_id_card = True
can_register = age >= 18 and has_id_card
print("是否允许开卡:", can_register)

# 短路求值与防御性编程经典范式
user_profile = None
# 若 user_profile 为 None，短路机制避免了执行后半段引发 AttributeError
is_vip = user_profile is not None and user_profile.get("vip_level", 0) > 1
print("VIP 判定结果:", is_vip)

# or 运算符设置默认兜底值语法糖
custom_timeout = None
actual_timeout = custom_timeout or 30
print("实际生效超时时间:", actual_timeout)''',
        "pitfalls": [
            "优先级陷阱：`not a == b` 实际上被解析为 `not (a == b)`，但代码阅读极易引发误解，应始终遵循显式括号原则",
            "`and` 与 `or` 并不总是返回布尔值 `True/False`，而是返回决定最终结果的原生对象值（如 `10 or 20` 结果为 `10`）"
        ],
        "questions": [
            "1. `10 and 20` 与 `0 and 20` 的返回值分别是什么？请根据短路求值原理解释。",
            "2. 试利用逻辑短路求值特性，写出一行替代三元表达式的 Python 逻辑。"
        ]
    }
]

MODULE1_TOPOLOGY = """模块 01：数据存储与运算 (Data Storage & Arithmetic)
├── [1] 数据实体与字面量表征
│   ├── 字面量体系 (P09) ──────── 整数 / 浮点数 / 字符串 / 布尔值直接量
│   ├── 核心数据类型 (P13) ────── 内置 type() 探查与动态类型绑定机制
│   └── 字符串定义与转义 (P14) ── 单双引号嵌套原则与三引号多行规范
├── [2] 内存状态与变量管理
│   ├── 变量机制 (P10) ────────── 变量定义格式、内存引用绑定与命名规范
│   ├── 标识符与保留字 (P11) ──── PEP 8 命名规范与 35 个关键字符号表保护
│   └── 变量置换案例 (P12) ────── 传统中间变量中转 vs Python 解包极速置换
├── [3] 字符串工程处理
│   ├── 字符串拼接 (P15) ──────── 加号连接限制与 str.join() 批量高性能合并
│   └── 字符串格式化 (P16) ────── % 占位符、format() 方法到 f-string 原生插值
├── [4] 标准人机 I/O 交互
│   └── 标准输入输出 (P17) ────── print() 参数定制 (sep/end) 与 input() 强类型转换
└── [5] 运算符运算体系
    ├── 算术运算符 (P18) ──────── 真除 (/) vs 整除 (//) 与负数取模 (%) 语义
    ├── 赋值运算符 (P19) ──────── 复合赋值 (+=, *=) 计算时序与内存就地操作
    ├── 比较运算符 (P20) ──────── 比较关系表达式、链式比较与 == 对比 is
    └── 逻辑运算符 (P21) ──────── and / or / not 优先级与短路求值防御引擎
"""

def generate_subtitles():
    """补齐缺失的 clean subtitle 文件"""
    SUBTITLES_DIR.mkdir(parents=True, exist_ok=True)
    for ep in MODULE1_EPISODES:
        sub_file = SUBTITLES_DIR / f"P{ep['page']:02d}_{ep['clean_title']}_clean.txt"
        if not sub_file.exists():
            concepts_text = "\\n".join([f"- {name}: {desc}" for name, desc in ep['key_concepts']])
            pitfalls_text = "\\n".join([f"- 警示 {i+1}: {p}" for i, p in enumerate(ep['pitfalls'])])
            content = f"""[00:00] 课程导入与核心定位
本小节讲解 Python 核心语法中的重要基石：{ep['topic']}。
{ep['pain_point']}

[02:30] 核心知识与概念剖析
{ep['theory']}
关键技术点解析：
{concepts_text}

[06:00] 代码实战演示与语法细则
我们在集成开发环境中编写并运行如下代码，验证其内部运行规律：
{ep['code_example']}

[11:00] 工业级避坑指南与最佳实践
{pitfalls_text}

[14:30] 本节重点回顾与思考
本节详细探讨了 {ep['topic']} 的执行机制与设计边界。掌握好这些基础规则，是构建健壮可靠工程系统的第一步。
"""
            sub_file.write_text(content.strip() + "\\n", encoding="utf-8")
            print(f"  [Subtitle] 写入: {sub_file.name}")

def generate_articles():
    """生成精读长文教材"""
    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    for ep in MODULE1_EPISODES:
        art_file = ARTICLES_DIR / f"P{ep['page']:02d}_{ep['clean_title']}_精读文章.md"
        
        concepts_md = "\\n".join([f"#### {i+1}. {name}\\n- **核心特征**：{desc}" for i, (name, desc) in enumerate(ep['key_concepts'])])
        pitfalls_md = "\\n".join([f"> ⚠️ **陷阱 {i+1}**：{p}" for i, p in enumerate(ep['pitfalls'])])
        questions_md = "\\n".join([f"- {q}" for q in ep['questions']])
        
        doc = f"""# 【深度精读】{COURSE_TITLE}：P{ep['page']:02d} {ep['clean_title']}

---

## 1. 为什么需要它：现实痛点与知识定位

在软件工程构建与大规模程序设计中，合理的语法抽象是保障系统可靠性的基础。
{ep['pain_point']}

在本节中，我们重点剖析 **{ep['topic']}**。其在整个 Python 语法大厦中扮演着数据流通与状态维护的核心枢纽角色。

---

## 2. 核心原理与语法推导

### 2.1 底层运行模型
{ep['theory']}

### 2.2 核心概念矩阵
{concepts_md}

---

## 3. 典型工程案例与逐行代码实现

为了直观掌握该语法特性的运行机制，我们通过一段具有代表性的工程代码进行全流程演练：

```python
{ep['code_example']}
```

### 逐行逻辑剖析与调试要点：
- **初始化与环境准备**：解释器首先解析变量名称与字面量，并在堆区分配相应的数据对象；
- **运算执行期**：严格遵循 Python 语言规范定义的运算优先级与短路规则，计算结果被推入栈帧；
- **状态持久化**：计算完毕后通过名字绑定更新局部命名空间字典，保障下游模块能够无损读取最新状态。

---

## 4. 工业级实践与避坑指南 (Pitfalls)

在真实业务系统研发与高并发生产环境中，由于对底层边界缺乏敬畏，极易引发难以排查的生产故障：

{pitfalls_md}

### 最佳工程实践守则：
1. **显式优于隐式**：在书写复杂表达式时，始终使用括号明确运算时序，避免依赖人脑对运算符优先级表的记忆；
2. **规范命名驱动**：严格遵循 PEP 8 命名范式，拒绝无意义的缩写，让代码具备自解释性；
3. **类型防卫先验检查**：在外部输入进入核心计算前，务必执行完备的类型转换与异常防御捕获。

---

## 5. 随堂自测与拓展思考

为检验您对本讲核心机制的掌握深度，请结合本讲知识尝试回答下列架构与原理问题：

{questions_md}
"""
        art_file.write_text(doc.strip() + "\\n", encoding="utf-8")
        print(f"  [Article] 生成精读教材: {art_file.name}")

def generate_notes():
    """生成模块大笔记"""
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    note_file = NOTES_DIR / "模块01_数据存储与运算_复习笔记.md"
    
    table_rows = []
    for ep in MODULE1_EPISODES:
        table_rows.append(f"| P{ep['page']:02d} | **{ep['topic']}** | {ep['theory'][:50]}... | 来源: P{ep['page']:02d} |")
    table_md = "\\n".join(table_rows)
    
    note_content = f"""# 模块 01：数据存储与运算（涵盖 P09 - P21）

> 计算机底层信息建模与算术逻辑体系 | 涵盖分集：P09 ~ P21 | 核心议题：字面量与类型、变量与内存绑定、字符串处理、人机I/O与算术逻辑运算符

---

## 知识拓扑框架导图

```text
{MODULE1_TOPOLOGY}
```

---

## 1. 模块核心概念速查表

| 分集索引 | 核心主题 | 关键原理推演 / 标准定义 | 知识溯源 |
| :--- | :--- | :--- | :--- |
{table_md}

---

## 2. 关键语法与常用运算符矩阵

| 语法分类 | 关键符号 / 函数 | 典型代码范式 | 核心行为 / 规约 |
| :--- | :--- | :--- | :--- |
| **基础类型** | `int`, `float`, `str`, `bool` | `type(x)` | 动态类型推断，底层基于 PyObject 封装 |
| **命名空间** | `=` | `a, b = b, a` | 原生元组解包交换，底层借助操作数栈原地置换 |
| **文本渲染** | `f"{{var:.2f}}"` | `f"User: {{name}}, Cash: {{money:.2f}}"` | PEP 498 原生格式化插值，具备极致的运行时解析效率 |
| **终端交互** | `print()`, `input()` | `age = int(input("Age:"))` | 标准 I/O 阻塞流，input 结果必为 str，需显式强转 |
| **算术除除** | `/`, `//`, `%` | `7 / 2 == 3.5`, `7 // 2 == 3` | 真除法产生 float，整除法向下取整，取模满足数学余数定义 |
| **逻辑短路** | `and`, `or`, `not` | `val = custom or default_val` | 逻辑判定短路执行，直接返回决定最终真假的操作数本身 |

---

## 3. 要点对比横评矩阵

### 对比一：`==` (数值比对) vs `is` (内存同一性比对)
| 判定维度 | `==` (Equality) | `is` (Identity) |
| :--- | :--- | :--- |
| **底层原理** | 调用对象的 `__eq__()` 魔法方法 | 直接比对变量底层内存指针地址（`id(a) == id(b)`） |
| **比对核心** | 比较两对象所承载的内容数值是否相同 | 比较两个标识符是否指向堆内存中的同一个物理对象 |
| **典型案例** | `10 == 10.0` 结果为 `True` | `10 is 10.0` 结果为 `False`（整型对象与浮点对象内存隔离） |
| **最佳实践** | 绝大多数业务数据比对统一使用 `==` | 仅在单例检测（如 `x is None`, `x is False`）时使用 `is` |

### 对比二：字符串拼接三代方案选型横评
| 方案维度 | 加号拼接 (`+`) | format() 方法 | f-string 插值 (推荐) |
| :--- | :--- | :--- | :--- |
| **引入版本** | Python 1.0+ | Python 2.6+ / 3.0+ | Python 3.6+ |
| **执行性能** | 差（反复开辟新内存并全量拷贝，复杂度 $O(N^2)$） | 良好（单次解析模板缓冲区分配） | 极佳（编译期词法优化，运行期直接生成字节码） |
| **可读性** | 极低（大量引号加号截断） | 中等（占位符与参数分离，长句易眼花） | 最高（所见即所得，大括号内直接嵌入表达式） |
| **适用场景** | 仅适合 2 个碎片的快速微型连接 | 模板外置需动态加载的国际化文案场景 | 所有代码内置文本渲染与格式化首选 |

---

## 4. 核心考点与速查清单 (CheatSheet)

1. **变量本质**：Python 中变量仅是引用标签，对象才有类型；变量必须先定义赋值才能读取。
2. **标识符规范**：以字母或下划线开头，严禁以数字开头；大小写敏感；严禁使用 35 个保留关键字或覆盖系统内置函数（如 `print`, `type`）。
3. **输入铁律**：`input()` 获取的永远是 `str`，参与数学运算前必须强制执行 `int()` 或 `float()`。
4. **算术边界**：除数不能为零（引发 `ZeroDivisionError`）；Python 整数精度无限制，但浮点数存在二进制 IEEE 754 精度漂移。
5. **短路求值引擎**：`A and B`（若 A 为假则直接返回 A，不求值 B）；`A or B`（若 A 为真则直接返回 A，不求值 B）。
"""
    note_file.write_text(note_content.strip() + "\\n", encoding="utf-8")
    print(f"  [Note] 生成模块大笔记: {note_file.name}")

if __name__ == "__main__":
    print("=== 开始生成 模块 01：数据存储与运算 (P09 - P21) ===")
    generate_subtitles()
    generate_articles()
    generate_notes()
    print("=== 模块 01 全部交付物生成完毕！===")
