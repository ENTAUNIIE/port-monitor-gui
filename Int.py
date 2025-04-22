import tkinter as tk
from tkinter import ttk, messagebox
from netmiko import ConnectHandler
import threading
import time
import csv
from tkinter import filedialog
import winsound

# Liste des équipements Cisco à surveiller
import json
import os

def load_devices():
    if os.path.exists("devices.json"):
        with open("devices.json", "r") as f:
            return json.load(f)
    return []

def save_devices():
    with open("devices.json", "w") as f:
        json.dump(devices, f, indent=4)

devices = load_devices()

# Fonction pour récupérer l'état des interfaces

def fetch_interface_status(device):
    def normalize(interface_name):
        return interface_name.replace('FastEthernet', 'Fa').replace('GigabitEthernet', 'Gi')

    try:
        valid_keys = ['device_type', 'ip', 'username', 'password', 'secret', 'port']
        netmiko_device = {k: v for k, v in device.items() if k in valid_keys}
        connection = ConnectHandler(**netmiko_device)

        int_brief = connection.send_command('show ip interface brief', use_textfsm=True)
        vlan_status = connection.send_command('show interfaces status', use_textfsm=True)

        vlan_map = {}
        for entry in vlan_status:
            port = entry.get('port')
            if port:
                vlan_map[port] = {
                    'vlan': entry.get('vlan') or entry.get('vlan_id') or entry.get('vlan name') or 'N/A',
                    'duplex': entry.get('duplex', ''),
                    'speed': entry.get('speed', ''),
                    'type': entry.get('type', '')
                }

        for intf in int_brief:
            iface = intf['interface']
            short_iface = normalize(iface)
            intf.update(vlan_map.get(short_iface, {}))

        connection.disconnect()
        return int_brief

    except Exception as e:
        return [{'interface': 'Erreur', 'status': f'{e}', 'vlan': '', 'duplex': '', 'speed': '', 'type': ''}]

# Couleur selon état d'interface
def get_color(status, _):
    status = status.lower()
    if status == 'administratively down':
        return 'red'
    elif status == 'up':
        return 'green'
    else:
        return 'yellow'

# Fonction de synthèse globale

def show_summary():
    summary_window = tk.Toplevel(app)
    summary_window.title("Synthèse des Interfaces")
    summary_window.geometry("1200x600")

    columns = ('Appareil', 'Interface', 'Status', 'VLAN', 'Duplex', 'Speed', 'Type')
    tree = ttk.Treeview(summary_window, columns=columns, show='headings')
    for col in columns:
        tree.heading(col, text=col)
    tree.pack(expand=True, fill='both')

    # Résumé VLAN encadré
    summary_box = ttk.LabelFrame(summary_window, text="Résumé Interface", padding=5)
    summary_box.pack(fill='x', padx=10, pady=5)
    vlan_summary_label = ttk.Label(summary_box, text="VLANs actifs: (chargement...)", font=("Arial", 10, "italic"))
    vlan_summary_label.pack(anchor='w')

    # Bouton manuel placé après la définition de refresh
        

    
    def refresh_summary():
        tree.delete(*tree.get_children())
        for entry in synthesis_data:
            tree.insert('', 'end', values=tuple(entry[col] for col in columns))

    refresh_summary()

    def export_csv():
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not file_path:
            return
        with open(file_path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=columns)
            writer.writeheader()
            writer.writerows(synthesis_data)

    export_button = ttk.Button(summary_window, text="Exporter en CSV", command=export_csv)
    export_button.pack(pady=5)

# Actualisation continue des données et mise à jour tableau synthèse

synthesis_data = []
previous_states = {}

