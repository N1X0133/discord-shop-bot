import discord
from discord.ext import commands
from discord.ui import Select, View, Button
import json
import os
from datetime import datetime, timedelta

# Настройки бота
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Файл для хранения данных пользователей
DATA_FILE = 'user_data.json'

# ID администраторов
ADMIN_IDS = [
    927642459998138418,  # Главный админ
    500965898476322817,  # Новый админ 1
    271067502102970371,  # Новый админ 2
]

# Загрузка данных пользователей
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

# Сохранение данных пользователей
def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Проверка на администратора
def is_admin(user_id):
    return user_id in ADMIN_IDS or user_id == bot.owner_id

# Класс для магазина
class ShopView(View):
    def __init__(self):
        super().__init__(timeout=None)
        
        # Создаем выпадающий список с товарами (БЕЗ ОПИСАНИЙ)
        self.shop_items = [
            # Глава 1: Расходники
            {"name": "💊 Реанимнабор", "price": 150, "description": "Нет описания"},
            {"name": "💉 Набор для самореанимации", "price": 200, "description": "Нет описания"},
            {"name": "🛡️ Ремкоплект для брони", "price": 100, "description": "Нет описания"},
            {"name": "🔫 MG Ammo", "price": 50, "description": "Нет описания"},
            {"name": "🎯 Sniper Ammo", "price": 75, "description": "Нет описания"},
            
            # Глава 2: Модули
            {"name": "🔇 Глушитель", "price": 300, "description": "Нет описания"},
            {"name": "📦 Увеличенный магазин (винтовка)", "price": 250, "description": "Нет описания"},
            {"name": "📦 Увеличенный магазин (пистолет)", "price": 200, "description": "Нет описания"},
            {"name": "📦 Увеличенный магазин (ПП)", "price": 225, "description": "Нет описания"},
            {"name": "📦 Увеличенный магазин (снайперская винтовка)", "price": 275, "description": "Нет описания"},
            {"name": "🥁 Барабанный магазин (винтовка)", "price": 400, "description": "Нет описания"},
            
            # Глава 3: Спец. вооружение
            {"name": "🔫 Тяжелый пулемет", "price": 800, "description": "Нет описания"},
            {"name": "⚡ Тяжелый пулемет MK2", "price": 1200, "description": "Нет описания"},
            {"name": "🎯 Тяжелая снайперская", "price": 1000, "description": "Нет описания"},
            {"name": "⭐ Тяжелая снайперская MK2", "price": 1500, "description": "Нет описания"},
            {"name": "🔫 Штурмовой дробовик", "price": 600, "description": "Нет описания"},
            {"name": "🔫 Тяжелый револьвер MK2", "price": 700, "description": "Нет описания"},
        ]
        
        # Создаем выпадающий список
        options = []
        for item in self.shop_items:
            options.append(
                discord.SelectOption(
                    label=item["name"],
                    description=" ",  # Пустое описание
                    value=item["name"]
                )
            )
        
        self.select_menu = Select(
            placeholder="Выберите товар для покупки...",
            options=options,
            custom_id="shop_select"
        )
        self.select_menu.callback = self.select_callback
        self.add_item(self.select_menu)
        
        # Кнопка покупки
        self.buy_button = Button(
            label="Купить",
            style=discord.ButtonStyle.green,
            custom_id="buy_button",
            emoji="💰"
        )
        self.buy_button.callback = self.buy_callback
        self.add_item(self.buy_button)
        
        # Кнопка для просмотра баланса
        self.balance_button = Button(
            label="Мой баланс",
            style=discord.ButtonStyle.blurple,
            custom_id="balance_button",
            emoji="💳"
        )
        self.balance_button.callback = self.balance_callback
        self.add_item(self.balance_button)
        
        self.selected_item = None
    
    async def select_callback(self, interaction: discord.Interaction):
        self.selected_item = self.select_menu.values[0]
        await interaction.response.send_message(
            f"Вы выбрали: {self.selected_item}",
            ephemeral=True
        )
    
    async def buy_callback(self, interaction: discord.Interaction):
        if not self.selected_item:
            await interaction.response.send_message(
                "❌ Сначала выберите товар из списка!",
                ephemeral=True
            )
            return
        
        selected_item_data = None
        for item in self.shop_items:
            if item["name"] == self.selected_item:
                selected_item_data = item
                break
        
        if not selected_item_data:
            await interaction.response.send_message(
                "❌ Товар не найден!",
                ephemeral=True
            )
            return
        
        data = load_data()
        user_id = str(interaction.user.id)
        
        if user_id not in data:
            data[user_id] = {
                "balance": 0, 
                "inventory": [],
                "name": interaction.user.name,
                "pending_items": []
            }
        
        if data[user_id]["balance"] < selected_item_data["price"]:
            await interaction.response.send_message(
                f"❌ У вас недостаточно средств!\n"
                f"Нужно: {selected_item_data['price']} монет\n"
                f"У вас: {data[user_id]['balance']} монет",
                ephemeral=True
            )
            return
        
        # Списываем деньги и добавляем предмет в ожидание выдачи
        data[user_id]["balance"] -= selected_item_data["price"]
        
        purchase = {
            "name": selected_item_data["name"],
            "price": selected_item_data["price"],
            "purchase_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "purchase_time": datetime.now().strftime("%H:%M:%S"),
            "week": datetime.now().strftime("%Y-%W"),
            "delivered": False
        }
        
        if "pending_items" not in data[user_id]:
            data[user_id]["pending_items"] = []
        
        data[user_id]["pending_items"].append(purchase)
        
        if "all_purchases" not in data[user_id]:
            data[user_id]["all_purchases"] = []
        
        data[user_id]["all_purchases"].append(purchase.copy())
        
        data[user_id]["name"] = interaction.user.name
        
        save_data(data)
        
        embed = discord.Embed(
            title="✅ Покупка совершена!",
            description=f"Вы купили **{selected_item_data['name']}**\nТовар будет выдан администратором в конце недели",
            color=discord.Color.green()
        )
        embed.add_field(name="Цена", value=f"{selected_item_data['price']} монет", inline=True)
        embed.add_field(name="Остаток", value=f"{data[user_id]['balance']} монет", inline=True)
        embed.add_field(name="Статус", value="⏳ Ожидает выдачи", inline=True)
        embed.set_footer(text="by Ilya Vetrov")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Подробное уведомление ВСЕМ админам
        for admin_id in ADMIN_IDS:
            admin = await bot.fetch_user(admin_id)
            if admin:
                try:
                    admin_embed = discord.Embed(
                        title="🛒 НОВАЯ ПОКУПКА!",
                        description=f"**Покупатель:** {interaction.user.name} (`{interaction.user.id}`)\n"
                                   f"**Предмет:** {selected_item_data['name']}\n"
                                   f"**Цена:** {selected_item_data['price']} монет\n"
                                   f"**Время:** {datetime.now().strftime('%H:%M:%S')}\n"
                                   f"**Дата:** {datetime.now().strftime('%d.%m.%Y')}",
                        color=discord.Color.blue()
                    )
                    admin_embed.add_field(
                        name="Остаток на счету", 
                        value=f"{data[user_id]['balance']} монет", 
                        inline=False
                    )
                    admin_embed.add_field(
                        name="Всего невыданных предметов", 
                        value=len([x for x in data[user_id].get("pending_items", []) if not x.get("delivered", False)]),
                        inline=False
                    )
                    admin_embed.set_footer(text="by Ilya Vetrov")
                    await admin.send(embed=admin_embed)
                except Exception as e:
                    print(f"Не удалось отправить уведомление админу {admin_id}: {e}")
    
    async def balance_callback(self, interaction: discord.Interaction):
        data = load_data()
        user_id = str(interaction.user.id)
        
        if user_id not in data:
            balance = 0
            pending = 0
        else:
            balance = data[user_id]["balance"]
            pending = len([x for x in data[user_id].get("pending_items", []) if not x.get("delivered", False)])
        
        embed = discord.Embed(
            title="💰 Ваш баланс",
            color=discord.Color.blue()
        )
        embed.add_field(name="Монеты", value=f"{balance} монет", inline=True)
        embed.add_field(name="Ожидают выдачи", value=f"{pending} шт.", inline=True)
        embed.set_footer(text="by Ilya Vetrov")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

