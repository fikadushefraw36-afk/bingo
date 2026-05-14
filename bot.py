import os
import logging
import random
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot token
BOT_TOKEN = os.environ.get("BOT_TOKEN")

if not BOT_TOKEN:
    logger.error("BOT_TOKEN not found!")
    exit(1)

# Data storage
user_data = {}
games = {}
admin_commission = {}  # የአስተዳዳሪ ኮሚሽን ማከማቻ
admin_ids = [6608478801]  # 👈 የአስተዳዳሪ ቴሌግራም አይዲ እዚህ አስገባ!

# Commission settings (ከዊን ብቻ)
COMMISSION_BIRR = 10      # 10 ብር ቋሚ ተቆራጭ
COMMISSION_PERCENT = 2    # 2% ተቆራጭ

# Color definitions
GREEN = "🟢"
RED = "🔴"
BLUE = "🔵"
YELLOW = "🟡"
PURPLE = "🟣"
ORANGE = "🟠"
RAINBOW = "🌈"

# ============ Helper Functions ============

def calculate_commission(amount):
    """ኮሚሽኑን አስላ (ከዊን ብቻ)"""
    commission = COMMISSION_BIRR + (amount * COMMISSION_PERCENT / 100)
    return int(commission)

def add_admin_commission(admin_id, amount):
    """ለአስተዳዳሪ ኮሚሽን ጨምር"""
    if admin_id not in admin_commission:
        admin_commission[admin_id] = {
            'total_commission': 0,
            'transactions': []
        }
    admin_commission[admin_id]['total_commission'] += amount
    admin_commission[admin_id]['transactions'].append({
        'amount': amount,
        'date': str(datetime.now()),
        'type': 'winning_commission'
    })
    return admin_commission[admin_id]['total_commission']

def generate_bingo_card():
    """Generate 5x5 Bingo card"""
    card = {}
    letters = ['B', 'I', 'N', 'G', 'O']
    ranges = [range(1,16), range(16,31), range(31,46), range(46,61), range(61,76)]
    
    for i, (letter, r) in enumerate(zip(letters, ranges)):
        nums = random.sample(list(r), 5)
        for j in range(5):
            card[f"{letter}{j+1}"] = nums[j]
    
    card["N3"] = "FREE"
    return card

def check_bingo(card, called_numbers):
    """Check if card has BINGO"""
    # Check rows
    for row in range(1, 6):
        row_complete = True
        for col in ['B', 'I', 'N', 'G', 'O']:
            key = f"{col}{row}"
            if key == "N3":
                continue
            if card.get(key) not in called_numbers:
                row_complete = False
                break
        if row_complete:
            return True
    
    # Check columns
    for col in ['B', 'I', 'N', 'G', 'O']:
        col_complete = True
        for row in range(1, 6):
            key = f"{col}{row}"
            if key == "N3":
                continue
            if card.get(key) not in called_numbers:
                col_complete = False
                break
        if col_complete:
            return True
    
    # Check diagonals
    diag1 = True
    diag2 = True
    for i in range(1, 6):
        key1 = f"{['B','I','N','G','O'][i-1]}{i}"
        key2 = f"{['B','I','N','G','O'][i-1]}{6-i}"
        if key1 != "N3" and card.get(key1) not in called_numbers:
            diag1 = False
        if key2 != "N3" and card.get(key2) not in called_numbers:
            diag2 = False
    
    return diag1 or diag2

def format_card(card, called_numbers, card_num):
    """Format a single card for display"""
    result = f"{BLUE}📋 ካርድ #{card_num}{BLUE}\n"
    result += "┌─────┬─────┬─────┬─────┬─────┐\n"
    result += "│  B  │  I  │  N  │  G  │  O  │\n"
    result += "├─────┼─────┼─────┼─────┼─────┤\n"
    
    for row in range(1, 6):
        line = "│"
        for col in ['B', 'I', 'N', 'G', 'O']:
            key = f"{col}{row}"
            val = card[key]
            if val in called_numbers:
                line += f" {GREEN}✅{GREEN} │"
            elif val == "FREE":
                line += f" {RAINBOW}⭐{RAINBOW} │"
            else:
                line += f" {YELLOW}{val:2d}{YELLOW} │"
        result += line + "\n"
        if row < 5:
            result += "├─────┼─────┼─────┼─────┼─────┤\n"
    
    result += "└─────┴─────┴─────┴─────┴─────┘\n"
    return result

