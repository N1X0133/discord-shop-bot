import discord
from discord.ext import commands
from discord.ui import Select, View, Button, Modal, TextInput
import json
import os
from datetime import datetime

# Настройки бота
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Файл для хранения данных
DATA_FILE = 'user_data.json'

# ID администраторов
ADMIN_IDS = [
    927642459998138418,  # Главный админ
    500965898476322817,  # Админ 1
    271067502102970371,  # Админ 2
]

# ID каналов
BALANCE_CHANNEL_ID = 1481753586835783861   # Только !баланс
SHOP_CHANNEL_ID = 1481753891124019302      # Магазин и всё остальное
ADMIN_CHANNEL_ID = 1481754087614841033     # Админский канал

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
    # Админский канал - всё можно
    if channel_id == ADMIN_CHANNEL_ID:
        return True
    
    # Для команды баланс - только канал баланса
    if command_type == 'balance':
        return channel_id == BALANCE_CHANNEL_ID
    
    # Для всех остальных команд - магазинный канал
    return channel_id == SHOP_CHANNEL_ID

# Модальное окно для ввода ника и CID
class NicknameModal(Modal, title="Введите игровые данные"):
    def __init__(self, item_name, item_price, shop_view):
        super().__init__()
        self.item_name = item_name
        self.item_price = item_price
        self.shop_view = shop_view
        
        self.nickname = TextInput(
            label="Игровой Никнейм",
            placeholder="Введите ваш никнейм...",
            required=True,
            max_length=50
        )
        self.add_item(self.nickname)
        
        self.cid = TextInput(
            label="CID",
            placeholder="Введите ваш CID...",
            required=True,
            max_length=20
        )
        self.add_item(self.cid)
    
    async def on_submit(self, interaction: discord.Interaction):
        await self.shop_view.process_purchase(
            interaction, 
            self.item_name, 
            self.item_price,
            self.nickname.value,
            self.cid.value
        )

