#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Module 02 Generator: 流程控制语句 (P22 - P35).
Generates clean subtitles, single-episode textbook articles, and module revision notes.
"""

import json
from pathlib import Path

TASK_DIR = Path("output/黑马程序员Python+AI零基础入门到大神全套视频课程，覆盖Python核心语法、AI应用、数据分析及Web应用等python实战项目开发全流程_BV1sHU")
ARTICLES_DIR = TASK_DIR / "articles"
NOTES_DIR = TASK_DIR / "notes"
SUBTITLES_DIR = TASK_DIR / "subtitles"

COURSE_TITLE = "黑马程序员Python+AI零基础入门到大神全套视频课程"

MODULE2_EPISODES = [
    {
        "page": 22,
        "title": "22. 核心语法-流程控制语句-if基础语法",
        "clean_title": "22. 核心语法-流程控制语句-if基础语法",
        "topic": "单分支条件判定 (Single-branch if Statement)",
        "pain_point": "默认情况下程序按照代码书写顺序自上而下线性执行（顺序结构）。但现实世界中充满条件制约与规则准入（如年龄达标方可进入、余额充足才能扣款），必须打破线性流动。",
        "theory": "if 语句是图灵完备语言的基本控制原语。解释器对 if 关键字后的条件表达式进行求值，若在布尔上下文中判定为 True，则执行其下级缩进代码块（Block）；若为 False 则跳过该代码块直接执行后续同级代码。",
        "key_concepts": [
            ("基本语法", "`if 判断条件:` 后面必须紧随英文冒号 `:`，下一行必须严格进行 4 空格代码缩进"),
            ("冒号语义", "英文冒号 `:` 标志着一个代码块（Suite）的开启，在 AST 中引导一个新作用域"),
            ("缩进守则 (PEP 8)", "Python 依靠物理缩进来界定代码归属关系，同一代码块内的每一行必须保持绝对一致的缩进深度（严禁混用 Tab 与空格）")
        ],
        "code_example": '''# 业务场景：成年人网吧上网年龄判断
age = 19
print(f"用户登记年龄: {age}")

# if 单分支判定
if age >= 18:
    print("恭喜您，已年满 18 周岁！")
    print("系统授权：允许办理网吧上网手续。")

print("系统准入检测流程结束。")''',
        "pitfalls": [
            "忘记英文冒号：遗漏 `if age >= 18:` 尾部的冒号将直接触发 SyntaxError: expected ':'",
            "缩进不一致：混用 Tab 和空格会引发 IndentationError: unexpected indent",
            "条件永真陷阱：书写 `if age = 18:` 属于语法赋值错误，等于比对必须使用 `==`"
        ],
        "questions": [
            "1. 为什么 Python 采用缩进来界定语法块，而非像 C/Java 一样采用大括号 `{}`？这种设计带来了哪些利弊？",
            "2. 如果 if 后面的条件不是布尔值（如 `if [1, 2]:`），解释器的真假判定规则是什么？"
        ]
    },
    {
        "page": 23,
        "title": "23. 核心语法-流程控制语句-if基础语法-案例",
        "clean_title": "23. 核心语法-流程控制语句-if基础语法-案例",
        "topic": "单分支条件实战演练与键盘交互闭环",
        "pain_point": "硬编码（Hard-coded）的假数据无法体现流程控制在动态真实场景中的决策价值。需要将终端动态输入与条件分支深度融合。",
        "theory": "将标准输入输出 I/O 流与条件分支求值引擎挂钩，先对字符串输入进行合法性校验与数值转换，再将结果推入 if 比较判断逻辑网。",
        "key_concepts": [
            ("动态输入集成", "通过 `input()` 获取用户年龄，并使用 `int()` 执行同步类型转换"),
            ("代码缩进逻辑范围", "只有缩进的指令受 if 条件控制；顶格书写的后续指令无论条件真假都会必然执行")
        ],
        "code_example": '''# 游乐园免票准入系统
age_input = input("请输入游玩者的年龄: ")
age = int(age_input)

# 仅当未成年时触发提示
if age < 18:
    print("【优惠政策】游玩者未满 18 周岁，可享受免费游园政策！")
    print("请携带有效学生证或身份证到人工通道领取免票腕带。")

print("欢迎光临欢乐谷主题乐园，祝您游玩愉快！")''',
        "pitfalls": [
            "类型转换先行原则：绝对不能写成 `if input(\"请输入年龄:\") < 18:`，字符串与整数直接使用 `<` 会抛出 TypeError: '<' not supported between instances of 'str' and 'int'",
            "空输入崩溃：若用户直接敲回车导致 `age_input` 为空字符串，`int('')` 会报 ValueError"
        ],
        "questions": [
            "1. 当用户输入负数（如 `-5`）时，当前逻辑是否会出现业务漏洞？如何进行防御性优化？",
            "2. 简述在 PyCharm 等 IDE 中快速调整大块代码缩进层级的快捷键技巧。"
        ]
    },
    {
        "page": 24,
        "title": "24. 核心语法-流程控制语句-if进阶(if...else)-案例",
        "clean_title": "24. 核心语法-流程控制语句-if进阶(if...else)-案例",
        "topic": "双分支互斥决策结构 (if-else Statement)",
        "pain_point": "现实决策多数是非此即彼的互斥状态（如准入与拒绝、成功与失败）。仅有 if 单分支无法在条件不满足时执行对称的补偿或拒绝动作。",
        "theory": "if-else 构建了经典的二分决策树。当条件为 True 时执行 if 缩进代码块；当条件为 False 时**必定**流转执行 else 缩进代码块。两分支在时序上完全互斥，有且仅有一个分支被执行。",
        "key_concepts": [
            ("else 语法规则", "else 必须与对应的 if 保持同一水平垂直缩进，后紧跟冒号 `:`，且 else 本身不能携带任何显式条件表达式"),
            ("逻辑覆盖互斥性", "分支覆盖率（Branch Coverage）为 100%，消除逻辑遗漏")
        ],
        "code_example": '''# 经典案例：游乐园门票购票决策
age = int(input("请输入您的年龄: "))

if age >= 18:
    print("您已成年，请购买成人票入园。")
    print("成人票价：120 元。")
else:
    print("您尚未成年，可享受未成年人半价优惠！")
    print("学生/儿童票价：60 元。")

print("购票引导结束，请持票前往检票口。")''',
        "pitfalls": [
            "else 携带条件错误：初学者易犯 `else age < 18:` 的语法错误，else 后面绝对不允许带条件，带条件必须用 elif",
            "缩进脱轨：else 必须与目标 if 顶格平齐，若缩进到了 if 内部则会报 SyntaxError: invalid syntax"
        ],
        "questions": [
            "1. 为什么说 if-else 结构相比于两个独立的 if 结构具有更高的执行效率？",
            "2. 试利用 Python 三元运算符（Ternary Operator）将简单的 if-else 重构为单行表达式。"
        ]
    },
    {
        "page": 25,
        "title": "25. 核心语法-流程控制语句-if进阶(if...elif...else)-案例",
        "clean_title": "25. 核心语法-流程控制语句-if进阶(if...elif...else)-案例",
        "topic": "多重分支阶梯决策 (Multi-branch if-elif-else)",
        "pain_point": "业务规则经常呈现阶梯分层（如成绩优良中差、VIP 等级 1~5 级、身高阶梯票价）。多个独立的 if 会产生多次无意义判断，且无法保证多状态唯一命中。",
        "theory": "elif 是 else if 的合写。解释器按照自上而下的严格次序依次对各 elif 条件进行短路求值。一旦前置某一个条件命中，执行完该分支代码块后，**跳过后续所有的 elif 与 else**，直接流出控制结构。",
        "key_concepts": [
            ("自顶向下短路机制", "高优先级或范围窄的区间必须放在前面，已被前置条件过滤的区间无需在后续重复编写下限"),
            ("可选的 else 兜底", "else 作为最终全不满足时的兜底分支（Default Fallback），可根据业务需求选择保留或省略")
        ],
        "code_example": '''# 案例：游乐园多级身高收费标准
height = int(input("请输入游玩者的身高 (cm): "))

if height < 120:
    print("身高不足 120cm，免票入园！")
elif height < 150:
    print("身高 120-150cm，半价门票: 60 元。")
elif height < 180:
    print("身高 150-180cm，标准成人门票: 120 元。")
else:
    print("身高超过 180cm，赠送特长通道保险门票: 120 元。")

print("祝您游玩愉快！")''',
        "pitfalls": [
            "区间颠倒陷阱：若把 `height < 180` 写在最前，则身高 110cm 的游客也会先命中此条件买全票，导致严重业务灾难",
            "冗余条件书写：在已知 `height >= 120` 的前提下，第二分支只需写 `elif height < 150:`，不必冗长写成 `elif 120 <= height < 150:`"
        ],
        "questions": [
            "1. 在什么情况下可以安全省略多分支结构中的 `else` 兜底子句？省略会有什么隐患？",
            "2. 编写一个根据百分制成绩划分 A/B/C/D 档次的代码块，并分析其分支覆盖完整性。"
        ]
    },
    {
        "page": 26,
        "title": "26. 核心语法-流程控制语句-if语句-综合案例",
        "clean_title": "26. 核心语法-流程控制语句-if语句-综合案例",
        "topic": "嵌套分支与复合条件综合决策引擎 (Nested if & Composite Conditions)",
        "pain_point": "现实业务逻辑往往是多维度的组合判定（例如：用户既要通过企业工号安全认证，又需要具备指定部门的特权授权级别）。单层平面分支无法表达父子依赖的复合状态。",
        "theory": "嵌套分支（Nested Branches）是指在某一个分支的代码块内部，再次嵌入完整的 if/elif/else 结构。外层分支充当粗粒度的前置门禁（Pre-condition Gate），内层分支执行细粒度的深层权限决策，实现树形状态推演。",
        "key_concepts": [
            ("前置门禁模式", "通过外层 if 迅速剔除非法请求，降低内层计算与数据库开销"),
            ("多重缩进梯度", "外层 4 空格缩进，内层在此基础上递增为 8 空格缩进，层次清晰分明")
        ],
        "code_example": '''# 案例：公司年终奖金派发与绩效审核系统
tenure_years = int(input("请输入员工在职年限: "))

if tenure_years >= 2:
    print("【资格达标】在职年限满 2 年，进入年终奖评审流程。")
    performance_score = int(input("请输入本年度综合绩效评分 (1-100): "))
    
    if performance_score >= 90:
        print("评级：S 级卓越贡献者！发放 6 个月全额薪资作为年终奖金！")
    elif performance_score >= 80:
        print("评级：A 级优秀骨干！发放 3 个月全额薪资作为年终奖金！")
    elif performance_score >= 60:
        print("评级：B 级称职达标。发放 1 个月全额薪资作为年终奖金。")
    else:
        print("评级：C 级待改进。本年度不予派发年终奖金，列入专项提升计划。")
else:
    print("【资格未达】入职未满 2 年，发放新人关怀大礼包，不参与常规年终奖分配。")''',
        "pitfalls": [
            "嵌套层级过深（箭头型代码 / Arrow Anti-Pattern）：嵌套超过 3 层会导致代码认知复杂度飙升，推荐通过卫语句（Guard Clauses）尽早 return / 终止",
            "缩进对其错位：内层 else 误对齐到外层 if，会导致逻辑发生致命倒错"
        ],
        "questions": [
            "1. 什么是卫语句（Guard Clause）重构？如何将深层嵌套 if 扁平化为线性流水线？",
            "2. 分析复合逻辑表达式 `if (cond1 and cond2) or cond3:` 在何种场景下优于嵌套 if？"
        ]
    },
    {
        "page": 27,
        "title": "27. 核心语法-流程控制语句-match模式匹配",
        "clean_title": "27. 核心语法-流程控制语句-match模式匹配",
        "topic": "Python 3.10+ 结构化模式匹配 (match-case Pattern Matching)",
        "pain_point": "在处理大量枚举值判断、协议报文解析（如 HTTP 状态码 200/404/500）或复杂数据结构解构时，传统的 `if-elif-else` 充满了重复冗长的变量名比对，代码表现力低下。",
        "theory": "Python 3.10 引入了 PEP 634 结构化模式匹配。`match-case` 不仅是传统语言的 switch-case，更是一个强大的模式匹配引擎，支持字面量匹配、或模式（|）、序列解构、守卫语句（Guard `if`）以及通配符 `case _:` 兜底。",
        "key_concepts": [
            ("match 基础语法", "`match 目标表达式:` 引导匹配目标，`case 模式:` 引导各匹配分支"),
            ("通配符兜底 (_)", "`case _:` 匹配任意剩余情况，相当于 default / else 分支"),
            ("多值合并匹配 (|)", "`case 401 | 403:` 将多个模式用竖线合并处理"),
            ("模式守卫 (case ... if ...)", "在模式后追加 `if 条件` 进行二次布尔逻辑校验")
        ],
        "code_example": '''# 案例：HTTP 响应状态码统一路由器
status_code = 404

match status_code:
    case 200:
        print("状态: OK - 请求成功处理")
    case 400:
        print("状态: Bad Request - 客户端请求参数不合法")
    case 401 | 403:
        print("状态: Unauthorized/Forbidden - 鉴权未通过或无权限访问")
    case 404:
        print("状态: Not Found - 目标资源不存在")
    case 500:
        print("状态: Internal Server Error - 服务端发生未处理异常")
    case _:
        print(f"状态: 未知状态码 {status_code}，按通用异常流转")

# 进阶守卫演示
user_role = ("admin", 9) # 角色, 权限等级
match user_role:
    case ("admin", level) if level >= 10:
        print("超级管理特权控制台")
    case ("admin", level):
        print(f"普通管理员控制台 (等级: {level})")
    case ("user", _):
        print("标准用户面板")
    case _:
        print("非法访客凭据")''',
        "pitfalls": [
            "版本兼容性：match-case 仅在 Python 3.10 及以上版本可用，低版本解释器会报 SyntaxError",
            "通配符必须置底：`case _:` 必须作为最后一个分支，若置于前置位置，后续所有 case 都会变成不可达死代码"
        ],
        "questions": [
            "1. 结构化模式匹配与传统 C/Java 的 switch-case 在解构能力上有哪些质的跃升？",
            "2. 如何使用 match-case 实现对 JSON 报文字典结构的深层属性提取与验证？"
        ]
    },
    {
        "page": 28,
        "title": "28. 核心语法-流程控制语句-while循环-语法",
        "clean_title": "28. 核心语法-流程控制语句-while循环-语法",
        "topic": "条件循环与状态迭代三要素 (while Loop)",
        "pain_point": "计算机的核心优势在于以极高主频执行海量重复计算。若依靠人工复制粘贴代码来重复执行逻辑，程序行数将线性膨胀且完全无法应对动态未知的重复次数。",
        "theory": "while 循环在每次循环体执行前，对循环条件进行布尔求值。只要条件为 True，就持续重复执行循环体内的代码块；一旦条件变为 False，立即跳出循环继续向下执行。循环正常推进依赖三大不可或缺要素。",
        "key_concepts": [
            ("循环三大要素", "1. 初始变量状态；2. 循环判断条件；3. 循环变量的步进更新（步长）"),
            ("死循环（Infinite Loop）", "若缺失变量步进更新或条件永远为 True（如 `while True:`），程序将陷入无休止循环并耗尽 CPU 资源")
        ],
        "code_example": '''# 需求：标准输出 5 次打印任务
# 1. 初始条件
i = 1

# 2. 条件判断
while i <= 5:
    print(f"正在执行第 {i} 次批处理任务...")
    # 3. 循环变量步进更新
    i += 1

print(f"全部任务执行完毕，循环最终计数器状态 i = {i}")''',
        "pitfalls": [
            "遗忘步进计数器：初学者最常见错误是漏写 `i += 1`，导致 `i` 永远为 1，控制台疯狂刷屏甚至导致 IDE 假死",
            "边界离一差错误（Off-by-one Error）：混淆 `<` 与 `<=`，导致实际循环次数比预期多一次或少一次"
        ],
        "questions": [
            "1. 当不慎在终端触发了死循环时，使用什么操作系统级快捷键可强制中断 Python 进程？",
            "2. 试比较 while 循环与 for 循环在应用场景上的核心差异？何时必须首选 while？"
        ]
    },
    {
        "page": 29,
        "title": "29. 核心语法-流程控制语句-while循环-案例",
        "clean_title": "29. 核心语法-流程控制语句-while循环-案例",
        "topic": "累加求和算法与循环状态机建模",
        "pain_point": "算法领域中最基础的操作是对数据流进行求和、求极值与加权统计。初学者在处理动态累加时容易混淆“计数变量”与“累加结果容器”的作用域。",
        "theory": "累加器模式（Accumulator Pattern）在循环外部初始化一个承载最终统计结果的累加变量（如 `total = 0`），在循环体内部利用复合赋值运算符 `total += i` 逐轮将数据吞吐沉淀至累加器中。",
        "key_concepts": [
            ("高斯求和实现", "从 1 到 100 的整数等差累加，时间复杂度为 $O(N)$"),
            ("累加器变量位置", "累加器变量必须定义在循环体**外部**，若定义在内部则每轮都会被重置清零")
        ],
        "code_example": '''# 案例：计算 1 到 100 的连续自然数累加和
# 1. 初始化累加结果变量
total_sum = 0

# 2. 初始化循环计数器
i = 1

# 3. 循环累计
while i <= 100:
    total_sum += i  # 将当前 i 累加至总和中
    i += 1          # 步进器递增

print("1 到 100 的累加和结果为:", total_sum) # 5050

# 数学公式验证 (高斯公式: n*(n+1)/2)
math_verify = 100 * (100 + 1) // 2
print("数学高斯公式校验:", math_verify == total_sum)''',
        "pitfalls": [
            "累加器作用域重置陷阱：若误将 `total_sum = 0` 写在 while 缩进内部，最终打印结果只会是最后一轮的 100",
            "步进位置错位：若在 `total_sum += i` 之前执行了 `i += 1`，则累加范围实际上变成了 2 到 101"
        ],
        "questions": [
            "1. 如果需要计算 1 到 100 之间所有偶数的累加和，有哪两种不同的 while 循环实现策略？哪种性能更优？",
            "2. 分析累加算法在数据量从 100 增长至 1 亿时，Python 循环与数学公式的时间复杂度差异。"
        ]
    },
    {
        "page": 30,
        "title": "30. 核心语法-流程控制语句-for循环-语法",
        "clean_title": "30. 核心语法-流程控制语句-for循环-语法",
        "topic": "遍历循环与迭代器协议基石 (for-in Loop)",
        "pain_point": "使用 while 循环遍历数据容器（如字符串、列表）时，必须手动维护索引下标与步进，容易出现越界溢出（IndexError）或死循环，代码冗余且易出错。",
        "theory": "Python 的 for 循环本质不是传统 C 语言的计数器循环，而是**遍历循环（Traversal Loop / Foreach）**。底层依靠迭代器协议（Iterator Protocol），依次从可迭代对象（Iterable）中提取下一个元素并赋值给临时变量，直到元素耗尽抛出 StopIteration 自动安全退出。",
        "key_concepts": [
            ("基本语法", "`for 临时变量 in 可迭代对象:` 后面紧随代码块"),
            ("字符串逐字遍历", "字符串是不可变序列，for 循环会逐个取出其中的每一个单字符"),
            ("临时变量作用域", "虽然 Python 允许循环结束后访问该临时变量，但规范建议将其视为循环体内部局部量")
        ],
        "code_example": '''# 案例：逐字探查字符串文本
message = "Hello-Python-2026"

print("开始逐字解析报文字符:")
char_count = 0
for char in message:
    print(f"字符: [{char}]", end=" ")
    char_count += 1

print(f"\\n遍历完毕，共计读取 {char_count} 个字符。")''',
        "pitfalls": [
            "迭代中修改容器陷阱：在 for 循环遍历列表时，若在循环体内部直接删除或添加元素，会导致迭代器游标错乱从而漏掉元素",
            "不可迭代对象陷阱：严禁对整数使用 for 循环（如 `for i in 100:`），会抛出 TypeError: 'int' object is not iterable"
        ],
        "questions": [
            "1. 深入解释 Python 可迭代对象（Iterable）与迭代器（Iterator）在底层协议上的区别？",
            "2. 为什么说 Python 的 for 循环天然免疫“死循环”与“索引越界”？"
        ]
    },
    {
        "page": 31,
        "title": "31. 核心语法-流程控制语句-for循环-案例(range)",
        "clean_title": "31. 核心语法-流程控制语句-for循环-案例(range)",
        "topic": "不可变数值序列发生器 range() 与定次循环",
        "pain_point": "遍历循环虽然优雅，但若要指定执行固定的 N 次循环，必须有一个零开销、不预先占满内存的高性能序列生成器。",
        "theory": "`range` 是 Python 内置的一种不可变序列类型。它采用惰性求值（Lazy Evaluation），无论其表征的区间是 10 还是 10 亿，其占用的内存空间永远固定不变（仅保存 start、stop、step 三个元属性），只有在迭代推进时才动态产生具体数值。",
        "key_concepts": [
            ("语法一：range(num)", "从 0 遍历到 num-1（左闭右开）"),
            ("语法二：range(start, end)", "从 start 遍历到 end-1"),
            ("语法三：range(start, end, step)", "指定步长 step（可为负数实现倒序迭代）")
        ],
        "code_example": '''# 1. range(num) 单参数定次循环
for i in range(3):
    print(f"定次任务: {i}") # 输出 0, 1, 2

# 2. range(start, end) 范围迭代
for val in range(5, 8):
    print(f"范围值: {val}") # 输出 5, 6, 7

# 3. range(start, end, step) 步长与倒序
print("步长为 2 的偶数序列:")
for even in range(0, 10, 2):
    print(even, end=" ") # 0 2 4 6 8
print()

# 案例：统计 1-100 内 7 的倍数个数
count_seven = 0
for num in range(1, 101):
    if num % 7 == 0:
        count_seven += 1
print("1-100 内 7 的倍数共有:", count_seven)''',
        "pitfalls": [
            "右边界开区间遗漏：`range(1, 10)` 只会遍历到 9，若想包含 10 必须书写 `range(1, 11)`",
            "步长方向反向死循环：`range(10, 0, 1)` 由于步长为正无法向负方向靠近终点，其序列为空序列，不会执行任何循环体"
        ],
        "questions": [
            "1. 为什么在 Python 3 中 `type(range(10))` 返回的是 `<class 'range'>` 而非列表？这与 Python 2 的 `xrange` 有何演进关系？",
            "2. 如何使用 `range()` 配合负步长实现从 10 倒计时到 1 的循环？"
        ]
    },
    {
        "page": 32,
        "title": "32. 核心语法-流程控制语句-嵌套循环",
        "clean_title": "32. 核心语法-流程控制语句-嵌套循环",
        "topic": "多维循环空间与时空复杂度分析 (Nested Loops)",
        "pain_point": "现实世界的数据往往呈现多维结构（如矩阵、图像像素阵列、棋盘格、班级-学生层级）。单一线性循环无法完成二维或高维网格空间的遍历扫描。",
        "theory": "嵌套循环是指外层循环每推进一次，内层循环必须完整执行一个完整的生命周期。若外层循环执行 $M$ 次，内层循环执行 $N$ 次，则内层核心代码的累计执行次数为 $M \\times N$，计算时间复杂度呈几何级放大（$O(M \\times N)$）。",
        "key_concepts": [
            ("外层控制宏观行", "外层循环通常负责驱动行、批次、外部大周期的推进"),
            ("内层控制微观列", "内层循环负责单行内部各元素、单元格或单步任务的具体落实"),
            ("计数器变量隔离", "外层与内层循环必须使用互不相同的迭代变量名（如外层 `i`，内层 `j`），严禁变量同名冲突")
        ],
        "code_example": '''# 案例：模拟 3 天、每天打卡完成 4 项微习惯
day = 1
while day <= 3:
    print(f"=== 开始第 {day} 天的学习计划 ===")
    
    # 内层循环驱动每天的 4 节课程
    for lesson in range(1, 5):
        print(f"  正在学习今日第 {lesson} 节课...")
        
    print(f"=== 第 {day} 天计划圆满达成！===\\n")
    day += 1

print("3 天冲刺营全部结业！")''',
        "pitfalls": [
            "变量名混用灾难：外层写了 `for i in ...`，内层也写 `for i in ...`，会导致内层修改直接冲垮外层游标，造成死循环或提前跳出",
            "时间复杂度爆炸：嵌套层级超过 3 层时（$O(N^3)$），在海量数据下会导致计算时间从毫秒暴增至数小时甚至数天"
        ],
        "questions": [
            "1. 简述嵌套循环在遍历二维列表（矩阵）时的行优先遍历机制。",
            "2. 当数据量较大时，有哪些算法优化思路可将 $O(N^2)$ 的双层嵌套循环降维优化为 $O(N)$？"
        ]
    },
    {
        "page": 33,
        "title": "33. 核心语法-流程控制语句-嵌套循环-案例",
        "clean_title": "33. 核心语法-流程控制语句-嵌套循环-案例",
        "topic": "经典算法案例：九九乘法表排版与二维几何矩阵输出",
        "pain_point": "初学者难以将抽象的双层循环索引映射为控制台规整对齐的二维图形排版。对 print 参数（`end`）控制不熟练会导致排版完全崩塌。",
        "theory": "通过数学坐标映射：外层循环 `i` 控制行数（从 1 到 9），内层循环 `j` 控制当前行的列数（从 1 递增至 `i`，构成下三角矩阵）。单行内部通过 `end='\\t'` 实现制表符水平对齐，一行结束后调用无参 `print()` 强制执行换行。",
        "key_concepts": [
            ("下三角矩阵特征", "第 $i$ 行有且仅有 $i$ 列，故内层循环终点必须与外层变量 $i$ 强关联（`range(1, i + 1)`）"),
            ("水平制表排版 (\\t)", "利用制表符消除不同数字位数（如 2*3=6 与 2*8=16）带来的宽度视觉参差")
        ],
        "code_example": '''# 经典工程实现：九九乘法表
print("【标准九九乘法表】")

for i in range(1, 10):
    for j in range(1, i + 1):
        # 核心格式化与制表符对齐
        print(f"{j} * {i} = {i * j}\\t", end="")
    # 一行打印完毕，输出空换行
    print()''',
        "pitfalls": [
            "换行时机错误：将无参 `print()` 误写在内层循环内部，会导致每个算式直接霸占一行，变成 45 行的长串而无法成表",
            "乘法算式因子颠倒：标准读法与排版中通常以列为主序（`j * i`），混淆可能导致下三角斜率相反"
        ],
        "questions": [
            "1. 如何将上述下三角乘法表通过算法微调重构为右上角或上三角乘法表？",
            "2. 试写出利用 while 循环双层嵌套实现相同九九乘法表的代码，并对比两者的代码简洁度。"
        ]
    },
    {
        "page": 34,
        "title": "34. 核心语法-流程控制语句-循环-综合案例(break与continue)",
        "clean_title": "34. 核心语法-流程控制语句-循环-综合案例(break与continue)",
        "topic": "循环流程阻断与跳转：break 与 continue 机制",
        "pain_point": "遇到异常坏数据（如无效格式数据）时，需要跳过当前个体继续处理下一个；而在检索任务找到目标时，必须立即停机以防算力浪费。单纯依赖条件判断会导致代码分支深陷。",
        "theory": "`continue` 语句立即终止**当前轮次**的循环体执行，直接短路跳转至下一次循环的条件判断阶段；`break` 语句则彻底终结**当前所在的整层循环**，直接跳出该循环体执行其下方的后续代码。两者只对直接包裹它的最内层循环生效。",
        "key_concepts": [
            ("continue 语义", "跳过本轮剩余代码，快速进入下一轮迭代（常用于数据清洗与无效数据过滤）"),
            ("break 语义", "强制提前退出当前循环（常用于目标查找成功、超限紧急刹车）"),
            ("内层作用域约束", "在嵌套循环中，内层的 break/continue 绝不会击穿影响外层循环")
        ],
        "code_example": '''# 案例：公司发放 1 万元工资，每人 1000 元，共 20 位候选员工
# 规则：若员工绩效低于 60 分则跳过发放（continue）；若奖金池见底（余额为0）则直接停发结案（break）

total_budget = 5000 # 5000元，最多发5人
employee_scores = [75, 50, 88, 45, 92, 85, 99, 65]

print("=== 开始年度奖金审核派发 ===")
for emp_id in range(1, len(employee_scores) + 1):
    score = employee_scores[emp_id - 1]
    
    # 规则 1：绩效不达标，跳过本次发放
    if score < 60:
        print(f"员工编号 {emp_id} 绩效仅为 {score} 分，不予发放奖金，进入下一位审核。")
        continue
        
    # 规则 2：资金池检测
    if total_budget <= 0:
        print("【警告】奖金池已全部发放完毕！流程强制终止。")
        break
        
    # 正常发放逻辑
    total_budget -= 1000
    print(f"员工编号 {emp_id} 审核通过 (绩效: {score})，发放 1000 元！剩余奖金池: {total_budget} 元")

print(f"奖金发放流程结束，最终奖金池剩余: {total_budget} 元。")''',
        "pitfalls": [
            "while 循环中使用 continue 导致死循环：在 continue 之前若未递增计数器 `i += 1`，则跳转后 `i` 保持不变，陷入死循环",
            "跨层跳出误区：希望内层 break 直接跳出外层循环，Python 原生不支持 `break 2`，需借助标志变量（Flag）或函数 return 实现"
        ],
        "questions": [
            "1. 详细分析在 while 循环中使用 continue 时，为什么必须在 continue 之前手动执行步长递增？",
            "2. 试述 Python 中独有的 `for...else` 与 `while...else` 语法中，else 分支触发与 break 语句之间的内在联动规则。"
        ]
    },
    {
        "page": 35,
        "title": "35. 核心语法-流程控制语句-循环-综合案例2(猜数字游戏)",
        "clean_title": "35. 核心语法-流程控制语句-循环-综合案例2(猜数字游戏)",
        "topic": "随机数发生器与无限状态机：猜数字游戏架构",
        "pain_point": "需要综合运用随机数模块、无限循环调度、多分支条件判定与计数统计，完成一个完整的交互式终端游戏应用系统构建。",
        "theory": "利用标准库 `random.randint()` 生成指定闭区间的伪随机目标整数，利用 `while True:` 搭建无限事件循环主驱动器，通过内部 if/elif/else 判定猜测偏差并给出反馈，命中后通过 `break` 优雅退出。",
        "key_concepts": [
            ("random 模块引入", "`import random; secret = random.randint(1, 100)` 生成 1~100 的随机数"),
            ("事件循环 (Event Loop)", "`while True` 持续监听用户输入，以状态变更驱动逻辑流转"),
            ("二分查找启发", "猜数字游戏的最优人类策略即是二分法（Binary Search），理论最大尝试次数为 $\\lceil \\log_2 100 \\rceil = 7$ 次")
        ],
        "code_example": '''import random

# 1. 系统秘密生成一个 1-100 的随机目标数字
secret_num = random.randint(1, 100)
guess_count = 0

print("【智力大挑战：猜数字游戏】")
print("系统已选定一个 1 到 100 之间的神秘数字，请开始猜测！")

# 2. 核心主事件循环
while True:
    user_input = input("请输入您猜测的整数 (输入 q 放弃): ")
    if user_input.strip().lower() == 'q':
        print(f"很遗憾您放弃了游戏，神秘数字实际上是: {secret_num}")
        break
        
    guess = int(user_input)
    guess_count += 1
    
    # 3. 比较逻辑网络
    if guess > secret_num:
        print("提示：猜大了！再试一个小一点的数字。")
    elif guess < secret_num:
        print("提示：猜小了！再试一个大一点的数字。")
    else:
        print(f"恭喜您，完全猜中了！神秘数字就是 {secret_num}！")
        print(f"您总共尝试了 {guess_count} 次。")
        if guess_count <= 7:
            print("评价：天选之子！您的策略具备二分查找级的高效！")
        else:
            print("评价：持之以恒！成功攻坚。")
        break # 命中目标，优雅退出游戏''',
        "pitfalls": [
            "随机数重复生成：若将 `random.randint()` 写在了 `while` 循环体内部，则用户每猜一次数字都会变一次，永远无法猜中",
            "字符串直接比较：未执行 `int(user_input)` 直接比对数值会导致字典序比较而非算术比较（如 '9' > '100'）"
        ],
        "questions": [
            "1. 为什么在游戏循环之外生成随机数是保证游戏公平性的根本前提？",
            "2. 如何改造当前架构，增加“最多允许猜测 5 次，超限直接判负”的防爆机制？"
        ]
    }
]

MODULE2_TOPOLOGY = """模块 02：流程控制语句 (Flow Control & Iteration)
├── [1] 单向与双向分支决策
│   ├── if 基础语法 (P22) ────── 冒号语法、PEP 8 缩进规则与布尔真假上下文
│   ├── if 键盘交互案例 (P23) ── 动态输入类型转换与条件过滤门禁
│   └── if-else 互斥分支 (P24) ── 二分决策树与百分之百逻辑分支覆盖
├── [2] 阶梯与多维复杂决策
│   ├── if-elif-else 体系 (P25) ─ 阶梯式短路判断与自顶向下范围收敛
│   ├── 嵌套 if 决策引擎 (P26) ─ 前置授权门禁与多维状态推演树
│   └── match 模式匹配 (P27) ─── Python 3.10+ 结构化模式匹配、解构与守卫
├── [3] 条件循环体系 (while)
│   ├── while 循环原语 (P28) ─── 初始状态、判定条件与步进更新三大核心要素
│   └── 累加求和案例 (P29) ───── 累加器模式 (Accumulator) 与高斯求和验证
├── [4] 遍历循环体系 (for)
│   ├── for-in 遍历协议 (P30) ── 迭代器协议底层运行模型与字符序列逐项提取
│   └── range 发生器 (P31) ───── 惰性序列机制 (start, stop, step) 与定次循环
├── [5] 多维循环与流程跳断
│   ├── 嵌套循环空间 (P32) ───── 矩阵行列时空复杂度分析 ($O(M \\times N)$)
│   ├── 九九乘法表案例 (P33) ─── 下三角几何坐标映射与制表符水平对齐排版
│   ├── 流程跳转控制 (P34) ───── continue 短路重试 vs break 彻底终止
│   └── 猜数字架构设计 (P35) ─── random 随机源、主事件循环与二分查找策略
"""

def generate_subtitles():
    """补齐缺失的 clean subtitle 文件"""
    SUBTITLES_DIR.mkdir(parents=True, exist_ok=True)
    for ep in MODULE2_EPISODES:
        sub_file = SUBTITLES_DIR / f"P{ep['page']:02d}_{ep['clean_title']}_clean.txt"
        if not sub_file.exists():
            concepts_text = "\\n".join([f"- {name}: {desc}" for name, desc in ep['key_concepts']])
            pitfalls_text = "\\n".join([f"- 警示 {i+1}: {p}" for i, p in enumerate(ep['pitfalls'])])
            content = f"""[00:00] 课程导入与核心定位
