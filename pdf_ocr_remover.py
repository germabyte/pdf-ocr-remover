import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import subprocess
import threading  # Import the threading module
import fitz  # pymupdf

def remove_ocr_from_pdf_pymupdf(input_pdf_path, output_pdf_path, progress_label, dpi=200, image_format="jpeg", jpeg_quality=85):
    """
    Removes OCR text layer from a PDF by rasterizing it using pymupdf.
    Optimized for smaller file size while retaining excellent quality.

    Args:
        input_pdf_path (str): Path to the OCR'ed PDF file.
        output_pdf_path (str): Path to save the non-OCR'ed PDF file.
        progress_label (tk.Label): Label to update with processing status.
        dpi (int): DPI (dots per inch) for rasterization. Lower DPI reduces file size.
        image_format (str): Image format for rasterization ("png" or "jpeg"). "jpeg" for smaller size.
        jpeg_quality (int): JPEG quality (1-100, higher is better quality, larger size). Ignored if image_format is not "jpeg".

    Returns:
        bool: True if processing was successful, False otherwise.
    """
    try:
        pdf_document = fitz.open(input_pdf_path)
        new_pdf = fitz.open()  # Create a new PDF in memory

        for page_num in range(pdf_document.page_count):
            page = pdf_document.load_page(page_num)
            # Render page to pixmap (image) at specified DPI
            mat = fitz.Matrix(dpi/72, dpi/72)  # Create DPI scaling matrix
            pix = page.get_pixmap(matrix=mat)

            if image_format == "jpeg":
                try:
                    # Try to use quality argument - might fail on older pymupdf
                    img_data = pix.tobytes("jpeg", quality=jpeg_quality)
                except TypeError as e:
                    if "unexpected keyword argument 'quality'" in str(e):
                        print("Warning: 'quality' argument not supported in your PyMuPDF version. Using default JPEG quality.")
                        img_data = pix.tobytes("jpeg") # Use JPEG without quality argument
                    else:
                        raise # Re-raise other TypeErrors
                except Exception as e:
                    raise # Re-raise other exceptions during tobytes
            elif image_format == "png":
                img_data = pix.tobytes("png") # Convert pixmap to PNG image data (lossless, larger size)
            else:
                img_data = pix.tobytes("png") # Default to PNG if format is not recognized

            img_pdf_page = new_pdf.new_page(width=page.rect.width, height=page.rect.height) # New page with original dimensions
            img_pdf_page.insert_image(page.rect, stream=img_data) # Insert image onto the new page

        new_pdf.save(output_pdf_path, garbage=4, deflate=True, clean=True) # Added PDF optimization options for smaller size
        new_pdf.close()
        pdf_document.close()
        return True
    except Exception as e:
        error_message = f"PyMuPDF error: {e}"
        print(f"Error processing {input_pdf_path}: {error_message}")
        tk.messagebox.showerror("PyMuPDF Error", f"Error processing {os.path.basename(input_pdf_path)} with PyMuPDF.\n{error_message}\n\nIt might be due to an outdated PyMuPDF version.\nPlease try upgrading PyMuPDF (pip install --upgrade pymupdf) or using PNG format.", icon='error')
        return False


def remove_ocr_from_pdf_pdftocairo(input_pdf_path, output_pdf_path, progress_label, dpi=200, jpeg_quality=85):
    """
    Removes OCR text layer from a PDF by rasterizing it using pdftocairo.
    Optimized for smaller file size and good quality.

    Args:
        input_pdf_path (str): Path to the OCR'ed PDF file.
        output_pdf_path (str): Path to save the non-OCR'ed PDF file.
        progress_label (tk.Label): Label to update with processing status.
        dpi (int): DPI for rasterization (may not directly apply to PDF output, but can influence quality).
        jpeg_quality (int): JPEG quality (may not be directly applicable to PDF output, implementation dependent).
                              This is added for potential future enhancements or if pdftocairo uses it internally.

    Returns:
        bool: True if processing was successful, False otherwise.
    """
    try:
        # Construct the pdftocairo command
        command = [
            "pdftocairo",
            "-pdf",  # Output as PDF - this is crucial for minimal quality loss
            "-r", str(dpi), # Set DPI (dots per inch) - influences rasterization quality
            input_pdf_path,
            output_pdf_path
        ]

        # Execute the command
        process = subprocess.run(command, check=True, capture_output=True)

        return True
    except subprocess.CalledProcessError as e:
        error_message = f"pdftocairo command failed with exit code {e.returncode}:\n"
        error_message += f"Command: {' '.join(command)}\n"
        error_message += f"Stderr: {e.stderr.decode()}" if e.stderr else "No stderr output."
        print(f"Error processing {input_pdf_path}: {error_message}")
        tk.messagebox.showerror("pdftocairo Error", f"Error processing {os.path.basename(input_pdf_path)} with pdftocairo.\nSee console for details.", icon='error')
        return False
    except FileNotFoundError:
        tk.messagebox.showerror("Error", "pdftocairo not found. Please ensure it is installed and in your system's PATH.", icon='error')
        return False
    except Exception as e:
        generic_error_message = f"An unexpected error occurred during processing:\n{e}"
        print(f"Error processing {input_pdf_path}: {generic_error_message}")
        tk.messagebox.showerror("Error", f"Error processing {os.path.basename(input_pdf_path)}.\nSee console for details.", icon='error')
        return False

