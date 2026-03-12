import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Select, View, Button, Modal, TextInput
import json
import os
from datetime import datetime

# Настройки бота
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# ID администраторов - ЗДЕСЬ ВАШ ID
ADMIN_IDS = [
    927642459998138418,  # Ваш ID
]

# ID каналов - ЗДЕСЬ ВАШИ КАНАЛЫ
BALANCE_CHANNEL_ID = 1481753586835783861   # Канал для !баланс
SHOP_CHANNEL_ID = 1481753891124019302      # Канал для магазина
ADMIN_CHANNEL_ID = 1481754087614841033     # Админский канал

# Файл для хранения данных
DATA_FILE = 'user_data.json'

class ShopBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)
    
    async def setup_hook(self):
        await self.tree.sync()
        print(f"✅ Слэш-команды синхронизированы")

bot = ShopBot()

# ==================== ФУНКЦИИ ====================

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def is_admin(user_id):
    return user_id in ADMIN_IDS

def is_allowed_channel(channel_id, command_type):
    if channel_id == ADMIN_CHANNEL_ID:
        return True
    if command_type == 'balance':
        return channel_id == BALANCE_CHANNEL_ID
    return channel_id == SHOP_CHANNEL_ID

# ==================== МОДАЛЬНОЕ ОКНО ====================

class PurchaseModal(Modal, title="Покупка товара"):
    def __init__(self, item_name, item_price):
        super().__init__()
        self.item_name = item_name
        self.item_price = item_price
        
        self.quantity = TextInput(
            label="Количество",
            placeholder="Введите количество (1-99)",
            required=True,
            max_length=2
        )
        self.add_item(self.quantity)
        
        self.nickname = TextInput(
            label="Игровой Никнейм",
            placeholder="Введите ваш никнейм",
            required=True,
            max_length=50
        )
        self.add_item(self.nickname)
        
        self.cid = TextInput(
            label="CID",
            placeholder="Введите ваш CID",
            required=True,
            max_length=20
        )
        self.add_item(self.cid)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            quantity = int(self.quantity.value)
            if quantity < 1 or quantity > 99:
                await interaction.response.send_message("❌ Количество от 1 до 99!", ephemeral=True)
                return
        except:
            await interaction.response.send_message("❌ Введите число!", ephemeral=True)
            return
        
        data = load_data()
        user_id = str(interaction.user.id)
        total_price = self.item_price * quantity
        
        if user_id not in data:
            data[user_id] = {"balance": 0, "inventory": [], "pending_items": [], "all_purchases": [], "name": interaction.user.name}
        
        if data[user_id]["balance"] < total_price:
            await interaction.response.send_message(f"❌ Недостаточно средств! Нужно: {total_price}", ephemeral=True)
            return
        
        data[user_id]["balance"] -= total_price
        
        purchase = {
            "name": self.item_name,
            "price": self.item_price,
            "quantity": quantity,
            "total": total_price,
            "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "nickname": self.nickname.value,
            "cid": self.cid.value,
            "delivered": False
        }
        
        data[user_id]["pending_items"].append(purchase)
        data[user_id]["all_purchases"].append(purchase)
        data[user_id]["name"] = interaction.user.name
        save_data(data)
        
        embed = discord.Embed(title="✅ Покупка совершена!", color=discord.Color.green())
        embed.add_field(name="Товар", value=self.item_name)
        embed.add_field(name="Количество", value=f"{quantity} шт.")
        embed.add_field(name="Цена", value=f"{total_price} монет")
        embed.add_field(name="Никнейм", value=self.nickname.value)
        embed.add_field(name="CID", value=self.cid.value)
        embed.set_footer(text="by Ilya Vetrov")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        admin_channel = bot.get_channel(ADMIN_CHANNEL_ID)
        if admin_channel:
            admin_embed = discord.Embed(title="🛒 Новая покупка!", color=discord.Color.blue())
            admin_embed.add_field(name="Покупатель", value=interaction.user.name)
            admin_embed.add_field(name="Товар", value=self.item_name)
            admin_embed.add_field(name="Количество", value=f"{quantity} шт.")
            admin_embed.add_field(name="Цена", value=f"{total_price} монет")
            admin_embed.add_field(name="Никнейм", value=self.nickname.value)
            admin_embed.add_field(name="CID", value=self.cid.value)
            await admin_channel.send(embed=admin_embed)

