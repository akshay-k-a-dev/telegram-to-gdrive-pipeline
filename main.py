import os
import time
import asyncio
from telethon import TelegramClient
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, DownloadColumn, TransferSpeedColumn
from rich.console import Console

console = Console()

# ===== CONFIG =====
api_id = "YOUR_API_ID"
api_hash = "YOUR_API_HASH"
channel_username = "YOUR_CHANNEL_USERNAME"  # e.g. "my_channel" or channel ID
session_name = "telegram_backup_session"
gdrive_folder_id = "YOUR_GOOGLE_DRIVE_FOLDER_ID"
log_file = "uploaded_files.log"
failed_log_file = "failed_downloads.log"
temp_dir = "temp_downloads"
download_resume_dir = "incomplete_uploads"

MAX_DOWNLOAD_WAIT = 10 * 60  # 10 minutes
MAX_DOWNLOAD_RETRIES = 3
MAX_UPLOAD_RETRIES = 3
MAX_CONCURRENT_DOWNLOADS = 3
MAX_CONCURRENT_UPLOADS = 2

# Allowed file extensions (no mp4/mkv)
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".mp3", ".wav", ".ogg", ".flac", ".m4a"}

# ==== INIT ====
os.makedirs(temp_dir, exist_ok=True)
os.makedirs(download_resume_dir, exist_ok=True)

if os.path.exists(log_file):
    with open(log_file, "r") as f:
        uploaded_ids = set(line.strip() for line in f)
else:
    uploaded_ids = set()

client = TelegramClient(session_name, api_id, api_hash)

gauth = GoogleAuth()
gauth.LoadClientConfigFile("PATH_TO_CLIENT_SECRETS_JSON")  # e.g. "./client_secrets.json"
gauth.LocalWebserverAuth()
drive = GoogleDrive(gauth)

# ==== GLOBAL FLAG ====
skip_current = False


async def check_skip_command():
    """Check console input for 's' while downloading/uploading."""
    global skip_current
    loop = asyncio.get_event_loop()
    while True:
        try:
            cmd = await loop.run_in_executor(None, input, "")
            if cmd.strip().lower() == "s":
                skip_current = True
                console.print("[yellow]⏭ Skip command received![/yellow]")
        except EOFError:
            break


async def download_with_retry(message, file_name, file_path):
    """Download file with retry and timeout logic."""
    global skip_current
    for attempt in range(1, MAX_DOWNLOAD_RETRIES + 1):
        skip_current = False
        try:
            start_time = time.time()
            with Progress(
                TextColumn("[cyan]Downloading...[/cyan] {task.description}"),
                BarColumn(),
                "[progress.percentage]{task.percentage:>3.1f}%",
                DownloadColumn(),
                TransferSpeedColumn(),
                TimeRemainingColumn(),
                console=console
            ) as progress:
                task = progress.add_task(file_name, total=None)
                download_task = asyncio.create_task(
                    message.download_media(file=file_path)
                )

                while not download_task.done():
                    await asyncio.sleep(1)
                    if skip_current:
                        download_task.cancel()
                        if os.path.exists(file_path):
                            os.remove(file_path)
                        return None
                    if not os.path.exists(file_path) and (time.time() - start_time > MAX_DOWNLOAD_WAIT):
                        raise TimeoutError("Download did not start in 10 minutes")

                result = await download_task
                if result:
                    progress.update(task, completed=1)
                    return result

        except Exception as e:
            console.print(f"[red]❌ Download failed ({file_name}) Attempt {attempt}/{MAX_DOWNLOAD_RETRIES}: {e}[/red]")
            if attempt < MAX_DOWNLOAD_RETRIES:
                await asyncio.sleep(5)
            else:
                with open(failed_log_file, "a") as f:
                    f.write(f"{message.id} - {file_name}\n")
                return None


