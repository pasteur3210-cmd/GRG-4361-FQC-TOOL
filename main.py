"""US factory English GUI for GRG-4361 FQC read-only verification."""
import datetime as dt
import json
import logging
import queue
import re
import threading
import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox
from grg4361 import Inspector
from openpyxl import Workbook
from master_record import sync_master, MASTER_NAME

APP='GRG-4361 FQC Test Tool V1.0.5'

def application_directory():
    """Return EXE folder in frozen mode, project folder for source execution."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent

ROOT=application_directory()/'Records'


def make_logger(directory):
    directory.mkdir(parents=True,exist_ok=True)
    logger=logging.getLogger('fqc'); logger.handlers.clear();logger.setLevel(logging.DEBUG)
    for filename,level in [('execution.log',logging.INFO),('debug.log',logging.DEBUG)]:
        h=logging.FileHandler(directory/filename,encoding='utf-8');h.setLevel(level)
        h.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'));logger.addHandler(h)
    return logger

def save_record(directory,overall,rows,details,sn="",operator="",scans=None):
    now=dt.datetime.now().astimezone().isoformat(timespec='seconds')
    payload={'timestamp':now,'overall':overall,'results':rows,'details':details,'dut_sn':sn,'operator':operator,'label_scans':scans or {}}
    (directory/'result.json').write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding='utf-8')
    with (directory/'test.log').open('w',encoding='utf-8') as f:
        f.write(f'{now} Overall: {overall}\n')
        for row in rows: f.write(f"{row['item']} | {row['expected']} | {row['actual']} | {row['result']}\n")
    wb=Workbook(); ws=wb.active; ws.title='FQC Result'
    ws.append(['GRG-4361 FQC Test Tool V1.0.5',now,overall]);ws.append(['Test Item','Expected','Actual','Result'])
    for row in rows:ws.append([row[k] for k in ('item','expected','actual','result')])
    ws.freeze_panes='A3';ws.auto_filter.ref=f'A2:D{ws.max_row}'
    for col,width in {'A':31,'B':44,'C':41,'D':17}.items():ws.column_dimensions[col].width=width
    wb.save(directory/'FQC_Result.xlsx')

class App:
    def __init__(self,root):
        self.root=root;root.title(APP);root.geometry('1240x810');root.minsize(840,540)
        self.q=queue.Queue();self.host=tk.StringVar(value='192.168.1.1');self.user=tk.StringVar(value='root')
        self.pw=tk.StringVar();self.sn=tk.StringVar();self.label_mac=tk.StringVar();self.label_gpon=tk.StringVar();self.fw=tk.StringVar();self.operator=tk.StringVar();self.status=tk.StringVar(value='READY FOR SCAN')
        top=ttk.Frame(root,padding=12);top.pack(fill='x')
        for label,var,width in [('Router IP',self.host,18),('Username',self.user,16),('Password',self.pw,18),('Approved FW',self.fw,18),('Operator',self.operator,13)]:
            cell=ttk.Frame(top);cell.pack(side='left',padx=4)
            ttk.Label(cell,text=label).pack(anchor='w')
            ttk.Entry(cell,textvariable=var,width=width,show='*' if label=='Password' else '').pack()
        bar=ttk.Frame(root,padding=(14,9));bar.pack(fill='x')
        self.btn=ttk.Button(bar,text='START READ-ONLY CHECK',command=self.start)
        self.btn.pack(side='right',padx=8)
        ttk.Label(bar,textvariable=self.status,font=('Arial',17,'bold')).pack(side='left',padx=10)
        scan_frame=ttk.LabelFrame(root,text='Chassis Label Barcode Scan',padding=10)
        scan_frame.pack(fill='x',padx=14,pady=6)
        self.scan_entries=[]
        for index,(label,var) in enumerate([('Scan SN (20 characters)',self.sn),('Scan MAC (12 hex)',self.label_mac),('Scan GPON SN (12 characters)',self.label_gpon)]):
            ttk.Label(scan_frame,text=label,width=29).grid(row=index,column=0,sticky='w',pady=4)
            entry=ttk.Entry(scan_frame,textvariable=var,width=44,font=('Arial',12))
            entry.grid(row=index,column=1,sticky='ew',pady=4)
            self.scan_entries.append(entry)
        scan_frame.columnconfigure(1,weight=1)
        for idx,entry in enumerate(self.scan_entries[:-1]):
            entry.bind('<Return>',lambda event,i=idx:self.scan_entries[i+1].focus_set())
        self.scan_entries[-1].bind('<Return>',lambda event:self.btn.focus_set())
        self.scan_entries[0].focus_set()
        self.last_run_dir=None
        root.option_add('*Font','Arial 10')
        menu=tk.Menu(root);tools=tk.Menu(menu,tearoff=False)
        tools.add_command(label='Open Records',command=self.open_records)
        tools.add_command(label='Open Last Run Logs',command=self.open_last_logs)
        tools.add_command(label='Open Master',command=self.open_master)
        tools.add_command(label='Sync Master',command=self.sync_master_manual)
        menu.add_cascade(label='Maintenance',menu=tools);root.configure(menu=menu)
        columns=('item','expected','actual','result')
        area=ttk.Frame(root,padding=12);area.pack(fill='both',expand=True)
        self.tree=ttk.Treeview(area,columns=columns,show='headings')
        for k,heading,width in zip(columns,['Test Item','Expected / Rule','Actual Value','Result'],[230,270,290,110]):
            self.tree.heading(k,text=heading);self.tree.column(k,width=width,stretch=True)
        sb=ttk.Scrollbar(area,orient='vertical',command=self.tree.yview);self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side='left',fill='both',expand=True);sb.pack(side='left',fill='y')
        ttk.Label(root,text='Records: <EXE Folder>\\Records   |   Read-only: no reset, write, or OLT operations',padding=10).pack(anchor='w')
        root.after(100,self.poll)
    def open_folder(self, path):
        path=Path(path)
        if not path.exists():
            messagebox.showinfo('Records', 'Folder not found: '+str(path));return
        try:
            if sys.platform=='win32': os.startfile(str(path))
            elif sys.platform=='darwin': subprocess.Popen(['open',str(path)])
            else: subprocess.Popen(['xdg-open',str(path)])
        except Exception as exc: messagebox.showerror('Open Records Error',str(exc))
    def open_records(self): self.open_folder(ROOT)
    def open_last_logs(self):
        if self.last_run_dir: self.open_folder(self.last_run_dir)
        else: messagebox.showinfo('Records','Run a test first.')
    def open_master(self):
        master=ROOT/MASTER_NAME
        if master.exists():
            try:
                if sys.platform=='win32':os.startfile(str(master))
                else:self.open_folder(ROOT)
            except Exception as exc:messagebox.showerror('Open Master Error',str(exc))
        else:messagebox.showinfo('Master Record','No Master Record yet. Run a test or SYNC MASTER.')
    def sync_master_manual(self):
        def job():
            try:self.q.put(('sync',str(sync_master(ROOT)),[],str(ROOT)))
            except Exception as exc:self.q.put(('sync_error',str(exc),[],str(ROOT)))
        threading.Thread(target=job,daemon=True).start()
    def led_confirm(self,title,instructions):
        """Blocking operator decision; focus PASS but never default to PASS silently."""
        dialog=tk.Toplevel(self.root);dialog.title(title);dialog.transient(self.root)
        dialog.grab_set();dialog.resizable(False,False)
        result={'value':None}
        ttk.Label(dialog,text=title,font=('Arial',15,'bold'),padding=15).pack()
        ttk.Label(dialog,text=instructions,justify='left',padding=12,font=('Arial',11)).pack()
        buttons=ttk.Frame(dialog,padding=12);buttons.pack()
        def choose(value): result['value']=value;dialog.destroy()
        good=ttk.Button(buttons,text='PASS',command=lambda:choose('PASS'),width=17)
        good.pack(side='left',padx=12)
        ttk.Button(buttons,text='FAIL',command=lambda:choose('FAIL'),width=17).pack(side='left',padx=12)
        good.focus_set();dialog.bind('<Return>',lambda _event:choose('PASS'))
        dialog.protocol('WM_DELETE_WINDOW',lambda:choose('CANCEL'))
        self.root.wait_window(dialog)
        return result['value']
    def start(self):
        if not self.host.get().strip() or not self.pw.get():
            messagebox.showwarning('Missing input','Router IP and password are required.');return
        scans={'sn':self.sn.get().strip(),'mac':self.label_mac.get().strip(),'gpon':self.label_gpon.get().strip()}
        if not all(scans.values()):
            messagebox.showwarning('Missing scans','Scan SN, MAC and GPON SN before starting.');return
        initial=self.led_confirm('STEP 1 / 2 - INITIAL LED CHECK',
            'Before connecting fiber (DUT boot completed):\n'
            'Power: green ON\nPhone: OFF\n10G LAN: blue ON (per qualified link)\nPON: red blinking\n\n'
            'Visually inspect all LEDs, then select PASS or FAIL.')
        if initial=='CANCEL':return
        functional='NOT TESTED'
        if initial=='PASS':
            functional=self.led_confirm('STEP 2 / 2 - FUNCTIONAL LED CHECK',
                '1. Pick up telephone handset: Phone LED green blinking.\n'
                '2. Connect fiber to the OLT. Wait for PON registration.\n'
                '3. When registered (O5), PON LED must be green solid.\n\n'
                'Inspect both LEDs. The software will independently check O5.')
            if functional=='CANCEL':return
        self.btn.configure(state='disabled');self.status.set('TESTING...' if initial=='PASS' and functional=='PASS' else 'LED FAIL')
        self.tree.delete(*self.tree.get_children())
        values=(self.host.get().strip(),self.user.get().strip(),self.pw.get(),scans,self.fw.get().strip(),self.operator.get().strip(),initial,functional)
        threading.Thread(target=self.work,args=values,daemon=True).start()
    def work(self,host,user,password,scans,fw,operator,initial,functional):
        stamp=dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f');directory=ROOT/stamp;client=None
        try:logger=make_logger(directory)
        except OSError as exc:
            self.q.put(('error','Cannot write Records next to EXE: '+str(exc),[],str(directory)));return
        try:
            logger.info('START router=%s mode=READ_ONLY LED_INITIAL=%s LED_FUNCTIONAL=%s',host,initial,functional)
            if initial!='PASS' or functional!='PASS':
                rows=[{'item':'LED Initial','expected':'Initial LED visual check','actual':initial,'result':initial},
                      {'item':'LED Functional','expected':'Phone off-hook and PON green at O5','actual':functional,
                       'result':functional if functional=='FAIL' else 'INFO'}]
                overall='FAIL';details={'label_scans':scans,'led_initial':initial,'led_functional':functional}
                logger.info('LED check FAIL; HTTP automatic testing SKIPPED')
            else:
                def safe_debug(msg):
                    msg=re.sub(r'(?i)(password|cookie|csrf|token|authorization)([^\s]*)',r'[REDACTED]',str(msg))
                    logger.debug(msg)
                client=Inspector(host,safe_debug)
                logger.info('LED checks PASS; HTTP login and read-only checks started')
                overall,rows,details=client.run(user,password,scans,fw,initial,functional)
            details['led_initial']=initial;details['led_functional']=functional
            for row in rows:logger.info('TEST %s | expected=%s | actual=%s | result=%s',row['item'],row['expected'],row['actual'],row['result'])
            save_record(directory,overall,rows,details,scans['sn'],operator,scans)
            try:
                appended=sync_master(ROOT)
                logger.info('MASTER SYNC success appended=%s',appended)
                displayed=overall
            except Exception as exc:
                logger.warning('MASTER SYNC PENDING: %s',exc)
                displayed=overall+' | MASTER PENDING'
            logger.info('END result=%s records=%s',overall,directory)
            self.q.put(('ok',displayed,rows,str(directory)))
        except Exception as exc:
            logger.exception('RUN ERROR (%s)',type(exc).__name__)
            (directory/'test.log').write_text('ERROR: inspection did not complete\n',encoding='utf-8')
            self.q.put(('error',type(exc).__name__+': '+str(exc),[],str(directory)))
        finally:
            if client:client.close()
    def poll(self):
        while not self.q.empty():
            kind,status,rows,path=self.q.get()
            if kind in ('sync','sync_error'):
                if kind=='sync':messagebox.showinfo('Master Sync','New rows appended: '+status)
                else:messagebox.showwarning('Master Sync Failed','Close Master Excel and retry.\n'+status)
                continue
            for r in rows:self.tree.insert('', 'end',values=tuple(r[k] for k in ('item','expected','actual','result')))
            self.last_run_dir=path
            self.status.set(status+' | '+path);self.btn.configure(state='normal')
            if kind=='error':messagebox.showerror('Inspection Error',status+'\n\nLogs: '+path)
        self.root.after(100,self.poll)

if __name__=='__main__':
    root=tk.Tk();App(root);root.mainloop()
