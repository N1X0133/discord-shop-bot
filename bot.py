import subprocess
import sys
import importlib

# Автоустановка недостающих модулей
def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

required_packages = {
    'asyncpg': 'asyncpg',
    'discord': 'discord.py'
}

for module, package in required_packages.items():
    try:
        importlib.import_module(module)
        print(f"✅ {package} уже установлен")
    except ImportError:
        print(f"📦 Устанавливаю {package}...")
        install(package)
        print(f"✅ {package} установлен")

import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Select, View, Button, Modal, TextInput
import asyncpg
import os
from datetime import datetime

# ==================== НАСТРОЙКИ ====================

DB_CONFIG = {
    'host': 'node1.pghost.ru',
    'port': 15654,
    'database': 'bothost_db_43744b936cee',
    'user': 'bothost_db_43744b936cee',
    'password': 'FxTHYBq3OwRPZ3Ge4Y3BpYxkWQG9Jqbpd3Trn7cx9OE'
}

MAIN_ADMIN_ID = 927642459998138418
ADMIN_IDS = [927642459998138418, 500965898476322817]

BALANCE_CHANNEL_ID = 1481753586835783861
SHOP_CHANNEL_ID = 1481753891124019302
ADMIN_CHANNEL_ID = 1481754087614841033
ANNOUNCE_CHANNEL_ID = 1483097607424446514

NOTIFY_USER_IDS = [271067502102970371, 1048236913447940106]

# ==================== БОТ ====================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class ShopBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)
        self.db_pool = None

    async def setup_hook(self):
        self.db_pool = await asyncpg.create_pool(**DB_CONFIG, min_size=2, max_size=10)

        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id BIGINT PRIMARY KEY,
                    balance INTEGER NOT NULL DEFAULT 0,
                    name VARCHAR(255)
                );
                CREATE TABLE IF NOT EXISTS admins (
                    user_id BIGINT PRIMARY KEY
                );
                CREATE TABLE IF NOT EXISTS purchases (
                    id SERIAL PRIMARY KEY,
                    purchase_id VARCHAR(255) UNIQUE,
                    user_id BIGINT NOT NULL,
                    item_name VARCHAR(255) NOT NULL,
                    price INTEGER NOT NULL,
                    quantity INTEGER NOT NULL DEFAULT 1,
                    total INTEGER NOT NULL,
                    nickname VARCHAR(100),
                    cid VARCHAR(50),
                    purchase_date TIMESTAMP DEFAULT NOW(),
                    status VARCHAR(20) DEFAULT 'pending',
                    delivered_by VARCHAR(255),
                    delivered_date TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS inventory (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    item_name VARCHAR(255) NOT NULL,
                    received_date TIMESTAMP DEFAULT NOW(),
                    received_by VARCHAR(255),
                    nickname VARCHAR(100),
                    cid VARCHAR(50)
                );
                CREATE INDEX IF NOT EXISTS idx_purchases_user ON purchases(user_id);
                CREATE INDEX IF NOT EXISTS idx_purchases_status ON purchases(status);
                CREATE INDEX IF NOT EXISTS idx_inventory_user ON inventory(user_id);
            """)

            rows = await conn.fetch("SELECT user_id FROM admins")
            for r in rows:
                if r['user_id'] not in ADMIN_IDS:
                    ADMIN_IDS.append(r['user_id'])

            await conn.execute("INSERT INTO admins (user_id) VALUES ($1) ON CONFLICT DO NOTHING", MAIN_ADMIN_ID)
            for admin_id in ADMIN_IDS:
                await conn.execute("INSERT INTO admins (user_id) VALUES ($1) ON CONFLICT DO NOTHING", admin_id)

        await self.tree.sync()
        print(f"✅ Бот запущен! БД подключена. Админов: {len(ADMIN_IDS)}")

bot = ShopBot()

def is_admin(user_id):
    return user_id in ADMIN_IDS

def is_main_admin(user_id):
    return user_id == MAIN_ADMIN_ID

def can_confirm_delivery(user_id):
    return user_id in NOTIFY_USER_IDS or user_id == MAIN_ADMIN_ID

def is_allowed_channel(channel_id, command_type):
    if channel_id == ADMIN_CHANNEL_ID:
        return True
    if command_type == 'balance':
        return channel_id == BALANCE_CHANNEL_ID
    return channel_id == SHOP_CHANNEL_ID

# ==================== ФУНКЦИИ БД ====================

async def db_get_balance(user_id: int) -> int:
    async with bot.db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT balance FROM users WHERE id = $1", user_id)
        return row['balance'] if row else 0

async def db_set_balance(user_id: int, amount: int, name: str = None):
    async with bot.db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (id, balance, name) VALUES ($1, $2, $3)
            ON CONFLICT (id) DO UPDATE SET balance = $2, name = COALESCE($3, users.name)
        """, user_id, amount, name)

async def db_add_balance(user_id: int, amount: int, name: str = None):
    async with bot.db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (id, balance, name) VALUES ($1, $2, $3)
            ON CONFLICT (id) DO UPDATE SET balance = users.balance + $2, name = COALESCE($3, users.name)
        """, user_id, amount, name)

async def db_create_purchase(user_id: int, item_name: str, price: int,
                              quantity: int, nickname: str, cid: str, total: int) -> str:
    purchase_id = f"{user_id}_{datetime.now().timestamp()}"
    async with bot.db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO purchases (purchase_id, user_id, item_name, price, quantity, total,
                                   nickname, cid, purchase_date, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'pending')
        """, purchase_id, user_id, item_name, price, quantity, total, nickname, cid, datetime.now())
    return purchase_id

async def db_deliver_purchase(purchase_id: str, delivered_by: str, buyer_id: int,
                               item_name: str, quantity: int, nickname: str, cid: str):
    async with bot.db_pool.acquire() as conn:
        await conn.execute("""
            UPDATE purchases SET status='delivered', delivered_by=$1, delivered_date=NOW()
            WHERE purchase_id=$2 AND status='pending'
        """, delivered_by, purchase_id)
        for _ in range(quantity):
            await conn.execute("""
                INSERT INTO inventory (user_id, item_name, received_date, received_by, nickname, cid)
                VALUES ($1, $2, NOW(), $3, $4, $5)
            """, buyer_id, item_name, delivered_by, nickname, cid)

async def db_cancel_purchase(purchase_id: str, user_id: int, total: int):
    async with bot.db_pool.acquire() as conn:
        await conn.execute("""
            UPDATE purchases SET status='cancelled' WHERE purchase_id=$1 AND status='pending'
        """, purchase_id)
        await conn.execute("UPDATE users SET balance = balance + $1 WHERE id = $2", total, user_id)

