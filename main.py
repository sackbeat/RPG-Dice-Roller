import random
import os
import json
from datetime import datetime
from colorama import Fore, Style, init
from pyfiglet import Figlet

init(autoreset=True)

# --- FILES ---
DATA_FILE = "data.json"
CHAR_FILE = "character.json"
SAVE_FILE = "session_history.json"

# --- LOAD DATA ---
def load_data():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

DATA = load_data()
ENCOUNTERS = DATA["encounters"]
CRIT_HIT = DATA["critical_hit"]
CRIT_FAIL = DATA["critical_fail"]

# --- GLOBALS ---
history = {"rolls": [], "encounters": []}
luck_history = []
PLAYER = {}  # Active character

# ==============================
#      UTILITY FUNCTIONS
# ==============================
def banner(text):
    print(Fore.CYAN + Figlet(font="slant").renderText(text))

def color_text(text, color):
    return getattr(Fore, color.upper(), Fore.WHITE) + text + Style.RESET_ALL

def save_history():
    with open(SAVE_FILE, "w") as f:
        json.dump({"history": history, "luck": luck_history}, f, indent=2)
    print(Fore.GREEN + "Session saved.\n")

def load_history():
    global history, luck_history
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r") as f:
            data = json.load(f)
            history = data.get("history", {"rolls": [], "encounters": []})
            luck_history = data.get("luck", [])
        print(Fore.GREEN + "Previous session loaded.\n")

# ==============================
#       CHARACTER SYSTEM
# ==============================
def create_character():
    global PLAYER
    print(Fore.CYAN + "\n--- Create New Character ---")
    name = input("Character name: ").strip()
    if not name:
        print(Fore.RED + "Name cannot be empty!\n")
        return create_character()

    print("Assign stats manually or roll randomly? (type 'manual' or 'roll')")
    choice = input("> ").strip().lower()
    stats = {}
    for stat in ["STR", "DEX", "CON", "INT", "WIS", "CHA"]:
        if choice == "manual":
            while True:
                try:
                    val = int(input(f"Assign {stat} (0-5): "))
                    if 0 <= val <= 5:
                        stats[stat] = val
                        break
                except:
                    pass
                print("Invalid. Enter a number 0-5.")
        else:  # roll
            stats[stat] = random.randint(0, 5)
            print(f"{stat}: {stats[stat]}")
    PLAYER = {"name": name, "stats": stats}
    with open(CHAR_FILE, "w") as f:
        json.dump(PLAYER, f, indent=2)
    print(Fore.GREEN + f"Character '{name}' created and saved!\n")

def load_character():
    global PLAYER
    if not os.path.exists(CHAR_FILE):
        print(Fore.YELLOW + "No saved character found. Creating one...\n")
        create_character()
    else:
        with open(CHAR_FILE, "r") as f:
            PLAYER = json.load(f)
        print(Fore.GREEN + f"Loaded character '{PLAYER['name']}'\n")

# ==============================
#       DICE & STATS
# ==============================
def roll_dice(num_dice, dice_sides, modifier=0, advantage=None):
    rolls = []
    for _ in range(num_dice):
        r1 = random.randint(1, dice_sides)
        r2 = random.randint(1, dice_sides) if advantage else r1
        roll = max(r1, r2) if advantage == "adv" else min(r1, r2) if advantage == "dis" else r1
        rolls.append(roll)
    total = sum(rolls) + modifier

    flavor = ""
    if dice_sides == 20:
        if 20 in rolls:
            flavor = Fore.YELLOW + random.choice(CRIT_HIT)
        elif 1 in rolls:
            flavor = Fore.RED + random.choice(CRIT_FAIL)

    print(f"{Fore.CYAN}Rolls: {rolls} | Mod: {modifier:+d} | Total: {Fore.GREEN}{total}{Style.RESET_ALL}")
    if flavor:
        print(flavor)

    history["rolls"].append({"dice": f"{num_dice}d{dice_sides}", "mod": modifier, "result": total})
    return total

def roll_from_input(user_input):
    parts = user_input.lower().split()
    dice_part = parts[0]
    advantage = "adv" if "adv" in parts else "dis" if "dis" in parts else None
    modifier = 0
    try:
        num_dice, rest = dice_part.split("d")
        num_dice = int(num_dice)
        if "+" in rest:
            dice_sides, mod = rest.split("+"); modifier = int(mod)
        elif "-" in rest:
            dice_sides, mod = rest.split("-"); modifier = -int(mod)
        else:
            dice_sides = rest
        dice_sides = int(dice_sides)
    except Exception:
        print(Fore.RED + "Invalid format! Example: 2d6+3 adv\n"); return None
    return roll_dice(num_dice, dice_sides, modifier, advantage)

