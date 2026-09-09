#!/usr/bin/env python3
"""校验与同步 SKILL.md，确保符合 Antigravity / Codex / Open Agent Skills 标准规范。

支持：
1. 校验 Frontmatter（name、description 等）；
2. 校验有无硬编码本地绝对物理路径；
3. 校验 references 引用完整性；
4. 校验与自动同步 .agents/skills/bili-video2book/ 目录。
"""

import argparse
import filecmp
import re
import shutil
import sys
from pathlib import Path


def sync_to_antigravity(project_root: Path) -> bool:
    """以根目录为权威源，同步至 .agents/skills/bili-video2book/。"""
    target_dir = project_root / ".agents" / "skills" / "bili-video2book"
    target_dir.mkdir(parents=True, exist_ok=True)

    # 1. 同步 SKILL.md
    src_skill = project_root / "SKILL.md"
    dst_skill = target_dir / "SKILL.md"
    if src_skill.exists():
        shutil.copy2(src_skill, dst_skill)
        print(f"[SYNC] 已同步 SKILL.md -> {dst_skill.relative_to(project_root)}")

    # 2. 同步 references/
    src_refs = project_root / "references"
    dst_refs = target_dir / "references"
    if src_refs.exists():
        if dst_refs.exists():
            shutil.rmtree(dst_refs)
        shutil.copytree(src_refs, dst_refs)
        print(f"[SYNC] 已同步 references/ -> {dst_refs.relative_to(project_root)}")

    # 3. 同步 agents/
    src_agents = project_root / "agents"
    dst_agents = target_dir / "agents"
    if src_agents.exists():
        if dst_agents.exists():
            shutil.rmtree(dst_agents)
        shutil.copytree(src_agents, dst_agents)
        print(f"[SYNC] 已同步 agents/ -> {dst_agents.relative_to(project_root)}")

    print("[SYNC] Antigravity 目录同步完毕！")
    return True


def validate_skill(skill_path: Path, project_root: Path) -> bool:
    if not skill_path.exists():
        print(f"[FAIL] {skill_path} 不存在")
        return False

    content = skill_path.read_text(encoding="utf-8")

    # 1. 检查 YAML Frontmatter 边界
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", content, re.DOTALL)
    if not match:
        print("[FAIL] 缺失合规的 YAML Frontmatter (以 --- 包裹)")
        return False

    frontmatter = match.group(1)

    # 2. 检查 name 字段
    name_match = re.search(r"^name:\s*([a-zA-Z0-9_-]+)", frontmatter, re.MULTILINE)
    if not name_match:
        print("[FAIL] Frontmatter 缺少 'name' 字段")
        return False
    name = name_match.group(1).strip()
    if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", name):
        print(f"[FAIL] 'name' 字段格式不符合规范（仅允许全小写字母、数字和中划线）: {name}")
        return False
    if len(name) > 64:
        print(f"[FAIL] 'name' 长度超过 64 字符: {len(name)}")
        return False
    print(f"[PASS] name 字段校验通过: {name}")

    # 3. 检查 description 字段
    desc_match = re.search(r"^description:\s*(.+)$", frontmatter, re.MULTILINE)
    if not desc_match:
        print("[FAIL] Frontmatter 缺少 'description' 字段")
        return False
    desc = desc_match.group(1).strip()
    if len(desc) < 10 or len(desc) > 1024:
        print(f"[FAIL] 'description' 长度异常（必须在 10~1024 字符之间）: {len(desc)}")
        return False
    print(f"[PASS] description 字段校验通过 (长度: {len(desc)})")

    # 4. 检查是否残留本地硬编码物理路径 (如 D:\, C:\Users, /Users/, /home/)
    hardcoded_match = re.search(r"(?<![a-zA-Z0-9])([A-Za-z]:[\\/]|/(Users|home)/)[^\s`)\"]+", content)
    if hardcoded_match:
        print(f"[FAIL] 文档中检测到硬编码本地绝对物理路径: {hardcoded_match.group(0)}")
        return False
    print("[PASS] 无本地硬编码物理绝对路径")

    # 5. 检查引用文档 references 的有效性
    ref_links = re.findall(r"\[.*?\]\((references/[^\)]+)\)", content)
    for link in ref_links:
        ref_file = project_root / link
        if not ref_file.exists():
            print(f"[FAIL] 引用的文档不存在: {link} (物理路径: {ref_file})")
            return False
    print(f"[PASS] 引用的 {len(ref_links)} 处 references 文档均存在有效")

    # 6. 检查正文长度与渐进披露
    lines = content.splitlines()
    print(f"[INFO] 文档总行数: {len(lines)} 行 (推荐 < 500 行)")
    if len(lines) > 500:
        print("[WARN] 行数超过 500 行，建议拆分至 references/")
    else:
        print("[PASS] 行数在精简建议阈值内")

    return True


def check_sync_status(project_root: Path) -> bool:
    """检查根目录与 .agents 副本是否一致。"""
    root_skill = project_root / "SKILL.md"
    agent_skill = project_root / ".agents" / "skills" / "bili-video2book" / "SKILL.md"
    if not agent_skill.exists():
        print("[WARN] .agents 副本不存在")
        return False

    if root_skill.read_text(encoding="utf-8") != agent_skill.read_text(encoding="utf-8"):
        print("[FAIL] 根目录 SKILL.md 与 .agents 目录中的 SKILL.md 内容不一致！")
        return False

    print("[PASS] 根目录与 Antigravity (.agents/) 副本保持 100% 同步")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Skill 规范校验与 Antigravity 自动同步工具")
    parser.add_argument("--sync", action="store_true", help="以根目录为权威源自动同步至 .agents/ 目录")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    target = project_root / "SKILL.md"

    if args.sync:
        sync_to_antigravity(project_root)

    valid = validate_skill(target, project_root)
    if not valid:
        sys.exit(1)

    # 默认自动检查或提示同步状态
    synced = check_sync_status(project_root)
    if not synced and not args.sync:
        print("[INFO] 检测到未同步，正在自动执行同步...")
        sync_to_antigravity(project_root)
        synced = check_sync_status(project_root)

    sys.exit(0 if (valid and synced) else 1)

