import discord
from discord.ext import commands
from discord.ui import Select, View, Button, Modal, TextInput
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
    500965898476322817,  # Админ 1
    271067502102970371,  # Админ 2
]

# ID каналов
BALANCE_CHANNEL_ID = 1481753586835783861   # Только для !баланс
SHOP_CHANNEL_ID = 1481753891124019302      # Для всех команд (магазин, покупки)
ADMIN_CHANNEL_ID = 1481754087614841033     # Админский канал (уведомления и все команды)

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

# Проверка разрешенного канала для команды
def is_allowed_channel(channel_id, command_name):
    # Админский канал - разрешено всё
    if channel_id == ADMIN_CHANNEL_ID:
        return True
    
    # Канал для баланса - только команда баланс
    if command_name == 'баланс':
        return channel_id == BALANCE_CHANNEL_ID or channel_id == ADMIN_CHANNEL_ID
    
    # Для всех остальных команд - только магазинный канал или админский
    return channel_id == SHOP_CHANNEL_ID or channel_id == ADMIN_CHANNEL_ID

# Класс для модального окна ввода ника (ИСПРАВЛЕННЫЙ)
class NicknameModal(Modal, title="Введите игровые данные"):
    def __init__(self, item_name, item_price, shop_view):
        super().__init__()
        self.item_name = item_name
        self.item_price = item_price
        self.shop_view = shop_view
        
        # Поле для ввода ника
        self.nickname_input = TextInput(
            label="Игровой Никнейм",
            placeholder="Введите ваш игровой никнейм...",
            required=True,
            max_length=50,
            style=discord.TextStyle.short
        )
        self.add_item(self.nickname_input)
        
        # Поле для ввода CID
        self.cid_input = TextInput(
            label="CID",
            placeholder="Введите ваш CID...",
            required=True,
            max_length=20,
            style=discord.TextStyle.short
        )
        self.add_item(self.cid_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        # Отвечаем, чтобы форма закрылась
        await interaction.response.defer(ephemeral=True)
        
        # Вызываем метод покупки
        await self.shop_view.process_purchase(
            interaction, 
            self.item_name, 
            self.item_price,
            self.nickname_input.value,
            self.cid_input.value
        )
    
    async def on_error(self, interaction: discord.Interaction, error: Exception):
        await interaction.response.send_message(
            "❌ Произошла ошибка. Пожалуйста, попробуйте еще раз.",
            ephemeral=True
        )
        print(f"Ошибка в модальном окне: {error}")

# Класс для магазина (исправленный метод process_purchase)
class ShopView(View):
    def __init__(self):
        super().__init__(timeout=None)
        
        # Создаем выпадающий список с товарами
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
                    description=" ",
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
        # Проверяем разрешен ли канал для покупок
        if not is_allowed_channel(interaction.channel_id, 'покупка'):
            await interaction.response.send_message(
                f"❌ Покупки доступны только в канале <#{SHOP_CHANNEL_ID}> или в админском канале!",
                ephemeral=True
            )
            return
        
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
        
        # Проверяем баланс
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
        
        # Открываем модальное окно
        modal = NicknameModal(
            selected_item_data["name"], 
            selected_item_data["price"],
            self
        )
        await interaction.response.send_modal(modal)
    
    async def process_purchase(self, interaction: discord.Interaction, item_name, item_price, nickname, cid):
        """Обработка покупки после ввода данных"""
        try:
            data = load_data()
            user_id = str(interaction.user.id)
            
            if user_id not in data:
                data[user_id] = {
                    "balance": 0, 
                    "inventory": [],
                    "name": interaction.user.name,
                    "pending_items": []
                }
            
            # Проверяем баланс
            if data[user_id]["balance"] < item_price:
                await interaction.followup.send(
                    f"❌ Ошибка: недостаточно средств!\n"
                    f"Нужно: {item_price} монет\n"
                    f"У вас: {data[user_id]['balance']} монет",
                    ephemeral=True
                )
                return
            
            # Списываем деньги
            data[user_id]["balance"] -= item_price
            
            purchase = {
                "name": item_name,
                "price": item_price,
                "purchase_date": datetime.now().strftime("%Y-%m-%d"),
                "purchase_time": datetime.now().strftime("%H:%M:%S"),
                "week": datetime.now().strftime("%Y-%W"),
                "delivered": False,
                "nickname": nickname,
                "cid": cid,
                "channel": interaction.channel.name
            }
            
            if "pending_items" not in data[user_id]:
                data[user_id]["pending_items"] = []
            
            data[user_id]["pending_items"].append(purchase)
            
            if "all_purchases" not in data[user_id]:
                data[user_id]["all_purchases"] = []
            
            data[user_id]["all_purchases"].append(purchase.copy())
            
            data[user_id]["name"] = interaction.user.name
            
            save_data(data)
            
            # Подтверждение пользователю
            embed = discord.Embed(
                title="✅ ПОКУПКА СОВЕРШЕНА!",
                description=f"Вы купили **{item_name}**\nТовар будет выдан администратором в конце недели",
                color=discord.Color.green()
            )
            embed.add_field(name="Цена", value=f"{item_price} монет", inline=True)
            embed.add_field(name="Остаток", value=f"{data[user_id]['balance']} монет", inline=True)
            embed.add_field(name="Статус", value="⏳ Ожидает выдачи", inline=True)
            embed.add_field(name="Игровой ник", value=nickname, inline=True)
            embed.add_field(name="CID", value=cid, inline=True)
            embed.set_footer(text="by Ilya Vetrov")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Отправляем уведомление в АДМИНСКИЙ КАНАЛ
            admin_channel = bot.get_channel(ADMIN_CHANNEL_ID)
            if admin_channel:
                admin_embed = discord.Embed(
                    title="🛒 НОВАЯ ПОКУПКА!",
                    description=f"**Покупатель:** {interaction.user.name} (`{interaction.user.id}`)\n"
                               f"**Предмет:** {item_name}\n"
                               f"**Цена:** {item_price} монет\n"
                               f"**Канал:** #{interaction.channel.name}\n"
                               f"**Время:** {datetime.now().strftime('%H:%M:%S')}\n"
                               f"**Дата:** {datetime.now().strftime('%d.%m.%Y')}",
                    color=discord.Color.blue()
                )
                admin_embed.add_field(name="Игровой никнейм", value=nickname, inline=True)
                admin_embed.add_field(name="CID", value=cid, inline=True)
                admin_embed.add_field(name="Остаток на счету", value=f"{data[user_id]['balance']} монет", inline=False)
                admin_embed.add_field(
                    name="Всего невыданных предметов", 
                    value=len([x for x in data[user_id].get("pending_items", []) if not x.get("delivered", False)]),
                    inline=False
                )
                admin_embed.set_footer(text="by Ilya Vetrov")
                
                await admin_channel.send(embed=admin_embed)
            
            # Также отправляем в личку админам
            for admin_id in ADMIN_IDS:
                try:
                    admin = await bot.fetch_user(admin_id)
                    if admin:
                        await admin.send(embed=admin_embed)
                except:
                    pass
                    
        except Exception as e:
            print(f"Ошибка при обработке покупки: {e}")
            await interaction.followup.send(
                "❌ Произошла ошибка при обработке покупки. Попробуйте позже.",
                ephemeral=True
            )
    
    async def balance_callback(self, interaction: discord.Interaction):
        # Проверяем разрешен ли канал для баланса
        if not is_allowed_channel(interaction.channel_id, 'баланс'):
            await interaction.response.send_message(
                f"❌ Команда `!баланс` доступна только в канале <#{BALANCE_CHANNEL_ID}> или в админском канале!",
                ephemeral=True
            )
            return
        
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

# Команда для открытия магазина
@bot.command(name='магазин')
async def shop(ctx):
    # Проверяем разрешен ли канал
    if not is_allowed_channel(ctx.channel.id, 'магазин'):
        await ctx.send(f"❌ Магазин доступен только в канале <#{SHOP_CHANNEL_ID}> или в админском канале!")
        return
    
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
                   "*При покупке нужно указать Игровой Никнейм и CID*\n"
                   "*Товары будут выданы администратором в конце недели*\n"
                   f"`!команды` - список всех команд",
        color=discord.Color.gold()
    )
    embed.set_footer(text="by Ilya Vetrov")
    
    view = ShopView()
    await ctx.send(embed=embed, view=view)

# ... остальные команды без изменений ...

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
