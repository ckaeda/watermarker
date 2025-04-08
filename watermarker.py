import os
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageDraw, ImageTk, ExifTags
import rawpy
import imageio
import threading

CONVERTING = False

def select_folder():
    folder_selected = filedialog.askdirectory()
    folder_path.set(folder_selected)

def select_watermark():
    file_selected = filedialog.askopenfilename(filetypes=[("PNG files", "*.png")])
    watermark_path.set(file_selected)

def apply_watermark(image, watermark, scale_factor, position, h_margin, v_margin):
    wm_width, wm_height = watermark.size
    new_width = int(wm_width * scale_factor)
    new_height = int(wm_height * scale_factor)
    
    wm_resized = watermark.resize((new_width, new_height), Image.LANCZOS)
    
    if position == "Top Left":
        pos = (h_margin, v_margin)
    elif position == "Top Right":
        pos = (image.width - new_width - h_margin, v_margin)
    elif position == "Bottom Left":
        pos = (h_margin, image.height - new_height - v_margin)
    else:  # Bottom Right (default)
        pos = (image.width - new_width - h_margin, image.height - new_height - v_margin)
    
    image.paste(wm_resized, pos, wm_resized)
    return image

def preview_watermark():
    folder = folder_path.get()
    watermark_file = watermark_path.get()
    if not folder or not watermark_file:
        messagebox.showerror("Error", "Please select a folder and a watermark image.")
        return
    
    try:
        scale_factor = float(scale_entry.get()) / 100
        h_margin = int(h_margin_entry.get())
        v_margin = int(v_margin_entry.get())
    except ValueError:
        messagebox.showerror("Error", "Please enter valid numerical values.")
        return
    
    position = position_var.get()
    
    for filename in os.listdir(folder):
        if filename.lower().endswith((".png", ".jpg", ".jpeg")):
            image_path = os.path.join(folder, filename)
            image = Image.open(image_path).convert("RGBA")
            watermark = Image.open(watermark_file).convert("RGBA")
            
            watermarked_image = apply_watermark(image, watermark, scale_factor, position, h_margin, v_margin)
            watermarked_image = watermarked_image.convert("RGB")
            
            img_scale_factor = 500 / watermarked_image.height
            scaled_height = watermarked_image.height * img_scale_factor
            scaled_width = watermarked_image.width * img_scale_factor

            preview_window = tk.Toplevel(root)
            preview_window.title("Watermark Preview")
            preview_window.geometry(f"{int(scaled_width + 10)}x{int(scaled_height + 10)}")
            
            img_resized = watermarked_image.resize((int(scaled_width), int(scaled_height)), Image.LANCZOS)
            img_preview = ImageTk.PhotoImage(img_resized)
            preview_label = tk.Label(preview_window, image=img_preview)
            preview_label.image = img_preview
            preview_label.pack()
            return  # Only preview the first image

def add_watermark():
    global CONVERTING
    CONVERTING = True
    folder = folder_path.get()
    watermark_file = watermark_path.get()
    if not folder or not watermark_file:
        messagebox.showerror("Error", "Please select a folder and a watermark image.")
        return
    
    output_folder = os.path.join(folder, "watermarked")
    os.makedirs(output_folder, exist_ok=True)
    
    watermark = Image.open(watermark_file).convert("RGBA")
    
    try:
        scale_factor = float(scale_entry.get()) / 100
        h_margin = int(h_margin_entry.get())
        v_margin = int(v_margin_entry.get())
        
    except ValueError:
        messagebox.showerror("Error", "Please enter valid numerical values.")
        return
    
    position = position_var.get()
    status_label.config(text="Processing images...")
    root.update_idletasks()
    
    for i, filename in enumerate(os.listdir(folder)):
        root.after(0, lambda: comment_label.config(text=""))
        file_path = os.path.join(folder, filename)
        
        if filename.lower().endswith(".nef"):
            jpg_filename = os.path.splitext(filename)[0] + ".JPG"
            jpg_path = os.path.join(folder, jpg_filename)
            
            try:
                with rawpy.imread(file_path) as raw:
                    root.after(0, lambda: comment_label.config(text=f"Converting {filename} to {jpg_filename}..."))
                    rgb = raw.postprocess()
                    imageio.imsave(jpg_path, rgb, quality=95)
                    
                os.remove(file_path)
                filename = jpg_filename
                file_path = jpg_path
            except Exception as e:
                messagebox.showinfo("Error", f"Error converting {filename}: {e}")

        if filename.lower().endswith((".png", ".jpg", ".jpeg")):
            try:
                image = Image.open(file_path)
                exif = image._getexif()
                
                if exif is not None:
                    for tag, value in exif.items():
                        tag_name = ExifTags.TAGS.get(tag, tag)
                        if tag_name == 'Orientation':
                            if value == 3:
                                image = image.rotate(180, expand=True)
                            elif value == 6:
                                image = image.rotate(270, expand=True)
                            elif value == 8:
                                image = image.rotate(90, expand=True)
                            image.save(file_path)
                            break
            except Exception as e:
                messagebox.showinfo("Error", f"Error processing {file_path}: {e}")
            
            image = image.convert("RGBA")
            root.after(0, lambda: status_label.config(text=f"Applying watermark to {filename} ({i+1}/{len(os.listdir(folder))})"))
            watermarked_image = apply_watermark(image, watermark, scale_factor, position, h_margin, v_margin)
            watermarked_image.convert("RGB").save(os.path.join(output_folder, filename))
    
    status_label.config(text="Watermarking complete!")
    messagebox.showinfo("Success", f"Watermarks added to images in: {output_folder}")
    toggle_inputs(tk.NORMAL)
    CONVERTING = False
    os.startfile(output_folder)

