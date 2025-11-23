import tkinter as tk
from tkinter import ttk, font

def setup_styling(root):
    """Configures the ttk style for a more modern look."""
    
    # --- Define Colors ---
    BG_COLOR = "#2E2E2E"       # Dark grey background
    CONTENT_BG = "#3C3C3C"     # Lighter grey for content areas (text boxes, frames)
    TEXT_COLOR = "#E0E0E0"     # Light grey text
    ACCENT_COLOR = "#007ACC"    # Blue accent for buttons/highlights
    BORDER_COLOR = "#4A4A4A"   # Subtle border color
    CODE_BG = "#1E1E1E"       # Dark background for code/text areas
    
    style = ttk.Style(root)
    
    try:
        style.theme_use('clam')
    except tk.TclError:
        print("Ttk 'clam' theme not available, using default.")
        return

    # --- Set Default Fonts ---
    try:
        default_font = font.nametofont("TkDefaultFont")
        default_font.configure(family="Arial", size=15)
        text_font = font.nametofont("TkTextFont")
        text_font.configure(family="Arial", size=15)
    except Exception as e:
        print(f"Font configuration error: {e}")

    # --- Configure Root Window ---
    root.configure(bg=BG_COLOR)

    # --- General Widget Styling ---
    style.configure('.',
                    background=BG_COLOR,
                    foreground=TEXT_COLOR,
                    fieldbackground=CONTENT_BG,
                    borderwidth=1,
                    font=("Arial", 12))
    style.map('.',
              background=[('disabled', '#555'), ('active', '#454545')],
              foreground=[('disabled', '#888')])

    # --- Frame and LabelFrame ---
    style.configure('TFrame', background=BG_COLOR)
    style.configure('TLabel', background=BG_COLOR, foreground=TEXT_COLOR)
    style.configure('TLabelframe',
                    background=BG_COLOR,
                    borderwidth=1,
                    relief="solid")
    style.configure('TLabelframe.Label',
                    background=BG_COLOR,
                    foreground=TEXT_COLOR)
    
    # --- Text Widgets (via Tk, not Ttk) ---
    # We can't style tk.Text directly with ttk, so we set its options in the library
    # But we can set the app-wide text color preference
    root.option_add("*Text.background", CONTENT_BG)
    root.option_add("*Text.foreground", TEXT_COLOR)
    root.option_add("*Text.insertBackground", TEXT_COLOR) # Cursor
    root.option_add("*Text.borderwidth", 1)
    root.option_add("*Text.relief", "solid")
    root.option_add("*Text.font", ("Arial", 12))

    # --- Button Styling ---
    style.configure('TButton',
                    background=ACCENT_COLOR,
                    foreground=TEXT_COLOR,
                    borderwidth=0,
                    padding=(10, 5),
                    font=("Arial", 10, "bold"))
    style.map('TButton',
              background=[('active', '#005FA3'), ('!disabled', ACCENT_COLOR)],
              relief=[('pressed', 'sunken'), ('!pressed', 'raised')])

    # --- Notebook (Tabs) ---
    style.configure('TNotebook',
                    background=BG_COLOR,
                    borderwidth=0,
                    tabposition='n')
    style.configure('TNotebook.Tab',
                    background=CONTENT_BG,
                    foreground=TEXT_COLOR,
                    padding=(8, 4),
                    borderwidth=0)
    style.map('TNotebook.Tab',
              background=[('selected', ACCENT_COLOR), ('active', '#555555')],
              foreground=[('selected', TEXT_COLOR), ('active', TEXT_COLOR)],
              padding=[('selected', (12, 6))],
              expand=[('selected', [1, 1, 1, 1])]) # Subtle expand

    # --- Scrollbar ---
    style.configure('Vertical.TScrollbar',
                    gripcount=0,
                    background=BG_COLOR,
                    darkcolor=CONTENT_BG,
                    lightcolor=CONTENT_BG,
                    troughcolor=BG_COLOR,
                    bordercolor=BG_COLOR,
                    arrowcolor=TEXT_COLOR)
    style.map('Vertical.TScrollbar',
              background=[('active', '#555')],
              gripcolor=[('active', '#888')])

    # --- Combobox (Dropdown) ---
    style.configure('TCombobox',
                    foreground='#000000',      # <-- SET TEXT TO BLACK
                    fieldbackground='#FFFFFF', # <-- SET FIELD TO WHITE
                    background=CONTENT_BG,
                    arrowcolor=TEXT_COLOR,
                    bordercolor=BORDER_COLOR)

    # Fix for readonly selection style
    style.map('TCombobox',
              fieldbackground=[('readonly', '#FFFFFF')],
              foreground=[('readonly', '#000000')],
              selectbackground=[('readonly', '#FFFFFF')],
              selectforeground=[('readonly', '#000000')]
              )

    # This makes the dropdown list match the theme
    root.option_add("*TCombobox*Listbox.background", CONTENT_BG)
    root.option_add("*TCombobox*Listbox.foreground", TEXT_COLOR)
    root.option_add("*TCombobox*Listbox.selectBackground", ACCENT_COLOR)
    root.option_add("*TCombobox*Listbox.selectForeground", TEXT_COLOR)
    
    # --- Checkbutton ---
    style.configure('TCheckbutton',
                    background=BG_COLOR,
                    foreground=TEXT_COLOR,
                    indicatorcolor=CONTENT_BG,
                    padding=5)
    style.map('TCheckbutton',
              indicatorcolor=[('selected', ACCENT_COLOR), ('!selected', CONTENT_BG)])