# Класс магазина
class ShopView(View):
    def __init__(self):
        super().__init__(timeout=None)
        
        self.shop_items = [
            # Глава 1: Расходники
            {"name": "💊 Реанимнабор", "price": 150},
            {"name": "💉 Набор для самореанимации", "price": 200},
            {"name": "🛡️ Ремкоплект для брони", "price": 100},
            {"name": "🔫 MG Ammo", "price": 50},
            {"name": "🎯 Sniper Ammo", "price": 75},
            
            # Глава 2: Модули
            {"name": "🔇 Глушитель", "price": 300},
            {"name": "📦 Увеличенный магазин (винтовка)", "price": 250},
            {"name": "📦 Увеличенный магазин (пистолет)", "price": 200},
            {"name": "📦 Увеличенный магазин (ПП)", "price": 225},
            {"name": "📦 Увеличенный магазин (снайперская винтовка)", "price": 275},
            {"name": "🥁 Барабанный магазин (винтовка)", "price": 400},
            
            # Глава 3: Спец. вооружение
            {"name": "🔫 Тяжелый пулемет", "price": 800},
            {"name": "⚡ Тяжелый пулемет MK2", "price": 1200},
            {"name": "🎯 Тяжелая снайперская", "price": 1000},
            {"name": "⭐ Тяжелая снайперская MK2", "price": 1500},
            {"name": "🔫 Штурмовой дробовик", "price": 600},
            {"name": "🔫 Тяжелый револьвер MK2", "price": 700},
        ]
        
        options = [discord.SelectOption(label=item["name"], value=item["name"]) for item in self.shop_items]
        
        self.select = Select(placeholder="Выберите товар...", options=options)
        self.select.callback = self.select_callback
        self.add_item(self.select)
        
        self.buy = Button(label="Купить", style=discord.ButtonStyle.green, emoji="💰")
        self.buy.callback = self.buy_callback
        self.add_item(self.buy)
        
        self.balance_btn = Button(label="Мой баланс", style=discord.ButtonStyle.blurple, emoji="💳")
        self.balance_btn.callback = self.balance_callback
        self.add_item(self.balance_btn)
        
        self.selected_item = None
    
    async def select_callback(self, interaction: discord.Interaction):
        self.selected_item = self.select.values[0]
        await interaction.response.send_message(f"✓ Вы выбрали: {self.selected_item}", ephemeral=True)
    
    async def buy_callback(self, interaction: discord.Interaction):
        if not self.selected_item:
            await interaction.response.send_message("❌ Сначала выберите товар!", ephemeral=True)
            return
        
        if not is_allowed_channel(interaction.channel_id, 'shop'):
            await interaction.response.send_message(f"❌ Покупки только в канале <#{SHOP_CHANNEL_ID}>", ephemeral=True)
            return
        
        item = next((x for x in self.shop_items if x["name"] == self.selected_item), None)
        if not item:
            return
        
        data = load_data()
        user_id = str(interaction.user.id)
        balance = data.get(user_id, {}).get("balance", 0)
        
        if balance < item["price"]:
            await interaction.response.send_message(
                f"❌ Недостаточно средств!\nНужно: {item['price']} монет\nУ вас: {balance} монет",
                ephemeral=True
            )
            return
        
        modal = NicknameModal(item["name"], item["price"], self)
        await interaction.response.send_modal(modal)
    
    async def process_purchase(self, interaction: discord.Interaction, name, price, nickname, cid):
        data = load_data()
        user_id = str(interaction.user.id)
        
        if user_id not in data:
            data[user_id] = {
                "balance": 0, 
                "inventory": [], 
                "pending_items": [], 
                "all_purchases": [], 
                "name": interaction.user.name
            }
        
        if data[user_id]["balance"] < price:
            await interaction.response.send_message("❌ Ошибка: недостаточно средств!", ephemeral=True)
            return
        
        # Списываем деньги
        data[user_id]["balance"] -= price
        
        purchase = {
            "name": name,
            "price": price,
            "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "nickname": nickname,
            "cid": cid,
            "delivered": False
        }
        
        data[user_id]["pending_items"].append(purchase)
        data[user_id]["all_purchases"].append(purchase.copy())
        data[user_id]["name"] = interaction.user.name
        save_data(data)
        
        # Ответ пользователю
        embed = discord.Embed(title="✅ ПОКУПКА СОВЕРШЕНА!", color=discord.Color.green())
        embed.add_field(name="Товар", value=name, inline=True)
        embed.add_field(name="Цена", value=f"{price} монет", inline=True)
        embed.add_field(name="Остаток", value=f"{data[user_id]['balance']} монет", inline=True)
        embed.add_field(name="Никнейм", value=nickname, inline=True)
        embed.add_field(name="CID", value=cid, inline=True)
        embed.add_field(name="Статус", value="⏳ Ожидает выдачи", inline=True)
        embed.set_footer(text="by Ilya Vetrov")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Уведомление в админский канал
        admin_channel = bot.get_channel(ADMIN_CHANNEL_ID)
        if admin_channel:
            admin_embed = discord.Embed(title="🛒 НОВАЯ ПОКУПКА!", color=discord.Color.blue())
            admin_embed.add_field(name="Покупатель", value=f"{interaction.user.name} ({interaction.user.id})", inline=False)
            admin_embed.add_field(name="Товар", value=name, inline=True)
            admin_embed.add_field(name="Цена", value=f"{price} монет", inline=True)
            admin_embed.add_field(name="Никнейм", value=nickname, inline=True)
            admin_embed.add_field(name="CID", value=cid, inline=True)
            admin_embed.add_field(name="Канал", value=f"#{interaction.channel.name}", inline=True)
            admin_embed.add_field(name="Время", value=datetime.now().strftime("%H:%M %d.%m.%Y"), inline=False)
            admin_embed.set_footer(text="by Ilya Vetrov")
            
            await admin_channel.send(embed=admin_embed)
    
    async def balance_callback(self, interaction: discord.Interaction):
        if not is_allowed_channel(interaction.channel_id, 'balance'):
            await interaction.response.send_message(f"❌ Баланс только в канале <#{BALANCE_CHANNEL_ID}>", ephemeral=True)
            return
        
        data = load_data()
        user_id = str(interaction.user.id)
        balance = data.get(user_id, {}).get("balance", 0)
        pending = len([x for x in data.get(user_id, {}).get("pending_items", []) if not x.get("delivered")])
        
        embed = discord.Embed(title="💰 ВАШ БАЛАНС", color=discord.Color.blue())
        embed.add_field(name="Монеты", value=f"{balance} монет", inline=True)
        embed.add_field(name="Ожидают выдачи", value=f"{pending} шт.", inline=True)
        embed.set_footer(text="by Ilya Vetrov")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ==================== КОМАНДЫ ====================

