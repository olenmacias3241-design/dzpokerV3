# 01 - 用户系统规格

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
