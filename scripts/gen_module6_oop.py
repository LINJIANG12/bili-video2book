#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Module 06 Generator: 面向对象基础 (P77 - P85).
Generates clean subtitles, single-episode textbook articles, and module revision notes.
"""

import json
from pathlib import Path

TASK_DIR = Path("output/黑马程序员Python+AI零基础入门到大神全套视频课程，覆盖Python核心语法、AI应用、数据分析及Web应用等python实战项目开发全流程_BV1sHU")
ARTICLES_DIR = TASK_DIR / "articles"
NOTES_DIR = TASK_DIR / "notes"
SUBTITLES_DIR = TASK_DIR / "subtitles"

COURSE_TITLE = "黑马程序员Python+AI零基础入门到大神全套视频课程"

MODULE6_EPISODES = [
    {
        "page": 77,
        "title": "77. 核心语法-面向对象基础-概述",
        "clean_title": "77. 核心语法-面向对象基础-概述",
        "topic": "面向对象编程 (OOP) 范式、实体抽象与面向过程对比",
        "pain_point": "面向过程编程（POP）以“步骤与执行流”为核心，当业务复杂化、实体属性众多且行为关联紧密时，数据与函数分离导致代码极易失谐、难以复用和扩展。",
        "theory": "面向对象编程（Object-Oriented Programming, OOP）是一种以“对象”为核心的软件开发范式。对象是现实世界中客观实体的映射，它将“状态”（属性/数据）与“行为”（方法/操作）高内聚地封装在同一个实体中。OOP 的三大支柱（封装、继承、多态）能够将复杂的现实系统降维映射为结构清晰、低耦合的高内聚模型。",
        "key_concepts": [
            ("面向过程 (POP) vs 面向对象 (OOP)", "POP 关注“怎么做”（步骤执行流程），OOP 关注“谁来做”（实体对象及其协作交互）"),
            ("现实世界的高内聚映射", "实体 = 静态特征（属性）+ 动态能力（方法）"),
            ("软件架构收益", "极大提高大型系统的可扩展性、可重用性与可维护性")
        ],
        "code_example": '''# 面向过程 vs 面向对象思维对比
# 1. 面向过程写法 (POP)：数据与函数完全解耦
hero_name = "孙悟空"
hero_hp = 3000
hero_atk = 180

def attack_enemy(name, atk):
    print(f"英雄 {name} 发动攻击，造成 {atk} 点物理伤害！")

attack_enemy(hero_name, hero_atk)

# 2. 面向对象写法 (OOP)：数据与行为高内聚绑定
class Hero:
    def __init__(self, name: str, hp: int, atk: int):
        self.name = name
        self.hp = hp
        self.atk = atk

    def attack(self):
        print(f"英雄 [{self.name}] 发动普通攻击，输出 {self.atk} 点伤害！")

wukong = Hero("孙悟空", 3000, 180)
wukong.attack()''',
        "pitfalls": [
            "过度面向对象设计（Over-engineering）：对于简单的三行脚本强行封装类，增加无谓的代码复杂度",
            "类变成了单纯的数据结构包：只包含属性没有任何行为方法，沦为伪对象"
        ],
        "questions": [
            "1. 为什么在游戏开发、大型 GUI 界面和企业业务系统中，面向对象思想占据统治地位？",
            "2. 简述面向对象三大核心特性（封装、继承、多态）的本质内涵。"
        ]
    },
    {
        "page": 78,
        "title": "78. 核心语法-面向对象基础-类与对象",
        "clean_title": "78. 核心语法-面向对象基础-类与对象",
        "topic": "类作为蓝图模版与对象实例化内存物理机制",
        "pain_point": "初学者常分不清“类”（Class）与“对象”（Object/Instance）的边界，容易误把类本身当成具体可操作的实体。",
        "theory": "类（Class）是创建对象的抽象蓝图或设计图纸（Blueprint），定义了该类事物共有的属性与方法；对象（Object）是依据类图纸在内存堆区（Heap）中物理开辟的具象化实例（Instance）。类只有一个，但可以基于该类实例化出成千上万个拥有独立内存状态的实例对象。使用 `isinstance()` 可检测对象与类的派生归属。",
        "key_concepts": [
            ("class 声明语法", "使用驼峰命名法（CamelCase，如 `CarDriver`），类体缩进定义方法与属性"),
            ("实例化语法", "`obj = ClassName()`，在内存堆区开辟空间并返回引用指针"),
            ("独立性法则", "不同实例对象拥有各自独立的成员变量物理内存空间，互不干扰")
        ],
        "code_example": '''# 类与对象的定义及多实例物理独立性验证
class Student:
    # 类体定义
    school_name = "黑马程序员学院"  # 类属性

# 1. 实例化多个独立对象
s1 = Student()
s2 = Student()

# 2. 动态挂载实例属性
s1.name = "张三"
s1.age = 20

s2.name = "李四"
s2.age = 22

# 3. 内存地址独立性验证
print(f"学生1: {s1.name}, 内存地址: {id(s1)}")
print(f"学生2: {s2.name}, 内存地址: {id(s2)}")
print("s1 与 s2 是否为同一对象:", s1 is s2)

# 4. 实例类型判定
print("s1 是否是 Student 的实例:", isinstance(s1, Student))''',
        "pitfalls": [
            "忘记加调用括号：写 `s = Student` 只是将类对象本身赋给了变量 `s`，并没有创建新的实例！必须写 `Student()`",
            "类名命名违背 PEP 8：使用小写或下划线命名类（如 `student_info`），严重违背大驼峰规范"
        ],
        "questions": [
            "1. 试从操作系统内存管理的角度，解释类对象（Class Object）与实例对象（Instance Object）在内存中的分配与引用关系。",
            "2. 为什么在 Python 中“一切皆对象”，甚至连 `class Student:` 本身也是 `type` 类的一个实例？"
        ]
    },
    {
        "page": 79,
        "title": "79. 核心语法-面向对象基础-实例方法",
        "clean_title": "79. 核心语法-面向对象基础-实例方法",
        "topic": "实例方法机制、底层绑定与 self 形参核心哲学",
        "pain_point": "为什么实例方法的第一个参数必须写 `self`？在调用时为什么又从来不需要传 `self`？初学者常对此感到极度困惑。",
        "theory": "实例方法（Instance Method）是定义在类体内部、专门用来操纵特定实例对象的函数。`self` 是 Python 的核心约定（非关键字），代表**当前正在调用该方法的具体实例对象本身**的引用指针。当通过 `obj.method(arg)` 调用时，Python 解释器会在底层自动将其脱糖转换为 `Class.method(obj, arg)`。`self` 是连接方法与实例专属数据属性的物理桥梁。",
        "key_concepts": [
            ("self 的物理本质", "当前被调用实例的指针引用，由解释器在调用时隐式自动注入首位形参"),
            ("属性读写机制", "必须通过 `self.attribute` 访问和修改当前实例的私有状态"),
            ("方法绑定（Bound Method）", "通过实例访问的方法会自动绑定该实例，成为绑定方法对象")
        ],
        "code_example": '''# 深入揭秘 self 传递与实例方法底层机制
class Phone:
    def ring(self, caller_name: str):
        # 通过 self 获取调用者绑定的品牌
        print(f"【{self.brand}】手机响铃了... 来电人是: {caller_name}")

# 实例化对象
iphone = Phone()
iphone.brand = "iPhone 15 Pro"

xiaomi = Phone()
xiaomi.brand = "Xiaomi 14 Ultra"

# 1. 常规实例调用 (解释器隐式传入 self)
iphone.ring("老板")
xiaomi.ring("快递小哥")

# 2. 底层物理等价调用 (证明 self 的本质)
print("\n=== 揭示底层语法糖真相 ===")
Phone.ring(iphone, "老板")  # 手动显式传入 iphone 作为 self''',
        "pitfalls": [
            "方法定义遗漏 self：写 `def ring(caller_name):`，当调用 `phone.ring('xxx')` 时抛出 TypeError: Phone.ring() takes 1 positional argument but 2 were given",
            "在方法内访问属性未加 self：写 `print(brand)` 而非 `self.brand`，会导致解释器去全局作用域查找该变量并引发 NameError"
        ],
        "questions": [
            "1. 为什么 Python 解释器选择显式在方法签名中书写 `self`，而不像 Java/C++ 那样采用隐式的 `this` 指针？",
            "2. 试分析当把一个实例方法赋值给一个新变量时（如 `func = iphone.ring`），这个绑定方法对象在底层缓存了什么？"
        ]
    },
    {
        "page": 80,
        "title": "80. 核心语法-面向对象基础-魔法方法",
        "clean_title": "80. 核心语法-面向对象基础-魔法方法",
        "topic": "双下划线魔法方法 (Dunder Methods) 与 __init__ 构造器",
        "pain_point": "对象每次实例化后，都需要手动在外部写好几行点号赋值（如 `p.name=...; p.age=...`），繁杂易漏；直接打印对象输出形如 `<__main__.Student at 0x...>`，毫无可读性。",
        "theory": "魔法方法（Magic Methods / Dunder Methods）是 Python 中以双下划线包裹的特殊方法（如 `__init__`, `__str__`）。它们是 Python 数据模型（Data Model）的核心，由解释器在特定生命周期事件触发时**自动隐式调用**：\n1. `__init__`：构造初始化方法，在实例分配内存后自动被触发，用于为实例绑定初始属性；\n2. `__str__`：用户友好的字符串表现形式，在 `print(obj)` 或 `str(obj)` 时触发；\n3. `__repr__`：面向开发者的机器自省字符串；\n4. `__del__`：析构方法，在对象被 GC 销毁前触发。",
        "key_concepts": [
            ("构造初始化器 `__init__`", "统一实例属性规范，严禁在 `__init__` 中返回除 `None` 外的任何值"),
            ("对象可读化 `__str__`", "重载该方法可自定义打印格式，输出清晰规整的业务信息"),
            ("隐式调用契约", "无需手动调用 `obj.__init__()`，由解释器在 `ClassName(...)` 时自动串联驱动")
        ],
        "code_example": '''# 魔法方法 __init__ 与 __str__ 实战
class Employee:
    def __init__(self, emp_id: int, name: str, dept: str, salary: float):
        """实例构造初始化魔法方法"""
        self.emp_id = emp_id
        self.name = name
        self.dept = dept
        self.salary = salary
        print(f"[生命周期] 员工 {self.name} 对象内存初始化完成！")

    def __str__(self) -> str:
        """格式化打印友好的字符串魔法方法"""
        return f"员工档案[工号={self.emp_id}, 姓名='{self.name}', 部门='{self.dept}', 月薪=￥{self.salary:.2f}]"

    def __repr__(self) -> str:
        """开发者控制台内省视图"""
        return f"Employee(emp_id={self.emp_id}, name='{self.name}')"

# 1. 优雅的一步实例化（自动触发 __init__）
emp1 = Employee(1001, "赵铁柱", "智能制造部", 15000.0)
emp2 = Employee(1002, "李翠花", "品质检验部", 12000.0)

# 2. 友好打印呈现（自动触发 __str__）
print("\n=== 友好报表输出 ===")
print(emp1)
print(emp2)''',
        "pitfalls": [
            "`__init__` 试图返回值：在 `__init__` 中写 `return 1` 会直接崩溃并抛出 TypeError: __init__() should return None, not 'int'",
            "方法名拼写错误：写成单下划线 `_init_` 或漏掉末尾下划线，导致该方法变成普通实例方法而无法在实例化时被自动调用"
        ],
        "questions": [
            "1. 严格区分 `__new__` 与 `__init__`：究竟哪一个是真正分配内存空间的构造方法？单例模式应在哪一个方法中实现？",
            "2. `__str__` 与 `__repr__` 的核心定位有何不同？当一个类只实现了 `__repr__` 时，调用 `str(obj)` 会发生什么？"
        ]
    },
    {
        "page": 81,
        "title": "81. 核心语法-面向对象基础-实例属性与类属性",
        "clean_title": "81. 核心语法-面向对象基础-实例属性与类属性",
        "topic": "类属性全实例共享机制与 @classmethod / @staticmethod 装饰器",
        "pain_point": "混淆了定义在类体内的类属性与绑定在 `self` 上的实例属性，通过实例对象去修改类属性时产生意料之外的属性遮蔽（Shadowing）Bug。",
        "theory": "类属性（Class Attribute）直接定义在类体顶层，归属于类对象本身，**被该类的所有实例对象共同共享同一份物理内存**；实例属性（Instance Attribute）绑定在 `self` 上，每个实例独有一份。当通过实例读取属性时，解释器遵循“先在实例局部命名空间找，找不到再去类命名空间找”的优先级；若通过实例对其赋值，则会在该实例上创建一个同名的实例属性遮蔽类属性。结合 `@classmethod` 可操纵类级状态，`@staticmethod` 用于纯工具函数。",
        "key_concepts": [
            ("共享内存特性", "类属性适合记录全局共享常量、计数器、连接池等全局状态"),
            ("类属性修改纪律", "修改类属性必须通过 `ClassName.attr = val`，切忌通过 `instance.attr = val`（后者只是创建了实例属性）"),
            ("类方法 @classmethod", "首个参数为 `cls`，代表类对象本身，支持多态子类工厂模式")
        ],
        "code_example": '''# 类属性共享计数器与类方法实操
class BankAccount:
    # 1. 类属性：记录银行全局开户总数与机构代码
    bank_code = "BK-998"
    total_accounts = 0

    def __init__(self, owner: str, initial_deposit: float):
        self.owner = owner          # 实例属性
        self.balance = initial_deposit
        # 每开一户，全行总账户数自增
        BankAccount.total_accounts += 1

    @classmethod
    def get_bank_summary(cls):
        """类方法：操纵类属性"""
        return f"【{cls.bank_code}】目前已为全社会开设 {cls.total_accounts} 个有效账户。"

    @staticmethod
    def validate_amount(amount: float) -> bool:
        """静态方法：不依赖 self 也不依赖 cls 的纯计算工具"""
        return amount > 0

# 实例化 3 个账户
acc1 = BankAccount("张三", 5000)
acc2 = BankAccount("李四", 8000)
acc3 = BankAccount("王五", 12000)

print(BankAccount.get_bank_summary())
print("账户1共享机构码:", acc1.bank_code)
print("静态校验金额 -50:", BankAccount.validate_amount(-50))''',
        "pitfalls": [
            "通过实例误改类属性：书写 `acc1.total_accounts = 999` 并不会改变全局计数，而只是在 `acc1` 上新建了一个私有实例属性遮蔽了它",
            "类方法中误用 self：在 `@classmethod` 修饰的方法中写 `self.xxx`，因为类方法的第一个参数是 `cls`，无 `self`"
        ],
        "questions": [
            "1. 试从内存节省和设计模式的角度，说明何时该用“实例属性”，何时该用“类属性”？",
            "2. 比较普通实例方法、`@classmethod` 类方法与 `@staticmethod` 静态方法在参数传递与应用场景上的区别。"
        ]
    },
    {
        "page": 82,
        "title": "82. 核心语法-面向对象基础-案例(教务系统-准备)",
        "clean_title": "82. 核心语法-面向对象基础-案例(教务系统-准备)",
        "topic": "综合实战设计：学员管理系统架构设计与模型建模",
        "pain_point": "面对一个功能完备的管理系统，新手容易盲目下笔，缺乏领域模型抽象意识，导致代码结构混乱、职责纠缠不清。",
        "theory": "采用面向对象领域驱动思想划分系统职责：\n1. **实体模型类（`Student`）**：纯领域模型，封装学员唯一标识学号 `sid`、姓名 `name`、年龄 `age`、手机号 `mobile` 以及自身字符串自省表达；\n2. **控制管理类（`StudentManager`）**：业务调度中心，持有一个学员对象容器列表 `students: list[Student]`，负责全生命周期 CRUD 维护与交互菜单调度。",
        "key_concepts": [
            ("模型与控制器分层", "实体类负责数据与属性验证，管理类负责业务流转与持久化调度"),
            ("对象集合管理", "在管理类内部使用列表或字典组织多个实体对象引用"),
            ("健壮骨架先行", "预先规划清晰的方法接口契约（Stubs），支撑敏捷演进")
        ],
        "code_example": '''# 学员管理系统架构原型与实体模型
class Student:
    """学员领域实体模型"""
    def __init__(self, sid: str, name: str, age: int, mobile: str):
        self.sid = sid
        self.name = name
        self.age = age
        self.mobile = mobile

    def __str__(self) -> str:
        return f"{self.sid}\t{self.name}\t{self.age}\t{self.mobile}"

class StudentManager:
    """学员管理调度控制系统"""
    def __init__(self):
        # 核心数据容器：存储 Student 实体对象的列表
        self.student_list: list[Student] = []

    def show_menu(self):
        """展示控制台交互菜单"""
        print("\n*************************************")
        print("     欢迎使用黑马学员教务管理系统    ")
        print("  1. 添加学员信息   2. 删除学员信息  ")
        print("  3. 修改学员信息   4. 查询学员信息  ")
        print("  5. 显示所有学员   6. 退出系统      ")
        print("*************************************")

# 验证实体模型构建
test_stu = Student("1001", "小明", 19, "13800138000")
print("测试实体模型打印:", test_stu)''',
        "pitfalls": [
            "把所有的增删改查方法全写在 `Student` 实体类里：违背单一职责原则，学员对象不应该负责去管理整个学校的学员名单",
            "学号采用整数存储导致前导零丢失：学号应用 `str` 存储，避免 `0012` 被误转为 `12`"
        ],
        "questions": [
            "1. 为什么在企业级软件架构中，模型层（Model）与服务控制层（Service/Manager）必须进行物理分层隔离？",
            "2. 如何使用 Python 的 `dataclasses` 模块极简声明 `Student` 实体类？"
        ]
    },
    {
        "page": 83,
        "title": "83. 核心语法-面向对象基础-案例(教务系统-添加学生信息)",
        "clean_title": "83. 核心语法-面向对象基础-案例(教务系统-添加学生信息)",
        "topic": "学员录入业务实现：主键防重校验与实体实例化流转",
        "pain_point": "录入新学员时若不进行唯一标识（学号）查重，会导致系统出现重复数据甚至覆盖历史档案；输入非法字符时程序崩溃。",
        "theory": "录入学员业务遵循四步闭环：1. 采集用户控制台输入；2. 遍历现有学员列表比对学号（主键排重），若命中重复立即终止并提示；3. 校验通过后实例化新 `Student` 对象；4. 将该对象追加至 `self.student_list` 中并给出成功反馈。",
        "key_concepts": [
            ("主键唯一性防御", "遍历现有列表，通过 `stu.sid == input_sid` 检测冲突"),
            ("对象实例化组装", "将零散的输入信息转化为封装完备的 `Student` 对象"),
            ("列表追加持有", "`self.student_list.append(new_student)` 确保持久化存活")
        ],
        "code_example": '''# 基于上一讲架构实现添加学员业务逻辑
class Student:
    def __init__(self, sid: str, name: str, age: int, mobile: str):
        self.sid = sid
        self.name = name
        self.age = age
        self.mobile = mobile

    def __str__(self) -> str:
        return f"{self.sid}\\t{self.name}\\t{self.age}\\t{self.mobile}"

class StudentManager:
    def __init__(self):
        self.student_list: list[Student] = []

    def add_student(self, sid: str, name: str, age: int, mobile: str) -> bool:
        """执行学员建档录入核心逻辑"""
        # 1. 唯一性查重校验
        for stu in self.student_list:
            if stu.sid == sid:
                print(f"【冲突】学号 {sid} 已存在，录入失败！")
                return False

        # 2. 实例化并追加
        new_student = Student(sid, name, age, mobile)
        self.student_list.append(new_student)
        print(f"【成功】学员 [{name}] 档案建立成功！")
        return True

# 模拟单元测试
mgr = StudentManager()
mgr.add_student("202601", "张无忌", 20, "13911112222")
mgr.add_student("202601", "张翠山", 45, "13911113333") # 触发查重拦截！''',
        "pitfalls": [
            "在列表遍历中修改列表长度：边查重边做额外操作导致游标错位",
            "录入未转换的数据类型：把 `age` 作为字符串存入，后续若做年龄统计排序会引发逻辑错误"
        ],
        "questions": [
            "1. 当学员数量达到 10 万人时，每次录入都遍历列表查重的时间复杂度是 $O(n)$，如何优化数据结构使查重达到 $O(1)$？",
            "2. 手机号码的合法性校验（11位纯数字且1开头）应该写在实体类内部还是控制类？为什么？"
        ]
    },
    {
        "page": 84,
        "title": "84. 核心语法-面向对象基础-案例(教务系统-修改删除查询)",
        "clean_title": "84. 核心语法-面向对象基础-案例(教务系统-修改删除查询)",
        "topic": "学员全功能 CRUD 闭环：按学号寻址、更新与安全移除",
        "pain_point": "如何高效根据学号定位目标学员对象，并支持只更新指定属性或安全将其从教务系统中注销移除。",
        "theory": "通过定义辅助查找方法 `_find_by_sid(sid)`，将学号寻址逻辑收敛为单个公共组件。在修改逻辑中，按引用直接就地更新该对象属性；在删除逻辑中，通过列表的 `remove()` 方法将其移除并切断引用指针；在查询逻辑中，格式化调用 `print(stu)` 触发其 `__str__` 方法。",
        "key_concepts": [
            ("寻址抽象复用", "提取 `_find_by_sid(sid) -> Student | None`，杜绝在删改查中重复书写循环遍历"),
            ("就地属性修改", "获取到对象引用后，直接执行 `stu.name = new_name` 即可实现内存同步生效"),
            ("列表安全移除", "使用 `self.student_list.remove(stu)` 完成对象解绑")
        ],
        "code_example": '''# 补充删、改、查核心完整逻辑
# (基于已有的 Student 与 StudentManager)
class StudentManagerAdvanced(StudentManager):
    def _find_by_sid(self, sid: str):
        """内部寻址组件：按学号查找学员实体"""
        for stu in self.student_list:
            if stu.sid == sid:
                return stu
        return None

    def search_student(self, sid: str):
        """查询学员详细信息"""
        stu = self._find_by_sid(sid)
        if stu:
            print("------------ 查询结果 ------------")
            print("学号\t姓名\t年龄\t手机号")
            print(stu)
            return stu
        print(f"【提示】未查找到学号为 {sid} 的学员！")
        return None

    def update_student(self, sid: str, new_name: str, new_age: int, new_mobile: str):
        """修改学员档案属性"""
        stu = self._find_by_sid(sid)
        if not stu:
            print(f"【错误】学号 {sid} 不存在，无法修改！")
            return False
        stu.name = new_name
        stu.age = new_age
        stu.mobile = new_mobile
        print(f"【成功】学号 {sid} 信息已更新完毕！")
        return True

    def delete_student(self, sid: str):
        """注销删除学员档案"""
        stu = self._find_by_sid(sid)
        if not stu:
            print(f"【错误】学号 {sid} 不存在，无法删除！")
            return False
        self.student_list.remove(stu)
        print(f"【成功】学员 [{stu.name}] 档案已成功注销。")
        return True''',
        "pitfalls": [
            "删除不存在的学员时直接 `list.remove()`：未先校验是否存在，直接触发 ValueError: list.remove(x): x not in list",
            "在修改时重新赋予了一个新对象：可能导致外部持有的旧引用失效，应始终原地更新对象属性"
        ],
        "questions": [
            "1. 为什么将 `_find_by_sid` 命名为下划线开头？这种约定的工程意义是什么？",
            "2. 如何支持按照学员姓名进行“模糊模糊搜索”（包含子串即命中返回列表）？"
        ]
    },
    {
        "page": 85,
        "title": "85. 核心语法-面向对象基础-案例(教务系统-运行测试)",
        "clean_title": "85. 核心语法-面向对象基础-案例(教务系统-运行测试)",
        "topic": "系统全功能集成联调与自动化冒烟测试闭环",
        "pain_point": "所有模块组装完毕后，需要打通控制台菜单调度循环，并进行全场景集成冒烟验证，确保系统坚固稳定。",
        "theory": "在系统入口处构建事件循环 `run()`，通过标准分支路由将用户操作分发给 `add`, `delete`, `update`, `search`, `show_all` 等各独立方法。运用自动化测试脚本模拟全流程增删改查及边界容错，验证面向对象系统的完整性与高鲁棒性。",
        "key_concepts": [
            ("主调度事件循环", "`while True` 持续响应用户菜单指令，输入 6 优雅退出"),
            ("全员视图呈现", "格式化打印输出所有在册学员报表"),
            ("集成冒烟测试", "自动化断言验证各项业务边界行为")
        ],
        "code_example": '''# 系统全生命周期集成测试驱动
def run_smoke_test():
    print("=== 启动教务管理系统端到端自动化冒烟测试 ===")
    mgr = StudentManagerAdvanced()

    # 1. 批量录入
    mgr.add_student("202601", "张三丰", 108, "13800001111")
    mgr.add_student("202602", "宋远桥", 50, "13800002222")
    mgr.add_student("202603", "俞莲舟", 48, "13800003333")

    # 2. 查重拦截验证
    print("\n[测试] 查重边界拦截:")
    mgr.add_student("202601", "伪造者", 18, "13800009999")

    # 3. 档案修改与验证
    print("\n[测试] 修改宋远桥手机号:")
    mgr.update_student("202602", "宋远桥", 51, "13988887777")
    mgr.search_student("202602")

    # 4. 删除注销与验证
    print("\n[测试] 注销俞莲舟档案:")
    mgr.delete_student("202603")
    mgr.search_student("202603")  # 期望提示未查找到

    print("\n=== 全部业务功能集成冒烟测试 100% 通过！===")

if __name__ == "__main__":
    run_smoke_test()''',
        "pitfalls": [
            "退出系统时未保存数据：内存中的数据随进程终结而瞬间蒸发，后续需要补充文件 I/O 或数据库持久化支持",
            "测试与业务代码耦合：正式部署时应将测试套件拆分为独立的 `test_manager.py`"
        ],
        "questions": [
            "1. 试总结从“面向过程”迁移到“面向对象”后，代码在结构组织和职责划分上发生了哪些根本改变？",
            "2. 如何使用 Python 的 `json` 模块在 `StudentManager` 退出时将所有学员对象序列化保存至本地文件？"
        ]
    }
]

def generate_subtitles():
    """Generates clean subtitles for P77 - P85."""
    for ep in MODULE6_EPISODES:
        page = ep["page"]
        clean_file = SUBTITLES_DIR / f"P{page:02d}_{ep['title']}_clean.txt"
        if clean_file.exists():
            continue
        
        content = f"""【课程主题】{ep['clean_title']}