@bot.command(name='магазин')
async def shop_command(ctx):
    """Открыть магазин"""
    if not is_allowed_channel(ctx.channel.id, 'shop'):
        await ctx.send(f"❌ Магазин доступен только в канале <#{SHOP_CHANNEL_ID}>")
        return
    
    view = ShopView()
    embed = discord.Embed(
        title="🛒 МАГАЗИН",
        description="**Глава 1: Расходники**\n"
                   "💊 Реанимнабор — 150 монет\n"
                   "💉 Набор для самореанимации — 200 монет\n"
                   "🛡️ Ремкоплект для брони — 100 монет\n"
                   "🔫 MG Ammo — 50 монет\n"
                   "🎯 Sniper Ammo — 75 монет\n\n"
                   
                   "**Глава 2: Модули**\n"
                   "🔇 Глушитель — 300 монет\n"
                   "📦 Увеличенный магазин (винтовка) — 250 монет\n"
                   "📦 Увеличенный магазин (пистолет) — 200 монет\n"
                   "📦 Увеличенный магазин (ПП) — 225 монет\n"
                   "📦 Увеличенный магазин (снайперская винтовка) — 275 монет\n"
                   "🥁 Барабанный магазин (винтовка) — 400 монет\n\n"
                   
                   "**Глава 3: Спец. вооружение**\n"
                   "🔫 Тяжелый пулемет — 800 монет\n"
                   "⚡ Тяжелый пулемет MK2 — 1200 монет\n"
                   "🎯 Тяжелая снайперская — 1000 монет\n"
                   "⭐ Тяжелая снайперская MK2 — 1500 монет\n"
                   "🔫 Штурмовой дробовик — 600 монет\n"
                   "🔫 Тяжелый револьвер MK2 — 700 монет",
        color=discord.Color.gold()
    )
    embed.add_field(name="ℹ Информация", value="При покупке нужно указать Игровой Никнейм и CID\nТовары выдаются в конце недели", inline=False)
    embed.set_footer(text="by Ilya Vetrov")
    
    await ctx.send(embed=embed, view=view)

@bot.command(name='баланс')
async def balance_command(ctx, member: discord.Member = None):
    """Проверить баланс"""
    if not is_allowed_channel(ctx.channel.id, 'balance'):
        await ctx.send(f"❌ Команда !баланс доступна только в канале <#{BALANCE_CHANNEL_ID}>")
        return
    
    member = member or ctx.author
    data = load_data()
    user_id = str(member.id)
    
    balance = data.get(user_id, {}).get("balance", 0)
    pending = len([x for x in data.get(user_id, {}).get("pending_items", []) if not x.get("delivered")])
    
    embed = discord.Embed(title=f"💰 БАЛАНС: {member.name}", color=discord.Color.blue())
    embed.add_field(name="Монеты", value=f"{balance} монет", inline=True)
    embed.add_field(name="Ожидают выдачи", value=f"{pending} шт.", inline=True)
    embed.set_footer(text="by Ilya Vetrov")
    
    await ctx.send(embed=embed)

