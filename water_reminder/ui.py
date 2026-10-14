import math
import tkinter as tk
from collections.abc import Callable
from dataclasses import replace
from tkinter import messagebox, ttk

from .config import Settings
from .paths import resource_directory


def remaining_text(seconds: float) -> str:
    minutes, seconds_left = divmod(math.ceil(seconds), 60)
    return f"{minutes} min {seconds_left:02d} s"


class SettingsDialog:
    def __init__(
        self,
        root: tk.Tk,
        settings: Settings,
        save: Callable[[Settings], None],
        closed: Callable[[], None],
        status: Callable[[], str],
        first_run: bool = False,
        focus: str = "name",
    ) -> None:
        self.save = save
        self.closed = closed
        self.settings = settings
        self.window = tk.Toplevel(root)
        self.window.title("Bienvenue dans Water Reminder" if first_run else "Water Reminder")
        self.window.resizable(False, False)
        self.window.configure(background="#f3f8fc")
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.window.iconbitmap(str(resource_directory() / "water.ico"))
        self.name = tk.StringVar(value="" if first_run else settings.name)
        self.interval = tk.StringVar(value=str(settings.interval_minutes))
        self.autostart = tk.BooleanVar(value=settings.autostart)
        self.status = tk.StringVar(value=status())
        content = ttk.Frame(self.window, padding=28)
        content.grid(sticky="nsew")
        ttk.Label(content, text="Une petite pause pour vous.", style="Title.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
        )
        ttk.Label(
            content, text="Des rappels discrets, à votre rythme.", style="Subtitle.TLabel"
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 24))
        ttk.Label(content, text="Votre prénom").grid(row=2, column=0, columnspan=2, sticky="w")
        name_entry = ttk.Entry(content, textvariable=self.name, width=38)
        name_entry.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(6, 18))
        ttk.Label(content, text="Intervalle entre les rappels (minutes)").grid(
            row=4, column=0, columnspan=2, sticky="w"
        )
        interval_entry = ttk.Spinbox(
            content, from_=1, to=1440, textvariable=self.interval, width=12
        )
        interval_entry.grid(row=5, column=0, columnspan=2, sticky="w", pady=(6, 18))
        ttk.Checkbutton(content, text="Démarrer avec Windows", variable=self.autostart).grid(
            row=6, column=0, columnspan=2, sticky="w"
        )
        ttk.Label(
            content,
            text="Changer l'intervalle relance le délai à la validation.\n"
            "En pause, le nouveau délai attend la reprise.",
            style="Subtitle.TLabel",
        ).grid(row=7, column=0, columnspan=2, sticky="w", pady=(18, 12))
        ttk.Label(content, textvariable=self.status, style="Subtitle.TLabel").grid(
            row=8, column=0, columnspan=2, sticky="w", pady=(0, 22)
        )
        ttk.Button(content, text="Annuler", command=self.close).grid(row=9, column=0, sticky="w")
        ttk.Button(
            content, text="Commencer" if first_run else "Enregistrer", command=self.submit
        ).grid(row=9, column=1, sticky="e")
        self.window.bind("<Return>", lambda _: self.submit())
        self.window.bind("<Escape>", lambda _: self.close())
        self.window.update_idletasks()
        width, height = self.window.winfo_reqwidth(), self.window.winfo_reqheight()
        x = (self.window.winfo_screenwidth() - width) // 2
        y = (self.window.winfo_screenheight() - height) // 2
        self.window.geometry(f"+{max(0, x)}+{max(0, y)}")
        self.window.lift()
        entry = interval_entry if focus == "interval" else name_entry
        entry.focus_set()
        entry.selection_range(0, tk.END)

    def submit(self) -> None:
        try:
            interval = self.interval.get().strip()
            if not interval.isascii() or not interval.isdigit():
                raise ValueError("Saisissez un nombre entier de minutes entre 1 et 1440.")
            settings = replace(
                self.settings,
                name=self.name.get().strip(),
                interval_minutes=int(self.interval.get()),
                autostart=self.autostart.get(),
                setup_complete=True,
            )
            self.save(settings)
        except (ValueError, OSError) as error:
            messagebox.showerror("Impossible d'enregistrer", str(error), parent=self.window)
            return
        self.close()

    def close(self) -> None:
        self.window.destroy()
        self.closed()


def configure_style(root: tk.Tk) -> None:
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".", font=("Segoe UI", 10), background="#f3f8fc", foreground="#183a50")
    style.configure("TEntry", fieldbackground="white", padding=7)
    style.configure("TSpinbox", fieldbackground="white", padding=7)
    style.configure("TButton", padding=(14, 8))
    style.configure("Title.TLabel", font=("Segoe UI Semibold", 19))
    style.configure("Subtitle.TLabel", foreground="#526d7d", font=("Segoe UI", 9))
