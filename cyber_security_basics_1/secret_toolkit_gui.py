"""Secret Toolkit (GUI) - Caesar, ROT13, Base64, Hex and Binary in a small window.
Needs only Python (tkinter ships with it). Run: python secret_toolkit_gui.py
"""
import base64
import binascii
import os
import re
import tkinter as tk
from tkinter import ttk, filedialog

COMMON_WORDS = {
    "the", "be", "to", "of", "and", "a", "in", "that", "have", "i", "it", "for",
    "not", "on", "with", "he", "as", "you", "do", "at", "this", "but", "his",
    "by", "from", "they", "we", "say", "her", "she", "or", "an", "will", "my",
    "one", "all", "would", "there", "their", "what", "so", "up", "out", "if",
    "about", "who", "get", "which", "go", "me", "meet", "park", "tonight",
    "attack", "dawn", "at", "is", "are", "hello", "world", "secret", "message",
}

# Approximate English letter frequencies (percent)
ENGLISH_FREQ = {
    "a": 8.2, "b": 1.5, "c": 2.8, "d": 4.3, "e": 12.7, "f": 2.2, "g": 2.0,
    "h": 6.1, "i": 7.0, "j": 0.15, "k": 0.77, "l": 4.0, "m": 2.4, "n": 6.7,
    "o": 7.5, "p": 1.9, "q": 0.1, "r": 6.0, "s": 6.3, "t": 9.1, "u": 2.8,
    "v": 1.0, "w": 2.4, "x": 0.15, "y": 2.0, "z": 0.07,
}


# ---------- core logic ----------
def caesar(text, shift):
    out = []
    for ch in text:
        if ch.isalpha() and ch.isascii():
            base = ord("A") if ch.isupper() else ord("a")
            out.append(chr((ord(ch) - base + shift) % 26 + base))
        else:
            out.append(ch)
    return "".join(out)


def score(text):
    """Higher is more English-like: real words count most, letter frequency breaks ties."""
    words = sum(w.strip(".,!?;:'\"").lower() in COMMON_WORDS for w in text.split())
    letters = [c.lower() for c in text if c.isalpha() and c.isascii()]
    if not letters:
        return words * 10
    n = len(letters)
    chi = 0.0
    for letter, expected_pct in ENGLISH_FREQ.items():
        expected = n * expected_pct / 100
        chi += (letters.count(letter) - expected) ** 2 / expected
    return words * 10 - chi / 10


def crack(text):
    results = []
    for s in range(26):
        plain = caesar(text, -s)
        results.append((score(plain), s, plain))
    results.sort(reverse=True)
    lines = [f"Best guess (shift {results[0][1]}): {results[0][2]}"]
    letters = sum(c.isalpha() for c in text)
    if letters < 20:
        lines.append("")
        lines.append("Text is short, so here are other likely guesses:")
        for _, s, plain in results[1:5]:
            lines.append(f"  shift {s}: {plain}")
    return "\n".join(lines)


def hex_decode(t):
    try:
        return bytes.fromhex("".join(t.split())).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        raise ValueError("That is not valid hex. Expect digits like 4f6c6761.")


def bin_decode(t):
    try:
        parts = t.split()
        return bytes(int(p, 2) for p in parts).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        raise ValueError("That is not valid binary. Expect groups like 01001111.")


def b64_decode(t):
    try:
        return base64.b64decode("".join(t.split()), validate=True).decode("utf-8")
    except (binascii.Error, ValueError, UnicodeDecodeError):
        raise ValueError("That is not valid Base64.")


MORSE = {
    "A": ".-", "B": "-...", "C": "-.-.", "D": "-..", "E": ".", "F": "..-.",
    "G": "--.", "H": "....", "I": "..", "J": ".---", "K": "-.-", "L": ".-..",
    "M": "--", "N": "-.", "O": "---", "P": ".--.", "Q": "--.-", "R": ".-.",
    "S": "...", "T": "-", "U": "..-", "V": "...-", "W": ".--", "X": "-..-",
    "Y": "-.--", "Z": "--..",
    "0": "-----", "1": ".----", "2": "..---", "3": "...--", "4": "....-",
    "5": ".....", "6": "-....", "7": "--...", "8": "---..", "9": "----.",
    ".": ".-.-.-", ",": "--..--", "?": "..--..", "!": "-.-.--", "'": ".----.",
    ":": "---...", ";": "-.-.-.", "-": "-....-", "/": "-..-.",
}
MORSE_REVERSE = {code: ch for ch, code in MORSE.items()}


