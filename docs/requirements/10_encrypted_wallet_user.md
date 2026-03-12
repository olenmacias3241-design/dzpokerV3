# 10 - 加密钱包用户系统

**文档类型**：产品需求规格  
**关联**：`docs/requirements/01_user_system.md`（主用户系统）、`docs/requirements/06_database_schema.md`（表结构）

---

## 1. 目的与范围

### 1.1 目的

- 支持用户通过**加密钱包**登录/注册，无需账号密码即可使用平台。
- 支持**多链**：用户可绑定多条链上的地址，同一平台账号可关联多个链、多个地址。

### 1.2 支持的链

| 链标识 | 链名称 | 说明 |
|--------|--------|------|
| **ETH** | Ethereum | 以太坊主网 |
| **BSC** | BNB Smart Chain | 币安智能链 |
| **SOL** | Solana | 索拉纳 |
| **Tron** | TRON | 波场 |

### 1.3 与现有用户体系的关系

- **双模式**：平台同时支持「账号密码用户」（见 01）与「钱包用户」。
- 钱包用户可**可选**绑定邮箱/用户名，用于找回、昵称展示与客服。
- 同一账号可**先注册账号密码再绑定钱包**，或**先用钱包登录再补填资料**；绑定后两种登录方式均可进入同一用户身份。

---

## 2. 钱包登录/注册流程

### 2.1 前端流程概要

1. 用户选择「钱包登录」并选择链（ETH / BSC / SOL / Tron）。
2. 前端通过对应链的**钱包连接**（如 MetaMask、WalletConnect、Phantom、TronLink 等）获取当前连接的**钱包地址**。
3. 前端向服务端请求**随机 Nonce**（或短效 Challenge）。
4. 用户使用**私钥对 Nonce/Challenge 签名**（链上不提交，仅用于验证身份）。
5. 前端将「链标识 + 地址 + 签名」提交服务端。
6. 服务端**验签**：用地址恢复出签名者，确认为该地址持有者；若该地址未注册则自动**创建钱包用户**并登录，若已绑定则直接登录。

### 2.2 各链验签与地址格式

| 链 | 地址格式示例 | 签名方式 | 服务端验签要点 |
|----|--------------|----------|----------------|
| **ETH** | 0x 开头的 42 字符 | personal_sign / EIP-191 | 用 ecrecover 恢复 signer，与地址比对（大小写 EIP-55） |
| **BSC** | 同 ETH | 同 ETH（兼容 EVM） | 与 ETH 相同 |
| **SOL** | Base58，32–44 字符 | 对 message 的 Ed25519 签名 | 使用 nacl/solana 库验签，恢复公钥与地址比对 |
| **Tron** | T 开头的 Base58Check | 对 message 的 ECDSA(secp256k1) 签名 | Tron 标准验签，地址可由公钥推导 |

- **Nonce/Challenge**：建议服务端生成随机字符串（或带过期时间），下发给前端；前端对「登录: {nonce}」或统一格式的 message 签名，防止重放。

### 2.3 注册与绑定策略

- **首次钱包登录**：若地址在系统中不存在，则自动创建「钱包用户」记录，并可选引导用户设置昵称/头像。
- **多地址绑定**：允许同一用户（同一 `user_id`）绑定多条链的多个地址；登录时用「任意已绑定地址+对应链」即可登录到同一账号。
- **解绑**：可支持「解绑某链某地址」，需二次验证（如该地址再次签名或账号密码验证），且解绑后该地址可再被其他账号绑定或重新注册。

---

## 3. API 定义

### 3.1 获取登录 Challenge（Nonce）

- **Endpoint:** `POST /api/auth/wallet/challenge`
- **Request Body:**
  - `chain`: `"ETH"` | `"BSC"` | `"SOL"` | `"Tron"`
  - `address`: string（该链上的钱包地址）
- **Success Response:**
  - `challenge`: string（一次性随机串或带时间戳的 message）
  - `expiresAt`: ISO8601（可选，Challenge 过期时间）
- **用途**：前端用此 challenge 作为签名内容，再调登录接口。

### 3.2 钱包登录/注册

- **Endpoint:** `POST /api/auth/wallet/login`
- **Request Body:**
  - `chain`: `"ETH"` | `"BSC"` | `"SOL"` | `"Tron"`
  - `address`: string
  - `signature`: string（对 challenge 的签名， hex 或 base64 视链而定）
  - `message`: string（可选，若前端本地拼 message 则传回服务端校验一致）
- **Success Response:**
  - `userId`: string
  - `token`: string (JWT)
  - `isNewUser`: boolean（是否本次新注册）
  - `userProfile`: object（同 01 用户资料结构，可含 `boundWallets`）
- **Error Handling:**
  - `invalid_signature`：验签失败
  - `challenge_expired`：Challenge 过期或已使用
  - `chain_not_supported`：链标识错误

### 3.3 绑定新钱包（已登录用户）

- **Endpoint:** `POST /api/auth/wallet/bind`
- **Headers:** `Authorization: Bearer <token>`
- **Request Body:**
  - `chain`, `address`, `signature`, `message`（同上；签名内容建议为「绑定: {address}」+ nonce）
- **Success Response:**
  - `boundWallets`: array of `{ chain, address }`
- **Error Handling:**
  - 该地址已被其他账号绑定
  - 验签失败

### 3.4 解绑钱包

- **Endpoint:** `POST /api/auth/wallet/unbind`
- **Request Body:**
  - `chain`, `address`
  - `signature`（可选：用该地址签名以二次确认）
- **约束**：至少保留一种登录方式（若仅剩一个钱包则不可解绑，或需先绑定其他方式）。

### 3.5 查询已绑定钱包

- **Endpoint:** `GET /api/users/me/wallets`
- **Response:**
  - `wallets`: `[{ "chain": "ETH", "address": "0x...", "isPrimary": boolean }]`

---

## 4. 安全与实现要点

### 4.1 安全

- **不存私钥**：服务端与前端均不存储用户私钥；仅存储链+地址及必要元数据。
- **Challenge 一次性**：每个 challenge 仅能用于一次登录，验签成功后立即失效。
- **防重放**：签名内容包含 nonce/过期时间，拒绝过期或重复使用的 challenge。
- **地址归一化**：ETH/BSC 地址统一为 EIP-55 校验格式存储；SOL/Tron 按各链规范归一化后存储。

### 4.2 与游戏币/资产的关系

- 钱包用户与「账号密码用户」在平台内使用**同一套游戏币/积分体系**（如 `coins_balance`）；是否支持链上充值/提现由**资产/支付规格**单独定义，本规格仅负责身份与绑定关系。

### 4.3 实现建议

- 服务端按链实现**验签模块**（ETH/BSC 可共用一套 EVM 验签；SOL、Tron 各一套）。
- 前端按链接入官方/社区推荐的钱包 SDK（如 ethers.js、@solana/web3.js、tronweb），统一封装「请求地址 + 请求签名」接口，便于多链切换。

---

## 5. 数据库扩展（参考 06）

- 在 `users` 表或独立表 `user_wallets` 中记录「用户–链–地址」绑定关系；钱包登录时先查 `user_wallets` 得到 `user_id` 再发 JWT。  
- 具体表结构见 `docs/requirements/06_database_schema.md` 中「加密钱包与绑定」相关章节。

---

**文档版本**：1.0  
**最后更新**：2026-03-12