# НОВАЯ КОМАНДА: !команды
@bot.command(name='команды')
async def show_commands(ctx):
    """Показать все доступные команды"""
    
    # Команды для всех пользователей
    user_commands = discord.Embed(
        title="📋 ДОСТУПНЫЕ КОМАНДЫ",
        description="**Команды для всех пользователей:**",
        color=discord.Color.blue()
    )
    user_commands.add_field(
        name="!магазин", 
        value="🛒 Открыть магазин и купить предметы", 
        inline=False
    )
    user_commands.add_field(
        name="!баланс", 
        value="💰 Проверить свой баланс монет", 
        inline=False
    )
    user_commands.add_field(
        name="!баланс @пользователь", 
        value="👤 Проверить баланс другого пользователя", 
        inline=False
    )
    user_commands.add_field(
        name="!инвентарь", 
        value="📦 Посмотреть свои полученные предметы", 
        inline=False
    )
    user_commands.add_field(
        name="!инвентарь @пользователь", 
        value="📦 Посмотреть инвентарь другого пользователя", 
        inline=False
    )
    user_commands.add_field(
        name="!история", 
        value="📜 Показать историю своих покупок", 
        inline=False
    )
    user_commands.add_field(
        name="!команды", 
        value="❓ Показать это сообщение", 
        inline=False
    )
    user_commands.set_footer(text="by Ilya Vetrov")
    
    await ctx.send(embed=user_commands)
    
    # Если пользователь админ - показываем дополнительные команды
    if is_admin(ctx.author.id):
        admin_commands = discord.Embed(
            title="👑 АДМИНИСТРАТОРСКИЕ КОМАНДЫ",
            description="**Команды только для администраторов:**",
            color=discord.Color.gold()
        )
        admin_commands.add_field(
            name="!датьмонет @пользователь сумма", 
            value="💰 Выдать монеты пользователю", 
            inline=False
        )
        admin_commands.add_field(
            name="!невыдано", 
            value="📋 Показать все предметы, ожидающие выдачи", 
            inline=False
        )
        admin_commands.add_field(
            name="!выдано @пользователь", 
            value="✅ Выдать ВСЕ предметы пользователю", 
            inline=False
        )
        admin_commands.add_field(
            name="!выдано", 
            value="✅ Выдать ВСЕ предметы ВСЕМ пользователям", 
            inline=False
        )
        admin_commands.add_field(
            name="!история @пользователь", 
            value="📜 Посмотреть историю покупок любого пользователя", 
            inline=False
        )
        admin_commands.add_field(
            name="!статистика", 
            value="📊 Показать общую статистику магазина", 
            inline=False
        )
        admin_commands.add_field(
            name="!админы", 
            value="👑 Список всех администраторов", 
            inline=False
        )
        admin_commands.set_footer(text="by Ilya Vetrov")
        
        await ctx.send(embed=admin_commands)