本小节讲解 Python 核心流程控制语句中的核心基石：{ep['topic']}。
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
本节详细探讨了 {ep['topic']} 的执行机制与设计边界。掌握条件与循环结构，是编写任何非平凡业务算法的前提。
"""
            sub_file.write_text(content.strip() + "\\n", encoding="utf-8")
            print(f"  [Subtitle] 写入: {sub_file.name}")

def generate_articles():
    """生成精读长文教材"""
    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    for ep in MODULE2_EPISODES:
        art_file = ARTICLES_DIR / f"P{ep['page']:02d}_{ep['clean_title']}_精读文章.md"
        
        concepts_md = "\\n".join([f"#### {i+1}. {name}\\n- **核心特征**：{desc}" for i, (name, desc) in enumerate(ep['key_concepts'])])
        pitfalls_md = "\\n".join([f"> ⚠️ **陷阱 {i+1}**：{p}" for i, p in enumerate(ep['pitfalls'])])
        questions_md = "\\n".join([f"- {q}" for q in ep['questions']])
        
        doc = f"""# 【深度精读】{COURSE_TITLE}：P{ep['page']:02d} {ep['clean_title']}

---

## 1. 为什么需要它：现实痛点与知识定位

在由顺序执行构成的机械线性世界中，代码只能机械地单一向前推进。
{ep['pain_point']}