def update_status(tab, device):
    vlan_summary_label = ttk.Label(ttk.LabelFrame(tab, text="Résumé Interface", padding=5), text="VLANs actifs: (chargement...)", font=("Arial", 10, "italic"))
    vlan_summary_label.master.pack(fill='x', padx=10, pady=5)
    vlan_summary_label.pack(anchor='w')
    columns = ('Interface', 'Status', 'VLAN', 'Duplex', 'Speed', 'Type')

    # Barre de recherche et filtre
    search_var = tk.StringVar()
    filter_var = tk.StringVar(value="Tous")

    control_frame = ttk.Frame(tab)
    control_frame.pack(fill='x', pady=5)
    ttk.Label(control_frame, text="Recherche:").pack(side='left')
    search_entry = ttk.Entry(control_frame, textvariable=search_var)
    search_entry.pack(side='left', padx=5)

    ttk.Label(control_frame, text="Filtre:").pack(side='left')
    filter_combo = ttk.Combobox(control_frame, values=["Tous", "UP", "DOWN", "SHUTDOWN", "VLAN", "TRUNK"], textvariable=filter_var, state='readonly')
    filter_combo.pack(side='left', padx=5)

    timestamp_label = ttk.Label(control_frame, text="Dernier scan: --:--:--")
    next_refresh_label = ttk.Label(control_frame, text="Prochain dans: 7s")
    timestamp_label.pack(side='right', padx=5)
    next_refresh_label.pack(side='right', padx=5)
    
    

    tree = ttk.Treeview(tab, columns=columns, show='headings')
    for col in columns:
        tree.heading(col, text=col)
    
    tree.tag_configure('vlan', background='#cfe2ff')
    tree.tag_configure('trunk', background='#ffe0b2')
    tree.pack(expand=True, fill='both')

    def refresh():
        interfaces = fetch_interface_status(device)

        # Générer résumé VLAN, TRUNK, UP
        def vlan_sort_key(x):
            return (0, int(x)) if x.isdigit() else (1, x.lower())

        vlan_set = sorted((str(iface.get('vlan', '')) for iface in interfaces if iface.get('vlan')), key=vlan_sort_key)
        trunk_count = sum(1 for iface in interfaces if iface.get('vlan', '').lower() == 'trunk')
        up_count = sum(1 for iface in interfaces if iface.get('status', '').lower() == 'up')

        if vlan_set:
            vlan_summary_label.config(
                text=f"VLANs actifs ({len(vlan_set)}): " + ", ".join(vlan_set) +
                     f" | Trunks: {trunk_count} | Ports UP: {up_count}"
            )
        else:
            vlan_summary_label.config(text="VLANs actifs: Aucun")
        tree.delete(*tree.get_children())

        filtered = []
        search = search_var.get().lower()
        filtre = filter_var.get().lower()

        for iface in interfaces:
            iface_name = iface.get('interface', 'inconnu')
            status = iface.get('status', 'unknown').lower()
            vlan = iface.get('vlan', '')
            duplex = iface.get('duplex', '')
            speed = iface.get('speed', '')
            itype = iface.get('type', '')
            # Ajout d'une icône pour les trunks
            if vlan.lower() == 'trunk':
                itype = f"🧷 {itype}" if itype else "🧷 Trunk"
            elif iface_name.lower().startswith('vlan'):
                itype = f"🔹 {itype}" if itype else "🔹 VLAN"
            color = get_color(status, '')

            if search and search not in iface_name.lower():
                continue
            if filtre == 'up' and status != 'up':
                continue
            if filtre == 'down' and status != 'down':
                continue
            if filtre == 'shutdown' and status != 'administratively down':
                continue
            if filtre == 'vlan' and not iface_name.lower().startswith('vlan'):
                continue
            if filtre == 'trunk' and vlan.lower() != 'trunk':
                continue

            tree.insert('', 'end', values=(
                iface_name,
                status,
                vlan,
                duplex,
                speed,
                itype
            ), tags=(color, 'vlan' if iface_name.lower().startswith('vlan') else 'trunk' if vlan.lower() == 'trunk' else ''))

            synthesis_data.append({
                'Appareil': device['name'],
                'Interface': iface_name,
                'Status': status,
                'VLAN': vlan,
                'Duplex': duplex,
                'Speed': speed,
                'Type': itype
            })

        tree.tag_configure('green', background='#b6ffb0')
        tree.tag_configure('yellow', background='#ffff99')
        tree.tag_configure('red', background='#ff9999')
        tree.tag_configure('vlan', background='#cfe2ff')

        timestamp_label.config(text=f"Dernier scan: {time.strftime('%H:%M:%S')} ✓")

    def loop():
        counter = 7
        while True:
            next_refresh_label.config(text=f"Prochain dans: {counter}s")
            if counter <= 0:
                refresh()
                counter = 7
            else:
                counter -= 1
            time.sleep(1)

    threading.Thread(target=loop, daemon=True).start()

# Export CSV manuel depuis interface principale

