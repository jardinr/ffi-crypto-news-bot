# 🚀 FFI Crypto News Bot - Deployment Instructions

## 📋 **Quick Setup Guide**

### **Step 1: Create GitHub Repository**
1. Go to **https://github.com/new**
2. Repository name: `ffi-crypto-news-bot`
3. Description: `🚀 FFI Crypto News Bot - Advanced crypto news aggregator`
4. **Public** ✅
5. Upload all bot files

### **Step 2: Add Repository Secrets**
Go to **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

**Add these 3 secrets:**

**Secret 1:**
- **Name**: `TELEGRAM_BOT_TOKEN`
- **Value**: `your_telegram_bot_token_here`

**Secret 2:**
- **Name**: `TELEGRAM_CHAT_ID`
- **Value**: `your_telegram_chat_id_here`

**Secret 3:**
- **Name**: `DISCORD_WEBHOOK_URL`
- **Value**: `your_discord_webhook_url_here`

### **Step 3: Enable Workflow**
1. Go to **Actions** tab
2. Enable workflows
3. Click **"FFI Crypto News Bot"**
4. Click **"Run workflow"** to test

## 🎯 **How to Get Your Values:**

### **Telegram Bot Token:**
1. Message @BotFather on Telegram
2. Create new bot with `/newbot`
3. Copy the token provided

### **Telegram Chat ID:**
1. Start conversation with your bot
2. Visit: `https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates`
3. Find the "chat" → "id" value

### **Discord Webhook URL:**
1. Go to your Discord server
2. Right-click channel → Edit Channel
3. Integrations → Webhooks → New Webhook
4. Copy webhook URL

## ✅ **Expected Results:**

After deployment:
- ⏰ **Runs every hour automatically**
- 📱 **Delivers to Telegram and Discord**
- 📊 **8 crypto articles per execution**
- 🤖 **AI sentiment analysis included**
- 📈 **Multiple premium news sources**

## 🔧 **Troubleshooting:**

- **No messages received**: Check secrets are correctly added
- **Workflow fails**: Check Actions tab for error details
- **Bot not responding**: Verify bot token and chat permissions

## 🏆 **Features:**

- ✅ **Free forever** (GitHub Actions )
- ✅ **Reliable execution** (30-60 seconds per run)
- ✅ **Multiple sources** (CoinDesk, Cointelegraph, etc.)
- ✅ **Smart filtering** (crypto-relevant content only)
- ✅ **No maintenance** (set and forget)

**Your FFI Crypto News Bot is ready for 24/7 operation!** 🚀📈