# Команда для открытия магазина (обновлена - убраны описания)
@bot.command(name='магазин')
async def shop(ctx):
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
                   "🔫 Тяжелый револьвер MK2 — 700 монет\n\n"
                   "*Товары будут выданы администратором в конце недели*\n"
                   "`!команды` - список всех команд",
        color=discord.Color.gold()
    )
    embed.set_footer(text="by Ilya Vetrov")
    
    view = ShopView()
    await ctx.send(embed=embed, view=view)

# Команда для просмотра невыданных предметов
@bot.command(name='невыдано')
async def pending_items(ctx):
    if not is_admin(ctx.author.id):
        await ctx.send("❌ Только администраторы могут использовать эту команду!")
        return
    
    data = load_data()
    
    pending_list = []
    total_value = 0
    
    for user_id, user_data in data.items():
        pending = user_data.get("pending_items", [])
        for item in pending:
            if not item.get("delivered", False):
                try:
                    user = await bot.fetch_user(int(user_id))
                    username = user.name
                except:
                    username = user_data.get("name", "Неизвестный")
                
                pending_list.append({
                    "user_id": user_id,
                    "username": username,
                    "item": item["name"],
                    "price": item.get("price", 0),
                    "date": item["purchase_date"],
                    "time": item.get("purchase_time", "00:00:00")
                })
                total_value += item.get("price", 0)
    
    if not pending_list:
        await ctx.send("📦 Нет предметов, ожидающих выдачи!")
        return
    
    embed = discord.Embed(
        title="📋 ПРЕДМЕТЫ К ВЫДАЧЕ",
        description=f"Всего ожидают выдачи: **{len(pending_list)}** предметов\n"
                   f"Общая стоимость: **{total_value}** монет",
        color=discord.Color.orange()
    )
    
    by_user = {}
    for item in pending_list:
        if item["username"] not in by_user:
            by_user[item["username"]] = []
        by_user[item["username"]].append(item)
    
    for username, items in by_user.items():
        item_list = "\n".join([f"• {x['item']} ({x['price']}💎) - {x['date']} {x['time']}" for x in items])
        user_total = sum(x['price'] for x in items)
        embed.add_field(
            name=f"{username} ({len(items)} шт. | {user_total}💎)",
            value=item_list[:1024],
            inline=False
        )
    
    embed.set_footer(text="by Ilya Vetrov")
    await ctx.send(embed=embed)