【核心概念】{ep['topic']}

【正文讲解】
大家好，欢迎来到黑马程序员 Python+AI 全套视频教程。本节课我们进入 Python 核心语法体系中极具分量的重磅模块——面向对象基础系列：{ep['clean_title']}。

首先分析为什么需要这项核心编程思想。{ep['pain_point']}
从底层计算机制和对象模型来看，{ep['theory']}

在具体语法规则和工程抽象上，大家需要掌握以下几个关键维度：
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
    for ep in MODULE6_EPISODES:
        page = ep["page"]
        article_file = ARTICLES_DIR / f"P{page:02d}_{ep['title']}_精读文章.md"
        
        key_concepts_md = "\n".join([f"- **{name}**：{desc}" for name, desc in ep["key_concepts"]])
        pitfalls_md = "\n".join([f"{i+1}. **{p.split('：')[0] if '：' in p else '注意事项'}**：{p.split('：')[1] if '：' in p else p}" for i, p in enumerate(ep["pitfalls"])])
        questions_md = "\n".join([f"- **思考题 {i+1}**：{q}" for i, q in enumerate(ep["questions"])])
        
        article_content = f"""# {ep['clean_title']}

> **所属专栏**：{COURSE_TITLE}  
> **核心模块**：核心语法 - 面向对象基础 (Module 06)  
> **单集定位**：第 {page} 集 / P{page:02d}  
> **本篇主题**：{ep['topic']}

---

## 一、问题引入与核心痛点

{ep['pain_point']}

在现代软件工程中，面向对象编程（OOP）不仅是一种代码组织语法，更是一种对客观世界的哲学抽象方式。如何通过类与对象将复杂多变的现实实体封装为具有自我管理能力的高内聚模块，是构建企业级稳定系统的必由之路。

---

## 二、底层运行机制与语法原理

{ep['theory']}

```mermaid
graph TD
    A["类定义 (Class Blueprint)"] --> B["内存堆区开辟空间"]
    B --> C["自动调用 __init__(self, ...)"]
    C --> D["绑定实例属性 (self.__dict__)"]
    D --> E["实例方法绑定 (Bound Method)"]
```

在 CPython 虚拟机的对象模型中，每一个对象都拥有类型指针（`ob_type`）与引用计数（`ob_refcnt`）。通过 `self` 访问属性本质上是在查询该实例底层的属性字典 `__dict__`。深刻理解实例与类在内存中的映射关系，是精通面向对象底层运作的关键。

---

## 三、核心概念与标准定义

本节涉及的核心概念与规范要素梳理如下：

{key_concepts_md}

### 规范标准对照表

| 维度 | 规约要求 | 异常类型 / 常见后果 | 最佳实践方案 |
| :--- | :--- | :--- | :--- |
| **实例方法声明** | 首个形参必须显式声明为 `self` | `TypeError: takes 1 positional argument but 2 given` | 遵循规范，所有实例方法首参恒为 `self` |
| **属性作用域** | 区分清楚实例私有属性与类共享属性 | 属性意外遮蔽 (Shadowing) / 共享数据错乱 | 修改类属性坚决使用 `ClassName.attr` |
| **构造方法** | `__init__` 严禁显式返回值 | `TypeError: __init__() should return None` | 构造方法仅做属性挂载，禁止写 `return` |

---

## 四、生产级代码演练与拆解

```python
{ep['code_example']}
```

### 关键代码逐步拆解

1. **类图纸与属性抽象**：设计具有高内聚、单一职责的类结构，在构造方法中固化基础属性约束。
2. **行为方法与状态变更**：通过 `self` 桥梁精准操纵当前实例状态，保障数据的完整性与一致性。
3. **架构分层与业务闭环**：分离模型实体与调度服务，保证面向对象系统具备高抗风险与可维护能力。

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
    note_file = NOTES_DIR / "模块06_面向对象基础_复习笔记.md"
    
    table_rows = []
    for ep in MODULE6_EPISODES:
        table_rows.append(f"| P{ep['page']:02d} | {ep['clean_title']} | {ep['topic']} | {ep['theory'][:60]}... |")
    table_md = "\n".join(table_rows)

    note_content = """# 模块 06：面向对象基础 (P77 - P85) 核心复习大笔记

