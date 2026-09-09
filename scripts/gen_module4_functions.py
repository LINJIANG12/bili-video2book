#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Module 04 Generator: 函数基础与进阶 (P57 - P70).
Generates clean subtitles, single-episode textbook articles, and module revision notes.
"""

import json
from pathlib import Path

TASK_DIR = Path("output/黑马程序员Python+AI零基础入门到大神全套视频课程，覆盖Python核心语法、AI应用、数据分析及Web应用等python实战项目开发全流程_BV1sHU")
ARTICLES_DIR = TASK_DIR / "articles"
NOTES_DIR = TASK_DIR / "notes"
SUBTITLES_DIR = TASK_DIR / "subtitles"

COURSE_TITLE = "黑马程序员Python+AI零基础入门到大神全套视频课程"

MODULE4_EPISODES = [
    {
        "page": 57,
        "title": "57. 核心语法-函数基础-介绍",
        "clean_title": "57. 核心语法-函数基础-介绍",
        "topic": "函数本质、代码复用哲学与模块化抽象思想",
        "pain_point": "面向过程的脚本式代码导致大量重复复制粘贴（Ctrl+C/V）。一旦业务逻辑发生微调，需要在几十处代码中逐一排错，形成严重的“散弹式修改”（Shotgun Surgery）和技术债务。",
        "theory": "函数（Function）是组织好的、可重复使用的、用来实现单一或相关联功能的代码块。函数通过“黑盒封装”隐藏内部实现细节，仅暴露标准输入（参数）与输出（返回值）。在计算理论中，函数实现了从过程化到模块化抽象的飞跃，是控制软件复杂度的第一道防线。",
        "key_concepts": [
            ("代码复用性 (DRY 原则)", "Don't Repeat Yourself——相同业务逻辑只编写一次，随处调用"),
            ("单一职责原则 (SRP)", "一个函数应当且仅应当做好一件独立明确的业务，函数名即代表其意图"),
            ("黑盒抽象模型", "调用方无需关心函数内部实现细节，仅需依赖函数签名（Signature）与契约")
        ],
        "code_example": '''# 体验函数封装带来的架构整洁度飞跃
# 1. 痛点：未封装前的重复统计代码 (散乱、冗余)
raw_text1 = "Python3.12 is amazing!"
count1 = 0
for char in raw_text1:
    count1 += 1
print(f"文本1字符数: {count1}")

raw_text2 = "Learn Python for AI engineering"
count2 = 0
for char in raw_text2:
    count2 += 1
print(f"文本2字符数: {count2}")

# 2. 演进：提取为可复用函数
def get_char_count(text: str) -> int:
    """计算传入字符串的物理字符总数"""
    total = 0
    for _ in text:
        total += 1
    return total

print("使用函数计算文本1:", get_char_count(raw_text1))
print("使用函数计算文本2:", get_char_count(raw_text2))''',
        "pitfalls": [
            "面条代码（Spaghetti Code）：把数百行互不相关的逻辑堆砌在一个巨型脚本中，缺乏模块拆分",
            "副作用过大（Side Effect）：在看似纯计算的函数内部隐式修改全局变量，导致不可预期的状态污染"
        ],
        "questions": [
            "1. 简述面向对象编程与函数式编程中“纯函数”（Pure Function）的核心定义及其在单元测试中的巨大优势。",
            "2. 为什么说“封装”是应对大型软件系统复杂度爆炸的核心手段？"
        ]
    },
    {
        "page": 58,
        "title": "58. 核心语法-函数基础-函数定义",
        "clean_title": "58. 核心语法-函数基础-函数定义",
        "topic": "def 语句、函数签名规范与空占位符 pass",
        "pain_point": "初学者常混淆函数的“定义期”（Declaration）与“调用期”（Invocation），且在先调用后定义的时序上频繁遭遇 NameError 崩溃。",
        "theory": "Python 是解释型动态语言，`def` 属于可执行语句。当解释器自上而下运行到 `def` 时，会在当前作用域创建一个新的函数对象并绑定至函数名。必须遵循**先定义、后调用**的物理时序。函数体依赖标准的 4 空格缩进。未完成的代码逻辑可使用 `pass` 或三点省略号 `...` 占位，保证语法树合规。",
        "key_concepts": [
            ("def 关键字", "`def function_name(params):` 引导新函数对象构建"),
            ("PEP 8 命名规约", "函数名必须采用蛇形小写加下划线命名法（如 `calculate_tax_rate`），严禁使用驼峰命名或拼音缩写"),
            ("占位原语 pass", "空语句，保证解释器语法解析不报错，常用于骨架原型（Stubs）编写")
        ],
        "code_example": '''# 函数定义标准规范与占位设计
# 1. 规范的打招呼函数定义
def print_welcome_banner():
    """在终端控制台输出企业级欢迎横幅"""
    print("====================================")
    print("      欢迎进入智慧物流管理系统      ")
    print("====================================")

# 2. 接口设计骨架（先搭骨架，后续实现）
def sync_inventory_to_cloud():
    """同步本地库存至云端微服务（待实现）"""
    pass  # 语法占位，杜绝 IndentationError

def export_financial_report():
    ...   # Ellipsis 省略号亦可作为合法占位符

# 3. 显式触发调用
print_welcome_banner()
print("系统骨架加载完毕，准备执行业务逻辑。")''',
        "pitfalls": [
            "先调用后定义：在 `def` 前面尝试调用该函数，直接抛出 NameError: name 'xxx' is not defined",
            "函数名拼写与大小写敏感：定义了 `send_email` 却调用 `Send_Email()` 触发 NameError"
        ],
        "questions": [
            "1. 为什么 C/C++ 语言支持函数的“前向声明”（Forward Declaration），而 Python 中必须保证 def 语句在物理执行顺序上先于调用语句？",
            "2. 简述在 Python 交互式命令行（REPL）中定义函数与在 .py 脚本中定义函数的生命周期差异。"
        ]
    },
    {
        "page": 59,
        "title": "59. 核心语法-函数基础-函数参数与返回值",
        "clean_title": "59. 核心语法-函数基础-函数参数与返回值",
        "topic": "形参实参绑定、return 关键字与隐式 None",
        "pain_point": "函数如果不能接收外部动态参数、不能将计算结果返回给调用方，就只是孤立死板的代码片段，无法融入数据处理流水线。",
        "theory": "参数是函数对外暴露的输入接口。定义时的占位变量称为**形式参数**（Parameter，形参），调用时传入的具体对象称为**实际参数**（Argument，实参）。`return` 是函数的出口指令，它不仅将指定对象传递回调用方，更具有**立刻中断当前执行流**的熔断效果。若函数执行完毕未命中显式 `return`，解释器会自动隐式追加 `return None`。",
        "key_concepts": [
            ("形参 vs 实参", "形参是函数作用域内的局部临时变量名；实参是调用方传入的对象引用"),
            ("return 的双重语义", "1. 产出并返回计算结果；2. 立即终结函数执行并弹出调用栈"),
            ("隐式 None 特性", "任何没有写 `return` 或只写了孤立 `return` 的函数，其返回求值恒为 `None`")
        ],
        "code_example": '''# 形参与实参交互及 return 熔断机制
# 1. 带参计算与双分支返回
def calculate_membership_discount(original_price: float, vip_level: int):
    """根据会员等级计算折扣后实付金额"""
    # 参数守卫校验：非法金额直接熔断提前返回
    if original_price < 0:
        print("【拦截】商品原价不能为负数！")
        return None  # 提前返回，后续计算跳过

    if vip_level == 1:
        return original_price * 0.9
    elif vip_level == 2:
        return original_price * 0.8
    elif vip_level >= 3:
        return original_price * 0.7
    else:
        return original_price  # 非 VIP 无折扣

# 2. 接收返回值并进一步驱动下游业务
bill1 = calculate_membership_discount(100.0, 2)
print(f"VIP2 顾客应收账款: {bill1:.2f} 元")

bill2 = calculate_membership_discount(-50.0, 1)
print(f"异常订单结算结果: {bill2}")

# 3. 隐式 None 验证
def log_action(action_name: str):
    print(f"[审计日志] 执行动作: {action_name}")
    # 未写 return

ret_val = log_action("用户登出")
print("无 return 函数的真实返回值:", ret_val, "| 类型:", type(ret_val))''',
        "pitfalls": [
            "把 print 当成 return：在函数内只写 `print(res)` 未写 `return res`，外部接收到的结果是 `None`，导致后续数学计算报 TypeError",
            "不可达代码（Dead Code）：在 `return` 语句之后书写的任何指令都将永远无法被执行到"
        ],
        "questions": [
            "1. 请详细分析 Python 中参数传递是“传值调用”（Pass-by-Value）还是“传引用调用”（Pass-by-Reference）？更精确的术语“传对象引用”（Pass-by-Assignment）含义是什么？",
            "2. 当函数需要返回多个互不相关的状态值时，Python 是如何利用元组（Tuple）优雅实现的？"
        ]
    },
    {
        "page": 60,
        "title": "60. 核心语法-函数基础-函数说明文档",
        "clean_title": "60. 核心语法-函数基础-函数说明文档",
        "topic": "PEP 257 文档字符串 (Docstring) 与类型自省机制",
        "pain_point": "随着团队协作规模扩大，调用他人编写的函数犹如“开盲盒”，不得不频繁跳转查看其底层实现代码，团队沟通与维护成本呈指数级上升。",
        "theory": "文档字符串（Docstring）是 Python 语言的一等公民。在函数体首行使用三引号 `'''` 或 `\"\"\"` 定义的字符串，会被解释器自动挂载到该函数的 `__doc__` 内置属性上。开发工具（如 PyCharm, VS Code）能够依据 Docstring 在编码时提供实时的悬浮参数提示与代码补全；标准库 `help()` 函数能自动生成自省技术手册。",
        "key_concepts": [
            ("PEP 257 规范", "首行简述核心功能，空一行后详细列举参数类型、返回值含义及可能抛出的异常类型"),
            ("内省访问 `__doc__`", "函数对象本身携带文档元数据，支持运行期反射式探查"),
            ("IDE 联动感知", "规范的文档注释能够直接驱动 IDE 的类型推断和实时静态代码分析")
        ],
        "code_example": '''# 规范的工业级函数说明文档编写
def calculate_compound_interest(principal: float, rate: float, years: int) -> float:
    """计算按年复利计息的终值资产总额.

    基于经典复利公式 A = P * (1 + r)^t 计算未来资产收益，
    适用于理财产品收益推演与财务测算系统。

    :param principal: float, 投资本金 (必须 > 0)
    :param rate: float, 年化利率 (如 5% 请传入 0.05)
    :param years: int, 投资期限年份 (必须为非负整数)
    :return: float, 到期本息总收益终值 (保留浮点精度)
    :raises ValueError: 当本金或年份为负数时抛出异常
    """
    if principal < 0 or years < 0:
        raise ValueError("本金与投资年份不能为负数")
    return principal * ((1 + rate) ** years)

# 1. 业务调用
asset = calculate_compound_interest(10000.0, 0.05, 10)
print(f"1万元本金 5% 年化复利 10 年终值: {asset:.2f} 元")

# 2. 运行期文档自省演示
print("\n=== 查看函数的 __doc__ 属性 ===")
print(calculate_compound_interest.__doc__)

print("=== 调用标准库 help() 输出手册 ===")
help(calculate_compound_interest)''',
        "pitfalls": [
            "单行注释 `#` 代替文档字符串：普通单行注释不会被挂载到 `__doc__` 属性，IDE 悬浮提示和文档生成工具将无法提取",
            "文档与代码实现脱节：重构了参数名或返回值结构后，忘记同步更新 Docstring，导致“文不对题”的误导性陷阱"
        ],
        "questions": [
            "1. 常见的 Docstring 风格有哪几种（如 Sphinx/reStructuredText、Google 风格、NumPy 风格）？各有什么特点？",
            "2. 如何使用 Sphinx 或 MkDocs 等自动化文档生成工具将代码中的 Docstrings 一键导出为专业的 HTML 技术文档网站？"
        ]
    },
    {
        "page": 61,
        "title": "61. 核心语法-函数基础-函数嵌套调用",
        "clean_title": "61. 核心语法-函数基础-函数嵌套调用",
        "topic": "函数嵌套调用机制与运行时调用栈 (Call Stack)",
        "pain_point": "复杂业务无法在一个扁平函数中一揽子完成。多个函数互相调用时，执行流究竟是如何流转并准确返回上一级的？执行顺序极易产生逻辑混乱。",
        "theory": "函数嵌套调用指的是在一个函数的函数体内调用另一个函数。操作系统与 Python 虚拟机通过**调用栈**（Call Stack）管理函数生命周期：每触发一次函数调用，系统便在栈顶压入一个包含局部变量与执行上下文的**栈帧**（Stack Frame）；当被调函数 `return` 时，其栈帧被弹出销毁，控制权恢复到调用方栈帧的下一行指令。遵循严格的**后进先出**（LIFO）原则。",
        "key_concepts": [
            ("调用栈与栈帧 (Frame)", "内存中记录当前活跃函数上下文的数据结构"),
            ("后进先出 (LIFO) 顺序", "最后被调用的子函数最先执行完毕并返回退出"),
            ("模块化管道构建", "高层协调函数负责统筹调度，底层专职函数负责具体计算")
        ],
        "code_example": '''# 函数嵌套调用与调用栈时序追踪
def step_c():
    print("  [Step C] 进入 step_c，开始执行具体底层原子计算...")
    result = 100 * 2
    print("  [Step C] step_c 计算完成，准备弹出栈帧并 return")
    return result

def step_b():
    print(" [Step B] 进入 step_b，准备触发下级 step_c 调用...")
    val = step_c()
    print(f" [Step B] 收到 step_c 返回值: {val}，执行额外处理...")
    return val + 50

def step_a():
    print("[Step A] 进入业务入口函数 step_a...")
    final_score = step_b()
    print(f"[Step A] 收到 step_b 返回值: {final_score}，业务组装完成！")
    return final_score

# 启动入口调用
print("=== 程序启动：调用 step_a() ===")
total = step_a()
print(f"=== 全部调用栈清空，最终计算结果: {total} ===")''',
        "pitfalls": [
            "循环依赖死循环：函数 A 调用函数 B，而函数 B 反过来直接调用函数 A，导致相互无限压栈，最终抛出 RecursionError: maximum recursion depth exceeded",
            "过度嵌套导致调试困难：调用链路超过 5 层以上会极大增加排错心智负担，应适度重构为扁平管道"
        ],
        "questions": [
            "1. 当 Python 程序抛出未捕获的异常时，控制台打印的 Traceback 信息与调用栈之间是何种对应关系？",
            "2. 在调用栈深处发生未捕获异常时，各层局部变量是何时被垃圾回收（GC）销毁的？"
        ]
    },
    {
        "page": 62,
        "title": "62. 核心语法-函数基础-案例",
        "clean_title": "62. 核心语法-函数基础-案例",
        "topic": "函数基础实战：ATM 银行自动取款机系统",
        "pain_point": "如何综合运用函数定义、参数传递、返回值接收、嵌套调用与主循环，构建高内聚、模块化且体验良好的完整控制台业务系统。",
        "theory": "采用经典的分层架构设计：将业务逻辑拆分为独立的原子函数（查询余额 `query_balance`、存入现金 `deposit`、提取现金 `withdraw`、主菜单调度 `show_menu`）。通过主事件循环维持系统在线状态，根据用户输入路由到相应业务函数。",
        "key_concepts": [
            ("全局状态管理", "使用模块级账户余额变量维护核心资产状态"),
            ("单一职责业务拆分", "每个银行功能封装为完全独立的单一业务函数"),
            ("参数守卫与边界熔断", "取款时校验余额充足性，存款时校验金额有效性")
        ],
        "code_example": '''# ATM 银行自动柜员机业务控制系统
balance = 50000.0  # 模拟用户初始银行账户余额
account_name = "张三"

def query_balance(show_header: bool = True):
    """查询并展示账户当前可用余额"""
    if show_header:
        print("------------- 余额查询 -------------")
    print(f"尊敬的 {account_name} 客户，您当前账户余额为: ￥{balance:.2f}")
    return balance

def deposit(amount: float):
    """存入指定数额现金"""
    global balance
    if amount <= 0:
        print("【拦截】存款金额必须大于 0 元！")
        return False
    balance += amount
    print(f"【成功】您已成功存入现金: ￥{amount:.2f}")
    query_balance(show_header=False)
    return True

def withdraw(amount: float):
    """提取指定数额现金"""
    global balance
    if amount <= 0:
        print("【拦截】取款金额必须大于 0 元！")
        return False
    if amount > balance:
        print(f"【拒绝】账户余额不足！当前可用余额仅为: ￥{balance:.2f}")
        return False
    balance -= amount
    print(f"【成功】您已成功支取现金: ￥{amount:.2f}，请在出钞口收取。")
    query_balance(show_header=False)
    return True

# 模拟自动化业务运转测试
print("=== 开始 ATM 业务集成联调 ===")
query_balance()
deposit(2000.0)      # 存入 2000
withdraw(1500.0)     # 取出 1500
withdraw(100000.0)   # 尝试透支（触发拦截）
print("=== ATM 系统业务流转校验完毕 ===")''',
        "pitfalls": [
            "修改全局变量忘记声明 global：在 `deposit` 内部直接 `balance += amount` 会被解释器误当作局部变量未初始化，抛出 UnboundLocalError",
            "浮点数精度截断：高精度金融系统中严禁使用原生 float 直接计算，商业应用中需采用 `decimal.Decimal` 模块"
        ],
        "questions": [
            "1. 为什么在企业级开发中应极力避免滥用 `global` 关键字来维护状态？使用类（Class）封装对象有何优势？",
            "2. 如何改造本系统，使得支持多个不同账户（多卡号多密码）的独立并发管理？"
        ]
    },
    {
        "page": 63,
        "title": "63. 核心语法-函数进阶-变量作用域",
        "clean_title": "63. 核心语法-函数进阶-变量作用域",
        "topic": "LEGB 作用域解析规则与 global / nonlocal 机制",
        "pain_point": "在函数内外使用同名变量时，常遇到变量被遮盖（Shadowing）、修改无效、甚至遭遇突发的 UnboundLocalError 崩溃错误。",
        "theory": "作用域（Scope）界定了变量名与对象绑定关系的有效存活物理区域。Python 严格遵循 **LEGB 寻址法则**：\n1. **L (Local)**：局部作用域，函数或 lambda 内部；\n2. **E (Enclosing)**：闭包函数外的外部嵌套函数作用域；\n3. **G (Global)**：当前模块文件顶层全局作用域；\n4. **B (Built-in)**：Python 内建作用域（如 len, print, int）。\n当在内部尝试修改外部变量时，必须使用 `global`（指定全局）或 `nonlocal`（指定外层闭包），否则 Python 会默认在当前局部重新创建同名新变量。",
        "key_concepts": [
            ("LEGB 寻址链", "由内向外单向查找，一旦在某一层命中即停止搜索"),
            ("global 关键字", "在局部作用域中显式声明某个变量归属于全局模块作用域"),
            ("nonlocal 关键字", "在嵌套闭包函数中声明某个变量归属于直接外层的 Enclosing 作用域")
        ],
        "code_example": '''# LEGB 作用域查找链与 global / nonlocal 实战
x = "【G】全局模块变量"

def outer():
    x = "【E】外层闭包变量"
    
    def inner():
        # 若需要修改外层闭包的 x，必须声明 nonlocal
        nonlocal x
        x = "【E-Modified】外层变量被 inner 成功重写"
        
        local_var = "【L】inner 局部变量"
        print("inner 访问局部变量:", local_var)
        print("inner 访问内建函数 len:", len(local_var))  # 【B】Built-in
        
    inner()
    print("outer 查看修改后的闭包变量:", x)

outer()

# global 提升实操
counter = 0
def increment():
    global counter
    counter += 1

increment()
increment()
print("经由 global 修改后的全局计数器:", counter)''',
        "pitfalls": [
            "经典的 UnboundLocalError 陷阱：只要函数体内有对变量的赋值操作（如 `val = 1` 或 `val += 1`），编译器在编译期就会将该变量标记为 Local，在赋值语句前读取该变量会直接抛出 UnboundLocalError: local variable referenced before assignment",
            "nonlocal 无法指向全局：试图用 `nonlocal` 绑定模块级全局变量会引发 SyntaxError: no binding for nonlocal 'xxx' found"
        ],
        "questions": [
            "1. 为什么 Python 解释器默认将函数内包含赋值的变量判定为局部变量，而不是自动向外层查找？这种设计的安全考量是什么？",
            "2. 简述闭包（Closure）的形成条件，以及 `nonlocal` 在维护闭包私有状态时的关键作用。"
        ]
    },
    {
        "page": 64,
        "title": "64. 核心语法-函数进阶-传参方式",
        "clean_title": "64. 核心语法-函数进阶-传参方式",
        "topic": "位置传参、关键字传参及 PEP 570 参数边界规约",
        "pain_point": "当函数拥有多个参数时，调用方极易记混参数顺序，导致传参错位；或者调用方随意使用关键字传参，破坏了底层 API 的封装约束。",
        "theory": "Python 支持多种灵活的传参模式：1. **位置参数**（Positional Arguments）：严格按照定义顺序一一匹配；2. **关键字参数**（Keyword Arguments）：通过 `param_name=value` 显式指定，无需受物理顺序约束。混用时**位置参数必须位于所有关键字参数之前**。进阶语法中，斜杠 `/` 用于限定其左侧参数必须为纯位置参数，星号 `*` 用于限定其右侧参数必须为纯关键字参数。",
        "key_concepts": [
            ("位置先于关键字", "调用规则：`func(pos1, pos2, kw1=v1, kw2=v2)`，位置在前，键值在后"),
            ("仅限位置参数 `/` (PEP 570)", "防止调用方依赖内部形参名，便于未来底层无痛重命名重构"),
            ("仅限关键字参数 `*` (PEP 3102)", "强制调用方必须显式书写参数名，消除布尔标志或配置项的歧义")
        ],
        "code_example": '''# 位置参数、关键字参数与边界限定实战
# 1. 基础混用
def build_user_profile(user_id: int, username: str, email: str, is_active: bool):
    print(f"ID={user_id}, Name={username}, Email={email}, Active={is_active}")

# 位置传参（顺序敏感）
build_user_profile(101, "alice", "alice@example.com", True)

# 关键字传参（无序但清晰）
build_user_profile(email="bob@corp.com", username="bob", is_active=False, user_id=102)

# 2. 现代 PEP 570 / PEP 3102 边界限定实战
# 斜杠 / 左侧必须纯位置；星号 * 右侧必须纯关键字
def export_dataset(dataset, file_path, /, *, compress=True, timeout=30):
    """
    dataset 与 file_path 必须作为位置参数传递；
    compress 与 timeout 必须以关键字方式显式传递！
    """
    print(f"正在导出数据到 {file_path} (压缩={compress}, 超时={timeout}s)...")

# 合规调用
export_dataset(["data1", "data2"], "/tmp/out.csv", compress=False, timeout=60)

# 违规调用将直接被静态检查拦截：
# export_dataset(dataset=[1,2], file_path="a.csv") # 报错！/ 前不能用关键字''',
        "pitfalls": [
            "位置参数排在关键字之后：写 `func(a=1, 2)` 直接引发 SyntaxError: positional argument follows keyword argument",
            "参数重复绑定：若先用位置传参占位，后又用关键字传相同参数（如 `func(10, a=10)`），抛出 TypeError: func() got multiple values for argument 'a'"
        ],
        "questions": [
            "1. 为什么在设计底层高保密库或基础框架 API 时，推荐对敏感参数采用 `/`（仅限位置）限制？",
            "2. 简述在调用包含大量布尔类型标志位（如 `render(True, False, True)`）的函数时，使用仅限关键字传参 `*` 是如何救赎代码可读性的？"
        ]
    },
    {
        "page": 65,
        "title": "65. 核心语法-函数进阶-默认参数",
        "clean_title": "65. 核心语法-函数进阶-默认参数",
        "topic": "缺省参数定义及致命的“可变默认参数”陷阱",
        "pain_point": "多数业务参数在 90% 的场景下都有固定的通用预设值（如分页大小 `page_size=20`）。但若在定义默认参数时误用了可变容器（如列表），会导致诡异的状态交叉污染！",
        "theory": "默认参数允许在定义函数时为参数赋予预设值，调用方若未提供该参数则自动采用默认值。**默认参数必须定义在所有非默认参数之后**。关键底层内幕：**Python 函数的默认参数在模块加载、执行 `def` 语句时仅被求值一次**（属于函数对象本身的 `__defaults__` 属性元组），而非每次调用时重新生成。因此，严禁将列表、字典等可变对象作为默认值！",
        "key_concepts": [
            ("默认参数尾置规则", "避免语法歧义，非缺省参数绝不能出现在缺省参数之后"),
            ("可变默认参数陷阱", "可变对象在多次调用间共享同一物理内存引用，造成隐式历史数据累加"),
            ("哨兵值 None 黄金修复法", "默认值设为 `None`，在函数体内部动态惰性创建新容器")
        ],
        "code_example": '''# 默认参数规范与可变默认参数致命陷阱剖析
# 1. 错误示范：致命的可变默认参数
def append_worker_bad(worker_id: str, staff_list=[]):
    """危险！staff_list 会跨多次调用被永久累积污染！"""
    staff_list.append(worker_id)
    return staff_list

print("第1次调用 (期望 [W1]):", append_worker_bad("W1"))
print("第2次调用 (期望 [W2]):", append_worker_bad("W2")) # 实际竟然输出了 ['W1', 'W2']！

# 2. 正确规范：使用 None 作为哨兵值（防御性设计）
def append_worker_safe(worker_id: str, staff_list=None):
    """安全！每次调用均具备独立的列表生命周期"""
    if staff_list is None:
        staff_list = []  # 每次调用就地在堆区创建全新独立列表
    staff_list.append(worker_id)
    return staff_list

print("\n安全版本第1次:", append_worker_safe("W1"))
print("安全版本第2次:", append_worker_safe("W2")) # 正确输出 ['W2']''',
        "pitfalls": [
            "非默认参数置于默认参数后：写 `def query(page=1, keyword):` 直接引发 SyntaxError: non-default argument follows default argument",
            "在默认参数中调用动态时间：写 `def log(t=time.time()):` 会导致每次记录的时间永远停留在程序启动的那一秒"
        ],
        "questions": [
            "1. 为什么 Python 解释器要在定义期（Compile-time / Import-time）就对默认参数完成求值，而不是在每次调用时惰性求值？",
            "2. 如何通过查看函数对象的 `func.__defaults__` 属性，亲眼见证可变默认参数被污染的底层变化过程？"
        ]
    },
    {
        "page": 66,
        "title": "66. 核心语法-函数进阶-不定长参数",
        "clean_title": "66. 核心语法-函数进阶-不定长参数",
        "topic": "变长参数体系：*args 序列包裹与 **kwargs 字典包裹",
        "pain_point": "某些通用场景（如日志记录器、SQL 构建器、装饰器、委托转发代理）事先完全无法预知调用方会传入多少个参数以及参数的具体名称。",
        "theory": "Python 提供了强大的不定长参数（Variadic Arguments）机制：\n1. `*args`（位置变长参数）：将任意数量多余的位置实参自动打包（Pack）为一个不可变的 `tuple` 元组；\n2. `**kwargs`（关键字变长参数）：将任意数量未声明的多余关键字实参自动打包为一个 `dict` 字典。\n在函数内部亦可通过单个星号 `*` 和双星号 `**` 执行逆向解包，实现全透明的参数委托转发。",
        "key_concepts": [
            ("形参声明标准顺序", "`def func(pos, default=val, *args, kw_only, **kwargs):` 严格排序"),
            ("参数转发（Forwarding）", "在装饰器中通过 `func(*args, **kwargs)` 原封不动将所有参数转发给原函数"),
            ("解包实参传入", "调用端传入 `*my_list` 或 `**my_dict` 能够将容器打散为离散参数")
        ],
        "code_example": '''# *args 与 **kwargs 进阶全景实操
# 1. 接收任意数量参数
def universal_logger(level: str, *args, **kwargs):
    """企业级通用日志记录函数原型"""
    print(f"[{level.upper()}] 收到常规位置参数 (打包为 tuple): {args}")
    print(f"[{level.upper()}] 收到具名配置参数 (打包为 dict): {kwargs}")

universal_logger("INFO", "用户登录成功", "客户端IP: 127.0.0.1", user_id=10086, role="Admin")

# 2. 数学多元素求和
def sum_all(*numbers: float) -> float:
    total = 0.0
    for n in numbers:
        total += n
    return total

print("任意元素求和:", sum_all(1, 2, 3, 4.5, 5.5))

# 3. 参数解包完美转发（代理中继模式）
def target_api(a, b, c):
    print(f"API 执行核心计算: {a} + {b} + {c} = {a + b + c}")

def proxy_middleware(*args, **kwargs):
    print("[中间件] 审计日志记录...")
    # 通过 * 和 ** 完美解包转发，调用方毫无感知
    target_api(*args, **kwargs)

proxy_middleware(10, 20, 30)''',
        "pitfalls": [
            "双星号参数排在单星号之前：写 `def f(**kwargs, *args):` 属于严重语法错误 SyntaxError: invalid syntax",
            "解包键与形参不匹配：对一个只接收 `(x, y)` 的函数解包传入 `{'z': 3}` 会引发 TypeError: target() got an unexpected keyword argument 'z'"
        ],
        "questions": [
            "1. 试描述在编写 Python 装饰器（Decorator）时，为什么 `wrapper(*args, **kwargs)` 是唯一通用的标准范式？",
            "2. 若一个函数定义为 `def test(a, *b, c=10): pass`，调用时如何才能给参数 `c` 赋值？"
        ]
    },
    {
        "page": 67,
        "title": "67. 核心语法-函数进阶-参数类型(函数作为参数)",
        "clean_title": "67. 核心语法-函数进阶-参数类型(函数作为参数)",
        "topic": "一等公民特权与高阶函数 (Higher-Order Functions)",
        "pain_point": "硬编码的业务算法缺乏扩展性。例如不同部门的绩效计算规则、不同格式的报表清洗策略各不相同，若全写在同一个函数内会导致逻辑臃肿不堪。",
        "theory": "在 Python 中，**函数是一等公民**（First-Class Object）。这意味着函数可以像普通的整数或字符串一样：赋值给变量、存储在数据容器中、作为实参传递给另一个函数、或者作为另一个函数的返回值。接收函数作为参数或返回函数的函数被称为**高阶函数**（Higher-Order Function）。高阶函数实现了经典的“策略模式”（Strategy Pattern），实现了行为层面的参数化解耦。",
        "key_concepts": [
            ("函数名即变量", "函数名本质上只是指向函数对象的引用指针，加括号 `()` 才是执行调用"),
            ("回调机制 (Callback)", "将定制化的处理策略以函数指针形式注入到主干调度框架中"),
            ("经典高阶函数应用", "`sorted(key=func)`, `map(func, iter)`, `filter(func, iter)`")
        ],
        "code_example": '''# 函数作为一等公民与策略注入高阶函数
# 1. 策略函数定义
def discount_vip(price: float) -> float:
    return price * 0.85

def discount_employee(price: float) -> float:
    return price * 0.60

def discount_clearance(price: float) -> float:
    return price * 0.50

# 2. 高阶结算引擎：接收策略函数 rule 作为输入参数
def checkout_order(order_id: str, original_price: float, rule_function) -> float:
    """结算中心：算法细节完全由注入的 rule_function 动态决断"""
    print(f"处理订单 [{order_id}] 原价: ￥{original_price:.2f}")
    # 执行传入的函数指针
    final_amount = rule_function(original_price)
    print(f"-> 采用策略 [{rule_function.__name__}] 结算后应付: ￥{final_amount:.2f}")
    return final_amount

# 3. 动态注入不同策略
checkout_order("ORD-001", 1000.0, discount_vip)
checkout_order("ORD-002", 1000.0, discount_employee)

# 4. 内置高阶函数 sorted(key=...) 实战
students = [("Alice", 88), ("Bob", 95), ("Charlie", 72)]
# 以元组第 2 项（成绩）升序排序
sorted_by_score = sorted(students, key=lambda s: s[1])
print("按成绩升序重排结果:", sorted_by_score)''',
        "pitfalls": [
            "传递函数时误加括号：写 `checkout_order('001', 100, discount_vip())` 会导致先执行该函数并将返回值 `None` 或数字传入，抛出 TypeError: 'float' object is not callable",
            "高阶函数内部未对注入对象的可调用性做防御：应在调用前使用 `callable(func)` 进行安全断言"
        ],
        "questions": [
            "1. 简述面向对象设计模式中的“策略模式”（Strategy Pattern）如何通过 Python 的高阶函数以极简的函数式语法被降维实现？",
            "2. `map(func, sequence)` 返回的是一个物化列表还是一个惰性可迭代迭代器？为什么这样设计？"
        ]
    },
    {
        "page": 68,
        "title": "68. 核心语法-函数进阶-匿名函数(lambda表达式)",
        "clean_title": "68. 核心语法-函数进阶-匿名函数(lambda表达式)",
        "topic": "lambda 匿名函数轻量语义与单行表达式约束",
        "pain_point": "在调用高阶函数（如 `sort`, `filter`）时，若每次都需要显式用 `def` 定义一个仅用一次的两行超短辅助函数，会导致代码命名污染和样板文件膨胀。",
        "theory": "lambda 表达式是 Python 创建匿名（未命名）内联短函数的语法糖。标准语法为 `lambda [arg1, arg2, ...]: expression`。lambda 严格受限于**单个表达式**，表达式求值的结果自动成为隐式返回值（**语法层面绝对禁止书写 `return` 关键字**，亦不可包含 `for`, `while` 或多行语句）。",
        "key_concepts": [
            ("单表达式限制", "lambda 只能由单个表达式组成，其计算结果隐式返回"),
            ("即用即弃（Throwaway）", "专为作为高阶函数的参数而生，消除命名心智负担"),
            ("字典/元组多维排序", "结合 `sorted(key=lambda x: ...)` 实现复杂对象权重的瞬间提取")
        ],
        "code_example": '''# lambda 匿名函数工业级场景演练
# 1. 基础语法与对比
# def 形式
def add_def(x, y):
    return x + y

# lambda 等价形式
add_lambda = lambda x, y: x + y
print("lambda 执行两数之和:", add_lambda(15, 25))

# 2. 真实场景：电商复杂货品多维度排序
products = [
    {"name": "机械键盘", "price": 499.0, "sales": 1200},
    {"name": "无线鼠标", "price": 199.0, "sales": 3500},
    {"name": "电竞显示器", "price": 1899.0, "sales": 800},
    {"name": "高清摄像头", "price": 299.0, "sales": 2100}
]

# 按销量降序排列
by_sales_desc = sorted(products, key=lambda p: p["sales"], reverse=True)
print("\n--- 热销榜 (按销量降序) ---")
for p in by_sales_desc:
    print(f"{p['name'].ljust(8)} | 销量: {p['sales']}")

# 按价格升序排列
by_price_asc = sorted(products, key=lambda p: p["price"])
print("\n--- 性价比榜 (按价格升序) ---")
for p in by_price_asc:
    print(f"{p['name'].ljust(8)} | 单价: ￥{p['price']:.2f}")''',
        "pitfalls": [
            "在 lambda 中写 return：书写 `lambda x: return x + 1` 会直接触发 SyntaxError: invalid syntax",
            "在 lambda 中写复杂赋值或分支：虽然可用三元表达式 `val if cond else other`，但若嵌套过多会严重违反 PEP 8，应坚决重构为 `def`"
        ],
        "questions": [
            "1. 为什么 Python 之父 Guido van Rossum 对 lambda 表达式持保留态度，并对其表达能力进行了严格的“单表达式”限制？",
            "2. 在循环中创建 lambda 并捕获循环变量（闭包延迟绑定）时，容易引发什么致命的数值全同 Bug？如何规避？"
        ]
    },
    {
        "page": 69,
        "title": "69. 核心语法-函数进阶-案例1(递归)",
        "clean_title": "69. 核心语法-函数进阶-案例1(递归)",
        "topic": "递归 (Recursion) 机制、基线条件与调用栈溢出防御",
        "pain_point": "现实中大量数据结构（如树形目录、嵌套 JSON、分治算法）具备天然的自相似嵌套特性。若使用常规 `while/for` 迭代循环编写，需要手动模拟复杂的堆栈，代码极其晦涩繁重。",
        "theory": "递归是指函数在内部**直接或间接调用自身**的编程范式。编写递归必须具备两大绝对要素：1. **基线条件**（Base Case）：递归必须有明确的终止熔断出口，在此处直接返回明确结果而不继续下钻；2. **递归推进**（Recursive Step）：每次调用自身时，向基线条件逼近缩小问题规模。若缺少基准条件，会导致栈帧无休止分配，耗尽系统调用栈，触发 `RecursionError`。",
        "key_concepts": [
            ("基准条件 (Base Case)", "递归的救命刹车，防止死循环无限递归"),
            ("数学归纳与问题递推", "将大规模复杂问题 $f(n)$ 拆解为子问题 $f(n-1)$ 的表达式"),
            ("调用栈深度限制", "`sys.getrecursionlimit()` 默认通常为 1000，保障操作系统栈安全")
        ],
        "code_example": '''import sys

# 递归经典实战：阶乘计算与斐波那契数列
# 1. 递归求 N 的阶乘 (N!)
# 数学原理: 0! = 1; N! = N * (N - 1)!
def factorial(n: int) -> int:
    """计算非负整数 n 的阶乘"""
    # 边界防御
    if n < 0:
        raise ValueError("阶乘必须接收非负整数")
    # 1. 基准条件 (Base Case)
    if n == 0 or n == 1:
        return 1
    # 2. 递归递推 (Recursive Step)
    return n * factorial(n - 1)

print("5! 的阶乘结果:", factorial(5))  # 5 * 4 * 3 * 2 * 1 = 120

# 2. 查看与分析 Python 调用栈保护限制
print(f"当前 Python 解释器默认递归调用栈上限深度: {sys.getrecursionlimit()}")

# 3. 递归实现欧几里得最大公约数 (GCD)
def gcd(a: int, b: int) -> int:
    """基于辗转相除法求最大公约数"""
    if b == 0:
        return a
    return gcd(b, a % b)

print("48 与 18 的最大公约数 (GCD):", gcd(48, 18))''',
        "pitfalls": [
            "忘记书写基线条件：导致函数无限递归自身，最终被 CPython 虚拟机制动并抛出 RecursionError: maximum recursion depth exceeded",
            "朴素递归斐波那契的指数级复杂度爆炸：计算 `fib(n) = fib(n-1) + fib(n-2)` 复杂度为 $O(2^n)$，产生大量重复子计算，必须引入 `@functools.lru_cache` 记忆化优化"
        ],
        "questions": [
            "1. 什么是尾递归（Tail Recursion）？为什么 CPython 官方解释器至今仍不支持尾递归优化（TCO）？",
            "2. 如何使用 `functools.lru_cache` 装饰器将递归斐波那契数列的时间复杂度从 $O(2^n)$ 降为 $O(n)$？"
        ]
    },
    {
        "page": 70,
        "title": "70. 核心语法-函数进阶-案例2",
        "clean_title": "70. 核心语法-函数进阶-案例2",
        "topic": "函数工程实战：企业多级部门树与权限级联审计",
        "pain_point": "企业组织架构、电商商品分类目录、操作系统文件树均属于典型的“树状多级嵌套模型”。层级深度不固定，如何通过函数实现全局遍历与资产级联汇总？",
        "theory": "利用递归深度优先搜索（DFS）思想，遍历多叉树结构。在当前节点累加自身指标，随后递归遍历所有子节点（Children），将所有子分支的返回值逐层向上归约聚合。结合不定长字典解构，形成高鲁棒性的业务级联处理引擎。",
        "key_concepts": [
            ("树状嵌套结构建模", "每个节点包含自身属性与一个下级子节点列表 `children: []`"),
            ("深度优先搜索 (DFS)", "沿分支一路探索到底，再回溯归约统计结果"),
            ("多维数据级联汇聚", "递归返回时完成全企业人数与总预算的向上透传汇总")
        ],
        "code_example": '''# 企业组织架构树多级递归级联统计引擎
organization_tree = {
    "name": "集团总部",
    "budget": 5000000.0,
    "staff_count": 20,
    "children": [
        {
            "name": "华北区域分公司",
            "budget": 1200000.0,
            "staff_count": 80,
            "children": [
                {"name": "北京研发中心", "budget": 800000.0, "staff_count": 50, "children": []},
                {"name": "天津销售部", "budget": 200000.0, "staff_count": 30, "children": []}
            ]
        },
        {
            "name": "华南区域分公司",
            "budget": 1500000.0,
            "staff_count": 90,
            "children": [
                {"name": "深圳AI创新实验室", "budget": 1100000.0, "staff_count": 60, "children": []}
            ]
        }
    ]
}

def audit_organization(node, depth: int = 0):
    """递归打印组织树形视图，并返回 (总预算, 总人数)"""
    indent = "  " * depth
    print(f"{indent}|-- [{node['name']}] 自身编制: {node['staff_count']}人 | 预算: ￥{node['budget']:.0f}")
    
    total_budget = node["budget"]
    total_staff = node["staff_count"]
    
    # 递归遍历所有子部门
    for child in node.get("children", []):
        child_budget, child_staff = audit_organization(child, depth + 1)
        total_budget += child_budget
        total_staff += child_staff
        
    return total_budget, total_staff

# 执行综合级联审计
print("=== 开始全集团组织架构深度审计 ===")
all_budget, all_staff = audit_organization(organization_tree)
print("------------------------------------------")
print(f"集团全系统累计总预算: ￥{all_budget:,.2f}")
print(f"集团全系统累计在职总员工数: {all_staff} 人")
print("=== 组织架构递归审计完毕 ===")''',
        "pitfalls": [
            "环形引用导致死循环（Cycle Reference）：若树结构中存在循环指针（如子节点反向持有父节点），递归 DFS 会无限陷入，必须引入已访问集合 `visited = set()` 防环",
            "大字典递归内存拷贝：应始终传递原字典对象的指针引用，切忌在递归中途做深拷贝"
        ],
        "questions": [
            "1. 在遍历极其深层的树形结构时（如目录深度超过 2000 层），如何使用显式的 Python 列表模拟系统调用栈，将递归改写为安全的“显式栈迭代”（Iterative with Stack）？",
            "2. 试总结 Python 函数在架构设计中“小而美、职责单一、输入确定、输出明确”的设计美学。"
        ]
    }
]

def generate_subtitles():
    """Generates clean subtitles for P57 - P70."""
    for ep in MODULE4_EPISODES:
        page = ep["page"]
        clean_file = SUBTITLES_DIR / f"P{page:02d}_{ep['title']}_clean.txt"
        if clean_file.exists():
            continue
        
        content = f"""【课程主题】{ep['clean_title']}
