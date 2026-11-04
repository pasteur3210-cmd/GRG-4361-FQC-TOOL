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

APP='GRG-4361 FQC Test Tool V1.0.2'

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

def save_record(directory,overall,rows,details):
    now=dt.datetime.now().astimezone().isoformat(timespec='seconds')
    payload={'timestamp':now,'overall':overall,'results':rows,'details':details}
    (directory/'result.json').write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding='utf-8')
    with (directory/'test.log').open('w',encoding='utf-8') as f:
        f.write(f'{now} Overall: {overall}\n')
        for row in rows: f.write(f"{row['item']} | {row['expected']} | {row['actual']} | {row['result']}\n")
    wb=Workbook(); ws=wb.active; ws.title='FQC Result'
    ws.append(['GRG-4361 FQC Test Tool V1.0.2',now,overall]);ws.append(['Test Item','Expected','Actual','Result'])
    for row in rows:ws.append([row[k] for k in ('item','expected','actual','result')])
    ws.freeze_panes='A3';ws.auto_filter.ref=f'A2:D{ws.max_row}'
    for col,width in {'A':31,'B':44,'C':41,'D':17}.items():ws.column_dimensions[col].width=width
    wb.save(directory/'FQC_Result.xlsx')

class App:
    def __init__(self,root):
        self.root=root;root.title(APP);root.geometry('1120x740');root.minsize(840,540)
        self.q=queue.Queue();self.host=tk.StringVar(value='192.168.1.1');self.user=tk.StringVar(value='root')
        self.pw=tk.StringVar();self.sn=tk.StringVar();self.fw=tk.StringVar();self.status=tk.StringVar(value='Ready — read-only mode')
        top=ttk.Frame(root,padding=12);top.pack(fill='x')
        for label,var,width in [('Router IP',self.host,18),('Username',self.user,16),('Password',self.pw,18),('DUT SN',self.sn,24),('Approved FW',self.fw,18)]:
            cell=ttk.Frame(top);cell.pack(side='left',padx=4)
            ttk.Label(cell,text=label).pack(anchor='w')
            ttk.Entry(cell,textvariable=var,width=width,show='*' if label=='Password' else '').pack()
        bar=ttk.Frame(root,padding=(14,2));bar.pack(fill='x')
        self.btn=ttk.Button(bar,text='START READ-ONLY CHECK',command=self.start);self.btn.pack(side='left')
        ttk.Button(bar,text='OPEN RECORDS',command=self.open_records).pack(side='left',padx=8)
        ttk.Button(bar,text='OPEN LAST RUN LOGS',command=self.open_last_logs).pack(side='left',padx=4)
        self.last_run_dir=None
        ttk.Label(bar,textvariable=self.status).pack(side='left',padx=18)
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
    def start(self):
        if not self.host.get().strip() or not self.pw.get():messagebox.showwarning('Missing input','Router IP and password are required.');return
        self.btn.configure(state='disabled');self.status.set('Connecting...');self.tree.delete(*self.tree.get_children())
        values=(self.host.get().strip(),self.user.get().strip(),self.pw.get(),self.sn.get().strip(),self.fw.get().strip())
        threading.Thread(target=self.work,args=values,daemon=True).start()
    def work(self,host,user,password,sn,fw):
        stamp=dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        directory=ROOT/stamp;client=None
        try:
            logger=make_logger(directory)
        except OSError as exc:
            self.q.put(('error','Cannot write Records next to EXE: '+str(exc),[],str(directory)))
            return
        try:
            logger.info('START router=%s  mode=READ_ONLY',host)
            def safe_debug(msg):
                msg=re.sub(r'(?i)(password|cookie|csrf|token|authorization)([^\s]*)',r'[REDACTED]',str(msg))
                logger.debug(msg)
            client=Inspector(host,safe_debug)
            logger.info('HTTP login and read-only verification started')
            overall,rows,details=client.run(user,password,sn,fw)
            for row in rows:
                logger.info('TEST %s | expected=%s | actual=%s | result=%s',row['item'],row['expected'],row['actual'],row['result'])
            save_record(directory,overall,rows,details)
            logger.info('END result=%s records=%s',overall,directory)
            self.q.put(('ok',overall,rows,str(directory)))
        except Exception as exc:
            logger.exception('RUN ERROR (%s)',type(exc).__name__)
            (directory/'test.log').write_text('ERROR: inspection did not complete\n',encoding='utf-8')
            self.q.put(('error',type(exc).__name__+': '+str(exc),[],str(directory)))
        finally:
            if client:client.close()
    def poll(self):
        while not self.q.empty():
            kind,status,rows,path=self.q.get()
            for r in rows:self.tree.insert('', 'end',values=tuple(r[k] for k in ('item','expected','actual','result')))
            self.last_run_dir=path
            self.status.set(status+' | '+path);self.btn.configure(state='normal')
            if kind=='error':messagebox.showerror('Inspection Error',status+'\n\nLogs: '+path)
        self.root.after(100,self.poll)

if __name__=='__main__':
    root=tk.Tk();App(root);root.mainloop()