def morse_encode(text):
    """Letters are separated by a space and words by ' / '."""
    words = []
    for word in text.upper().split():
        codes = [MORSE[c] for c in word if c in MORSE]
        if codes:
            words.append(" ".join(codes))
    if not words:
        raise ValueError("Nothing to encode. Morse supports letters, digits and basic punctuation.")
    return " / ".join(words)


def morse_decode(text):
    # Accept common look-alike symbols for dot and dash
    t = text.strip()
    for dot in "•·":
        t = t.replace(dot, ".")
    for dash in "−–—_":
        t = t.replace(dash, "-")
    if not t or any(c not in ".- /|\n" for c in t):
        raise ValueError("That is not valid Morse. Use dots and dashes, a space between letters and / between words.")
    words = []
    for word in t.replace("|", "/").replace("\n", " / ").split("/"):
        letters = []
        for code in word.split():
            if code not in MORSE_REVERSE:
                raise ValueError(f"Unknown Morse code: {code}")
            letters.append(MORSE_REVERSE[code])
        if letters:
            words.append("".join(letters))
    return " ".join(words)


def looks_like_text(s):
    """True if s is mostly letters, digits, spaces and common punctuation."""
    if not s or not all(c.isprintable() or c in "\n\t" for c in s):
        return False
    good = sum(c.isalnum() or c in " .,!?'\"-:;\n" for c in s)
    return good / len(s) >= 0.85


def word_hits(s):
    return sum(w.strip(".,!?;:'\"").lower() in COMMON_WORDS for w in s.split())


def decode_chain(text, depth=3, path=()):
    """Try Base64, hex and binary, and keep going on the result (up to `depth` layers)."""
    found = []
    for name, fn in (("Base64", b64_decode), ("Hex", hex_decode), ("Binary", bin_decode),
                     ("Morse", morse_decode)):
        try:
            result = fn(text.strip())
        except ValueError:
            continue
        if result == text or not looks_like_text(result):
            continue
        steps = path + (name,)
        found.append((" → ".join(steps), result))
        if depth > 1:
            found += decode_chain(result, depth - 1, steps)
    return found


def decode_anything(text):
    found = decode_chain(text)
    # Caesar / ROT13: only report if the shifted text contains real English words
    best = max(range(1, 26), key=lambda s: word_hits(caesar(text, -s)))
    if word_hits(caesar(text, -best)) > 0 and word_hits(text) == 0:
        label = "ROT13" if best == 13 else f"Caesar (shift {best})"
        found.append((label, caesar(text, -best)))
    if not found:
        return "No encoding recognised.\nIt might be plain text, a Caesar cipher on a name\nor short text, or an encoding this toolkit doesn't know yet."
    return "\n\n".join(f"[{label}]\n{result}" for label, result in found)


# name -> (function, needs_shift)
OPERATIONS = {
    "Caesar encrypt": (lambda t, s: caesar(t, s), True),
    "Caesar decrypt": (lambda t, s: caesar(t, -s), True),
    "Caesar crack": (lambda t, s: crack(t), False),
    "ROT13": (lambda t, s: caesar(t, 13), False),
    "Base64 encode": (lambda t, s: base64.b64encode(t.encode()).decode(), False),
    "Base64 decode": (lambda t, s: b64_decode(t), False),
    "Hex encode": (lambda t, s: t.encode().hex(), False),
    "Hex decode": (lambda t, s: hex_decode(t), False),
    "Binary encode": (lambda t, s: " ".join(f"{b:08b}" for b in t.encode()), False),
    "Binary decode": (lambda t, s: bin_decode(t), False),
    "Morse encode": (lambda t, s: morse_encode(t), False),
    "Morse decode": (lambda t, s: morse_decode(t), False),
    "Decode anything": (lambda t, s: decode_anything(t), False),
}