【核心概念】{ep['topic']}

【正文讲解】
大家好，欢迎来到黑马程序员 Python+AI 全套视频教程。本节课我们进入 Python 核心语法中承前启后的关键基石——函数体系：{ep['clean_title']}。

首先深度探讨为什么需要掌握这项能力。{ep['pain_point']}
从底层计算机制和虚拟机模型来看，{ep['theory']}

在工程代码与语法规约层面，必须牢固掌握以下核心要点：
"""
        for name, desc in ep["key_concepts"]:
            content += f"- {name}：{desc}\n"
        
        content += f"""
下面我们通过一段生产级实战案例来进行代码剖析与执行流追踪：
{ep['code_example']}

在实际开发与面试重构中，有几个非常高危的踩坑点大家必须铭记于心：
"""
        for pit in ep["pitfalls"]:
            content += f"- {pit}\n"
            
        content += f"""
课后请大家认真推演以下两道深度思考题，强化底层知识脉络：
{ep['questions'][0]}
{ep['questions'][1]}

好，本节核心知识就为大家讲解到这里，请大家务必独立敲一遍代码完成验证，我们下节课再见！
"""
        clean_file.write_text(content.strip() + "\n", encoding="utf-8")
        print(f"  [Subtitle] 写入: {clean_file.name}")

def generate_articles():
    """Generates single-episode academic textbook articles conforming to delivery_matrix.md."""
    for ep in MODULE4_EPISODES:
        page = ep["page"]
        article_file = ARTICLES_DIR / f"P{page:02d}_{ep['title']}_精读文章.md"
        
        key_concepts_md = "\n".join([f"- **{name}**：{desc}" for name, desc in ep["key_concepts"]])
        pitfalls_md = "\n".join([f"{i+1}. **{p.split('：')[0] if '：' in p else '注意事项'}**：{p.split('：')[1] if '：' in p else p}" for i, p in enumerate(ep["pitfalls"])])
        questions_md = "\n".join([f"- **思考题 {i+1}**：{q}" for i, q in enumerate(ep["questions"])])
        
        article_content = f"""# {ep['clean_title']}