# ============ User Commands ============

async def start(update: Update, context):
    user_id = update.effective_user.id
    username = update.effective_user.first_name
    
    if user_id not in user_data:
        user_data[user_id] = {
            'balance': 10,  # 10 ብር ቦነስ
            'username': username,
            'wins': 0,
            'games_played': 0,
            'joined_at': str(datetime.now()),
            'total_spent': 0,
            'total_commission': 0
        }
        bonus_msg = f"\n\n{RAINBOW}🎁 እንኳን ደስ ያለህ! 10 ብር ቦነስ አግኝተሃል! 🎁{RAINBOW}"
    else:
        bonus_msg = ""
    
    await update.message.reply_text(
        f"{RAINBOW}🌈 *ወደ ቢንጎ ቦት እንኳን በደህና መጣህ!* 🌈{RAINBOW}\n\n"
        f"{GREEN}👋 እንኳን ደህና መጣህ {username}!{GREEN}\n\n"
        f"{BLUE}💰 /balance - ሂሳብህን ማየት{BLUE}\n"
        f"{GREEN}💸 /deposit <ብር> - ገንዘብ ማስገባት (ኮሚሽን የለም){GREEN}\n"
        f"{YELLOW}🎮 /newgame - አዲስ ጨዋታ መጀመር{YELLOW}\n"
        f"{PURPLE}🃟 /buy <ካርድ_ብዛት> - ካርድ መግዛት (ኮሚሽን የለም){PURPLE}\n"
        f"{ORANGE}🎲 /call - ቁጥር መጥራት{ORANGE}\n"
        f"{RED}🏆 /leaderboard - ከፍተኛ አሸናፊዎች{RED}\n"
        f"{BLUE}📊 /stats - ስታቲስቲክስህን ማየት{BLUE}\n"
        f"{PURPLE}🃟 /mycard - ካርዶችህን ማየት{PURPLE}\n"
        f"{YELLOW}👑 /admin - የአስተዳዳሪ ሜኑ (አስተዳዳሪ ብቻ){YELLOW}{bonus_msg}",
        parse_mode='Markdown'
    )

async def balance(update: Update, context):
    user_id = update.effective_user.id
    if user_id not in user_data:
        user_data[user_id] = {'balance': 10, 'wins': 0, 'games_played': 0}
    
    bal = user_data[user_id]['balance']
    await update.message.reply_text(f"{GREEN}💰 *ሂሳብህ*: {bal} ብር{GREEN}", parse_mode='Markdown')