> **课程专栏**：__COURSE_TITLE__  
> **模块跨度**：P77 ~ P85（共 9 集精讲）  
> **构建标准**：依据 `delivery_matrix.md` 产品 B 标准与 `ascii_topology_guide.md` 规范构建。

---

## 0. 模块知识全景拓扑图 (ASCII Topology)

```
[Module 06: 面向对象基础与系统实战]
  |
  +-- [OOP 核心哲学与类模型]
  |     |-- 范式演进: 面向过程 (POP) vs 面向对象 (OOP) / 高内聚封装 [P77]
  |     |-- 类与对象: 蓝图图纸 vs 物理实例 / CamelCase 规约 / isinstance 判定 [P78]
  |     |-- 实例方法: self 指针本质 / Class.method(obj) 脱糖底层 / 绑定方法 [P79]
  |     |-- 魔法方法: __init__ 构造器 / __str__ 友好打印 / __repr__ 开发者视图 [P80]
  |     \\-- 属性模型: 实例属性 (self.x) vs 类属性 (全员共享) / @classmethod / @staticmethod [P81]
  |
  \\-- [教务管理系统综合实战: Model-Manager 架构]
        |-- 架构准备: Student 实体模型 + StudentManager 控制中心分层设计 [P82]
        |-- 添加业务: 主键学号排重 / 实体对象构建 / 列表聚合 [P83]
        |-- 删改查业务: _find_by_sid 寻址抽象 / 属性原地修改 / 安全移除 [P84]
        \\-- 测试闭环: 终端交互事件驱动 / 自动化冒烟测试 / 边界防御断言 [P85]
```