@bot.command(name='инвентарь')
async def inventory_command(ctx, member: discord.Member = None):
    """Посмотреть полученные предметы"""
    if not is_allowed_channel(ctx.channel.id, 'shop'):
        await ctx.send(f"❌ Команда !инвентарь доступна в канале <#{SHOP_CHANNEL_ID}>")
        return
    
    member = member or ctx.author
    data = load_data()
    user_id = str(member.id)
    
    if user_id not in data or "inventory" not in data[user_id] or not data[user_id]["inventory"]:
        embed = discord.Embed(title=f"📦 ИНВЕНТАРЬ: {member.name}", description="Инвентарь пуст!", color=discord.Color.light_grey())
        embed.add_field(name="Баланс", value=f"{data.get(user_id, {}).get('balance', 0)} монет", inline=True)
        embed.set_footer(text="by Ilya Vetrov")
        await ctx.send(embed=embed)
        return
    
    embed = discord.Embed(title=f"📦 ИНВЕНТАРЬ: {member.name}", color=discord.Color.purple())
    
    items = []
    for item in data[user_id]["inventory"][-15:]:
        items.append(f"• {item['name']} (выдано: {item.get('received_date', '?')})")
    
    embed.add_field(name="Полученные предметы", value="\n".join(items) or "Нет предметов", inline=False)
    embed.add_field(name="Баланс", value=f"{data[user_id]['balance']} монет", inline=True)
    
    pending = len([x for x in data[user_id].get("pending_items", []) if not x.get("delivered")])
    if pending > 0:
        embed.add_field(name="Ожидают выдачи", value=f"{pending} шт.", inline=True)
    
    embed.set_footer(text="by Ilya Vetrov")
    await ctx.send(embed=embed)

@bot.command(name='история')
async def history_command(ctx, member: discord.Member = None):
    """История покупок"""
    if not is_allowed_channel(ctx.channel.id, 'shop'):
        await ctx.send(f"❌ Команда !история доступна в канале <#{SHOP_CHANNEL_ID}>")
        return
    
    member = member or ctx.author
    
    if member != ctx.author and not is_admin(ctx.author.id):
        await ctx.send("❌ Вы можете смотреть только свою историю!")
        return
    
    data = load_data()
    user_id = str(member.id)
    
    if user_id not in data or "all_purchases" not in data[user_id] or not data[user_id]["all_purchases"]:
        await ctx.send(f"📭 У пользователя {member.mention} нет истории покупок")
        return
    
    embed = discord.Embed(title=f"📜 ИСТОРИЯ ПОКУПОК: {member.name}", color=discord.Color.purple())
    
    total = sum(p.get("price", 0) for p in data[user_id]["all_purchases"])
    embed.add_field(name="Всего потрачено", value=f"{total} монет", inline=True)
    embed.add_field(name="Всего покупок", value=len(data[user_id]["all_purchases"]), inline=True)
    
    recent = data[user_id]["all_purchases"][-10:]
    items = []
    for p in recent:
        status = "✅" if p.get("delivered") else "⏳"
        items.append(f"{status} {p['name']} - {p['price']}💎 ({p['date']})")
    
    embed.add_field(name="Последние покупки", value="\n".join(items) or "Нет", inline=False)
    embed.set_footer(text="by Ilya Vetrov")
    
    await ctx.send(embed=embed)

@bot.command(name='каналы')
async def channels_command(ctx):
    """Информация о каналах"""
    embed = discord.Embed(title="📢 ДОСТУПНЫЕ КАНАЛЫ", color=discord.Color.blue())
    embed.add_field(name="💰 Канал баланса", value=f"<#{BALANCE_CHANNEL_ID}>\nТолько !баланс", inline=False)
    embed.add_field(name="🛒 Магазинный канал", value=f"<#{SHOP_CHANNEL_ID}>\nМагазин, покупки, инвентарь, история", inline=False)
    embed.add_field(name="👑 Админский канал", value=f"<#{ADMIN_CHANNEL_ID}>\nУведомления и все команды", inline=False)
    embed.set_footer(text="by Ilya Vetrov")
    
    await ctx.send(embed=embed)

