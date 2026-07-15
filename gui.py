import customtkinter as ctk
from tkinter import messagebox, filedialog
import threading
import subprocess
import os
import sys
import signal
import logging
import queue

# Set appearance and theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, ".env")
KEYWORDS_FILE = os.path.join(BASE_DIR, "keywords.txt")
DATA_DIR = os.path.join(BASE_DIR, "data")
USER_DATA_DIR = os.path.join(BASE_DIR, "user_data")
MAIN_SCRIPT = os.path.join(BASE_DIR, "main.py")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
EMAIL_SUBJECT_TEMPLATE_FILE = os.path.join(TEMPLATES_DIR, "email_subject_template.txt")
EMAIL_BODY_TEMPLATE_FILE = os.path.join(TEMPLATES_DIR, "email_body_template.txt")

DEFAULT_EMAIL_SUBJECT_TEMPLATE = "Application for {job_keyword} Role — {sender_name}"
DEFAULT_EMAIL_BODY_TEMPLATE = """Dear {recruiter_name},

I came across your post about a {job_keyword} opportunity on LinkedIn and I am very interested in exploring this role further.

I have hands-on experience in {job_keyword} development and I am confident my background aligns well with what you are looking for. Please find my resume attached for your review.

I would love the opportunity to connect and discuss how I can contribute to your team or your client's requirements.

Looking forward to hearing from you.

Warm regards,
{sender_name}
{gmail_address}
"""

def _default_env_vars():
    return {
        "LINKEDIN_EMAIL": "",
        "LINKEDIN_PASSWORD": "",
        "GMAIL_ADDRESS": "",
        "GMAIL_APP_PASSWORD": "",
        "SENDER_NAME": "",
        "RESUME_PATH": "assets/resume.pdf",
        "PAGE_LOAD_DELAY": "3.0",
        "SCROLL_DELAY": "2.0",
        "ACTION_DELAY": "1.5",
        "MAX_SCROLL_COUNT": "10",
        "AUTO_SEND_EMAILS": "True"
    }

def load_env():
    env_vars = _default_env_vars()
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    key, val = line.strip().split("=", 1)
                    if key in env_vars:
                        env_vars[key] = val
    return env_vars

def load_template_text(path: str, default_text: str) -> str:
    """Load a template text file, falling back to a default if missing/unreadable."""
    try:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
    except Exception:
        pass
    return default_text

def save_template_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

def load_env_from_path(env_path):
    env_vars = _default_env_vars()
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                key, val = line.strip().split("=", 1)
                if key in env_vars:
                    env_vars[key] = val
    return env_vars

def save_env(env_vars):
    with open(ENV_FILE, "w", encoding='utf-8') as f:
        for k, v in env_vars.items():
            f.write(f"{k}={v}\n")

def load_keywords():
    if os.path.exists(KEYWORDS_FILE):
        with open(KEYWORDS_FILE, "r", encoding='utf-8') as f:
            return f.read()
    return "Java Developer hiring\nPython Developer recruiter\n"

def save_keywords(keywords_text):
    with open(KEYWORDS_FILE, "w", encoding='utf-8') as f:
        f.write(keywords_text)