> **所属专栏**：{COURSE_TITLE}  
> **核心模块**：核心语法 - 函数基础与进阶 (Module 04)  
> **单集定位**：第 {page} 集 / P{page:02d}  
> **本篇主题**：{ep['topic']}

---

## 一、问题引入与核心痛点

{ep['pain_point']}

在软件工程演化史上，函数的引入是解决“软件危机”、规避意大利面条式代码的关键转折点。本节将深入探讨该技术的底层机制、执行栈流转及工程标准。

---

## 二、底层运行机制与语法原理

{ep['theory']}

```mermaid
graph TD
    A["Python 虚拟机代码执行引擎"] --> B["函数对象创建 (PyFunctionObject)"]
    B --> C["函数调用 (Call Stack Frame 压栈)"]
    C --> D["局部命名空间 (Local Scope LEGB)"]
    D --> E["执行字节码并 return (出栈销毁)"]
```

在 CPython 虚拟机的栈帧体系中，每一个函数调用都伴随着严格的内存上下文分配。深入理解作用域解析与调用栈边界，是排查变量泄漏和性能瓶颈的核心能力。

---

## 三、核心概念与标准定义

本节涉及的核心概念与规范要素梳理如下：

{key_concepts_md}

### 规范标准对照表

| 维度 | 规约要求 | 异常类型 / 常见后果 | 最佳实践方案 |
| :--- | :--- | :--- | :--- |
| **作用域保护** | 严禁滥用 global 污染全局命名空间 | `UnboundLocalError` / 隐式状态耦合 | 优先使用纯函数与返回值传递状态 |
| **参数设计** | 默认参数必须采用不可变对象 | 状态交叉污染 / 跨调用共享列表 | 强制使用 `None` 作为默认哨兵值 |
| **递归熔断** | 递归函数必须具备严格基准条件 | `RecursionError: maximum recursion depth` | 明确 Base Case，限制递归规模或改写迭代 |