# ---------- animals ----------
# Any of these words in a result is replaced by a picture. If animals/<name>.png (or .gif)
# exists next to this script, that picture is used; otherwise the emoji is shown.
ANIMALS = {
    "dog": "🐶", "puppy": "🐶", "cat": "🐱", "kitten": "🐱", "mouse": "🐭",
    "rabbit": "🐰", "bunny": "🐰", "hamster": "🐹", "fox": "🦊", "bear": "🐻",
    "panda": "🐼", "koala": "🐨", "tiger": "🐯", "lion": "🦁", "cow": "🐮",
    "pig": "🐷", "frog": "🐸", "monkey": "🐵", "chicken": "🐔", "penguin": "🐧",
    "bird": "🐦", "duck": "🦆", "eagle": "🦅", "owl": "🦉", "wolf": "🐺",
    "horse": "🐴", "unicorn": "🦄", "bee": "🐝", "butterfly": "🦋", "snail": "🐌",
    "ant": "🐜", "spider": "🕷", "turtle": "🐢", "snake": "🐍", "crocodile": "🐊",
    "fish": "🐟", "dolphin": "🐬", "whale": "🐳", "shark": "🦈", "octopus": "🐙",
    "crab": "🦀", "elephant": "🐘", "giraffe": "🦒", "zebra": "🦓", "camel": "🐫",
    "sheep": "🐑", "goat": "🐐", "deer": "🦌", "squirrel": "🐿", "hedgehog": "🦔",
    "goose": "🪿", "turkey": "🦃", "rat": "🐀", "dinosaur": "🦖",
}
IRREGULAR_PLURALS = {"mice": "mouse", "geese": "goose", "wolves": "wolf",
                     "butterflies": "butterfly", "puppies": "puppy"}
ANIMAL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "animals")
PICTURE_HEIGHT = 48  # pixels


def animal_for(word):
    """Return the animal name a word stands for (handles simple plurals), or None."""
    w = word.lower()
    if w in ANIMALS:
        return w
    if w in IRREGULAR_PLURALS:
        return IRREGULAR_PLURALS[w]
    for suffix in ("es", "s"):
        if w.endswith(suffix) and w[: -len(suffix)] in ANIMALS:
            return w[: -len(suffix)]
    return None