# ==================== СЛЭШ-КОМАНДЫ ====================

@bot.tree.command(name="магазин", description="🛒 Открыть магазин")
async def shop(interaction: discord.Interaction):
    if not is_allowed_channel(interaction.channel_id, 'shop'):
        await interaction.response.send_message(f"❌ Используйте канал <#{SHOP_CHANNEL_ID}>", ephemeral=True)
        return
    
    items = [
        # Глава 1
        {"name": "💊 Реанимнабор", "price": 150},
        {"name": "💉 Набор для самореанимации", "price": 200},
        {"name": "🛡️ Ремкоплект для брони", "price": 100},
        {"name": "🔫 MG Ammo", "price": 50},
        {"name": "🎯 Sniper Ammo", "price": 75},
        # Глава 2
        {"name": "🔇 Глушитель", "price": 300},
        {"name": "📦 Увеличенный магазин (винтовка)", "price": 250},
        {"name": "📦 Увеличенный магазин (пистолет)", "price": 200},
        {"name": "📦 Увеличенный магазин (ПП)", "price": 225},
        {"name": "📦 Увеличенный магазин (снайперская)", "price": 275},
        {"name": "🥁 Барабанный магазин (винтовка)", "price": 400},
        # Глава 3
        {"name": "🔫 Тяжелый пулемет", "price": 800},
        {"name": "⚡ Тяжелый пулемет MK2", "price": 1200},
        {"name": "🎯 Тяжелая снайперская", "price": 1000},
        {"name": "⭐ Тяжелая снайперская MK2", "price": 1500},
        {"name": "🔫 Штурмовой дробовик", "price": 600},
        {"name": "🔫 Тяжелый револьвер MK2", "price": 700},
    ]
    
    options = [discord.SelectOption(label=item["name"], value=str(i)) for i, item in enumerate(items)]
    
    class ShopSelect(Select):
        def __init__(self):
            super().__init__(placeholder="Выберите товар...", options=options)
        
        async def callback(self, interaction: discord.Interaction):
            index = int(self.values[0])
            item = items[index]
            await interaction.response.send_modal(PurchaseModal(item["name"], item["price"]))
    
    view = View()
    view.add_item(ShopSelect())
    
    embed = discord.Embed(title="🛒 МАГАЗИН", color=discord.Color.gold())
    embed.add_field(name="ℹ Информация", value="Выберите товар, укажите количество, ник и CID", inline=False)
    embed.set_footer(text="by Ilya Vetrov")
    
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="баланс", description="💰 Проверить баланс")
async def balance(interaction: discord.Interaction, пользователь: discord.Member = None):
    if not is_allowed_channel(interaction.channel_id, 'balance'):
        await interaction.response.send_message(f"❌ Используйте канал <#{BALANCE_CHANNEL_ID}>", ephemeral=True)
        return
    
    member = пользователь or interaction.user
    data = load_data()
    user_id = str(member.id)
    balance = data.get(user_id, {}).get("balance", 0)
    pending = len([x for x in data.get(user_id, {}).get("pending_items", []) if not x.get("delivered")])
    
    embed = discord.Embed(title=f"💰 Баланс: {member.name}", color=discord.Color.blue())
    embed.add_field(name="Монеты", value=f"{balance} монет")
    embed.add_field(name="Ожидают выдачи", value=f"{pending} шт.")
    embed.set_footer(text="by Ilya Vetrov")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="инвентарь", description="📦 Полученные предметы")
