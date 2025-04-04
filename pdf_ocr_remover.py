import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import subprocess
import threading
import fitz  # PyMuPDF

def remove_ocr_from_pdf_pymupdf(
    input_pdf_path, output_pdf_path, progress_label, dpi=200, image_format="jpeg", jpeg_quality=85
):
    """
    Removes OCR text layer from a PDF by rasterizing it using pymupdf.
    Optimized for smaller file size while retaining excellent quality.
    """
    try:
        pdf_document = fitz.open(input_pdf_path)
        new_pdf = fitz.open()  # Create a new PDF in memory

        for page_num in range(pdf_document.page_count):
            page = pdf_document.load_page(page_num)
            # Render page to pixmap (image) at specified DPI
            mat = fitz.Matrix(dpi / 72, dpi / 72)  # Create DPI scaling matrix
            pix = page.get_pixmap(matrix=mat)

            if image_format == "jpeg":
                try:
                    # Try to use quality argument - might fail on older pymupdf
                    img_data = pix.tobytes("jpeg", quality=jpeg_quality)
                except TypeError as e:
                    if "unexpected keyword argument 'quality'" in str(e):
                        print(
                            "Warning: 'quality' argument not supported in your PyMuPDF version. "
                            "Using default JPEG quality."
                        )
                        img_data = pix.tobytes("jpeg")  # Use JPEG without quality argument
                    else:
                        raise
                except Exception as e:
                    raise
            elif image_format == "png":
                img_data = pix.tobytes("png")
            else:
                img_data = pix.tobytes("png")  # Default to PNG if format is not recognized

            img_pdf_page = new_pdf.new_page(width=page.rect.width, height=page.rect.height)
            img_pdf_page.insert_image(page.rect, stream=img_data)

        new_pdf.save(output_pdf_path, garbage=4, deflate=True, clean=True)
        new_pdf.close()
        pdf_document.close()
        return True
    except Exception as e:
        error_message = f"PyMuPDF error: {e}"
        print(f"Error processing {input_pdf_path}: {error_message}")
        tk.messagebox.showerror(
            "PyMuPDF Error",
            f"Error processing {os.path.basename(input_pdf_path)} with PyMuPDF.\n"
            f"{error_message}\n\nIt might be due to an outdated PyMuPDF version.\n"
            "Please try upgrading PyMuPDF (pip install --upgrade pymupdf) or using PNG format.",
            icon="error",
        )
        return False

def remove_ocr_from_pdf_pdftocairo(input_pdf_path, output_pdf_path, progress_label, dpi=200, jpeg_quality=85):
    """
    Removes OCR text layer from a PDF by rasterizing it using pdftocairo.
    """
    try:
        command = [
            "pdftocairo",
            "-pdf",
            "-r",
            str(dpi),
            input_pdf_path,
            output_pdf_path,
        ]
        process = subprocess.run(command, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        error_message = f"pdftocairo command failed with exit code {e.returncode}:\n"
        error_message += f"Command: {' '.join(command)}\n"
        error_message += f"Stderr: {e.stderr.decode()}" if e.stderr else "No stderr output."
        print(f"Error processing {input_pdf_path}: {error_message}")
        tk.messagebox.showerror(
            "pdftocairo Error",
            f"Error processing {os.path.basename(input_pdf_path)} with pdftocairo.\nSee console for details.",
            icon="error",
        )
        return False
    except FileNotFoundError:
        tk.messagebox.showerror(
            "Error",
            "pdftocairo not found. Please ensure it is installed and in your system's PATH.",
            icon="error",
        )
        return False
    except Exception as e:
        generic_error_message = f"An unexpected error occurred during processing:\n{e}"
        print(f"Error processing {input_pdf_path}: {generic_error_message}")
        tk.messagebox.showerror("Error", f"Error processing {os.path.basename(input_pdf_path)}.\nSee console for details.", icon="error")
        return False

def convert_pdf_to_png(input_pdf_path, output_dir, progress_label, dpi=200):
    """
    Converts a PDF into individual PNG images (one per page).
    For each PDF, creates a folder named after the PDF (without extension).
    """
    try:
        pdf_document = fitz.open(input_pdf_path)
        base_name = os.path.splitext(os.path.basename(input_pdf_path))[0]
        # Create a folder with the name of the PDF
        folder_path = os.path.join(output_dir, base_name)
        os.makedirs(folder_path, exist_ok=True)

        for page_num in range(pdf_document.page_count):
            page = pdf_document.load_page(page_num)
            mat = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=mat)
            output_filename = os.path.join(folder_path, f"page_{page_num+1}.png")
            pix.save(output_filename)

        pdf_document.close()
        return True
    except Exception as e:
        error_message = f"Error converting {os.path.basename(input_pdf_path)} to PNG: {e}"
        print(error_message)
        tk.messagebox.showerror("Conversion Error", error_message, icon="error")
        return False