# Команда для отметки предметов как выданных
@bot.command(name='выдано')
async def mark_delivered(ctx, member: discord.Member = None):
    if not is_admin(ctx.author.id):
        await ctx.send("❌ Только администраторы могут использовать эту команду!")
        return
    
    data = load_data()
    
    if member:
        user_id = str(member.id)
        if user_id in data:
            count = 0
            total_price = 0
            items_list = []
            
            for item in data[user_id].get("pending_items", []):
                if not item.get("delivered", False):
                    item["delivered"] = True
                    count += 1
                    total_price += item.get("price", 0)
                    items_list.append(item["name"])
                    
                    if "inventory" not in data[user_id]:
                        data[user_id]["inventory"] = []
                    data[user_id]["inventory"].append({
                        "name": item["name"],
                        "received_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "received_by": ctx.author.name
                    })
            
            if count > 0:
                save_data(data)
                
                log_embed = discord.Embed(
                    title="📦 ПРЕДМЕТЫ ВЫДАНЫ",
                    description=f"**Администратор:** {ctx.author.name}\n"
                               f"**Получатель:** {member.mention}\n"
                               f"**Количество:** {count} предметов\n"
                               f"**Общая стоимость:** {total_price} монет",
                    color=discord.Color.green()
                )
                log_embed.add_field(name="Предметы", value="\n".join(items_list)[:1024])
                log_embed.set_footer(text="by Ilya Vetrov")
                
                for admin_id in ADMIN_IDS:
                    admin = await bot.fetch_user(admin_id)
                    if admin and admin_id != ctx.author.id:
                        try:
                            await admin.send(embed=log_embed)
                        except:
                            pass
                
                await ctx.send(embed=log_embed)
            else:
                await ctx.send(f"📦 У пользователя {member.mention} нет предметов к выдаче")
    else:
        total = 0
        total_price_all = 0
        
        for user_id, user_data in data.items():
            for item in user_data.get("pending_items", []):
                if not item.get("delivered", False):
                    item["delivered"] = True
                    total += 1
                    total_price_all += item.get("price", 0)
                    
                    if "inventory" not in user_data:
                        user_data["inventory"] = []
                    user_data["inventory"].append({
                        "name": item["name"],
                        "received_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "received_by": ctx.author.name
                    })
        
        if total > 0:
            save_data(data)
            
            log_embed = discord.Embed(
                title="📦 МАССОВАЯ ВЫДАЧА",
                description=f"**Администратор:** {ctx.author.name}\n"
                           f"**Выдано всего:** {total} предметов\n"
                           f"**Общая стоимость:** {total_price_all} монет",
                color=discord.Color.green()
            )
            log_embed.set_footer(text="by Ilya Vetrov")
            
            for admin_id in ADMIN_IDS:
                admin = await bot.fetch_user(admin_id)
                if admin and admin_id != ctx.author.id:
                    try:
                        await admin.send(embed=log_embed)
                    except:
                        pass
            
            await ctx.send(embed=log_embed)
        else:
            await ctx.send("📦 Нет предметов к выдаче")