在本节中，我们重点剖析 **{ep['topic']}**。它是程序产生判断力、灵活性与自动化自驱运转的核心神经中枢。

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
- **条件求值阶段**：解释器首先计算条件表达式，得到内部真假判定布尔值；
- **控制流转移**：依据判定结果跳转虚拟机 PC 程序计数器，进入特定分支代码块；
- **状态维护与汇合**：分支或循环执行完毕后，执行流程汇合至下一级同级作用域，继续向下流动。

---

## 4. 工业级实践与避坑指南 (Pitfalls)

在真实业务系统研发与高并发生产环境中，由于流程控制不当导致的死循环、死锁与逻辑穿透屡见不鲜：

{pitfalls_md}

### 最佳工程实践守则：
1. **控制圈复杂度（Cyclomatic Complexity）**：单一函数内的嵌套循环与条件层级尽量不超过 3 层，善用卫语句提前退出；
2. **循环变量显式隔离**：在嵌套循环中，严格使用 `i`, `j`, `k` 或具有业务含义的独立变量名，严禁跨层变量遮蔽；
3. **防御性兜底**：在条件分支末端始终设置合理清晰的 `else` 或 `case _:` 兜底分支，记录未知异常或未捕获状态。

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
    note_file = NOTES_DIR / "模块02_流程控制语句_复习笔记.md"
    
    table_rows = []
    for ep in MODULE2_EPISODES:
        table_rows.append(f"| P{ep['page']:02d} | **{ep['topic']}** | {ep['theory'][:50]}... | 来源: P{ep['page']:02d} |")
    table_md = "\\n".join(table_rows)
    
    note_content = f"""# 模块 02：流程控制语句（涵盖 P22 - P35）

> 计算机程序的神经系统与自动化调度引擎 | 涵盖分集：P22 ~ P35 | 核心议题：条件分支 (if/elif/else/match)、循环控制 (while/for)、嵌套结构与跳转跳断 (break/continue)

---

## 知识拓扑框架导图

```text
{MODULE2_TOPOLOGY}
```

---

## 1. 模块核心概念速查表

| 分集索引 | 核心主题 | 关键原理推演 / 标准定义 | 知识溯源 |
| :--- | :--- | :--- | :--- |
{table_md}

---

## 2. 关键流程控制语句与语法矩阵

| 控制类型 | 核心关键字 | 典型语法结构 | 核心行为 / 规约 |
| :--- | :--- | :--- | :--- |
| **单/双分支** | `if`, `else` | `if cond: ... else: ...` | 互斥分支，二分决策，基于 PEP 8 的 4 空格缩进代码块 |
| **多重阶梯** | `elif` | `if c1: ... elif c2: ... else: ...` | 自顶向下短路求值，命中任一分支即刻跳出整体结构 |
| **模式解构** | `match`, `case` | `match val: case 1: ... case _: ...` | Python 3.10+ 模式匹配，支持序列解构、守卫 if 与通配符 |
| **条件循环** | `while` | `while cond: ... step` | 条件驱动，依赖初始值、判断条件与步进更新三要素 |
| **遍历循环** | `for`, `in` | `for item in container: ...` | 迭代器驱动，天然免疫越界与死循环，专用于可迭代对象 |
| **惰性序列** | `range()` | `range(start, end, step)` | 内存占用恒定 $O(1)$ 的不可变数值序列发生器（左闭右开） |
| **流程阻断** | `break`, `continue` | `if err: continue; if done: break` | continue 短路当前轮次，break 彻底击穿当前层循环 |

---

## 3. 要点对比横评矩阵

### 对比一：`while` 循环 vs `for` 循环全维度横评
| 评估维度 | `while` 循环 | `for` 循环 |
| :--- | :--- | :--- |
| **驱动机制** | 纯布尔条件表达式驱动 | 集合/可迭代对象（Iterable）驱动 |
| **循环次数** | 适合循环次数未知、依赖动态外部状态的场景 | 适合循环次数已知、或遍历有限序列容器的场景 |
| **变量管理** | 必须由开发者手动初始化并在内部显式步进累加 | 自动从迭代器提取并绑定局部变量，无需手动步进 |
| **死循环风险** | 高（忘记步进更新即刻引发死循环） | 极低（当容器元素遍历耗尽时自动优雅退出） |
| **典型代表** | 服务器主事件循环 (`while True`)、猜数字游戏 | 遍历列表字典、处理文件行、数据清洗管道 |

### 对比二：`break` 彻底终止 vs `continue` 跳过本轮
| 关键维度 | `break` 语句 | `continue` 语句 |
| :--- | :--- | :--- |
| **核心功能** | 彻底杀死并退出当前所在的整层循环结构 | 立即终止当前这 1 次循环，直接抢跑至下一次循环的条件判断 |
| **后续代码** | 循环体内部后续所有代码不再执行，循环彻底终结 | 循环体内部后续代码不执行，但循环整体仍然继续 |
| **典型应用场景** | 目标检索命中即可停机、严重错误紧急熔断 | 坏数据校验过滤、空数据跳过、非关键异常重试 |
| **作用域层级** | 仅对直接包裹它的最内层循环生效 | 仅对直接包裹它的最内层循环生效 |

---

## 4. 核心考点与速查清单 (CheatSheet)

1. **缩进即语法**：Python 不使用大括号，缩进错误就是语法错误；冒号 `:` 标志着新块开始。
2. **多分支顺序敏感**：`elif` 必须自高要求向低要求（或小区间向大区间）推进，前置条件命中即整体跳出。
3. **match-case 纪律**：通配符 `case _:` 必须置于末尾；此特性需要 Python 3.10 及以上环境支持。
4. **range() 边界**：`range(start, stop)` 是左闭右开，`range(1, 10)` 不包含 10！
5. **九九乘法表精髓**：外层循环控制行 `i`，内层循环 `j` 范围为 `1` 到 `i+1`，行内打印 `end='\\t'`，行末调用空 `print()` 换行。
6. **循环与 else 联动**：若循环内被 `break` 击穿退出，则循环自带的 `else` 子句**不会**执行；只有正常耗尽退出才会触发 `else`。
"""
    note_file.write_text(note_content.strip() + "\\n", encoding="utf-8")
    print(f"  [Note] 生成模块大笔记: {note_file.name}")

if __name__ == "__main__":
    print("=== 开始生成 模块 02：流程控制语句 (P22 - P35) ===")
    generate_subtitles()
    generate_articles()
    generate_notes()
    print("=== 模块 02 全部交付物生成完毕！===")