def select_source_folder():
    folder_selected = filedialog.askdirectory()
    if folder_selected:
        source_folder_entry.delete(0, tk.END)
        source_folder_entry.insert(0, folder_selected)

def select_output_folder():
    folder_selected = filedialog.askdirectory()
    if folder_selected:
        output_folder_entry.delete(0, tk.END)
        output_folder_entry.insert(0, folder_selected)

def toggle_output_folder_state():
    if overwrite_var.get():
        output_folder_entry.config(state=tk.DISABLED)
        output_folder_button.config(state=tk.DISABLED)
    else:
        output_folder_entry.config(state=tk.NORMAL)
        output_folder_button.config(state=tk.NORMAL)

def update_ui_based_on_mode():
    mode = operation_mode_var.get()
    if mode == "remove_ocr":
        # Enable image format and JPEG quality controls
        image_format_radio_png.config(state=tk.NORMAL)
        image_format_radio_jpeg.config(state=tk.NORMAL)
        jpeg_quality_scale.config(state=tk.NORMAL)
        process_button.config(text="Remove OCR and Process PDFs")
    else:  # mode == "convert_png"
        # Disable image format controls since we're strictly producing PNG images
        image_format_radio_png.config(state=tk.DISABLED)
        image_format_radio_jpeg.config(state=tk.DISABLED)
        # Force the image format variable to PNG
        image_format_var.set("png")
        # Set JPEG quality to 100, disable the scale
        jpeg_quality_scale.set(100)
        jpeg_quality_scale.config(state=tk.DISABLED)
        process_button.config(text="Convert PDFs to PNG")

