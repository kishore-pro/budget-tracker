import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
from datetime import datetime
import csv
from collections import defaultdict
import pathlib

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# ---------------------------------------------------------------------------
# Theme / shared constants
# ---------------------------------------------------------------------------
class Theme:
    BG = '#0f0f23'
    BG_LIGHT = '#1a1a2e'
    CARD = '#242438'
    CARD_ALT = '#2a2a40'
    SIDEBAR = '#181828'
    SIDEBAR_ACTIVE = '#2d2d55'
    ACCENT = '#00d4ff'
    ACCENT2 = '#6c5ce7'
    SUCCESS = '#2ed573'
    DANGER = '#ff4757'
    WARNING = '#feca57'
    TEXT = '#ffffff'
    TEXT_DIM = '#9a9ab5'
    BORDER = '#33334d'
    FONT = 'Segoe UI'

CATEGORIES = ["🍚 Food", "🚗 Transport", "📚 Study", "🎮 Fun", "🛍️ Shopping",
              "🏠 Bills", "💊 Health", "📱 Mobile", "🧾 Other"]
CURRENCIES = ["₹", "$", "€", "£", "¥"]
SAVINGS_OPTIONS = ["0%", "5%", "10%", "15%", "20%", "25%", "30%", "50%"]


def _clamp(v):
    return max(0, min(255, v))


def _shade(hexcolor, amount=18):
    """Lighten (positive amount) or darken (negative) a hex color."""
    hexcolor = hexcolor.lstrip('#')
    r, g, b = int(hexcolor[0:2], 16), int(hexcolor[2:4], 16), int(hexcolor[4:6], 16)
    r, g, b = _clamp(r + amount), _clamp(g + amount), _clamp(b + amount)
    return f'#{r:02x}{g:02x}{b:02x}'


def make_button(parent, text, command, bg, fg='white', size=14, bold=True,
                 pady=12, padx=30, anchor=None, width=None):
    """A tk.Button with a simple hover-lighten effect, styled consistently."""
    weight = 'bold' if bold else 'normal'
    kwargs = dict(text=text, command=command, font=(Theme.FONT, size, weight),
                  bg=bg, fg=fg, bd=0, pady=pady, padx=padx, cursor='hand2',
                  activebackground=_shade(bg, 24), activeforeground=fg,
                  relief='flat')
    if anchor:
        kwargs['anchor'] = anchor
    if width:
        kwargs['width'] = width
    btn = tk.Button(parent, **kwargs)
    hover_bg = _shade(bg, 18)

    def on_enter(_):
        btn.configure(bg=hover_bg)

    def on_leave(_):
        btn.configure(bg=bg)

    btn.bind("<Enter>", on_enter)
    btn.bind("<Leave>", on_leave)
    return btn


def make_entry(parent, width=22, size=16):
    return tk.Entry(parent, font=(Theme.FONT, size), width=width, bg=Theme.CARD_ALT,
                     fg=Theme.TEXT, insertbackground=Theme.TEXT, relief='flat',
                     highlightthickness=1, highlightbackground=Theme.BORDER,
                     highlightcolor=Theme.ACCENT)


def make_combo(parent, var, values, width=22, size=14):
    style_name = f"Combo{id(var)}.TCombobox"
    style = ttk.Style()
    style.theme_use('clam')
    style.configure(style_name, fieldbackground=Theme.CARD_ALT, background=Theme.CARD_ALT,
                     foreground=Theme.TEXT, arrowcolor=Theme.ACCENT, bordercolor=Theme.BORDER,
                     lightcolor=Theme.BORDER, darkcolor=Theme.BORDER)
    return ttk.Combobox(parent, textvariable=var, values=values, font=(Theme.FONT, size),
                         state='readonly', width=width, style=style_name)


def section_title(parent, text, size=32, color=None, pady=(30, 20)):
    tk.Label(parent, text=text, font=(Theme.FONT, size, 'bold'), bg=parent['bg'],
              fg=color or Theme.TEXT).pack(pady=pady)


def scrollable_area(parent, bg=None):
    """Returns (outer_frame, canvas, inner_frame) with a mousewheel-friendly vertical scrollbar."""
    bg = bg or Theme.BG
    outer = tk.Frame(parent, bg=bg)
    outer.pack(fill='both', expand=True)
    canvas = tk.Canvas(outer, bg=bg, highlightthickness=0)
    scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    inner = tk.Frame(canvas, bg=bg)
    inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    window_id = canvas.create_window((0, 0), window=inner, anchor="nw")
    canvas.bind("<Configure>", lambda e: canvas.itemconfig(window_id, width=e.width))
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    return outer, canvas, inner


