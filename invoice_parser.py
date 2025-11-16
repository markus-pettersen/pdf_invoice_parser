import utils.ecommerce_utils as ecom
import os
import csv
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

# Global variables
df_memory = None
invoice_type = None

# Create logs
if not os.path.isfile("outputs/evri_log.csv"):
    with open("outputs/evri_log.csv", mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["week", "actual_cost", "fixed_rate", "difference", "total_despatches"])

# Interface functions
def select_evri_invoice():
    global df_memory
    global invoice_type
    try:
        file_path = filedialog.askopenfilename()
        if not file_path:
            return

        invoice_type = "evri"
        df_memory = ecom.extract(file_path)
        df_memory = ecom.transform(df_memory)
        file_name = os.path.basename(file_path)
        status_label["text"] = f"{file_name} parsed successfully!"

        export_invoice_button.pack(pady=5)
        export_summary_button.pack(pady=5)
        summarize_invoice_button.pack(pady=5)
        summary_output.pack(pady=5)
        summary_output.delete("1.0", tk.END)

    except Exception as e:
        file_name = os.path.basename(file_path)
        messagebox.showerror("Error", f"{file_name} is unreadable as an Evri invoice")
        root.destroy()


def select_fedex_invoice():
    pass


def export_invoice():
    if df_memory is None:
        return
    elif invoice_type == "evri":
        ecom.load(df_memory)
        messagebox.showinfo("Saved", "CSV exported successfully!")


def log_summary():
    if df_memory is None:
        return
    elif invoice_type == "evri":
        week, actual, fixed, total_orders = ecom.calculate_costs(df_memory)
        difference = round(actual - fixed, 2)
        summary_row = [str(week), str(actual), str(fixed), str(difference), str(total_orders)]

        # check if row already exists
        existing_rows = set()

        with open("outputs/evri_log.csv", mode="r", newline="") as file:
            reader = csv.reader(file)
            for row in reader:
                existing_rows.add(tuple(row))


        if tuple(summary_row) in existing_rows:
            messagebox.showinfo("Logged", "Invoice already logged!")
            return

        else:
            with open("outputs/evri_log.csv", mode="a", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(summary_row)
            messagebox.showinfo("Logged", "Invoice logged successfully!")


def summarize_invoice_button():
    if df_memory is None:
        return
    elif invoice_type == "evri":
        week, actual, fixed, total_orders = ecom.calculate_costs(df_memory)
        str_description = "UNDER"
        if actual > fixed:
            str_description = "OVER"

        summary_string = f"""Evri E-commerce Despatch
Week: {str(week)}

The actual cost is {str_description} the fixed rate.

Fixed rate: £{fixed} per despatch
Actual cost: £{actual} per despatch
Difference: £{actual - fixed:+.2f} ({100*(actual/fixed - 1):+.2f}%)
Total despatches: {total_orders:,}
"""

    summary_output.delete("1.0", tk.END)
    summary_output.insert(tk.END, summary_string)

# GUI structure

root = tk.Tk()
root.title("PDF Invoice Parser")
root.geometry("450x450")

label = tk.Label(root, text="Load Invoice")
label.pack(pady=10)

load_evri_button = tk.Button(root, text="Load Evri Invoice", width=25, command=select_evri_invoice)
load_evri_button.pack(pady=5)

load_fedex_button = tk.Button(root, text="Load FedEx Invoice", width=25, command=select_fedex_invoice)
load_fedex_button.pack(pady=5)

export_invoice_button = tk.Button(root, text="Save Invoice as CSV", width=25, command=export_invoice)
export_summary_button = tk.Button(root, text="Log Summary", width=25, command=log_summary)
summarize_invoice_button = tk.Button(root, text="View Summary", width=25, command=summarize_invoice_button)

status_label = tk.Label(root, text="")
status_label.pack(pady=5)

summary_output = scrolledtext.ScrolledText(root, width=50, height=10)

root.mainloop()