def process_pdfs_threaded():
    source_folder = source_folder_entry.get()
    if not source_folder:
        tk.messagebox.showerror("Error", "Please select a source folder.", icon="error")
        enable_ui_elements()
        return

    overwrite_files = overwrite_var.get()
    output_folder = source_folder if overwrite_files else output_folder_entry.get()

    if not overwrite_files and not output_folder:
        tk.messagebox.showerror(
            "Error",
            "Please select an output folder or choose to overwrite files.",
            icon="error",
        )
        enable_ui_elements()
        return

    if not overwrite_files and not os.path.exists(output_folder):
        try:
            os.makedirs(output_folder, exist_ok=True)
        except OSError as e:
            tk.messagebox.showerror("Error", f"Could not create output folder: {e}", icon="error")
            enable_ui_elements()
            return

    pdf_files_to_process = sum(1 for f in os.listdir(source_folder) if f.lower().endswith(".pdf"))
    if pdf_files_to_process == 0:
        tk.messagebox.showinfo("Info", "No PDF files found in the selected source folder.")
        enable_ui_elements()
        return

    progressbar["maximum"] = pdf_files_to_process
    progressbar["value"] = 0
    pdf_files_processed = 0
    pdf_files_failed = 0

    dpi_value = dpi_scale.get()
    jpeg_quality_value = jpeg_quality_scale.get()
    image_format_value = image_format_var.get()
    operation = operation_mode_var.get()

    for i, filename in enumerate(os.listdir(source_folder)):
        if filename.lower().endswith(".pdf"):
            input_pdf_path = os.path.join(source_folder, filename)

            if overwrite_files:
                # For remove OCR, output is a PDF; for convert_png, output is the folder
                output_path = input_pdf_path if operation == "remove_ocr" else output_folder
            else:
                output_path = (
                    os.path.join(output_folder, filename) if operation == "remove_ocr" else output_folder
                )

            update_progress_label(f"Processing: {filename} ({i+1}/{pdf_files_to_process})")

            if operation == "remove_ocr":
                use_pymupdf = True  # True => Use PyMuPDF; False => Use pdftocairo
                if use_pymupdf:
                    success = remove_ocr_from_pdf_pymupdf(
                        input_pdf_path,
                        output_path,
                        progress_label,
                        dpi=dpi_value,
                        image_format=image_format_value,
                        jpeg_quality=jpeg_quality_value,
                    )
                else:
                    success = remove_ocr_from_pdf_pdftocairo(
                        input_pdf_path,
                        output_path,
                        progress_label,
                        dpi=dpi_value,
                        jpeg_quality=jpeg_quality_value,
                    )

                if success:
                    pdf_files_processed += 1
                else:
                    pdf_files_failed += 1

            elif operation == "convert_png":
                success = convert_pdf_to_png(input_pdf_path, output_path, progress_label, dpi=dpi_value)
                if success:
                    pdf_files_processed += 1
                else:
                    pdf_files_failed += 1

            update_progressbar()

    update_progress_label("Processing Complete")
    enable_ui_elements()

    message = f"Processed {pdf_files_processed} PDFs successfully."
    if pdf_files_failed > 0:
        message += f"\nFailed to process {pdf_files_failed} PDFs. Check console for errors."
    tk.messagebox.showinfo("Process Complete", message)

def process_pdfs():
    disable_ui_elements()
    thread = threading.Thread(target=process_pdfs_threaded)
    thread.start()

def update_progress_label(text):
    progress_label.config(text=text)

def update_progressbar():
    progressbar.step(1)

def disable_ui_elements():
    source_folder_button.config(state=tk.DISABLED)
    overwrite_check.config(state=tk.DISABLED)
    output_folder_button.config(state=tk.DISABLED)
    output_folder_entry.config(state=tk.DISABLED)
    process_button.config(state=tk.DISABLED)
    dpi_scale.config(state=tk.DISABLED)
    jpeg_quality_scale.config(state=tk.DISABLED)
    image_format_radio_png.config(state=tk.DISABLED)
    image_format_radio_jpeg.config(state=tk.DISABLED)
    root.update_idletasks()

def enable_ui_elements():
    source_folder_button.config(state=tk.NORMAL)
    overwrite_check.config(state=tk.NORMAL)
    toggle_output_folder_state()
    process_button.config(state=tk.NORMAL)
    dpi_scale.config(state=tk.NORMAL)
    # Let the mode updater decide what to do with other controls
    update_ui_based_on_mode()

# --- GUI Setup ---
root = tk.Tk()
root.title("PDF OCR Remover / PNG Converter")

# Source Folder
source_folder_label = tk.Label(root, text="Source Folder:")
source_folder_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")

source_folder_entry = tk.Entry(root, width=50)
source_folder_entry.grid(row=0, column=1, padx=10, pady=10, sticky="we")

source_folder_button = tk.Button(root, text="Browse", command=select_source_folder)
source_folder_button.grid(row=0, column=2, padx=10, pady=10)

