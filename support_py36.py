#!/usr/bin/env python3
"""
基于.format()的f-string修复脚本
- 将有问题的f-string转换为.format()调用
- 支持单引号和双引号f-string
- 显示修改前后对比
"""

import re
import os
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class FixInfo:
    line_num: int
    col_start: int
    col_end: int
    original: str
    fixed: str
    description: str

class FormatFixer:
    def __init__(self):
        self.fixes: List[FixInfo] = []
    
    def _get_line_col(self, content: str, pos: int) -> Tuple[int, int]:
        """获取位置对应的行号和列号"""
        lines_before = content[:pos].split('\n')
        line_num = len(lines_before)
        col_num = len(lines_before[-1]) + 1
        return line_num, col_num
    
    def _extract_fstring_parts(self, fstring_content: str, quote_char: str) -> Tuple[List[str], List[str]]:
        """
        从f-string内容中提取文本部分和表达式部分
        返回: (文本部分列表, 表达式列表)
        """
        # 简单的解析逻辑，处理 {expression} 格式
        parts = []
        expressions = []
        current_part = ""
        i = 0
        
        while i < len(fstring_content):
            if fstring_content[i] == '{' and i + 1 < len(fstring_content) and fstring_content[i + 1] != '{':
                # 找到表达式开始
                if current_part:
                    parts.append(current_part)
                    current_part = ""
                
                # 找到表达式结束
                brace_count = 1
                expr_start = i + 1
                i += 1
                
                while i < len(fstring_content) and brace_count > 0:
                    if fstring_content[i] == '{':
                        brace_count += 1
                    elif fstring_content[i] == '}':
                        brace_count -= 1
                    i += 1
                
                if brace_count == 0:
                    expression = fstring_content[expr_start:i-1]
                    expressions.append(expression)
                    parts.append("{}")  # 占位符
                else:
                    # 未匹配的花括号，按字面量处理
                    current_part += fstring_content[expr_start-1:i]
            
            elif fstring_content[i] == '{' and i + 1 < len(fstring_content) and fstring_content[i + 1] == '{':
                # 转义的花括号 {{
                current_part += '{'
                i += 2
            elif fstring_content[i] == '}' and i + 1 < len(fstring_content) and fstring_content[i + 1] == '}':
                # 转义的花括号 }}
                current_part += '}'
                i += 2
            else:
                current_part += fstring_content[i]
                i += 1
        
        if current_part:
            parts.append(current_part)
        
        # 合并连续的文本部分
        merged_parts = []
        expr_index = 0
        
        for part in parts:
            if part == "{}":
                merged_parts.append(part)
            else:
                if merged_parts and merged_parts[-1] != "{}":
                    merged_parts[-1] += part
                else:
                    merged_parts.append(part)
        
        return merged_parts, expressions
    
    def fix_fstring_patterns(self, content: str) -> str:
        """修复f-string模式"""
        
        # 更准确的f-string匹配模式
        patterns = [
            # f"..." 格式 - 改进的正则表达式，正确处理嵌套花括号
            (r'f"((?:[^"{}]|\{[^}]*\})*)"', '"'),
            # f'...' 格式 - 改进的正则表达式，正确处理嵌套花括号
            (r"f'((?:[^'{}]|\{[^}]*\})*)'", "'"),
        ]
        
        new_content = content
        
        for pattern, quote_char in patterns:
            matches = list(re.finditer(pattern, content))
            
            for match in matches:
                fstring_content = match.group(1)
                
                # 检查是否包含需要修复的嵌套引号
                if self._needs_fixing(fstring_content):
                    line_num, col_start = self._get_line_col(content, match.start())
                    _, col_end = self._get_line_col(content, match.end())
                    
                    # 转换为.format()
                    format_string, format_args = self._convert_to_format(fstring_content, quote_char)
                    
                    if format_args:
                        fixed_code = f'"{format_string}".format({", ".join(format_args)})'
                    else:
                        fixed_code = f'"{format_string}"'
                    
                    # 记录修复信息
                    fix_info = FixInfo(
                        line_num=line_num,
                        col_start=col_start,
                        col_end=col_end,
                        original=match.group(0),
                        fixed=fixed_code,
                        description="转换f-string为.format()调用"
                    )
                    self.fixes.append(fix_info)
        
        # 应用修复（从后往前，避免位置偏移）
        for pattern, quote_char in patterns:
            def replacer(match):
                fstring_content = match.group(1)
                
                if self._needs_fixing(fstring_content):
                    format_string, format_args = self._convert_to_format(fstring_content, quote_char)
                    
                    if format_args:
                        return f'"{format_string}".format({", ".join(format_args)})'
                    else:
                        return f'"{format_string}"'
                
                return match.group(0)
            
            new_content = re.sub(pattern, replacer, new_content)
        
        return new_content
    
    def _needs_fixing(self, fstring_content: str) -> bool:
        """检查f-string是否需要修复"""
        # 更精确的检查模式
        patterns_to_fix = [
            # 检查.join()调用中包含引号的情况
            r'\{[^}]*[\'"][^}]*\.join\([^}]*\)[^}]*\}',
            # 检查简单的引号+.join模式，如 {",".join(list)}
            r'\{[\'"][^\'\"]*[\'"]\.join\([^}]+\)\}',
            # 检查条件表达式中包含引号的情况
            r'\{[^}]*[\'"][^}]*\sif\s[^}]*\selse\s[^}]*[\'"][^}]*\}',
            # 检查表达式中有多个引号的情况
            r'\{[^}]*[\'"][^}]*[\'"][^}]*\}',
        ]
        
        for pattern in patterns_to_fix:
            if re.search(pattern, fstring_content):
                return True
        
        # 额外检查：包含引号且包含.join的情况
        if (('["\']' in fstring_content or '[\'""]' in fstring_content) and 
            '.join(' in fstring_content):
            return True
        
        return False
    
    def _convert_to_format(self, fstring_content: str, original_quote: str) -> Tuple[str, List[str]]:
        """将f-string内容转换为.format()格式"""
        # 使用正则表达式找到所有的{expression}
        expressions = []
        format_string = fstring_content
        
        # 找到所有表达式
        def replace_expr(match):
            expr = match.group(1)
            expressions.append(expr)
            return "{}"
        
        # 替换表达式为占位符
        format_string = re.sub(r'\{([^}]+)\}', replace_expr, format_string)
        
        # 处理转义的花括号
        format_string = format_string.replace('{{', '{').replace('}}', '}')
        
        return format_string, expressions
    
    def fix_content(self, content: str) -> str:
        """修复内容中的所有f-string问题"""
        self.fixes.clear()
        return self.fix_fstring_patterns(content)
    
    def print_fixes(self, file_path: str):
        """打印修复详情"""
        if not self.fixes:
            print(f"⏭️  {file_path}: 无需修复")
            return
        
        print(f"\n🔧 修复文件: {file_path}")
        print(f"📊 发现 {len(self.fixes)} 处需要修复的f-string")
        print("-" * 80)
        
        for i, fix in enumerate(self.fixes, 1):
            print(f"\n🔍 修复 #{i}:")
            print(f"   位置: 第{fix.line_num}行, 第{fix.col_start}-{fix.col_end}列")
            print(f"   描述: {fix.description}")
            
            print(f"\n   📝 修改前:")
            print(f"      {fix.original}")
            
            print(f"\n   ✅ 修改后:")
            print(f"      {fix.fixed}")
            
            if i < len(self.fixes):
                print()