async def db_get_pending_count(user_id: int) -> int:
    async with bot.db_pool.acquire() as conn:
        return await conn.fetchval("SELECT COUNT(*) FROM purchases WHERE user_id=$1 AND status='pending'", user_id)

async def db_get_all_pending():
    async with bot.db_pool.acquire() as conn:
        return await conn.fetch("""
            SELECT u.name as username, u.id as uid, p.*
            FROM purchases p JOIN users u ON u.id = p.user_id
            WHERE p.status='pending' ORDER BY p.purchase_date
        """)

async def db_get_user_inventory(user_id: int, limit: int = 20):
    async with bot.db_pool.acquire() as conn:
        return await conn.fetch("""
            SELECT * FROM inventory WHERE user_id=$1 ORDER BY received_date DESC LIMIT $2
        """, user_id, limit)

async def db_get_user_purchases(user_id: int, limit: int = 10):
    async with bot.db_pool.acquire() as conn:
        return await conn.fetch("""
            SELECT * FROM purchases WHERE user_id=$1 ORDER BY purchase_date DESC LIMIT $2
        """, user_id, limit)

async def db_get_stats():
    async with bot.db_pool.acquire() as conn:
        users = await conn.fetchval("SELECT COUNT(*) FROM users")
        total_balance = await conn.fetchval("SELECT COALESCE(SUM(balance), 0) FROM users")
        pending = await conn.fetchval("SELECT COUNT(*) FROM purchases WHERE status='pending'")
        delivered = await conn.fetchval("SELECT COUNT(*) FROM inventory")
        cancelled = await conn.fetchval("SELECT COUNT(*) FROM purchases WHERE status='cancelled'")
        spent = await conn.fetchval("SELECT COALESCE(SUM(total), 0) FROM purchases WHERE status!='cancelled'")
        return {'users': users, 'total_balance': total_balance, 'pending': pending,
                'delivered': delivered, 'cancelled': cancelled, 'spent': spent}

async def db_reset_pending_for_user(user_id: int, item_name: str = None) -> dict:
    async with bot.db_pool.acquire() as conn:
        if item_name:
            rows = await conn.fetch("""
                UPDATE purchases SET status='cancelled' WHERE user_id=$1 AND status='pending' AND item_name ILIKE $2
                RETURNING total
            """, user_id, f"%{item_name}%")
        else:
            rows = await conn.fetch("""
                UPDATE purchases SET status='cancelled' WHERE user_id=$1 AND status='pending'
                RETURNING total
            """, user_id)
        total_refund = sum(r['total'] for r in rows) if rows else 0
        if total_refund > 0:
            await conn.execute("UPDATE users SET balance = balance + $1 WHERE id = $2", total_refund, user_id)
        return {'count': len(rows) if rows else 0, 'refund': total_refund}

async def db_reset_all_pending() -> dict:
    async with bot.db_pool.acquire() as conn:
        rows = await conn.fetch("""
            UPDATE purchases SET status='cancelled' WHERE status='pending'
            RETURNING user_id, total
        """)
        refunds = {}
        for r in rows:
            refunds[r['user_id']] = refunds.get(r['user_id'], 0) + r['total']
        for uid, amount in refunds.items():
            await conn.execute("UPDATE users SET balance = balance + $1 WHERE id = $2", amount, uid)
        return {'count': len(rows) if rows else 0, 'refund': sum(refunds.values())}

# ==================== КНОПКИ ====================

class ConfirmDeliveryView(View):
    def __init__(self, buyer_id, item_name, quantity, nickname, cid, purchase_id, total_price):
        super().__init__(timeout=None)
        self.buyer_id = buyer_id
        self.item_name = item_name
        self.quantity = quantity
        self.nickname = nickname
        self.cid = cid
        self.purchase_id = purchase_id
        self.total_price = total_price

    @discord.ui.button(label="✅ Подтвердить выдачу", style=discord.ButtonStyle.green, emoji="✅")
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not can_confirm_delivery(interaction.user.id):
            await interaction.response.send_message("❌ Только указанные пользователи могут подтверждать!", ephemeral=True)
            return

        await db_deliver_purchase(self.purchase_id, interaction.user.name, self.buyer_id,
                                  self.item_name, self.quantity, self.nickname, self.cid)

        try:
            buyer = await bot.fetch_user(self.buyer_id)
            if buyer:
                embed = discord.Embed(title="✅ ТОВАР ВЫДАН!", description=f"Вам выдан: **{self.item_name}**",
                                      color=0x2ecc71, timestamp=datetime.now())
                embed.add_field(name="Количество", value=f"{self.quantity} шт.", inline=True)
                embed.add_field(name="Выдал", value=interaction.user.name, inline=True)
                embed.add_field(name="Никнейм", value=self.nickname, inline=True)
                embed.add_field(name="CID", value=self.cid, inline=True)
                embed.set_footer(text="by Ilya Vetrov")
                await buyer.send(embed=embed)
        except:
            pass

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.title = "✅ ВЫДАЧА ПОДТВЕРЖДЕНА!"
        embed.description = f"**{interaction.user.name}** подтвердил выдачу товара"
        embed.set_footer(text="Товар выдан")
        await interaction.message.edit(embed=embed, view=None)
        await interaction.response.send_message("✅ Выдача товара подтверждена!", ephemeral=True)

