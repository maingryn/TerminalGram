import os
import json
import shutil
import subprocess
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Загрузка конфигураций
with open("config.json") as f:
    CONFIG = json.load(f)

with open("user.json") as f:
    USERS = json.load(f)

with open("settings.json") as f:
    COMMAND_PERMISSIONS = json.load(f)

OWNER_ID = USERS["owner"]
MEMBER_IDS = USERS.get("members", [])
pending_deletion = {}
user_dirs = {}

def get_user_dir(user_id):
    if user_id not in user_dirs:
        user_dirs[user_id] = os.path.expanduser("~")
    return user_dirs[user_id]

def is_authorized(user_id):
    return user_id == OWNER_ID or user_id in MEMBER_IDS

def is_allowed(user_id, command):
    if user_id == OWNER_ID:
        return True
    return COMMAND_PERMISSIONS.get(command, False)

async def handle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_authorized(user_id):
        return

    command = update.message.text.strip()
    cwd = get_user_dir(user_id)

    if command == "+" and user_id in pending_deletion:
        path = pending_deletion.pop(user_id)
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            await update.message.reply_text(f"Удалено: {path}")
        except Exception as e:
            await update.message.reply_text(f"Ошибка при удалении: {e}")
        return

    try:
        parts = command.split()
        if not parts:
            await update.message.reply_text("Пустая команда.")
            return

        cmd = parts[0]
        args = parts[1:]

        if not is_allowed(user_id, cmd):
            await update.message.reply_text("Команда запрещена.")
            return

        if cmd == "cd":
            new_path = os.path.abspath(os.path.join(cwd, *args))
            if os.path.isdir(new_path):
                user_dirs[user_id] = new_path
                await update.message.reply_text(f"Текущая директория: {new_path}")
            else:
                await update.message.reply_text("Папка не найдена.")
        elif cmd == "ls":
            items = os.listdir(cwd)
            lines = []
            for item in items:
                full_path = os.path.join(cwd, item)
                if os.path.isdir(full_path):
                    lines.append(f"[DIR] {item}")
                else:
                    lines.append(item)
            content = f"Текущая директория:\n{cwd}\n\n" + ("\n".join(lines) if lines else "Пусто.")
            await update.message.reply_text(content)
        elif cmd == "mkdir":
            os.makedirs(os.path.join(cwd, *args), exist_ok=True)
            await update.message.reply_text("Папка создана.")
        elif cmd == "touch":
            for name in args:
                open(os.path.join(cwd, name), 'a').close()
            await update.message.reply_text("Файлы созданы.")
        elif cmd == "cat":
            path = os.path.join(cwd, *args)
            with open(path, 'r') as f:
                content = f.read()
            await update.message.reply_text(content or "Файл пуст.")
        elif cmd == "echo":
            await update.message.reply_text(" ".join(args))
        elif cmd == "rm":
            path = os.path.join(cwd, *args)
            pending_deletion[user_id] = path
            await update.message.reply_text(f"Вы уверены, что хотите удалить: {path}?\nНапишите '+' для подтверждения.")
        else:
            result = subprocess.run(command, cwd=cwd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output = result.stdout.strip() or result.stderr.strip() or "Выполнено."
            await update.message.reply_text(output)
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_authorized(update.effective_user.id):
        await update.message.reply_text("TerminalGram запущен. Введите команду.")

def main():
    app = ApplicationBuilder().token(CONFIG["token"]).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_command))
    app.run_polling()

if __name__ == '__main__':
    main()