async def inventory(interaction: discord.Interaction, пользователь: discord.Member = None):
    if not is_allowed_channel(interaction.channel_id, 'shop'):
        await interaction.response.send_message(f"❌ Используйте канал <#{SHOP_CHANNEL_ID}>", ephemeral=True)
        return
    
    member = пользователь or interaction.user
    data = load_data()
    user_id = str(member.id)
    
    if user_id not in data or not data[user_id].get("inventory"):
        await interaction.response.send_message(f"📦 У {member.name} пустой инвентарь")
        return
    
    items = []
    for item in data[user_id]["inventory"][-20:]:
        items.append(f"• {item['name']} ({item.get('received_date', '?')})")
    
    embed = discord.Embed(title=f"📦 Инвентарь: {member.name}", description="\n".join(items), color=discord.Color.purple())
    embed.set_footer(text="by Ilya Vetrov")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="история", description="📜 История покупок")
async def history(interaction: discord.Interaction, пользователь: discord.Member = None):
    if not is_allowed_channel(interaction.channel_id, 'shop'):
        await interaction.response.send_message(f"❌ Используйте канал <#{SHOP_CHANNEL_ID}>", ephemeral=True)
        return
    
    member = пользователь or interaction.user
    if member != interaction.user and not is_admin(interaction.user.id):
        await interaction.response.send_message("❌ Можно смотреть только свою историю!", ephemeral=True)
        return
    
    data = load_data()
    user_id = str(member.id)
    
    if user_id not in data or not data[user_id].get("all_purchases"):
        await interaction.response.send_message(f"📭 У {member.name} нет истории покупок")
        return
    
    purchases = []
    for p in data[user_id]["all_purchases"][-10:]:
        status = "✅" if p.get("delivered") else "⏳"
        purchases.append(f"{status} {p['name']} x{p.get('quantity',1)} - {p['date']}")
    
    embed = discord.Embed(title=f"📜 История: {member.name}", description="\n".join(purchases), color=discord.Color.purple())
    embed.set_footer(text="by Ilya Vetrov")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="каналы", description="📢 Информация о каналах")
async def channels(interaction: discord.Interaction):
    embed = discord.Embed(title="📢 Каналы бота", color=discord.Color.blue())
    embed.add_field(name="💰 Баланс", value=f"<#{BALANCE_CHANNEL_ID}>")
    embed.add_field(name="🛒 Магазин", value=f"<#{SHOP_CHANNEL_ID}>")
    embed.add_field(name="👑 Админский", value=f"<#{ADMIN_CHANNEL_ID}>")
    embed.set_footer(text="by Ilya Vetrov")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="команды", description="📋 Список команд")
async def commands_list(interaction: discord.Interaction):
    embed = discord.Embed(title="📋 Команды", color=discord.Color.blue())
    embed.add_field(name="Основные", 
                   value="/магазин\n/баланс\n/инвентарь\n/история\n/каналы\n/команды", 
                   inline=True)
    
    if is_admin(interaction.user.id):
        embed.add_field(name="Админские", 
                       value="!датьмонет\n!невыдано\n!выдано\n!статистика\n!админы", 
                       inline=True)
    
    embed.set_footer(text="by Ilya Vetrov")
    await interaction.response.send_message(embed=embed)

# ==================== ПРЕФИКСНЫЕ КОМАНДЫ ДЛЯ АДМИНОВ ====================

@bot.command(name='датьмонет')
async def give_money(ctx, member: discord.Member, amount: int):
    if not is_admin(ctx.author.id):
        await ctx.send("❌ Нет прав!")
        return
    
    data = load_data()
    user_id = str(member.id)
    
    if user_id not in data:
        data[user_id] = {"balance": 0, "inventory": [], "pending_items": [], "all_purchases": [], "name": member.name}
    
    data[user_id]["balance"] += amount
    save_data(data)
    await ctx.send(f"✅ {member.mention} получил {amount} монет!")

@bot.command(name='невыдано')
async def pending(ctx):
    if not is_admin(ctx.author.id):
        await ctx.send("❌ Нет прав!")
        return
    
    data = load_data()
    pending_list = []
    
    for uid, udata in data.items():
        for item in udata.get("pending_items", []):
            if not item.get("delivered"):
                try:
                    user = await bot.fetch_user(int(uid))
                    name = user.name
                except:
                    name = udata.get("name", "?")
                pending_list.append(f"{name}: {item['name']} x{item.get('quantity',1)} ({item.get('nickname','?')})")
    
    if not pending_list:
        await ctx.send("📦 Нет предметов к выдаче")
        return
    
    await ctx.send("📋 **К выдаче:**\n" + "\n".join(pending_list[:20]))