class DeliveryView(View):
    def __init__(self, user_id, item_name, quantity, nickname, cid, purchase_id, total_price):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.item_name = item_name
        self.quantity = quantity
        self.nickname = nickname
        self.cid = cid
        self.purchase_id = purchase_id
        self.total_price = total_price
        self.requested = False

    async def notify_users(self, interaction):
        admin_channel = bot.get_channel(ADMIN_CHANNEL_ID)
        if not admin_channel:
            return

        embed = discord.Embed(title="❓ ЗАПРОС НА ВЫДАЧУ ТОВАРА!",
                              description=f"**{interaction.user.name}** запросил выдачу товара.",
                              color=0xe74c3c, timestamp=datetime.now())
        embed.add_field(name="👤 Кто запросил", value=f"```{interaction.user.name}```", inline=True)
        embed.add_field(name="👤 ID покупателя", value=f"```{self.user_id}```", inline=True)
        embed.add_field(name="📦 Товар", value=f"```{self.item_name}```", inline=True)
        embed.add_field(name="🔢 Количество", value=f"```{self.quantity} шт.```", inline=True)
        embed.add_field(name="💰 Сумма", value=f"```{self.total_price} монет```", inline=True)
        embed.add_field(name="👤 Никнейм", value=f"```{self.nickname}```", inline=True)
        embed.add_field(name="🆔 CID", value=f"```{self.cid}```", inline=True)
        embed.set_footer(text="Нажмите кнопку для подтверждения")

        view = ConfirmDeliveryView(self.user_id, self.item_name, self.quantity,
                                   self.nickname, self.cid, self.purchase_id, self.total_price)
        mentions = " ".join(f"<@{uid}>" for uid in NOTIFY_USER_IDS)
        await admin_channel.send(mentions, embed=embed, view=view)

    @discord.ui.button(label="✅ Выдать", style=discord.ButtonStyle.green, emoji="✅")
    async def deliver_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user.id):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return

        await db_deliver_purchase(self.purchase_id, interaction.user.name, self.user_id,
                                  self.item_name, self.quantity, self.nickname, self.cid)

        try:
            buyer = await bot.fetch_user(self.user_id)
            if buyer:
                embed = discord.Embed(title="✅ ТОВАР ВЫДАН!", description=f"Вам выдан товар: **{self.item_name}**",
                                      color=0x2ecc71, timestamp=datetime.now())
                embed.add_field(name="Количество", value=f"```{self.quantity} шт.```", inline=True)
                embed.add_field(name="Выдал", value=f"```{interaction.user.name}```", inline=True)
                embed.add_field(name="Никнейм", value=f"```{self.nickname}```", inline=True)
                embed.add_field(name="CID", value=f"```{self.cid}```", inline=True)
                embed.set_footer(text="by Ilya Vetrov")
                await buyer.send(embed=embed)
        except:
            pass

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.add_field(name="Статус", value="✅ ВЫДАНО", inline=False)
        await interaction.message.edit(embed=embed, view=None)
        await interaction.response.send_message("✅ Товар отмечен как выданный!", ephemeral=True)

    @discord.ui.button(label="❌ Не выдавать", style=discord.ButtonStyle.red, emoji="❌")
    async def not_deliver_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user.id):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return

        await db_cancel_purchase(self.purchase_id, self.user_id, self.total_price)

        try:
            buyer = await bot.fetch_user(self.user_id)
            if buyer:
                embed = discord.Embed(title="💰 ВОЗВРАТ МОНЕТ",
                                      description=f"Ваш заказ на **{self.item_name}** был отменен.",
                                      color=0xf1c40f, timestamp=datetime.now())
                embed.add_field(name="Возвращено", value=f"```+{self.total_price} монет```", inline=True)
                embed.add_field(name="Причина", value="```Отказ в выдаче товара```", inline=True)
                embed.set_footer(text="by Ilya Vetrov")
                await buyer.send(embed=embed)
        except:
            pass

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.add_field(name="Статус", value="❌ ОТКАЗАНО (монеты возвращены)", inline=False)
        await interaction.message.edit(embed=embed, view=None)
        await interaction.response.send_message("❌ Товар отмечен как отказанный. Монеты возвращены!", ephemeral=True)

    @discord.ui.button(label="❓ Запросить", style=discord.ButtonStyle.blurple, emoji="❓")
    async def request_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_admin(interaction.user.id):
            await interaction.response.send_message("❌ Только администраторы!", ephemeral=True)
            return
        if self.requested:
            await interaction.response.send_message("❌ Запрос уже был отправлен!", ephemeral=True)
            return

        self.requested = True
        await self.notify_users(interaction)

        embed = interaction.message.embeds[0]
        embed.color = discord.Color.blurple()
        embed.add_field(name="Статус", value="❓ ЗАПРОС ОТПРАВЛЕН", inline=False)
        await interaction.message.edit(embed=embed, view=None)
        await interaction.response.send_message("✅ Запрос на выдачу отправлен!", ephemeral=True)

# ==================== МОДАЛЬНОЕ ОКНО ПОКУПКИ ====================

