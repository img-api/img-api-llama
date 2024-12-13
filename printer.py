

def print_e(text):
    print(Back.RED + line_80)
    print(Back.RED + text.center(80))
    print(Back.RED + line_80)


def print_json(json_in):
    print_b(json.dumps(json_in, indent=4))

def print_b(text):
    print(Fore.LIGHTBLUE_EX + text)


def print_g(text, in_place=False):
    print(Fore.GREEN + text, end="\r" if in_place else "\n", flush=in_place)


def print_r(text, in_place=False):
    print(Fore.RED + text, end="\r" if in_place else "\n", flush=in_place)


line_80 = (
    "--------------------------------------------------------------------------------"
)


def print_h(text):
    print(Back.GREEN + Fore.BLUE + line_80)
    print(Back.GREEN + Fore.BLUE + text.center(80))
    print(Back.GREEN + Fore.BLUE + line_80)
    print("\n")


def print_exception(err, text=""):
    import traceback

    print(Fore.RED + str(err))
    traceback.print_tb(err.__traceback__)

