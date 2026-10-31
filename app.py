# Kindle Calendar App v1.2.0

""" 
 v1.2.0 updates include:
 - editable settings
 - automatic '/' between date elements
 - abbreviated days of week
 - help menu
 - smaller defualt text


Future Updates:
 - support for ANSI characters (ex: arrow keys)
 - run app directly from kindle library
 - directly edit events
 - automatic holiday population
 - automatic capitalization
 - customizable text size
"""


import csv
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta


DATE_FORMAT = "%y/%m/%d"
DISPLAY_FORMAT = "%y/%m/%d"

DATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "events.csv")
SETTINGS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")

# change so the path is called with a paramater - dont have to have multiple paths?
ABOUT_HELP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "help", "about.txt")
MAIN_HELP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "help", "main.txt")
OTHER_HELP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "help", "other.txt")


# === Event Helpers ===

def display_date(date_str):
    return datetime.strptime(date_str, DATE_FORMAT).strftime(DISPLAY_FORMAT)
    
def menu_event_stored(event_number):
    if event_number == 1:
        return("1 event currently stored.")
    elif event_number == 0:
        return("0 events currently stored. Start by entering '2' then pressing 'Enter' to create an event!")
    else:
        return(f"{event_number} events currently stored.")

# === DATE CSV Backend ===

def _ensure_csv_date():
    if not os.path.exists(DATE_PATH):
        with open(DATE_PATH, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["date", "event_name"])

def load_events():
    _ensure_csv_date()
    with open(DATE_PATH, "r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def save_events(events):
    _ensure_csv_date()
    with open(DATE_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["date", "event_name"])
        w.writeheader()
        w.writerows(events)

def add_event(date, event_name):
    events = load_events() 
    events.append({"date": date, "event_name": event_name})
    save_events(events)

def get_events_on_date(date):
    return [e["event_name"] for e in load_events() if e["date"] == date]

def get_events_in_range(start_date, num_extra_days):
    try:
        base = datetime.strptime(start_date, DATE_FORMAT)
    except ValueError:
        return []
    results = []
    for i in range(num_extra_days + 1):
        d = (base + timedelta(days=i)).strftime(DATE_FORMAT)
        for name in get_events_on_date(d):
            results.append((d, name))
    return results

def delete_event(date, event_name):
    events = load_events()
    for i, e in enumerate(events):
        if e["date"] == date and e["event_name"] == event_name:
            events.pop(i)
            save_events(events)
            return True
    return False

def search_events(term, include_past=False):
    tl = term.lower()
    today = datetime.now().date()
    matches = []
    for e in load_events():
        try:
            event_date = datetime.strptime(e["date"], DATE_FORMAT).date()
        except ValueError:
            continue
        if not include_past and event_date < today:
            continue
        if tl in e["event_name"].lower():
            matches.append((e["date"], e["event_name"]))
    matches.sort(key=lambda x: x[0])
    return matches

# === SETTINGS json Backend ===

def load_settings(setting):
    with open(SETTINGS_PATH, "r", newline="", encoding="utf-8") as f:
        return list(json.load(f)[setting].items())[::2]

def load_configs(setting, config):
    with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)[setting][config + "_Options"]
    
# === Setting Helpers ===

def format_settings(settings_list):
    sl = settings_list
    formatted_list = ""
    
    for item in sl:
        formatted_list += str(item[0]) + ": " + str(item[1]) + " | "
            
    return str("|"+formatted_list)

def display_current_settings(setting):
    settings_list = load_settings(setting)
    return format_settings(settings_list)

def check_setting_active(setting):
    return load_settings(setting)[0]

def check_config(setting):    
    return load_settings(setting)[1]

# === Input parsers ===

def validate_date(text):
    try:
        datetime.strptime(text.strip(), DATE_FORMAT)
        return True
    except ValueError:
        return False

def parse_enter_event(text):
    parts = text.split(",", 1)
    if len(parts) != 2:
        return None
    date_part, name_part = parts[0].strip(), parts[1].strip()
    if not validate_date(date_part) or not name_part:
        return None
    return date_part, name_part

def parse_retrieve(text):
    parts = text.split(",", 1)
    if len(parts) == 1:
        date_part = parts[0].strip()
        days = 0
    else:
        date_part, days_part = parts[0].strip(), parts[1].strip()
        try:
            days = int(days_part)
            if days < 0:
                return None
        except ValueError:
            return None
    if not validate_date(date_part):
        return None
    return date_part, days

