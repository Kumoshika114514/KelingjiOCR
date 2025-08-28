import tkinter as tk
from tkinter import ttk, filedialog
from PIL import Image, ImageTk, ImageGrab
import threading
from paddleocr import PaddleOCR
import cv2
import numpy as np
from typing import List, Optional


class OCRUnit:
    def __init__(self, parent, image: Image.Image):
        self.frame = ttk.Frame(parent, padding=10)
        self.frame.pack(fill=tk.BOTH, expand=True, pady=5, padx=10)

        # image preview
        self.image_label = ttk.Label(self.frame)
        self.image_label.pack(side=tk.LEFT, padx=10)
        self.display_image(image)
        
        # text box and copy button
        text_frame = ttk.Frame(self.frame)
        text_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10)
        
        self.text_box = tk.Text(
            text_frame, 
            height=8, 
            width=65, 
            font=("Arial", 10),
            wrap=tk.WORD
        )
        self.text_box.pack(fill=tk.BOTH, expand=True)
        
        self.copy_btn = ttk.Button(
            text_frame, 
            text="Copy Text",
            command=self.copy_text
        )
        self.copy_btn.pack(anchor=tk.E, pady=(5, 0))
        
        self.text_box.insert(tk.END, "Processing...")
        self.copy_btn.state(["disabled"])
    
    def display_image(self, image: Image.Image):
        img = image.copy()
        img.thumbnail((200, 200))
        photo = ImageTk.PhotoImage(img)
        
        self.image_label.configure(image=photo)
        self.image_label.image = photo
    
    def set_text(self, text: str):
        self.text_box.delete("1.0", tk.END)
        self.text_box.insert(tk.END, text)
        self.copy_btn.state(["!disabled"])
    
    def copy_text(self):
        text = self.text_box.get("1.0", tk.END)
        self.text_box.clipboard_clear()
        self.text_box.clipboard_append(text)


def main():
    root = tk.Tk()
    root.title("Text To Image by Kumoshika")

    # default window size and position
    window_width = 800
    window_height = 600
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    center_x = int(screen_width / 2 - window_width / 2)
    center_y = int(screen_height / 2 - window_height / 2)
    root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
    root.minsize(window_width, window_height)
    root.maxsize(window_width, window_height)

    ocr_units: List[OCRUnit] = []
    MAX_IMAGES = 5


    def reset_all():
        status_label.config(text="Ready")
        for unit in ocr_units:
            unit.frame.destroy()
        ocr_units.clear()

    def configure_styles():
        style = ttk.Style()
        style.configure("Title.TLabel", font=("Helvetica", 24, "bold"), padding=(10, 20))
        style.configure("Select.TButton", font=("Helvetica", 11), padding=(8, 5))
        style.configure("Status.TLabel", font=("Helvetica", 10), foreground="#666")

    def run_paddleocr_ocr(image: Image.Image) -> str:
        try:
            ocr = PaddleOCR(
                lang="ch",
                text_detection_model_name=None,
                #text_detection_model_dir="models/pp_ocr_v5_server_det",
                text_recognition_model_name=None,
                #text_recognition_model_dir="models/pp_ocr_v5_server_rec",
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
                ocr_version="PP-OCRv5"
            )

            img_np = np.array(image.convert("RGB"))

            if img_np.shape[2] == 3:
                img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

            result = ocr.predict(img_np)

            if result: 
                texts = []
                for res_obj in result:
                    if hasattr(res_obj, 'json') and isinstance(res_obj.json, dict):
                        json_data = res_obj.json
                        if 'res' in json_data and isinstance(json_data['res'], dict):
                            res_content = json_data['res']
                            if 'rec_texts' in res_content and isinstance(res_content['rec_texts'], list):
                                texts.extend(
                                    text.strip() 
                                    for text in res_content['rec_texts'] 
                                    if isinstance(text, str) and text.strip()
                                )
                
                if texts:
                    return "\n".join(texts)
                else:
                    return "No text was extracted from the OCR results"
            else:
                return "No text found. "

        except Exception as e:
            return f"PaddleOCR Error: {str(e)}"


    def perform_ocr(image: Image.Image) -> str:
        return run_paddleocr_ocr(image)

    def load_images_from_files() -> List[Image.Image]:
        file_types = [("Image Files", "*.png *.jpg *.jpeg *.bmp *.tiff *.webp")]
        file_paths = filedialog.askopenfilenames(
            title="Select Image Files", 
            filetypes=file_types
        )
        return [Image.open(path) for path in file_paths] if file_paths else []

    def load_image_from_clipboard() -> Optional[Image.Image]:
        image = ImageGrab.grabclipboard()
        return image if isinstance(image, Image.Image) else None

    def process_images(new_images: List[Image.Image]):
        if not new_images:
            status_label.config(text="No images selected")
            return

        current_count = len(ocr_units)
        slots_left = MAX_IMAGES - current_count

        if current_count >= MAX_IMAGES:
            status_label.config(text=f"Limit of {MAX_IMAGES} images reached. Please reset before adding more.")
            return

        if len(new_images) > slots_left:
            status_label.config(
                text=f"Can only add {slots_left} more image(s). Extra will be ignored."
            )
            new_images = new_images[:slots_left]
        else:
            status_label.config(
                text=f"Adding {len(new_images)} image(s)... Total: {current_count + len(new_images)}"
            )

        for img in new_images:
            unit = OCRUnit(scrollable_frame, img)
            ocr_units.append(unit)
            threading.Thread(
                target=process_single_image,
                args=(img, unit),
                daemon=True
            ).start()

    def process_single_image(image: Image.Image, unit: OCRUnit):
        try:
            result = perform_ocr(image)
            unit.set_text(result)
        except Exception as e:
            unit.set_text(f"Error: {str(e)}")

    def create_widgets():
        main_frame = ttk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        reset_btn = ttk.Button(root, text="Reset", command=reset_all, style="Select.TButton")
        reset_btn.pack(anchor="ne", padx=10, pady=10)
        
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(
            title_frame, 
            text='Text To Image Converter', 
            style="Title.TLabel"
        ).pack(side=tk.LEFT)
        
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(
            button_frame,
            text='Select Images',
            command=lambda: process_images(load_images_from_files()),
            style="Select.TButton"
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="Paste From Clipboard",
            command=lambda: process_images(
                [img] if (img := load_image_from_clipboard()) else []
            ),
            style="Select.TButton"
        ).pack(side=tk.LEFT, padx=5)
        
        nonlocal status_label
        status_label = ttk.Label(
            button_frame, 
            text="Ready to process images", 
            style="Status.TLabel"
        )
        status_label.pack(side=tk.RIGHT, padx=10)
        
        nonlocal results_frame, scrollable_frame
        results_frame = ttk.Frame(main_frame)
        results_frame.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(results_frame)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        scrollable_frame = ttk.Frame(canvas)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        scrollable_frame.bind("<Configure>", on_frame_configure)

        canvas.configure(yscrollcommand=scrollbar.set)


    status_label = None
    results_frame = None
    scrollable_frame = None
    
    configure_styles()
    create_widgets()
    root.mainloop()


if __name__ == "__main__":
    main()