# Команда для просмотра истории покупок
@bot.command(name='история')
async def purchase_history(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author
    
    if member != ctx.author and not is_admin(ctx.author.id):
        await ctx.send("❌ Вы можете смотреть только свою историю!")
        return
    
    data = load_data()
    user_id = str(member.id)
    
    if user_id not in data or "all_purchases" not in data[user_id] or not data[user_id]["all_purchases"]:
        await ctx.send(f"📭 У пользователя {member.mention} нет истории покупок")
        return
    
    embed = discord.Embed(
        title=f"📜 ИСТОРИЯ ПОКУПОК: {member.name}",
        color=discord.Color.purple()
    )
    
    total_spent = sum(p.get("price", 0) for p in data[user_id]["all_purchases"])
    total_items = len(data[user_id]["all_purchases"])
    pending = len([p for p in data[user_id].get("pending_items", []) if not p.get("delivered", False)])
    
    embed.add_field(name="Всего потрачено", value=f"{total_spent} монет", inline=True)
    embed.add_field(name="Всего покупок", value=total_items, inline=True)
    embed.add_field(name="Ожидают выдачи", value=pending, inline=True)
    
    recent = data[user_id]["all_purchases"][-10:]
    recent_list = ""
    for p in recent:
        status = "✅" if p.get("delivered", False) else "⏳"
        recent_list += f"{status} {p['name']} - {p['price']}💎 ({p['purchase_date']})\n"
    
    embed.add_field(name="Последние покупки", value=recent_list or "Нет", inline=False)
    embed.set_footer(text="by Ilya Vetrov")
    
    await ctx.send(embed=embed)

# Команда для выдачи валюты
@bot.command(name='датьмонет')
async def give_money(ctx, member: discord.Member = None, amount: int = None):
    if not is_admin(ctx.author.id):
        await ctx.send("❌ Только администраторы могут выдавать валюту!")
        return
    
    if member is None or amount is None:
        await ctx.send("❌ Использование: !датьмонет @пользователь сумма")
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
    
    old_balance = data[user_id]["balance"]
    data[user_id]["balance"] += amount
    data[user_id]["name"] = member.name
    save_data(data)
    
    embed = discord.Embed(
        title="💰 МОНЕТЫ ВЫДАНЫ",
        description=f"**Администратор:** {ctx.author.name}\n"
                   f"**Получатель:** {member.mention}\n"
                   f"**Сумма:** +{amount} монет\n"
                   f"**Было:** {old_balance} монет\n"
                   f"**Стало:** {data[user_id]['balance']} монет",
        color=discord.Color.green()
    )
    embed.set_footer(text="by Ilya Vetrov")
    
    for admin_id in ADMIN_IDS:
        admin = await bot.fetch_user(admin_id)
        if admin and admin_id != ctx.author.id:
            try:
                await admin.send(embed=embed)
            except:
                pass
    
    await ctx.send(embed=embed)

# Команда для просмотра баланса
@bot.command(name='баланс')
async def check_balance(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author
    
    data = load_data()
    user_id = str(member.id)
    
    if user_id not in data:
        balance = 0
        pending = 0
    else:
        balance = data[user_id]["balance"]
        pending = len([x for x in data[user_id].get("pending_items", []) if not x.get("delivered", False)])
    
    embed = discord.Embed(
        title=f"💰 БАЛАНС: {member.name}",
        color=discord.Color.blue()
    )
    embed.add_field(name="Монеты", value=f"{balance} монет", inline=True)
    embed.add_field(name="Ожидают выдачи", value=f"{pending} шт.", inline=True)
    embed.set_footer(text="by Ilya Vetrov")
    
    await ctx.send(embed=embed)

# Команда для просмотра инвентаря
@bot.command(name='инвентарь')
async def inventory(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author
    
    data = load_data()
    user_id = str(member.id)
    
    if user_id not in data or "inventory" not in data[user_id] or not data[user_id]["inventory"]:
        embed = discord.Embed(
            title=f"📦 ИНВЕНТАРЬ: {member.name}",
            description="Инвентарь пуст!",
            color=discord.Color.light_grey()
        )
        embed.add_field(name="Баланс", value=f"{data.get(user_id, {}).get('balance', 0)} монет", inline=True)
        pending = len(data.get(user_id, {}).get("pending_items", []))
        if pending > 0:
            embed.add_field(name="Ожидают выдачи", value=f"{pending} шт.", inline=True)
        embed.set_footer(text="by Ilya Vetrov")
        await ctx.send(embed=embed)
        return
    
    embed = discord.Embed(
        title=f"📦 ИНВЕНТАРЬ: {member.name}",
        description="**Полученные предметы:**",
        color=discord.Color.purple()
    )
    
    inventory_list = ""
    for i, item in enumerate(data[user_id]["inventory"][-20:], 1):
        received_by = item.get("received_by", "админ")
        inventory_list += f"{i}. {item['name']} (выдал: {received_by}, {item.get('received_date', 'неизвестно')})\n"
    
    embed.add_field(name="Предметы", value=inventory_list or "Нет предметов", inline=False)
    embed.add_field(name="Баланс", value=f"{data[user_id]['balance']} монет", inline=True)
    
    pending = len([x for x in data[user_id].get("pending_items", []) if not x.get("delivered", False)])
    if pending > 0:
        embed.add_field(name="Ожидают выдачи", value=f"{pending} шт.", inline=True)
    
    embed.set_footer(text="by Ilya Vetrov")
    await ctx.send(embed=embed)

# Команда для просмотра всех админов
@bot.command(name='админы')
async def list_admins(ctx):
    admin_list = []
    for admin_id in ADMIN_IDS:
        try:
            user = await bot.fetch_user(admin_id)
            admin_list.append(f"• {user.name} (`{admin_id}`)")
        except:
            admin_list.append(f"• Неизвестный (`{admin_id}`)")
    
    embed = discord.Embed(
        title="👑 АДМИНИСТРАТОРЫ",
        description="\n".join(admin_list),
        color=discord.Color.gold()
    )
    embed.set_footer(text="by Ilya Vetrov")
    await ctx.send(embed=embed)

# Команда для просмотра статистики
@bot.command(name='статистика')
async def shop_stats(ctx):
    if not is_admin(ctx.author.id):
        await ctx.send("❌ Только администраторы могут использовать эту команду!")
        return
    
    data = load_data()
    
    total_users = len(data)
    total_pending = 0
    total_delivered = 0
    total_spent_all = 0
    
    for user_data in data.values():
        total_pending += len([x for x in user_data.get("pending_items", []) if not x.get("delivered", False)])
        total_delivered += len(user_data.get("inventory", []))
        total_spent_all += sum(p.get("price", 0) for p in user_data.get("all_purchases", []))
    
    embed = discord.Embed(
        title="📊 СТАТИСТИКА МАГАЗИНА",
        color=discord.Color.blue()
    )
    embed.add_field(name="Всего пользователей", value=total_users, inline=True)
    embed.add_field(name="Всего покупок", value=total_pending + total_delivered, inline=True)
    embed.add_field(name="Ожидают выдачи", value=total_pending, inline=True)
    embed.add_field(name="Уже выдано", value=total_delivered, inline=True)
    embed.add_field(name="Всего потрачено", value=f"{total_spent_all} монет", inline=True)
    embed.set_footer(text="by Ilya Vetrov")
    
    await ctx.send(embed=embed)

# Запуск бота
@bot.event
async def on_ready():
    print(f'✅ Бот {bot.user} готов к работе!')
    print(f'📁 Папка: /app')
    print(f'👑 Администраторов: {len(ADMIN_IDS)}')
    await bot.change_presence(activity=discord.Game(name="!команды | !магазин"))

# Запуск бота с токеном из переменной окружения
token = os.getenv('TOKEN')
if token is None:
    print("❌ ОШИБКА: Токен не найден! Добавьте переменную TOKEN в Variables")
    exit(1)
bot.run(token)
