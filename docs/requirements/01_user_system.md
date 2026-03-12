# 01 - 用户系统规格

## 1. 概述

- 平台支持**双模式登录**并存（本规格中加密钱包部分引用 **spec 10**）：
  - **账号密码**：传统注册/登录（见下文 2.1–2.3）。
  - **加密钱包**：支持 BSC、ETH、SOL、Tron 四条链，详见 **docs/requirements/10_encrypted_wallet_user.md**。
- 用户可**先注册再绑定钱包**，或**先钱包登录再补填资料**；绑定后两种方式均可登录同一账号。
- 个人资料与游戏币体系对两类用户统一（见 2.3）。

---

## 2. 账号密码模式

## 2.1 用户注册
- **Endpoint:** `POST /api/auth/register`
- **Request Body:**
  - `username` (string, unique, 4-16 chars, alphanumeric)
  - `password` (string, 6-20 chars)
  - `email` (string, optional, for password recovery)
- **Success Response:**
  - `userId`
  - `token` (JWT)
  - `initialCoins` (e.g., 10000)
- **Error Handling:**
  - 用户名已存在
  - 用户名/密码格式无效

## 2.2 用户登录
- **Endpoint:** `POST /api/auth/login`
- **Request Body:**
  - `username`
  - `password`
- **Success Response:**
  - `userId`
  - `token` (JWT)
  - `userProfile` (object)
- **Error Handling:**
  - 用户名或密码错误

## 2.3 用户个人资料
- **Endpoint:** `GET /api/users/{userId}`
- **Data Points:**
  - `userId`
  - `username`
  - `avatarUrl`
  - `coinsBalance`
  - `level` / `experiencePoints`
  - `stats`:
    - `totalHandsPlayed`
    - `winRate` (percentage)
    - `biggestPotWon`
- **Functionality:**
  - 用户可以修改 `username` (有冷却时间，如30天) 和 `avatarUrl`。
  - `coinsBalance` 只能通过游戏输赢或系统奖励改变。

## 2.4 加密钱包登录与绑定概要（多链）

- **完整规格**：见 **docs/requirements/10_encrypted_wallet_user.md**。
- **支持链**：ETH（以太坊）、BSC（币安智能链）、SOL（索拉纳）、Tron（波场）。
- **流程概要**：前端连接钱包 → 服务端下发 Challenge → 用户签名 → 服务端验签通过则登录/注册；支持同一账号绑定多条链的多个地址。
- **API 概要**：`POST /api/auth/wallet/challenge`、`POST /api/auth/wallet/login`、`POST /api/auth/wallet/bind`、`POST /api/auth/wallet/unbind`、`GET /api/users/me/wallets`。
