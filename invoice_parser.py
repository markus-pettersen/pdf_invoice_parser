import utils.ecommerce_utils as ecom
import utils.retail_utils as retail
import utils.invoice_classifier as invoice_classifier
import os
import csv
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

# Global variables
df_memory = None
invoice_type = None
file_name = None

# Create folder structure
if not os.path.exists("outputs/"):
    os.mkdir("outputs/")

# Create logs
if not os.path.isfile("outputs/evri_log.csv"):
    with open("outputs/evri_log.csv", mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([
                "week",
                "actual_cost",
                "fixed_rate",
                "difference",
                "total_despatches"])


# Interface functions
def load_invoice():
    global invoice_type
    file_path = filedialog.askopenfilename()

    if not file_path:
        return

    invoice_type = invoice_classifier.invoice_detect(file_path)

    if invoice_type == "evri":
        select_evri_invoice(file_path)

    elif invoice_type == "fedex":
        select_fedex_invoice(file_path)

    else:
        file_name = os.path.basename(file_path)
        messagebox.showerror(
            "Error", f"{file_name} is an unrecogized invoice!"
        )
        root.destroy()


def select_evri_invoice(file_path):
    global df_memory

    file_name = os.path.basename(file_path)
    df_memory = ecom.extract(file_path)

    if len(df_memory) == 0:
        messagebox.showerror(
            "Error", f"{file_name} is unreadable as an Evri invoice!"
        )
        root.destroy()

    else:
        df_memory = ecom.transform(df_memory)
        status_label["text"] = f"{file_name} parsed as an Evri invoice!"
        invoice_loaded_successfully()


def select_fedex_invoice(file_path):
    global df_memory
    global file_name

    file_name = os.path.basename(file_path)
    df_memory = retail.extract(file_path)

    if len(df_memory) == 0:
        messagebox.showerror(
            "Error", f"{file_name} is unreadable as a FedEx invoice!"
        )
        root.destroy()

    else:
        df_memory = retail.transform(df_memory)
        status_label["text"] = f"{file_name} parsed as a FedEx invoice!"
        invoice_loaded_successfully()


def invoice_loaded_successfully():
    export_invoice_button.pack(pady=5)
    export_summary_button.pack(pady=5)
    summarize_invoice_button.pack(pady=5)
    summary_output.pack(pady=5)
    summary_output.delete("1.0", tk.END)


def export_invoice():
    if df_memory is None:
        return

    if invoice_type == "evri":
        ecom.load(df_memory)
        messagebox.showinfo("Saved", "CSV exported successfully!")

    elif invoice_type == "fedex":
        retail.load(df_memory, file_name)
        messagebox.showinfo("Saved", "CSV exported successfully!")


def log_summary():
    # abstract into util files
    if df_memory is None:
        return
    if invoice_type == "evri":
        already_saved = ecom.log_summary(df_memory, "outputs/evri_log.csv")
        if already_saved:
            messagebox.showinfo("Logged", "Invoice already logged!")
        else:
            messagebox.showinfo("Logged", "Invoice logged successfully!")


def summarize_invoice_button():
    if df_memory is None:
        return
    if invoice_type == "evri":
        summary_string = ecom.generate_summary(df_memory)

    elif invoice_type == "fedex":
        summary_string = retail.generate_summary(df_memory)
    else:
        return

    summary_output.delete("1.0", tk.END)
    summary_output.insert(tk.END, summary_string)


# GUI structure
root = tk.Tk()
root.title("PDF Invoice Parser")
root.geometry("450x450")

label = tk.Label(root, text="Select Invoice")
label.pack(pady=10)

load_button = tk.Button(
                        root,
                        text="Load from file",
                        width=25,
                        command=load_invoice
                    )
load_button.pack(pady=5)

export_invoice_button = tk.Button(
                            root,
                            text="Save Invoice as CSV",
                            width=25,
                            command=export_invoice
                    )

export_summary_button = tk.Button(
                            root,
                            text="Log Summary",
                            width=25,
                            command=log_summary
                    )

summarize_invoice_button = tk.Button(
                            root,
                            text="View Summary",
                            width=25,
                            command=summarize_invoice_button
                    )

status_label = tk.Label(root, text="")
status_label.pack(pady=5)

summary_output = scrolledtext.ScrolledText(root, width=50, height=10)

root.mainloop()