class PurchaseModal(Modal, title="🛒 Оформление покупки"):
    def __init__(self, item_name, item_price, item_note=""):
        super().__init__()
        self.item_name = item_name
        self.item_price = item_price
        self.item_note = item_note

        self.quantity = TextInput(label="Количество", placeholder="Введите количество (1-1000)", required=True, max_length=4)
        self.nickname = TextInput(label="Игровой Никнейм", placeholder="Введите ваш никнейм", required=True, max_length=50)
        self.cid = TextInput(label="CID", placeholder="Введите ваш CID", required=True, max_length=20)
        self.add_item(self.quantity)
        self.add_item(self.nickname)
        self.add_item(self.cid)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            quantity = int(self.quantity.value)
            if quantity < 1 or quantity > 1000:
                await interaction.response.send_message("❌ Количество от 1 до 1000!", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("❌ Введите число!", ephemeral=True)
            return

        if not self.nickname.value or not self.cid.value:
            await interaction.response.send_message("❌ Никнейм и CID обязательны!", ephemeral=True)
            return

        total_price = self.item_price * quantity
        balance = await db_get_balance(interaction.user.id)

        if balance < total_price:
            await interaction.response.send_message(f"❌ Недостаточно средств! Нужно: {total_price}, у вас: {balance}", ephemeral=True)
            return

        await db_set_balance(interaction.user.id, balance - total_price, interaction.user.name)
        purchase_id = await db_create_purchase(interaction.user.id, self.item_name, self.item_price,
                                               quantity, self.nickname.value, self.cid.value, total_price)

        for uid in NOTIFY_USER_IDS:
            try:
                user = await bot.fetch_user(uid)
                if user:
                    embed = discord.Embed(title="🛒 НОВАЯ ПОКУПКА!",
                                          description=f"**{interaction.user.name}** совершил покупку!",
                                          color=0x2ecc71, timestamp=datetime.now())
                    embed.add_field(name="📦 Товар", value=f"```{self.item_name}```", inline=True)
                    embed.add_field(name="🔢 Количество", value=f"```{quantity} шт.```", inline=True)
                    embed.add_field(name="💰 Сумма", value=f"```{total_price} монет```", inline=True)
                    embed.add_field(name="👤 Никнейм", value=f"```{self.nickname.value}```", inline=True)
                    embed.add_field(name="🆔 CID", value=f"```{self.cid.value}```", inline=True)
                    embed.set_footer(text="by Ilya Vetrov")
                    await user.send(embed=embed)
            except:
                pass

        special_note = ""
        if self.item_name == "⚡ Максимальный ур. выносливости":
            special_note = "\n❗ Вы должны быть в игре чтобы товар был выдан"

        embed = discord.Embed(title="✅ ПОКУПКА УСПЕШНО ОФОРМЛЕНА!", color=0x2ecc71, timestamp=datetime.now())
        embed.add_field(name="📦 Товар", value=f"```{self.item_name}```", inline=False)
        embed.add_field(name="🔢 Количество", value=f"```{quantity} шт.```", inline=True)
        embed.add_field(name="💰 Цена", value=f"```{total_price} монет```", inline=True)
        embed.add_field(name="👤 Никнейм", value=f"```{self.nickname.value}```", inline=True)
        embed.add_field(name="🆔 CID", value=f"```{self.cid.value}```", inline=True)
        if special_note:
            embed.add_field(name="⚠️ ВНИМАНИЕ", value=special_note, inline=False)
        else:
            embed.add_field(name="⏳ Статус", value="```Ожидает выдачи администратором```", inline=False)
        embed.set_footer(text="by Ilya Vetrov")
        await interaction.response.send_message(embed=embed, ephemeral=True)

        admin_channel = bot.get_channel(ADMIN_CHANNEL_ID)
        if admin_channel:
            admin_embed = discord.Embed(title="🛒 НОВАЯ ПОКУПКА!", color=0xe74c3c, timestamp=datetime.now())
            admin_embed.add_field(name="👤 Покупатель", value=f"```{interaction.user.name} ({interaction.user.id})```", inline=False)
            admin_embed.add_field(name="📦 Товар", value=f"```{self.item_name}```", inline=True)
            admin_embed.add_field(name="🔢 Количество", value=f"```{quantity} шт.```", inline=True)
            admin_embed.add_field(name="💰 Общая сумма", value=f"```{total_price} монет```", inline=True)
            admin_embed.add_field(name="👤 Никнейм", value=f"```{self.nickname.value}```", inline=True)
            admin_embed.add_field(name="🆔 CID", value=f"```{self.cid.value}```", inline=True)
            admin_embed.add_field(name="📊 Баланс после", value=f"```{balance - total_price} монет```", inline=False)
            if self.item_name == "⚡ Максимальный ур. выносливости":
                admin_embed.add_field(name="⚠️ ВНИМАНИЕ", value="❗ Требуется присутствие в игре для выдачи", inline=False)
            admin_embed.set_footer(text="by Ilya Vetrov")
            view = DeliveryView(interaction.user.id, self.item_name, quantity,
                                self.nickname.value, self.cid.value, purchase_id, total_price)
            await admin_channel.send(embed=admin_embed, view=view)

# ==================== VIEW МАГАЗИНА ====================

class ShopView(View):
    def __init__(self):
        super().__init__(timeout=None)

        self.shop_items = [
            {"name": "💊 Реанимнабор", "price": 50},
            {"name": "🛡️ Ремкоплект для брони", "price": 10},
            {"name": "🔫 MG Ammo", "price": 5, "note": "за 100 шт"},
            {"name": "🎯 Sniper Ammo", "price": 50, "note": "за 10 шт"},
            {"name": "⚡ Максимальный ур. выносливости", "price": 300, "note": "❗ Вы должны быть в игре"},
            {"name": "🔇 Глушитель", "price": 10},
            {"name": "📦 Увеличенный магазин (винтовка)", "price": 80},
            {"name": "📦 Увеличенный магазин (пистолет)", "price": 10},
            {"name": "🥁 Барабанный магазин (ПП)", "price": 40},
            {"name": "📦 Увеличенный магазин (снайперская винтовка)", "price": 45},
            {"name": "🔫 Тяжелый пулемет", "price": 65},
            {"name": "⚡ Тяжелый пулемет MK2", "price": 300},
            {"name": "🎯 Тяжелая снайперская", "price": 300},
            {"name": "⭐ Тяжелая снайперская MK2", "price": 800},
            {"name": "🔫 Штурмовой дробовик", "price": 500},
            {"name": "🔫 Тяжелый револьвер MK2", "price": 400},
        ]

        options = []
        for i, item in enumerate(self.shop_items):
            label = item["name"]
            if "note" in item:
                label += f" ({item['note']})"
            options.append(discord.SelectOption(label=label, value=str(i), description=f"{item['price']} монет"))

        self.select = Select(placeholder="🔍 Выберите товар...", options=options)
        self.select.callback = self.select_callback
        self.add_item(self.select)

        self.buy = Button(label="💰 Купить", style=discord.ButtonStyle.green, emoji="💳")
        self.buy.callback = self.buy_callback
        self.add_item(self.buy)

        self.balance_btn = Button(label="💎 Мой баланс", style=discord.ButtonStyle.blurple, emoji="💎")
        self.balance_btn.callback = self.balance_callback
        self.add_item(self.balance_btn)

        self.selected_item = None
        self.selected_note = ""

    async def select_callback(self, interaction: discord.Interaction):
        index = int(self.select.values[0])
        self.selected_item = self.shop_items[index]
        self.selected_note = self.selected_item.get("note", "")

        description = f"**{self.selected_item['name']}**\nЦена: {self.selected_item['price']} монет"
        if self.selected_note:
            description += f"\n*{self.selected_note}*"

        embed = discord.Embed(title="✅ Товар выбран", description=description, color=0x3498db)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def buy_callback(self, interaction: discord.Interaction):
        if not self.selected_item:
            await interaction.response.send_message("❌ Сначала выберите товар!", ephemeral=True)
            return

        if not is_allowed_channel(interaction.channel_id, 'shop'):
            await interaction.response.send_message(f"❌ Покупки только в канале <#{SHOP_CHANNEL_ID}>", ephemeral=True)
            return

        balance = await db_get_balance(interaction.user.id)

        if balance < self.selected_item["price"]:
            embed = discord.Embed(title="❌ Недостаточно средств",
                                  description=f"**Нужно:** {self.selected_item['price']} монет\n**У вас:** {balance} монет",
                                  color=0xe74c3c)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        modal = PurchaseModal(self.selected_item["name"], self.selected_item["price"], self.selected_note)
        await interaction.response.send_modal(modal)

    async def balance_callback(self, interaction: discord.Interaction):
        if not is_allowed_channel(interaction.channel_id, 'balance'):
            await interaction.response.send_message(f"❌ Баланс только в канале <#{BALANCE_CHANNEL_ID}>", ephemeral=True)
            return

        balance = await db_get_balance(interaction.user.id)
        pending = await db_get_pending_count(interaction.user.id)

        embed = discord.Embed(title="💰 ВАШ БАЛАНС", color=0xf1c40f, timestamp=datetime.now())
        embed.add_field(name="Монеты", value=f"```{balance}```", inline=True)
        embed.add_field(name="Ожидают выдачи", value=f"```{pending} шт.```", inline=True)
        embed.set_footer(text="by Ilya Vetrov")
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ==================== СЛЭШ-КОМАНДЫ ====================

@bot.tree.command(name="магазин", description="🛒 Открыть магазин")
async def slash_shop(interaction: discord.Interaction):
    if not is_allowed_channel(interaction.channel_id, 'shop'):
        await interaction.response.send_message(f"❌ Используйте канал <#{SHOP_CHANNEL_ID}>", ephemeral=True)
        return

    view = ShopView()

    embed = discord.Embed(title="🛒 ДОБРО ПОЖАЛОВАТЬ В МАГАЗИН",
                          description="```Выберите товар и укажите количество```",
                          color=0x9b59b6, timestamp=datetime.now())

    embed.add_field(name="📦 **Глава 1: Расходники**",
                    value="```"
                          "💊 Реанимнабор                      50 монет/шт\n"
                          "🛡️ Ремкоплект для брони             10 монет/шт\n"
                          "🔫 MG Ammo                            5 монет/100 шт\n"
                          "🎯 Sniper Ammo                       50 монет/10 шт\n"
                          "⚡ Максимальный ур. выносливости    300 монет/шт\n"
                          "⚡ Максимальный ур. выносливости - ❗ Вы должны быть в игре```",
                    inline=False)

    embed.add_field(name="⚙️ **Глава 2: Модули**",
                    value="```"
                          "🔇 Глушитель                         10 монет/шт\n"
                          "📦 Увеличенный магазин (винтовка)    80 монет/шт\n"
                          "📦 Увеличенный магазин (пистолет)    10 монет/шт\n"
                          "🥁 Барабанный магазин (ПП)           40 монет/шт\n"
                          "📦 Увеличенный магазин (снайперская) 45 монет/шт```",
                    inline=False)

    embed.add_field(name="🔫 **Глава 3: Спец. вооружение**",
                    value="```"
                          "🔫 Тяжелый пулемет              65 монет/шт\n"
                          "⚡ Тяжелый пулемет MK2         300 монет/шт\n"
                          "🎯 Тяжелая снайперская         300 монет/шт\n"
                          "⭐ Тяжелая снайперская MK2     800 монет/шт\n"
                          "🔫 Штурмовой дробовик          500 монет/шт\n"
                          "🔫 Тяжелый револьвер MK2       400 монет/шт```",
                    inline=False)

    embed.add_field(name="ℹ️ **Информация**",
                    value="• Максимальное количество: **1000 шт**\n"
                          "• При покупке укажите **никнейм и CID**\n"
                          "• Товары выдаются **в конце недели**",
                    inline=False)

    embed.set_footer(text="by Ilya Vetrov")
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="баланс", description="💰 Проверить баланс")
async def slash_balance(interaction: discord.Interaction, пользователь: discord.Member = None):
    if not is_allowed_channel(interaction.channel_id, 'balance'):
        await interaction.response.send_message(f"❌ Используйте канал <#{BALANCE_CHANNEL_ID}>", ephemeral=True)
        return

    if пользователь and not is_admin(interaction.user.id):
        await interaction.response.send_message("❌ Вы можете смотреть только свой баланс!", ephemeral=True)
        return

    member = пользователь or interaction.user
    balance = await db_get_balance(member.id)
    pending = await db_get_pending_count(member.id)

    embed = discord.Embed(title=f"💰 БАЛАНС: {member.name}", color=0xf1c40f, timestamp=datetime.now())
    embed.add_field(name="Монеты", value=f"```{balance}```", inline=True)
    embed.add_field(name="Ожидают выдачи", value=f"```{pending} шт.```", inline=True)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
    embed.set_footer(text="by Ilya Vetrov")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="инвентарь", description="📦 Полученные предметы")
