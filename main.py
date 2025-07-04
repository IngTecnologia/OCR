import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
from tkinterdnd2 import DND_FILES, TkinterDnD
from PIL import Image, ImageTk
import easyocr
import threading
import os
from pathlib import Path
import cv2
import numpy as np
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from docx import Document
import json

# Fix for Pillow compatibility
try:
    # For older versions of Pillow
    if not hasattr(Image, 'ANTIALIAS'):
        Image.ANTIALIAS = Image.Resampling.LANCZOS
except AttributeError:
    pass

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class OCRApp:
    def __init__(self):
        self.root = TkinterDnD.Tk()
        self.root.title("OCR Pro - Extractor de Texto")
        self.root.geometry("1400x900")
        
        self.reader = None
        self.images = []
        self.ocr_results = []
        self.current_preview_index = 0
        
        self.init_ui()
        self.init_ocr()
        
    def init_ui(self):
        # Main container
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title
        title_label = ctk.CTkLabel(main_frame, text="OCR Pro", font=ctk.CTkFont(size=24, weight="bold"))
        title_label.pack(pady=10)
        
        # Content frame
        content_frame = ctk.CTkFrame(main_frame)
        content_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Left panel - Image list and controls
        self.left_panel = ctk.CTkFrame(content_frame)
        self.left_panel.pack(side="left", fill="y", padx=(0, 5))
        
        # Drop zone and file selection
        self.drop_frame = ctk.CTkFrame(self.left_panel, height=150)
        self.drop_frame.pack(fill="x", padx=10, pady=10)
        self.drop_frame.pack_propagate(False)
        
        drop_label = ctk.CTkLabel(self.drop_frame, text="Arrastra imágenes aquí\n(PNG, JPG, JPEG, BMP)", 
                                 font=ctk.CTkFont(size=14))
        drop_label.pack(expand=True, pady=(10, 5))
        
        # File selection button
        self.select_files_btn = ctk.CTkButton(self.drop_frame, text="📁 Seleccionar Archivos", 
                                             command=self.select_files, width=200)
        self.select_files_btn.pack(pady=(0, 10))
        
        # Configure drag and drop
        self.drop_frame.drop_target_register(DND_FILES)
        self.drop_frame.dnd_bind('<<Drop>>', self.drop_files)
        
        # Image list
        list_label = ctk.CTkLabel(self.left_panel, text="Imágenes:", font=ctk.CTkFont(size=16, weight="bold"))
        list_label.pack(pady=(20, 5))
        
        self.image_listbox = tk.Listbox(self.left_panel, height=15, bg="#212121", fg="white", 
                                       selectbackground="#1f538d", font=("Arial", 10))
        self.image_listbox.pack(fill="both", expand=True, padx=10, pady=5)
        self.image_listbox.bind('<<ListboxSelect>>', self.on_image_select)
        
        # Control buttons
        button_frame = ctk.CTkFrame(self.left_panel)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        self.move_up_btn = ctk.CTkButton(button_frame, text="▲", width=50, command=self.move_up)
        self.move_up_btn.pack(side="left", padx=2)
        
        self.move_down_btn = ctk.CTkButton(button_frame, text="▼", width=50, command=self.move_down)
        self.move_down_btn.pack(side="left", padx=2)
        
        self.remove_btn = ctk.CTkButton(button_frame, text="Eliminar", width=80, command=self.remove_image)
        self.remove_btn.pack(side="left", padx=2)
        
        self.process_btn = ctk.CTkButton(button_frame, text="Procesar OCR", width=120, command=self.process_ocr)
        self.process_btn.pack(side="left", padx=2)
        
        # Export buttons
        export_frame = ctk.CTkFrame(self.left_panel)
        export_frame.pack(fill="x", padx=10, pady=5)
        
        self.export_txt_btn = ctk.CTkButton(export_frame, text="Exportar TXT", command=self.export_txt)
        self.export_txt_btn.pack(side="left", padx=2)
        
        self.export_pdf_btn = ctk.CTkButton(export_frame, text="Exportar PDF", command=self.export_pdf)
        self.export_pdf_btn.pack(side="left", padx=2)
        
        # Right panel - Preview
        self.right_panel = ctk.CTkFrame(content_frame)
        self.right_panel.pack(side="right", fill="both", expand=True, padx=(5, 0))
        
        preview_label = ctk.CTkLabel(self.right_panel, text="Vista Previa", font=ctk.CTkFont(size=16, weight="bold"))
        preview_label.pack(pady=10)
        
        # Preview content
        self.preview_frame = ctk.CTkFrame(self.right_panel)
        self.preview_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Image preview
        self.image_label = ctk.CTkLabel(self.preview_frame, text="Selecciona una imagen para ver la vista previa")
        self.image_label.pack(pady=10)
        
        # Text preview
        self.text_frame = ctk.CTkFrame(self.preview_frame)
        self.text_frame.pack(fill="both", expand=True, pady=10)
        
        text_label = ctk.CTkLabel(self.text_frame, text="Texto extraído:", font=ctk.CTkFont(size=14, weight="bold"))
        text_label.pack(pady=(10, 5))
        
        self.text_preview = ctk.CTkTextbox(self.text_frame, height=300)
        self.text_preview.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Status bar
        self.status_label = ctk.CTkLabel(main_frame, text="Listo", font=ctk.CTkFont(size=12))
        self.status_label.pack(pady=5)
    
    def init_ocr(self):
        def load_ocr():
            try:
                self.status_label.configure(text="Inicializando OCR...")
                self.reader = easyocr.Reader(['es', 'en'], gpu=True)
                self.status_label.configure(text="OCR inicializado - Listo")
            except Exception as e:
                self.status_label.configure(text=f"Error al inicializar OCR: {str(e)}")
                
        thread = threading.Thread(target=load_ocr)
        thread.daemon = True
        thread.start()
    
    def drop_files(self, event):
        files = self.root.tk.splitlist(event.data)
        valid_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp'}
        
        for file_path in files:
            if Path(file_path).suffix.lower() in valid_extensions:
                self.add_image(file_path)
    
    def select_files(self):
        file_types = [
            ("Archivos de imagen", "*.png *.jpg *.jpeg *.bmp *.tiff *.webp"),
            ("PNG", "*.png"),
            ("JPEG", "*.jpg *.jpeg"),
            ("BMP", "*.bmp"),
            ("TIFF", "*.tiff"),
            ("WebP", "*.webp"),
            ("Todos los archivos", "*.*")
        ]
        
        files = filedialog.askopenfilenames(
            title="Seleccionar imágenes",
            filetypes=file_types
        )
        
        if files:
            for file_path in files:
                self.add_image(file_path)
    
    def add_image(self, file_path):
        if file_path not in [img['path'] for img in self.images]:
            self.images.append({'path': file_path, 'text': ''})
            self.image_listbox.insert(tk.END, Path(file_path).name)
            self.status_label.configure(text=f"Imagen agregada: {Path(file_path).name}")
    
    def on_image_select(self, event):
        selection = self.image_listbox.curselection()
        if selection:
            self.current_preview_index = selection[0]
            self.update_preview()
    
    def update_preview(self):
        if not self.images:
            return
            
        image_data = self.images[self.current_preview_index]
        
        # Load and display image
        try:
            img = Image.open(image_data['path'])
            img.thumbnail((400, 400), Image.Resampling.LANCZOS)
            # Convert to PhotoImage for compatibility
            photo = ImageTk.PhotoImage(img)
            self.image_label.configure(image=photo, text="")
            self.image_label.image = photo
        except Exception as e:
            self.image_label.configure(text=f"Error al cargar imagen: {str(e)}")
        
        # Update text preview
        self.text_preview.delete("1.0", tk.END)
        self.text_preview.insert("1.0", image_data['text'])
    
    def move_up(self):
        selection = self.image_listbox.curselection()
        if selection and selection[0] > 0:
            idx = selection[0]
            self.images[idx], self.images[idx-1] = self.images[idx-1], self.images[idx]
            self.refresh_listbox()
            self.image_listbox.selection_set(idx-1)
    
    def move_down(self):
        selection = self.image_listbox.curselection()
        if selection and selection[0] < len(self.images) - 1:
            idx = selection[0]
            self.images[idx], self.images[idx+1] = self.images[idx+1], self.images[idx]
            self.refresh_listbox()
            self.image_listbox.selection_set(idx+1)
    
    def remove_image(self):
        selection = self.image_listbox.curselection()
        if selection:
            idx = selection[0]
            del self.images[idx]
            self.refresh_listbox()
            if self.images and idx < len(self.images):
                self.image_listbox.selection_set(idx)
                self.update_preview()
    
    def refresh_listbox(self):
        self.image_listbox.delete(0, tk.END)
        for img in self.images:
            self.image_listbox.insert(tk.END, Path(img['path']).name)
    
    def process_ocr(self):
        if not self.reader:
            self.status_label.configure(text="OCR no inicializado")
            return
        
        if not self.images:
            self.status_label.configure(text="No hay imágenes para procesar")
            return
        
        def process():
            try:
                self.status_label.configure(text="Procesando OCR...")
                for i, image_data in enumerate(self.images):
                    self.status_label.configure(text=f"Procesando imagen {i+1}/{len(self.images)}...")
                    
                    try:
                        # Handle paths with special characters
                        file_path = image_data['path']
                        
                        # Use PIL to read image first (better unicode support)
                        pil_img = Image.open(file_path)
                        # Convert PIL to numpy array
                        img_array = np.array(pil_img)
                        
                        # If image is RGBA, convert to RGB
                        if len(img_array.shape) == 3 and img_array.shape[2] == 4:
                            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)
                        
                        # Convert RGB to BGR for OpenCV
                        if len(img_array.shape) == 3:
                            img = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
                        else:
                            img = img_array
                        
                        # Convert to grayscale and enhance
                        if len(img.shape) == 3:
                            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                        else:
                            gray = img
                        
                        enhanced = cv2.convertScaleAbs(gray, alpha=1.2, beta=30)
                        
                        # OCR using enhanced image
                        results = self.reader.readtext(enhanced)
                        text = '\n'.join([item[1] for item in results])
                        
                        image_data['text'] = text
                        
                    except Exception as img_error:
                        self.status_label.configure(text=f"Error procesando {Path(file_path).name}: {str(img_error)}")
                        image_data['text'] = f"Error: No se pudo procesar la imagen - {str(img_error)}"
                        continue
                
                self.status_label.configure(text="OCR completado")
                self.update_preview()
                
            except Exception as e:
                self.status_label.configure(text=f"Error en OCR: {str(e)}")
        
        thread = threading.Thread(target=process)
        thread.daemon = True
        thread.start()
    
    def export_txt(self):
        if not any(img['text'] for img in self.images):
            self.status_label.configure(text="No hay texto extraído para exportar")
            return
        
        try:
            with open("ocr_output.txt", "w", encoding="utf-8") as f:
                for i, img in enumerate(self.images):
                    if img['text']:
                        f.write(f"=== Imagen {i+1}: {Path(img['path']).name} ===\n")
                        f.write(img['text'])
                        f.write("\n\n")
            
            self.status_label.configure(text="Texto exportado a ocr_output.txt")
        except Exception as e:
            self.status_label.configure(text=f"Error al exportar: {str(e)}")
    
    def export_pdf(self):
        if not any(img['text'] for img in self.images):
            self.status_label.configure(text="No hay texto extraído para exportar")
            return
        
        try:
            c = canvas.Canvas("ocr_output.pdf", pagesize=letter)
            width, height = letter
            y_position = height - 50
            
            for i, img in enumerate(self.images):
                if img['text']:
                    c.drawString(50, y_position, f"Imagen {i+1}: {Path(img['path']).name}")
                    y_position -= 30
                    
                    lines = img['text'].split('\n')
                    for line in lines:
                        if y_position < 50:
                            c.showPage()
                            y_position = height - 50
                        c.drawString(70, y_position, line[:80])
                        y_position -= 15
                    
                    y_position -= 20
            
            c.save()
            self.status_label.configure(text="PDF exportado a ocr_output.pdf")
        except Exception as e:
            self.status_label.configure(text=f"Error al exportar PDF: {str(e)}")
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = OCRApp()
    app.run()