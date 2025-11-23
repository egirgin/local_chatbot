import tkinter as tk
import threading
import queue
import os
import io
import time
import platform
import re

# Pillow
from PIL import ImageGrab, Image, ImageTk

# Ollama
import ollama

# This project's modules
from chatbot_gui_library import ChatbotGuiLibrary
from config import (
    DEFAULT_SYSTEM_PROMPT, THUMBNAIL_SIZE, 
    PDF_EXTENSIONS, TEXT_EXTENSIONS, IMAGE_EXTENSIONS, 
    PDF_FUNCTIONALITY_DISABLED, MAX_RETRIES
)
from utils import (
    read_image_bytes_from_file, read_text_file, extract_pdf_text
)
from ollama_client import execute_ollama_call

# --- PLATFORM-SPECIFIC IMPORTS ---
try:
    if platform.system() == "Windows":
        import win32clipboard
        import win32con
except ImportError:
    pass

try:
    if platform.system() == "Darwin":
        from AppKit import NSPasteboard, NSFilenamesPboardType
except ImportError:
    pass
# --- END PLATFORM-SPECIFIC IMPORTS ---


class ChatbotInstance:
    """
    This class manages the logic and state for a *single* chat tab.
    It acts as the controller, connecting the GUI (View) to the Ollama (Model) logic.
    """
    def __init__(self, parent_tab_frame, close_callback, chat_mode: str, selected_model: str, use_gpu: bool):

        # 1. State
        self.root = parent_tab_frame
        self.close_callback = close_callback
        self.logic_queue = queue.Queue()

        self.image_attachments = [] 
        self.pdf_attachments = []   
        self.text_attachments = []  
        self.attachment_photo_refs = [] 

        self.processing = False
        self.chat_mode = chat_mode
        self.selected_model = selected_model
        self.use_gpu = use_gpu

        # 2. LLM State
        self.client = ollama.Client()
        self.messages = [] 

        # 3. Create the GUI View
        self.gui = ChatbotGuiLibrary(
            self.root,
            drop_callback=self.on_drop,
            paste_callback=self.on_paste
        )

        # 4. Bind GUI widgets to controller methods
        self.setup_gui_bindings()

        # 5. Start the queue-checking loop
        self.root.after(100, self.check_logic_queue)

        # 6. Start the chat!
        self.start_new_chat()

    def setup_gui_bindings(self):
        """Binds all GUI buttons to their controller methods."""
        self.gui.text_process_button.config(command=self.on_send_message)
        self.gui.restart_button.config(command=self.on_restart_chat)
        self.gui.close_button.config(command=self.on_closing)

    def start_new_chat(self):
        """Clears the screen and state for a new chat."""
        self.gui.clear_output()
        self.gui.clear_attachment_viewer()

        mode_str = "VLM" if self.chat_mode == 'vlm' else "LLM Only"
        self.gui.log_output(f"Welcome! [Mode: {mode_str}] [Model: {self.selected_model}]")

        if self.use_gpu:
            system = platform.system()
            if system == "Darwin": gpu_info = "Metal (macOS)"
            elif system == "Linux": gpu_info = "CUDA/ROCm (Linux)"
            elif system == "Windows": gpu_info = "CUDA/ROCm (Windows)"
            else: gpu_info = "Unknown"
            self.gui.log_output(f"[Info: GPU acceleration enabled ({gpu_info}).]")
        else:
            self.gui.log_output("[Info: CPU processing will be used.]")

        if self.chat_mode == 'llm_only':
            self.gui.log_output("Image attachments are disabled.")

        self.gui.log_output("--------------------------------------------------")

        self.messages.clear()
        self.gui.set_personality_text(DEFAULT_SYSTEM_PROMPT)

        self.image_attachments.clear()
        self.pdf_attachments.clear()
        self.text_attachments.clear()
        self.attachment_photo_refs.clear()
        self.processing = False
        self.gui.set_button_state(True)

    def on_restart_chat(self):
        if self.processing:
            self.gui.log_output("\n[!!] Please wait for the current response to finish. [!!]")
        else:
            self.gui.log_output("\n--- CHAT CLEARED ---")
            self.start_new_chat()

    # --- Input Handling Callbacks (on_drop, on_paste) ---

    def _get_pasted_file_paths(self):
        """Platform-specific attempt to get a list of file paths from the clipboard."""
        system = platform.system()
        try:
            if system == "Windows":
                win32clipboard.OpenClipboard()
                try:
                    if win32clipboard.IsClipboardFormatAvailable(win32con.CF_HDROP):
                        data = win32clipboard.GetClipboardData(win32con.CF_HDROP)
                        return list(data)
                finally:
                    win32clipboard.CloseClipboard()
            
            elif system == "Darwin":
                pb = NSPasteboard.generalPasteboard()
                if NSFilenamesPboardType in pb.types():
                    paths = pb.propertyListForType_(NSFilenamesPboardType)
                    return list(paths)
            
            elif system == "Linux":
                try:
                    clipboard_content = self.root.clipboard_get(type='text/uri-list')
                    paths = []
                    for uri in clipboard_content.splitlines():
                        if uri.startswith('file://'):
                            path = uri[7:]
                            path = re.sub(r'^/([A-Za-z]):/', r'\1:/', path)
                            if platform.system() != "Windows" and path.startswith('/'):
                                path = path
                            elif platform.system() == "Windows" and path.startswith('/'):
                                path = path[1:]
                            paths.append(os.path.normpath(path))
                    if paths:
                        return paths
                except tk.TclError:
                    pass
        except Exception as e:
            print(f"Error checking clipboard for files: {e}")
        
        return None 

    def _process_pasted_file_paths(self, file_paths, source="dropped"):
        """Attaches a list of file paths."""
        file_added = False
        for file_path in file_paths:
            if not os.path.exists(file_path):
                self.gui.log_output(f"[!!] Error: {source.title()} file path not found: {file_path} [!!]")
                continue

            ext = os.path.splitext(file_path)[1].lower()

            if ext in IMAGE_EXTENSIONS:
                if self.chat_mode == 'llm_only':
                    self.gui.log_output("[!!] Image attachments are disabled for this LLM. [!!]")
                    continue
                self.image_attachments.append({'type': 'image', 'path': file_path})
                self.gui.log_output(f"\n[+] Image {len(self.image_attachments)} {source}: {os.path.basename(file_path)}")
                file_added = True

            elif ext in PDF_EXTENSIONS:
                if PDF_FUNCTIONALITY_DISABLED:
                    self.gui.log_output("[!!] PDF processing is disabled. Please install 'pypdf'. [!!]")
                    continue
                self.pdf_attachments.append({'type': 'pdf', 'path': file_path})
                self.gui.log_output(f"\n[+] PDF {len(self.pdf_attachments)} {source}: {os.path.basename(file_path)}")
                file_added = True

            elif ext in TEXT_EXTENSIONS or ext not in PDF_EXTENSIONS:
                self.text_attachments.append({'type': 'text', 'path': file_path})
                self.gui.log_output(f"\n[+] File {len(self.text_attachments)} {source}: {os.path.basename(file_path)}")
                file_added = True
            
            else:
                 self.gui.log_output(f"\n[!!] Unhandled file type: {os.path.basename(file_path)} [!!]")

        if file_added:
            self.update_attachment_viewer()
            # If we processed files, we want to stop the event bubbling
            # and potentially clear the text box if the paste put path text in there.
            if source == "pasted":
                self.root.after(1, lambda: self.gui.text_input.delete("1.0", tk.END))

    def on_drop(self, event):
        """Callback for when a file is dropped onto the output window."""
        if self.processing:
            self.gui.log_output("[!!] Cannot attach file while processing. [!!]")
            return

        try:
            file_paths = self.root.tk.splitlist(event.data)
        except Exception:
            file_paths = [event.data.strip('{}')]
        
        self._process_pasted_file_paths(file_paths, source="dropped")

    def on_paste(self, event):
        """
        Callback for when 'paste' is triggered in the input box.
        Includes FREEZE PREVENTION logic.
        """
        if self.processing:
            self.gui.log_output("[!!] Cannot paste while processing. [!!]")
            return "break"

        # --- FREEZE PREVENTION / OPTIMIZATION ---
        # Before attempting to read files/images (which can deadlock on Linux/macOS
        # if copying from the app itself), check if it's just plain text.
        try:
            # Try to get data as standard string first
            text_data = self.root.clipboard_get()
            
            # Check if this text is likely a file path
            is_likely_file = False
            if os.path.exists(text_data) or text_data.startswith('file://'):
                is_likely_file = True
            
            # If it is NOT a file path, it is just normal text.
            # We return None to let Tkinter's default paste handler insert the text.
            if not is_likely_file:
                return None 
        except Exception:
            # If clipboard_get() fails, the content is likely not text (Image or specialized format).
            # Proceed to the file/image checks.
            pass

        # 1. Try to get file paths from clipboard (Complex objects)
        pasted_file_paths = self._get_pasted_file_paths()
        if pasted_file_paths:
            self._process_pasted_file_paths(pasted_file_paths, source="pasted")
            return "break" # Stop default paste

        # 2. Try to get a pasted image (Bitmap/PIL)
        try:
            image = ImageGrab.grabclipboard()
            if isinstance(image, Image.Image):
                if self.chat_mode == 'llm_only':
                    self.gui.log_output("[!!] Image pasting is disabled for this LLM. [!!]")
                    return "break"

                self.image_attachments.append({'type': 'image', 'data': image})
                self.gui.log_output(f"\n[+] Image {len(self.image_attachments)} pasted from clipboard.")
                self.update_attachment_viewer()
                return "break" # Stop default paste

        except Exception:
            pass

        # 3. Fallback
        return None # Let default paste happen

    # --- UI Update Function ---

    def update_attachment_viewer(self):
        """Clears and repopulates the attachment viewer based on current state."""
        self.gui.clear_attachment_viewer()
        self.attachment_photo_refs.clear()

        # 1. Show Images
        for i, att in enumerate(self.image_attachments):
            pil_image = None
            source_text = ""
            try:
                if 'data' in att: 
                    pil_image = att['data']
                    source_text = f"Pasted Image {i+1}"
                elif 'path' in att: 
                    pil_image = Image.open(att['path'])
                    source_text = os.path.basename(att['path'])

                if pil_image:
                    pil_image.thumbnail(THUMBNAIL_SIZE)
                    photo = ImageTk.PhotoImage(pil_image)
                    self.attachment_photo_refs.append(photo) 
                    self.gui.add_image_thumbnail(photo, source_text)
            except Exception as e:
                self.gui.log_output(f"[!!] Error creating thumbnail: {e} [!!]")

        # 2. Show PDFs
        for i, att in enumerate(self.pdf_attachments):
            path = att['path']
            self.gui.show_pdf_path(f"{i+1}. {os.path.basename(path)}")

        # 3. Show Text Files
        for i, att in enumerate(self.text_attachments):
            path = att['path']
            self.gui.show_text_file_path(f"{i+1}. {os.path.basename(path)}")

    # --- Main Send Logic ---

    def on_send_message(self):
        """Handles sending text and all attachments to the 'LLM'."""
        if self.processing:
            return

        prompt_text = self.gui.get_input_text()

        image_list = self.image_attachments
        pdf_list = self.pdf_attachments
        text_list = self.text_attachments
        self.image_attachments = []
        self.pdf_attachments = []
        self.text_attachments = []

        self.gui.clear_attachment_viewer()
        self.attachment_photo_refs.clear()

        has_attachments = bool(image_list or pdf_list or text_list)

        if has_attachments:
            if not prompt_text:
                prompt_text = "Please describe or analyze the attached content."
            
            log_msg = f"--- Me (with {len(image_list)} images, {len(pdf_list)} PDFs, {len(text_list)} files) ---"
            self.gui.log_output(f"\n{log_msg}\n{prompt_text}")
            self.start_processing_thread(
                target=self.process_attachments_thread,
                args=(prompt_text, image_list, pdf_list, text_list)
            )
        elif prompt_text:
            self.gui.log_output(f"\n--- Me ---\n{prompt_text}")
            self.start_processing_thread(
                target=self.process_text_thread,
                args=(prompt_text,)
            )
        else:
            self.gui.log_output("\n[!!] Please type a message or attach a file. [!!]")

    def start_processing_thread(self, target, args):
        self.processing = True
        self.gui.set_button_state(False)
        threading.Thread(target=target, args=args, daemon=True).start()

    # --- Processing Threads ---

    def _handle_ollama_result(self, success: bool, reply: str, user_message: dict, elapsed_time: float):
        if success:
            assistant_message = {'role': 'assistant', 'content': reply}
            self.messages.append(user_message) 
            self.messages.append(assistant_message) 
            time_str = f"({elapsed_time:.1f} secs)"
            final_message_content = f"{time_str}\n{reply}\n"
            self.logic_queue.put(("REPLACE_THINKING", final_message_content))
        else:
            self.logic_queue.put(("LOG", f"\n[!!] Chatbot failed to generate a valid response after {MAX_RETRIES} attempts. [!!]"))
            fallback_reply = "[The assistant is unable to provide a valid response at this time.]"
            assistant_message = {'role': 'assistant', 'content': fallback_reply}
            self.messages.append(user_message) 
            self.messages.append(assistant_message) 
            final_message_content = f"\n{fallback_reply}\n"
            self.logic_queue.put(("REPLACE_THINKING", final_message_content))

    def process_text_thread(self, prompt: str):
        try:
            system_prompt = self.gui.get_personality_text() or DEFAULT_SYSTEM_PROMPT
            user_message = {'role': 'user', 'content': prompt}
            messages_for_call = [{'role': 'system', 'content': system_prompt}]
            messages_for_call.extend(self.messages) 
            messages_for_call.append(user_message) 

            self.logic_queue.put(("THINKING", None))

            reply, elapsed_time, success = execute_ollama_call(
                self.client, self.selected_model, self.use_gpu, messages_for_call, self.logic_queue
            )
            self._handle_ollama_result(success, reply, user_message, elapsed_time)

        except Exception as e:
            self.logic_queue.put(("LOG", f"\n[!!] CRITICAL THREAD ERROR: {e} [!!]"))
        finally:
            self.logic_queue.put(("READY", None))


    def process_attachments_thread(self, prompt: str, image_list: list, pdf_list: list, text_list: list):
        try:
            system_prompt = self.gui.get_personality_text() or DEFAULT_SYSTEM_PROMPT

            image_bytes_list = []
            if self.chat_mode == 'vlm':
                for att in image_list:
                    try:
                        if 'data' in att: 
                            with io.BytesIO() as output:
                                att['data'].save(output, format="PNG")
                                image_bytes_list.append(output.getvalue())
                        elif 'path' in att: 
                            img_bytes = read_image_bytes_from_file(att['path'])
                            if img_bytes:
                                image_bytes_list.append(img_bytes)
                    except Exception as e:
                        self.logic_queue.put(("LOG", f"[!!] Failed to read image {att.get('path', 'pasted image')}: {e} [!!]"))

            file_context_parts = []
            if text_list:
                for att in text_list:
                    path = att['path']
                    content = read_text_file(path)
                    if content is not None:
                        file_context_parts.append(f"--- Content of {os.path.basename(path)} ---\n{content}\n")
                    else:
                        self.logic_queue.put(("LOG", f"[!!] Failed to read text file {path} [!!]"))

            if pdf_list:
                for att in pdf_list:
                    path = att['path']
                    content = extract_pdf_text(path)
                    if content is not None:
                        file_context_parts.append(f"--- Content of {os.path.basename(path)} ---\n{content}\n")
                    else:
                        self.logic_queue.put(("LOG", f"[!!] Failed to extract text from PDF {path} [!!]"))

            file_context = "\n".join(file_context_parts)
            final_prompt = prompt
            if file_context:
                final_prompt = (
                    "Here is the context from the attached files:\n"
                    f"{file_context}\n"
                    "--- End of file context ---\n\n"
                    f"User's question: {prompt}"
                )

            user_message = {'role': 'user', 'content': final_prompt}
            if image_bytes_list: 
                user_message['images'] = image_bytes_list

            messages_for_call = [{'role': 'system', 'content': system_prompt}]
            messages_for_call.extend(self.messages) 
            messages_for_call.append(user_message) 

            self.logic_queue.put(("THINKING", None))

            reply, elapsed_time, success = execute_ollama_call(
                self.client, self.selected_model, self.use_gpu, messages_for_call, self.logic_queue
            )
            self._handle_ollama_result(success, reply, user_message, elapsed_time)

        except Exception as e:
            self.logic_queue.put(("LOG", f"\n[!!] CRITICAL THREAD ERROR: {e} [!!]"))
        finally:
            self.logic_queue.put(("READY", None))

    def check_logic_queue(self):
        try:
            while not self.logic_queue.empty():
                msg_type, data = self.logic_queue.get_nowait()
                if msg_type == "LOG":
                    self.gui.log_output(data)
                elif msg_type == "THINKING":
                    self.gui.show_thinking_indicator()
                elif msg_type == "REPLACE_THINKING":
                    self.gui.replace_thinking_indicator(data)
                elif msg_type == "READY":
                    self.processing = False
                    self.gui.set_button_state(True)
                    self.gui.text_input.focus()
        finally:
            self.root.after(100, self.check_logic_queue)

    def on_closing(self):
        print("Closing chat instance.")
        self.close_callback()