def select_source_folder():
    """Opens a folder selection dialog and updates the source folder entry."""
    folder_selected = filedialog.askdirectory()
    if folder_selected:
        source_folder_entry.delete(0, tk.END)
        source_folder_entry.insert(0, folder_selected)

def select_output_folder():
    """Opens a folder selection dialog and updates the output folder entry if a folder is selected."""
    folder_selected = filedialog.askdirectory()
    if folder_selected:
        output_folder_entry.delete(0, tk.END)
        output_folder_entry.insert(0, folder_selected)

def toggle_output_folder_state():
    """Enables/disables output folder widgets based on overwrite checkbox."""
    if overwrite_var.get():
        output_folder_entry.config(state=tk.DISABLED)
        output_folder_button.config(state=tk.DISABLED)
    else:
        output_folder_entry.config(state=tk.NORMAL)
        output_folder_button.config(state=tk.NORMAL)

def process_pdfs_threaded():
    """
    Processes PDF files in the selected source folder to remove OCR in a separate thread to prevent UI freezing.
    """
    source_folder = source_folder_entry.get()
    if not source_folder:
        tk.messagebox.showerror("Error", "Please select a source folder.", icon='error')
        enable_ui_elements() # Re-enable UI in case of early exit
        return

    overwrite_files = overwrite_var.get()
    output_folder = source_folder if overwrite_files else output_folder_entry.get()

    if not overwrite_files and not output_folder:
        tk.messagebox.showerror("Error", "Please select an output folder or choose to overwrite files.", icon='error')
        enable_ui_elements() # Re-enable UI in case of early exit
        return

    if not overwrite_files and not os.path.exists(output_folder):
        try:
            os.makedirs(output_folder, exist_ok=True)
        except OSError as e:
            tk.messagebox.showerror("Error", f"Could not create output folder: {e}", icon='error')
            enable_ui_elements() # Re-enable UI in case of early exit
            return

    pdf_files_to_process = 0
    for filename in os.listdir(source_folder):
        if filename.lower().endswith(".pdf"):
            pdf_files_to_process += 1

    if pdf_files_to_process == 0:
        tk.messagebox.showinfo("Info", "No PDF files found in the selected source folder.")
        enable_ui_elements() # Re-enable UI in case of early exit
        return

    progressbar['maximum'] = pdf_files_to_process
    progressbar['value'] = 0
    pdf_files_processed = 0
    pdf_files_failed = 0

    use_pymupdf = True # <--- SET THIS TO True TO USE PYMUPDF, False FOR PDFTOCAIRO
                       #      PyMuPDF is pure Python and easier to distribute.
                       #      pdftocairo generally provides excellent quality but requires external dependencies (poppler/cairo).

    dpi_value = dpi_scale.get() # Get DPI from scale widget
    jpeg_quality_value = jpeg_quality_scale.get() # Get JPEG quality from scale widget
    image_format_value = image_format_var.get() # Get image format from radio button

    for i, filename in enumerate(os.listdir(source_folder)):
        if filename.lower().endswith(".pdf"):
            input_pdf_path = os.path.join(source_folder, filename)
            output_filename = filename

            if overwrite_files:
                output_pdf_path = input_pdf_path
            else:
                output_pdf_path = os.path.join(output_folder, output_filename)

            update_progress_label(f"Processing: {filename} ({i+1}/{pdf_files_to_process})") # Use update function
            if use_pymupdf:
                if remove_ocr_from_pdf_pymupdf(input_pdf_path, output_pdf_path, progress_label, dpi=dpi_value, image_format=image_format_value, jpeg_quality=jpeg_quality_value):
                    pdf_files_processed += 1
                else:
                    pdf_files_failed += 1
            else: # Use pdftocairo
                if remove_ocr_from_pdf_pdftocairo(input_pdf_path, output_pdf_path, progress_label, dpi=dpi_value, jpeg_quality=jpeg_quality_value):
                    pdf_files_processed += 1
                else:
                    pdf_files_failed += 1

            update_progressbar() # Use update function

    update_progress_label("Processing Complete") # Use update function
    enable_ui_elements()

    message = f"Processed {pdf_files_processed} PDFs successfully."
    if pdf_files_failed > 0:
        message += f"\nFailed to process {pdf_files_failed} PDFs. Check console for errors."

    tk.messagebox.showinfo("Process Complete", message)

def process_pdfs():
    """Starts the PDF processing in a separate thread."""
    disable_ui_elements()
    thread = threading.Thread(target=process_pdfs_threaded)
    thread.start()

def update_progress_label(text):
    """Updates the progress label text in a thread-safe way."""
    progress_label.config(text=text)

def update_progressbar():
    """Updates the progressbar value in a thread-safe way."""
    progressbar.step(1)