def fix_file(file_path: Path) -> bool:
    """修复单个文件"""
    # 避免修复脚本自身
    script_name = Path(__file__).name if __file__ else "fix_fstring_format.py"
    if file_path.name == script_name:
        print(f"⏭️  {file_path}: 跳过脚本自身")
        return False
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        fixer = FormatFixer()
        new_content = fixer.fix_content(original_content)
        
        # 只有内容确实发生变化时才进行修复和备份
        if new_content != original_content and fixer.fixes:
            # 创建备份
            backup_path = file_path.with_suffix(file_path.suffix + '.backup')
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(original_content)
            
            # 写入修复后的文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            # 打印修复详情
            fixer.print_fixes(str(file_path))
            print(f"💾 已创建备份: {backup_path}")
            
            return True
        else:
            print(f"⏭️  {file_path}: 无需修复")
            return False
            
    except Exception as e:
        print(f"❌ 处理文件出错 {file_path}: {e}")
        return False

def cleanup_backup_files(target_path: Path) -> None:
    """交互式清理备份文件"""
    # 查找所有备份文件
    backup_files = []
    
    if target_path.is_file():
        backup_file = target_path.with_suffix(target_path.suffix + '.backup')
        if backup_file.exists():
            backup_files.append(backup_file)
    elif target_path.is_dir():
        backup_files = list(target_path.rglob('*.backup'))
    
    if not backup_files:
        print("📂 没有找到备份文件")
        return
    
    print(f"\n📂 找到 {len(backup_files)} 个备份文件:")
    for i, backup_file in enumerate(backup_files, 1):
        print(f"   {i}. {backup_file}")
    
    print("\n🤔 您想要如何处理这些备份文件?")
    print("   1. 删除所有备份文件")
    print("   2. 逐个选择删除")
    print("   3. 保留所有备份文件")
    print("   4. 查看备份文件内容对比")
    
    while True:
        try:
            choice = input("\n请选择 (1-4): ").strip()
            
            if choice == '1':
                # 删除所有备份文件
                print("\n🗑️  正在删除所有备份文件...")
                deleted_count = 0
                for backup_file in backup_files:
                    try:
                        backup_file.unlink()
                        print(f"   ✅ 已删除: {backup_file}")
                        deleted_count += 1
                    except Exception as e:
                        print(f"   ❌ 删除失败 {backup_file}: {e}")
                
                print(f"\n🎉 成功删除 {deleted_count}/{len(backup_files)} 个备份文件")
                break
                
            elif choice == '2':
                # 逐个选择删除
                print("\n📋 逐个确认删除备份文件:")
                deleted_count = 0
                
                for backup_file in backup_files:
                    while True:
                        delete_choice = input(f"\n删除 {backup_file}? (y/n/s): ").strip().lower()
                        if delete_choice in ['y', 'yes']:
                            try:
                                backup_file.unlink()
                                print(f"   ✅ 已删除: {backup_file}")
                                deleted_count += 1
                            except Exception as e:
                                print(f"   ❌ 删除失败: {e}")
                            break
                        elif delete_choice in ['n', 'no']:
                            print(f"   ⏭️  跳过: {backup_file}")
                            break
                        elif delete_choice in ['s', 'skip']:
                            print("   🛑 跳过剩余文件")
                            break
                        else:
                            print("   请输入 y(是)/n(否)/s(跳过剩余)")
                    
                    if delete_choice in ['s', 'skip']:
                        break
                
                print(f"\n🎉 成功删除 {deleted_count}/{len(backup_files)} 个备份文件")
                break
                
            elif choice == '3':
                # 保留所有备份文件
                print("\n💾 保留所有备份文件")
                print("💡 您可以稍后手动删除这些文件:")
                for backup_file in backup_files:
                    print(f"   📄 {backup_file}")
                break
                
            elif choice == '4':
                # 查看备份文件内容对比
                print("\n🔍 备份文件内容对比:")
                
                for backup_file in backup_files[:3]:  # 最多显示前3个文件的对比
                    original_file = backup_file.with_suffix('')
                    if original_file.exists():
                        print(f"\n📄 文件: {original_file}")
                        print("-" * 60)
                        
                        try:
                            with open(backup_file, 'r', encoding='utf-8') as f:
                                backup_content = f.read()
                            with open(original_file, 'r', encoding='utf-8') as f:
                                current_content = f.read()
                            
                            backup_lines = backup_content.splitlines()
                            current_lines = current_content.splitlines()
                            
                            print("📝 修改前 (前5行):")
                            for i, line in enumerate(backup_lines[:5], 1):
                                print(f"   {i:2d}: {line}")
                            
                            print("\n✅ 修改后 (前5行):")
                            for i, line in enumerate(current_lines[:5], 1):
                                print(f"   {i:2d}: {line}")
                            
                            if len(backup_files) > 3:
                                print(f"\n... 还有 {len(backup_files) - 3} 个文件，请使用文本编辑器查看")
                                break
                                
                        except Exception as e:
                            print(f"   ❌ 读取文件失败: {e}")
                
                # 查看后重新显示选项
                continue
                
            else:
                print("❌ 无效选择，请输入 1-4")
                continue
                
        except KeyboardInterrupt:
            print("\n\n👋 操作已取消")
            break
        except EOFError:
            print("\n\n👋 操作已取消")
            break