async def deposit(update: Update, context):
    user_id = update.effective_user.id
    args = context.args
    
    # Check if admin
    if user_id not in admin_ids:
        await update.message.reply_text(f"{RED}❌ ይህ ትዕዛዝ ለአስተዳዳሪዎች ብቻ ነው!{RED}", parse_mode='Markdown')
        return
    
    if not args:
        await update.message.reply_text(
            f"{YELLOW}📝 ምሳሌ: /deposit 100 @username{YELLOW}\n\n"
            f"{GREEN}💡 ማስታወሻ: ከdeposit ላይ ኮሚሽን አይቆረጥም!{GREEN}",
            parse_mode='Markdown'
        )
        return
    
    try:
        amount = int(args[0])
        target = args[1] if len(args) > 1 else None
        
        if target and target.startswith('@'):
            target_user = None
            for uid, data in user_data.items():
                if data.get('username') == target[1:]:
                    target_user = uid
                    break
            
            if target_user:
                # ኮሚሽን አይቆረጥም! ሙሉ ገንዘብ ይጨመራል
                user_data[target_user]['balance'] += amount
                
                await update.message.reply_text(
                    f"{GREEN}✅ {amount} ብር ለ{target} ተጨምሯል!{GREEN}\n"
                    f"{BLUE}💰 ኮሚሽን: አልተቆረጠም!{BLUE}",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(f"{RED}❌ ተጠቃሚ አልተገኘም!{RED}")
        else:
            await update.message.reply_text(f"{RED}❌ ትክክለኛ የተጠቃሚ ስም ያስገቡ! ምሳሌ: @username{RED}")
    except:
        await update.message.reply_text(f"{RED}❌ ስህተት ተፈጥሯል!{RED}")

async def newgame(update: Update, context):
    chat_id = update.effective_chat.id
    
    if chat_id in games and games[chat_id].get('active'):
        await update.message.reply_text(f"{RED}🔴 ጨዋታ ቀድሞውኑ እየተካሄደ ነው!{RED}", parse_mode='Markdown')
        return
    
    games[chat_id] = {
        'active': True,
        'players': {},
        'called_numbers': [],
        'start_time': str(datetime.now())
    }
    
    keyboard = [[InlineKeyboardButton(f"{YELLOW}🎲 ቀላቀል 🎲{YELLOW}", callback_data='join_game')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"{RAINBOW}🌈 *አዲስ ቢንጎ ጨዋታ ተጀምሯል!* 🌈{RAINBOW}\n\n"
        f"{GREEN}🔴 ለመቀላቀል ታች ያለውን ቁልፍ ተጫን!{GREEN}\n"
        f"{PURPLE}🃟 ካርድ ለመግዛት /buy (ኮሚሽን የለም){PURPLE}\n"
        f"{ORANGE}🎲 ቁጥር ለመጥራት /call{ORANGE}\n\n"
        f"{YELLOW}🏆 አሸናፊው 200 ብር ያገኛል!{YELLOW}\n"
        f"{RED}📊 ከሽልማት ላይ ኮሚሽን ይቆረጣል!{RED}",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def join_game_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    user_id = user.id
    chat_id = query.message.chat_id
    
    if chat_id not in games or not games[chat_id].get('active'):
        await query.edit_message_text(f"{RED}🔴 ጨዋታው አልተጀመረም ወይም አልቋል!{RED}", parse_mode='Markdown')
        return
    
    if user_id in games[chat_id]['players']:
        await query.edit_message_text(f"{YELLOW}🔴 ቀድሞውኑ ተቀላቅለሃል!{YELLOW}", parse_mode='Markdown')
        return
    
    games[chat_id]['players'][user_id] = {
        'username': user.first_name,
        'cards': [],
        'has_bingo': False
    }
    
    await query.edit_message_text(
        f"{GREEN}✅ *{user.first_name}* ጨዋታውን ተቀላቀለ!{GREEN}\n"
        f"{BLUE}👥 አሁን {len(games[chat_id]['players'])} ተጫዋቾች አሉ!{BLUE}\n\n"
        f"{PURPLE}🃟 /buy <ካርድ_ብዛት> - ካርድ ለመግዛት (ኮሚሽን የለም){PURPLE}",
        parse_mode='Markdown'
    )

async def buy(update: Update, context):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    args = context.args
    
    if chat_id not in games or not games[chat_id].get('active'):
        await update.message.reply_text(f"{RED}🔴 ምንም ንቁ ጨዋታ የለም! /newgame ተጠቀም{RED}", parse_mode='Markdown')
        return
    
    if user_id not in games[chat_id]['players']:
        await update.message.reply_text(f"{YELLOW}🔴 መጀመሪያ ጨዋታውን ተቀላቀል!{YELLOW}", parse_mode='Markdown')
        return
    
    num_cards = 1
    if args and args[0].isdigit():
        num_cards = min(int(args[0]), 5)
    
    cost = num_cards * 10  # 1 ካርድ = 10 ብር
    
    if user_id not in user_data:
        user_data[user_id] = {'balance': 0, 'wins': 0, 'games_played': 0}
    
    if user_data[user_id]['balance'] < cost:
        await update.message.reply_text(
            f"{RED}❌ *በቂ ገንዘብ የለም!*{RED}\n"
            f"{YELLOW}💰 ያለህ: {user_data[user_id]['balance']} ብር{YELLOW}\n"
            f"{PURPLE}🃟 የሚፈለጉት: {num_cards} ካርድ = {cost} ብር{PURPLE}\n\n"
            f"{BLUE}💸 ለማስገባት አስተዳዳሪን አግኝ{BLUE}",
            parse_mode='Markdown'
        )
        return
    
    # ኮሚሽን አይቆረጥም! ሙሉ ገንዘብ ይቀንሳል
    user_data[user_id]['balance'] -= cost
    user_data[user_id]['total_spent'] = user_data[user_id].get('total_spent', 0) + cost
    
    # Generate cards
    cards = []
    for i in range(num_cards):
        card = generate_bingo_card()
        cards.append(card)
        games[chat_id]['players'][user_id]['cards'].append(card)
    
    await update.message.reply_text(
        f"{GREEN}✅ *{num_cards} ካርድ(ዎች) ገዝተሃል!*{GREEN}\n"
        f"{BLUE}💵 ወጪ: {cost} ብር{BLUE}\n"
        f"{GREEN}💰 ኮሚሽን: አልተቆረጠም!{GREEN}\n"
        f"{YELLOW}💰 ቀሪ ሂሳብ: {user_data[user_id]['balance']} ብር{YELLOW}\n\n"
        f"{ORANGE}🎲 /call በመጠቀም ቁጥሮች ጥራ!{ORANGE}",
        parse_mode='Markdown'
    )

async def call(update: Update, context):
    chat_id = update.effective_chat.id
    
    if chat_id not in games or not games[chat_id].get('active'):
        await update.message.reply_text(f"{RED}🔴 ምንም ንቁ ጨዋታ የለም!{RED}", parse_mode='Markdown')
        return
    
    game = games[chat_id]
    
    if not game['players']:
        await update.message.reply_text(f"{YELLOW}🔴 ምንም ተጫዋቾች የሉም! መጀመሪያ ጨዋታውን ተቀላቀሉ{YELLOW}", parse_mode='Markdown')
        return
    
    available = [n for n in range(1, 76) if n not in game['called_numbers']]
    
    if not available:
        await update.message.reply_text(f"{RED}🔴 ሁሉም ቁጥሮች ተጠርተዋል! ጨዋታው አልቋል!{RED}", parse_mode='Markdown')
        game['active'] = False
        return
    
    number = random.choice(available)
    game['called_numbers'].append(number)
    
    message = f"{ORANGE}🔴 *ቁጥር {number} ተጠራ!* 🔴{ORANGE}\n"
    message += f"{BLUE}📊 የተጠሩ ቁጥሮች: {len(game['called_numbers'])}/75{BLUE}\n\n"
    
    # Check for winners
    winner = None
    for uid, player in game['players'].items():
        if player['has_bingo']:
            continue
        
        for card in player['cards']:
            if check_bingo(card, game['called_numbers']):
                player['has_bingo'] = True
                winner = uid
                break
        
        if winner:
            break
    
    if winner:
        prize = 200
        
        # ኮሚሽን ከሽልማት ላይ ብቻ ይቆረጣል!
        commission = calculate_commission(prize)
        net_prize = prize - commission
        
        if winner not in user_data:
            user_data[winner] = {'balance': 0, 'wins': 0, 'games_played': 0}
        
        user_data[winner]['balance'] += net_prize
        user_data[winner]['wins'] += 1
        user_data[winner]['games_played'] += 1
        user_data[winner]['total_commission'] = user_data[winner].get('total_commission', 0) + commission
        
        # ኮሚሽን ለአስተዳዳሪ መጨመር
        for admin_id in admin_ids:
            add_admin_commission(admin_id, commission)
        
        message += f"{RAINBOW}🎉 *ቢንጎ!* 🎉{RAINBOW}\n"
        message += f"{GREEN}🏆 አሸናፊ: {game['players'][winner]['username']}{GREEN}\n"
        message += f"{YELLOW}💰 ሽልማት: {prize} ብር{YELLOW}\n"
        message += f"{RED}📊 የተቆረጠ ኮሚሽን: {commission} ብር (ከዊን ብቻ!){RED}\n"
        message += f"{GREEN}💰 የተጨመረው: {net_prize} ብር{GREEN}\n"
        message += f"{RAINBOW}🎉 እንኳን ደስ ያለህ!{RAINBOW}"
        
        game['active'] = False
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def leaderboard(update: Update, context):
    if not user_data:
        await update.message.reply_text(f"{BLUE}📭 እስካሁን ምንም ተጫዋች የለም!{BLUE}", parse_mode='Markdown')
        return
    
    sorted_users = sorted(user_data.items(), key=lambda x: x[1]['wins'], reverse=True)[:10]
    
    message = f"{YELLOW}🏆 *ከፍተኛ አሸናፊዎች* 🏆{YELLOW}\n\n"
    for i, (uid, data) in enumerate(sorted_users, 1):
        if i == 1:
            medal = f"{GREEN}🥇{GREEN}"
        elif i == 2:
            medal = f"{BLUE}🥈{BLUE}"
        elif i == 3:
            medal = f"{ORANGE}🥉{ORANGE}"
        else:
            medal = f"{PURPLE}📌{PURPLE}"
        message += f"{medal} {i}. {data['username']}: *{data['wins']}* ድል(ዎች) | {data['balance']} ብር\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def stats(update: Update, context):
    user_id = update.effective_user.id
    
    if user_id not in user_data:
        user_data[user_id] = {'balance': 0, 'wins': 0, 'games_played': 0, 'username': update.effective_user.first_name}
    
    data = user_data[user_id]
    
    message = f"{BLUE}📊 *የ{data['username']} ስታቲስቲክስ* 📊{BLUE}\n\n"
    message += f"{GREEN}💰 ሂሳብ: {data['balance']} ብር{GREEN}\n"
    message += f"{YELLOW}🏆 ድሎች: {data['wins']}{YELLOW}\n"
    message += f"{PURPLE}🎮 የተጫወተው ጨዋታ: {data['games_played']}{PURPLE}\n"
    message += f"{RED}📊 ከዊን ላይ የተቆረጠ ኮሚሽን: {data.get('total_commission', 0)} ብር{RED}\n"
    message += f"{BLUE}📅 የተመዘገበ: {data.get('joined_at', 'አይታወቅም')}{BLUE}"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def mycard(update: Update, context):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if chat_id not in games:
        await update.message.reply_text(f"{RED}🔴 ምንም ንቁ ጨዋታ የለም!{RED}", parse_mode='Markdown')
        return
    
    if user_id not in games[chat_id]['players']:
        await update.message.reply_text(f"{YELLOW}🔴 ጨዋታውን አልተቀላቀልክም!{YELLOW}", parse_mode='Markdown')
        return
    
    player = games[chat_id]['players'][user_id]
    
    if not player['cards']:
        await update.message.reply_text(f"{PURPLE}🔴 እስካሁን ካርድ አልገዛህም! /buy ተጠቀም{PURPLE}", parse_mode='Markdown')
        return
    
    called = games[chat_id]['called_numbers']
    
    message = f"{RAINBOW}🃟 *{player['username']} ካርዶች* 🃟{RAINBOW}\n\n"
    
    for i, card in enumerate(player['cards'], 1):
        message += format_card(card, called, i)
        message += "\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def admin_menu(update: Update, context):
    user_id = update.effective_user.id
    
    if user_id not in admin_ids:
        await update.message.reply_text(f"{RED}❌ ይህ ትዕዛዝ ለአስተዳዳሪዎች ብቻ ነው!{RED}", parse_mode='Markdown')
        return
    
    total_commission = admin_commission.get(user_id, {}).get('total_commission', 0)
    transaction_count = len(admin_commission.get(user_id, {}).get('transactions', []))
    
    message = f"{YELLOW}👑 *የአስተዳዳሪ ሜኑ* 👑{YELLOW}\n\n"
    message += f"{GREEN}💰 ጠቅላላ ኮሚሽን (ከዊን ብቻ): {total_commission} ብር{GREEN}\n"
    message += f"{BLUE}📊 የግብይት ብዛት: {transaction_count}{BLUE}\n"
    message += f"{PURPLE}💡 1 ካርድ = 10 ብር (ኮሚሽን የለም){PURPLE}\n"
    message += f"{RED}💡 ከዊን ላይ ኮሚሽን: {COMMISSION_BIRR} ብር + {COMMISSION_PERCENT}%{RED}\n\n"
    message += f"{YELLOW}📝 ትዕዛዞች:{YELLOW}\n"
    message += f"{GREEN} /deposit <ብር> @username - ገንዘብ ማስገባት (ኮሚሽን የለም){GREEN}\n"
    message += f"{BLUE} /admin_commission - ኮሚሽን ሪፖርት ማየት{BLUE}\n"
    message += f"{RED} /admin_reset - ሁሉንም ውሂብ ማጥፋት (ጥንቃቄ!){RED}"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def admin_commission(update: Update, context):
    user_id = update.effective_user.id
    
    if user_id not in admin_ids:
        await update.message.reply_text(f"{RED}❌ ይህ ትዕዛዝ ለአስተዳዳሪዎች ብቻ ነው!{RED}", parse_mode='Markdown')
        return
    
    total_commission = admin_commission.get(user_id, {}).get('total_commission', 0)
    transactions = admin_commission.get(user_id, {}).get('transactions', [])[-10:]
    
    message = f"{GREEN}💰 *ኮሚሽን ሪፖርት* 💰{GREEN}\n\n"
    message += f"{YELLOW}📊 ጠቅላላ ኮሚሽን (ከዊን ብቻ): {total_commission} ብር{YELLOW}\n\n"
    
    if transactions:
        message += f"{BLUE}📝 የቅርብ ጊዜ ግብይቶች:{BLUE}\n"
        for t in transactions[-5:]:
            message += f"💸 {t['amount']} ብር - {t['date'][:16]}\n"
    else:
        message += f"{PURPLE}📭 እስካሁን ምንም ግብይት የለም!{PURPLE}"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def admin_reset(update: Update, context):
    user_id = update.effective_user.id
    
    if user_id not in admin_ids:
        await update.message.reply_text(f"{RED}❌ ይህ ትዕዛዝ ለአስተዳዳሪዎች ብቻ ነው!{RED}", parse_mode='Markdown')
        return
    
    user_data.clear()
    games.clear()
    admin_commission.clear()
    
    await update.message.reply_text(
        f"{RED}⚠️ *ሁሉም ውሂብ ተጠፍቷል!* ⚠️{RED}\n"
        f"{YELLOW}ተጠቃሚዎች፣ ጨዋታዎች እና ኮሚሽኖች ተሰርዘዋል!{YELLOW}",
        parse_mode='Markdown'
    )

async def help_command(update: Update, context):
    await update.message.reply_text(
        f"{RAINBOW}🌈 *የቢንጎ ቦት እርዳታ* 🌈{RAINBOW}\n\n"
        f"{GREEN}🎮 /newgame - አዲስ ጨዋታ መጀመር{GREEN}\n"
        f"{BLUE}🃟 /buy <ቁጥር> - ካርድ መግዛት (1-5 ካርድ){BLUE}\n"
        f"{ORANGE}🎲 /call - ቁጥር መጥራት{ORANGE}\n"
        f"{PURPLE}🃟 /mycard - ካርዶችህን ማየት{PURPLE}\n"
        f"{YELLOW}💰 /balance - ሂሳብህን ማየት{YELLOW}\n"
        f"{RED}🏆 /leaderboard - ከፍተኛ አሸናፊዎች{RED}\n"
        f"{BLUE}📊 /stats - ስታቲስቲክስህን ማየት{BLUE}\n\n"
        f"{GREEN}💡 1 ካርድ = 10 ብር (ኮሚሽን የለም){GREEN}\n"
        f"{RED}💡 ኮሚሽን የሚቆረጠው ከዊን ላይ ብቻ! {COMMISSION_BIRR} ብር + {COMMISSION_PERCENT}%{RED}\n"
        f"{YELLOW}🏆 ሽልማት: 200 ብር → ከዚህ ላይ ኮሚሽን ይቆረጣል{YELLOW}\n\n"
        f"{PURPLE}👑 /admin - ለአስተዳዳሪ ሜኑ (አስተዳዳሪ ብቻ){PURPLE}",
        parse_mode='Markdown'
    )

# ============ Main ============

def main():
    logger.info(f"{RAINBOW}🌈 ዋና ቢንጎ ቦት እየተነሳ ነው...{RAINBOW}")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("deposit", deposit))
    app.add_handler(CommandHandler("newgame", newgame))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(CommandHandler("call", call))
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("mycard", mycard))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("admin", admin_menu))
    app.add_handler(CommandHandler("admin_commission", admin_commission))
    app.add_handler(CommandHandler("admin_reset", admin_reset))
    
    # Callbacks
    app.add_handler(CallbackQueryHandler(join_game_callback, pattern='join_game'))
    
    logger.info(f"{GREEN}✅ ቢንጎ ቦት ተጀምሯል! 🎲{GREEN}")
    app.run_polling()

if __name__ == "__main__":
    main()
