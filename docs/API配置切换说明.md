# API配置切换说明

## 概述

本文档说明如何在GLFT网格交易程序中进行沙盒模式和实盘模式的切换。

## 环境变量配置

### .env文件结构

```env
# 沙盒环境API配置
apiKey = your_sandbox_api_key
secret = your_sandbox_secret
password = your_sandbox_password

# 实盘环境API配置
prod_apiKey = your_production_api_key
prod_secret = your_production_secret
prod_password = your_production_password

# 模式控制参数
sandbox = True  # True=沙盒模式, False=实盘模式
```

## 模式切换

### 沙盒模式（默认）

```env
sandbox = True
```

- 使用 `apiKey`, `secret`, `password` 配置
- 连接到交易所沙盒环境
- 使用虚拟资金进行测试
- 安全无风险

### 实盘模式

```env
sandbox = False
```

- 使用 `prod_apiKey`, `prod_secret`, `prod_password` 配置
- 连接到交易所实盘环境
- 使用真实资金进行交易
- ⚠️ **存在资金风险**

## 切换步骤

### 1. 准备API密钥

**沙盒环境：**
- 在交易所申请沙盒API密钥
- 配置到 `apiKey`, `secret`, `password`

**实盘环境：**
- 在交易所申请实盘API密钥
- 配置到 `prod_apiKey`, `prod_secret`, `prod_password`
- 确保API权限包含：现货交易、合约交易、账户查询

### 2. 修改配置

编辑 `.env` 文件中的 `sandbox` 参数：

```bash
# 切换到实盘模式
sandbox = False

# 切换到沙盒模式
sandbox = True
```

### 3. 验证配置

运行测试脚本验证配置：

```bash
python tests/test_实盘准备检查.py
```

### 4. 启动程序

使用安全启动脚本：

```bash
python 启动实盘测试.py
```

## 安全建议

### 🔒 API密钥安全

1. **分离管理**：沙盒和实盘API密钥分开管理
2. **权限最小化**：只授予必要的交易权限
3. **定期轮换**：定期更换API密钥
4. **环境隔离**：不要在生产环境使用沙盒密钥

### ⚠️ 实盘切换警告

1. **充分测试**：在沙盒环境充分测试后再切换实盘
2. **小额开始**：实盘测试建议从小额资金开始
3. **监控机制**：实盘运行时保持密切监控
4. **应急预案**：准备紧急停止和手动干预方案

### 📊 风险控制

实盘模式建议配置：

```json
{
  "maxStockRadio": 0.25,     // 最大持仓比例25%
  "orderAmountRatio": 0.02,  // 单次下单比例2%
  "baseSpread": 0.002,       // 基础价差0.2%
  "orderCoolDown": 5         // 下单冷却时间5秒
}
```

## 程序逻辑

### 自动选择机制

程序会根据 `sandbox` 参数自动选择相应的API配置：

```python
if sandbox == "False":
    # 实盘模式
    current_apiKey = prod_apiKey
    current_secret = prod_secret
    current_password = prod_password
    is_sandbox = False
else:
    # 沙盒模式
    current_apiKey = apiKey
    current_secret = secret
    current_password = password
    is_sandbox = True
```

### 日志记录

程序启动时会记录当前使用的API配置模式：

- 沙盒模式：`"使用沙盒API配置"`
- 实盘模式：`"使用实盘API配置"`

## 故障排除

### 常见问题

1. **API配置不完整**
   - 检查相应模式下的API密钥是否完整配置
   - 确保没有空值或格式错误

2. **连接失败**
   - 验证API密钥的有效性
   - 检查网络连接
   - 确认交易所服务状态

3. **权限错误**
   - 确认API密钥具有必要的交易权限
   - 检查IP白名单设置

### 测试验证

使用测试脚本验证配置：

```bash
# 运行完整测试
python tests/test_实盘准备检查.py

# 检查特定配置
python 启动实盘测试.py
```

## 总结

通过合理配置 `.env` 文件中的API密钥和 `sandbox` 参数，可以安全地在沙盒和实盘模式之间切换。建议在充分的沙盒测试后，谨慎地切换到实盘模式，并始终保持适当的风险控制措施。