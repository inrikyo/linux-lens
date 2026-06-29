import json  
import subprocess
import tempfile
import threading
import tkinter as tk
from sub_osr_pro import ocr_with_layout
import tkinter.messagebox as messagebox
from tkinter import filedialog
import webbrowser as wb
from queue import Queue
import customtkinter as ctk
import requests
from PIL import Image, ImageEnhance, ImageGrab, ImageTk
import sys
import time

# Remove duplicate import - only need one threading import

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# Global variable for model preload status
model_loading = False
model_loaded = False

class bigimagebox:
    def __init__(self, boxa):  # ← Fixed: only need boxa
        self.boxa = boxa
        self.boxa.attributes("-fullscreen", True)

        screen_width = self.boxa.winfo_screenwidth()
        screen_height = self.boxa.winfo_screenheight()

        self.canvas = tk.Canvas(
            self.boxa,
            width=screen_width,
            height=screen_height,
            highlightthickness=0,
            cursor="crosshair",
        )
        self.canvas.pack(fill="both", expand=True)
        self.canvas.focus_set()

        # Take screenshot NOW (not at module load)
        self.screenshot = ImageGrab.grab()

        try:
            # Use NEAREST for speed (LANCZOS is slow)
            image = self.screenshot.resize((screen_width, screen_height), Image.NEAREST)
            # Dim the image using point() instead of ImageEnhance
            dimmed_image = image.point(lambda p: int(p * 0.5))
            self.photo = ImageTk.PhotoImage(dimmed_image)

            self.canvas.create_image(0, 0, image=self.photo, anchor="nw")
        except Exception as e:
            print(f"Error displaying image: {e}")
            messagebox.showerror("Image Error", f"Error processing image:\n{e}")
            self.canvas.configure(bg="black")

        self.start_x = None
        self.start_y = None
        self.rect = None

        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        self.canvas.bind("<Escape>", lambda e: self.boxa.destroy())

    def on_button_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        if self.rect:
            self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(
            self.start_x,
            self.start_y,
            self.start_x,
            self.start_y,
            outline="red",
            width=2,
        )

    def on_move_press(self, event):
        curX, curY = event.x, event.y
        self.canvas.coords(self.rect, self.start_x, self.start_y, curX, curY)

    def on_button_release(self, event):
        x1, y1 = self.start_x, self.start_y
        x2, y2 = event.x, event.y

        left = min(x1, x2)
        right = max(x1, x2)
        top = min(y1, y2)
        bottom = max(y1, y2)

        if right - left < 5 or bottom - top < 5:
            messagebox.showwarning(
                "Selection Too Small", "Please draw a larger selection area."
            )
            return

        try:
            cropped = self.screenshot.crop((left, top, right, bottom))

            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                cropped.save(tmp.name)
                self.tempfile_path = tmp.name

            self.boxa.destroy()

        except Exception as e:
            print(f"Cropping failed: {e}")
            messagebox.showerror(
                "Cropping Error", f"Failed to crop image:\n{e}"
            )