@bot.command(name='выдано')
async def delivered(ctx, member: discord.Member = None):
    if not is_admin(ctx.author.id):
        await ctx.send("❌ Нет прав!")
        return
    
    data = load_data()
    
    if member:
        user_id = str(member.id)
        count = 0
        for item in data[user_id]["pending_items"]:
            if not item["delivered"]:
                item["delivered"] = True
                if "inventory" not in data[user_id]:
                    data[user_id]["inventory"] = []
                data[user_id]["inventory"].append({
                    "name": item["name"],
                    "received_date": datetime.now().strftime("%d.%m.%Y %H:%M"),
                    "received_by": ctx.author.name
                })
                count += 1
        if count:
            save_data(data)
            await ctx.send(f"✅ Выдано {count} предметов {member.mention}")
        else:
            await ctx.send(f"📦 У {member.mention} нет предметов")
    else:
        total = 0
        for uid, udata in data.items():
            for item in udata["pending_items"]:
                if not item["delivered"]:
                    item["delivered"] = True
                    if "inventory" not in udata:
                        udata["inventory"] = []
                    udata["inventory"].append({
                        "name": item["name"],
                        "received_date": datetime.now().strftime("%d.%m.%Y %H:%M"),
                        "received_by": ctx.author.name
                    })
                    total += 1
        if total:
            save_data(data)
            await ctx.send(f"✅ Выдано всего {total} предметов")
        else:
            await ctx.send("📦 Нет предметов к выдаче")

@bot.command(name='статистика')
async def stats(ctx):
    if not is_admin(ctx.author.id):
        await ctx.send("❌ Нет прав!")
        return
    
    data = load_data()
    users = len(data)
    pending = 0
    delivered = 0
    spent = 0
    
    for udata in data.values():
        pending += sum(item.get("quantity", 1) for item in udata.get("pending_items", []) if not item.get("delivered"))
        delivered += len(udata.get("inventory", []))
        spent += sum(p.get("total", 0) for p in udata.get("all_purchases", []))
    
    embed = discord.Embed(title="📊 Статистика", color=discord.Color.blue())
    embed.add_field(name="Пользователей", value=users)
    embed.add_field(name="Ожидают выдачи", value=pending)
    embed.add_field(name="Выдано", value=delivered)
    embed.add_field(name="Потрачено", value=f"{spent} монет")
    embed.set_footer(text="by Ilya Vetrov")
    
    await ctx.send(embed=embed)

@bot.command(name='админы')
async def admins(ctx):
    admin_list = []
    for admin_id in ADMIN_IDS:
        try:
            user = await bot.fetch_user(admin_id)
            admin_list.append(f"• {user.name}")
        except:
            admin_list.append(f"• Админ (ID: {admin_id})")
    
    embed = discord.Embed(title="👑 Администраторы", description="\n".join(admin_list), color=discord.Color.gold())
    embed.set_footer(text="by Ilya Vetrov")
    
    await ctx.send(embed=embed)

@bot.command(name='синхронизировать')
async def sync(ctx):
    if not is_admin(ctx.author.id):
        await ctx.send("❌ Нет прав!")
        return
    
    await bot.tree.sync()
    await ctx.send("✅ Команды синхронизированы!")

# ==================== СОБЫТИЯ ====================

@bot.event
async def on_ready():
    print(f'✅ Бот {bot.user} запущен!')
    print(f'📋 На серверах: {len(bot.guilds)}')
    await bot.change_presence(activity=discord.Game(name="/команды | /магазин"))

# ==================== ЗАПУСК ====================

token = os.getenv('TOKEN')
if not token:
    print("❌ ОШИБКА: Токен не найден!")
    print("📝 Добавьте переменную TOKEN в Environment Variables")
    exit(1)

print("🔄 Запуск бота...")
bot.run(token)
