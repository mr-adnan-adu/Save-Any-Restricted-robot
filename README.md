# Save Any Restricted Robot 🤖

This Telegram bot automatically downloads and sends media or files from both public and private channel posts, even restricted content.

---

## 💡 Features

- Download from `https://t.me/c/...` links
- Supports **private channels** via invite links
- Automatically joins private channels (if invite link provided)
- Sends files 📁, videos 🎞️, photos 🖼️, and messages 💬
- Fast and lightweight using **Pyrogram**

---

## 🚀 Deploy to Render (FREE)

Click below to deploy your own version instantly on Render:

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/mr-adnan-adu/Save-Any-Restricted-robot)

> 🔑 After deployment, don’t forget to set your environment variables (`API_ID`, `API_HASH`, `BOT_TOKEN`) in the **Render Dashboard** under the **Environment** tab.



## 🚀 Deploy to Koyeb (FREE)

Click below to deploy on [Koyeb](https://www.koyeb.com) cloud:

[![Deploy to Koyeb](https://www.koyeb.com/static/images/deploy/button.svg)](https://app.koyeb.com/deploy?type=git&repository=github.com/mr-adnan-adu/Save-Any-Restricted-robot&branch=main&name=save-restricted-bot)

> 🛠️ Environment Variables:
> - `API_ID`
> - `API_HASH`
> - `BOT_TOKEN`

---

## 📦 Manual Setup

### 1. Clone the Repo

```bash
git clone https://github.com/mr-adnan-adu/Save-Any-Restricted-robot.git
cd Save-Any-Restricted-robot
````

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Add Your Telegram Credentials

Create a `.env` file or set environment variables:

* `API_ID` → Get from [my.telegram.org](https://my.telegram.org)
* `API_HASH` → Get from [my.telegram.org](https://my.telegram.org)
* `BOT_TOKEN` → From [@BotFather](https://t.me/BotFather)

### 4. Run the Bot

```bash
python bot.py
```

---

## ✅ Usage Instructions

### ✅ Public Channel Post:

Just send the post link:

```
https://t.me/c/<channel_id>/<message_id>
```

### 🔒 Private Channel Post:

1. Send the invite link: `https://t.me/+abcd...`
2. Then send the post link: `https://t.me/c/...`
3. The bot will join and send the file

---

## 🛠️ Built With

* [Pyrogram](https://docs.pyrogram.org/)
* [Render](https://render.com)
* [Koyeb](https://www.koyeb.com)

---

## 👤 Author

Made with ❤️ by [@mr-adnan-adu](https://github.com/mr-adnan-adu)

```

---

### ✅ What’s New
- Added `Deploy to Koyeb` button
- Ready for automatic deployment via GitHub

---

Do you want me to:
- Push this `README.md` update to your GitHub?
- Add any demo screenshots or GIFs of the bot in action?

Let me know if you'd also like a **one-click deploy button for Railway** or **Replit**.
```