@bot.command(name='команды')
async def commands_command(ctx):
    """Список команд"""
    embed = discord.Embed(title="📋 ДОСТУПНЫЕ КОМАНДЫ", color=discord.Color.blue())
    embed.add_field(name="!магазин", value="🛒 Открыть магазин", inline=False)
    embed.add_field(name="!баланс", value="💰 Проверить баланс", inline=False)
    embed.add_field(name="!баланс @пользователь", value="👤 Баланс другого", inline=False)
    embed.add_field(name="!инвентарь", value="📦 Полученные предметы", inline=False)
    embed.add_field(name="!история", value="📜 История покупок", inline=False)
    embed.add_field(name="!каналы", value="📢 Информация о каналах", inline=False)
    embed.set_footer(text="by Ilya Vetrov")
    
    await ctx.send(embed=embed)
    
    if is_admin(ctx.author.id):
        admin_embed = discord.Embed(title="👑 АДМИН КОМАНДЫ", color=discord.Color.gold())
        admin_embed.add_field(name="!датьмонет @пользователь сумма", value="💰 Выдать монеты", inline=False)
        admin_embed.add_field(name="!невыдано", value="📋 Показать ожидающие выдачи", inline=False)
        admin_embed.add_field(name="!выдано @пользователь", value="✅ Выдать предметы пользователю", inline=False)
        admin_embed.add_field(name="!выдано", value="✅ Выдать всё всем", inline=False)
        admin_embed.add_field(name="!статистика", value="📊 Статистика магазина", inline=False)
        admin_embed.add_field(name="!админы", value="👑 Список админов", inline=False)
        admin_embed.set_footer(text="by Ilya Vetrov")
        
        await ctx.send(embed=admin_embed)

# ==================== АДМИН КОМАНДЫ ====================

@bot.command(name='датьмонет')
async def give_money_command(ctx, member: discord.Member, amount: int):
    """Выдать монеты пользователю"""
    if not is_admin(ctx.author.id):
        await ctx.send("❌ Только администраторы могут использовать эту команду!")
        return
    
    if amount <= 0:
        await ctx.send("❌ Сумма должна быть положительной!")
        return
    
    data = load_data()
    user_id = str(member.id)
    
    if user_id not in data:
        data[user_id] = {
            "balance": 0, 
            "inventory": [], 
            "pending_items": [], 
            "all_purchases": [], 
            "name": member.name
        }
    
    old = data[user_id]["balance"]
    data[user_id]["balance"] += amount
    data[user_id]["name"] = member.name
    save_data(data)
    
    embed = discord.Embed(title="💰 МОНЕТЫ ВЫДАНЫ", color=discord.Color.green())
    embed.add_field(name="Администратор", value=ctx.author.name, inline=True)
    embed.add_field(name="Получатель", value=member.mention, inline=True)
    embed.add_field(name="Сумма", value=f"+{amount} монет", inline=True)
    embed.add_field(name="Было", value=f"{old} монет", inline=True)
    embed.add_field(name="Стало", value=f"{data[user_id]['balance']} монет", inline=True)
    embed.set_footer(text="by Ilya Vetrov")
    
    await ctx.send(embed=embed)

@bot.command(name='невыдано')
async def pending_command(ctx):
    """Показать предметы к выдаче"""
    if not is_admin(ctx.author.id):
        await ctx.send("❌ Только администраторы могут использовать эту команду!")
        return
    
    data = load_data()
    pending_list = []
    total_value = 0
    
    for user_id, user_data in data.items():
        for item in user_data.get("pending_items", []):
            if not item.get("delivered"):
                try:
                    user = await bot.fetch_user(int(user_id))
                    username = user.name
                except:
                    username = user_data.get("name", "?")
                
                pending_list.append({
                    "user": username,
                    "item": item["name"],
                    "price": item["price"],
                    "nickname": item.get("nickname", "?"),
                    "cid": item.get("cid", "?"),
                    "date": item.get("date", "?")
                })
                total_value += item["price"]
    
    if not pending_list:
        await ctx.send("📦 Нет предметов к выдаче!")
        return
    
    embed = discord.Embed(
        title="📋 ПРЕДМЕТЫ К ВЫДАЧЕ",
        description=f"Всего: **{len(pending_list)}** предметов на **{total_value}** монет",
        color=discord.Color.orange()
    )
    
    for p in pending_list[:10]:
        embed.add_field(
            name=f"{p['user']} - {p['item']}",
            value=f"💰 {p['price']} | Ник: {p['nickname']} | CID: {p['cid']} | {p['date']}",
            inline=False
        )
    
    embed.set_footer(text="by Ilya Vetrov")
    await ctx.send(embed=embed)

