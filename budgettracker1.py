import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
from datetime import datetime
import csv
from collections import defaultdict
import matplotlib.pyplot as plt
import pathlib

plt.rcParams['figure.dpi'] = 100

class BudgetTracker:
    def __init__(self, root):
        self.root = root
        self.root.title("BudgetPro - Professional")
       
        try:
            self.root.state('zoomed')
        except:
            self.root.geometry("1400x900")
           
        self.root.configure(bg='#0f0f23')
       
        self.data_dir = self.ensure_data_directory()
        self.data_file = os.path.join(self.data_dir, 'profiles_data.json')
       
        self.current_profile = None
        self.profiles = self.load_profiles()
        self.profile_data = {}
       
        self.root.bind_all("<MouseWheel>", self._on_mousewheel)
        self.root.bind_all("<Button-4>", self._on_mousewheel)
        self.root.bind_all("<Button-5>", self._on_mousewheel)
       
        self.show_profile_screen()

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
                suggestions.append(f"💡 SUGGESTION: You've made {count} transactions in {cat} recently. Consider a monthly bulk budget for this.")

        total_saved = sum(s['amount'] for s in self.profile_data.get('savings_vault', []))
        if balance > 0 and total_saved < (balance * 0.2):
            suggestions.append("📉 ADVICE: Your savings vault is low relative to spending. Consider increasing your auto-save %.")

        return "\n\n".join(suggestions) if suggestions else "✅ Your spending pattern looks stable."

    def get_current_balance(self):
        total_spent = sum(t['amount'] for t in self.profile_data.get('transactions', []) if t['type'] == 'expense')
        total_income = sum(t['amount'] for t in self.profile_data.get('transactions', []) if t['type'] == 'income')
        return self.profile_data.get('budget', 10000) + total_income - total_spent

    def _on_mousewheel(self, event):
        for widget in self.root.winfo_children():
            canvas = self._find_canvas(widget)
            if canvas:
                if event.num == 4:
                    canvas.yview_scroll(-1, "units")
                elif event.num == 5:
                    canvas.yview_scroll(1, "units")
                else:
                    canvas.yview_scroll(int(-1*(event.delta/120)), "units")
                break

    def _find_canvas(self, widget):
        if isinstance(widget, tk.Canvas): return widget
        for child in widget.winfo_children():
            res = self._find_canvas(child)
            if res: return res
        return None
   
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
   
    def delete_profile(self, profile_id):
        profile_name = self.profiles[profile_id]['name']
        if messagebox.askyesno("Delete Profile", f"Delete profile '{profile_name}'?\nThis will remove ALL data permanently."):
            if messagebox.askokcancel("⚠️ FINAL WARNING", f"ARE YOU SURE?\n\n'{profile_name}' and all transactions will be PERMANENTLY DELETED.", icon='warning'):
                try:
                    profile_file = os.path.join(self.data_dir, f"{profile_id}.json")
                    if os.path.exists(profile_file): os.remove(profile_file)
                    del self.profiles[profile_id]
                    self.save_profiles()
                    messagebox.showinfo("✅ Success", f"Profile '{profile_name}' deleted!")
                    if self.current_profile == profile_id:
                        self.current_profile = None
                        self.profile_data = {}
                    self.show_profile_screen()
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to delete profile: {str(e)}")

    def delete_transaction(self, transaction):
        if messagebox.askyesno("Delete", "Remove this transaction?"):
            self.profile_data['transactions'].remove(transaction)
            self.save_profile_data()
            self.show_transactions()

    def save_profile_data(self):
        if self.current_profile:
            profile_file = os.path.join(self.data_dir, f"{self.current_profile}.json")
            try:
                os.makedirs(os.path.dirname(profile_file), exist_ok=True)
                with open(profile_file, 'w', encoding='utf-8') as f:
                    json.dump(self.profile_data, f, indent=2)
            except Exception as e:
                print(f"Error saving profile data: {e}")

    def show_profile_screen(self):
        self.clear_root()
        bg = tk.Label(self.root, text="BudgetPro", font=('Segoe UI', 48, 'bold'), bg='#0f0f23', fg='#00d4ff')
        bg.pack(pady=(50, 0))
        main_frame = tk.Frame(self.root, bg='#0f0f23')
        main_frame.pack(expand=True, fill='both', padx=100, pady=50)
       
        if self.profiles:
            self.show_existing_profiles(main_frame)
        else:
            self.show_first_time(main_frame)

    def show_existing_profiles(self, parent):
        tk.Label(parent, text="Choose Your Profile", font=('Segoe UI', 20, 'bold'), bg='#0f0f23', fg='white').pack(pady=20)
        canvas = tk.Canvas(parent, bg='#1a1a2e', highlightthickness=0, height=400)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_container = tk.Frame(canvas, bg='#1a1a2e')
        scrollable_container.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_container, anchor="nw", width=800)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True, padx=(150, 0))
        scrollbar.pack(side="left", fill="y")

        for profile_id, data in self.profiles.items():
            self.create_profile_card(scrollable_container, profile_id, data)
       
        new_btn = tk.Button(parent, text="➕ Create New Profile", font=('Segoe UI', 16, 'bold'), bg='#ff6b6b', fg='white', bd=0, pady=15, padx=40, command=self.show_create_profile)
        new_btn.pack(pady=20)

    def create_profile_card(self, parent, profile_id, data):
        card = tk.Frame(parent, bg='#2a2a3e', relief='flat', bd=2)
        card.pack(fill='x', padx=50, pady=10)
        pic = tk.Label(card, text="👤", font=('Segoe UI', 24), bg='#4ecdc4', fg='white', width=4)
        pic.pack(side='left', padx=20, pady=10)
        info_frame = tk.Frame(card, bg='#2a2a3e')
        info_frame.pack(side='left', padx=20)
        tk.Label(info_frame, text=data['name'], font=('Segoe UI', 16, 'bold'), bg='#2a2a3e', fg='white').pack(anchor='w')
        tk.Label(info_frame, text=f"{data['category']} | Savings: {data.get('savings_percent', 0)}%", font=('Segoe UI', 12), bg='#2a2a3e', fg='#00d4ff').pack(anchor='w')
        tk.Button(card, text="LAUNCH", font=('Segoe UI', 12, 'bold'), bg='#00d2d3', fg='white', bd=0, padx=20, command=lambda p=profile_id: self.load_profile(p)).pack(side='right', padx=20)

    def show_first_time(self, parent):
        tk.Label(parent, text="🎉 First Time? Create Profile!", font=('Segoe UI', 22, 'bold'), bg='#0f0f23', fg='white').pack(pady=50)
        tk.Button(parent, text="➕ Create Your Profile", font=('Segoe UI', 20, 'bold'), bg='#ff9ff3', fg='white', bd=0, pady=25, padx=60, command=self.show_create_profile).pack(pady=30)

    def show_create_profile(self):
        self.clear_root()
        tk.Label(self.root, text="➕ Create Profile", font=('Segoe UI', 32, 'bold'), bg='#0f0f23', fg='white').pack(pady=30)
        form = tk.Frame(self.root, bg='#1a1a2e', relief='raised', bd=1)
        form.pack(pady=10, padx=200)
       
        tk.Label(form, text="Name", font=('Segoe UI', 14, 'bold'), bg='#1a1a2e', fg='white').pack(pady=(15, 2))
        name_entry = tk.Entry(form, font=('Segoe UI', 16), width=25, bg='#2a2a3e', fg='white', insertbackground='white')
        name_entry.pack(pady=5, padx=50)
       
        tk.Label(form, text="Category", font=('Segoe UI', 14, 'bold'), bg='#1a1a2e', fg='white').pack(pady=(15, 2))
        category_var = tk.StringVar(value="Student")
        combo_cat = ttk.Combobox(form, textvariable=category_var, values=["Student", "Employee", "Freelancer", "Business"], font=('Segoe UI', 14), state='readonly', width=22)
        combo_cat.pack(pady=5)

        tk.Label(form, text="💰 Automatic Savings (%)", font=('Segoe UI', 14, 'bold'), bg='#1a1a2e', fg='#feca57').pack(pady=(15, 2))
        savings_var = tk.StringVar(value="10%")
        savings_options = ["0%", "5%", "10%", "15%", "20%", "25%", "30%", "50%"]
        combo_save = ttk.Combobox(form, textvariable=savings_var, values=savings_options, font=('Segoe UI', 14), state='readonly', width=22)
        combo_save.pack(pady=5)
       
        def save_profile():
            name = name_entry.get().strip()
            if not name:
                messagebox.showerror("Error", "Enter your name!")
                return
           
            p_id = f"profile_{int(datetime.now().timestamp())}"
            s_val = int(savings_var.get().replace('%', ''))
           
            self.profiles[p_id] = {
                'name': name,
                'category': category_var.get(),
                'savings_percent': s_val,
                'created': datetime.now().strftime("%Y-%m-%d")
            }
           
            if self.save_profiles():
                self.current_profile = p_id
                self.profile_data = {
                    'budget': 10000,
                    'transactions': [],
                    'savings_vault': [],
                    'created': datetime.now().strftime("%Y-%m-%d")
                }
                self.save_profile_data()
                self.show_main_app()
       
        tk.Button(form, text="✅ CREATE PROFILE", command=save_profile, font=('Segoe UI', 16, 'bold'), bg='#00b894', fg='white', bd=0, pady=12, padx=50).pack(pady=20)
        tk.Button(form, text="🔙 Back", command=self.show_profile_screen, font=('Segoe UI', 12), bg='#6c5ce7', fg='white', bd=0, pady=8, padx=25).pack(pady=(0, 15))

    def load_profile(self, profile_id):
        self.current_profile = profile_id
        profile_file = os.path.join(self.data_dir, f"{profile_id}.json")
        try:
            if os.path.exists(profile_file):
                with open(profile_file, 'r', encoding='utf-8') as f:
                    self.profile_data = json.load(f)
                    if 'savings_vault' not in self.profile_data: self.profile_data['savings_vault'] = []
            else:
                self.profile_data = {'budget': 10000, 'transactions': [], 'savings_vault': []}
        except:
            self.profile_data = {'budget': 10000, 'transactions': [], 'savings_vault': []}
        self.show_main_app()

    def clear_root(self):
        for widget in self.root.winfo_children(): widget.destroy()

    def show_main_app(self):
        self.clear_root()
        top_bar = tk.Frame(self.root, bg='#1a1a2e', height=70)
        top_bar.pack(fill='x')
        top_bar.pack_propagate(False)
       
        tk.Button(top_bar, text="☰", font=('Segoe UI', 24, 'bold'), bg='#1a1a2e', fg='white', bd=0, width=3, command=self.toggle_menu).pack(side='left', padx=20)
       
        p_name = self.profiles[self.current_profile]['name']
        tk.Label(top_bar, text=f"Hi, {p_name}!", font=('Segoe UI', 18, 'bold'), bg='#1a1a2e', fg='#00d4ff').pack(side='left', padx=10)
       
        self.main_container = tk.Frame(self.root, bg='#0f0f23')
        self.main_container.pack(fill='both', expand=True)
       
        self.content_frame = tk.Frame(self.main_container, bg='#0f0f23')
        self.content_frame.place(x=0, y=0, relwidth=1, relheight=1)
       
        self.sidebar = tk.Frame(self.main_container, width=300, bg='#2a2a3e')
        self.sidebar.place(x=-300, y=0, relheight=1)
       
        tk.Label(self.sidebar, text="📋 Menu", font=('Segoe UI', 20, 'bold'), bg='#2a2a3e', fg='white').pack(pady=30)
       
        menu_items = [
            ("📊 Dashboard", self.show_dashboard),
            ("💸 Expense", self.show_expense),
            ("💰 Income", self.show_income),
            ("🏦 Savings Vault", self.show_savings),
            ("📜 Transactions", self.show_transactions),
            ("📈 Analysis", self.show_analysis),
            ("👤 Profile", self.show_profile)
        ]
       
        for text, cmd in menu_items:
            tk.Button(self.sidebar, text=text, font=('Segoe UI', 16, 'bold'), bg='#3a3a4e', fg='white', bd=0, pady=15, anchor='w', command=lambda c=cmd: [self.toggle_menu(), c()], cursor='hand2', padx=30).pack(fill='x')
       
        self.show_dashboard()

    def toggle_menu(self):
        if self.sidebar.winfo_x() < 0:
            self.sidebar.place(x=0); self.sidebar.lift()
        else:
            self.sidebar.place(x=-300)

    def clear_content(self):
        for widget in self.content_frame.winfo_children(): widget.destroy()

    def show_dashboard(self):
        self.clear_content()
        tk.Label(self.content_frame, text="📊 Dashboard", font=('Segoe UI', 32, 'bold'), bg='#0f0f23', fg='white').pack(pady=40)
       
        insight_text = self.get_ai_insights()
        insight_box = tk.Label(self.content_frame, text=insight_text, font=('Segoe UI', 12, 'italic'), bg='#1a1a2e', fg='#00d4ff', pady=10, padx=20, relief='groove')
        insight_box.pack(pady=10, fill='x', padx=100)

        stats_frame = tk.Frame(self.content_frame, bg='#0f0f23')
        stats_frame.pack(pady=30)
       
        total_spent = sum(t['amount'] for t in self.profile_data.get('transactions', []) if t['type'] == 'expense')
        total_income = sum(t['amount'] for t in self.profile_data.get('transactions', []) if t['type'] == 'income')
        total_saved = sum(s['amount'] for s in self.profile_data.get('savings_vault', []))
        balance = self.get_current_balance()
       
        cards = [
            ("💸 Total Spent", f"₹{total_spent:,.0f}", '#ff6b6b'),
            ("🏦 Total Saved", f"₹{total_saved:,.0f}", '#feca57'),
            ("💳 Current Balance", f"₹{balance:,.0f}", '#4ecdc4')
        ]
       
        for i, (label, value, color) in enumerate(cards):
            card = tk.Frame(stats_frame, bg=color, width=350, height=160)
            card.grid(row=0, column=i, padx=25, pady=25); card.pack_propagate(False)
            tk.Label(card, text=label, font=('Segoe UI', 16, 'bold'), fg='white', bg=color).pack(pady=(25, 10))
            tk.Label(card, text=value, font=('Segoe UI', 28, 'bold'), fg='white', bg=color).pack()

    def show_expense(self):
        self.clear_content()
        canvas = tk.Canvas(self.content_frame, bg='#0f0f23', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.content_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#0f0f23')
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=self.root.winfo_width())
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        tk.Label(scrollable_frame, text="💸 Add Expense", font=('Segoe UI', 32, 'bold'), bg='#0f0f23', fg='white').pack(pady=40)
        form = tk.Frame(scrollable_frame, bg='#1a1a2e', bd=1)
        form.pack(pady=10, padx=200)
       
        tk.Label(form, text="💸 Amount (₹)", font=('Segoe UI', 18, 'bold'), bg='#1a1a2e', fg='white').pack(pady=20)
        amount_entry = tk.Entry(form, font=('Segoe UI', 20), width=20, bg='#2a2a3e', fg='white', insertbackground='white')
        amount_entry.pack(pady=10, padx=60)
       
        balance_label = tk.Label(form, text=f"💳 Available Balance: ₹{self.get_current_balance():,.0f}", font=('Segoe UI', 14), bg='#1a1a2e', fg='#4ecdc4')
        balance_label.pack(pady=(10, 0))
       
        cat_var = tk.StringVar(value="🍚 Food")
        cats = ["🍚 Food", "🚗 Transport", "📚 Study", "🎮 Fun", "🛍️ Shopping", "🏠 Bills", "💊 Health", "📱 Mobile"]
        combo = ttk.Combobox(form, textvariable=cat_var, values=cats, font=('Segoe UI', 16), state='readonly', width=22)
        combo.pack(pady=20)
       
        def add_expense():
            try:
                amount = float(amount_entry.get())
                if amount <= 0: raise ValueError
                ai_warning = self.get_ai_insights(amount)
                if "⚠️" in ai_warning:
                    if not messagebox.askyesno("AI Financial Warning", f"{ai_warning}\n\nDo you still want to proceed?"):
                        return
                curr_bal = self.get_current_balance()
                if amount > curr_bal:
                    messagebox.showerror("❌ Error", f"Insufficient funds! Available: ₹{curr_bal:,.0f}")
                    return
                self.profile_data['transactions'].append({
                    'date': datetime.now().strftime("%Y-%m-%d %H:%M"), 'amount': amount,
                    'category': cat_var.get(), 'type': 'expense', 'note': None
                })
                self.save_profile_data()
                messagebox.showinfo("✅ Success", f"Added ₹{amount:,.0f}")
                amount_entry.delete(0, tk.END)
                balance_label.config(text=f"💳 Available Balance: ₹{self.get_current_balance():,.0f}")
            except: messagebox.showerror("❌ Error", "Invalid amount!")
       
        tk.Button(form, text="➕ ADD EXPENSE", command=add_expense, font=('Segoe UI', 18, 'bold'), bg='#ff4757', fg='white', bd=0, pady=18, padx=60).pack(pady=30)

    def show_income(self):
        self.clear_content()
        tk.Label(self.content_frame, text="💰 Add Income", font=('Segoe UI', 32, 'bold'), bg='#0f0f23', fg='white').pack(pady=40)
        form = tk.Frame(self.content_frame, bg='#1a1a2e', bd=1)
        form.pack(pady=10, padx=200)
       
        tk.Label(form, text="💸 Amount (₹)", font=('Segoe UI', 18, 'bold'), bg='#1a1a2e', fg='white').pack(pady=20)
        amount_entry = tk.Entry(form, font=('Segoe UI', 20), width=20, bg='#2a2a3e', fg='white', insertbackground='white')
        amount_entry.pack(pady=10, padx=60)
       
        save_pct = self.profiles[self.current_profile].get('savings_percent', 0)
        tk.Label(form, text=f"✨ Auto-Savings Active: {save_pct}%", font=('Segoe UI', 12), bg='#1a1a2e', fg='#feca57').pack()

        def add_income():
            try:
                gross_amount = float(amount_entry.get())
                if gross_amount <= 0: raise ValueError
                savings_deduction = (gross_amount * save_pct) / 100
                net_income = gross_amount - savings_deduction
                self.profile_data['transactions'].append({
                    'date': datetime.now().strftime("%Y-%m-%d %H:%M"), 'amount': net_income,
                    'category': 'Income (Net)', 'type': 'income', 'note': f"Gross: ₹{gross_amount}"
                })
                if savings_deduction > 0:
                    self.profile_data['savings_vault'].append({
                        'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
                        'amount': savings_deduction,
                        'source': f"Income of ₹{gross_amount}"
                    })
                self.save_profile_data()
                messagebox.showinfo("✅ Success", f"Net Income: ₹{net_income:,.0f}\nSaved: ₹{savings_deduction:,.0f}")
                amount_entry.delete(0, tk.END)
            except: messagebox.showerror("❌ Error", "Invalid amount!")
       
        tk.Button(form, text="➕ ADD INCOME", command=add_income, font=('Segoe UI', 18, 'bold'), bg='#2ed573', fg='white', bd=0, pady=18, padx=60).pack(pady=30)

    def show_savings(self):
        self.clear_content()
        tk.Label(self.content_frame, text="🏦 Savings Vault", font=('Segoe UI', 32, 'bold'), bg='#0f0f23', fg='#feca57').pack(pady=40)
        vault = self.profile_data.get('savings_vault', [])
        total_saved = sum(s['amount'] for s in vault)
        tk.Label(self.content_frame, text=f"Total Vault Balance: ₹{total_saved:,.0f}", font=('Segoe UI', 24, 'bold'), bg='#0f0f23', fg='white').pack(pady=10)

        canvas = tk.Canvas(self.content_frame, bg='#0f0f23', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.content_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#0f0f23')
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=1000)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True, padx=50)
        scrollbar.pack(side="right", fill="y")

        for s in reversed(vault):
            card = tk.Frame(scrollable_frame, bg='#2a2a3e', pady=10)
            card.pack(fill='x', pady=5)
            tk.Label(card, text=f"₹{s['amount']:,.0f}", font=('Segoe UI', 18, 'bold'), fg='#2ed573', bg='#2a2a3e').pack(side='left', padx=20)
            tk.Label(card, text=f"Saved from {s['source']}\n{s['date']}", font=('Segoe UI', 10), fg='white', bg='#2a2a3e', justify='left').pack(side='left', padx=10)

    def show_transactions(self):
        self.clear_content()
        tk.Label(self.content_frame, text="📜 Transaction History", font=('Segoe UI', 32, 'bold'), bg='#0f0f23', fg='white').pack(pady=40)
        transactions = self.profile_data.get('transactions', [])
        canvas = tk.Canvas(self.content_frame, bg='#0f0f23', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.content_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#0f0f23')
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=1100)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True, padx=50)
        scrollbar.pack(side="right", fill="y")
       
        for trans in reversed(transactions[-50:]):
            color = '#ff6b6b' if trans['type'] == 'expense' else '#2ed573'
            card = tk.Frame(scrollable_frame, bg=color, relief='flat')
            card.pack(fill='x', padx=30, pady=5)
            tk.Label(card, text=f"₹{trans['amount']:,.0f}", font=('Segoe UI', 20, 'bold'), fg='white', bg=color).pack(side='left', padx=20, pady=15)
            tk.Label(card, text=f"{trans['category']}\n{trans['date']}", font=('Segoe UI', 11), fg='white', bg=color, justify='left').pack(side='left', padx=10)
            tk.Button(card, text="🗑️", font=('Segoe UI', 12), bg=color, fg='white', bd=0, command=lambda t=trans: self.delete_transaction(t)).pack(side='right', padx=15)

    def show_analysis(self):
        self.clear_content()
        tk.Label(self.content_frame, text="📈 Analysis", font=('Segoe UI', 32, 'bold'), bg='#0f0f23', fg='white').pack(pady=50)
        btn_frame = tk.Frame(self.content_frame, bg='#0f0f23')
        btn_frame.pack(pady=50)
        tk.Button(btn_frame, text="📊 Show Pie Chart", font=('Segoe UI', 18, 'bold'), bg='#ff9ff3', fg='white', bd=0, pady=20, padx=60, command=self.show_pie_chart).pack(pady=10)
        tk.Button(btn_frame, text="💾 Export CSV", font=('Segoe UI', 18, 'bold'), bg='#00d2d3', fg='white', bd=0, pady=20, padx=80, command=self.export_csv).pack(pady=10)

    def show_profile(self):
        self.clear_content()
        profile = self.profiles[self.current_profile]
        tk.Label(self.content_frame, text="👤 Profile Info", font=('Segoe UI', 32, 'bold'), bg='#0f0f23', fg='white').pack(pady=50)
        info_frame = tk.Frame(self.content_frame, bg='#1a1a2e', bd=1)
        info_frame.pack(pady=30, padx=200, fill='x')
        tk.Label(info_frame, text=f"Name: {profile['name']}", font=('Segoe UI', 20, 'bold'), bg='#1a1a2e', fg='white').pack(pady=20)
        tk.Label(info_frame, text=f"Category: {profile['category']}", font=('Segoe UI', 18), bg='#1a1a2e', fg='#00d4ff').pack(pady=10)
        tk.Label(info_frame, text=f"Savings Rate: {profile.get('savings_percent', 0)}%", font=('Segoe UI', 18), bg='#1a1a2e', fg='#feca57').pack(pady=10)
       
        btn_frame = tk.Frame(info_frame, bg='#1a1a2e')
        btn_frame.pack(pady=30)
        tk.Button(btn_frame, text="✏️ Edit Profile", command=self.show_edit_profile, font=('Segoe UI', 14, 'bold'), bg='#4ecdc4', fg='white', bd=0, pady=15, padx=30).pack(side='left', padx=20)
        tk.Button(btn_frame, text="🔙 Switch Profile", command=self.show_profile_screen, font=('Segoe UI', 14, 'bold'), bg='#6c5ce7', fg='white', bd=0, pady=15, padx=30).pack(side='left', padx=20)
        tk.Button(btn_frame, text="🗑️ Delete Profile", command=lambda: self.delete_profile(self.current_profile), font=('Segoe UI', 14, 'bold'), bg='#ff4757', fg='white', bd=0, pady=15, padx=30).pack(side='left', padx=20)

    def show_edit_profile(self):
        self.clear_content()
        profile = self.profiles[self.current_profile]
        tk.Label(self.content_frame, text="✏️ Edit Profile", font=('Segoe UI', 32, 'bold'), bg='#0f0f23', fg='white').pack(pady=30)
        form = tk.Frame(self.content_frame, bg='#1a1a2e', relief='raised', bd=1)
        form.pack(pady=10, padx=200)
       
        tk.Label(form, text="Name", font=('Segoe UI', 14, 'bold'), bg='#1a1a2e', fg='white').pack(pady=(15, 2))
        name_entry = tk.Entry(form, font=('Segoe UI', 16), width=25, bg='#2a2a3e', fg='white', insertbackground='white')
        name_entry.insert(0, profile['name'])
        name_entry.pack(pady=5, padx=50)
       
        tk.Label(form, text="Category", font=('Segoe UI', 14, 'bold'), bg='#1a1a2e', fg='white').pack(pady=(15, 2))
        category_var = tk.StringVar(value=profile['category'])
        combo_cat = ttk.Combobox(form, textvariable=category_var, values=["Student", "Employee", "Freelancer", "Business"], font=('Segoe UI', 14), state='readonly', width=22)
        combo_cat.pack(pady=5)

        tk.Label(form, text="💰 Automatic Savings (%)", font=('Segoe UI', 14, 'bold'), bg='#1a1a2e', fg='#feca57').pack(pady=(15, 2))
        savings_var = tk.StringVar(value=f"{profile.get('savings_percent', 0)}%")
        savings_options = ["0%", "5%", "10%", "15%", "20%", "25%", "30%", "50%"]
        combo_save = ttk.Combobox(form, textvariable=savings_var, values=savings_options, font=('Segoe UI', 14), state='readonly', width=22)
        combo_save.pack(pady=5)
       
        def update_profile():
            name = name_entry.get().strip()
            if not name:
                messagebox.showerror("Error", "Enter your name!")
                return
            s_val = int(savings_var.get().replace('%', ''))
            self.profiles[self.current_profile].update({
                'name': name,
                'category': category_var.get(),
                'savings_percent': s_val
            })
            if self.save_profiles():
                messagebox.showinfo("✅ Success", "Profile updated successfully!")
                self.show_main_app()
       
        tk.Button(form, text="💾 SAVE CHANGES", command=update_profile, font=('Segoe UI', 16, 'bold'), bg='#00b894', fg='white', bd=0, pady=12, padx=50).pack(pady=20)
        tk.Button(form, text="🔙 Cancel", command=self.show_profile, font=('Segoe UI', 12), bg='#6c5ce7', fg='white', bd=0, pady=8, padx=25).pack(pady=(0, 15))

    def show_pie_chart(self):
        expenses = [t for t in self.profile_data.get('transactions', []) if t['type'] == 'expense']
        if not expenses:
            messagebox.showwarning("No Data", "Add expenses first!")
            return
        categories = defaultdict(float)
        for t in expenses: categories[t['category']] += t['amount']
        colors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#f9ca24', '#ff9ff3', '#00d2d3', '#2ed573']
        plt.figure(figsize=(10, 7))
        plt.pie(categories.values(), labels=categories.keys(), colors=colors[:len(categories)], autopct='%1.1f%%', startangle=140)
        plt.title('Spending by Category')
        plt.show()

    def export_csv(self):
        if not self.profile_data.get('transactions'):
            messagebox.showwarning("No Data", "No transactions!")
            return
        filename = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if filename:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['date', 'amount', 'category', 'type', 'note'])
                writer.writeheader()
                writer.writerows(self.profile_data['transactions'])
            messagebox.showinfo("Success", "Exported!")

if __name__ == "__main__":
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    root = tk.Tk()
    app = BudgetTracker(root)
    root.mainloop()
