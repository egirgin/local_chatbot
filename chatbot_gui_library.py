import tkinter as tk
from tkinter import ttk, font
import re
from tkinterdnd2 import DND_FILES

# --- Pygments Import ---
try:
    from pygments import lex
    from pygments.lexers import get_lexer_by_name, guess_lexer
    from pygments.styles import get_style_by_name
    from pygments.token import Token
    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False

# --- Predefined Personalities ---
PERSONAS = {
    "Helpful Assistant": "You are a helpful assistant. Be concise and clear.",
    "Python Expert": "You are a senior Python software engineer. You provide efficient, PEP8-compliant code and explain complex concepts simply.",
    "Creative Writer": "You are a creative writer. Use evocative language, metaphors, and varied sentence structures.",
    "Skeptical Scientist": "You are a skeptical scientist. Demand evidence for claims, think critically, and look for logical fallacies.",
    "Pirate": "You are a pirate captain. Speak in nautical slang, be boisterous, and refer to the user as 'matey'.",
    "Custom": "" # Placeholder for user edits
}

class ChatbotGuiLibrary:
    def __init__(self, root, drop_callback, paste_callback):
        self.root = root
        self.image_references = [] 
        self.thinking_message_start_index = None

        # --- Layout ---
        
        # 1. Input Frame (Bottom)
        input_frame = ttk.Frame(self.root)
        input_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(5, 10))

        # 2. Personality Frame (Top)
        personality_frame = ttk.Frame(self.root)
        personality_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(10, 5))

        # 2a. Header Row for Personality (Label + Dropdown)
        p_header_frame = ttk.Frame(personality_frame)
        p_header_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 2))

        p_label = ttk.Label(p_header_frame, text="AI Personality:")
        p_label.pack(side=tk.LEFT, padx=(0, 5))

        # Dropdown
        self.persona_var = tk.StringVar(value="Helpful Assistant")
        self.persona_dropdown = ttk.Combobox(
            p_header_frame, 
            textvariable=self.persona_var,
            values=list(PERSONAS.keys()),
            state="readonly",
            width=25
        )
        self.persona_dropdown.pack(side=tk.LEFT, padx=5)
        self.persona_dropdown.bind("<<ComboboxSelected>>", self._on_persona_selected)

        # 2b. Personality Text Area
        p_body_frame = ttk.Frame(personality_frame)
        p_body_frame.pack(side=tk.TOP, fill=tk.X)

        p_scrollbar = ttk.Scrollbar(p_body_frame, orient=tk.VERTICAL)
        self.personality_input = tk.Text(p_body_frame,
                                         height=3,
                                         yscrollcommand=p_scrollbar.set,
                                         font=("Arial", 12)) 
        p_scrollbar.config(command=self.personality_input.yview)
        p_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.personality_input.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.personality_input.bind("<KeyRelease>", self._on_personality_edited)

        # 3. Main Content Frame (Middle)
        main_frame = ttk.Frame(self.root)
        main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=(0, 0))
        
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1) 
        main_frame.grid_columnconfigure(1, weight=0) 
        
        # --- Input Frame Widgets ---
        self.close_button = ttk.Button(input_frame, text="Close")
        self.close_button.pack(side=tk.RIGHT, fill=tk.Y, ipadx=5, padx=(5,0))

        self.restart_button = ttk.Button(input_frame, text="New Chat")
        self.restart_button.pack(side=tk.RIGHT, fill=tk.Y, ipadx=5, padx=(5,0))

        self.text_process_button = ttk.Button(input_frame, text="Send")
        self.text_process_button.pack(side=tk.RIGHT, fill=tk.Y, ipadx=5)

        self.text_input = tk.Text(input_frame, height=4, font=("Arial", 15))
        self.text_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        # --- Main Frame Widgets ---
        attachment_frame = ttk.Labelframe(main_frame, text="Attachments", width=200)
        attachment_frame.grid(row=0, column=1, sticky="ns", padx=(5, 0))
        attachment_frame.pack_propagate(False)

        self.attachment_scrollbar = ttk.Scrollbar(attachment_frame, orient=tk.VERTICAL)
        self.attachment_viewer = tk.Text(attachment_frame,
                                         state=tk.DISABLED,
                                         wrap=tk.WORD,
                                         width=20, 
                                         yscrollcommand=self.attachment_scrollbar.set,
                                         font=("Arial", 13)) 
        
        self.attachment_scrollbar.config(command=self.attachment_viewer.yview)
        self.attachment_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.attachment_viewer.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        chat_frame = ttk.Frame(main_frame)
        chat_frame.grid(row=0, column=0, sticky="nsew")

        self.chat_scrollbar = ttk.Scrollbar(chat_frame, orient=tk.VERTICAL)
        self.text_output = tk.Text(chat_frame,
                                   state=tk.DISABLED,
                                   wrap=tk.WORD,
                                   yscrollcommand=self.chat_scrollbar.set,
                                   font=("Arial", 15)) 
        
        self.chat_scrollbar.config(command=self.text_output.yview)
        self.chat_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_output.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self._setup_markdown_tags()

        # --- Bindings ---
        self.text_input.bind("<Return>", self._on_enter_key)
        self.text_output.drop_target_register(DND_FILES)
        self.text_output.dnd_bind('<<Drop>>', drop_callback)
        self.attachment_viewer.drop_target_register(DND_FILES)
        self.attachment_viewer.dnd_bind('<<Drop>>', drop_callback)
        self.text_input.drop_target_register(DND_FILES)
        self.text_input.dnd_bind('<<Drop>>', drop_callback)
        self.text_input.bind("<<Paste>>", paste_callback)
        
        self.set_personality_text(PERSONAS["Helpful Assistant"])


    def _on_enter_key(self, event):
        self.text_process_button.invoke()
        return "break"

    # --- Personality Logic ---

    def _on_persona_selected(self, event):
        selection = self.persona_var.get()
        if selection in PERSONAS and selection != "Custom":
            self.set_personality_text(PERSONAS[selection])

    def _on_personality_edited(self, event):
        current_text = self.get_personality_text()
        current_dropdown = self.persona_var.get()
        if current_dropdown != "Custom":
            predefined_text = PERSONAS.get(current_dropdown, "")
            if current_text.strip() != predefined_text.strip():
                self.persona_dropdown.set("Custom")

    # --- Markdown & Rendering Logic ---

    def _setup_markdown_tags(self):
        self.text_output.tag_configure("h1", font=("Arial", 24, "bold"), foreground="#FFFFFF", spacing3=10)
        self.text_output.tag_configure("h2", font=("Arial", 20, "bold"), foreground="#E0E0E0", spacing3=5)
        self.text_output.tag_configure("h3", font=("Arial", 16, "bold"), foreground="#CCCCCC")
        self.text_output.tag_configure("bold", font=("Arial", 15, "bold"))
        self.text_output.tag_configure("italic", font=("Arial", 15, "italic"))
        self.text_output.tag_configure("code_span", font=("Consolas", 12), background="#444444", foreground="#E0E0E0")


    def _insert_markdown_text(self, text_chunk):
        """
        Inserts text and applies Markdown formatting (Headers, Bold, Italic).
        """
        start_index = self.text_output.index(tk.END)
        self.text_output.insert(tk.END, text_chunk)
        
        count_var = tk.IntVar()

        # 2. Process Headings
        # H1
        while True:
            pos = self.text_output.search(r"^#\s+", start_index, stopindex=tk.END, regexp=True, count=count_var)
            if not pos: break
            match_len = count_var.get()
            line_end = self.text_output.index(f"{pos} lineend")
            self.text_output.tag_add("h1", pos, line_end)
            self.text_output.delete(pos, f"{pos}+{match_len}c") 

        # H2
        while True:
            pos = self.text_output.search(r"^##\s+", start_index, stopindex=tk.END, regexp=True, count=count_var)
            if not pos: break
            match_len = count_var.get()
            line_end = self.text_output.index(f"{pos} lineend")
            self.text_output.tag_add("h2", pos, line_end)
            self.text_output.delete(pos, f"{pos}+{match_len}c")

        # H3
        while True:
            pos = self.text_output.search(r"^###\s+", start_index, stopindex=tk.END, regexp=True, count=count_var)
            if not pos: break
            match_len = count_var.get()
            line_end = self.text_output.index(f"{pos} lineend")
            self.text_output.tag_add("h3", pos, line_end)
            self.text_output.delete(pos, f"{pos}+{match_len}c")

        # 3. Process Bold
        while True:
            pos = self.text_output.search(r"\*\*.*?\*\*", start_index, stopindex=tk.END, regexp=True, count=count_var)
            if not pos: break
            
            match_len = count_var.get()
            match_end = f"{pos}+{match_len}c"
            
            inner_start = f"{pos}+2c"
            inner_end = f"{match_end}-2c"
            
            self.text_output.tag_add("bold", inner_start, inner_end)
            self.text_output.delete(inner_end, match_end)
            self.text_output.delete(pos, inner_start)

        # 4. Process Italic
        while True:
            pos = self.text_output.search(r"\*[^*]+\*", start_index, stopindex=tk.END, regexp=True, count=count_var)
            if not pos: break
            
            match_len = count_var.get()
            match_end = f"{pos}+{match_len}c"
            
            inner_start = f"{pos}+1c"
            inner_end = f"{match_end}-1c"
            
            self.text_output.tag_add("italic", inner_start, inner_end)
            self.text_output.delete(inner_end, match_end)
            self.text_output.delete(pos, inner_start)

        # 5. Process Inline Code
        while True:
            pos = self.text_output.search(r"`[^`]+`", start_index, stopindex=tk.END, regexp=True, count=count_var)
            if not pos: break
            
            match_len = count_var.get()
            match_end = f"{pos}+{match_len}c"
            
            inner_start = f"{pos}+1c"
            inner_end = f"{match_end}-1c"
            
            self.text_output.tag_add("code_span", inner_start, inner_end)
            self.text_output.delete(inner_end, match_end)
            self.text_output.delete(pos, inner_start)


    # --- NEW: Toast Notification ---

    def show_toast(self, message, duration=2000):
        """Displays a temporary popup message."""
        toast = tk.Toplevel(self.root)
        toast.wm_overrideredirect(True) # Remove window decorations
        
        # Style the toast
        bg_color = "#333333"
        fg_color = "#FFFFFF"
        toast.configure(bg=bg_color)
        
        # Add label
        label = tk.Label(toast, text=message, bg=bg_color, fg=fg_color, 
                         padx=20, pady=10, font=("Arial", 10))
        label.pack()

        # Center the toast relative to the root window
        self.root.update_idletasks() # Ensure root geometry is up to date
        
        root_x = self.root.winfo_x()
        root_y = self.root.winfo_y()
        root_w = self.root.winfo_width()
        root_h = self.root.winfo_height()
        
        # Get toast size
        w = label.winfo_reqwidth()
        h = label.winfo_reqheight()
        
        # Calculate position (Centered horizontally, near bottom)
        x = root_x + (root_w - w) // 2
        y = root_y + (root_h - h) - 100 
        
        toast.geometry(f"+{x}+{y}")
        
        # Destroy after 'duration' milliseconds
        self.root.after(duration, toast.destroy)

    def _copy_to_clipboard(self, content):
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        self.root.update() 
        self.show_toast("Code copied to clipboard!") # Trigger toast

    def _apply_syntax_highlighting(self, text_widget, code_content, language):
        if not PYGMENTS_AVAILABLE:
            text_widget.insert("1.0", code_content)
            return

        try:
            if language and language.strip():
                lexer = get_lexer_by_name(language.strip())
            else:
                lexer = guess_lexer(code_content)
        except Exception:
            try:
                lexer = get_lexer_by_name("text")
            except:
                text_widget.insert("1.0", code_content)
                return

        try:
            style = get_style_by_name('monokai')
        except:
            style = get_style_by_name('default')

        for token, opts in style.list_styles():
            kwargs = {}
            if opts['color']: kwargs['foreground'] = '#' + opts['color']
            if opts['bgcolor']: kwargs['background'] = '#' + opts['bgcolor']
            if opts['bold']: kwargs['font'] = ("Consolas", 11, "bold")
            if kwargs:
                text_widget.tag_configure(str(token), **kwargs)

        for token, text in lex(code_content, lexer):
            text_widget.insert(tk.END, text, str(token))

    def _render_code_block(self, language, code_content):
        code_bg = "#1E1E1E"
        header_bg = "#252526" # Variable to ensure match
        
        block_frame = tk.Frame(self.text_output, bd=1, relief="solid", bg=code_bg)
        
        header_frame = tk.Frame(block_frame, bg=header_bg, height=25)
        header_frame.pack(fill="x", side="top")
        
        lang_label = tk.Label(header_frame, text=language.upper() if language else "CODE", 
                              fg="#AAAAAA", bg=header_bg, font=("Consolas", 9, "bold"))
        lang_label.pack(side="left", padx=5)

        # --- FIX: Match highlightbackground to parent (header_bg) to hide border artifact ---
        copy_btn = tk.Button(header_frame, text="Copy Code", 
                             bg="#E0E0E0", 
                             fg="black", 
                             highlightbackground=header_bg, # FIX IS HERE
                             activebackground="#CCCCCC",
                             activeforeground="black",
                             font=("Arial", 9, "bold"),
                             bd=0, padx=10, pady=2,
                             command=lambda: self._copy_to_clipboard(code_content))
        copy_btn.pack(side="right", padx=5, pady=2)

        line_count = len(code_content.splitlines())
        display_height = min(line_count, 20)
        if display_height < 1: display_height = 1

        code_text_widget = tk.Text(block_frame, height=display_height, 
                                   bg=code_bg, fg="#D4D4D4", 
                                   font=("Consolas", 11), 
                                   bd=0, highlightthickness=0,
                                   padx=5, pady=5)
        
        self._apply_syntax_highlighting(code_text_widget, code_content, language)
        code_text_widget.config(state=tk.DISABLED)
        code_text_widget.pack(fill="x", side="top", padx=0, pady=0)

        return block_frame

    def render_markdown(self, raw_text):
        """Parses the text for code blocks AND markdown syntax."""
        self.text_output.config(state=tk.NORMAL)
        
        pattern = r"```(\w*)\n(.*?)```"
        last_pos = 0
        
        for match in re.finditer(pattern, raw_text, re.DOTALL):
            start_idx, end_idx = match.span()
            
            # 1. Process Text BEFORE code block
            pre_text = raw_text[last_pos:start_idx]
            if pre_text:
                self._insert_markdown_text(pre_text)
            
            # 2. Process Code Block
            language = match.group(1).strip()
            code_content = match.group(2)
            if code_content.endswith('\n'):
                code_content = code_content[:-1]

            code_widget = self._render_code_block(language, code_content)
            
            self.text_output.insert(tk.END, "\n")
            self.text_output.window_create(tk.END, window=code_widget, stretch=1)
            self.text_output.insert(tk.END, "\n")
            
            last_pos = end_idx

        # 3. Process remaining text
        remaining_text = raw_text[last_pos:]
        if remaining_text:
            self._insert_markdown_text(remaining_text)
            
        self.text_output.see(tk.END)
        self.text_output.config(state=tk.DISABLED)

    # --- Public API Methods ---

    def log_output(self, message):
        self.text_output.config(state=tk.NORMAL)
        self.text_output.insert(tk.END, f"{message}\n")
        self.text_output.see(tk.END)
        self.text_output.config(state=tk.DISABLED)

    def clear_output(self):
        self.text_output.config(state=tk.NORMAL)
        self.text_output.delete("1.0", tk.END)
        self.text_output.config(state=tk.DISABLED)

    def get_input_text(self):
        text = self.text_input.get("1.0", tk.END).strip()
        self.text_input.delete("1.0", tk.END)
        return text

    def set_button_state(self, enabled: bool):
        state = tk.NORMAL if enabled else tk.DISABLED
        self.text_process_button.config(state=state)

    def clear_attachment_viewer(self):
        self.image_references.clear()
        self.attachment_viewer.config(state=tk.NORMAL)
        self.attachment_viewer.delete("1.0", tk.END)
        self.attachment_viewer.config(state=tk.DISABLED)

    def add_image_thumbnail(self, photo_image, source_text):
        self.image_references.append(photo_image)
        self.attachment_viewer.config(state=tk.NORMAL)
        self.attachment_viewer.image_create(tk.END, image=photo_image, padx=5, pady=5)
        self.attachment_viewer.insert(tk.END, f"\n{source_text}\n\n---\n\n")
        self.attachment_viewer.see(tk.END)
        self.attachment_viewer.config(state=tk.DISABLED)

    def show_pdf_path(self, path_text):
        self.attachment_viewer.config(state=tk.NORMAL)
        self.attachment_viewer.insert(tk.END, f"[PDF]\n{path_text}\n\n---\n\n")
        self.attachment_viewer.see(tk.END)
        self.attachment_viewer.config(state=tk.DISABLED)

    def show_text_file_path(self, path_text):
        self.attachment_viewer.config(state=tk.NORMAL)
        self.attachment_viewer.insert(tk.END, f"[File]\n{path_text}\n\n---\n\n")
        self.attachment_viewer.see(tk.END)
        self.attachment_viewer.config(state=tk.DISABLED)

    def get_personality_text(self):
        try:
            return self.personality_input.get("1.0", tk.END).strip()
        except Exception:
            return ""

    def set_personality_text(self, text: str):
        try:
            self.personality_input.delete("1.0", tk.END)
            self.personality_input.insert("1.0", text)
        except Exception as e:
            print(f"Error setting personality text: {e}")

    def show_thinking_indicator(self):
        self.text_output.config(state=tk.NORMAL)
        self.thinking_message_start_index = self.text_output.index(f"{tk.END} -1c")
        self.text_output.insert(tk.END, "\n--- Chatbot ---\nChatbot is thinking...")
        self.text_output.see(tk.END)
        self.text_output.config(state=tk.DISABLED)

    def replace_thinking_indicator(self, final_message_content: str):
        if self.thinking_message_start_index:
            self.text_output.config(state=tk.NORMAL)
            self.text_output.delete(self.thinking_message_start_index, tk.END)
            self.text_output.insert(tk.END, f"\n\n--- Chatbot ---\n")
            self.render_markdown(final_message_content)
            self.thinking_message_start_index = None
        else:
            self.log_output(f"\n--- Chatbot ---")
            self.render_markdown(final_message_content)