def check_double_enter(text, previous_empty):
    if text == "":
        if previous_empty:
            return True, False
        return False, True
    return False, False

def parse_search(text):
    parts = text.split(",", 1)
    term = parts[0].strip()
    if not term:
        return None
    if len(parts) == 1:
        return term, False
    answer = parts[1].strip().lower()
    if answer not in ("y", "n"):
        return None
    return term, (answer == "y")

# === Setting Functions ===

def setting_slash_input():
    import tty
    import termios
    text = ""
    print("> ", end="", flush=True)
    while True:
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        
        if ch == "\r" or ch == "\n":
            print("")
            return text
        elif ch == "\x7f":
            if text:
                text = text[:-1]
                print(f"\r> {text} ", end="", flush=True)
                print(f"\r> {text}", end="", flush=True)
        else:
            text += ch
            if len(text) == 2 or len(text) == 5:
                text += "/"
            print(f"\r> {text}", end="", flush=True)
            

def setting_days_of_week(date_str):
    week_list = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    short_list = ["M", "T", "W", "R", "F", "S", "Y"]
    day_length = int(check_config("Days of the Week")[1])
    if check_setting_active("Days of the Week")[1] == "yes":
        week_day = datetime.strptime(date_str, DATE_FORMAT).weekday()
            
        if day_length > 1:
            return (f" {str((week_list[week_day])[:day_length])}")
        else:
            return (f" {str((short_list[week_day])[:day_length])}")
    else:
        return ""        
  
  
# === Main Menu Actions ===

def action_today_events():
    print("= Today's Events =")
    today = datetime.now().strftime(DATE_FORMAT)
    events = get_events_on_date(today)
    if not events:
        print(f"No events found for today{setting_days_of_week(today)} {display_date(today)}.")
    else:
        print(f"Events for today{setting_days_of_week(today)} {display_date(today)}:")
        for i, name in enumerate(events, start=1):
            print(f"  {i}. {name}")
    print("\nPress Enter to return to the main menu.")
    input()

def action_enter_event():
    print("= Enter Event =")
    print("Format: yy/mm/dd, event name")
    previous_empty = False
    while True:
        if check_setting_active("Automatic Slashes")[1] == "yes":
            text = setting_slash_input()
        else:
            text = input("> ").strip()
            
        canceled, previous_empty = check_double_enter(text, previous_empty)
        if canceled:
            print("Successfully canceled.")
            return
        if text == "":
            continue
        parsed = parse_enter_event(text)
        if parsed is None:
            print("Please try again with: yy/mm/dd, event name")
            continue
        date_str, event_name = parsed
        add_event(date_str, event_name)
        print(f"Event entered: '{event_name}' on{setting_days_of_week(date_str)} {display_date(date_str)}")
        return

def action_retrieve():
    print("= Retrieve Events =")
    print("Format: yy/mm/dd, number of days after date to include")
    previous_empty = False
    
    while True:
        if check_setting_active("Automatic Slashes")[1] == "yes":
            text=setting_slash_input()
        else:
            text = input("> ").strip()           
            
        canceled, previous_empty = check_double_enter(text, previous_empty)
        if canceled:
            print("Successfully canceled.")
            return
        if text == "":
            continue
        parsed = parse_retrieve(text)
        if parsed is None:
            print("Please try again with: yy/mm/dd, number of days")
            continue
        date_str, num_days = parsed
        results = get_events_in_range(date_str, num_days)
        print(results)
        if not results:
            end_date = (
                datetime.strptime(date_str, DATE_FORMAT) + timedelta(days=num_days)
            ).strftime(DATE_FORMAT)
            print(f"No events found between{setting_days_of_week(date_str)} {display_date(date_str)} and {setting_days_of_week(end_date)} {display_date(end_date)}.")
        else:
            print("Event(s) found:")
            for i, name in results:
                print(f"  {i} -{setting_days_of_week((results[i])[0])} {name}")
        print("\nPress Enter to return to the main menu.")
        input()
        return

