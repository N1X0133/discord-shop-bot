import discord
from discord.ext import commands
from discord.ui import Select, View, Button
import json
import os
from datetime import datetime

# Настройки бота
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Файл для хранения данных пользователей
DATA_FILE = 'user_data.json'

# ID администраторов (ЗАМЕНИТЕ НА СВОЙ ID)
ADMIN_IDS = [
    927642459998138418,  # ВСТАВЬТЕ СВОЙ ID СЮДА!
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
        
        # Создаем выпадающий список с товарами
        self.shop_items = [
            {"name": "🔮 Магический свиток", "price": 100, "description": "Древний свиток с заклинаниями"},
            {"name": "⚔️ Легендарный меч", "price": 500, "description": "Меч, выкованный из звездной стали"},
            {"name": "🛡️ Непробиваемый щит", "price": 300, "description": "Щит, способный выдержать любой удар"},
            {"name": "🧪 Зелье опыта", "price": 150, "description": "Дает +100 к опыту"},
            {"name": "💎 Магический кристалл", "price": 200, "description": "Кристалл, наполненный магической энергией"},
        ]
        
        # Создаем выпадающий список
        options = []
        for item in self.shop_items:
            options.append(
                discord.SelectOption(
                    label=item["name"],
                    description=item["description"],
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
            data[user_id] = {"balance": 0, "inventory": []}
        
        if data[user_id]["balance"] < selected_item_data["price"]:
            await interaction.response.send_message(
                f"❌ У вас недостаточно средств!\n"
                f"Нужно: {selected_item_data['price']} монет\n"
                f"У вас: {data[user_id]['balance']} монет",
                ephemeral=True
            )
            return
        
        data[user_id]["balance"] -= selected_item_data["price"]
        data[user_id]["inventory"].append({
            "name": selected_item_data["name"],
            "purchase_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        save_data(data)
        
        embed = discord.Embed(
            title="✅ Покупка совершена!",
            color=discord.Color.green()
        )
        embed.add_field(
            name="Товар",
            value=selected_item_data["name"],
            inline=True
        )
        embed.add_field(
            name="Цена",
            value=f"{selected_item_data['price']} монет",
            inline=True
        )
        embed.add_field(
            name="Остаток",
            value=f"{data[user_id]['balance']} монет",
            inline=True
        )
        embed.set_footer(text=f"Покупатель: {interaction.user.name}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def balance_callback(self, interaction: discord.Interaction):
        data = load_data()
        user_id = str(interaction.user.id)
        
        if user_id not in data:
            balance = 0
        else:
            balance = data[user_id]["balance"]
        
        embed = discord.Embed(
            title="💰 Ваш баланс",
            color=discord.Color.blue()
        )
        embed.add_field(name="Монеты", value=f"{balance} монет", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

# Команда для открытия магазина
@bot.command(name='магазин')
async def shop(ctx):
    embed = discord.Embed(
        title="🛒 Магазин",
        description="Выберите товар из списка ниже и нажмите кнопку **Купить**",
        color=discord.Color.gold()
    )
    
    shop_items = [
        {"name": "🔮 Магический свиток", "price": 100, "description": "Древний свиток с заклинаниями"},
        {"name": "⚔️ Легендарный меч", "price": 500, "description": "Меч, выкованный из звездной стали"},
        {"name": "🛡️ Непробиваемый щит", "price": 300, "description": "Щит, способный выдержать любой удар"},
        {"name": "🧪 Зелье опыта", "price": 150, "description": "Дает +100 к опыту"},
        {"name": "💎 Магический кристалл", "price": 200, "description": "Кристалл, наполненный магической энергией"},
    ]
    
    items_list = ""
    for item in shop_items:
        items_list += f"{item['name']} — {item['price']} монет\n_{item['description']}_\n\n"
    
    embed.add_field(name="Доступные товары", value=items_list, inline=False)
    
    view = ShopView()
    await ctx.send(embed=embed, view=view)

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
        data[user_id] = {"balance": 0, "inventory": []}
    
    data[user_id]["balance"] += amount
    save_data(data)
    
    embed = discord.Embed(
        title="💰 Монеты выданы!",
        color=discord.Color.green()
    )
    embed.add_field(name="Получатель", value=member.mention, inline=True)
    embed.add_field(name="Сумма", value=f"+{amount} монет", inline=True)
    embed.add_field(name="Новый баланс", value=f"{data[user_id]['balance']} монет", inline=True)
    
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
    else:
        balance = data[user_id]["balance"]
    
    embed = discord.Embed(
        title=f"💰 Баланс {member.name}",
        color=discord.Color.blue()
    )
    embed.add_field(name="Монеты", value=f"{balance} монет", inline=True)
    
    await ctx.send(embed=embed)

# Команда для просмотра инвентаря
@bot.command(name='инвентарь')
async def inventory(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author
    
    data = load_data()
    user_id = str(member.id)
    
    if user_id not in data or not data[user_id]["inventory"]:
        await ctx.send(f"📦 Инвентарь {member.name} пуст!")
        return
    
    embed = discord.Embed(
        title=f"📦 Инвентарь {member.name}",
        color=discord.Color.purple()
    )
    
    inventory_list = ""
    for i, item in enumerate(data[user_id]["inventory"], 1):
        inventory_list += f"{i}. {item['name']} (приобретено: {item['purchase_date']})\n"
    
    embed.add_field(name="Предметы", value=inventory_list, inline=False)
    embed.add_field(name="Баланс", value=f"{data[user_id]['balance']} монет", inline=True)
    
    await ctx.send(embed=embed)

# Запуск бота
@bot.event
async def on_ready():
    print(f'✅ Бот {bot.user} готов к работе!')
    print(f'📁 Папка: C:\\DiscordBot')
    await bot.change_presence(activity=discord.Game(name="!магазин"))

# Запуск бота с токеном из переменной окружения
bot.run(os.getenv('TOKEN'))