# ---------- GUI ----------
MAX_FILE_BYTES = 1024 * 1024  # 1 MB
BG, PANEL, FG = "#1e1e2e", "#2a2a3c", "#e6e6f0"
ACCENT, GOOD, BAD = "#b48ead", "#a3be8c", "#bf616a"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Secret Toolkit")
        self.result_text = ""      # plain text of the result (pictures excluded)
        self.animal_images = {}    # cache, also keeps Tk from discarding the pictures
        self.geometry("620x560")
        self.configure(bg=BG, padx=16, pady=14)
        self.minsize(520, 480)

        tk.Label(self, text="🔐 SECRET TOOLKIT", bg=BG, fg=ACCENT,
                 font=("Helvetica", 20, "bold")).pack(anchor="w")
        tk.Label(self, text="Encrypt, encode, decode and crack text",
                 bg=BG, fg="#8888a0").pack(anchor="w", pady=(0, 10))

        row = tk.Frame(self, bg=BG)
        row.pack(fill="x")
        tk.Label(row, text="Operation", bg=BG, fg=FG).pack(side="left")
        self.op = tk.StringVar(value="Caesar encrypt")
        box = ttk.Combobox(row, textvariable=self.op, values=list(OPERATIONS),
                           state="readonly", width=18)
        box.pack(side="left", padx=8)
        box.bind("<<ComboboxSelected>>", lambda e: self.update_shift_state())

        tk.Label(row, text="Shift", bg=BG, fg=FG).pack(side="left", padx=(12, 4))
        self.shift = tk.IntVar(value=3)
        self.shift_box = ttk.Spinbox(row, from_=0, to=25, width=5,
                                     textvariable=self.shift)
        self.shift_box.pack(side="left")

        src = tk.Frame(self, bg=BG)
        src.pack(fill="x", pady=(12, 2))
        tk.Label(src, text="Input from", bg=BG, fg=FG).pack(side="left")
        self.source = tk.StringVar(value="text")
        for label, value in (("Type text", "text"), ("Read a file", "file")):
            tk.Radiobutton(src, text=label, variable=self.source, value=value,
                           command=self.choose_source, bg=BG, fg=FG,
                           selectcolor=PANEL, activebackground=BG,
                           activeforeground=FG, highlightthickness=0
                           ).pack(side="left", padx=(8, 0))
        self.file_label = tk.Label(src, text="", bg=BG, fg="#8888a0")
        self.file_label.pack(side="left", padx=10)
        self.inp = tk.Text(self, height=7, bg=PANEL, fg=FG, insertbackground=FG,
                           relief="flat", wrap="word", padx=8, pady=6)
        self.inp.pack(fill="x")

        btns = tk.Frame(self, bg=BG)
        btns.pack(fill="x", pady=10)
        self.button(btns, "Run ▶", self.run, ACCENT).pack(side="left")
        self.button(btns, "Swap ⇅", self.swap, PANEL).pack(side="left", padx=6)
        self.button(btns, "Copy", self.copy, PANEL).pack(side="left")
        self.button(btns, "Clear", self.clear, PANEL).pack(side="left", padx=6)

        tk.Label(self, text="Result", bg=BG, fg=FG).pack(anchor="w", pady=(0, 2))
        self.out = tk.Text(self, height=9, bg=PANEL, fg=GOOD, relief="flat",
                           wrap="word", padx=8, pady=6, state="disabled")
        self.out.pack(fill="both", expand=True)
        self.out.tag_configure("emoji", font=("Helvetica", 24))

        self.update_shift_state()
        self.bind("<Control-Return>", lambda e: self.run())

    def button(self, parent, text, cmd, color):
        return tk.Button(parent, text=text, command=cmd, bg=color, fg="white",
                         activebackground=color, relief="flat", padx=14, pady=5,
                         cursor="hand2")

    def update_shift_state(self):
        needs = OPERATIONS[self.op.get()][1]
        self.shift_box.configure(state="normal" if needs else "disabled")

    def choose_source(self):
        if self.source.get() == "file":
            self.open_file()
        else:
            self.file_label.configure(text="")
            self.inp.focus_set()

    def open_file(self):
        path = filedialog.askopenfilename(
            title="Choose a text file",
            filetypes=[("Text files", "*.txt *.md *.csv *.log"), ("All files", "*.*")])
        if not path:  # cancelled: go back to typing
            self.source.set("text")
            return
        try:
            with open(path, "rb") as f:
                data = f.read(MAX_FILE_BYTES + 1)
        except OSError as err:
            self.source.set("text")
            self.show(f"✖ Could not read the file: {err.strerror or err}", ok=False)
            return
        if len(data) > MAX_FILE_BYTES:
            self.source.set("text")
            self.show(f"✖ File is too large (limit {MAX_FILE_BYTES // 1024} KB).", ok=False)
            return
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = data.decode("latin-1")
        self.inp.delete("1.0", "end")
        self.inp.insert("1.0", text)
        self.file_label.configure(text=f"📄 {os.path.basename(path)}")
        self.show("")

    def show(self, text, ok=True):
        self.out.configure(state="normal", fg=GOOD if ok else BAD)
        self.out.delete("1.0", "end")
        self.result_text = text
        if ok:
            self.insert_with_animals(text)
        else:
            self.out.insert("1.0", text)
        self.out.configure(state="disabled")

    def animal_image(self, name):
        """Load animals/<name>.png or .gif, scaled down to about PICTURE_HEIGHT. None if absent."""
        if name not in self.animal_images:
            image = None
            for ext in (".png", ".gif"):
                path = os.path.join(ANIMAL_DIR, name + ext)
                if os.path.isfile(path):
                    try:
                        image = tk.PhotoImage(file=path)
                        factor = max(1, round(image.height() / PICTURE_HEIGHT))
                        if factor > 1:
                            image = image.subsample(factor)
                        break
                    except tk.TclError:
                        image = None
            self.animal_images[name] = image
        return self.animal_images[name]

    def insert_with_animals(self, text):
        pos = 0
        for m in re.finditer(r"[A-Za-z]+", text):
            name = animal_for(m.group())
            if not name:
                continue
            self.out.insert("end", text[pos:m.start()])
            image = self.animal_image(name)
            if image:
                self.out.image_create("end", image=image, padx=2)
            else:
                self.out.insert("end", ANIMALS[name], "emoji")
            pos = m.end()
        self.out.insert("end", text[pos:])

    def run(self):
        text = self.inp.get("1.0", "end").rstrip("\n")
        if not text:
            self.show("✖ Please enter some text first.", ok=False)
            return
        func, needs_shift = OPERATIONS[self.op.get()]
        try:
            shift = int(self.shift.get()) if needs_shift else 0
        except (tk.TclError, ValueError):
            self.show("✖ Shift must be a whole number.", ok=False)
            return
        try:
            self.show(func(text, shift))
        except ValueError as err:
            self.show(f"✖ {err}", ok=False)

    def swap(self):
        result = self.result_text
        if result and not result.startswith("✖"):
            self.inp.delete("1.0", "end")
            self.inp.insert("1.0", result)

    def copy(self):
        self.clipboard_clear()
        self.clipboard_append(self.result_text)

    def clear(self):
        self.source.set("text")
        self.file_label.configure(text="")
        self.inp.delete("1.0", "end")
        self.show("")


if __name__ == "__main__":
    App().mainloop()