def test_single_pattern(pattern_str: str) -> None:
    """测试单个f-string模式是否会被正确识别和修复"""
    print(f"\n🧪 测试模式: {pattern_str}")
    print("-" * 50)
    
    fixer = FormatFixer()
    result = fixer.fix_content(pattern_str)
    
    if fixer.fixes:
        print("✅ 识别为需要修复")
        for fix in fixer.fixes:
            print(f"   原始: {fix.original}")
            print(f"   修复: {fix.fixed}")
    else:
        print("❌ 未识别为需要修复")

def main():
    """主函数"""
    # 如果第一个参数是 --test，则进入测试模式
    if len(sys.argv) >= 2 and sys.argv[1] == '--test':
        print("🧪 进入测试模式")
        
        test_patterns = [
            'f"  - {",".join(alias_list)} -> {target}\\n"',
            'f"关键词：{\'|\'.join(keywords)}\\n"',
            'f"结果：{\'|\'.join(keywords) if keyword_type == \'or\' else \'+\'.join(keywords)}\\n"',
            'f"🔑 关键词：{\'|\'.join(keywords) if keyword_type == \'or\' else \'+\'.join(keywords)}\\n"',
            'f"简单测试: {variable}"',  # 这个不应该被修复
        ]
        
        for pattern in test_patterns:
            test_single_pattern(pattern)
        
        return
    
    if len(sys.argv) < 2:
        print("用法: python fix_fstring_format.py <文件或目录路径>")
        print("测试: python fix_fstring_format.py --test")
        print("示例: python fix_fstring_format.py my_script.py")
        print("示例: python fix_fstring_format.py ./my_project")
        return
    
    target_path = Path(sys.argv[1])
    
    if not target_path.exists():
        print(f"❌ 路径不存在: {target_path}")
        return
    
    print("🚀 开始使用.format()修复f-string兼容性问题...")
    print("=" * 80)
    
    fixed_count = 0
    total_files = 0
    
    if target_path.is_file():
        if target_path.suffix == '.py':
            total_files = 1
            if fix_file(target_path):
                fixed_count += 1
        else:
            print("❌ 请提供Python文件(.py)")
            return
    
    elif target_path.is_dir():
        py_files = list(target_path.rglob('*.py'))
        
        # 过滤掉脚本自身
        script_name = Path(__file__).name if __file__ else "fix_fstring_format.py"
        py_files = [f for f in py_files if f.name != script_name]
        
        total_files = len(py_files)
        print(f"📁 找到 {total_files} 个Python文件 (已排除脚本自身)")
        
        for py_file in py_files:
            if fix_file(py_file):
                fixed_count += 1
    
    print("\n" + "=" * 80)
    print(f"🎉 完成!")
    print(f"📈 统计: 处理了 {total_files} 个文件，修复了 {fixed_count} 个文件")
    
    if fixed_count > 0:
        print("💡 修复摘要:")
        print("   - 已为修复的文件创建 .backup 备份")
        print("   - f-string已转换为.format()调用")
        print("   - 请测试修复后的代码是否正常运行")
        
        # 交互式清理备份文件
        cleanup_backup_files(target_path)
    else:
        print("✨ 所有文件都无需修复，未创建任何备份文件")
    
    print("\n👋 感谢使用f-string修复工具!")

if __name__ == "__main__":
    main()