class GUILogHandler(logging.Handler):
    """
    Thread-safe logging handler that routes log records into
    the GUI's log textbox via a queue (safe for background threads).
    """
    def __init__(self, log_queue: queue.Queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record: logging.LogRecord):
        msg = self.format(record) + "\n"
        self.log_queue.put(msg)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("LinkedIn Outreach Pro")
        self.geometry("950x750")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.env_data = load_env()
        self.keywords_text = load_keywords()
        self.process = None

        # Thread-safe queue for routing in-process log messages to the GUI
        self._log_queue: queue.Queue = queue.Queue()
        self._start_log_queue_poll()

        # Configure grid layout (1x2)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Create sidebar frame with widgets
        self.sidebar_frame = ctk.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="LinkedIn Bot", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.sidebar_button_1 = ctk.CTkButton(self.sidebar_frame, text="Home", command=self.show_settings)
        self.sidebar_button_1.grid(row=1, column=0, padx=20, pady=10)

        self.sidebar_button_credentials = ctk.CTkButton(self.sidebar_frame, text="Credentials", command=self.show_credentials)
        self.sidebar_button_credentials.grid(row=2, column=0, padx=20, pady=10)

        self.sidebar_button_3 = ctk.CTkButton(self.sidebar_frame, text="Time and Delay", command=self.show_time_settings)
        self.sidebar_button_3.grid(row=3, column=0, padx=20, pady=10)

        self.sidebar_button_2 = ctk.CTkButton(self.sidebar_frame, text="Logs", command=self.show_logs)
        self.sidebar_button_2.grid(row=4, column=0, padx=20, pady=10)

        self.sidebar_button_gmail_template = ctk.CTkButton(
            self.sidebar_frame,
            text="Gmail Template",
            command=self.show_gmail_template
        )
        self.sidebar_button_gmail_template.grid(row=5, column=0, padx=20, pady=10)

        self.appearance_mode_label = ctk.CTkLabel(self.sidebar_frame, text="Appearance Mode:", anchor="w")
        self.appearance_mode_label.grid(row=6, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu = ctk.CTkOptionMenu(self.sidebar_frame, values=["Light", "Dark", "System"],
                                                                       command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=7, column=0, padx=20, pady=(10, 10))
        self.appearance_mode_optionemenu.set("Dark")

        # Create main content area
        self.main_content = ctk.CTkFrame(self, corner_radius=10)
        self.main_content.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.main_content.grid_columnconfigure(0, weight=1)
        self.main_content.grid_rowconfigure(0, weight=1)

        self.entries = {}

        # ---------------- Credentials Container ----------------
        self.credentials_frame = ctk.CTkScrollableFrame(self.main_content, label_text="Secure Credentials")
        self.credentials_frame.grid_columnconfigure(1, weight=1)

        cred_fields = [
            ("LinkedIn Email", "LINKEDIN_EMAIL"),
            ("LinkedIn Password", "LINKEDIN_PASSWORD"),
            ("Optional Gmail Address", "GMAIL_ADDRESS"),
            ("Optional Gmail App Password", "GMAIL_APP_PASSWORD"),
        ]

        for idx, (label_text, key) in enumerate(cred_fields):
            lbl = ctk.CTkLabel(self.credentials_frame, text=label_text)
            lbl.grid(row=idx, column=0, padx=20, pady=10, sticky="w")
            
            pass_frame = ctk.CTkFrame(self.credentials_frame, fg_color="transparent")
            pass_frame.grid(row=idx, column=1, padx=20, pady=10, sticky="ew")
            pass_frame.grid_columnconfigure(0, weight=1)

            is_password = "PASSWORD" in key
            entry = ctk.CTkEntry(pass_frame, placeholder_text=f"Enter {label_text}", show="*" if is_password else "")
            entry.insert(0, self.env_data.get(key, ""))
            entry.grid(row=0, column=0, sticky="ew")

            if is_password:
                def toggle_password(e=entry, btn=None):
                    if e.cget("show") == "*":
                        e.configure(show="")
                        btn.configure(text="Hide")
                    else:
                        e.configure(show="*")
                        btn.configure(text="Show")

                toggle_btn = ctk.CTkButton(pass_frame, text="Show", width=60)
                toggle_btn.configure(command=lambda e=entry, b=toggle_btn: toggle_password(e, b))
                toggle_btn.grid(row=0, column=1, padx=(10, 0))
            
            self.entries[key] = entry

        self.import_btn = ctk.CTkButton(self.credentials_frame, text="Reload Last Saved Credentials", command=self.reload_credentials, fg_color="gray30")
        self.import_btn.grid(row=len(cred_fields), column=0, columnspan=2, padx=20, pady=(20, 10))

        self.forget_btn = ctk.CTkButton(self.credentials_frame, text="Forget All User Data", command=self.forget_user_data, fg_color="#a11d1d", hover_color="#7a1414")
        self.forget_btn.grid(row=len(cred_fields)+1, column=0, columnspan=2, padx=20, pady=(0, 20))


        # ---------------- Settings Container (Home) ----------------
        self.settings_frame = ctk.CTkScrollableFrame(self.main_content, label_text="Home")
        self.settings_frame.grid_columnconfigure(1, weight=1)

        profile_fields = [
            ("Sender Name", "SENDER_NAME"),
            ("Resume Path", "RESUME_PATH"),
        ]

        for idx, (label_text, key) in enumerate(profile_fields):
            lbl = ctk.CTkLabel(self.settings_frame, text=label_text)
            lbl.grid(row=idx, column=0, padx=20, pady=10, sticky="w")
            
            if key == "RESUME_PATH":
                resume_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
                resume_frame.grid(row=idx, column=1, padx=20, pady=10, sticky="ew")
                resume_frame.grid_columnconfigure(0, weight=1)

                entry = ctk.CTkEntry(resume_frame, placeholder_text="Path to resume.pdf")
                entry.insert(0, self.env_data.get(key, ""))
                entry.grid(row=0, column=0, sticky="ew")
                
                browse_btn = ctk.CTkButton(resume_frame, text="Browse", width=80, 
                                          command=lambda: self.browse_file(self.entries["RESUME_PATH"]))
                browse_btn.grid(row=0, column=1, padx=(10, 0))
                self.entries[key] = entry
            else:
                entry = ctk.CTkEntry(self.settings_frame, width=300, placeholder_text=f"Enter {label_text}")
                entry.insert(0, self.env_data.get(key, ""))
                entry.grid(row=idx, column=1, padx=20, pady=10, sticky="ew")
                self.entries[key] = entry

        self.kw_label = ctk.CTkLabel(self.settings_frame, text="Keywords (one per line)", font=ctk.CTkFont(size=16, weight="bold"))
        self.kw_label.grid(row=len(profile_fields), column=0, padx=20, pady=(20, 0), sticky="nw")

        self.enhance_btn = ctk.CTkButton(self.settings_frame, text="✨ Enhance", width=120, command=self.enhance_keywords, fg_color="#2b7a3b", hover_color="#1d5428")
        self.enhance_btn.grid(row=len(profile_fields), column=0, padx=20, pady=(55, 10), sticky="nw")
        
        self.kw_text = ctk.CTkTextbox(self.settings_frame, height=150)
        self.kw_text.grid(row=len(profile_fields), column=1, padx=20, pady=10, sticky="ew")
        self.kw_text.insert("1.0", self.keywords_text)

        curr_row = len(profile_fields) + 1

        # Auto Send Toggle
        self.auto_send_switch = ctk.CTkSwitch(self.settings_frame, text="Auto-Send Emails Automatically")
        self.auto_send_switch.grid(row=curr_row, column=0, columnspan=2, padx=20, pady=10, sticky="w")
        if self.env_data.get("AUTO_SEND_EMAILS") == "True":
            self.auto_send_switch.select()

        curr_row += 1

        # Found Emails Display
        self.emails_label = ctk.CTkLabel(self.settings_frame, text="Found Emails", font=ctk.CTkFont(size=16, weight="bold"))
        self.emails_label.grid(row=curr_row, column=0, padx=20, pady=(20, 0), sticky="nw")

        self.emails_text = ctk.CTkTextbox(self.settings_frame, height=150)
        self.emails_text.grid(row=curr_row, column=1, padx=20, pady=10, sticky="ew")

        curr_row += 1

        self.email_action_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        self.email_action_frame.grid(row=curr_row, column=1, padx=20, pady=10, sticky="w")

        self.load_emails_btn = ctk.CTkButton(self.email_action_frame, text="Load Saved Emails", command=self.load_found_emails)
        self.load_emails_btn.pack(side="left", padx=(0, 10))

        self.manual_send_btn = ctk.CTkButton(self.email_action_frame, text="Send Mails Now", command=self.manual_send_mails, fg_color="#1f538d", hover_color="#14375e")
        self.manual_send_btn.pack(side="left")

        self.stop_manual_btn = ctk.CTkButton(self.email_action_frame, text="Stop Sending", command=self.stop_manual_send, fg_color="#a11d1d", hover_color="#7a1414", state="disabled")
        self.stop_manual_btn.pack(side="left", padx=(10, 0))

        # ---------------- Time Settings Container ----------------
        self.time_settings_frame = ctk.CTkScrollableFrame(self.main_content, label_text="Time & Delay Configuration")
        self.time_settings_frame.grid_columnconfigure(1, weight=1)

        time_fields = [
            ("Page Load Delay (s)", "PAGE_LOAD_DELAY", "Recommended: 3.0. Time to wait for full page load."),
            ("Scroll Delay (s)", "SCROLL_DELAY", "Recommended: 2.0. Buffer time between page scrolls."),
            ("Action/Click Delay (s)", "ACTION_DELAY", "Recommended: 1.5. Buffer time between clicks/typing."),
            ("Max Scroll Count", "MAX_SCROLL_COUNT", "Recommended: 10. Max scrolls per keyword search.")
        ]

        for idx, (label_text, key, recommended) in enumerate(time_fields):
            lbl_frame = ctk.CTkFrame(self.time_settings_frame, fg_color="transparent")
            lbl_frame.grid(row=idx, column=0, padx=20, pady=10, sticky="w")
            
            ctk.CTkLabel(lbl_frame, text=label_text).pack(anchor="w")
            ctk.CTkLabel(lbl_frame, text=recommended, font=ctk.CTkFont(size=11), text_color="gray").pack(anchor="w")
            
            entry = ctk.CTkEntry(self.time_settings_frame, width=150)
            entry.insert(0, self.env_data.get(key, ""))
            entry.grid(row=idx, column=1, padx=20, pady=10, sticky="w")
            self.entries[key] = entry

        # ---------------- Gmail Template Container ----------------
        self.gmail_template_frame = ctk.CTkScrollableFrame(self.main_content, label_text="Gmail Template")
        self.gmail_template_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            self.gmail_template_frame,
            text="Placeholders you can use:",
            font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=0, columnspan=2, padx=20, pady=(15, 5), sticky="w")

        placeholders = "{recruiter_name}, {job_keyword}, {sender_name}, {gmail_address}"
        ctk.CTkLabel(self.gmail_template_frame, text=placeholders).grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 15), sticky="w")

        ctk.CTkLabel(self.gmail_template_frame, text="Subject Template").grid(row=2, column=0, padx=20, pady=10, sticky="w")
        self.gmail_template_subject_text = ctk.CTkTextbox(self.gmail_template_frame, height=60)
        self.gmail_template_subject_text.grid(row=2, column=1, padx=20, pady=10, sticky="ew")

        ctk.CTkLabel(self.gmail_template_frame, text="Body Template").grid(row=3, column=0, padx=20, pady=10, sticky="w")
        self.gmail_template_body_text = ctk.CTkTextbox(self.gmail_template_frame, height=320)
        self.gmail_template_body_text.grid(row=3, column=1, padx=20, pady=10, sticky="nsew")

        self.gmail_template_save_btn = ctk.CTkButton(
            self.gmail_template_frame,
            text="Save Gmail Template",
            command=self.save_gmail_template,
            fg_color="gray30",
            hover_color="gray40"
        )
        self.gmail_template_save_btn.grid(row=4, column=1, padx=20, pady=(10, 20), sticky="e")

        self.load_gmail_template_into_gui()

        # ---------------- Logs Container ----------------
        self.logs_frame = ctk.CTkFrame(self.main_content)
        
        self.logs_top_frame = ctk.CTkFrame(self.logs_frame, fg_color="transparent")
        self.logs_top_frame.pack(fill="x", padx=10, pady=(10, 0))
        
        self.clear_logs_btn = ctk.CTkButton(self.logs_top_frame, text="Clear Logs", width=100, command=self.clear_logs)
        self.clear_logs_btn.pack(side="right")

        self.log_textbox = ctk.CTkTextbox(self.logs_frame, font=("Consolas", 12))
        self.log_textbox.pack(fill="both", expand=True, padx=10, pady=10)

        # ---------------- Control Buttons ----------------
        self.button_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")
        self.button_frame.grid(row=1, column=0, pady=10)

        self.save_button = ctk.CTkButton(self.button_frame, text="Save Settings", command=self.save_settings, fg_color="gray30", hover_color="gray40")
        self.save_button.grid(row=0, column=0, padx=10)

        self.run_button = ctk.CTkButton(self.button_frame, text="Run Automation", command=self.start_automation, fg_color="#1f538d", hover_color="#14375e")
        self.run_button.grid(row=0, column=1, padx=10)

        self.stop_button = ctk.CTkButton(self.button_frame, text="Stop Automation", command=self.stop_automation, fg_color="#a11d1d", hover_color="#7a1414", state="disabled")
        self.stop_button.grid(row=0, column=2, padx=10)

        # Show default tab
        self.show_settings()

    def show_settings(self):
        self.hide_all_frames()
        self.settings_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.button_frame.grid(row=1, column=0, pady=10)

    def show_credentials(self):
        self.hide_all_frames()
        self.credentials_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.button_frame.grid(row=1, column=0, pady=10)

    def show_time_settings(self):
        self.hide_all_frames()
        self.time_settings_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.button_frame.grid(row=1, column=0, pady=10)

    def show_logs(self):
        self.hide_all_frames()
        self.button_frame.grid_forget()
        self.logs_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    def show_gmail_template(self):
        self.hide_all_frames()
        self.button_frame.grid_forget()
        self.gmail_template_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.load_gmail_template_into_gui()

    def hide_all_frames(self):
        self.logs_frame.grid_forget()
        self.settings_frame.grid_forget()
        self.credentials_frame.grid_forget()
        self.time_settings_frame.grid_forget()
        self.gmail_template_frame.grid_forget()

    def load_gmail_template_into_gui(self):
        subject = load_template_text(EMAIL_SUBJECT_TEMPLATE_FILE, DEFAULT_EMAIL_SUBJECT_TEMPLATE)
        body = load_template_text(EMAIL_BODY_TEMPLATE_FILE, DEFAULT_EMAIL_BODY_TEMPLATE)

        self.gmail_template_subject_text.delete("1.0", "end")
        self.gmail_template_subject_text.insert("1.0", subject)

        self.gmail_template_body_text.delete("1.0", "end")
        self.gmail_template_body_text.insert("1.0", body)

    def save_gmail_template(self, show_popup=True):
        subject = self.gmail_template_subject_text.get("1.0", "end-1c").strip()
        body = self.gmail_template_body_text.get("1.0", "end-1c")

        if not subject.strip() or not body.strip():
            messagebox.showerror("Error", "Subject and Body templates cannot be empty.")
            return False

        warnings = []
        try:
            save_template_text(EMAIL_SUBJECT_TEMPLATE_FILE, subject)
        except PermissionError:
            warnings.append(
                f"Could not save `{EMAIL_SUBJECT_TEMPLATE_FILE}` because Windows denied access."
            )
        except OSError as exc:
            warnings.append(
                f"Could not save `{EMAIL_SUBJECT_TEMPLATE_FILE}`. Reason: {exc}"
            )

        try:
            save_template_text(EMAIL_BODY_TEMPLATE_FILE, body)
        except PermissionError:
            warnings.append(
                f"Could not save `{EMAIL_BODY_TEMPLATE_FILE}` because Windows denied access."
            )
        except OSError as exc:
            warnings.append(
                f"Could not save `{EMAIL_BODY_TEMPLATE_FILE}`. Reason: {exc}"
            )

        if warnings:
            warning_message = "\n\n".join(warnings)
            if show_popup:
                messagebox.showwarning("Template Not Saved", warning_message)
            self.append_log(f">>> Warning: {warning_message}\n")
            return False

        if show_popup:
            messagebox.showinfo("Success", "Gmail template saved successfully!")
        return True

    def reload_credentials(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Import Credentials")
        dialog.geometry("520x280")
        dialog.transient(self)
        dialog.grab_set()
        dialog.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            dialog,
            text="Import credentials from .env",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        help_text = (
            "Choose one option below:\n"
            "1. Drag and drop or browse your .env file.\n"
            "2. Paste the full path of your .env file."
        )
        info = ctk.CTkLabel(dialog, text=help_text, justify="left")
        info.grid(row=1, column=0, padx=20, pady=(0, 15), sticky="w")

        browse_btn = ctk.CTkButton(
            dialog,
            text="Drag/Drop or Browse .env File",
            command=lambda: self._browse_env_file(dialog)
        )
        browse_btn.grid(row=2, column=0, padx=20, pady=(0, 15), sticky="ew")

        paste_label = ctk.CTkLabel(dialog, text="Paste .env file path")
        paste_label.grid(row=3, column=0, padx=20, pady=(0, 5), sticky="w")

        path_entry = ctk.CTkEntry(
            dialog,
            placeholder_text=r"Example: C:\Users\Dell\Documents\LinkedIn Automation\.env"
        )
        path_entry.grid(row=4, column=0, padx=20, pady=(0, 15), sticky="ew")

        import_btn = ctk.CTkButton(
            dialog,
            text="Import From Path",
            command=lambda: self._import_env_from_path(path_entry.get().strip(), dialog)
        )
        import_btn.grid(row=5, column=0, padx=20, pady=(0, 10), sticky="ew")

        cancel_btn = ctk.CTkButton(
            dialog,
            text="Cancel",
            fg_color="gray30",
            hover_color="gray40",
            command=dialog.destroy
        )
        cancel_btn.grid(row=6, column=0, padx=20, pady=(0, 20), sticky="ew")

    def _browse_env_file(self, dialog):
        env_path = filedialog.askopenfilename(
            title="Select .env File",
            filetypes=(("ENV files", ".env"), ("All files", "*.*"))
        )
        if env_path:
            self._import_env_from_path(env_path, dialog)

    def _import_env_from_path(self, env_path, dialog=None):
        if not env_path:
            messagebox.showerror("Missing Path", "Please choose or paste the path to a .env file.")
            return

        normalized_path = os.path.normpath(env_path.strip().strip('"'))
        if not os.path.isfile(normalized_path):
            messagebox.showerror("File Not Found", f"No file was found at:\n\n{normalized_path}")
            return

        try:
            imported_env = load_env_from_path(normalized_path)
        except Exception as exc:
            messagebox.showerror("Import Failed", f"Could not read the .env file.\n\nReason: {exc}")
            return

        self.env_data.update(imported_env)
        self._populate_form_from_env()

        if dialog is not None and dialog.winfo_exists():
            dialog.destroy()
        messagebox.showinfo("Imported", f"Credentials loaded successfully from:\n\n{normalized_path}")

    def _populate_form_from_env(self):
        for key, entry in self.entries.items():
            if key not in self.env_data:
                continue
            entry.delete(0, "end")
            entry.insert(0, self.env_data.get(key, ""))

        self.kw_text.delete("1.0", "end")
        self.kw_text.insert("1.0", load_keywords())

        if self.env_data.get("AUTO_SEND_EMAILS") == "True":
            self.auto_send_switch.select()
        else:
            self.auto_send_switch.deselect()

    def on_close(self):
        if hasattr(self, "entries") and hasattr(self, "kw_text"):
            self.save_settings(show_popup=False)
        if hasattr(self, "gmail_template_subject_text") and hasattr(self, "gmail_template_body_text"):
            self.save_gmail_template(show_popup=False)
        self.destroy()

    def save_settings(self, show_popup=True):
        for key, entry in self.entries.items():
            self.env_data[key] = entry.get()
            os.environ[key] = entry.get()  # Immediately update running environment
        self.env_data["AUTO_SEND_EMAILS"] = "True" if self.auto_send_switch.get() == 1 else "False"
        os.environ["AUTO_SEND_EMAILS"] = self.env_data["AUTO_SEND_EMAILS"]
        save_warnings = []
        try:
            save_env(self.env_data)
        except PermissionError:
            save_warnings.append(
                f"Could not save `{ENV_FILE}` because Windows denied access.\n\n"
                "The current session will still use the values you entered, "
                "but they were not saved to disk."
            )
        except OSError as exc:
            save_warnings.append(
                f"Could not save `{ENV_FILE}`.\n\n"
                f"Reason: {exc}\n\n"
                "The current session will still use the values you entered, "
                "but they were not saved to disk."
            )

        try:
            save_keywords(self.kw_text.get("1.0", "end-1c").strip())
        except PermissionError:
            save_warnings.append(
                f"Could not save `{KEYWORDS_FILE}` because Windows denied access.\n\n"
                "The current session will still use the keywords you entered, "
                "but they were not saved to disk."
            )
        except OSError as exc:
            save_warnings.append(
                f"Could not save `{KEYWORDS_FILE}`.\n\n"
                f"Reason: {exc}\n\n"
                "The current session will still use the keywords you entered, "
                "but they were not saved to disk."
            )

        if save_warnings:
            warning_message = "\n\n".join(save_warnings)
            if show_popup:
                messagebox.showwarning("Settings Partially Saved", warning_message)
            self.append_log(f">>> Warning: {warning_message}\n")
            return False
        if show_popup:
            messagebox.showinfo("Success", "All settings and credentials saved successfully!")
        return True

    def clear_logs(self):
        self.log_textbox.delete("1.0", "end")

    def enhance_keywords(self):
        text = self.kw_text.get("1.0", "end-1c").strip()
        if not text:
            return
            
        lines = text.split('\n')
        enhanced = []
        corrections = {
            "developement": "development",
            "enginer": "engineer",
            "enigneer": "engineer",
            "front end": "frontend",
            "back end": "backend",
            "fullstack": "full stack"
        }
        
        for line in lines:
            line = line.strip()
            if not line: continue
            
            # Apply corrections
            words = line.split()
            fixed_words = []
            for w in words:
                lower_w = w.lower()
                if lower_w in corrections:
                    fixed_words.append(corrections[lower_w])
                else:
                    fixed_words.append(w)
            
            line = " ".join(fixed_words).title()
            
            # Enhance with LinkedIn specific terms if they are just job titles
            lower_line = line.lower()
            if not any(x in lower_line for x in ["hiring", "recruiter", "opportunity", "send resume", "looking for", "role"]):
                enhanced.append(f"{line} Hiring")
                enhanced.append(f'"{line}" Send Resume')
            else:
                enhanced.append(line)
                
        # Remove duplicates
        final_list = []
        for item in enhanced:
            if item not in final_list:
                final_list.append(item)
                
        self.kw_text.delete("1.0", "end")
        self.kw_text.insert("1.0", "\n".join(final_list))
        messagebox.showinfo("Enhanced", "Keywords have been auto-corrected and optimized for LinkedIn search!")

    def change_appearance_mode_event(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)

    def browse_file(self, entry_widget):
        filename = filedialog.askopenfilename(
            initialdir="/",
            title="Select Resume PDF",
            filetypes=(("PDF files", "*.pdf"), ("all files", "*.*"))
        )
        if filename:
            entry_widget.delete(0, "end")
            entry_widget.insert(0, filename)

    def load_found_emails(self):
        self.emails_text.delete("1.0", "end")
        csv_path = os.path.join(DATA_DIR, "recruiters.csv")
        if not os.path.exists(csv_path):
            self.emails_text.insert("1.0", "No emails found yet.")
            return
            
        import csv
        emails = []
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    email = row.get('email', '').strip()
                    if email and email.lower() not in [e.lower() for e in emails]:
                        emails.append(email)
            if emails:
                self.emails_text.insert("1.0", ", ".join(emails))
            else:
                self.emails_text.insert("1.0", "No emails found yet.")
        except Exception as e:
            self.emails_text.insert("1.0", f"Error loading: {e}")

    def manual_send_mails(self):
        # Read emails currently in the text box
        raw_emails = self.emails_text.get("1.0", "end-1c").strip()
        if not raw_emails or raw_emails == "No emails found yet.":
            messagebox.showinfo("Info", "No emails in the text box to send to.")
            return

        gmail_address = self.entries["GMAIL_ADDRESS"].get().strip()
        gmail_password = self.entries["GMAIL_APP_PASSWORD"].get().strip()
        if not gmail_address or not gmail_password:
            messagebox.showerror(
                "Gmail Required",
                "Manual email sending needs Gmail Address and Gmail App Password."
            )
            return

        # Split by comma only — simple and safe. Emails are comma-joined by load_found_emails.
        target_emails = [
            e.strip() for e in raw_emails.split(',') if e.strip() and '@' in e
        ]
        
        if not target_emails:
            messagebox.showinfo("Info", "No valid emails found in the text box.")
            return

        # We invoke the mail sending script logic without UI blocking
        self.save_settings(show_popup=False)
        messagebox.showinfo("Sending", f"Starting Manual Email Send to {len(target_emails)} email(s)...")
        self.show_logs()
        self.append_log(f"\n>>> Starting Manual Email Sending to {len(target_emails)} specific email(s)...\n")
        
        self.manual_send_btn.configure(state="disabled")
        self.stop_manual_btn.configure(state="normal")
        self.manual_stop_event = threading.Event()

        # IMPORTANT: Call setup_logger() FIRST to ensure StreamHandler (terminal)
        # and FileHandler (log file) are registered on the "recruiter_bot" logger.
        # Only then attach the GUI handler on top. If we add GUILogHandler first,
        # setup_logger() sees handlers exist and skips adding console/file handlers.
        from utils.logger import setup_logger
        setup_logger()  # Ensures terminal + file handlers are set up

        # Now attach the GUI log handler on top — logs will go to ALL three destinations
        gui_handler = GUILogHandler(self._log_queue)
        gui_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S"))
        root_logger = logging.getLogger("recruiter_bot")
        root_logger.addHandler(gui_handler)

        def run_sender():
            from modules.gmail_sender import GmailSender
            from utils.csv_handler import load_recruiters
            try:
                # Load existing data to get names/companies if available
                all_recruiters = load_recruiters()
                recruiter_dict = {r.get('email', '').strip().lower(): r for r in all_recruiters if r.get('email')}
                
                final_recruiters = []
                for email in target_emails:
                    e_lower = email.lower()
                    if e_lower in recruiter_dict:
                        final_recruiters.append(recruiter_dict[e_lower])
                    else:
                        # Construct a generic recruiter object for new emails manually added
                        final_recruiters.append({
                            "name": "HR",
                            "email": email,
                            "company": "",
                            "keyword": "LinkedIn Search"
                        })
                
                sender = GmailSender()
                sender.send_bulk(final_recruiters, stop_event=self.manual_stop_event)
                self.append_log(">>> Manual sending process ended.\n")
            except Exception as e:
                self.append_log(f">>> Error during manual send: {e}\n")
            finally:
                # Remove the temporary GUI log handler
                root_logger = logging.getLogger("recruiter_bot")
                for h in root_logger.handlers[:]:
                    if isinstance(h, GUILogHandler):
                        root_logger.removeHandler(h)
                self.manual_send_btn.configure(state="normal")
                self.stop_manual_btn.configure(state="disabled")
                
        t = threading.Thread(target=run_sender)
        t.daemon = True
        t.start()

    def stop_manual_send(self):
        if hasattr(self, 'manual_stop_event'):
            self.manual_stop_event.set()
            self.append_log("\n>>> Stopping manual email sending...\n")

    def _start_log_queue_poll(self):
        """Poll the log queue every 100ms and write messages to the GUI textbox."""
        def poll():
            try:
                while True:
                    msg = self._log_queue.get_nowait()
                    # Only write to textbox if it exists and the window is still alive
                    if hasattr(self, 'log_textbox'):
                        self.log_textbox.insert("end", msg)
                        self.log_textbox.see("end")
            except queue.Empty:
                pass
            self.after(100, poll)
        self.after(100, poll)

    def start_automation(self):
        required_keys = {
            "LINKEDIN_EMAIL",
            "LINKEDIN_PASSWORD",
            "SENDER_NAME",
            "RESUME_PATH",
            "PAGE_LOAD_DELAY",
            "SCROLL_DELAY",
            "ACTION_DELAY",
            "MAX_SCROLL_COUNT",
        }
        for key, entry in self.entries.items():
            if key not in required_keys:
                continue
            if not entry.get().strip():
                messagebox.showerror("Error", "Please fill all required fields before running.")
                return
                
        if not self.kw_text.get("1.0", "end-1c").strip():
            messagebox.showerror("Error", "Please provide at least one search keyword.")
            return

        self.save_settings(show_popup=False)
        gmail_address = self.entries["GMAIL_ADDRESS"].get().strip()
        gmail_password = self.entries["GMAIL_APP_PASSWORD"].get().strip()
        self.run_env = os.environ.copy()
        auto_send_enabled = self.auto_send_switch.get() == 1

        self.show_logs()
        self.log_textbox.delete("1.0", "end")
        if auto_send_enabled and (not gmail_address or not gmail_password):
            self.run_env["AUTO_SEND_EMAILS"] = "False"
            self.append_log(">>> Gmail credentials not provided. Automation will run without auto-sending emails.\n")
            messagebox.showinfo(
                "Running Without Gmail",
                "Gmail Address and App Password are optional.\n\n"
                "Automation will continue, but auto-send emails is disabled for this run."
            )
        messagebox.showinfo("Running", "Starting Automation Script...")

        self.run_button.configure(state="disabled", text="Running...")
        self.stop_button.configure(state="normal")
        
        thread = threading.Thread(target=self.run_script_thread)
        thread.daemon = True
        thread.start()

    def stop_automation(self):
        if self.process:
            try:
                if os.name == 'nt':
                    subprocess.call(['taskkill', '/F', '/T', '/PID', str(self.process.pid)])
                else:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                self.append_log("\n>>> Automation STOPPED by user.\n")
            except Exception as e:
                self.append_log(f"\n>>> Error stopping process: {e}\n")
            finally:
                self.process = None
                self.run_button.configure(state="normal", text="Run Automation")
                self.stop_button.configure(state="disabled")

    def run_script_thread(self):
        self.append_log(">>> Starting LinkedIn Automation Process...\n")
        
        self.process = subprocess.Popen(
            [sys.executable, MAIN_SCRIPT],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            env=getattr(self, "run_env", os.environ.copy()),
            cwd=BASE_DIR
        )

        for line in self.process.stdout:
            self.append_log(line)
            
        self.process.wait()
        if self.process: # If it wasn't stopped manually
            self.append_log("\n>>> Process Completed.\n")
            self.run_button.configure(state="normal", text="Run Automation")
            self.stop_button.configure(state="disabled")
            self.process = None

    def append_log(self, text):
        self.log_textbox.insert("end", text)
        self.log_textbox.see("end")

    def forget_user_data(self):
        confirm = messagebox.askyesno("Warning", "Are you sure you want to delete all user data?\n\nThis will remove:\n- All saved credentials\n- Search keywords\n- Found emails (recruiters.csv)\n- Sent history (sent_log.csv)\n- Saved browser sessions\n\nThis action CANNOT be undone.")
        if confirm:
            import shutil
            # 1. Delete physical files
            if os.path.exists(ENV_FILE): os.remove(ENV_FILE)
            if os.path.exists(KEYWORDS_FILE): os.remove(KEYWORDS_FILE)
            if os.path.exists(DATA_DIR):
                for file in os.listdir(DATA_DIR):
                    file_path = os.path.join(DATA_DIR, file)
                    try:
                        if os.path.isfile(file_path): os.remove(file_path)
                    except Exception: pass
            if os.path.exists(USER_DATA_DIR):
                try: shutil.rmtree(USER_DATA_DIR)
                except Exception: pass
            
            # 2. Reset GUI to factory defaults
            defaults = _default_env_vars()
            
            for key, entry in self.entries.items():
                entry.delete(0, "end")
                entry.insert(0, defaults.get(key, ""))
            
            # Reset Keywords
            self.kw_text.delete("1.0", "end")
            self.kw_text.insert("1.0", "Java Developer hiring\nPython Developer recruiter\n")
            
            # Reset Emails and logs
            self.emails_text.delete("1.0", "end")
            self.emails_text.insert("1.0", "No emails found yet.")
            self.log_textbox.delete("1.0", "end")
            
            # Reset Auto-send switch
            self.auto_send_switch.select()
            
            self.append_log(">>> All user data has been wiped. App reset to factory defaults.\n")
            messagebox.showinfo("Success", "All traces have been deleted and settings reset to defaults.")

if __name__ == "__main__":
    app = App()
    app.mainloop()
