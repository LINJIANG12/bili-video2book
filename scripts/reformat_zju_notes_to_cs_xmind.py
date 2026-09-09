#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reformat ZJU Software Engineering course notes to SSHeRun/CS-Xmind-Note minimal mindmap style.

Converts the 14 module notes in `output/【公开课】浙江大学：软件工程 陈越（全33讲）_BV16g411M7r2/notes`
into the strict 408 CS examination / XMind / Markmap tree format:
- Metadata header: minimal (精简) - CS-Xmind-Note
- Section 1: 核心知识思维导图与考纲笔记 (Pure multi-level list trees `*`, `    * > 核心定义与本质: ...`)
- Section 2: 关键方法与要素对比矩阵 (表格速查) (Markdown comparison tables)
- Section 3: 典型工程案例与实践思维导图 (`* 案例: ...`, `    * > 背景: ...`, `    * 故障根因: ...`)
- Section 4: 常见反模式与避坑要点思维导图 (`* 反模式: ...`, `    * > 表现: ...`, `    * 规避策略: ...`)
- Section 5: 408考纲强化自测与深度解析 (Exam-style deep-dive self assessment)
"""

import re
import sys
from pathlib import Path
from typing import List


def convert_module_note(content: str) -> str:
    # 1. Update header
    content = re.sub(
        r'>\s*(软件工程体系化知识模块|.*?)\s*\|\s*涵盖分集：(.*?)(\n|$)',
        r'> 计算机核心体系考纲笔记 | 风格：精简 (minimal) - CS-Xmind-Note 思维导图树 | 涵盖分集：\2\3',
        content
    )
    content = content.replace('核心议题：', '核心考点：')

    # Ensure header tag is present
    lines = content.splitlines()
    if len(lines) > 2 and 'CS-Xmind-Note' not in lines[2]:
        for idx in range(1, min(5, len(lines))):
            if lines[idx].startswith('>'):
                m_eps = re.search(r'P\d+.*', lines[idx])
                if m_eps:
                    lines[idx] = f'> 计算机核心体系考纲笔记 | 风格：精简 (minimal) - CS-Xmind-Note 思维导图树 | 涵盖分集：{m_eps.group(0)}'
                break
        content = '\n'.join(lines)

    sections = re.split(r'\n(?=## )', content)
    
    header_sec = ''
    topo_sec = ''
    core_sec = ''
    cases_sec = ''
    tables_sec = ''
    anti_sec = ''
    quiz_sec = ''
    
    for sec in sections:
        h = sec.strip().splitlines()[0] if sec.strip() else ''
        if h.startswith('# 模块'):
            header_sec = sec.strip()
        elif '## 知识拓扑框架导图' in h:
            topo_sec = sec.strip()
        elif '## 核心概念与理论模型' in h or '## 1. 核心知识思维导图' in h:
            core_sec = sec.strip()
        elif '## 跨集工程案例与演进复盘' in h or '## 3. 典型工程案例' in h:
            cases_sec = sec.strip()
        elif '## 关键概念对比与辨析' in h or '## 2. 关键方法与要素对比矩阵' in h:
            tables_sec = sec.strip()
        elif '## 常见反模式与避坑要点' in h or '## 4. 常见反模式' in h:
            anti_sec = sec.strip()
        elif '## 随堂强化自测与深度解析' in h or '## 5. 408考纲强化自测' in h:
            quiz_sec = sec.strip()

    # --- 1. Core Section ---
    core_res = ['## 1. 核心知识思维导图与考纲笔记\n']
    subsecs = re.split(r'\n(?=### )', '\n'.join(core_sec.splitlines()[1:]))
    sub_idx = 1
    for sub in subsecs:
        if not sub.strip():
            continue
        sub_lines = sub.strip().splitlines()
        sub_h = sub_lines[0].replace('### ', '').strip()
        sub_h_clean = re.sub(r'^\d+[\.\、\s]*', '', sub_h).strip()
        core_res.append(f'### 1.{sub_idx} {sub_h_clean}\n')
        sub_idx += 1
        
        in_code = False
        for line in sub_lines[1:]:
            if line.strip().startswith('```'):
                in_code = not in_code
                core_res.append(line)
                continue
            if in_code:
                core_res.append(line)
                continue
            sline = line.strip()
            if not sline or sline == '---':
                continue
            if sline.startswith('#### '):
                h4 = sline.replace('#### ', '').strip()
                h4_clean = re.sub(r'^[A-Z0-9]+[\.\、\s]*', '', h4).strip()
                core_res.append(f'* {h4_clean}')
            elif sline.startswith('> '):
                core_res.append(f'    * > 核心定律/本质：{sline[2:].strip()}')
            elif sline.startswith('- **') or sline.startswith('* **'):
                m = re.match(r'^[-*]\s*\*\*(.*?)\*\*[:：]?(.*)', sline)
                if m:
                    term, desc = m.group(1).strip(), m.group(2).strip()
                    core_res.append(f'* {term}')
                    if desc:
                        core_res.append(f'    * > 核心定义与本质：{desc}')
                else:
                    core_res.append(f'    * {sline[2:].strip()}')
            elif re.match(r'^\d+\.\s*\*\*(.*?)\*\*[:：]?(.*)', sline):
                m = re.match(r'^\d+\.\s*\*\*(.*?)\*\*[:：]?(.*)', sline)
                term, desc = m.group(1).strip(), m.group(2).strip()
                core_res.append(f'    * {term}')
                if desc:
                    core_res.append(f'        * > 核心机理：{desc}')
            elif re.match(r'^\d+\.\s+', sline):
                core_res.append(f'        * {sline}')
            elif sline.startswith('- ') or sline.startswith('* '):
                core_res.append(f'    * {sline[2:].strip()}')
            else:
                core_res.append(f'* > 概念机理：{sline}')
        core_res.append('')

    # --- 2. Tables Section ---
    tables_lines = tables_sec.splitlines()
    tables_res = ['## 2. 关键方法与要素对比矩阵 (表格速查)\n']
    if len(tables_lines) > 1:
        tables_res.extend(tables_lines[1:])
    
    # --- 3. Cases Section ---
    cases_res = ['## 3. 典型工程案例与实践思维导图\n']
    case_lines = cases_sec.splitlines()[1:]
    
    intro_code = []
    rest_lines = []
    in_intro = True
    in_code = False
    for l in case_lines:
        if in_intro:
            if l.strip().startswith('```'):
                intro_code.append(l)
                if in_code:
                    in_intro = False
                in_code = not in_code
                continue
            elif in_code:
                intro_code.append(l)
                continue
            elif l.strip().startswith('###') or l.strip().startswith('####'):
                in_intro = False
                rest_lines.append(l)
            elif l.strip():
                intro_code.append(l)
        else:
            rest_lines.append(l)
            
    if intro_code:
        cases_res.append('\n'.join(intro_code).strip() + '\n')
        
    case_subsecs = re.split(r'\n(?=### |#### )', '\n'.join(rest_lines))
    c_idx = 1
    for cs in case_subsecs:
        if not cs.strip():
            continue
        c_lines = cs.strip().splitlines()
        first = c_lines[0].strip()
        if first.startswith('### ') and not any(k in first for k in ['案例', 'Case']):
            grp_name = re.sub(r'^###\s*(\d+[\.\、\s]*)?', '', first).strip()
            cases_res.append(f'### 3.{c_idx} {grp_name}\n')
            c_idx += 1
            continue
        
        c_h = re.sub(r'^[#]+\s*', '', first).strip()
        c_h_clean = re.sub(r'^(案例\s*[A-Za-z0-9一二三四五六七八九十]+[:：]?\s*|\d+[\.\、\s]*)', '', c_h).strip()
        if not c_h_clean:
            c_h_clean = c_h
        cases_res.append(f'* 案例：{c_h_clean}')
        for line in c_lines[1:]:
            sline = line.strip()
            if not sline or sline == '---':
                continue
            if sline.startswith('```'):
                cases_res.append(sline)
                continue
            if sline.startswith('- **') or sline.startswith('* **'):
                m = re.match(r'^[-*]\s*\*\*(.*?)\*\*[:：]?(.*)', sline)
                if m:
                    k, v = m.group(1).strip(), m.group(2).strip()
                    cases_res.append(f'    * > {k}：{v}')
            elif sline.startswith('- ') or sline.startswith('* '):
                cases_res.append(f'    * {sline[2:].strip()}')
            else:
                cases_res.append(f'    * {sline}')
        cases_res.append('')

    # --- 4. Anti-Patterns Section ---
    anti_res = ['## 4. 常见反模式与避坑要点思维导图\n']
    anti_subsecs = re.split(r'\n(?=### |#### )', '\n'.join(anti_sec.splitlines()[1:]))
    a_idx = 1
    for asub in anti_subsecs:
        if not asub.strip():
            continue
        a_lines = asub.strip().splitlines()
        a_h = re.sub(r'^[#]+\s*', '', a_lines[0]).strip()
        a_h_clean = re.sub(r'^\d+[\.\、\s]*', '', a_h).strip()
        anti_res.append(f'* 反模式 {a_idx:02d}：{a_h_clean}')
        a_idx += 1
        for line in a_lines[1:]:
            sline = line.strip()
            if not sline or sline == '---':
                continue
            if sline.startswith('- **') or sline.startswith('* **'):
                m = re.match(r'^[-*]\s*\*\*(.*?)\*\*[:：]?(.*)', sline)
                if m:
                    k, v = m.group(1).strip(), m.group(2).strip()
                    anti_res.append(f'    * > {k}：{v}')
            elif sline.startswith('- ') or sline.startswith('* '):
                anti_res.append(f'    * {sline[2:].strip()}')
            else:
                anti_res.append(f'    * {sline}')
        anti_res.append('')

    # --- 5. Quiz Section ---
    quiz_res = ['## 5. 408考纲强化自测与深度解析\n']
    quiz_lines = quiz_sec.splitlines()
    if len(quiz_lines) > 1:
        quiz_res.extend(quiz_lines[1:])

    final_doc = [
        header_sec,
        '---',
        topo_sec,
        '---',
        '\n'.join(core_res).strip(),
        '---',
        '\n'.join(tables_res).strip(),
        '---',
        '\n'.join(cases_res).strip(),
        '---',
        '\n'.join(anti_res).strip(),
        '---',
        '\n'.join(quiz_res).strip(),
    ]
    res = '\n\n'.join(final_doc).strip() + '\n'
    # Clean duplicate consecutive separators
    res = re.sub(r'(\n\s*---\s*){2,}', '\n\n---\n\n', res)
    return res


def run_reformat(notes_dir: Path):
    print(f"[*] 开始将 {notes_dir} 目录下的模块笔记转换为 CS-Xmind-Note 精简思维导图风格...")
    count = 0
    for mod_num in range(1, 15):
        files = list(notes_dir.glob(f"模块{mod_num:02d}_*_笔记.md"))
        if not files:
            print(f"[-] 警告：未找到模块 {mod_num:02d} 的笔记文件！")
            continue
        target_file = files[0]
        original_text = target_file.read_text(encoding="utf-8")
        new_text = convert_module_note(original_text)
        target_file.write_text(new_text, encoding="utf-8")
        size_kb = round(target_file.stat().st_size / 1024, 1)
        print(f"[✓] 模块 {mod_num:02d} 笔记已转换覆盖: {target_file.name} ({size_kb} KB)")
        count += 1
    print(f"[*] 全部完成！共重构转换 {count} 份 CS-Xmind-Note 模块树状笔记。")


if __name__ == "__main__":
    default_dir = Path("output/【公开课】浙江大学：软件工程 陈越（全33讲）_BV16g411M7r2/notes")
    if len(sys.argv) > 1:
        default_dir = Path(sys.argv[1])
    run_reformat(default_dir)
