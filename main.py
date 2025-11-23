import tkinter as tk
from tkinter import ttk
from tkinterdnd2 import TkinterDnD

# Import the refactored components
from config import ALL_MODELS, VLM_PREFIX, LLM_PREFIX
from style import setup_styling
from chatbot_instance import ChatbotInstance

class ChatbotManager:
    """
    This class manages the main application window, the top control bar,
    and the notebook (tabs) that hold ChatbotInstance objects.
    """
    def __init__(self, root):
        self.root = root
        self.root.title("Multimodal Chatbot")

        self.tab_counter = 0
        self.chat_instances = {}

        # --- Control Frame (Top) ---
        self.control_frame = ttk.Frame(root)
        self.control_frame.pack(fill="x", side="top", padx=10, pady=(10, 5))

        add_tab_button = ttk.Button(
            self.control_frame,
            text="New Chat (+)",
            command=self.add_new_chat_tab
        )
        add_tab_button.pack(side="right", padx=(10, 0))

        model_label = ttk.Label(self.control_frame, text="Model:")
        model_label.pack(side="left", padx=(10, 0))

        self.model_var = tk.StringVar()
        self.model_dropdown = ttk.Combobox(
            self.control_frame,
            textvariable=self.model_var,
            values=ALL_MODELS, # From config.py
            state='readonly',
            width=20
        )
        self.model_dropdown.set('[VLM] llava:latest')
        self.model_dropdown.pack(side="left", padx=5)

        self.use_gpu_var = tk.BooleanVar(value=True) # Default to ON
        self.gpu_toggle = ttk.Checkbutton(
            self.control_frame,
            text="Use GPU",
            variable=self.use_gpu_var,
            onvalue=True,
            offvalue=False
        )
        self.gpu_toggle.pack(side="left", padx=5)
        
        # --- Notebook (Tabs) ---
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.root.protocol("WM_DELETE_WINDOW", self.on_app_quit)
        self.add_new_chat_tab() # Start with one chat tab

    def add_new_chat_tab(self):
        """Creates a new tab with a new, independent chat instance."""
        self.tab_counter += 1
        tab_id = f"chat_{self.tab_counter}"

        tab_frame = ttk.Frame(self.notebook)

        # Get settings from the control bar
        selected_formatted_string = self.model_var.get()
        if not selected_formatted_string:
            selected_formatted_string = '[VLM] llava:latest' # Fallback
            print("Warning: No model selected, defaulting to '[VLM] llava:latest'")

        use_gpu = self.use_gpu_var.get()

        selected_model = ""
        selected_mode = ""

        if selected_formatted_string.startswith(VLM_PREFIX):
            selected_mode = 'vlm'
            selected_model = selected_formatted_string[len(VLM_PREFIX):]
        elif selected_formatted_string.startswith(LLM_PREFIX):
            selected_mode = 'llm_only'
            selected_model = selected_formatted_string[len(LLM_PREFIX):]
        else:
            print(f"Error: Could not parse model string '{selected_formatted_string}'. Defaulting...")
            selected_model = 'llava:latest'
            selected_mode = 'vlm'

        # Create tab name
        model_base_name = selected_model.split(':')[0]
        gpu_flag = " [G]" if use_gpu else ""
        tab_name = f"{model_base_name}{gpu_flag} ({self.tab_counter})"

        self.notebook.add(tab_frame, text=tab_name)
        self.notebook.select(tab_frame)

        close_callback = lambda: self.close_tab(tab_id, tab_frame)

        # Create the new ChatbotInstance (from chatbot_instance.py)
        chat = ChatbotInstance(
            tab_frame,
            close_callback,
            selected_mode,
            selected_model,
            use_gpu
        )

        self.chat_instances[tab_id] = chat

    def close_tab(self, tab_id, tab_frame):
        """Callback function to close a specific tab."""
        print(f"Closing tab {tab_id}")
        self.notebook.forget(tab_frame)

        if tab_id in self.chat_instances:
            del self.chat_instances[tab_id]

        if not self.chat_instances:
            print("All chats closed. Exiting application.")
            self.on_app_quit()

    def on_app_quit(self):
        """Called when the main window 'X' is clicked."""
        print("Closing all chats and exiting.")
        self.root.destroy()


# --- Main execution ---
if __name__ == "__main__":
    # CRITICAL: We must use TkinterDnD.Tk() as the root window
    root = TkinterDnD.Tk()
    root.geometry("1000x700")

    try:
        # Load the logo image
        # Assumes you have 'logo.png' in the 'assets' folder
        logo_image = tk.PhotoImage(file="assets/logo.png")
        
        # Set the window icon
        root.iconphoto(True, logo_image)
    except tk.TclError as e:
        print(f"Error: Could not load logo 'assets/logo.png': {e}")

    # Apply styling (from style.py)
    setup_styling(root)

    # Create and run the app
    app = ChatbotManager(root)
    root.mainloop()