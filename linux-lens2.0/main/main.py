import json  
from osr_proso import ocr_with_layout
import subprocess, sys
import tempfile
import threading
import tkinter as tk
import tkinter.messagebox as messagebox
import webbrowser as wb
from queue import Queue
import customtkinter as ctk
import requests
from PIL import Image, ImageEnhance, ImageGrab, ImageTk

nordic_colors = {
    "primary": "#5e81ac",      # muted blue
    "primary_hover": "#81a1c1", # lighter blue
    "success": "#a3be8c",       # muted green
    "success_hover": "#b48ead", # soft purple
    "danger": "#bf616a",        # muted red
    "danger_hover": "#d08770",  # warm orange
}

screenshot = ImageGrab.grab()

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

class bigimagebox:
    def __init__(self, boxa):
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

        try:
            image = screenshot.resize((screen_width, screen_height), Image.LANCZOS)
            enhancer = ImageEnhance.Brightness(image)
            dimmed_image = enhancer.enhance(0.5)
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
            cropped = screenshot.crop((left, top, right, bottom))

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

        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self.toolbar = ctk.CTkFrame(self.root, fg_color="#181825", height=40)
        self.toolbar.grid(row=0, column=0, sticky="ew")

        ctk.CTkButton(
            self.toolbar,
            text="search",
            command=self.search,
            fg_color=nordic_colors["primary"],
            hover_color=nordic_colors["primary_hover"],
            width=100,
            corner_radius=6,  # nordic minimalism
        ).pack(side="left", padx=5, pady=5)

        ctk.CTkButton(
            self.toolbar,
            text="ocr",
            command=self.ocr,
            fg_color=nordic_colors["success"],
            hover_color=nordic_colors["success_hover"],
            width=100,
            corner_radius=6,
        ).pack(side="left", padx=5, pady=5)

        ctk.CTkButton(
            self.toolbar,
            text="clear",
            command=self.clear_text,
            fg_color=nordic_colors["danger"],
            hover_color=nordic_colors["danger_hover"],
            width=100,
            corner_radius=6,
        ).pack(side="left", padx=5, pady=5)

        self.main = ctk.CTkFrame(self.root, fg_color="transparent")
        self.main.grid(row=1, column=0, sticky="nsew")

        self.main.grid_rowconfigure(1, weight=1)
        self.main.grid_columnconfigure(0, weight=1)

        img = Image.open(self.img_path)
        self.ctk_img = ctk.CTkImage(img, size=(700, 300))

        self.image_label = ctk.CTkLabel(
            self.main,
            image=self.ctk_img,
            text="",
        )
        self.image_label.grid(row=0, column=0, pady=10)

        self.textbox = ctk.CTkTextbox(
            self.main, fg_color="#1a1b26", text_color="#c0caf5", corner_radius=10
        )
        self.textbox.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.textbox.configure(font=("JetBrains Mono", 12))

        self.status = ctk.CTkLabel(
            self.root, text="ready", anchor="w", fg_color="#181825", height=25
        )
        self.status.grid(row=2, column=0, sticky="ew")

    def search(self):
        confirm = messagebox.askyesno(
            "Upload Image", "This will be uploaded to a temphost online, shall we you know?"
        )

        if confirm:
            self.status.configure(text="putting it for search...")
            try:
                YesImageMe(self.img_path)
                self.status.configure(text="its... opning")
            except Exception as e:
                self.status.configure(text=f"mission failed better luck next time: {str(e)[:50]}")

    def ocr(self):
        self.status.configure(text="OCR is running")
        threading.Thread(target=self._ocr_worker, daemon=True).start()

    def _ocr_worker(self):
        try:
            text = textmebro(self.img_path)
            text = format_text(text)
            self.root.after(0, self._update_textbox, text)
            self.root.after(0, lambda: self.status.configure(text="OCR finished the marathon first"))
        except Exception as e:
            self.root.after(0, lambda: self.status.configure(text=f"OCR lost: {str(e)[:50]}"))
            self.root.after(0, lambda: self._update_textbox(f"Error: {str(e)}"))

    def _update_textbox(self, text):
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", text)

    def clear_text(self):
        self.textbox.delete("1.0", "end")
        self.status.configure(text="cleared")
    
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
        return text if text else "i did my best dude idk what going on"
    except Exception as e:
        return f"ocr error{e}"


def format_text(text):

    if not text:
        return "No text detected"

    lines = text.split('\n')
    

    while lines and not lines[-1].strip():
        lines.pop()

    while lines and not lines[0].strip():
        lines.pop(0)
    

    return '\n'.join(lines)


if __name__ == "__main__":
    import sys 
    
    boxa = tk.Tk()
    selector = bigimagebox(boxa)
    boxa.mainloop()

    if hasattr(selector, "tempfile_path"):
        root = ctk.CTk()
        ui = bluat(root, selector.tempfile_path)
        root.mainloop()
    else:
        print("No image selected - awkward...")