def stat_check(stat):
    stat = stat.upper()
    if stat not in PLAYER["stats"]:
        print(Fore.RED + f"Unknown stat '{stat}'.\n"); return
    mod = PLAYER["stats"][stat]
    print(Fore.MAGENTA + f"Rolling {stat} check (+{mod})")
    roll_dice(1, 20, mod)

# ==============================
#       ENCOUNTER SYSTEM
# ==============================
def generate_encounter():
    print(Fore.CYAN + "Locations: " + ", ".join(ENCOUNTERS.keys()))
    loc = input("Location: ").strip().lower()
    if loc not in ENCOUNTERS:
        print(Fore.RED + "Invalid location.\n"); return
    print(Fore.CYAN + "Difficulty: easy / normal / hard")
    diff = input("Difficulty: ").strip().lower()
    if diff not in ENCOUNTERS[loc]:
        print(Fore.RED + "Invalid difficulty.\n"); return

    avg_luck = sum(luck_history[-5:]) / len(luck_history[-5:]) if luck_history[-5:] else 50
    if avg_luck > 70 and diff == "easy": diff = "normal"
    elif avg_luck < 30 and diff == "hard": diff = "normal"

    encounter = random.choice(ENCOUNTERS[loc][diff])
    color = "GREEN" if diff == "easy" else "YELLOW" if diff == "normal" else "RED"
    print(color_text(f"Encounter! {encounter} ({diff.title()})", color))
    result = roll_dice(1, 20)
    success = "Success" if result >= 10 else "Fail"
    print(Fore.CYAN + f"Outcome: {success}\n")

    history["encounters"].append({
        "location": loc, "difficulty": diff, "enemy": encounter,
        "result": success, "time": datetime.now().strftime("%H:%M:%S")
    })
    luck_history.append((result / 20) * 100)

# ==============================
#       INITIATIVE & SUMMARY
# ==============================
def initiative_tracker():
    print(Fore.CYAN + "\nEnter names separated by commas:")
    participants = [p.strip() for p in input("Participants: ").split(",") if p.strip()]
    if not participants:
        print(Fore.RED + "No participants.\n"); return
    rolls = {p: random.randint(1, 20) for p in participants}
    ordered = sorted(rolls.items(), key=lambda x: x[1], reverse=True)
    print(Fore.YELLOW + "\n--- Initiative Order ---")
    for p, r in ordered:
        print(f"{p}: {r}")

def session_summary():
    print(Fore.YELLOW + "\n--- SESSION SUMMARY ---")
    print(f"Character: {PLAYER['name']}")
    print(f"Rolls: {len(history['rolls'])} | Encounters: {len(history['encounters'])}")
    if luck_history:
        avg = sum(luck_history) / len(luck_history)
        trend = "📈" if len(luck_history) > 1 and luck_history[-1] > luck_history[-2] else "📉"
        print(f"Average Luck: {avg:.1f}% {trend}")
    print("-" * 30)

# ==============================
#       MENUS
# ==============================
def main_menu():
    while True:
        banner("RPG Dice Roller")
        print(Fore.CYAN + """
1. Roll Dice
2. Stat Check
3. Generate Encounter
4. Initiative Tracker
5. Session Summary
6. Command Mode
7. Save & Quit
""")
        choice = input(Fore.YELLOW + "Choose: ").strip()
        if choice == "1":
            roll_from_input(input("Dice (e.g. 2d6+3 adv): "))
        elif choice == "2":
            stat_check(input("Stat (STR, DEX, CON, INT, WIS, CHA): "))
        elif choice == "3":
            generate_encounter()
        elif choice == "4":
            initiative_tracker()
        elif choice == "5":
            session_summary()
        elif choice == "6":
            command_mode()
        elif choice == "7":
            save_history(); print(Fore.MAGENTA + "Goodbye adventurer!\n"); break
        else:
            print(Fore.RED + "Invalid.\n")

def command_mode():
    print(Fore.CYAN + "\nCommand Mode ('help' for options, 'menu' to return)\n")
    while True:
        cmd = input("> ").strip().lower()
        if cmd in ["q", "quit", "exit"]:
            save_history(); print(Fore.MAGENTA + "Session saved. Farewell!\n"); break
        elif cmd == "menu": return
        elif cmd.startswith("roll "): roll_from_input(cmd.replace("roll ", ""))
        elif cmd.startswith("check "): stat_check(cmd.replace("check ", ""))
        elif cmd.startswith("enc"): generate_encounter()
        elif cmd == "sum": session_summary()
        elif cmd == "init": initiative_tracker()
        elif cmd == "help":
            print(Fore.YELLOW + "Commands: roll 2d6+3 | check str | enc | sum | init | menu | quit\n")
        else:
            print(Fore.RED + "Unknown command.\n")

# ==============================
#           MAIN
# ==============================
if __name__ == "__main__":
    load_character()
    load_history()
    main_menu()
