

# 🚀 Telegram → Google Drive Pipeline

> **Backup your Telegram files automatically, like a boss.**

---

## 🤔 Why I Made This

I used Telegram as my **personal cloud** for years —
stuffed it with images, music, memes, GIFs… and suddenly:
📈 **3,000+ files** and counting.

At that point, finding anything in Telegram was like:

```
search → scroll → scroll → scroll → rage quit
```

So I decided to **rescue my files** and move them to **Google Drive**,
where they can actually be *searched*, *sorted*, and *found in seconds*.

This script:
✅ Downloads your Telegram **images**, **music**, **GIFs** (skips text & MP4s)
✅ Uploads them straight to **Google Drive**
✅ Can **resume** where it left off if your internet dies 💀
✅ Lets you **skip** a file mid-download/upload if you don’t want it
✅ Can do **parallel downloads & uploads** so it’s not slooooow
✅ Saves your sanity 🧠✨

---

## 🛠 Features

* **Auto-resume** → restarts from last successful upload
* **Skip command** → type `s` during download/upload to skip the current file
* **Retry logic** → failed files will retry up to 3 times before being skipped
* **Timeout handling** → skips files that don’t start downloading after 10 min
* **Selective backup** → only grabs **images, music, GIFs** (no MP4s, no random text files)
* **Parallel transfers** → downloads & uploads multiple files at once for speed

---

## 📦 Requirements

* Python **3.8+**
* A **Telegram API key** → [Get it here](https://my.telegram.org/auth)
* A **Google Drive API client secret** → [Follow this guide](https://developers.google.com/drive/api/v3/quickstart/python)
* Internet that doesn’t cry halfway through 😅

---

## ⚙️ Installation

```bash
# Clone the repo
git clone https://github.com/akshay-k-a-dev/telegram-to-gdrive-pipeline.git
cd telegram-to-gdrive-pipeline

# Install dependencies
pip install -r requirements.txt
```

---

## 🔑 Configuration

1️⃣ Put your **Telegram API ID** & **API Hash** in the config section of the script.
2️⃣ Download your **Google Drive client\_secrets.json** and save it somewhere safe.
3️⃣ Update the script with your **Google Drive folder ID**.

---

## 🚀 Usage

```bash
python backup.py
```

* Script will ask you to log into **Telegram** on first run.
* It will also open a browser window for **Google Drive authentication**.
* Sit back, relax, and let it work. ☕

💡 While it’s running:

* Type **`s`** → skip the current file and move to the next one.

---

## 📜 Logs

* **uploaded\_files.log** → Keeps track of files already uploaded.
* **failed\_downloads.log** → Files that failed after retries.

---

## 🎯 Roadmap

* [ ] Add support for MP4 video backup (optional)
* [ ] Add filtering by file size
* [ ] Make it run as a scheduled background service

---

## 💬 Final Words

> This project started as a **"I’ll just move a few files"** thing…
> And turned into a **"Holy crap my Telegram is a warehouse"** mission.
>
> Now my files live happily in Google Drive,
> and I don’t have to scroll endlessly anymore.
>
> 🐢 + ⚡ = ❤️