def action_delete():
    print("= Delete Events =")
    print("Format: yy/mm/dd")
    print("")
    previous_empty = False
    while True:
        if check_setting_active("Automatic Slashes")[1] == "yes":
            text=setting_slash_input()
        else:
            text = input("> ").strip()
            
        canceled, previous_empty = check_double_enter(text, previous_empty)
        if canceled:
            print("Successfully canceled.")
            return
        if text == "":
            continue
        if not validate_date(text):
            print("Please try again with: yy/mm/dd")
            continue
        events_on_day = get_events_on_date(text)
        if not events_on_day:
            print(f"No events found on{setting_days_of_week(date_str)} {text}.")
            return
        date_str = text
        print(f"Events on {date_str}:")
        for i, name in enumerate(events_on_day, start=1):
            print(f"  {i}. {name}")
        if len(events_on_day) == 1:
            print("Do you want to delete this event?")
            print("Format: 1 to accept or double enter to exit.")
        else:
            print("Which event would you like to delete?")
            print(f"Format: number between 1 and {len(events_on_day)}.")
        while True:
            choice = input("> ").strip()
            canceled, previous_empty = check_double_enter(choice, previous_empty)
            if canceled:
                print("Successfully canceled.")
                return
            if choice == "":
                continue
            if not choice.isdigit() and len(events_on_day) != 1:
                print(f"Please enter a number between 1 and {len(events_on_day)}.")
                continue
            if not choice.isdigit() and len(events_on_day) ==1:
                print("Please type 1 or double enter to exit")
                continue

            index = int(choice)
            if index != 1 and len(events_on_day) == 1:
                print("Please type 1 or double enter to exit.")
                continue
            elif index < 1 or index > len(events_on_day):
                print(f"Please enter a number between 1 and {len(events_on_day)}.")
                continue
            event_name = events_on_day[index - 1]
            delete_event(date_str, event_name)
            print(f"'{event_name}' on{setting_days_of_week(today)} {date_str} deleted.")
            return

def action_search():
    print("= Search Events =")
    print("Format: search term, include past events? y/n")
    previous_empty = False
    while True:
        text = input("> ").strip()
        canceled, previous_empty = check_double_enter(text, previous_empty)
        if canceled:
            print("Successfully canceled.")
            return
        if text == "":
            continue
        parsed = parse_search(text)
        if parsed is None:
            print("Please try again with: search term, y/n")
            continue
        term, include_past = parsed
        matches = search_events(term, include_past)
        if not matches:
            if include_past:
                print(f"No events found containing '{term}'.")
            else:
                print(f"No upcoming events found containing '{term}'.")
        else:
            print("Search results:")
            for i, (d, name) in enumerate(matches, start=1):
                print(f"  {i}.{setting_days_of_week(d)} {display_date(d)} - {name}")
            print(f"{len(matches)} result(s) found.")
        print("\nPress Enter to return to the main menu.")
        input()
        return

# === Other Actions Menu ===

def print_other_menu():
   print("")
   print(" === Other Actions Menu ===")
   print("  1. Exit to Kindle Home")
   print("  2. Help")
   print("  3. Settings")
   print("  4. Back to Main Menu")
   
   actions = {
        "1": action_exit,
        "2": print_help_menu,
        "3": print_settings_menu,
        "4": action_back,
   }
   while True:
        choice = input("> ").strip()
        if choice in actions:
            print("")
            actions[choice]()
        else:
            print(f"Please enter a number 1-{len(actions)}.")

# === Other Menu Actions ===

def action_exit():
    print("= Exit to Kindle =")
    print("Kindle will return home in a few seconds.")
    print("Press Enter to cancel.")
    start = time.time()
    while time.time() - start < 2:
        import select
        if select.select([sys.stdin], [], [], 0.1)[0]:
            input()
            print("Successfully canceled.")
            print_other_menu()
            return
    os.system("lipc-set-prop com.lab126.appmgrd start app://com.lab126.booklet.home")
    sys.exit(0)

def print_help_menu():
    print("")
    print("= Help Menu =")
    print(" 1. Exit to Other Actions Menu")
    print(" 2. About Kindle Calendar")
    print(" 3. Main Actions Help")
    print(" 4. Other Actions Help")
    
    actions = {
        "1": action_exit_help,
        "2": lambda: print_help(ABOUT_HELP_PATH),
        "3": lambda: print_help(MAIN_HELP_PATH),
        "4": lambda: print_help(OTHER_HELP_PATH)
    }
    
    while True:
        choice = input("> ").strip()
        if choice in actions:
            print("")
            actions[choice]()
        else:
            print(f"Please enter a number 1-{len(actions)}.")    
    
def print_help(path):
    with open(path, "r", newline="", encoding="utf-8") as f:
        print(f"{f.read()}")
        print("")
        print("Press Enter to return to the help menu.")
        while True:
            input("> ").strip()
            print_help_menu()
            f.close()
            return