async def slash_inventory(interaction: discord.Interaction, пользователь: discord.Member = None):
    if not is_allowed_channel(interaction.channel_id, 'shop'):
        await interaction.response.send_message(f"❌ Используйте канал <#{SHOP_CHANNEL_ID}>", ephemeral=True)
        return

    if пользователь and not is_admin(interaction.user.id):
        await interaction.response.send_message("❌ Вы можете смотреть только свой инвентарь!", ephemeral=True)
        return

    member = пользователь or interaction.user
    items = await db_get_user_inventory(member.id)
    balance = await db_get_balance(member.id)

    embed = discord.Embed(title=f"📦 ИНВЕНТАРЬ: {member.name}", color=0x9b59b6, timestamp=datetime.now())

    if not items:
        embed.description = "```Инвентарь пуст```"
    else:
        items_list = []
        for item in items:
            date = item['received_date'].strftime("%d.%m.%Y") if item['received_date'] else "?"
            items_list.append(f"• {item['item_name']} ({date})")
        embed.add_field(name="Полученные предметы", value="```\n" + "\n".join(items_list) + "```", inline=False)

    embed.add_field(name="Баланс", value=f"```{balance} монет```", inline=True)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
    embed.set_footer(text="by Ilya Vetrov")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="история", description="📜 История покупок")
async def slash_history(interaction: discord.Interaction, пользователь: discord.Member = None):
    if not is_allowed_channel(interaction.channel_id, 'shop'):
        await interaction.response.send_message(f"❌ Используйте канал <#{SHOP_CHANNEL_ID}>", ephemeral=True)
        return

    if пользователь and not is_admin(interaction.user.id):
        await interaction.response.send_message("❌ Вы можете смотреть только свою историю!", ephemeral=True)
        return

    member = пользователь or interaction.user
    purchases = await db_get_user_purchases(member.id)

    if not purchases:
        await interaction.response.send_message(f"📭 У {member.name} нет истории покупок")
        return

    embed = discord.Embed(title=f"📜 ИСТОРИЯ: {member.name}", color=0x3498db, timestamp=datetime.now())

    total = sum(p['total'] for p in purchases)
    total_items = sum(p['quantity'] for p in purchases)

    embed.add_field(name="Всего потрачено", value=f"```{total} монет```", inline=True)
    embed.add_field(name="Всего предметов", value=f"```{total_items} шт.```", inline=True)

    recent = purchases[:10]
    lines = []
    for p in recent:
        if p['status'] == 'cancelled':
            status = "❌"
        elif p['status'] == 'delivered':
            status = "✅"
        else:
            status = "⏳"
        date = p['purchase_date'].strftime("%d.%m.%Y") if p['purchase_date'] else "?"
        lines.append(f"{status} {p['item_name']} x{p['quantity']} - {date}")

    embed.add_field(name="Последние покупки", value="```\n" + "\n".join(lines) + "```", inline=False)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
    embed.set_footer(text="by Ilya Vetrov")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="каналы", description="📢 Информация о каналах")