# ---------------------------------------------------------------------------
# Modal dialog helper
# ---------------------------------------------------------------------------
class ModalDialog(tk.Toplevel):
    """A small styled modal window centered on the parent."""

    def __init__(self, parent, title, width=440, height=320):
        super().__init__(parent)
        self.title(title)
        self.configure(bg=Theme.BG_LIGHT)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        parent.update_idletasks()
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        x = px + (pw - width) // 2
        y = py + (ph - height) // 2
        self.geometry(f"{width}x{height}+{max(x,0)}+{max(y,0)}")
        self.body = tk.Frame(self, bg=Theme.BG_LIGHT)
        self.body.pack(fill='both', expand=True, padx=25, pady=20)


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------
class BudgetTracker:
    def __init__(self, root):
        self.root = root
        self.root.title("BudgetPro - Professional")

        try:
            self.root.state('zoomed')
        except Exception:
            self.root.geometry("1400x900")

        self.root.configure(bg=Theme.BG)
        self.root.minsize(1000, 650)

        self.data_dir = self.ensure_data_directory()
        self.data_file = os.path.join(self.data_dir, 'profiles_data.json')

        self.current_profile = None
        self.profiles = self.load_profiles()
        self.profile_data = {}
        self.active_page = None
        self.sidebar_open = False

        self.root.bind_all("<MouseWheel>", self._on_mousewheel)
        self.root.bind_all("<Button-4>", self._on_mousewheel)
        self.root.bind_all("<Button-5>", self._on_mousewheel)

        self.show_profile_screen()

    # ----- currency / formatting -------------------------------------------------
    def currency_symbol(self):
        if self.current_profile and self.current_profile in self.profiles:
            return self.profiles[self.current_profile].get('currency', '₹')
        return '₹'

    def fmt(self, amount):
        return f"{self.currency_symbol()}{amount:,.0f}"

    # ----- AI-style insights -------------------------------------------------
    def get_ai_insights(self, new_expense_amount=0):
        transactions = self.profile_data.get('transactions', [])
        expenses = [t for t in transactions if t['type'] == 'expense']
        balance = self.get_current_balance()

        suggestions = []

        if new_expense_amount > (balance * 0.8) and balance > 0:
            suggestions.append("⚠️ CRITICAL: This expense will consume over 80% of your remaining liquidity.")

        cat_counts = defaultdict(int)
        for e in expenses:
            cat_counts[e['category']] += 1

        for cat, count in cat_counts.items():
            if count > 5:
                suggestions.append(f"💡 SUGGESTION: You've made {count} transactions in {cat} recently. "
                                    f"Consider a monthly bulk budget for this.")

        total_saved = sum(s['amount'] for s in self.profile_data.get('savings_vault', []))
        if balance > 0 and total_saved < (balance * 0.2):
            suggestions.append("📉 ADVICE: Your savings vault is low relative to spending. "
                                "Consider increasing your auto-save %.")

        budget = self.profile_data.get('budget', 10000)
        total_spent = sum(t['amount'] for t in transactions if t['type'] == 'expense')
        if budget > 0 and total_spent > budget:
            over = total_spent - budget
            suggestions.append(f"🚨 OVER BUDGET: You've exceeded your base budget by {self.fmt(over)}.")

        return "\n\n".join(suggestions) if suggestions else "✅ Your spending pattern looks stable."

    def get_current_balance(self):
        total_spent = sum(t['amount'] for t in self.profile_data.get('transactions', []) if t['type'] == 'expense')
        total_income = sum(t['amount'] for t in self.profile_data.get('transactions', []) if t['type'] == 'income')
        return self.profile_data.get('budget', 10000) + total_income - total_spent

    def get_budget_used_fraction(self):
        budget = self.profile_data.get('budget', 10000)
        if budget <= 0:
            return 0
        total_spent = sum(t['amount'] for t in self.profile_data.get('transactions', []) if t['type'] == 'expense')
        return min(total_spent / budget, 1.5)

    # ----- scrolling -------------------------------------------------
    def _on_mousewheel(self, event):
        for widget in self.root.winfo_children():
            canvas = self._find_canvas(widget)
            if canvas:
                if event.num == 4:
                    canvas.yview_scroll(-1, "units")
                elif event.num == 5:
                    canvas.yview_scroll(1, "units")
                else:
                    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
                break

    def _find_canvas(self, widget):
        if isinstance(widget, tk.Canvas):
            return widget
        for child in widget.winfo_children():
            res = self._find_canvas(child)
            if res:
                return res
        return None

    # ----- persistence -------------------------------------------------
    def ensure_data_directory(self):
        home_dir = pathlib.Path.home()
        data_dir = home_dir / "BudgetPro_Data"
        data_dir.mkdir(exist_ok=True)
        return str(data_dir)

    def load_profiles(self):
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading profiles: {e}")
        return {}

    def save_profiles(self):
        try:
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            temp_file = self.data_file + '.tmp'
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.profiles, f, indent=2)
            os.replace(temp_file, self.data_file)
            return True
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save profiles: {str(e)}")
            return False

    def save_profile_data(self):
        if self.current_profile:
            profile_file = os.path.join(self.data_dir, f"{self.current_profile}.json")
            try:
                os.makedirs(os.path.dirname(profile_file), exist_ok=True)
                with open(profile_file, 'w', encoding='utf-8') as f:
                    json.dump(self.profile_data, f, indent=2)
            except Exception as e:
                print(f"Error saving profile data: {e}")

    def delete_profile(self, profile_id):
        profile_name = self.profiles[profile_id]['name']
        if messagebox.askyesno("Delete Profile", f"Delete profile '{profile_name}'?\nThis will remove ALL data permanently."):
            if messagebox.askokcancel("⚠️ FINAL WARNING",
                                       f"ARE YOU SURE?\n\n'{profile_name}' and all transactions will be PERMANENTLY DELETED.",
                                       icon='warning'):
                try:
                    profile_file = os.path.join(self.data_dir, f"{profile_id}.json")
                    if os.path.exists(profile_file):
                        os.remove(profile_file)
                    del self.profiles[profile_id]
                    self.save_profiles()
                    messagebox.showinfo("✅ Success", f"Profile '{profile_name}' deleted!")
                    if self.current_profile == profile_id:
                        self.current_profile = None
                        self.profile_data = {}
                    self.show_profile_screen()
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to delete profile: {str(e)}")

    def load_profile(self, profile_id):
        self.current_profile = profile_id
        profile_file = os.path.join(self.data_dir, f"{profile_id}.json")
        try:
            if os.path.exists(profile_file):
                with open(profile_file, 'r', encoding='utf-8') as f:
                    self.profile_data = json.load(f)
            else:
                self.profile_data = {}
        except Exception:
            self.profile_data = {}

        self.profile_data.setdefault('budget', 10000)
        self.profile_data.setdefault('transactions', [])
        self.profile_data.setdefault('savings_vault', [])
        self.profiles[profile_id].setdefault('currency', '₹')
        self.show_main_app()

    def clear_root(self):
        self._unbind_enter()
        for widget in self.root.winfo_children():
            widget.destroy()

    def clear_content(self):
        self._unbind_enter()
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def _unbind_enter(self):
        try:
            self.root.unbind('<Return>')
        except Exception:
            pass

    # ----- profile selection / creation -------------------------------------------------
    def show_profile_screen(self):
        self.clear_root()
        tk.Label(self.root, text="💰 BudgetPro", font=(Theme.FONT, 48, 'bold'), bg=Theme.BG,
                 fg=Theme.ACCENT).pack(pady=(60, 5))
        tk.Label(self.root, text="Take control of your money", font=(Theme.FONT, 14), bg=Theme.BG,
                 fg=Theme.TEXT_DIM).pack(pady=(0, 20))
        main_frame = tk.Frame(self.root, bg=Theme.BG)
        main_frame.pack(expand=True, fill='both', padx=100, pady=20)

        if self.profiles:
            self.show_existing_profiles(main_frame)
        else:
            self.show_first_time(main_frame)

    def show_existing_profiles(self, parent):
        tk.Label(parent, text="Choose Your Profile", font=(Theme.FONT, 20, 'bold'), bg=Theme.BG,
                 fg=Theme.TEXT).pack(pady=15)
        list_wrap = tk.Frame(parent, bg=Theme.BG)
        list_wrap.pack(fill='both', expand=True, padx=150)
        _, _, inner = scrollable_area(list_wrap, bg=Theme.BG)

        for profile_id, data in self.profiles.items():
            self.create_profile_card(inner, profile_id, data)

        make_button(parent, "➕  Create New Profile", self.show_create_profile, Theme.DANGER,
                    size=16).pack(pady=25)

    def create_profile_card(self, parent, profile_id, data):
        card = tk.Frame(parent, bg=Theme.CARD)
        card.pack(fill='x', pady=8)
        stripe = tk.Frame(card, bg=Theme.ACCENT, width=6)
        stripe.pack(side='left', fill='y')
        pic = tk.Label(card, text="👤", font=(Theme.FONT, 22), bg=Theme.ACCENT2, fg='white', width=3, height=1)
        pic.pack(side='left', padx=18, pady=14)
        info_frame = tk.Frame(card, bg=Theme.CARD)
        info_frame.pack(side='left', padx=10, fill='y', expand=True)
        tk.Label(info_frame, text=data['name'], font=(Theme.FONT, 16, 'bold'), bg=Theme.CARD,
                 fg=Theme.TEXT).pack(anchor='w', pady=(10, 0))
        curr = data.get('currency', '₹')
        tk.Label(info_frame, text=f"{data['category']}  ·  Auto-save {data.get('savings_percent', 0)}%  ·  {curr}",
                 font=(Theme.FONT, 12), bg=Theme.CARD, fg=Theme.ACCENT).pack(anchor='w', pady=(2, 10))
        make_button(card, "LAUNCH →", lambda p=profile_id: self.load_profile(p), Theme.ACCENT,
                    size=12, pady=10, padx=20).pack(side='right', padx=20)

    def show_first_time(self, parent):
        wrap = tk.Frame(parent, bg=Theme.BG)
        wrap.pack(expand=True)
        tk.Label(wrap, text="🎉", font=(Theme.FONT, 48), bg=Theme.BG).pack(pady=(30, 10))
        tk.Label(wrap, text="Let's set up your first profile", font=(Theme.FONT, 22, 'bold'), bg=Theme.BG,
                 fg=Theme.TEXT).pack(pady=10)
        make_button(wrap, "➕  Create Your Profile", self.show_create_profile, Theme.ACCENT2,
                    size=18, pady=20, padx=50).pack(pady=25)

    def _profile_form(self, title, defaults, on_save, on_cancel, save_label="✅  CREATE PROFILE"):
        """Shared form builder for create + edit profile screens."""
        self.clear_root()
        section_title(self.root, title)
        form = tk.Frame(self.root, bg=Theme.BG_LIGHT, highlightbackground=Theme.BORDER,
                         highlightthickness=1)
        form.pack(pady=10, padx=200)

        tk.Label(form, text="Name", font=(Theme.FONT, 14, 'bold'), bg=Theme.BG_LIGHT,
                 fg=Theme.TEXT).pack(pady=(20, 4))
        name_entry = make_entry(form, width=25)
        name_entry.insert(0, defaults.get('name', ''))
        name_entry.pack(pady=5, padx=50)
        name_entry.focus_set()

        tk.Label(form, text="Category", font=(Theme.FONT, 14, 'bold'), bg=Theme.BG_LIGHT,
                 fg=Theme.TEXT).pack(pady=(15, 4))
        category_var = tk.StringVar(value=defaults.get('category', 'Student'))
        make_combo(form, category_var, ["Student", "Employee", "Freelancer", "Business"],
                   width=22).pack(pady=5)

        row = tk.Frame(form, bg=Theme.BG_LIGHT)
        row.pack(pady=(15, 4))
        left = tk.Frame(row, bg=Theme.BG_LIGHT)
        left.pack(side='left', padx=15)
        tk.Label(left, text="💰 Auto-Savings (%)", font=(Theme.FONT, 13, 'bold'), bg=Theme.BG_LIGHT,
                 fg=Theme.WARNING).pack()
        savings_var = tk.StringVar(value=f"{defaults.get('savings_percent', 10)}%")
        make_combo(left, savings_var, SAVINGS_OPTIONS, width=10).pack(pady=5)

        right = tk.Frame(row, bg=Theme.BG_LIGHT)
        right.pack(side='left', padx=15)
        tk.Label(right, text="💱 Currency", font=(Theme.FONT, 13, 'bold'), bg=Theme.BG_LIGHT,
                 fg=Theme.WARNING).pack()
        currency_var = tk.StringVar(value=defaults.get('currency', '₹'))
        make_combo(right, currency_var, CURRENCIES, width=10).pack(pady=5)

        def do_save():
            name = name_entry.get().strip()
            if not name:
                messagebox.showerror("Error", "Enter your name!")
                return
            on_save(name, category_var.get(), int(savings_var.get().replace('%', '')), currency_var.get())

        make_button(form, save_label, do_save, Theme.SUCCESS, size=16).pack(pady=20)
        make_button(form, "🔙  Back", on_cancel, Theme.ACCENT2, size=12, pady=8, padx=25).pack(pady=(0, 18))
        self.root.bind('<Return>', lambda e: do_save())

    def show_create_profile(self):
        def on_save(name, category, savings_pct, currency):
            p_id = f"profile_{int(datetime.now().timestamp())}"
            self.profiles[p_id] = {
                'name': name, 'category': category, 'savings_percent': savings_pct,
                'currency': currency, 'created': datetime.now().strftime("%Y-%m-%d")
            }
            if self.save_profiles():
                self.current_profile = p_id
                self.profile_data = {'budget': 10000, 'transactions': [], 'savings_vault': [],
                                      'created': datetime.now().strftime("%Y-%m-%d")}
                self.save_profile_data()
                self.root.unbind('<Return>')
                self.show_main_app()

        self._profile_form("➕ Create Profile", {}, on_save, self.show_profile_screen)

    def show_edit_profile(self):
        profile = self.profiles[self.current_profile]

        def on_save(name, category, savings_pct, currency):
            self.profiles[self.current_profile].update({
                'name': name, 'category': category, 'savings_percent': savings_pct, 'currency': currency
            })
            if self.save_profiles():
                messagebox.showinfo("✅ Success", "Profile updated successfully!")
                self.root.unbind('<Return>')
                self.show_main_app()

        self._profile_form("✏️ Edit Profile", profile, on_save, self.show_profile,
                            save_label="💾  SAVE CHANGES")

    # ----- main app shell -------------------------------------------------
    def show_main_app(self):
        self.clear_root()
        top_bar = tk.Frame(self.root, bg=Theme.BG_LIGHT, height=70)
        top_bar.pack(fill='x')
        top_bar.pack_propagate(False)

        make_button(top_bar, "☰", self.toggle_menu, Theme.BG_LIGHT, size=22, pady=0, padx=15,
                    width=2).pack(side='left', padx=15)

        p_name = self.profiles[self.current_profile]['name']
        tk.Label(top_bar, text=f"Hi, {p_name}! 👋", font=(Theme.FONT, 18, 'bold'), bg=Theme.BG_LIGHT,
                 fg=Theme.ACCENT).pack(side='left', padx=10)

        bal = self.get_current_balance()
        bal_color = Theme.SUCCESS if bal >= 0 else Theme.DANGER
        tk.Label(top_bar, text=f"Balance: {self.fmt(bal)}", font=(Theme.FONT, 15, 'bold'),
                 bg=Theme.BG_LIGHT, fg=bal_color).pack(side='right', padx=25)

        self.main_container = tk.Frame(self.root, bg=Theme.BG)
        self.main_container.pack(fill='both', expand=True)

        self.content_frame = tk.Frame(self.main_container, bg=Theme.BG)
        self.content_frame.place(x=0, y=0, relwidth=1, relheight=1)

        # dim overlay used while the sidebar is open, click to close
        self.overlay = tk.Frame(self.main_container, bg='black')
        self.overlay.bind("<Button-1>", lambda e: self.toggle_menu())

        self.sidebar = tk.Frame(self.main_container, width=280, bg=Theme.SIDEBAR)
        self.sidebar.place(x=-280, y=0, relheight=1)
        self.sidebar_open = False

        sb_head = tk.Frame(self.sidebar, bg=Theme.SIDEBAR)
        sb_head.pack(fill='x', pady=(20, 10), padx=15)
        tk.Label(sb_head, text="📋 Menu", font=(Theme.FONT, 18, 'bold'), bg=Theme.SIDEBAR,
                 fg=Theme.TEXT).pack(side='left')
        make_button(sb_head, "✕", self.toggle_menu, Theme.SIDEBAR, size=14, pady=0, padx=8).pack(side='right')

        self.menu_buttons = {}
        menu_items = [
            ("dashboard", "📊  Dashboard", self.show_dashboard),
            ("expense", "💸  Add Expense", self.show_expense),
            ("income", "💰  Add Income", self.show_income),
            ("savings", "🏦  Savings Vault", self.show_savings),
            ("transactions", "📜  Transactions", self.show_transactions),
            ("analysis", "📈  Analysis", self.show_analysis),
            ("profile", "👤  Profile", self.show_profile),
        ]

        for key, text, cmd in menu_items:
            btn = tk.Button(self.sidebar, text=text, font=(Theme.FONT, 15, 'bold'), bg=Theme.SIDEBAR,
                             fg=Theme.TEXT, bd=0, pady=14, anchor='w', padx=25, cursor='hand2',
                             activebackground=Theme.SIDEBAR_ACTIVE, activeforeground=Theme.TEXT,
                             command=lambda c=cmd, k=key: self._navigate(k, c))
            btn.pack(fill='x')
            self.menu_buttons[key] = btn

        self._navigate("dashboard", self.show_dashboard)

    def _navigate(self, key, cmd):
        self.active_page = key
        for k, btn in self.menu_buttons.items():
            btn.configure(bg=Theme.SIDEBAR_ACTIVE if k == key else Theme.SIDEBAR)
        if self.sidebar_open:
            self.toggle_menu()
        cmd()

    def toggle_menu(self):
        if not self.sidebar_open:
            self.sidebar.place(x=0)
            self.overlay.place(x=0, y=0, relwidth=1, relheight=1)
            self.overlay.lift()
            self.sidebar.lift()
            self.sidebar_open = True
        else:
            self.sidebar.place(x=-280)
            self.overlay.place_forget()
            self.sidebar_open = False

    # ----- dashboard -------------------------------------------------
    def show_dashboard(self):
        self.clear_content()
        outer, _, inner = scrollable_area(self.content_frame, bg=Theme.BG)
        section_title(inner, "📊 Dashboard")

        insight_text = self.get_ai_insights()
        insight_box = tk.Label(inner, text=insight_text, font=(Theme.FONT, 12, 'italic'), bg=Theme.BG_LIGHT,
                                fg=Theme.ACCENT, pady=14, padx=20, justify='left', wraplength=900,
                                highlightbackground=Theme.BORDER, highlightthickness=1)
        insight_box.pack(pady=10, fill='x', padx=80)

        total_spent = sum(t['amount'] for t in self.profile_data.get('transactions', []) if t['type'] == 'expense')
        total_income = sum(t['amount'] for t in self.profile_data.get('transactions', []) if t['type'] == 'income')
        total_saved = sum(s['amount'] for s in self.profile_data.get('savings_vault', []))
        balance = self.get_current_balance()

        stats_frame = tk.Frame(inner, bg=Theme.BG)
        stats_frame.pack(pady=25, padx=80, fill='x')
        for i in range(3):
            stats_frame.grid_columnconfigure(i, weight=1)

        cards = [
            ("💸 Total Spent", self.fmt(total_spent), Theme.DANGER),
            ("💰 Total Income", self.fmt(total_income), Theme.ACCENT2),
            ("🏦 Total Saved", self.fmt(total_saved), Theme.WARNING),
        ]
        for i, (label, value, color) in enumerate(cards):
            card = tk.Frame(stats_frame, bg=color, height=140)
            card.grid(row=0, column=i, padx=12, pady=10, sticky='nsew')
            card.grid_propagate(False)
            tk.Label(card, text=label, font=(Theme.FONT, 14, 'bold'), fg='white', bg=color).pack(pady=(22, 8))
            tk.Label(card, text=value, font=(Theme.FONT, 24, 'bold'), fg='white', bg=color).pack()

        # Balance + budget progress
        bal_frame = tk.Frame(inner, bg=Theme.CARD)
        bal_frame.pack(pady=10, padx=80, fill='x')
        bal_color = Theme.SUCCESS if balance >= 0 else Theme.DANGER
        tk.Label(bal_frame, text=f"💳 Current Balance: {self.fmt(balance)}", font=(Theme.FONT, 18, 'bold'),
                 bg=Theme.CARD, fg=bal_color).pack(pady=(18, 6), padx=20, anchor='w')

        budget = self.profile_data.get('budget', 10000)
        used_frac = self.get_budget_used_fraction()
        bar_bg = tk.Frame(bal_frame, bg=Theme.BORDER, height=18)
        bar_bg.pack(fill='x', padx=20, pady=(0, 6))
        bar_bg.pack_propagate(False)
        fill_color = Theme.SUCCESS if used_frac < 0.75 else (Theme.WARNING if used_frac < 1 else Theme.DANGER)
        bar_fill = tk.Frame(bar_bg, bg=fill_color)
        bar_fill.place(relx=0, rely=0, relwidth=min(used_frac, 1.0), relheight=1)
        tk.Label(bal_frame, text=f"Base budget: {self.fmt(budget)}  ·  {used_frac*100:.0f}% used",
                 font=(Theme.FONT, 11), bg=Theme.CARD, fg=Theme.TEXT_DIM).pack(pady=(0, 16), padx=20, anchor='w')

        # Recent transactions preview
        recent = list(reversed(self.profile_data.get('transactions', [])))[:5]
        if recent:
            tk.Label(inner, text="Recent Activity", font=(Theme.FONT, 16, 'bold'), bg=Theme.BG,
                     fg=Theme.TEXT).pack(pady=(20, 8), padx=80, anchor='w')
            recent_wrap = tk.Frame(inner, bg=Theme.BG)
            recent_wrap.pack(fill='x', padx=80, pady=(0, 30))
            for t in recent:
                color = Theme.DANGER if t['type'] == 'expense' else Theme.SUCCESS
                sign = '-' if t['type'] == 'expense' else '+'
                row = tk.Frame(recent_wrap, bg=Theme.CARD)
                row.pack(fill='x', pady=4)
                tk.Label(row, text=f"{sign}{self.fmt(t['amount'])}", font=(Theme.FONT, 13, 'bold'),
                         bg=Theme.CARD, fg=color, width=12, anchor='w').pack(side='left', padx=15, pady=10)
                tk.Label(row, text=t['category'], font=(Theme.FONT, 12), bg=Theme.CARD,
                         fg=Theme.TEXT).pack(side='left', padx=5)
                tk.Label(row, text=t['date'], font=(Theme.FONT, 10), bg=Theme.CARD,
                         fg=Theme.TEXT_DIM).pack(side='right', padx=15)

    # ----- add expense / income -------------------------------------------------
    def show_expense(self):
        self.clear_content()
        _, _, inner = scrollable_area(self.content_frame, bg=Theme.BG)
        section_title(inner, "💸 Add Expense")
        form = tk.Frame(inner, bg=Theme.BG_LIGHT, highlightbackground=Theme.BORDER, highlightthickness=1)
        form.pack(pady=10, padx=200)

        tk.Label(form, text=f"Amount ({self.currency_symbol()})", font=(Theme.FONT, 16, 'bold'),
                 bg=Theme.BG_LIGHT, fg=Theme.TEXT).pack(pady=(20, 6))
        amount_entry = make_entry(form, width=20, size=20)
        amount_entry.pack(pady=6, padx=60)
        amount_entry.focus_set()

        balance_label = tk.Label(form, text=f"💳 Available Balance: {self.fmt(self.get_current_balance())}",
                                  font=(Theme.FONT, 13), bg=Theme.BG_LIGHT, fg=Theme.ACCENT)
        balance_label.pack(pady=(6, 10))

        cat_var = tk.StringVar(value=CATEGORIES[0])
        make_combo(form, cat_var, CATEGORIES, width=22).pack(pady=10)

        tk.Label(form, text="Note (optional)", font=(Theme.FONT, 12, 'bold'), bg=Theme.BG_LIGHT,
                 fg=Theme.TEXT_DIM).pack(pady=(6, 4))
        note_entry = make_entry(form, width=28, size=13)
        note_entry.pack(pady=(0, 10), padx=60)

        def add_expense():
            try:
                amount = float(amount_entry.get())
                if amount <= 0:
                    raise ValueError
            except (ValueError, TypeError):
                messagebox.showerror("❌ Error", "Enter a valid positive amount!")
                return
            ai_warning = self.get_ai_insights(amount)
            if "⚠️" in ai_warning:
                if not messagebox.askyesno("AI Financial Warning", f"{ai_warning}\n\nDo you still want to proceed?"):
                    return
            curr_bal = self.get_current_balance()
            if amount > curr_bal:
                messagebox.showerror("❌ Error", f"Insufficient funds! Available: {self.fmt(curr_bal)}")
                return
            self.profile_data['transactions'].append({
                'date': datetime.now().strftime("%Y-%m-%d %H:%M"), 'amount': amount,
                'category': cat_var.get(), 'type': 'expense', 'note': note_entry.get().strip() or None
            })
            self.save_profile_data()
            messagebox.showinfo("✅ Success", f"Added {self.fmt(amount)}")
            amount_entry.delete(0, tk.END)
            note_entry.delete(0, tk.END)
            balance_label.config(text=f"💳 Available Balance: {self.fmt(self.get_current_balance())}")

        self.root.bind('<Return>', lambda e: add_expense())
        make_button(form, "➕  ADD EXPENSE", add_expense, Theme.DANGER, size=17).pack(pady=25)

    def show_income(self):
        self.clear_content()
        _, _, inner = scrollable_area(self.content_frame, bg=Theme.BG)
        section_title(inner, "💰 Add Income")
        form = tk.Frame(inner, bg=Theme.BG_LIGHT, highlightbackground=Theme.BORDER, highlightthickness=1)
        form.pack(pady=10, padx=200)

        tk.Label(form, text=f"Gross Amount ({self.currency_symbol()})", font=(Theme.FONT, 16, 'bold'),
                 bg=Theme.BG_LIGHT, fg=Theme.TEXT).pack(pady=(20, 6))
        amount_entry = make_entry(form, width=20, size=20)
        amount_entry.pack(pady=6, padx=60)
        amount_entry.focus_set()

        save_pct = self.profiles[self.current_profile].get('savings_percent', 0)
        tk.Label(form, text=f"✨ Auto-Savings Active: {save_pct}%", font=(Theme.FONT, 12), bg=Theme.BG_LIGHT,
                 fg=Theme.WARNING).pack(pady=(4, 10))

        tk.Label(form, text="Source / Note (optional)", font=(Theme.FONT, 12, 'bold'), bg=Theme.BG_LIGHT,
                 fg=Theme.TEXT_DIM).pack(pady=(6, 4))
        note_entry = make_entry(form, width=28, size=13)
        note_entry.pack(pady=(0, 10), padx=60)

        def add_income():
            try:
                gross_amount = float(amount_entry.get())
                if gross_amount <= 0:
                    raise ValueError
            except (ValueError, TypeError):
                messagebox.showerror("❌ Error", "Enter a valid positive amount!")
                return
            savings_deduction = (gross_amount * save_pct) / 100
            net_income = gross_amount - savings_deduction
            note = note_entry.get().strip()
            self.profile_data['transactions'].append({
                'date': datetime.now().strftime("%Y-%m-%d %H:%M"), 'amount': net_income,
                'category': 'Income (Net)', 'type': 'income',
                'note': (note + " · " if note else "") + f"Gross: {self.fmt(gross_amount)}"
            })
            if savings_deduction > 0:
                self.profile_data['savings_vault'].append({
                    'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
                    'amount': savings_deduction,
                    'source': note if note else f"Income of {self.fmt(gross_amount)}"
                })
            self.save_profile_data()
            messagebox.showinfo("✅ Success", f"Net Income: {self.fmt(net_income)}\nSaved: {self.fmt(savings_deduction)}")
            amount_entry.delete(0, tk.END)
            note_entry.delete(0, tk.END)

        self.root.bind('<Return>', lambda e: add_income())
        make_button(form, "➕  ADD INCOME", add_income, Theme.SUCCESS, size=17).pack(pady=25)

    # ----- budget -------------------------------------------------
    def set_budget_dialog(self):
        dlg = ModalDialog(self.root, "Set Base Budget", width=420, height=250)
        tk.Label(dlg.body, text="💼 Set Base Budget", font=(Theme.FONT, 18, 'bold'), bg=Theme.BG_LIGHT,
                 fg=Theme.TEXT).pack(pady=(0, 15))
        tk.Label(dlg.body, text=f"Current: {self.fmt(self.profile_data.get('budget', 10000))}",
                 font=(Theme.FONT, 11), bg=Theme.BG_LIGHT, fg=Theme.TEXT_DIM).pack(pady=(0, 10))
        entry = make_entry(dlg.body, width=18, size=18)
        entry.insert(0, str(self.profile_data.get('budget', 10000)))
        entry.pack(pady=5)
        entry.focus_set()

        def save():
            try:
                val = float(entry.get())
                if val < 0:
                    raise ValueError
            except (ValueError, TypeError):
                messagebox.showerror("❌ Error", "Enter a valid non-negative amount!")
                return
            self.profile_data['budget'] = val
            self.save_profile_data()
            dlg.destroy()
            self.show_dashboard()

        make_button(dlg.body, "💾  Save Budget", save, Theme.SUCCESS, size=14, pady=10).pack(pady=20)
        dlg.bind('<Return>', lambda e: save())

    # ----- savings vault -------------------------------------------------
    def show_savings(self):
        self.clear_content()
        _, _, inner = scrollable_area(self.content_frame, bg=Theme.BG)
        section_title(inner, "🏦 Savings Vault", color=Theme.WARNING)

        vault = self.profile_data.get('savings_vault', [])
        total_saved = sum(s['amount'] for s in vault)
        tk.Label(inner, text=f"Total Vault Balance: {self.fmt(total_saved)}", font=(Theme.FONT, 22, 'bold'),
                 bg=Theme.BG, fg=Theme.TEXT).pack(pady=(0, 10))

        btn_row = tk.Frame(inner, bg=Theme.BG)
        btn_row.pack(pady=10)
        make_button(btn_row, "➕ Deposit", self.deposit_savings_dialog, Theme.SUCCESS, size=13,
                    pady=10, padx=25).pack(side='left', padx=8)
        make_button(btn_row, "➖ Withdraw", self.withdraw_savings_dialog, Theme.DANGER, size=13,
                    pady=10, padx=25).pack(side='left', padx=8)

        list_wrap = tk.Frame(inner, bg=Theme.BG)
        list_wrap.pack(fill='x', padx=100, pady=15)

        if not vault:
            tk.Label(list_wrap, text="No savings activity yet.", font=(Theme.FONT, 12), bg=Theme.BG,
                     fg=Theme.TEXT_DIM).pack(pady=20)

        for s in reversed(vault):
            is_withdrawal = s['amount'] < 0
            color = Theme.CARD if not is_withdrawal else Theme.CARD_ALT
            amt_color = Theme.SUCCESS if not is_withdrawal else Theme.DANGER
            card = tk.Frame(list_wrap, bg=color, pady=10)
            card.pack(fill='x', pady=5)
            tk.Label(card, text=f"{'+' if not is_withdrawal else ''}{self.fmt(s['amount'])}",
                     font=(Theme.FONT, 16, 'bold'), fg=amt_color, bg=color, width=14, anchor='w').pack(side='left', padx=20)
            tk.Label(card, text=f"{s['source']}\n{s['date']}", font=(Theme.FONT, 10), fg=Theme.TEXT,
                     bg=color, justify='left').pack(side='left', padx=10)

    def deposit_savings_dialog(self):
        dlg = ModalDialog(self.root, "Deposit to Vault", width=420, height=280)
        tk.Label(dlg.body, text="➕ Manual Deposit", font=(Theme.FONT, 18, 'bold'), bg=Theme.BG_LIGHT,
                 fg=Theme.TEXT).pack(pady=(0, 15))
        entry = make_entry(dlg.body, width=18, size=18)
        entry.pack(pady=5)
        entry.focus_set()
        note = make_entry(dlg.body, width=24, size=12)
        note.insert(0, "Manual deposit")
        note.pack(pady=10)

        def save():
            try:
                amt = float(entry.get())
                if amt <= 0:
                    raise ValueError
            except (ValueError, TypeError):
                messagebox.showerror("❌ Error", "Enter a valid positive amount!")
                return
            if amt > self.get_current_balance():
                messagebox.showerror("❌ Error", "Deposit exceeds your current balance!")
                return
            self.profile_data['savings_vault'].append({
                'date': datetime.now().strftime("%Y-%m-%d %H:%M"), 'amount': amt,
                'source': note.get().strip() or "Manual deposit"
            })
            self.profile_data['transactions'].append({
                'date': datetime.now().strftime("%Y-%m-%d %H:%M"), 'amount': amt,
                'category': '🏦 Savings Deposit', 'type': 'expense', 'note': 'Moved to savings vault'
            })
            self.save_profile_data()
            dlg.destroy()
            self.show_savings()

        make_button(dlg.body, "💾  Deposit", save, Theme.SUCCESS, size=14, pady=10).pack(pady=15)
        dlg.bind('<Return>', lambda e: save())

    def withdraw_savings_dialog(self):
        vault_total = sum(s['amount'] for s in self.profile_data.get('savings_vault', []))
        dlg = ModalDialog(self.root, "Withdraw from Vault", width=420, height=280)
        tk.Label(dlg.body, text="➖ Withdraw Savings", font=(Theme.FONT, 18, 'bold'), bg=Theme.BG_LIGHT,
                 fg=Theme.TEXT).pack(pady=(0, 8))
        tk.Label(dlg.body, text=f"Vault balance: {self.fmt(vault_total)}", font=(Theme.FONT, 11),
                 bg=Theme.BG_LIGHT, fg=Theme.TEXT_DIM).pack(pady=(0, 10))
        entry = make_entry(dlg.body, width=18, size=18)
        entry.pack(pady=5)
        entry.focus_set()

        def save():
            try:
                amt = float(entry.get())
                if amt <= 0:
                    raise ValueError
            except (ValueError, TypeError):
                messagebox.showerror("❌ Error", "Enter a valid positive amount!")
                return
            if amt > vault_total:
                messagebox.showerror("❌ Error", "Withdrawal exceeds vault balance!")
                return
            self.profile_data['savings_vault'].append({
                'date': datetime.now().strftime("%Y-%m-%d %H:%M"), 'amount': -amt,
                'source': "Withdrawal to balance"
            })
            self.profile_data['transactions'].append({
                'date': datetime.now().strftime("%Y-%m-%d %H:%M"), 'amount': amt,
                'category': '🏦 Savings Withdrawal', 'type': 'income', 'note': 'Withdrawn from savings vault'
            })
            self.save_profile_data()
            dlg.destroy()
            self.show_savings()

        make_button(dlg.body, "💾  Withdraw", save, Theme.DANGER, size=14, pady=10).pack(pady=15)
        dlg.bind('<Return>', lambda e: save())

    # ----- transactions: search / filter / edit / delete -------------------------------------------------
    def show_transactions(self, filter_type="All", filter_cat="All", search_text=""):
        self.clear_content()
        section_title(self.content_frame, "📜 Transaction History", pady=(30, 15))

        filt_bar = tk.Frame(self.content_frame, bg=Theme.BG)
        filt_bar.pack(pady=(0, 10), padx=50, fill='x')

        tk.Label(filt_bar, text="Type:", font=(Theme.FONT, 11), bg=Theme.BG, fg=Theme.TEXT_DIM).pack(side='left')
        type_var = tk.StringVar(value=filter_type)
        make_combo(filt_bar, type_var, ["All", "Expense", "Income"], width=10).pack(side='left', padx=(5, 15))

        tk.Label(filt_bar, text="Category:", font=(Theme.FONT, 11), bg=Theme.BG, fg=Theme.TEXT_DIM).pack(side='left')
        cat_values = ["All"] + sorted({t['category'] for t in self.profile_data.get('transactions', [])})
        cat_var = tk.StringVar(value=filter_cat if filter_cat in cat_values else "All")
        make_combo(filt_bar, cat_var, cat_values, width=16).pack(side='left', padx=(5, 15))

        tk.Label(filt_bar, text="Search:", font=(Theme.FONT, 11), bg=Theme.BG, fg=Theme.TEXT_DIM).pack(side='left')
        search_entry = make_entry(filt_bar, width=18, size=12)
        search_entry.insert(0, search_text)
        search_entry.pack(side='left', padx=5)

        def apply_filters():
            self.show_transactions(type_var.get(), cat_var.get(), search_entry.get().strip().lower())

        make_button(filt_bar, "🔍 Apply", apply_filters, Theme.ACCENT, size=11, pady=6, padx=15).pack(side='left', padx=10)
        search_entry.bind('<Return>', lambda e: apply_filters())

        transactions = list(self.profile_data.get('transactions', []))
        if filter_type != "All":
            transactions = [t for t in transactions if t['type'] == filter_type.lower()]
        if filter_cat != "All":
            transactions = [t for t in transactions if t['category'] == filter_cat]
        if search_text:
            transactions = [t for t in transactions
                             if search_text in (t.get('note') or '').lower()
                             or search_text in t['category'].lower()]

        _, _, inner = scrollable_area(self.content_frame, bg=Theme.BG)

        if not transactions:
            tk.Label(inner, text="No matching transactions.", font=(Theme.FONT, 13), bg=Theme.BG,
                     fg=Theme.TEXT_DIM).pack(pady=40)

        for trans in reversed(transactions[-200:]):
            color = Theme.DANGER if trans['type'] == 'expense' else Theme.SUCCESS
            sign = '-' if trans['type'] == 'expense' else '+'
            card = tk.Frame(inner, bg=color, relief='flat')
            card.pack(fill='x', padx=30, pady=5)
            tk.Label(card, text=f"{sign}{self.fmt(trans['amount'])}", font=(Theme.FONT, 18, 'bold'), fg='white',
                     bg=color, width=12, anchor='w').pack(side='left', padx=20, pady=14)
            note = f"\n📝 {trans['note']}" if trans.get('note') else ""
            tk.Label(card, text=f"{trans['category']}\n{trans['date']}{note}", font=(Theme.FONT, 11), fg='white',
                     bg=color, justify='left').pack(side='left', padx=10)
            make_button(card, "🗑️", lambda t=trans: self.delete_transaction(t, type_var.get(), cat_var.get(), search_entry.get()),
                        color, size=12, pady=6, padx=10).pack(side='right', padx=8)
            make_button(card, "✏️", lambda t=trans: self.edit_transaction_dialog(t, type_var.get(), cat_var.get(), search_entry.get()),
                        color, size=12, pady=6, padx=10).pack(side='right', padx=2)

    def delete_transaction(self, transaction, ft="All", fc="All", fs=""):
        if messagebox.askyesno("Delete", "Remove this transaction?"):
            self.profile_data['transactions'].remove(transaction)
            self.save_profile_data()
            self.show_transactions(ft, fc, fs)

    def edit_transaction_dialog(self, transaction, ft="All", fc="All", fs=""):
        dlg = ModalDialog(self.root, "Edit Transaction", width=440, height=380)
        tk.Label(dlg.body, text="✏️ Edit Transaction", font=(Theme.FONT, 18, 'bold'), bg=Theme.BG_LIGHT,
                 fg=Theme.TEXT).pack(pady=(0, 15))

        tk.Label(dlg.body, text="Amount", font=(Theme.FONT, 12), bg=Theme.BG_LIGHT, fg=Theme.TEXT_DIM).pack()
        amount_entry = make_entry(dlg.body, width=18, size=16)
        amount_entry.insert(0, str(transaction['amount']))
        amount_entry.pack(pady=(2, 10))

        tk.Label(dlg.body, text="Category", font=(Theme.FONT, 12), bg=Theme.BG_LIGHT, fg=Theme.TEXT_DIM).pack()
        cat_options = CATEGORIES if transaction['type'] == 'expense' else \
            sorted({t['category'] for t in self.profile_data['transactions'] if t['type'] == 'income'} | {transaction['category']})
        cat_var = tk.StringVar(value=transaction['category'])
        make_combo(dlg.body, cat_var, cat_options, width=22).pack(pady=(2, 10))

        tk.Label(dlg.body, text="Note", font=(Theme.FONT, 12), bg=Theme.BG_LIGHT, fg=Theme.TEXT_DIM).pack()
        note_entry = make_entry(dlg.body, width=26, size=12)
        note_entry.insert(0, transaction.get('note') or '')
        note_entry.pack(pady=(2, 10))

        def save():
            try:
                new_amt = float(amount_entry.get())
                if new_amt <= 0:
                    raise ValueError
            except (ValueError, TypeError):
                messagebox.showerror("❌ Error", "Enter a valid positive amount!")
                return
            transaction['amount'] = new_amt
            transaction['category'] = cat_var.get()
            transaction['note'] = note_entry.get().strip() or None
            self.save_profile_data()
            dlg.destroy()
            self.show_transactions(ft, fc, fs)

        make_button(dlg.body, "💾  Save Changes", save, Theme.SUCCESS, size=13, pady=10).pack(pady=18)
        dlg.bind('<Return>', lambda e: save())

    # ----- analysis (embedded charts) -------------------------------------------------
    def show_analysis(self):
        self.clear_content()
        section_title(self.content_frame, "📈 Analysis", pady=(30, 10))

        btn_frame = tk.Frame(self.content_frame, bg=Theme.BG)
        btn_frame.pack(pady=10)
        make_button(btn_frame, "🥧 Category Breakdown", lambda: self.render_pie_chart(chart_holder),
                    Theme.ACCENT2, size=13, pady=10, padx=20).pack(side='left', padx=6)
        make_button(btn_frame, "📊 Monthly Trend", lambda: self.render_monthly_chart(chart_holder),
                    Theme.ACCENT, size=13, pady=10, padx=20).pack(side='left', padx=6)
        make_button(btn_frame, "💾 Export CSV", self.export_csv, Theme.WARNING, size=13, pady=10, padx=20).pack(side='left', padx=6)
        make_button(btn_frame, "📥 Import CSV", self.import_csv, Theme.SUCCESS, size=13, pady=10, padx=20).pack(side='left', padx=6)

        chart_holder = tk.Frame(self.content_frame, bg=Theme.BG)
        chart_holder.pack(fill='both', expand=True, padx=40, pady=10)

        self.render_pie_chart(chart_holder)

    def _clear_frame(self, frame):
        for w in frame.winfo_children():
            w.destroy()

    def _themed_figure(self, figsize=(7.5, 5)):
        fig = Figure(figsize=figsize, dpi=100)
        fig.patch.set_facecolor(Theme.BG)
        ax = fig.add_subplot(111)
        ax.set_facecolor(Theme.BG)
        for spine in ax.spines.values():
            spine.set_color(Theme.BORDER)
        ax.tick_params(colors=Theme.TEXT_DIM)
        ax.title.set_color(Theme.TEXT)
        ax.xaxis.label.set_color(Theme.TEXT_DIM)
        ax.yaxis.label.set_color(Theme.TEXT_DIM)
        return fig, ax

    def render_pie_chart(self, holder):
        self._clear_frame(holder)
        expenses = [t for t in self.profile_data.get('transactions', []) if t['type'] == 'expense']
        if not expenses:
            tk.Label(holder, text="No expense data yet. Add some expenses first!", font=(Theme.FONT, 13),
                     bg=Theme.BG, fg=Theme.TEXT_DIM).pack(pady=60)
            return
        categories = defaultdict(float)
        for t in expenses:
            categories[t['category']] += t['amount']
        colors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#f9ca24', '#ff9ff3', '#00d2d3', '#2ed573', '#feca57', '#6c5ce7']

        fig, ax = self._themed_figure()
        wedges, texts, autotexts = ax.pie(categories.values(), labels=categories.keys(),
                                           colors=colors[:len(categories)], autopct='%1.1f%%', startangle=140,
                                           textprops={'color': Theme.TEXT, 'fontsize': 9})
        ax.set_title('Spending by Category')

        canvas = FigureCanvasTkAgg(fig, master=holder)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)

    def render_monthly_chart(self, holder):
        self._clear_frame(holder)
        transactions = self.profile_data.get('transactions', [])
        if not transactions:
            tk.Label(holder, text="No transaction data yet.", font=(Theme.FONT, 13), bg=Theme.BG,
                     fg=Theme.TEXT_DIM).pack(pady=60)
            return

        monthly_income = defaultdict(float)
        monthly_expense = defaultdict(float)
        for t in transactions:
            try:
                month_key = datetime.strptime(t['date'], "%Y-%m-%d %H:%M").strftime("%Y-%m")
            except ValueError:
                month_key = t['date'][:7]
            if t['type'] == 'income':
                monthly_income[month_key] += t['amount']
            else:
                monthly_expense[month_key] += t['amount']

        months = sorted(set(monthly_income) | set(monthly_expense))
        income_vals = [monthly_income.get(m, 0) for m in months]
        expense_vals = [monthly_expense.get(m, 0) for m in months]

        fig, ax = self._themed_figure()
        x = range(len(months))
        width = 0.38
        ax.bar([i - width / 2 for i in x], income_vals, width, label='Income', color=Theme.SUCCESS)
        ax.bar([i + width / 2 for i in x], expense_vals, width, label='Expense', color=Theme.DANGER)
        ax.set_xticks(list(x))
        ax.set_xticklabels(months, rotation=45, ha='right', fontsize=9)
        ax.set_title('Monthly Income vs Expense')
        legend = ax.legend(facecolor=Theme.CARD, edgecolor=Theme.BORDER, labelcolor=Theme.TEXT)
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=holder)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)

    # ----- import / export -------------------------------------------------
    def export_csv(self):
        if not self.profile_data.get('transactions'):
            messagebox.showwarning("No Data", "No transactions to export!")
            return
        filename = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if filename:
            try:
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=['date', 'amount', 'category', 'type', 'note'])
                    writer.writeheader()
                    writer.writerows(self.profile_data['transactions'])
                messagebox.showinfo("✅ Success", "Transactions exported!")
            except Exception as e:
                messagebox.showerror("Error", f"Export failed: {str(e)}")

    def import_csv(self):
        filename = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if not filename:
            return
        try:
            imported = 0
            with open(filename, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if not {'date', 'amount', 'category', 'type'}.issubset(row.keys()):
                        continue
                    try:
                        amount = float(row['amount'])
                    except (ValueError, TypeError):
                        continue
                    if row['type'] not in ('income', 'expense'):
                        continue
                    self.profile_data['transactions'].append({
                        'date': row['date'] or datetime.now().strftime("%Y-%m-%d %H:%M"),
                        'amount': amount, 'category': row['category'] or 'Other',
                        'type': row['type'], 'note': row.get('note') or None
                    })
                    imported += 1
            self.save_profile_data()
            messagebox.showinfo("✅ Import Complete", f"Imported {imported} transactions.")
            self.show_transactions()
        except Exception as e:
            messagebox.showerror("Error", f"Import failed: {str(e)}")

    # ----- profile page -------------------------------------------------
    def show_profile(self):
        self.clear_content()
        profile = self.profiles[self.current_profile]
        section_title(self.content_frame, "👤 Profile Info", pady=(30, 20))
        info_frame = tk.Frame(self.content_frame, bg=Theme.BG_LIGHT, highlightbackground=Theme.BORDER,
                               highlightthickness=1)
        info_frame.pack(pady=10, padx=200, fill='x')
        tk.Label(info_frame, text=f"Name: {profile['name']}", font=(Theme.FONT, 20, 'bold'), bg=Theme.BG_LIGHT,
                 fg=Theme.TEXT).pack(pady=(20, 6))
        tk.Label(info_frame, text=f"Category: {profile['category']}", font=(Theme.FONT, 16), bg=Theme.BG_LIGHT,
                 fg=Theme.ACCENT).pack(pady=4)
        tk.Label(info_frame, text=f"Savings Rate: {profile.get('savings_percent', 0)}%", font=(Theme.FONT, 16),
                 bg=Theme.BG_LIGHT, fg=Theme.WARNING).pack(pady=4)
        tk.Label(info_frame, text=f"Currency: {profile.get('currency', '₹')}", font=(Theme.FONT, 16),
                 bg=Theme.BG_LIGHT, fg=Theme.TEXT_DIM).pack(pady=4)
        tk.Label(info_frame, text=f"Base Budget: {self.fmt(self.profile_data.get('budget', 10000))}",
                 font=(Theme.FONT, 16), bg=Theme.BG_LIGHT, fg=Theme.SUCCESS).pack(pady=4)

        btn_frame = tk.Frame(info_frame, bg=Theme.BG_LIGHT)
        btn_frame.pack(pady=25)
        make_button(btn_frame, "💼 Set Budget", self.set_budget_dialog, Theme.SUCCESS, size=13, pady=12,
                    padx=20).pack(side='left', padx=10)
        make_button(btn_frame, "✏️ Edit Profile", self.show_edit_profile, Theme.ACCENT, size=13, pady=12,
                    padx=20).pack(side='left', padx=10)
        make_button(btn_frame, "🔙 Switch Profile", self.show_profile_screen, Theme.ACCENT2, size=13, pady=12,
                    padx=20).pack(side='left', padx=10)
        make_button(btn_frame, "🗑️ Delete Profile", lambda: self.delete_profile(self.current_profile),
                    Theme.DANGER, size=13, pady=12, padx=20).pack(side='left', padx=10)


if __name__ == "__main__":
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    root = tk.Tk()
    app = BudgetTracker(root)
    root.mainloop()