@bot.command(name='выдано')
async def deliver_command(ctx, member: discord.Member = None):
    """Отметить предметы как выданные"""
    if not is_admin(ctx.author.id):
        await ctx.send("❌ Только администраторы могут использовать эту команду!")
        return
    
    data = load_data()
    
    if member:
        user_id = str(member.id)
        if user_id in data:
            count = 0
            items = []
            
            for item in data[user_id].get("pending_items", []):
                if not item.get("delivered"):
                    item["delivered"] = True
                    count += 1
                    items.append(item["name"])
                    
                    if "inventory" not in data[user_id]:
                        data[user_id]["inventory"] = []
                    data[user_id]["inventory"].append({
                        "name": item["name"],
                        "received_date": datetime.now().strftime("%d.%m.%Y %H:%M"),
                        "received_by": ctx.author.name
                    })
            
            if count > 0:
                save_data(data)
                await ctx.send(f"✅ Выдано **{count}** предметов {member.mention}")
            else:
                await ctx.send(f"📦 У {member.mention} нет предметов к выдаче")
    else:
        total = 0
        for user_id, user_data in data.items():
            for item in user_data.get("pending_items", []):
                if not item.get("delivered"):
                    item["delivered"] = True
                    total += 1
                    
                    if "inventory" not in user_data:
                        user_data["inventory"] = []
                    user_data["inventory"].append({
                        "name": item["name"],
                        "received_date": datetime.now().strftime("%d.%m.%Y %H:%M"),
                        "received_by": ctx.author.name
                    })
        
        if total > 0:
            save_data(data)
            await ctx.send(f"✅ Выдано всего **{total}** предметов всем!")
        else:
            await ctx.send("📦 Нет предметов к выдаче")

@bot.command(name='статистика')
async def stats_command(ctx):
    """Статистика магазина"""
    if not is_admin(ctx.author.id):
        await ctx.send("❌ Только администраторы могут использовать эту команду!")
        return
    
    data = load_data()
    
    users = len(data)
    pending = 0
    delivered = 0
    spent = 0
    
    for user_data in data.values():
        pending += len([x for x in user_data.get("pending_items", []) if not x.get("delivered")])
        delivered += len(user_data.get("inventory", []))
        spent += sum(p.get("price", 0) for p in user_data.get("all_purchases", []))
    
    embed = discord.Embed(title="📊 СТАТИСТИКА МАГАЗИНА", color=discord.Color.blue())
    embed.add_field(name="Пользователей", value=users, inline=True)
    embed.add_field(name="Всего покупок", value=pending + delivered, inline=True)
    embed.add_field(name="Ожидают выдачи", value=pending, inline=True)
    embed.add_field(name="Уже выдано", value=delivered, inline=True)
    embed.add_field(name="Всего потрачено", value=f"{spent} монет", inline=True)
    embed.set_footer(text="by Ilya Vetrov")
    
    await ctx.send(embed=embed)

@bot.command(name='админы')
async def admins_command(ctx):
    """Список администраторов"""
    admin_list = []
    for admin_id in ADMIN_IDS:
        try:
            user = await bot.fetch_user(admin_id)
            admin_list.append(f"• {user.name}")
        except:
            admin_list.append(f"• Админ (ID: {admin_id})")
    
    embed = discord.Embed(title="👑 АДМИНИСТРАТОРЫ", description="\n".join(admin_list), color=discord.Color.gold())
    embed.set_footer(text="by Ilya Vetrov")
    
    await ctx.send(embed=embed)

# ==================== ЗАПУСК ====================

@bot.event
async def on_ready():
    print(f'✅ Бот {bot.user} успешно запущен!')
    print(f'👑 Администраторов: {len(ADMIN_IDS)}')
    print(f'💰 Канал баланса: {BALANCE_CHANNEL_ID}')
    print(f'🛒 Магазинный канал: {SHOP_CHANNEL_ID}')
    print(f'👑 Админский канал: {ADMIN_CHANNEL_ID}')
    await bot.change_presence(activity=discord.Game(name="!команды | !магазин"))

token = os.getenv('TOKEN')
if not token:
    print("❌ ОШИБКА: Токен не найден!")
    exit(1)

bot.run(token)
