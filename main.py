import csv
import math
import tkinter as tk
import tkinter.font as tkfont

from pathlib import Path
from typing import Callable
from tkinter import filedialog, messagebox, ttk


# Define the absolute order of the txt (23 fields)
TARGET_COLUMNS: list[str] = [
    "TipoTercero", "TipoOperacion", "RFCProveedor", "NIF", "NombreExtranjero", "Pais",
    "JurisdiccionFiscal", "ValorTotal", "IVANoAcreditable", "ValorIVA11", "IVAPagado11",
    "ValorFronterNorte", "IVAFronteraNorte", "ValorFronteraSur", "IVAFronteraSur", 
    "ValorImportacion", "IVAImportacion", "ValorImportacionExentos", "ValorExentosIVA",
    "ValorIVA0", "ValorNoIVA", "IVARetenidoContribuyente", "IVAPagadoGastosGeneral"
]

def round_numeric(value: float) -> str:
    #if fecha == "":
    #    raise ValueError(f"Fecha was not provided: case({value}, {fecha})")

    integer_part = math.floor(value)
    decimal_part = value - integer_part

    #year = int(fecha[:4])
    #if year >= 2024:
    if 0.01 <= decimal_part <= 0.50:
        return str(integer_part)
    elif 0.51 <= decimal_part <= 0.99:
        return str(integer_part + 1)
    else:
        return str(integer_part)


# Define the operations done for IVA calculation
DERIVED: dict[str, Callable[[dict[str, str]], str]] = {
    #"IVA": lambda r: r.get("TOTAL", 0) * 0.16,
    "TipoTercero": lambda r: "04", # For now, all are national
    "TipoOperacion": lambda r: "03", # For now, all are Serv Prof.
    "RFCProveedor": lambda r: r.get("RFCProveedor", "").upper(),
    "ValorTotal": lambda r: round_numeric(float(r.get("ValorTotal", "0"))),
    "IVANoAcreditable": lambda r: round_numeric( int(r.get("ValorTotal", "0")) * 0.16 ),
}

# Dictionary to map from metadata columns to Target
map_metadata_to_target: dict[str, str] = {
    "RfcEmisor": "RFCProveedor",
    "Uuid": "UUID",
    "Monto": "ValorTotal",
    "FechaCertificacionSat": "Fecha",
}

# Verify TARGET_COLUMNS contain DERIVED
unknown_derived = [c for c in DERIVED.keys() if c not in TARGET_COLUMNS]
if unknown_derived:
    raise ValueError(f"Derived contains columns not in TARGET_COLUMNS: {unknown_derived}")


def read_metadata(input_file: Path) -> tuple[list[str], dict[str, int], list[list[str]]]:

    data = []
    with open(str(input_file), "r") as f:

        # Get header
        try:
            header = f.readline().strip()
        except:
            raise ValueError("Input file is empty")

        # Split by separator ~
        input_header = header.split("~")
        n_columns = len(input_header)

        # Build header -> index mapping
        col2idx = {name: i for i, name in enumerate(input_header)}

        # Read entries
        for line in f:
            # Split
            entries = line.strip().split("~")

            data.append(entries)

        # Verify matrix integrity
        for i, row in enumerate(data):
            if len(row) != n_columns:
                raise ValueError(f"Data is irregular. Row: {i+1} has {len(row)} entries, it must have {n_columns}.")
        f.close()

    return input_header, col2idx, data

# Processing logic from raw metadata into acceptable txt file.
def process_data(input_file: Path, output_file: Path) -> None:

    # Read input file
    header, col2idx, data = read_metadata(input_file)

    # Make csv file path from txt one.
    output_file_txt = output_file
    output_file_csv = output_file.with_suffix(".csv")

    # Write files
    with (
        open(output_file_txt, "w", encoding="utf-8", newline="") as f_txt,
        open(output_file_csv, "w", encoding="utf-8", newline="") as f_csv
    ):
        # Make writer objects
        txt_writer = csv.writer(f_txt, delimiter="|", lineterminator="\n")
        csv_writer = csv.writer(f_csv, delimiter=",", lineterminator="\n")

        # --- Write target header to csv ---
        csv_writer.writerow(TARGET_COLUMNS)

        # Write each row
        for row_num, row in enumerate(data):

            # Build a dict to access fields
            row_dict = {
                map_metadata_to_target.get(name, name):
                (row[idx].strip() if idx < len(row) else "") for name, idx in col2idx.items()
            }

            # Preprocess fields
            out_row: list[str] = []
            for col in TARGET_COLUMNS:
                if col in DERIVED:
                    val = DERIVED[col](row_dict)
                    if col in row_dict.keys():
                        row_dict[col] = val
                else:
                    # Blank cell for missing columns
                    val = row_dict.get(col, "")
                out_row.append(val)

            # Write to both files
            txt_writer.writerow(out_row)
            csv_writer.writerow(out_row)

    return 0


class ConverterApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        # Start Application
        self.title("SAT DIOT")
        self._set_global_font()
        self._set_initial_geometry(target_w=854, target_h=480)

        # State variables
        self.input_path_var = tk.StringVar()
        self.output_dir_var = tk.StringVar()
        self.output_name_var = tk.StringVar(value="output.txt")
        self.status_var = tk.StringVar(value="Select an input file and an output location.")

        # Make Layout
        self._build_ui()

    def _set_global_font(self) -> None:
        default_font = tkfont.nametofont("TkDefaultFont")
        default_font.configure(family="Calibri", size=12)

        tkfont.nametofont("TkTextFont").configure(family="Calibri", size=12)
        tkfont.nametofont("TkFixedFont").configure(family="Consolas", size=11)
        tkfont.nametofont("TkMenuFont").configure(family="Calibri", size=12)

    def _set_initial_geometry(self, target_w: int, target_h: int) -> None:
        """
        For wide compatibility, set a 480p window.
        Clamp it to the screen if needed.
        """
        #
        self.update_idletasks()

        # Get monitor dimensions
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()

        # Leave a margin
        margin_w = 80
        margin_h = 120

        # Compute dimensions
        w = min(target_w, max(640, screen_w - margin_w)) # Clamp
        h = min(target_h, max(420, screen_h - margin_h)) # Clamp

        x = max(0, (screen_w - w) // 2)
        y = max(0, (screen_h - h) // 2)

        # Set geometry
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.minsize(640, 420)

    def _build_ui(self) -> None:
        # Root grid config (make column 1 expand)
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=0)
        self.columnconfigure(2, weight=1)

        pad = {"padx": 10, "pady": 8}

        # Row 0: Header
        ttk.Label(self, text="File Selection", font=("Calibri", 12, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="ew", **pad
        )

        # Row 1: Input file
        ttk.Label(self, text="Input .txt file:").grid(row=1, column=0, sticky="w", **pad)

        ttk.Button(self, text="Browse...", command=self.on_browse_input).grid(
            row=1, column=1, sticky="w", **pad
        )

        input_entry = ttk.Entry(self, textvariable=self.input_path_var)
        input_entry.grid(row=1, column=2, sticky="we", **pad)


        # Row 2: Output folder
        ttk.Label(self, text="Output folder:").grid(row=2, column=0, sticky="w", **pad)

        ttk.Button(self, text="Browse...", command=self.on_browse_output_dir).grid(
            row=2, column=1, sticky="w", **pad
        )

        outdir_entry = ttk.Entry(self, textvariable=self.output_dir_var)
        outdir_entry.grid(row=2, column=2, sticky="we", **pad)


        # Row 3: Output filename
        ttk.Label(self, text="Output filename:").grid(row=3, column=0, sticky="w", **pad)

        ttk.Button(self, text="Use input name", command=self.on_use_input_name).grid(
            row=3, column=1, sticky="w", **pad
        )

        outname_entry = ttk.Entry(self, textvariable=self.output_name_var)
        outname_entry.grid(row=3, column=2, sticky="we", **pad)


        # Row 4: Actions
        actions = ttk.Frame(self)
        actions.grid(row=4, column=0, columnspan=3, sticky="ew", **pad)
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=0)

        self.convert_btn = ttk.Button(actions, text="Convert", command=self.on_convert)
        self.convert_btn.grid(row=0, column=0, sticky="e")

        # Row 5: Status + filler
        status_frame = ttk.Frame(self)
        status_frame.grid(row=5, column=0, columnspan=3, sticky="nsew", **pad)
        self.rowconfigure(5, weight=1)

        ttk.Label(status_frame, text="Status:", anchor="w", font=("Calibri", 12, "bold")).pack(anchor="w")
        self.status_label = ttk.Label(
            status_frame,
            textvariable=self.status_var,
            anchor="nw",
            justify="left",
            wraplength=900,
        )
        self.status_label.pack(fill="both", expand=True)

        # Wrap as window resizes
        self.bind("<Configure>", self._on_resize_wrap)

    def _on_resize_wrap(self, event: tk.Event) -> None:
        # Make status text wrap with window width
        try:
            w = max(400, self.winfo.width() - 60)
            self.status_label.configure(wraplength=w)
        except Exception:
            pass

    def on_browse_input(self) -> None:
        # Get path from user
        path = filedialog.askopenfilename(
            title="select input .txt file",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        # Verify integrity
        if not path:
            return

        # Set variable
        self.input_path_var.set(path)

        # Set defaults if output folder is empty
        in_path = Path(path)
        if not self.output_dir_var.get():
            # Set output dir as the parent of input.
            self.output_dir_var.set(str(in_path.parent))

        # Set output filename default
        self.output_name_var.set(f"output_converted.txt")
        self.status_var.set("Input selected. Choose output folder/name, then click Convert.")

    def on_browse_output_dir(self) -> None:
        # Get path from user
        path = filedialog.askdirectory(title="Select output folder")
        if not path:
            return
        # Set variables
        self.output_dir_var.set(path)
        self.status_var.set("Output folder selected. Choose output name, then click Convert")

    def on_use_input_name(self) -> None:

        in_str = self.input_path_var.get().strip()
        if not in_str:
            messagebox.showwarning("Missing input", "Select an input file first.")
            return
        # Make it Path
        in_path = Path(in_str)
        self.output_name_var.set(f"{in_path.stem}_converted.txt")

    def _validate_paths(self) -> tuple[Path, Path]:
        # Get variables
        in_str = self.input_path_var.get().strip()
        out_dir_str = self.output_dir_var.get().strip()
        out_name_str = self.output_name_var.get().strip()

        # Input file verification
        ## Verify user provided the input file
        if not in_str:
            raise ValueError("Please select an input .txt file.")
        input_file = Path(in_str)

        ## Verify existence of input file
        if not input_file.exists() or not input_file.is_file():
            raise ValueError("The selected input file does not exist (or is not a file).")

        # Output dir verification
        ## Verify user provided the output folder
        if not out_dir_str:
            raise ValueError("Please select an output folder.")
        output_dir = Path(out_dir_str)

        ## Ensure output folder is not file.
        if output_dir.name and output_dir.suffix.lower() == ".txt":
            # In case someone pasted a full file path into "folder"
            raise ValueError("Output folder looks like a file. Please choose a folder, not a file.")

        ## Verify existence of parent (output_directory)
        if not output_dir.exists() or not output_dir.is_dir():
            raise ValueError("The selected output folder does not exist (or is not a folder).")

        # Output file verification
        ## Verify user provided the output file
        if not out_name_str:
            raise ValueError("Please enter an output filename (e.g., output.txt).")

        ## Add .txt to filename if it was not provided
        output_name = out_name_str
        if not output_name.lower().endswith(".txt"):
            output_name += ".txt"

        # Build output file
        output_file = output_dir / output_name
        if not output_file.parent.exists():
            raise ValueError("Parent directory of the output file does not exists.")

        return input_file, output_file

    def on_convert(self) -> None:
        """
        Button "Convert" logic.
        """

        # Get input and output files
        try:
            input_file, output_file = self._validate_paths()
        except ValueError as e:
            messagebox.showerror("Invalid input", str(e))
            self.status_var.set(f"Error: {e}")
            return

        # Disable button during processing
        self.convert_btn.configure(state="disabled")
        self.status_var.set("Processing...")

        # Execute the converter
        try:
            exit_code = process_data(input_file=input_file, output_file=output_file)
        except Exception as e:
            messagebox.showerror("Conversion failed", f"An error ocurred:\n\n{e}")
            self.status_var.set(f"Failed: {e}")
        else:
            messagebox.showinfo("Done", f"File created:\n\n{output_file}")
            self.status_var.set(f"Done. Output written to: {output_file}")
        finally:
            self.convert_btn.configure(state="normal")


def main():
    # Build App
    app = ConverterApp()
    app.mainloop()


if __name__ == "__main__":
    main()