def submit():
    threading.Thread(target=add_watermark, daemon=True).start()
    toggle_inputs(tk.DISABLED)

def toggle_inputs(state):
    widgets = [folder_entry, watermark_entry, scale_entry, h_margin_entry, v_margin_entry, position_menu, select_btn, watermark_btn, preview_btn, apply_btn]
    for widget in widgets:
        widget.config(state=state)

def on_close():
    global CONVERTING
    if CONVERTING:
        response = messagebox.askyesno("Exit", "Watermarking still in progress. Do you really want to exit?")
        if not response:
            return  # Cancel exit if the user chooses "No"

    root.destroy()  # Close the application

# GUI Setup
root = tk.Tk()
root.title("Image Watermarker")
root.geometry("500x400")
root.protocol("WM_DELETE_WINDOW", on_close)  # Override exit button behavior

folder_path = tk.StringVar()
watermark_path = tk.StringVar()
position_var = tk.StringVar(value="Bottom Right")

frame = tk.Frame(root)
frame.pack(pady=10)

tk.Label(frame, text="Select Folder:").grid(row=0, column=0)
folder_entry = tk.Entry(frame, textvariable=folder_path, width=40)
folder_entry.grid(row=0, column=1)
select_btn = tk.Button(frame, text="Browse", command=select_folder)
select_btn.grid(row=0, column=2)

tk.Label(frame, text="Select Watermark:").grid(row=1, column=0)
watermark_entry = tk.Entry(frame, textvariable=watermark_path, width=40)
watermark_entry.grid(row=1, column=1)
watermark_btn = tk.Button(frame, text="Browse", command=select_watermark)
watermark_btn.grid(row=1, column=2)

tk.Label(frame, text="Scale Factor (%):").grid(row=2, column=0)
scale_entry = tk.Entry(frame, width=10)
scale_entry.grid(row=2, column=1)
scale_entry.insert(0, "10")

positions = ["Top Left", "Top Right", "Bottom Left", "Bottom Right"]
tk.Label(frame, text="Watermark Position:").grid(row=3, column=0)
position_menu = tk.OptionMenu(frame, position_var, *positions)
position_menu.grid(row=3, column=1)

tk.Label(frame, text="Horizontal Margin:").grid(row=4, column=0)
h_margin_entry = tk.Entry(frame, width=10)
h_margin_entry.grid(row=4, column=1)
h_margin_entry.insert(0, "10")

tk.Label(frame, text="Vertical Margin:").grid(row=5, column=0)
v_margin_entry = tk.Entry(frame, width=10)
v_margin_entry.grid(row=5, column=1)
v_margin_entry.insert(0, "10")

preview_btn = tk.Button(root, text="Preview Watermark", command=preview_watermark)
preview_btn.pack(pady=10)

apply_btn = tk.Button(root, text="Add Watermark", command=submit)
apply_btn.pack(pady=10)

status_label = tk.Label(root, text="")
status_label.pack()

comment_label = tk.Label(root, text="")
comment_label.pack()

root.mainloop()