async def slash_channels(interaction: discord.Interaction):
    embed = discord.Embed(title="📢 ДОСТУПНЫЕ КАНАЛЫ", color=0x3498db, timestamp=datetime.now())
    embed.add_field(name="💰 Баланс", value=f"<#{BALANCE_CHANNEL_ID}>", inline=False)
    embed.add_field(name="🛒 Магазин", value=f"<#{SHOP_CHANNEL_ID}>", inline=False)
    embed.set_footer(text="by Ilya Vetrov")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="команды", description="📋 Список команд")
async def slash_commands(interaction: discord.Interaction):
    embed = discord.Embed(title="📋 ДОСТУПНЫЕ КОМАНДЫ", color=0x3498db, timestamp=datetime.now())

    commands_text = ""
    for cmd, desc in [
        ("/магазин", "🛒 Открыть магазин"), ("/баланс", "💰 Проверить баланс"),
        ("/инвентарь", "📦 Полученные предметы"), ("/история", "📜 История покупок"),
        ("/каналы", "📢 Информация о каналах"), ("/команды", "📋 Этот список")
    ]:
        commands_text += f"**{cmd}** — {desc}\n"
    embed.add_field(name="📌 Основные команды", value=commands_text, inline=False)

    if is_admin(interaction.user.id):
        admin_text = ""
        for cmd, desc in [
            ("!датьмонет @user сумма", "💰 Выдать монеты"),
            ("!забрать_монеты @user сумма", "💸 Забрать монеты"),
            ("!невыдано", "📋 Список к выдаче"),
            ("!выдано @user", "✅ Выдать предметы"),
            ("!выдано", "✅ Выдать всё всем"),
            ("!сбросить_выдачу @user", "🔄 Сбросить ожидание выдачи"),
            ("!сбросить_все_выдачи", "🔄 Сбросить все ожидания"),
            ("!статистика", "📊 Статистика магазина"),
            ("!админы", "👑 Список админов"),
            ("!добавить_админа @user", "➕ Добавить админа"),
            ("!удалить_админа @user", "➖ Удалить админа"),
            ("!объявление текст", "📢 Отправить объявление"),
            ("!объявление_срочное текст", "🚨 Срочное объявление"),
            ("!объявление_embed цвет заголовок текст", "🎨 Красивое объявление")
        ]:
            admin_text += f"**{cmd}** — {desc}\n"
        embed.add_field(name="👑 Админские команды", value=admin_text, inline=False)

    embed.set_footer(text="by Ilya Vetrov")
    await interaction.response.send_message(embed=embed)

# ==================== ПРЕФИКСНЫЕ КОМАНДЫ ====================

@bot.command(name='датьмонет')
async def give_money_command(ctx, member: discord.Member, amount: int):
    if not is_admin(ctx.author.id):
        await ctx.send("❌ Только администраторы!")
        return
    if amount <= 0:
        await ctx.send("❌ Сумма должна быть положительной!")
        return

    old_balance = await db_get_balance(member.id)
    await db_add_balance(member.id, amount, member.name)
    new_balance = await db_get_balance(member.id)

    embed = discord.Embed(title="💰 МОНЕТЫ ВЫДАНЫ", color=0x2ecc71, timestamp=datetime.now())
    embed.add_field(name="Администратор", value=f"```{ctx.author.name}```", inline=True)
    embed.add_field(name="Получатель", value=member.mention, inline=True)
    embed.add_field(name="Сумма", value=f"```+{amount} монет```", inline=True)
    embed.add_field(name="Было", value=f"```{old_balance} монет```", inline=True)
    embed.add_field(name="Стало", value=f"```{new_balance} монет```", inline=True)
    embed.set_footer(text="by Ilya Vetrov")
    await ctx.send(embed=embed)

    try:
        dm_embed = discord.Embed(title="💰 ВАМ НАЧИСЛЕНЫ МОНЕТЫ!",
                                 description=f"Администратор **{ctx.author.name}** выдал вам монеты.",
                                 color=0xf1c40f, timestamp=datetime.now())
        dm_embed.add_field(name="Сумма", value=f"```+{amount} монет```", inline=True)
        dm_embed.add_field(name="Ваш баланс", value=f"```{new_balance} монет```", inline=True)
        dm_embed.add_field(name="💡 Как потратить?", value="Используйте `/магазин` чтобы купить товары!", inline=False)
        dm_embed.set_footer(text="by Ilya Vetrov")
        await member.send(embed=dm_embed)
    except:
        pass

@bot.command(name='забрать_монеты')
async def take_money_command(ctx, member: discord.Member, amount: int):
    if not is_admin(ctx.author.id):
        await ctx.send("❌ Только администраторы!")
        return
    if amount <= 0:
        await ctx.send("❌ Количество должно быть положительным!")
        return

    balance = await db_get_balance(member.id)
    if balance < amount:
        await ctx.send(f"❌ Недостаточно монет! У {member.mention} всего {balance} монет.")
        return

    await db_set_balance(member.id, balance - amount, member.name)
    new_balance = await db_get_balance(member.id)

    embed = discord.Embed(title="💸 МОНЕТЫ ЗАБРАНЫ", color=0xe74c3c, timestamp=datetime.now())
    embed.add_field(name="Администратор", value=f"```{ctx.author.name}```", inline=True)
    embed.add_field(name="У кого забрали", value=member.mention, inline=True)
    embed.add_field(name="Сумма", value=f"```-{amount} монет```", inline=True)
    embed.add_field(name="Было", value=f"```{balance} монет```", inline=True)
    embed.add_field(name="Стало", value=f"```{new_balance} монет```", inline=True)
    embed.set_footer(text="by Ilya Vetrov")
    await ctx.send(embed=embed)

    try:
        dm_embed = discord.Embed(title="💸 У ВАС ЗАБРАЛИ МОНЕТЫ",
                                 description=f"Администратор **{ctx.author.name}** забрал у вас монеты.",
                                 color=0xe74c3c, timestamp=datetime.now())
        dm_embed.add_field(name="Сумма", value=f"```-{amount} монет```", inline=True)
        dm_embed.add_field(name="Ваш баланс", value=f"```{new_balance} монет```", inline=True)
        dm_embed.set_footer(text="by Ilya Vetrov")
        await member.send(embed=dm_embed)
    except:
        pass