class bluat:
    def __init__(self, root, img_path):
        self.root = root
        self.img_path = img_path

        self.root.geometry("700x700")
        self.root.title("ScreenSearch")
        self.root.configure(fg_color="#1e1e2e")

        # ===== GRID LAYOUT =====
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # ===== TOOLBAR =====
        self.toolbar = ctk.CTkFrame(self.root, fg_color="#181825", height=40)
        self.toolbar.grid(row=0, column=0, sticky="ew")

        ctk.CTkButton(
            self.toolbar,
            text="image",
            command=self.imagetaken,
            fg_color="#89b4fa",
            hover_color="#74c7ec",
            width=100,
        ).pack(side="left", padx=5, pady=5)

        ctk.CTkButton(
            self.toolbar,
            text="🔍 Search",
            command=self.search,
            fg_color="#89b4fa",
            hover_color="#74c7ec",
            width=100,
        ).pack(side="left", padx=5, pady=5)

        ctk.CTkButton(
            self.toolbar,
            text="📝 OCR",
            command=self.ocr,
            fg_color="#a6e3a1",
            hover_color="#94e2d5",
            width=100,
        ).pack(side="left", padx=5, pady=5)

        ctk.CTkButton(
            self.toolbar,
            text="🧹 Clear",
            command=self.clear_text,
            fg_color="#f38ba8",
            hover_color="#eba0ac",
            width=100,
        ).pack(side="left", padx=5, pady=5)

        self.main = ctk.CTkFrame(self.root, fg_color="transparent")
        self.main.grid(row=1, column=0, sticky="nsew")

        self.main.grid_rowconfigure(1, weight=1)
        self.main.grid_columnconfigure(0, weight=1)

        # Display image
        img = Image.open(self.img_path)
        self.ctk_img = ctk.CTkImage(img, size=(700, 300))

        self.image_label = ctk.CTkLabel(
            self.main,
            image=self.ctk_img,
            text="",
        )
        self.image_label.grid(row=0, column=0, pady=10)

        # Text area
        self.textbox = ctk.CTkTextbox(
            self.main, fg_color="#1a1b26", text_color="#c0caf5", corner_radius=10
        )
        self.textbox.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.textbox.configure(font=("JetBrains Mono", 12))

        # Status bar
        self.status = ctk.CTkLabel(
            self.root, text="✅ Ready", anchor="w", fg_color="#181825", height=25
        )
        self.status.grid(row=2, column=0, sticky="ew")

        # Check if model is already loaded
        if model_loaded:
            self.status.configure(text="✅ OCR model ready")
        else:
            self.status.configure(text="⏳ Loading OCR model...")

    def imagetaken(self):
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[
                    ("PNG files", "*.png"),
                    ("JPEG files", "*.jpg"),
                    ("All files", "*.*")
                ],
                title="save screenshot as"
            )

            if file_path:
                # Take fresh screenshot
                fresh_screenshot = ImageGrab.grab()
                fresh_screenshot.save(file_path)
                print("Screenshot saved!")
            else:
                print("No save")

        except Exception as e:
            print(f"Save error: {e}")

    def search(self):
        confirm = messagebox.askyesno(
            "Upload Image", "This will be uploaded to an external server. Continue?"
        )

        if confirm:
            self.status.configure(text="📤 Uploading for search...")
            try:
                YesImageMe(self.img_path)
                self.status.configure(text="🌐 Opened in browser")
            except Exception as e:
                self.status.configure(text=f"❌ Upload failed: {str(e)[:50]}")

    def ocr(self):
        """OCR button handler - runs in background"""
        self.status.configure(text="🔍 Running OCR...")
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", "⏳ Processing... Please wait...\n")
        
        # Run OCR in background
        thread = threading.Thread(target=self._ocr_worker, daemon=True)
        thread.start()

    def _ocr_worker(self):
        """OCR worker - runs in background thread"""
        try:
            # This is the slow part - runs in background
            text = textmebro(self.img_path)
            text = format_text(text)
            
            # Update UI from main thread
            self.root.after(0, self._update_textbox, text)
            self.root.after(0, lambda: self.status.configure(text="✅ OCR complete"))
            
        except Exception as e:
            error_msg = f"❌ OCR failed: {str(e)}"
            self.root.after(0, lambda: self.status.configure(text=error_msg[:50]))
            self.root.after(0, lambda: self._update_textbox(f"Error: {str(e)}"))

    def _update_textbox(self, text):
        """Update textbox from main thread"""
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", text)

    def clear_text(self):
        self.textbox.delete("1.0", "end")
        self.status.configure(text="🧹 Cleared")


class YesImageMe:
    def __init__(self, img_path):
        self.img_path = img_path

        self.url = "https://tmpfiles.org/api/v1/upload"
        with open(self.img_path, "rb") as f:
            responses = requests.post(self.url, files={"file": f})

        data = responses.json()
        url = data["data"]["url"]
        direct_url = url.replace("https://tmpfiles.org/", "https://tmpfiles.org/dl/")
        print(direct_url)

        link = f"https://imgops.com/{direct_url}"
        wb.open(link)


def textmebro(img_path):
    try:
        text = ocr_with_layout(img_path)
        return text if text else "No text detected"
    except Exception as e:
        return f"OCR error: {e}"


def format_text(text):
    """Clean up OCR text but preserve structure"""
    if not text:
        return "No text detected"
    
    lines = text.split('\n')
    
    while lines and not lines[-1].strip():
        lines.pop()
    
    while lines and not lines[0].strip():
        lines.pop(0)
    
    return '\n'.join(lines)


def preload_ocr_model():
    """Preload the OCR model in background"""
    global model_loading, model_loaded
    model_loading = True
    try:
        import sub_osr_pro
        sub_osr_pro.get_reader()  # This loads the model
        model_loaded = True
        print("✅ OCR model preloaded successfully")
    except Exception as e:
        print(f"❌ Failed to preload OCR model: {e}")
    finally:
        model_loading = False


if __name__ == "__main__":
    # Start preloading OCR model in background
    print("🔄 Preloading OCR model in background...")
    threading.Thread(target=preload_ocr_model, daemon=True).start()
    
    # Show screenshot selector immediately (doesn't wait for model)
    print("📸 Starting screenshot selector...")
    boxa = tk.Tk()
    selector = bigimagebox(boxa)  # ← Fixed: only pass boxa
    boxa.mainloop()
    
    # By the time user selects area, model is probably loaded
    if hasattr(selector, "tempfile_path"):
        root = ctk.CTk()
        ui = bluat(root, selector.tempfile_path)
        root.mainloop()
    else:
        print("No image selected")