def action_exit_help():
    while True:
        print_other_menu()
        return    
    
    
def action_back():
    for i in range(0,35):
        print("■■■■■■■■■■■■■■■■■■■■■■■")

    os.system('clear')
    main()
    return

# === Settings Menu ===

def print_settings_menu():
   print(" === Settings Menu ===")
   print("  1. Exit to Other Actions Menu")
   print("  2. Abbr. Days of the Week")
   print(f"{display_current_settings('Days of the Week')}")
   print("  3. Automatic Slashes")
   print(f"{display_current_settings('Automatic Slashes')}")
   
   actions = {
        "1": action_exit_settings,
        "2": lambda: print_edit_menu("Days of the Week"),
        "3": lambda: print_edit_menu("Automatic Slashes"),
   }
   while True:
        choice = input("> ").strip()
        if choice in actions:
            print("")   
            actions[choice]()
        else:
            print(f"Please enter a number 1-{len(actions)}.")
            

def action_exit_settings():
    while True:
        print_other_menu()
        return


# === Edit Settings Menu ===

def print_edit_menu(setting):
    print(f"Settings for {setting}.")
    
    settings_list = load_settings(setting)
    sl = settings_list
    formatted_list = ""
    j = 1
    
    for i in range(0, len(sl)):
            formatted_list += str(j) + ". " + str(sl[i][0]) + ": "
            formatted_list += str(sl[i][1])
            print(formatted_list)
            formatted_list = ""
            j += 1

    actions = {}
    for i in range(0, len(sl)):
        actions[str(i + 1)] = lambda i=i: action_edit_setting(setting, sl[i][0])
        
    actions[str(len(sl) + 1)] = action_exit_edit
    print(f"{len(sl)+1}. Exit to Settings Menu")
    
    while True:
        choice = input("> ").strip()
        if choice in actions:
            print("")
            actions[choice]()
        else:
            print(f"Please enter a number 1-{len(actions)}.")
           
    
def action_exit_edit():
    while True:
        print_settings_menu()
        return


# === Edit Actions ===

def action_edit_setting(setting,config):
    print(f"Editing {config} in {setting}")
    cl = load_configs(setting,config)
    
    if type(cl[0]) is int:
        print(f"Choose a number between {cl[0]} and {cl[1]}")
        
        actions = {}
        for i in range(cl[0], cl[1]+1):
            actions[str(i)] = i
    
        actions[str(cl[1]+1)] = "exit"       
        print(f"{cl[1]+1}. Exit to Settings Menu")
        
        
    else:
    
        for i in range(0,len(cl)):
            print(f"{i+1}. {cl[i]}")
        
        actions = {}
        for i in range(0, len(cl)):
            actions[str(i + 1)] = cl[i]  
        actions[str(len(cl) + 1)] = "exit"
        print(f"{len(cl)+1}. Exit to Settings Menu")

    while True:
        choice = input("> ").strip()
        if choice not in actions:
            print(f"Please enter a number 1-{len(actions)}.")
        elif actions[choice] == "exit":
            print("Successfully exited")
            print("")
            print_edit_menu(setting)
            return
        else:
            settings = json.load(open(SETTINGS_PATH, "r", encoding="utf-8"))
            settings[setting][config] = actions[choice]
            json.dump(settings, open(SETTINGS_PATH, "w", encoding="utf-8"), indent=4)
             
            print("")
            print_edit_menu(setting)
            return
    

# === Main loop ===

def print_menu(today):
    print("")
    print(f"=== Calendar{setting_days_of_week(today)} {display_date(today)}===")
    print("  1. Today's Events")
    print("  2. Enter Event")
    print("  3. Retrieve Events")
    print("  4. Search Events")
    print("  5. Delete Event")
    print("  6. Other Actions")
    print("")

def main():
    _ensure_csv_date()
    print("Welcome to Your Kindle Calendar :)")
    today = datetime.now().strftime(DATE_FORMAT)
    print(f"{menu_event_stored(len(load_events()))}")
    print("")
    print("Press Enter twice anytime to return to the main menu.")
    actions = {
        "1": action_today_events,
        "2": action_enter_event,
        "3": action_retrieve,
        "4": action_search,
        "5": action_delete,
        "6": print_other_menu,
    }
    while True:
        print_menu(today)
        choice = input("> ").strip()
        if choice in actions:
            print("")
            actions[choice]()
        else:
            print(f"Please enter a number 1-{len(actions)}.")


if __name__ == "__main__":
    main()