@bot.command(name='невыдано')
async def pending_command(ctx):
    if not is_admin(ctx.author.id):
        await ctx.send("❌ Только администраторы!")
        return

    pending = await db_get_all_pending()

    if not pending:
        await ctx.send("📦 Нет предметов к выдаче!")
        return

    embed = discord.Embed(title="📋 ПРЕДМЕТЫ К ВЫДАЧЕ",
                          description=f"Всего: **{len(pending)}** позиций",
                          color=0xe67e22, timestamp=datetime.now())

    for p in pending[:10]:
        embed.add_field(name=f"{p['username']} - {p['item_name']} x{p['quantity']}",
                        value=f"```💰 {p['total']} | Ник: {p['nickname']} | CID: {p['cid']} | {p['purchase_date'].strftime('%d.%m.%Y')}```",
                        inline=False)

    embed.set_footer(text="by Ilya Vetrov")
    await ctx.send(embed=embed)

@bot.command(name='выдано')
async def deliver_command(ctx, member: discord.Member = None):
    if not is_admin(ctx.author.id):
        await ctx.send("❌ Только администраторы!")
        return

    if member:
        pending = await db_get_all_pending()
        user_pending = [p for p in pending if p['uid'] == member.id]

        if not user_pending:
            await ctx.send(f"📦 У {member.mention} нет предметов к выдаче")
            return

        count = 0
        for p in user_pending:
            await db_deliver_purchase(p['purchase_id'], ctx.author.name, p['uid'],
                                      p['item_name'], p['quantity'], p['nickname'], p['cid'])
            count += p['quantity']

        embed = discord.Embed(title="✅ ПРЕДМЕТЫ ВЫДАНЫ",
                              description=f"Выдано **{count}** предметов {member.mention}",
                              color=0x2ecc71, timestamp=datetime.now())
        embed.set_footer(text="by Ilya Vetrov")
        await ctx.send(embed=embed)

        try:
            dm_embed = discord.Embed(title="✅ ТОВАРЫ ВЫДАНЫ!",
                                     description=f"Администратор **{ctx.author.name}** выдал вам товары.",
                                     color=0x2ecc71, timestamp=datetime.now())
            dm_embed.add_field(name="Получено предметов", value=f"```{count} шт.```", inline=True)
            dm_embed.add_field(name="📦 Где посмотреть?", value="Используйте `/инвентарь`", inline=False)
            dm_embed.set_footer(text="by Ilya Vetrov")
            await member.send(embed=dm_embed)
        except:
            pass
    else:
        pending = await db_get_all_pending()
        if not pending:
            await ctx.send("📦 Нет предметов к выдаче")
            return

        for p in pending:
            await db_deliver_purchase(p['purchase_id'], ctx.author.name, p['uid'],
                                      p['item_name'], p['quantity'], p['nickname'], p['cid'])

        total = sum(p['quantity'] for p in pending)
        embed = discord.Embed(title="✅ МАССОВАЯ ВЫДАЧА",
                              description=f"Выдано всего **{total}** предметов всем!",
                              color=0x2ecc71, timestamp=datetime.now())
        embed.set_footer(text="by Ilya Vetrov")
        await ctx.send(embed=embed)

@bot.command(name='статистика')
async def stats_command(ctx):
    if not is_admin(ctx.author.id):
        await ctx.send("❌ Только администраторы!")
        return

    stats = await db_get_stats()

    embed = discord.Embed(title="📊 СТАТИСТИКА МАГАЗИНА", color=0x3498db, timestamp=datetime.now())
    embed.add_field(name="👥 Пользователей", value=f"```{stats['users']}```", inline=True)
    embed.add_field(name="💰 Всего монет", value=f"```{stats['total_balance']}```", inline=True)
    embed.add_field(name="⏳ Ожидают выдачи", value=f"```{stats['pending']} шт.```", inline=True)
    embed.add_field(name="✅ Уже выдано", value=f"```{stats['delivered']} шт.```", inline=True)
    embed.add_field(name="❌ Отменено", value=f"```{stats['cancelled']} шт.```", inline=True)
    embed.add_field(name="💸 Всего потрачено", value=f"```{stats['spent']} монет```", inline=True)
    embed.set_footer(text="by Ilya Vetrov")
    await ctx.send(embed=embed)

@bot.command(name='сбросить_выдачу')
async def reset_pending_command(ctx, member: discord.Member, *, товар: str = None):
    if not is_admin(ctx.author.id):
        await ctx.send("❌ Только администраторы!")
        return

    result = await db_reset_pending_for_user(member.id, товар)

    if result['count'] == 0:
        await ctx.send(f"📦 У {member.mention} нет предметов в ожидании выдачи!")
        return

    embed = discord.Embed(title="🔄 СБРОС ОЖИДАНИЯ ВЫДАЧИ",
                          description=f"Сброшено **{result['count']}** позиций для {member.mention}",
                          color=0xf1c40f, timestamp=datetime.now())
    embed.add_field(name="Возвращено монет", value=f"```{result['refund']} монет```", inline=True)
    embed.set_footer(text="by Ilya Vetrov")
    await ctx.send(embed=embed)

    try:
        dm_embed = discord.Embed(title="🔄 СБРОС ОЖИДАНИЯ ВЫДАЧИ",
                                 description=f"Администратор **{ctx.author.name}** сбросил статус ожидания выдачи.",
                                 color=0xf1c40f, timestamp=datetime.now())
        dm_embed.add_field(name="Сброшено позиций", value=f"```{result['count']} шт.```", inline=True)
        dm_embed.add_field(name="Возвращено монет", value=f"```{result['refund']} монет```", inline=True)
        dm_embed.set_footer(text="by Ilya Vetrov")
        await member.send(embed=dm_embed)
    except:
        pass

@bot.command(name='сбросить_все_выдачи')
async def reset_all_pending_command(ctx):
    if not is_admin(ctx.author.id):
        await ctx.send("❌ Только администраторы!")
        return

    result = await db_reset_all_pending()

    if result['count'] == 0:
        await ctx.send("📦 Нет активных ожиданий выдачи!")
        return

    embed = discord.Embed(title="🔄 СБРОС ВСЕХ ОЖИДАНИЙ ВЫДАЧИ",
                          description=f"Сброшено **{result['count']}** позиций для всех пользователей",
                          color=0xf1c40f, timestamp=datetime.now())
    embed.add_field(name="Всего возвращено монет", value=f"```{result['refund']} монет```", inline=True)
    embed.set_footer(text="by Ilya Vetrov")
    await ctx.send(embed=embed)