# Overwrite Option
overwrite_var = tk.BooleanVar()
overwrite_check = tk.Checkbutton(
    root, text="Overwrite files in source folder", variable=overwrite_var, command=toggle_output_folder_state
)
overwrite_check.grid(row=1, column=0, columnspan=3, padx=10, pady=5, sticky="w")

# Output Folder
output_folder_label = tk.Label(root, text="Output Folder (if not overwriting):")
output_folder_label.grid(row=2, column=0, padx=10, pady=10, sticky="w")

output_folder_entry = tk.Entry(root, width=50, state=tk.NORMAL)
output_folder_entry.grid(row=2, column=1, padx=10, pady=10, sticky="we")

output_folder_button = tk.Button(root, text="Browse", command=select_output_folder, state=tk.NORMAL)
output_folder_button.grid(row=2, column=2, padx=10, pady=10)

# Operation Mode
operation_mode_var = tk.StringVar(value="remove_ocr")
operation_mode_label = tk.Label(root, text="Operation Mode:")
operation_mode_label.grid(row=3, column=0, padx=10, pady=10, sticky="w")

operation_mode_radio_remove = tk.Radiobutton(
    root, text="Remove OCR", variable=operation_mode_var, value="remove_ocr", command=update_ui_based_on_mode
)
operation_mode_radio_convert = tk.Radiobutton(
    root, text="Convert to PNG", variable=operation_mode_var, value="convert_png", command=update_ui_based_on_mode
)
operation_mode_radio_remove.grid(row=3, column=1, padx=10, pady=5, sticky="w")
operation_mode_radio_convert.grid(row=3, column=2, padx=10, pady=5, sticky="w")

# DPI Control
dpi_label = tk.Label(root, text="DPI (Resolution):")
dpi_label.grid(row=4, column=0, padx=10, pady=10, sticky="w")

dpi_scale = tk.Scale(root, from_=72, to=300, orient=tk.HORIZONTAL, resolution=10, label="Dots Per Inch", length=200)
dpi_scale.set(200)
dpi_scale.grid(row=4, column=1, columnspan=2, padx=10, pady=10, sticky="we")

# JPEG Quality Control
jpeg_quality_label = tk.Label(root, text="JPEG Quality (for JPEG format):")
jpeg_quality_label.grid(row=5, column=0, padx=10, pady=10, sticky="w")

jpeg_quality_scale = tk.Scale(root, from_=1, to=100, orient=tk.HORIZONTAL, label="Quality (1-100)", length=200)
jpeg_quality_scale.set(85)
jpeg_quality_scale.grid(row=5, column=1, columnspan=2, padx=10, pady=10, sticky="we")

# Image Format Selection
image_format_label = tk.Label(root, text="Image Format (Remove OCR Mode):")
image_format_label.grid(row=6, column=0, padx=10, pady=10, sticky="w")

image_format_var = tk.StringVar(value="jpeg")
image_format_radio_png = tk.Radiobutton(
    root, text="PNG (lossless, larger size)", variable=image_format_var, value="png"
)
image_format_radio_jpeg = tk.Radiobutton(
    root, text="JPEG (lossy, smaller size)", variable=image_format_var, value="jpeg"
)
image_format_radio_png.grid(row=6, column=1, padx=10, pady=5, sticky="w")
image_format_radio_jpeg.grid(row=6, column=2, padx=10, pady=5, sticky="w")

# Process Button
process_button = tk.Button(root, text="Remove OCR and Process PDFs", command=process_pdfs)
process_button.grid(row=7, column=0, columnspan=3, pady=10)

# Progress Label
progress_label = tk.Label(root, text="")
progress_label.grid(row=8, column=0, columnspan=3, pady=5)

# Progress Bar
progressbar = ttk.Progressbar(root, orient=tk.HORIZONTAL, length=300, mode="determinate")
progressbar.grid(row=9, column=0, columnspan=3, pady=10)

root.columnconfigure(1, weight=1)

update_ui_based_on_mode()
toggle_output_folder_state()

root.mainloop()
