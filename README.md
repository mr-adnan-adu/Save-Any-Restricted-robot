

````markdown
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

> 🔑 After deployment, don’t forget to set your environment variables (`API_ID`, `API_HASH`, `BOT_TOKEN`) in the **Render Dashboard** under **Environment** tab.

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

Create a `.env` file or use environment variables:

* `API_ID` → Get it from [https://my.telegram.org](https://my.telegram.org)
* `API_HASH` → Same place
* `BOT_TOKEN` → From [@BotFather](https://t.me/BotFather)

### 4. Run the Bot

```bash
python bot.py
```

---

## ✅ Usage Instructions

### ✅ Public Channel Post:

Send the post link directly:

```
https://t.me/c/<channel_id>/<message_id>
```

### 🔒 Private Channel Post:

1. Send the invite link: `https://t.me/+abcd...`
2. Then send the post link: `https://t.me/c/...`
3. The bot will join the channel and send you the file

---

## 🛠️ Built With

* [Pyrogram](https://docs.pyrogram.org/)
* [Render](https://render.com) - for free hosting

---

## 👤 Author

Made with ❤️ by [@mr-adnan-adu](https://github.com/mr-adnan-adu)

```

---

### ✅ What to do next:
1. Copy this content into your repo's `README.md` file (you can edit it on GitHub directly).
2. Anyone can now click the **"Deploy to Render"** button and launch your bot!

Would you like me to open a **pull request** to your repo and add this automatically?
```