def disable_ui_elements():
    """Disables UI elements during processing."""
    source_folder_button.config(state=tk.DISABLED)
    overwrite_check.config(state=tk.DISABLED)
    output_folder_button.config(state=tk.DISABLED)
    output_folder_entry.config(state=tk.DISABLED)
    process_button.config(state=tk.DISABLED)
    dpi_scale.config(state=tk.DISABLED) # Disable DPI scale
    jpeg_quality_scale.config(state=tk.DISABLED) # Disable JPEG quality scale
    image_format_radio_png.config(state=tk.DISABLED) # Disable image format radio buttons
    image_format_radio_jpeg.config(state=tk.DISABLED)
    root.update_idletasks()

def enable_ui_elements():
    """Enables UI elements after processing."""
    source_folder_button.config(state=tk.NORMAL)
    overwrite_check.config(state=tk.NORMAL)
    toggle_output_folder_state() # Restore output folder button/entry state based on overwrite_var
    process_button.config(state=tk.NORMAL)
    dpi_scale.config(state=tk.NORMAL) # Enable DPI scale
    jpeg_quality_scale.config(state=tk.NORMAL) # Enable JPEG quality scale
    image_format_radio_png.config(state=tk.NORMAL) # Enable image format radio buttons
    image_format_radio_jpeg.config(state=tk.NORMAL)


# --- GUI Setup ---
root = tk.Tk()
root.title("PDF OCR Remover")

# Source Folder Selection
source_folder_label = tk.Label(root, text="Source Folder:")
source_folder_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")

source_folder_entry = tk.Entry(root, width=50)
source_folder_entry.grid(row=0, column=1, padx=10, pady=10, sticky="we")

source_folder_button = tk.Button(root, text="Browse", command=select_source_folder)
source_folder_button.grid(row=0, column=2, padx=10, pady=10)

# Overwrite Option
overwrite_var = tk.BooleanVar()
overwrite_check = tk.Checkbutton(root, text="Overwrite files in source folder", variable=overwrite_var)
overwrite_check.grid(row=1, column=0, columnspan=3, padx=10, pady=5, sticky="w")
overwrite_check.config(command=toggle_output_folder_state)

# Output Folder Selection (Only shown if not overwriting)
output_folder_label = tk.Label(root, text="Output Folder (if not overwriting):")
output_folder_label.grid(row=2, column=0, padx=10, pady=10, sticky="w")

output_folder_entry = tk.Entry(root, width=50, state=tk.NORMAL)
output_folder_entry.grid(row=2, column=1, padx=10, pady=10, sticky="we")

output_folder_button = tk.Button(root, text="Browse", command=select_output_folder, state=tk.NORMAL)
output_folder_button.grid(row=2, column=2, padx=10, pady=10)


# DPI Control
dpi_label = tk.Label(root, text="DPI (Resolution):")
dpi_label.grid(row=3, column=0, padx=10, pady=10, sticky="w")
dpi_scale = tk.Scale(root, from_=72, to=300, orient=tk.HORIZONTAL, resolution=10, label="Dots Per Inch", length=200)
dpi_scale.set(200) # Default DPI - reduced from 300 for smaller size
dpi_scale.grid(row=3, column=1, columnspan=2, padx=10, pady=10, sticky="we")

# JPEG Quality Control (Only relevant for PyMuPDF with JPEG format)
jpeg_quality_label = tk.Label(root, text="JPEG Quality (for JPEG format):")
jpeg_quality_label.grid(row=4, column=0, padx=10, pady=10, sticky="w")
jpeg_quality_scale = tk.Scale(root, from_=1, to=100, orient=tk.HORIZONTAL, label="Quality (1-100)", length=200)
jpeg_quality_scale.set(85) # Default JPEG quality - good balance
jpeg_quality_scale.grid(row=4, column=1, columnspan=2, padx=10, pady=10, sticky="we")


# Image Format Selection
image_format_label = tk.Label(root, text="Image Format:")
image_format_label.grid(row=5, column=0, padx=10, pady=10, sticky="w")
image_format_var = tk.StringVar(value="jpeg") # Default to JPEG for smaller size
image_format_radio_png = tk.Radiobutton(root, text="PNG (lossless, larger size)", variable=image_format_var, value="png")
image_format_radio_jpeg = tk.Radiobutton(root, text="JPEG (lossy, smaller size)", variable=image_format_var, value="jpeg")
image_format_radio_png.grid(row=5, column=1, padx=10, pady=5, sticky="w")
image_format_radio_jpeg.grid(row=5, column=2, padx=10, pady=5, sticky="w")


# Process Button
process_button = tk.Button(root, text="Remove OCR and Process PDFs", command=process_pdfs)
process_button.grid(row=6, column=0, columnspan=3, pady=10)

# Progress Label
progress_label = tk.Label(root, text="")
progress_label.grid(row=7, column=0, columnspan=3, pady=5)

# Progress Bar
progressbar = ttk.Progressbar(root, orient=tk.HORIZONTAL, length=300, mode='determinate')
progressbar.grid(row=8, column=0, columnspan=3, pady=10)

root.columnconfigure(1, weight=1)

toggle_output_folder_state()

root.mainloop()