def upload_to_gdrive(file_path, file_name, retries=MAX_UPLOAD_RETRIES):
    """Upload file to Google Drive with retry logic."""
    global skip_current
    for attempt in range(1, retries + 1):
        skip_current = False
        try:
            file_size = os.path.getsize(file_path)
            gfile = drive.CreateFile({'title': file_name, 'parents': [{'id': gdrive_folder_id}]})

            with open(file_path, "rb") as f:
                with Progress(
                    TextColumn("[green]Uploading...[/green] {task.description}"),
                    BarColumn(),
                    "[progress.percentage]{task.percentage:>3.1f}%",
                    TransferSpeedColumn(),
                    TimeRemainingColumn(),
                    console=console
                ) as progress:
                    task = progress.add_task(file_name, total=file_size)
                    chunk_size = 1024 * 1024
                    while True:
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        if skip_current:
                            console.print(f"[yellow]⏭ Skipped {file_name} during upload[/yellow]")
                            return False
                        progress.update(task, advance=len(chunk))

                    gfile.SetContentFile(file_path)
                    gfile.Upload()

            return True

        except Exception as e:
            console.print(f"[red]❌ Upload failed for {file_name} (Attempt {attempt}/{retries}): {e}[/red]")
            if attempt < retries:
                time.sleep(attempt * 5)
            else:
                return False


async def download_worker(download_queue, upload_queue, semaphore):
    """Worker to download files and put into upload queue."""
    while True:
        item = await download_queue.get()
        if item is None:
            download_queue.task_done()
            break

        message, file_name, file_path, msg_id = item
        async with semaphore:
            file_path = await download_with_retry(message, file_name, file_path)
            if file_path:
                await upload_queue.put((file_path, file_name, msg_id))
        download_queue.task_done()


async def upload_worker(upload_queue, semaphore):
    """Worker to upload files from queue to Google Drive."""
    while True:
        item = await upload_queue.get()
        if item is None:
            upload_queue.task_done()
            break

        file_path, file_name, msg_id = item
        async with semaphore:
            success = upload_to_gdrive(file_path, file_name)
            if success:
                with open(log_file, "a") as f:
                    f.write(msg_id + "\n")
                uploaded_ids.add(msg_id)
                os.remove(file_path)
                console.print(f"✅ [bold green]{file_name} uploaded & removed local copy[/bold green]")
            else:
                os.rename(file_path, os.path.join(download_resume_dir, file_name))
        upload_queue.task_done()


async def backup_channel():
    skip_task = asyncio.create_task(check_skip_command())
    await client.start()

    download_queue = asyncio.Queue()
    upload_queue = asyncio.Queue()

    download_sem = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)
    upload_sem = asyncio.Semaphore(MAX_CONCURRENT_UPLOADS)

    # Start workers
    download_workers = [asyncio.create_task(download_worker(download_queue, upload_queue, download_sem))
                        for _ in range(MAX_CONCURRENT_DOWNLOADS)]
    upload_workers = [asyncio.create_task(upload_worker(upload_queue, upload_sem))
                      for _ in range(MAX_CONCURRENT_UPLOADS)]

    async for message in client.iter_messages(channel_username, reverse=True):
        if not message.file or not message.file.name:
            continue

        ext = os.path.splitext(message.file.name)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            continue  # Skip disallowed file types

        msg_id = str(message.id)
        if msg_id in uploaded_ids:
            continue

        file_name = message.file.name
        file_path = os.path.join(temp_dir, file_name)

        if os.path.exists(file_path):
            await upload_queue.put((file_path, file_name, msg_id))
        else:
            await download_queue.put((message, file_name, file_path, msg_id))

    # Wait for all tasks
    await download_queue.join()
    await upload_queue.join()

    # Stop workers
    for _ in range(MAX_CONCURRENT_DOWNLOADS):
        await download_queue.put(None)
    for _ in range(MAX_CONCURRENT_UPLOADS):
        await upload_queue.put(None)

    await asyncio.gather(*download_workers)
    await asyncio.gather(*upload_workers)

    skip_task.cancel()
    console.print("🎉 [bold yellow]All files processed![/bold yellow]")


with client:
    client.loop.run_until_complete(backup_channel())