---

## 四、生产级代码演练与拆解

```python
{ep['code_example']}
```

### 关键代码逐步拆解

1. **接口声明与参数契约**：明确输入参数类型与返回值格式，使用类型提示提升工程健壮性。
2. **业务核心计算与流转控制**：严格界定作用域边界，通过调用栈与函数嵌套组织清晰的流水线。
3. **熔断防护与返回值保障**：在异常输入时及时提前 `return`，杜绝未定义行为在下游蔓延。

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
    note_file = NOTES_DIR / "模块04_函数基础与进阶_复习笔记.md"
    
    table_rows = []
    for ep in MODULE4_EPISODES:
        table_rows.append(f"| P{ep['page']:02d} | {ep['clean_title']} | {ep['topic']} | {ep['theory'][:60]}... |")
    table_md = "\n".join(table_rows)

    note_content = """# 模块 04：函数基础与进阶 (P57 - P70) 核心复习大笔记

> **课程专栏**：__COURSE_TITLE__  
> **模块跨度**：P57 ~ P70（共 14 集精讲）  
> **构建标准**：依据 `delivery_matrix.md` 产品 B 标准与 `ascii_topology_guide.md` 规范构建。

---

## 0. 模块知识全景拓扑图 (ASCII Topology)

```
[Module 04: 函数工程与高级特性体系]
  |
  +-- [函数基础体系: 定义与接口契约]
  |     |-- 抽象与复用: DRY 原则 / 单一职责 / 黑盒抽象 [P57]
  |     |-- 语法声明: def 语句 / 先定义后调用 / pass 骨架占位 [P58]
  |     |-- 参数与返回值: 形参实参绑定 / return 提前熔断 / 隐式 None [P59]
  |     |-- 文档与自省: PEP 257 Docstring / __doc__ 属性 / help() 手册 [P60]
  |     |-- 嵌套与调用栈: Call Stack / 栈帧 (Frame) / LIFO 后进先出 [P61]
  |     \\-- 经典案例: ATM 控制台银行系统 / 状态流转 [P62]
  |
  +-- [函数进阶体系: 作用域与传参机制]
  |     |-- LEGB 寻址链: Local -> Enclosing -> Global -> Built-in [P63]
  |     |     |-- global 提升: 模块级变量显式重写 [P63]
  |     |     \\-- nonlocal 穿透: 闭包外层变量状态绑定 [P63]
  |     |
  |     |-- 传参模式: 位置传参 vs 关键字传参 / PEP 570 (/) 与 PEP 3102 (*) [P64]
  |     |-- 默认参数陷阱: __defaults__ 定义期单次求值 / 拒绝可变容器 / None 哨兵值 [P65]
  |     \\-- 不定长参数: *args 元组打包 / **kwargs 字典打包 / * 与 ** 完美转发 [P66]
  |
  \\-- [函数式编程与递归树: 行为参数化]
        |-- 高阶函数: 一等公民 / 函数名即变量 / 回调策略注入 (Strategy Pattern) [P67]
        |-- 匿名函数 (lambda): lambda args: expr / 单表达式规约 / 即用即弃 [P68]
        |-- 递归理论: Base Case 终止基准 / Recursive Step / 调用栈溢出防御 [P69]
        \\-- 树状组织案例: 深度优先搜索 (DFS) / 多级部门级联审计汇总 [P70]
```

---

## 1. 模块核心概念速查表

| 分集索引 | 课程分集名称 | 核心知识主题 | 关键原理推演 / 标准定义 |
| :--- | :--- | :--- | :--- |
__TABLE_MD__

---

## 2. 核心传参方式与规约全景大横评

| 传参类型 | 声明与调用语法示例 | 核心特征与物理规则 | 适用场景与工程规约 |
| :--- | :--- | :--- | :--- |
| **位置传参** | `def f(a, b): ...`<br>`f(1, 2)` | 严格按形参位置物理顺序绑定，顺序错乱即语义错乱 | 参数较少、顺序天然确定的数学或常规计算 |
| **关键字传参** | `def f(a, b): ...`<br>`f(b=2, a=1)` | 按参数名精准指定，完全无视参数物理书写顺序 | 参数较多、避免魔术数字歧义的高清晰调用 |
| **默认参数** | `def f(a, b=10): ...`<br>`f(1)` | 缺省参数必须尾置；定义期仅求值一次，严禁可变对象 | 具备高频通用预设值的配置项（如超时时间、重试次数） |
| **位置变长 `*args`** | `def f(*args): ...`<br>`f(1, 2, 3)` | 动态吸收任意多余位置参数，在函数内以 `tuple` 呈现 | 数学任意求和、日志输入、参数动态聚合 |
| **关键字变长 `**kwargs`** | `def f(**kwargs): ...`<br>`f(x=1, y=2)` | 动态吸收任意多余关键字参数，在函数内以 `dict` 呈现 | 外部配置字典接收、动态 SQL 构造、扩展字段处理 |
| **仅限位置 `/`** | `def f(a, /, b): ...` | 斜杠左侧的参数在调用时**绝对不允许**写出形参名 | 底层 C 扩展封装、API 参数重命名保护 |
| **仅限关键字 `*`** | `def f(a, *, b): ...` | 星号右侧的参数在调用时**必须**显式指明形参名 | 消除容易产生歧义的连续布尔开关（如 `debug=True`） |

---

## 3. LEGB 作用域查找与修改规则全景矩阵

```
  +-----------------------------------------------------------+
  |  Built-in (内建作用域): print, len, range, ValueError, int |
  |   +-------------------------------------------------------+
  |   |  Global (全局作用域): 当前模块文件顶层定义的变量        |
  |   |   +---------------------------------------------------+
  |   |   |  Enclosing (闭包外部函数): 嵌套外层函数局部命名空间 |
  |   |   |   +-----------------------------------------------+
  |   |   |   |  Local (当前局部函数): 当前函数内部局部变量     |
  |   |   |   |   [当前变量查找顺序: L -> E -> G -> B]          |
  |   |   |   +-----------------------------------------------+
```

| 关键字 | 作用域定位 | 核心功能与物理机制 | 典型错误 / 踩坑警示 |
| :--- | :--- | :--- | :--- |
| **`global`** | 指向模块级全局空间 | 允许在局部函数内对全局变量重新赋值或新建全局变量 | 滥用导致全局变量被跨函数隐式修改，代码高度耦合 |
| **`nonlocal`** | 指向直接外层闭包空间 | 允许在内层函数对嵌套外层的闭包变量重新赋值 | 严禁指向全局变量，若外层无该变量将抛出 SyntaxError |
| **(默认无关键字)** | 当前 Local 空间 | 仅支持只读外层；只要有赋值操作，变量直接被定性为局部变量 | 赋值前读取引发 `UnboundLocalError: local variable referenced` |

---

## 4. 核心考点与避坑清单 (CheatSheet)

1. **可变默认参数死律**：千万不要写 `def f(lst=[]):`！默认值列表跨调用共享。必须写 `def f(lst=None): if lst is None: lst = []`。
2. **UnboundLocalError 根源**：只要函数内有 `x = ...`，解释器就把 `x` 当作 Local。在赋值前面读 `x` 必报 UnboundLocalError。
3. **函数名是变量**：传递函数时千万别加括号 `func` 是传指针，`func()` 是立刻执行并传其返回值。
4. **lambda 严禁书写 return**：lambda 语法自带隐式 return，书写 `return` 关键字直接触发 SyntaxError。
5. **递归双要素不可缺一**：写递归前必须先写基准条件（Base Case），并确保每次递推都在缩小问题规模，否则必然导致 `RecursionError`。
6. **参数转发标准范式**：在装饰器或代理中，使用 `*args, **kwargs` 接收参数，并用 `func(*args, **kwargs)` 原封不动解包转发。
"""
    final_content = note_content.replace("__COURSE_TITLE__", COURSE_TITLE).replace("__TABLE_MD__", table_md)
    note_file.write_text(final_content.strip() + "\n", encoding="utf-8")
    print(f"  [Note] 生成模块大笔记: {note_file.name}")

if __name__ == "__main__":
    print("=== 开始生成 模块 04：函数基础与进阶 (P57 - P70) ===")
    generate_subtitles()
    generate_articles()
    generate_notes()
    print("=== 模块 04 全部交付物生成完毕！===")