def export_summary_csv():
    if not synthesis_data:
        messagebox.showinfo("Aucune donnée", "Aucune donnée à exporter.")
        return

    file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
    if not file_path:
        return

    columns = ('Appareil', 'Interface', 'Status', 'VLAN', 'Duplex', 'Speed', 'Type')
    with open(file_path, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(synthesis_data)

# Réinitialisation de la liste des appareils
def reset_devices():
    if messagebox.askyesno("Réinitialiser", "Es-tu sûr de vouloir supprimer tous les appareils ?"):
        if messagebox.askyesno("Confirmation", "Action irréversible. Supprimer tous les appareils ?"):
            with open("devices.json", "w") as f:
                json.dump([], f)
            messagebox.showinfo("Liste vidée", "La liste des appareils a été réinitialisée. Redémarre l'application.")

# Menu pour ajouter ou supprimer dynamiquement un appareil
def add_device_popup():
    popup = tk.Toplevel(app)
    popup.title("Ajouter un Appareil")
    popup.geometry("400x300")

    fields = {
        'name': tk.StringVar(),
        'ip': tk.StringVar(),
        'username': tk.StringVar(),
        'password': tk.StringVar()
    }

    for i, (label, var) in enumerate(fields.items()):
        ttk.Label(popup, text=label.capitalize() + ":").grid(row=i, column=0, sticky='w', padx=10, pady=5)
        ttk.Entry(popup, textvariable=var).grid(row=i, column=1, padx=10, pady=5)

    def save_device():
        new_device = {
            'name': fields['name'].get(),
            'device_type': 'cisco_ios',
            'ip': fields['ip'].get(),
            'username': fields['username'].get(),
            'password': fields['password'].get()
        }
        devices.append(new_device)
        tab = ttk.Frame(notebook)
        notebook.add(tab, text=new_device['name'])
        threading.Thread(target=update_status, args=(tab, new_device), daemon=True).start()
        popup.destroy()

    ttk.Button(popup, text="Ajouter", command=lambda: [save_device(), save_devices()]).grid(row=len(fields), column=0, columnspan=2, pady=10)

    ttk.Separator(popup, orient='horizontal').grid(row=len(fields)+1, columnspan=2, sticky='ew', pady=10)

# Déplacement de la suppression d'appareil dans le menu principal

def open_delete_device_popup():
    popup = tk.Toplevel(app)
    popup.title("Supprimer un Appareil")
    popup.geometry("300x200")

    ttk.Label(popup, text="Supprimer un appareil existant:").pack(pady=5)
    device_names = [d['name'] for d in devices]
    selected = tk.StringVar()
    dropdown = ttk.Combobox(popup, values=device_names, textvariable=selected)
    dropdown.pack(padx=10, pady=5)

    def delete_device():
        name = selected.get()
        if not name:
            return
        if messagebox.askyesno("Confirmation", f"Êtes-vous sûr de vouloir supprimer {name} ?"):
            if messagebox.askyesno("Vérification", f"Confirmez-vous définitivement la suppression de {name} ?"):
                devices[:] = [d for d in devices if d['name'] != name]
                save_devices()
                messagebox.showinfo("Appareil supprimé", f"{name} a été supprimé.")
                popup.destroy()

    ttk.Button(popup, text="Supprimer", command=delete_device).pack(pady=10)

    def filter_dropdown(event, combo, all_values):
        typed = combo.get().lower()
        filtered = [name for name in all_values if typed in name.lower()]
        combo['values'] = filtered if filtered else all_values

    def delete_device():
        name = selected.get()
        if not name:
            return
        if messagebox.askyesno("Confirmation", f"Êtes-vous sûr de vouloir supprimer {name} ?"):
            if messagebox.askyesno("Vérification", f"Confirmez-vous définitivement la suppression de {name} ?"):
                devices[:] = [d for d in devices if d['name'] != name]
                save_devices()
                messagebox.showinfo("Appareil supprimé", f"{name} a été supprimé.")
                popup.destroy()

        ttk.Button(popup, text="Supprimer", command=delete_device).grid(row=len(fields)+4, column=0, columnspan=2, pady=10)
from tkinter import PhotoImage

app = tk.Tk()
app.iconphoto(False, PhotoImage(file='icon.png'))  # Assure-toi que 'icon.png' est dans le même dossier
app.title("🛜 Surveillance Réseau Cisco")
app.geometry('1200x600')

notebook = ttk.Notebook(app)
notebook.pack(expand=True, fill='both')

button_frame = ttk.Frame(app)
button_frame.pack(pady=10)

summary_btn = ttk.Button(button_frame, text="Afficher la Synthèse", command=show_summary)
summary_btn.pack(side='left', padx=5)

add_btn = ttk.Button(button_frame, text="Ajouter un Appareil", command=add_device_popup)
add_btn.pack(side='left', padx=5)

reset_btn = ttk.Button(button_frame, text="Réinitialiser la Liste", command=lambda: reset_devices())
reset_btn.pack(side='left', padx=5)

delete_btn = ttk.Button(button_frame, text="Supprimer un Appareil", command=open_delete_device_popup)
delete_btn.pack(side='left', padx=5)

save_btn = ttk.Button(button_frame, text="Exporter Synthèse CSV", command=lambda: export_summary_csv())
save_btn.pack(side='left', padx=5)

# Création des onglets pour chaque appareil
if not devices:
    messagebox.showinfo("Aucun appareil", "Aucun appareil configuré. Ajoutez-en un via le bouton ci-dessus.")

for device in devices:
    tab = ttk.Frame(notebook)
    icon = ""
    notebook.add(tab, text=device['name'])

    

    
    threading.Thread(target=update_status, args=(tab, device), daemon=True).start()

app.mainloop()
