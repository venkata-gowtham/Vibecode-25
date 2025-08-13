import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import xml.etree.ElementTree as ET
import xml.dom.minidom
import os

def transform_idoc(input_xml_path, output_xml_path, mappings):
    try:
        tree = ET.parse(input_xml_path)
        root = tree.getroot()
        new_root = ET.Element(root.tag)
        idoc_in = root.find('.//IDOC')
        idoc_out = ET.SubElement(new_root, 'IDOC', idoc_in.attrib if idoc_in is not None else {})

        for seg_name, field_map in mappings.items():
            segments_in = root.findall(f'.//{seg_name}')
            for seg_in in segments_in:
                seg_out = ET.SubElement(idoc_out, seg_name, seg_in.attrib if seg_in is not None else {})
                for out_field, in_field, hardcoded_value in field_map:
                    if hardcoded_value:
                        value = hardcoded_value
                    elif in_field and seg_in is not None and in_field in [c.tag for c in seg_in]:
                        value = seg_in.findtext(in_field, '')
                    else:
                        value = ''
                    ET.SubElement(seg_out, out_field).text = value

        rough_string = ET.tostring(new_root, encoding='utf-8')
        reparsed = xml.dom.minidom.parseString(rough_string)
        pretty_xml = reparsed.toprettyxml(indent="    ")

        with open(output_xml_path, 'w', encoding='utf-8') as f:
            f.write(pretty_xml)
        return True
    except Exception as e:
        messagebox.showerror("Error", f"Failed to generate XML: {e}")
        return False

class MappingApp:
    def __init__(self, master):
        self.master = master
        master.title("IDoc to XML Advanced Mapper")

        self.input_path = ""
        self.output_path = ""
        self.segments = {}
        self.mapping_widgets = {}
        self.segment_frames = {}

        self.select_input_btn = tk.Button(master, text="Select IDoc XML", command=self.select_input)
        self.select_input_btn.pack(pady=5)

        # --- Scrollable mapping frame ---
        self.canvas = tk.Canvas(master, height=400)
        self.scrollbar = tk.Scrollbar(master, orient="vertical", command=self.canvas.yview)
        self.mapping_frame = tk.Frame(self.canvas)

        self.mapping_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window((0, 0), window=self.mapping_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=5)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Mouse wheel binding for Windows
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        self.add_segment_btn = tk.Button(master, text="Add Output Field", command=self.add_output_field, state=tk.DISABLED)
        self.add_segment_btn.pack(pady=5)

        self.save_btn = tk.Button(master, text="Save Output XML", command=self.save_output, state=tk.DISABLED)
        self.save_btn.pack(pady=5)

        self.preview_btn = tk.Button(master, text="Preview Output XML", command=self.preview_output, state=tk.DISABLED)
        self.preview_btn.pack(pady=5)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def select_input(self):
        self.input_path = filedialog.askopenfilename(title="Select IDoc XML File", filetypes=[("XML Files", "*.xml")])
        if self.input_path:
            # Load the XML file and populate the mapping fields
            try:
                tree = ET.parse(self.input_path)
                root = tree.getroot()

                # Clear existing mappings
                self.segments.clear()
                for widget in self.mapping_frame.winfo_children():
                    widget.destroy()

                # Extract segment names and create mapping fields
                for segment in root.findall('.//'):
                    seg_name = segment.tag
                    if seg_name not in self.segments:
                        self.segments[seg_name] = []
                        self.add_mapping_fields(seg_name, segment)

                self.add_segment_btn.config(state=tk.NORMAL)
                self.save_btn.config(state=tk.NORMAL)
                self.preview_btn.config(state=tk.NORMAL)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load XML: {e}")

    def add_mapping_fields(self, seg_name, segment):
        frame = tk.Frame(self.mapping_frame)
        frame.pack(fill=tk.X, pady=2)

        label = tk.Label(frame, text=seg_name, width=15, anchor="w")
        label.pack(side=tk.LEFT, padx=5)

        # Hardcoded value checkbox
        var = tk.BooleanVar()
        chk = tk.Checkbutton(frame, variable=var)
        chk.pack(side=tk.LEFT, padx=5)

        # Output field
        out_entry = tk.Entry(frame, width=20)
        out_entry.pack(side=tk.LEFT, padx=5)

        # Input field dropdown
        in_field_var = tk.StringVar()
        in_field_dropdown = tk.OptionMenu(frame, in_field_var, *[c.tag for c in segment])
        in_field_dropdown.pack(side=tk.LEFT, padx=5)

        self.segments[seg_name].append((var, out_entry, in_field_var))

        # Add remove button
        remove_btn = tk.Button(frame, text="Remove", command=lambda: self.remove_mapping(seg_name, frame))
        remove_btn.pack(side=tk.LEFT, padx=5)

    def remove_mapping(self, seg_name, frame):
        frame.pack_forget()
        self.segments[seg_name] = [m for m in self.segments[seg_name] if m[1].get() != frame.winfo_children()[1].get()]

    def add_output_field(self):
        # For simplicity, just add a new field to the first segment
        if self.segments:
            first_segment = next(iter(self.segments))
            self.add_mapping_fields(first_segment, ET.Element(first_segment))

    def save_output(self):
        output_path = filedialog.asksaveasfilename(defaultextension=".xml", filetypes=[("XML Files", "*.xml")])
        if output_path:
            mappings = {seg_name: [(var.get(), out_entry.get(), var.get()) for var, out_entry, in_field_var in fields] for seg_name, fields in self.segments.items()}
            transform_idoc(self.input_path, output_path, mappings)

    def preview_output(self):
        try:
            mappings = {seg_name: [(var.get(), out_entry.get(), var.get()) for var, out_entry, in_field_var in fields] for seg_name, fields in self.segments.items()}
            temp_output = "temp_output.xml"
            if transform_idoc(self.input_path, temp_output, mappings):
                with open(temp_output, 'r', encoding='utf-8') as f:
                    xml_content = f.read()
                os.remove(temp_output)

                # Show preview in a new window
                preview_window = tk.Toplevel(self.master)
                preview_window.title("Preview Output XML")

                text = tk.Text(preview_window, wrap=tk.WORD)
                text.pack(fill=tk.BOTH, expand=True)

                # Add a scrollbar to the text widget
                scrollbar = tk.Scrollbar(preview_window, orient="vertical", command=text.yview)
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                text.configure(yscrollcommand=scrollbar.set)

                text.insert(tk.END, xml_content)
            else:
                messagebox.showerror("Error", "Failed to generate preview XML.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to preview XML: {e}")