@bot.command(name='синхронизировать')
async def sync_command(ctx):
    if not is_admin(ctx.author.id):
        await ctx.send("❌ Только администраторы!")
        return
    await bot.tree.sync()
    await ctx.send("✅ Слэш-команды синхронизированы!")

@bot.command(name='добавить_админа')
async def add_admin_command(ctx, user: discord.User):
    if not is_main_admin(ctx.author.id):
        await ctx.send("❌ Только главный администратор может добавлять админов!")
        return
    if user.bot:
        await ctx.send("❌ Боты не могут быть администраторами!")
        return
    if user.id in ADMIN_IDS:
        await ctx.send(f"❌ {user.mention} уже администратор!")
        return

    ADMIN_IDS.append(user.id)
    async with bot.db_pool.acquire() as conn:
        await conn.execute("INSERT INTO admins (user_id) VALUES ($1) ON CONFLICT DO NOTHING", user.id)

    embed = discord.Embed(title="👑 НОВЫЙ АДМИНИСТРАТОР",
                          description=f"Главный админ **{ctx.author.name}** добавил нового администратора!",
                          color=0xf1c40f, timestamp=datetime.now())
    embed.add_field(name="Новый админ", value=user.mention, inline=True)
    embed.add_field(name="ID", value=f"`{user.id}`", inline=True)
    embed.set_footer(text="by Ilya Vetrov")
    await ctx.send(embed=embed)

    try:
        dm_embed = discord.Embed(title="👑 ВАС НАЗНАЧИЛИ АДМИНИСТРОМ!",
                                 description=f"Главный администратор **{ctx.author.name}** добавил вас в администраторы.",
                                 color=0xf1c40f)
        dm_embed.add_field(name="Ваши новые возможности",
                           value="• Выдавать монеты\n• Забирать монеты\n• Смотреть невыданное\n• Отмечать как выданное\n• Смотреть статистику", inline=False)
        dm_embed.set_footer(text="by Ilya Vetrov")
        await user.send(embed=dm_embed)
    except:
        pass

@bot.command(name='удалить_админа')
async def remove_admin_command(ctx, user: discord.User):
    if not is_main_admin(ctx.author.id):
        await ctx.send("❌ Только главный администратор может удалять админов!")
        return
    if user.id == MAIN_ADMIN_ID:
        await ctx.send("❌ Нельзя удалить главного администратора!")
        return
    if user.id not in ADMIN_IDS:
        await ctx.send(f"❌ {user.mention} не является администратором!")
        return

    ADMIN_IDS.remove(user.id)
    async with bot.db_pool.acquire() as conn:
        await conn.execute("DELETE FROM admins WHERE user_id = $1", user.id)

    embed = discord.Embed(title="👑 АДМИНИСТРАТОР УДАЛЕН",
                          description=f"Главный админ **{ctx.author.name}** удалил администратора",
                          color=0xe74c3c, timestamp=datetime.now())
    embed.add_field(name="Бывший админ", value=user.mention, inline=True)
    embed.add_field(name="ID", value=f"`{user.id}`", inline=True)
    embed.set_footer(text="by Ilya Vetrov")
    await ctx.send(embed=embed)

@bot.command(name='админы')
async def list_admins_command(ctx):
    admin_list = []
    for admin_id in ADMIN_IDS:
        try:
            user = await bot.fetch_user(admin_id)
            admin_list.append(f"👑 **{user.name}** (Главный)" if admin_id == MAIN_ADMIN_ID else f"• {user.name}")
        except:
            admin_list.append(f"• Админ ID: {admin_id}")

    embed = discord.Embed(title="👑 СПИСОК АДМИНИСТРАТОРОВ",
                          description="\n".join(admin_list),
                          color=0xf1c40f, timestamp=datetime.now())
    embed.set_footer(text=f"Всего: {len(ADMIN_IDS)} | by Ilya Vetrov")
    await ctx.send(embed=embed)

@bot.command(name='объявление')
async def announcement_command(ctx, *, текст: str):
    if not is_admin(ctx.author.id):
        await ctx.send("❌ Только администраторы!")
        return

    channel = bot.get_channel(ANNOUNCE_CHANNEL_ID)
    if not channel:
        await ctx.send(f"❌ Канал не найден!")
        return

    embed = discord.Embed(title="📢 ОБЪЯВЛЕНИЕ", description=текст, color=0x9b59b6, timestamp=datetime.now())
    embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
    embed.set_footer(text="by Ilya Vetrov")
    await channel.send(embed=embed)
    await ctx.send("✅ Отправлено!")

@bot.command(name='объявление_срочное')
async def announcement_urgent_command(ctx, *, текст: str):
    if not is_admin(ctx.author.id):
        await ctx.send("❌ Только администраторы!")
        return

    channel = bot.get_channel(ANNOUNCE_CHANNEL_ID)
    if not channel:
        await ctx.send(f"❌ Канал не найден!")
        return

    embed = discord.Embed(title="🚨 СРОЧНОЕ ОБЪЯВЛЕНИЕ", description=текст, color=0xe74c3c, timestamp=datetime.now())
    embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
    embed.set_footer(text="by Ilya Vetrov")
    await channel.send("@everyone", embed=embed)
    await ctx.send("✅ Отправлено!")

@bot.command(name='объявление_embed')
async def announcement_embed_command(ctx, цвет: str, заголовок: str, *, текст: str):
    if not is_admin(ctx.author.id):
        await ctx.send("❌ Только администраторы!")
        return

    color_map = {"красный": 0xe74c3c, "зеленый": 0x2ecc71, "синий": 0x3498db,
                 "желтый": 0xf1c40f, "фиолетовый": 0x9b59b6, "оранжевый": 0xe67e22}
    color = color_map.get(цвет.lower(), 0x3498db)

    channel = bot.get_channel(ANNOUNCE_CHANNEL_ID)
    if not channel:
        await ctx.send(f"❌ Канал не найден!")
        return

    embed = discord.Embed(title=заголовок, description=текст, color=color, timestamp=datetime.now())
    embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
    embed.set_footer(text="by Ilya Vetrov")
    await channel.send(embed=embed)
    await ctx.send("✅ Отправлено!")

# ==================== ЗАПУСК ====================

@bot.event
async def on_ready():
    print(f'✅ Бот {bot.user} запущен! Серверов: {len(bot.guilds)} | Админов: {len(ADMIN_IDS)} | БД: PostgreSQL')
    await bot.change_presence(activity=discord.Game(name="/команды | /магазин"))

token = os.getenv('TOKEN')
if not token:
    print("❌ Токен не найден!")
    exit(1)

print("🔄 Запуск бота...")
bot.run(token)
