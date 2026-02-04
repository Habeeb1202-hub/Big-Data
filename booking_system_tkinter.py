import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3, pathlib
import pandas as pd
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

BASE = pathlib.Path(__file__).resolve().parent
DBFOLDER = BASE / 'db'
DBFOLDER.mkdir(exist_ok=True)
DB = DBFOLDER / 'app.db'

BG = '#1e1e1e'
PANEL = '#2a2a2a'
BTN = '#007acc'
FG = 'white'

def conn():
    c = sqlite3.connect(str(DB))
    c.execute('PRAGMA foreign_keys=ON')
    return c


def initdb():
    c = conn(); cur = c.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, phone TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS rooms(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, capacity INTEGER NOT NULL, price REAL NOT NULL)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS bookings(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, room_id INTEGER NOT NULL, checkin_date TEXT NOT NULL, nights INTEGER NOT NULL, total REAL NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE, FOREIGN KEY(room_id) REFERENCES rooms(id) ON DELETE CASCADE)''')
    c.commit(); c.close()

def run(q,p=(),fetch=False):
    c = conn(); cur = c.cursor(); cur.execute(q,p)
    data = cur.fetchall() if fetch else None
    c.commit(); c.close(); return data

def clean_str(v):
    if pd.isna(v): return ''
    if isinstance(v, str):
        return v.strip().replace('\ufeff','')
    return str(v)

style = None

def style_widgets(root):
    global style
    style = ttk.Style(root)
    try:
        style.theme_use('clam')
    except:
        pass
    style.configure('TButton', background=BTN, foreground=FG)

# USERS

def users_win(master):
    w = tk.Toplevel(master); w.title('Users'); w.configure(bg=BG); w.geometry('760x430'); w.minsize(640,380); w.resizable(True, True)
    frame = tk.Frame(w, bg=PANEL); frame.pack(fill='both', expand=True, padx=8, pady=8)
    cols = ('id','name','email','phone')
    tree = ttk.Treeview(frame, columns=cols, show='headings')
    for c in cols:
        tree.heading(c, text=c.capitalize())
        tree.column(c, width=150 if c!='id' else 50)
    tree.pack(fill='both', expand=True, padx=6, pady=6)

    def load():
        tree.delete(*tree.get_children())
        rows = run('SELECT id,name,email,phone FROM users ORDER BY name', fetch=True)
        if rows:
            for r in rows: tree.insert('', 'end', values=r)

    def open_form(vals=None):
        f = tk.Toplevel(w); f.title('User'); f.configure(bg=BG); f.resizable(True, True)
        tk.Label(f, text='Name', bg=BG, fg=FG).grid(row=0,column=0,sticky='w')
        n = tk.Entry(f); n.grid(row=0,column=1,padx=4,pady=4)
        tk.Label(f, text='Email', bg=BG, fg=FG).grid(row=1,column=0,sticky='w')
        e = tk.Entry(f); e.grid(row=1,column=1,padx=4,pady=4)
        tk.Label(f, text='Phone', bg=BG, fg=FG).grid(row=2,column=0,sticky='w')
        p = tk.Entry(f); p.grid(row=2,column=1,padx=4,pady=4)
        if vals:
            n.insert(0, vals[1]); e.insert(0, vals[2]); p.insert(0, vals[3])
        def save():
            name = clean_str(n.get()); email = clean_str(e.get()).lower(); phone = clean_str(p.get())
            if not name or not email or '@' not in email:
                messagebox.showerror('Error','Name and valid Email required'); return
            try:
                if vals:
                    run('UPDATE users SET name=?,email=?,phone=? WHERE id=?',(name,email,phone,vals[0]))
                else:
                    run('INSERT INTO users(name,email,phone) VALUES(?,?,?)',(name,email,phone))
            except Exception:
                messagebox.showerror('Error','Email may already exist or invalid'); return
            f.destroy(); load()
        tk.Button(f, text='Save', bg=BTN, fg=FG, command=save).grid(row=3,column=0,columnspan=2,pady=6)

    def add(): open_form()
    def edit():
        s = tree.selection();
        if not s: return
        open_form(tree.item(s[0])['values'])
    def delete():
        s = tree.selection();
        if not s: return
        rid = tree.item(s[0])['values'][0]
        if messagebox.askyesno('Delete','Remove user?'): run('DELETE FROM users WHERE id=?',(rid,)); load()

    def export_csv():
        rows = run('SELECT id,name,email,phone FROM users', fetch=True)
        if not rows: messagebox.showinfo('Export','No data'); return
        df = pd.DataFrame(rows, columns=cols)
        p = filedialog.asksaveasfilename(defaultextension='.csv')
        if p: df.to_csv(p,index=False); messagebox.showinfo('Export','Saved')

    def import_csv():
        p = filedialog.askopenfilename(filetypes=[('CSV','*.csv'),('All','*.*')])
        if not p: return
        try:
            df = pd.read_csv(p)
        except Exception as e:
            messagebox.showerror('Error','Cannot read CSV'); return
        headers = {clean_str(h).lower():h for h in df.columns}
        possible = {'name':'name','first_name':'name','full_name':'name', 'email':'email','e-mail':'email','phone':'phone','telephone':'phone'}
        mapping = {}
        for k,v in possible.items():
            if k in headers: mapping[v]=headers[k]
        if not {'name','email'}.issubset(set(mapping.keys())):
            messagebox.showerror('Error','CSV must contain name and email columns'); return
        inserted = 0
        for _,row in df.iterrows():
            name = clean_str(row.get(mapping['name'],'')).strip()
            email = clean_str(row.get(mapping['email'],'')).lower()
            phone = clean_str(row.get(mapping.get('phone',''),'')).strip()
            if not name or not email or '@' not in email: continue
            try:
                run('INSERT INTO users(name,email,phone) VALUES(?,?,?)',(name,email,phone))
                inserted +=1
            except:
                continue
        load(); messagebox.showinfo('Import',f'Inserted: {inserted}')

    btnf = tk.Frame(w,bg=BG); btnf.pack(fill='x')
    for txt,cmd in [('Add',add),('Edit',edit),('Delete',delete),('Import',import_csv),('Export',export_csv),('Refresh',load)]:
        b = tk.Button(btnf,text=txt,command=cmd,bg=BTN,fg=FG)
        b.pack(side='left',padx=6,pady=6)

    load()

# ROOMS

def rooms_win(master):
    w = tk.Toplevel(master); w.title('Rooms'); w.configure(bg=BG); w.geometry('700x420'); w.minsize(600,360); w.resizable(True, True)
    frame = tk.Frame(w,bg=PANEL); frame.pack(fill='both',expand=True,padx=8,pady=8)
    cols=('id','name','capacity','price')
    tree = ttk.Treeview(frame,columns=cols,show='headings')
    for c in cols:
        tree.heading(c,text=c.capitalize()); tree.column(c,width=120 if c!='id' else 50)
    tree.pack(fill='both',expand=True,padx=6,pady=6)

    def load():
        tree.delete(*tree.get_children())
        for r in run('SELECT id,name,capacity,price FROM rooms ORDER BY name',fetch=True): tree.insert('','end',values=r)

    def open_form(vals=None):
        f = tk.Toplevel(w); f.title('Room'); f.configure(bg=BG); f.resizable(True, True)
        tk.Label(f,text='Name',bg=BG,fg=FG).grid(row=0,column=0,sticky='w'); n=tk.Entry(f); n.grid(row=0,column=1)
        tk.Label(f,text='Capacity',bg=BG,fg=FG).grid(row=1,column=0,sticky='w'); c_e=tk.Entry(f); c_e.grid(row=1,column=1)
        tk.Label(f,text='Price',bg=BG,fg=FG).grid(row=2,column=0,sticky='w'); p=tk.Entry(f); p.grid(row=2,column=1)
        if vals: n.insert(0,vals[1]); c_e.insert(0,vals[2]); p.insert(0,vals[3])
        def save():
            name=clean_str(n.get()); cap=clean_str(c_e.get()); price=clean_str(p.get())
            if not name or not cap.isdigit() or int(cap)<=0 or not price.replace('.','',1).isdigit():
                messagebox.showerror('Error','Check fields'); return
            try:
                if vals: run('UPDATE rooms SET name=?,capacity=?,price=? WHERE id=?',(name,int(cap),float(price),vals[0]))
                else: run('INSERT INTO rooms(name,capacity,price) VALUES(?,?,?)',(name,int(cap),float(price)))
            except Exception:
                messagebox.showerror('Error','Room name exists or invalid'); return
            f.destroy(); load()
        tk.Button(f,text='Save',bg=BTN,fg=FG,command=save).grid(row=3,column=0,columnspan=2,pady=6)

    def add(): open_form()
    def edit():
        s=tree.selection();
        if not s: return
        open_form(tree.item(s[0])['values'])
    def delete():
        s=tree.selection();
        if not s: return
        rid=tree.item(s[0])['values'][0]
        if messagebox.askyesno('Delete','Remove room?'): run('DELETE FROM rooms WHERE id=?',(rid,)); load()

    def export_csv():
        rows = run('SELECT id,name,capacity,price FROM rooms', fetch=True)
        if not rows: messagebox.showinfo('Export','No data'); return
        df = pd.DataFrame(rows, columns=cols); p=filedialog.asksaveasfilename(defaultextension='.csv')
        if p: df.to_csv(p,index=False); messagebox.showinfo('Export','Saved')

    def import_csv():
        p=filedialog.askopenfilename(filetypes=[('CSV','*.csv'),('All','*.*')])
        if not p: return
        try: df=pd.read_csv(p)
        except: messagebox.showerror('Error','Cannot read CSV'); return
        headers = {clean_str(h).lower():h for h in df.columns}
        possible = {'name':'name','capacity':'capacity','cap':'capacity','price':'price','cost':'price'}
        mapping={}
        for k,v in possible.items():
            if k in headers: mapping[v]=headers[k]
        if not {'name','capacity','price'}.issubset(mapping.keys()): messagebox.showerror('Error','CSV needs name,capacity,price'); return
        ins=0
        for _,r in df.iterrows():
            name=clean_str(r.get(mapping['name'],'')).strip(); cap=clean_str(r.get(mapping['capacity'],'')).strip(); pr=clean_str(r.get(mapping['price'],'')).strip()
            if not name or not cap.replace('.','',1).isdigit(): continue
            try:
                run('INSERT INTO rooms(name,capacity,price) VALUES(?,?,?)',(name,int(float(cap)),float(pr)))
            except: continue
        load(); messagebox.showinfo('Import',f'Inserted {ins}')

    btnf=tk.Frame(w,bg=BG); btnf.pack(fill='x')
    for txt,cmd in [('Add',add),('Edit',edit),('Delete',delete),('Import',import_csv),('Export',export_csv),('Refresh',load)]:
        tk.Button(btnf,text=txt,command=cmd,bg=BTN,fg=FG).pack(side='left',padx=6,pady=6)

    load()

# BOOKINGS

def bookings_win(master):
    w = tk.Toplevel(master); w.title('Bookings'); w.configure(bg=BG); w.geometry('900x480'); w.minsize(700,420); w.resizable(True, True)
    frame=tk.Frame(w,bg=PANEL); frame.pack(fill='both',expand=True,padx=8,pady=8)
    cols=('id','user','room','checkin_date','nights','total','user_id','room_id') 
    tree=ttk.Treeview(frame,columns=cols,show='headings')
    heads=['ID','User','Room','Check-in','Nights','Total','',''] 
    widths=[50,180,180,120,70,80,0,0]
    for c,h,wid in zip(cols,heads,widths): tree.heading(c,text=h); tree.column(c,width=wid,stretch=False)
    tree.pack(fill='both',expand=True,padx=6,pady=6)

    def load():
        tree.delete(*tree.get_children())
        q='''SELECT b.id,u.name,r.name,b.checkin_date,b.nights,b.total,b.user_id,b.room_id FROM bookings b JOIN users u ON b.user_id=u.id JOIN rooms r ON b.room_id=r.id ORDER BY b.checkin_date DESC''' 
        for r in run(q, fetch=True): tree.insert('','end',values=r)

    def open_form(vals=None):
        f=tk.Toplevel(w); f.title('Booking'); f.configure(bg=BG); f.resizable(True, True)
        tk.Label(f,text='User',bg=BG,fg=FG).grid(row=0,column=0,sticky='w')
        users = run('SELECT id,name FROM users ORDER BY name', fetch=True)
        umap={f"{u[1]} (id:{u[0]})":u[0] for u in users}
        ucb=ttk.Combobox(f, values=list(umap.keys()), width=36)
        ucb.grid(row=0,column=1)
        tk.Label(f,text='Room',bg=BG,fg=FG).grid(row=1,column=0,sticky='w')
        rooms = run('SELECT id,name,price FROM rooms ORDER BY name', fetch=True)
        rmap={f"{r[1]} (id:{r[0]})":(r[0],r[2]) for r in rooms}
        rcb=ttk.Combobox(f, values=list(rmap.keys()), width=36)
        rcb.grid(row=1,column=1)
        tk.Label(f,text='Check-in Date (YYYY-MM-DD)',bg=BG,fg=FG).grid(row=2,column=0,sticky='w') 
        cin=tk.Entry(f); cin.grid(row=2,column=1)
        tk.Label(f,text='Nights',bg=BG,fg=FG).grid(row=3,column=0,sticky='w')
        nights=tk.Entry(f); nights.grid(row=3,column=1)
        tk.Label(f,text='Total (blank to auto)',bg=BG,fg=FG).grid(row=4,column=0,sticky='w')
        total=tk.Entry(f); total.grid(row=4,column=1)
        if vals:
            # populate
            uid=vals[6]; rid=vals[7]; selu=[k for k,v in umap.items() if v==uid]; selr=[k for k,v in rmap.items() if v[0]==rid]
            if selu: ucb.set(selu[0])
            if selr: rcb.set(selr[0])
            cin.insert(0,vals[3]); nights.insert(0,vals[4]); total.insert(0,vals[5]) 
        def calc():
             sel = rcb.get()
             if not sel or sel not in rmap:
                 return
             pr = rmap[sel][1]
             n = nights.get().strip()
             if n.isdigit():
                 total.delete(0, 'end')
                 total.insert(0, str(pr * int(n)))
        tk.Button(f,text='Auto-calc',bg=BTN,fg=FG,command=calc).grid(row=5,column=0,columnspan=2,pady=4)
        def save():
            ukey=ucb.get(); rkey=rcb.get(); cinv=clean_str(cin.get()); n=nights.get().strip(); tot=clean_str(total.get())
            if not ukey or not rkey or not cinv or not n.isdigit(): messagebox.showerror('Error','Check required fields'); return
            uid=umap.get(ukey); rp=rmap.get(rkey); rid=rp[0]
            if not tot.replace('.','',1).isdigit(): tot=str(rp[1]*int(n))
            room_cap = run("SELECT capacity FROM rooms WHERE id=?", (rid,), fetch=True)[0][0]
            current_count = run("SELECT COUNT(*) FROM bookings WHERE room_id=? AND checkin_date=?",(rid, cinv),fetch=True)[0][0]
            if not vals:
              future_total = current_count + 1
            else:
                old_rid = vals[7]
                old_date = vals[3]
                if old_rid == rid and old_date == cinv:
                    future_total = current_count
                else:
                     future_total = current_count + 1

            if future_total > room_cap:
                messagebox.showerror("Room Full",f"This room can only take {room_cap} people.\n"f"{current_count} already booked for this date.")
                return
            try:
                if vals: run('UPDATE bookings SET user_id=?,room_id=?,checkin_date=?,nights=?,total=? WHERE id=?',(uid,rid,cinv,int(n),float(tot),vals[0]))
                else: run('INSERT INTO bookings(user_id,room_id,checkin_date,nights,total) VALUES(?,?,?,?,?)',(uid,rid,cinv,int(n),float(tot)))
            except Exception as e:
                messagebox.showerror('Error','Could not save booking'); return
            f.destroy(); load()
        tk.Button(f,text='Save',bg=BTN,fg=FG,command=save).grid(row=6,column=0,columnspan=2,pady=6)

    def add(): open_form()
    def edit():
        s=tree.selection();
        if not s: return
        open_form(tree.item(s[0])['values'])
    def delete():
        s=tree.selection();
        if not s: return
        bid=tree.item(s[0])['values'][0]
        if messagebox.askyesno('Delete','Remove booking?'): run('DELETE FROM bookings WHERE id=?',(bid,)); load()

    def view_user():
        s=tree.selection();
        if not s: return
        uid=tree.item(s[0])['values'][6]
        user_details(uid)
    def view_room():
        s=tree.selection();
        if not s: return
        rid=tree.item(s[0])['values'][7]
        room_details(rid)

    def export_csv():
        rows = run('SELECT id,user_id,room_id,checkin_date,nights,total FROM bookings', fetch=True)
        if not rows: messagebox.showinfo('Export','No data'); return
        df = pd.DataFrame(rows, columns=['id','user_id','room_id','checkin_date','nights','total'])
        p=filedialog.asksaveasfilename(defaultextension='.csv')
        if p: df.to_csv(p,index=False); messagebox.showinfo('Export','Saved')

    def import_csv():
        p=filedialog.askopenfilename(filetypes=[('CSV','*.csv'),('All','*.*')])
        if not p: return
        try: df=pd.read_csv(p)
        except: messagebox.showerror('Error','Cannot read CSV'); return
        hdrs={clean_str(h).lower():h for h in df.columns}
        need_keys=['user_id','room_id','checkin_date','nights','total']
        if not set(need_keys).issubset(hdrs.keys()): messagebox.showerror('Error','CSV must have user_id,room_id,checkin_date,nights,total columns'); return
        userset={r[0] for r in run('SELECT id FROM users',fetch=True)}
        roomset={r[0] for r in run('SELECT id FROM rooms',fetch=True)}
        ins=0
        for _,r in df.iterrows():
            try:
                uid=int(r.get(hdrs['user_id'])); rid=int(r.get(hdrs['room_id'])); cin=clean_str(r.get(hdrs['checkin_date'])); nights=int(r.get(hdrs['nights'])); tot=float(r.get(hdrs['total']))
            except Exception:
                continue
            if uid not in userset or rid not in roomset: continue
            try: run('INSERT INTO bookings(user_id,room_id,checkin_date,nights,total) VALUES(?,?,?,?,?)',(uid,rid,cin,nights,tot)); ins+=1
            except: continue
        load(); messagebox.showinfo('Import',f'Inserted {ins}')

    btnf=tk.Frame(w,bg=BG); btnf.pack(fill='x')
    for txt,cmd in [('Add',add),('Edit',edit),('Delete',delete),('View User',view_user),('View Room',view_room),('Import',import_csv),('Export',export_csv),('Refresh',load)]:
        tk.Button(btnf,text=txt,command=cmd,bg=BTN,fg=FG).pack(side='left',padx=4,pady=6)

    load()

# DETAILS

def user_details(uid):
    row = run('SELECT id,name,email,phone FROM users WHERE id=?',(uid,),fetch=True)
    if not row: return
    r = row[0]
    w = tk.Toplevel(); w.title(f'User {r[1]}'); w.configure(bg=BG)
    tk.Label(w,text=f'ID: {r[0]}',bg=BG,fg=FG).pack(anchor='w')
    tk.Label(w,text=f'Name: {r[1]}',bg=BG,fg=FG).pack(anchor='w')
    tk.Label(w,text=f'Email: {r[2]}',bg=BG,fg=FG).pack(anchor='w')
    tk.Label(w,text=f'Phone: {r[3]}',bg=BG,fg=FG).pack(anchor='w')
    cols=('id','room','checkin_date','nights','total')
    tree=ttk.Treeview(w,columns=cols,show='headings')
    tree.heading('checkin_date',text='Check-in Date'); tree.heading('id',text='Id'); tree.heading('room',text='Room'); tree.heading('nights',text='Nights'); tree.heading('total',text='Total')
    tree.pack(fill='both',expand=True)
    for x in run('SELECT b.id,r.name,b.checkin_date,b.nights,b.total FROM bookings b JOIN rooms r ON b.room_id=r.id WHERE b.user_id=?',(uid,),fetch=True): tree.insert('','end',values=x)

def room_details(rid):
    row = run('SELECT id,name,capacity,price FROM rooms WHERE id=?',(rid,),fetch=True)
    if not row: return
    r = row[0]
    w = tk.Toplevel(); w.title(f'Room {r[1]}'); w.configure(bg=BG)
    tk.Label(w,text=f'ID: {r[0]}',bg=BG,fg=FG).pack(anchor='w')
    tk.Label(w,text=f'Name: {r[1]}',bg=BG,fg=FG).pack(anchor='w')
    tk.Label(w,text=f'Capacity: {r[2]}',bg=BG,fg=FG).pack(anchor='w')
    tk.Label(w,text=f'Price: {r[3]}',bg=BG,fg=FG).pack(anchor='w')
    cols=('id','user','checkin_date','nights','total')
    tree=ttk.Treeview(w,columns=cols,show='headings')
    tree.heading('checkin_date',text='Check-in Date'); tree.heading('id',text='Id'); tree.heading('user',text='User'); tree.heading('nights',text='Nights'); tree.heading('total',text='Total')
    tree.pack(fill='both',expand=True)
    for x in run('SELECT b.id,u.name,b.checkin_date,b.nights,b.total FROM bookings b JOIN users u ON b.user_id=u.id WHERE b.room_id=?',(rid,),fetch=True): tree.insert('','end',values=x)

# REPORTS

def reports_win(master):
    w = tk.Toplevel(master); w.title('Reports'); w.geometry('800x600'); w.configure(bg=BG); w.resizable(True, True)
    top=tk.Frame(w,bg=BG); top.pack(fill='x')
    plot = tk.Frame(w,bg=PANEL); plot.pack(fill='both',expand=True,padx=6,pady=6)

    def clear():
        for c in plot.winfo_children(): c.destroy()

    def by_room():
        clear()
        q = 'SELECT r.name, COUNT(b.id) FROM bookings b JOIN rooms r ON b.room_id=r.id GROUP BY r.name ORDER BY 2 DESC'
        df = pd.read_sql_query(q, conn())
        if df.empty: messagebox.showinfo('No data','No bookings'); return
        fig = Figure(figsize=(6,4)); ax = fig.add_subplot(111); ax.bar(df['name'], df.iloc[:,1]); fig.autofmt_xdate(rotation=45)
        canvas = FigureCanvasTkAgg(fig, master=plot); canvas.draw(); canvas.get_tk_widget().pack(fill='both',expand=True)

    def top_rooms():
        clear()
        q = 'SELECT r.name, COUNT(b.id) as cnt FROM bookings b JOIN rooms r ON b.room_id=r.id GROUP BY r.name ORDER BY cnt DESC LIMIT 10'
        df = pd.read_sql_query(q, conn())
        if df.empty: messagebox.showinfo('No data','No bookings'); return
        fig = Figure(figsize=(6,4)); ax = fig.add_subplot(111); ax.barh(df['name'], df['cnt']); canvas = FigureCanvasTkAgg(fig, master=plot); canvas.draw(); canvas.get_tk_widget().pack(fill='both',expand=True)

    def top_bookings():
        clear()
        q = 'SELECT b.id,u.name,r.name,b.total FROM bookings b JOIN users u ON b.user_id=u.id JOIN rooms r ON b.room_id=r.id ORDER BY b.total DESC LIMIT 20'
        df = pd.read_sql_query(q, conn())
        if df.empty: messagebox.showinfo('No data','No bookings'); return
        tree = ttk.Treeview(plot, columns=('id','user','room','total'), show='headings');
        for c in ('id','user','room','total'): tree.heading(c,text=c.capitalize()); tree.pack(fill='x')
        for r in df.itertuples(index=False): tree.insert('','end',values=r)
        fig = Figure(figsize=(6,3)); ax = fig.add_subplot(111); ax.bar(df['id'].astype(str).head(10), df['total'].head(10)); canvas = FigureCanvasTkAgg(fig, master=plot); canvas.draw(); canvas.get_tk_widget().pack(fill='both',expand=True)

    tk.Button(top,text='Bookings per room',bg=BTN,fg=FG,command=by_room).pack(side='left',padx=6,pady=6)
    tk.Button(top,text='Top rooms',bg=BTN,fg=FG,command=top_rooms).pack(side='left',padx=6,pady=6)
    tk.Button(top,text='Top bookings',bg=BTN,fg=FG,command=top_bookings).pack(side='left',padx=6,pady=6)

# MAIN

def main():
    initdb(); root = tk.Tk(); root.title('Booking System'); root.configure(bg=BG); root.geometry('480x360'); root.minsize(420,320)
    style_widgets(root)
    tk.Label(root,text='Booking System',font=('Arial',18,'bold'),bg=BG,fg=FG).pack(pady=18)
    f=tk.Frame(root,bg=BG); f.pack()
    tk.Button(f,text='Users',width=22,command=lambda: users_win(root),bg=BTN,fg=FG).pack(pady=6)
    tk.Button(f,text='Rooms',width=22,command=lambda: rooms_win(root),bg=BTN,fg=FG).pack(pady=6)
    tk.Button(f,text='Bookings',width=22,command=lambda: bookings_win(root),bg=BTN,fg=FG).pack(pady=6)
    tk.Button(f,text='Reports',width=22,command=lambda: reports_win(root),bg=BTN,fg=FG).pack(pady=6)
    tk.Label(root,text='Use Import/Export to load test data',bg=BG,fg=FG).pack(pady=12)
    root.mainloop()

if __name__ == '__main__': 
    main()