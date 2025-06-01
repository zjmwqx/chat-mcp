"""
pytest配置文件
确保测试时能正确导入src目录下的模块
"""

import sys
from pathlib import Path

# 获取项目根目录
project_root = Path(__file__).parent.parent

# 将src目录添加到Python路径
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# 确保项目根目录也在路径中
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