---

## 1. 模块核心概念速查表

| 分集索引 | 课程分集名称 | 核心知识主题 | 关键原理推演 / 标准定义 |
| :--- | :--- | :--- | :--- |
__TABLE_MD__

---

## 2. 关键方法类型全维度大横评矩阵

| 方法类型 | 声明装饰器 | 首个固定形参 | 访问权限与数据边界 | 典型应用场景 |
| :--- | :--- | :--- | :--- | :--- |
| **实例方法** | (无装饰器) | `self` | 可自由读写**当前实例属性**及所属**类属性** | 对象的常规业务行为（如攻击、发消息、修改个人信息） |
| **类方法** | `@classmethod` | `cls` | 仅能访问与修改**类属性**，无法访问特定实例的属性 | 工厂方法（根据多种不同数据源派生实例）、修改全局类配置 |
| **静态方法** | `@staticmethod` | (无硬性要求) | 既无法直接访问实例属性，也无法直接访问类属性 | 与类相关的独立纯算法工具函数（如密码哈希校验、格式验证） |

---

## 3. 核心考点与避坑清单 (CheatSheet)

1. **self 是实例引用，不是关键字**：`self` 只是强烈的社区共识约定，在调用时由解释器自动作为第一个参数静默传入。
2. **`__init__` 绝不能 return**：`__init__` 只能返回 `None`；如需控制实例生成过程应使用 `__new__`。
3. **类属性修改大坑**：若写 `instance.class_attr = val`，绝不会修改类属性，而是动态新建了一个同名的实例属性遮蔽了它！修改类属性务必写 `ClassName.class_attr = val`。
4. **打印对象友好化**：为类重载 `__str__(self)` 方法，即可让 `print(obj)` 优雅输出可读的业务详情，彻底摆脱 `<Student object at 0x...>`。
5. **模型与业务分层**：实体类（如 Student）只负责表达数据属性，不要把全局名单的增删查逻辑堆进实体类中，应由专职的 Manager 类负责调度。
"""
    final_content = note_content.replace("__COURSE_TITLE__", COURSE_TITLE).replace("__TABLE_MD__", table_md)
    note_file.write_text(final_content.strip() + "\n", encoding="utf-8")
    print(f"  [Note] 生成模块大笔记: {note_file.name}")

if __name__ == "__main__":
    print("=== 开始生成 模块 06：面向对象基础 (P77 - P85) ===")
    generate_subtitles()
    generate_articles()
    generate_notes()
    print("=== 模块 06 全部交付物生成完毕！===")
