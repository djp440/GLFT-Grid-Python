# 更新日志 (CHANGELOG)

## [v1.0.1] - 2025-08-06

### 🐛 Bug修复

#### 修复固定价差模式下价差仍会变动的问题

**问题描述**: 
- 在固定价差模式(`SPREAD_MODE = 'fixed'`)下，价差参数仍会随着市场波动率的变化而更新
- 这违背了固定价差模式的设计初衷，应该保持价差参数不变

**根本原因**: 
- `volatilityManager.py` 中的 `_update_trade_manager_spreads()` 方法会无条件地根据波动率更新价差参数
- 该方法没有检查当前的价差模式设置

**解决方案**: 
- 在 `_update_trade_manager_spreads()` 方法中添加价差模式检查逻辑
- 仅在动态模式(`dynamic`)或混合模式(`hybrid`)下才根据波动率更新价差
- 在固定模式(`fixed`)下跳过价差更新，保持原有价差参数不变

**修改文件**: 
- `core/volatilityManager.py`: 添加价差模式检查逻辑
- `docs/价差模式使用说明.md`: 添加常见问题解答
- `test_fixed_spread.py`: 新增测试脚本验证修复效果

**验证方法**: 
```bash
python test_fixed_spread.py
```

**影响范围**: 
- ✅ 修复后，固定价差模式下价差参数保持稳定
- ✅ 动态和混合模式功能不受影响
- ✅ 向后兼容，无需修改现有配置

---

## [v1.0.0] - 2025-08-05

### 🎉 初始版本

- 实现基础网格交易功能
- 支持多种价差模式：固定、动态、混合
- 集成波动率管理器
- 完整的配置系统
- 详细的日志记录

---

## 版本说明

### 版本号格式
采用语义化版本控制 (Semantic Versioning)：`主版本号.次版本号.修订号`

- **主版本号**: 不兼容的API修改
- **次版本号**: 向后兼容的功能性新增
- **修订号**: 向后兼容的问题修正

### 更新类型图标
- 🎉 新功能 (Features)
- 🐛 Bug修复 (Bug Fixes)
- 📝 文档更新 (Documentation)
- 🔧 配置变更 (Configuration)
- ⚡ 性能优化 (Performance)
- 🔒 安全修复 (Security)
- 💥 破坏性变更 (Breaking Changes)