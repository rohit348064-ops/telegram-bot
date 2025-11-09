import os, sqlite3, uuid
from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading, requests, time, os

def web_server():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is running!")

    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()

def keep_alive():
    url = "https://telegram-bot-rohit348064.repl.co"
    while True:
        try:
            requests.get(url)
        except:
            pass
        time.sleep(240)

web_server()
threading.Thread(target=keep_alive, daemon=True).start()

TOKEN = (os.environ.get("BOT_TOKEN", "").strip() or (open("token.txt").read().strip() if os.path.exists("token.txt") else ""))
ADMIN_MASTER = 8303783205
ADMIN_MASTER = 8303783205
ADMIN_MASTER = 8303783205
JOIN_DEFAULTS = [("channel","https://t.me/+DgemL2yHDWVjNTI9","-1002807713488"),("group","https://t.me/+f9txcMDhgRs5ODk1","-1003000982225")]
REPORT_TARGET_DEFAULT = "-1003154444002"
PER_REF_DEFAULT = 5.0
JOIN_REWARD_DEFAULT = 1.0
MIN_WITHDRAW_DEFAULT = 10.0

conn = sqlite3.connect("database.db", check_same_thread=False)
cur = conn.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY, username TEXT, balance REAL DEFAULT 0, verified INTEGER DEFAULT 0, reward_claimed INTEGER DEFAULT 0, created_at TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS refs(referrer INTEGER, refereed INTEGER, created_at TEXT, PRIMARY KEY(referrer,refereed))")
cur.execute("CREATE TABLE IF NOT EXISTS withdraws(id TEXT PRIMARY KEY, user_id INTEGER, amount REAL, method TEXT, data TEXT, photo TEXT, status TEXT, requested_at TEXT, processed_by INTEGER, processed_at TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY, v TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS channels(kind TEXT, join_link TEXT, check_id TEXT, PRIMARY KEY(kind,check_id))")
cur.execute("CREATE TABLE IF NOT EXISTS promotions(id TEXT PRIMARY KEY, user_id INTEGER, channel_link TEXT, check_id TEXT, proof_photo TEXT, status TEXT, created_at TEXT, processed_by INTEGER, processed_at TEXT)")
conn.commit()

def sget(k, default=""):
    c = conn.cursor(); c.execute("SELECT v FROM settings WHERE k=?", (k,)); r = c.fetchone(); return r[0] if r else default
def sset(k, v):
    c = conn.cursor(); c.execute("INSERT OR REPLACE INTO settings(k,v) VALUES(?,?)",(k,str(v))); conn.commit()

def boot_defaults():
    if not sget("admins"): sset("admins", str(ADMIN_MASTER))
    if not sget("report_target"): sset("report_target", REPORT_TARGET_DEFAULT)
    if not sget("per_ref"): sset("per_ref", PER_REF_DEFAULT)
    if not sget("join_reward"): sset("join_reward", JOIN_REWARD_DEFAULT)
    if not sget("min_withdraw"): sset("min_withdraw", MIN_WITHDRAW_DEFAULT)
    if not sget("rules_text"): sset("rules_text","")
    c = conn.cursor(); c.execute("SELECT COUNT(*) FROM channels"); n = c.fetchone()[0]
    if n == 0:
        for kind,link,cid in JOIN_DEFAULTS:
            c.execute("INSERT OR IGNORE INTO channels(kind,join_link,check_id) VALUES(?,?,?)",(kind,link,cid))
        conn.commit()
boot_defaults()

def is_admin(uid):
    try:
        ids = [int(x) for x in str(sget("admins")).split(",") if x]
        return int(uid) in ids or int(uid) == int(ADMIN_MASTER)
    except:
        return False

def add_admin(uid):
    ids = [x for x in str(sget("admins")).split(",") if x]
    if str(uid) not in ids: ids.append(str(uid))
    sset("admins", ",".join(sorted(ids)))

def rm_admin(uid):
    ids = [x for x in str(sget("admins")).split(",") if x]
    ids = [x for x in ids if x != str(uid)]
    if not ids: ids = [str(ADMIN_MASTER)]
    sset("admins", ",".join(sorted(ids)))

def ensure_user(u):
    c = conn.cursor(); c.execute("SELECT 1 FROM users WHERE user_id=?", (u.id,))
    if not c.fetchone():
        c.execute("INSERT INTO users(user_id,username,created_at) VALUES(?,?,?)",(u.id, u.username or u.first_name or "", datetime.now(timezone.utc).isoformat()))
        conn.commit()

def user_row(uid):
    c = conn.cursor(); c.execute("SELECT user_id,username,balance,verified,reward_claimed FROM users WHERE user_id=?", (uid,))
    r = c.fetchone(); return None if not r else {"user_id":r[0],"username":r[1],"balance":float(r[2]),"verified":int(r[3]),"reward_claimed":int(r[4])}

def set_balance(uid, amt):
    c = conn.cursor(); c.execute("UPDATE users SET balance=? WHERE user_id=?", (float(amt), uid)); conn.commit()
def add_balance(uid, amt):
    c = conn.cursor(); c.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (float(amt), uid)); conn.commit()
def mark_verified(uid):
    c = conn.cursor(); c.execute("UPDATE users SET verified=1, reward_claimed=1 WHERE user_id=?", (uid,)); conn.commit()
def unverify(uid):
    c = conn.cursor(); c.execute("UPDATE users SET verified=0 WHERE user_id=?", (uid,)); conn.commit()

def channel_rows():
    c = conn.cursor(); c.execute("SELECT kind,join_link,check_id FROM channels"); return c.fetchall()

async def safe_get_member(bot, chat, uid):
    try:
        cid = int(chat) if str(chat).lstrip("-").isdigit() else chat
        return await bot.get_chat_member(cid, uid)
    except:
        return None

async def joined_everywhere(bot, uid):
    ok = True
    for _,_,check_id in channel_rows():
        m = await safe_get_member(bot, check_id, uid)
        status = str(getattr(m, "status", "left")) if m else "left"
        ok = ok and (status not in ("left","kicked"))
    return ok

def main_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Balance", callback_data="u_bal"), InlineKeyboardButton("👥 Referral", callback_data="u_ref")],
        [InlineKeyboardButton("🏦 Withdraw", callback_data="u_wd"), InlineKeyboardButton("✅ Verify", callback_data="u_verify")],
        [InlineKeyboardButton("📢 Promote Channel", callback_data="u_promote"), InlineKeyboardButton("📜 Rules", callback_data="u_rules")],
        [InlineKeyboardButton("🔄 Refresh", callback_data="u_refresh"), InlineKeyboardButton("⚙️ Admin", callback_data="a_panel")],
    ])

def verify_kb():
    rows = []
    for kind,link,_ in channel_rows():
        txt = "📢 Join Channel" if kind=="channel" else "💬 Join Group"
        rows.append([InlineKeyboardButton(txt, url=link)])
    rows.append([InlineKeyboardButton("🔁 Check Again", callback_data="u_verify")])
    return InlineKeyboardMarkup(rows)

def admin_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Manage Join", callback_data="a_manage_join")],
        [InlineKeyboardButton("💳 Rewards / MinWD", callback_data="a_rewards")],
        [InlineKeyboardButton("📣 Withdraw Report", callback_data="a_report")],
        [InlineKeyboardButton("📝 Rules Text", callback_data="a_rules")],
        [InlineKeyboardButton("👤 Admins", callback_data="a_admins")],
        [InlineKeyboardButton("📊 Users", callback_data="a_users"), InlineKeyboardButton("💸 Requests", callback_data="a_wq")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="a_bc")],
        [InlineKeyboardButton("📯 Promotions", callback_data="a_promos")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
    ])

def admin_join_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Channel", callback_data="aj_add_ch"), InlineKeyboardButton("➕ Add Group", callback_data="aj_add_gp")],
        [InlineKeyboardButton("🗑️ Remove", callback_data="aj_del"), InlineKeyboardButton("📃 List", callback_data="aj_list")],
        [InlineKeyboardButton("🔙 Back", callback_data="a_panel")]
    ])

def admin_rewards_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Set Join ₹", callback_data="ar_set_join"), InlineKeyboardButton("Set Ref ₹", callback_data="ar_set_ref")],
        [InlineKeyboardButton("Set Min Withdraw ₹", callback_data="ar_set_minwd")],
        [InlineKeyboardButton("🔙 Back", callback_data="a_panel")]
    ])

def admin_admins_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Admin", callback_data="aa_add"), InlineKeyboardButton("➖ Remove Admin", callback_data="aa_rm")],
        [InlineKeyboardButton("🔙 Back", callback_data="a_panel")]
    ])

def admin_promos_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📥 Pending", callback_data="p_list")],
        [InlineKeyboardButton("🔙 Back", callback_data="a_panel")]
    ])

async def try_auto_verify(bot, uid, udata):
    u = user_row(uid)
    already = bool(u and u["reward_claimed"])
    ok = await joined_everywhere(bot, uid)
    if ok:
        if not already:
            add_balance(uid, float(sget("join_reward", JOIN_REWARD_DEFAULT)))
        mark_verified(uid)
        ref_by = udata.get("ref_by")
        if ref_by and ref_by != uid:
            c = conn.cursor()
            try:
                c.execute("INSERT OR IGNORE INTO refs(referrer,refereed,created_at) VALUES(?,?,?)",(ref_by,uid,datetime.now(timezone.utc).isoformat())); conn.commit()
                add_balance(ref_by, float(sget("per_ref", PER_REF_DEFAULT)))
            except: pass
        return True
    else:
        if u and u["verified"]: unverify(uid)
        return False

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    ensure_user(u)
    if update.message and update.message.text:
        parts = update.message.text.split()
        if len(parts)>1:
            try:
                rid = int(parts[1])
                if rid!=u.id:
                    c = conn.cursor()
                    try:
                        c.execute("INSERT OR IGNORE INTO refs(referrer,refereed,created_at) VALUES(?,?,?)",(rid,u.id,datetime.now(timezone.utc).isoformat())); conn.commit()
                        add_balance(rid, float(sget("per_ref", PER_REF_DEFAULT))); context.user_data["ref_by"]=rid
                    except: pass
            except: pass
    ok = await try_auto_verify(context.bot, u.id, context.user_data)
    if ok: await update.message.reply_text("Verified", reply_markup=main_kb())
    else: await update.message.reply_text("Welcome\nJoin and verify.", reply_markup=verify_kb())

async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure_user(update.effective_user)
    await update.message.reply_text("Menu", reply_markup=main_kb())

async def on_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    uid = q.from_user.id; ensure_user(q.from_user)
    d = q.data
    if d=="u_bal":
        u = user_row(uid); b = u["balance"] if u else 0.0
        await q.message.reply_text(f"Balance: ₹{b:.2f}", reply_markup=main_kb()); return
    if d=="u_ref":
        me = await context.bot.get_me(); link = f"https://t.me/{me.username}?start={uid}"
        await q.message.reply_text(f"Referral Link:\n{link}\nPer referral ₹{sget('per_ref',PER_REF_DEFAULT)}", reply_markup=main_kb()); return
    if d=="u_rules":
        await q.message.reply_text(sget("rules_text",""), reply_markup=main_kb()); return
    if d=="u_refresh":
        await try_auto_verify(context.bot, uid, context.user_data)
        await q.message.reply_text("Refreshed.", reply_markup=main_kb()); return
    if d=="u_verify":
        ok = await try_auto_verify(context.bot, uid, context.user_data)
        if ok: await q.message.reply_text("Verified now.", reply_markup=main_kb()); return
        await q.message.reply_text("Join required, then press again.", reply_markup=verify_kb()); return
    if d=="u_wd":
        context.user_data["await_wd_amount"]=True
        await q.message.reply_text(f"Enter amount (min ₹{sget('min_withdraw',MIN_WITHDRAW_DEFAULT)})"); return
    if d=="u_promote":
        context.user_data["prom_wait_link"]=True
        await q.message.reply_text("Send your channel invite link."); return
    if d=="a_panel":
        if not is_admin(uid): await q.answer("Admin only", show_alert=True); return
        await q.message.reply_text("Admin", reply_markup=admin_kb()); return
    if d=="a_manage_join":
        if not is_admin(uid): return
        await q.message.reply_text("Manage Join", reply_markup=admin_join_kb()); return
    if d=="aj_list":
        if not is_admin(uid): return
        rows=channel_rows(); txt="No channels." if not rows else "\n".join([f"{k} | {cid} | {lnk}" for k,lnk,cid in rows])
        await q.message.reply_text(txt, reply_markup=admin_join_kb()); return
    if d=="aj_add_ch":
        if not is_admin(uid): return
        context.user_data["await_add_kind"]="channel"; context.user_data["await_add_link"]=True
        await q.message.reply_text("Send channel invite link."); return
    if d=="aj_add_gp":
        if not is_admin(uid): return
        context.user_data["await_add_kind"]="group"; context.user_data["await_add_link"]=True
        await q.message.reply_text("Send group invite link."); return
    if d=="aj_del":
        if not is_admin(uid): return
        context.user_data["await_del_check"]=True
        await q.message.reply_text("Send check ID (@username or -100..)."); return
    if d=="a_rewards":
        if not is_admin(uid): return
        await q.message.reply_text("Rewards / MinWD", reply_markup=admin_rewards_kb()); return
    if d=="ar_set_join":
        context.user_data["await_set_join"]=True; await q.message.reply_text("Send join reward ₹"); return
    if d=="ar_set_ref":
        context.user_data["await_set_ref"]=True; await q.message.reply_text("Send per referral ₹"); return
    if d=="ar_set_minwd":
        context.user_data["await_set_minwd"]=True; await q.message.reply_text("Send minimum withdraw ₹"); return
    if d=="a_report":
        if not is_admin(uid): return
        context.user_data["await_report"]=True; await q.message.reply_text("Send report chat id (@username or -100..)"); return
    if d=="a_rules":
        if not is_admin(uid): return
        context.user_data["await_rules"]=True; await q.message.reply_text("Send new rules text"); return
    if d=="a_admins":
        if not is_admin(uid): return
        await q.message.reply_text(f"Admins: {sget('admins')}", reply_markup=admin_admins_kb()); return
    if d=="aa_add":
        context.user_data["await_add_admin"]=True; await q.message.reply_text("Send user ID"); return
    if d=="aa_rm":
        context.user_data["await_rm_admin"]=True; await q.message.reply_text("Send user ID to remove"); return
    if d=="a_users":
        if not is_admin(uid): return
        c = conn.cursor(); c.execute("SELECT COUNT(*), SUM(balance) FROM users"); n,tot=c.fetchone(); tot=tot or 0.0
        await q.message.reply_text(f"Users: {n}\nTotal balance: ₹{tot:.2f}", reply_markup=admin_kb()); return
    if d=="a_wq":
        if not is_admin(uid): return
        c=conn.cursor(); c.execute("SELECT id,user_id,amount,method,data,photo,status,requested_at FROM withdraws WHERE status='pending' ORDER BY requested_at DESC")
        rows=c.fetchall()
        if not rows: await q.message.reply_text("No pending.", reply_markup=admin_kb()); return
        for wid,uidr,amt,mth,dta,ph,_,at in rows:
            kb=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Approve",callback_data=f"w_ok_{wid}")],[InlineKeyboardButton("❌ Reject",callback_data=f"w_no_{wid}")]])
            cap=f"{wid}\nUser:{uidr}\nAmt:₹{amt}\nMethod:{mth}\nData:{dta}\nAt:{at}"
            if ph:
                try: await q.message.reply_photo(ph, caption=cap, reply_markup=kb)
                except: await q.message.reply_text(cap, reply_markup=kb)
            else:
                await q.message.reply_text(cap, reply_markup=kb)
        return
    if d=="a_bc":
        if not is_admin(uid): return
        context.user_data["await_broadcast"]=True; await q.message.reply_text("Send broadcast text"); return
    if d=="a_promos":
        if not is_admin(uid): return
        await q.message.reply_text("Promotions", reply_markup=admin_promos_kb()); return
    if d=="p_list":
        if not is_admin(uid): return
        c=conn.cursor(); c.execute("SELECT id,user_id,channel_link,check_id,proof_photo,status,created_at FROM promotions WHERE status='pending' ORDER BY created_at DESC")
        rows=c.fetchall()
        if not rows: await q.message.reply_text("No pending promotions.", reply_markup=admin_kb()); return
        for pid,uidr,cl,chk,ph,st,at in rows:
            kb=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Approve",callback_data=f"p_ok_{pid}")],[InlineKeyboardButton("❌ Reject",callback_data=f"p_no_{pid}")]])
            cap=f"{pid}\nUser:{uidr}\nLink:{cl}\nCheck:{chk}\nAt:{at}"
            if ph:
                try: await q.message.reply_photo(ph, caption=cap, reply_markup=kb)
                except: await q.message.reply_text(cap, reply_markup=kb)
            else:
                await q.message.reply_text(cap, reply_markup=kb)
        return
    if d.startswith("p_ok_") or d.startswith("p_no_"):
        if not is_admin(uid): return
        pid=d.split("_",2)[2]; c=conn.cursor(); c.execute("SELECT user_id,channel_link,check_id,status FROM promotions WHERE id=?", (pid,)); r=c.fetchone()
        if not r: await q.message.reply_text("Not found.", reply_markup=admin_kb()); return
        uidr,cl,chk,st=r
        if st!="pending": await q.message.reply_text("Already processed.", reply_markup=admin_kb()); return
        if d.startswith("p_ok_"):
            c.execute("UPDATE promotions SET status='approved', processed_by=?, processed_at=? WHERE id=?", (uid, datetime.now(timezone.utc).isoformat(), pid))
            c.execute("INSERT OR IGNORE INTO channels(kind,join_link,check_id) VALUES(?,?,?)", ("channel", cl, chk)); conn.commit()
            try: await context.bot.send_message(uidr, "Your channel added for promotion.")
            except: pass
            await q.message.reply_text("Promotion approved", reply_markup=admin_kb())
        else:
            c.execute("UPDATE promotions SET status='rejected', processed_by=?, processed_at=? WHERE id=?", (uid, datetime.now(timezone.utc).isoformat(), pid)); conn.commit()
            try: await context.bot.send_message(uidr, "Promotion rejected.")
            except: pass
            await q.message.reply_text("Promotion rejected", reply_markup=admin_kb())
        return
    if d.startswith("w_ok_") or d.startswith("w_no_"):
        if not is_admin(uid): return
        wid=d.split("_",2)[2]; c=conn.cursor(); c.execute("SELECT user_id,amount,method,data,photo,status FROM withdraws WHERE id=?",(wid,)); r=c.fetchone()
        if not r: await q.message.reply_text("Not found.", reply_markup=admin_kb()); return
        uidr,amt,method,dta,ph,status=r
        if status!="pending": await q.message.reply_text("Already processed.", reply_markup=admin_kb()); return
        if d.startswith("w_ok_"):
            set_balance(uidr,0.0)
            c.execute("UPDATE withdraws SET status='approved', processed_by=?, processed_at=? WHERE id=?", (uid, datetime.now(timezone.utc).isoformat(), wid)); conn.commit()
            try: await context.bot.send_message(uidr, f"Payment Successful ₹{amt}")
            except: pass
            try:
                tgt=sget("report_target",REPORT_TARGET_DEFAULT)
                if ph: await context.bot.send_photo(tgt, ph, caption=f"Paid\nUser:{uidr}\nAmt:₹{amt}\nMethod:{method}\nData:{dta}\nID:{wid}")
                else: await context.bot.send_message(tgt, f"Paid\nUser:{uidr}\nAmt:₹{amt}\nMethod:{method}\nData:{dta}\nID:{wid}")
            except: pass
            await q.message.reply_text("Approved", reply_markup=admin_kb())
        else:
            c.execute("UPDATE withdraws SET status='rejected', processed_by=?, processed_at=? WHERE id=?", (uid, datetime.now(timezone.utc).isoformat(), wid)); conn.commit()
            try: await context.bot.send_message(uidr, f"Payment Rejected ₹{amt}")
            except: pass
            await q.message.reply_text("Rejected", reply_markup=admin_kb())
        return
    if d=="back_main":
        await q.message.reply_text("Back", reply_markup=main_kb()); return

async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id; t = (update.message.text or "").strip()
    ensure_user(update.effective_user)
    if context.user_data.get("await_wd_amount"):
        context.user_data.pop("await_wd_amount",None)
        try:
            amt=float(t); minv=float(sget("min_withdraw",MIN_WITHDRAW_DEFAULT))
            u=user_row(uid); bal=u["balance"] if u else 0.0
            if amt<minv: await update.message.reply_text(f"Min ₹{minv}", reply_markup=main_kb()); return
            if amt>bal: await update.message.reply_text("Insufficient balance", reply_markup=main_kb()); return
            context.user_data["wd_amount"]=amt
            kb=InlineKeyboardMarkup([[InlineKeyboardButton("Send UPI ID",callback_data="wd_m_upi"),InlineKeyboardButton("Send QR Photo",callback_data="wd_m_qr")]])
            await update.message.reply_text("Choose method", reply_markup=kb); return
        except:
            await update.message.reply_text("Send a number amount", reply_markup=main_kb()); return
    if context.user_data.get("await_report") and is_admin(uid):
        context.user_data.pop("await_report",None); sset("report_target", t)
        await update.message.reply_text("Saved.", reply_markup=admin_kb()); return
    if context.user_data.get("await_add_admin") and is_admin(uid):
        context.user_data.pop("await_add_admin",None)
        try: add_admin(int(t)); await update.message.reply_text("Admin added.", reply_markup=admin_admins_kb())
        except: await update.message.reply_text("Invalid id", reply_markup=admin_admins_kb())
        return
    if context.user_data.get("await_rm_admin") and is_admin(uid):
        context.user_data.pop("await_rm_admin",None)
        try: rm_admin(int(t)); await update.message.reply_text("Admin removed.", reply_markup=admin_admins_kb())
        except: await update.message.reply_text("Invalid id", reply_markup=admin_admins_kb())
        return
    if context.user_data.get("await_set_join") and is_admin(uid):
        context.user_data.pop("await_set_join",None)
        try: sset("join_reward", float(t)); await update.message.reply_text("Saved.", reply_markup=admin_rewards_kb())
        except: await update.message.reply_text("Send number"); return
    if context.user_data.get("await_set_ref") and is_admin(uid):
        context.user_data.pop("await_set_ref",None)
        try: sset("per_ref", float(t)); await update.message.reply_text("Saved.", reply_markup=admin_rewards_kb())
        except: await update.message.reply_text("Send number"); return
    if context.user_data.get("await_set_minwd") and is_admin(uid):
        context.user_data.pop("await_set_minwd",None)
        try: sset("min_withdraw", float(t)); await update.message.reply_text("Saved.", reply_markup=admin_rewards_kb())
        except: await update.message.reply_text("Send number"); return
    if context.user_data.get("await_add_link") and is_admin(uid):
        context.user_data.pop("await_add_link",None); context.user_data["new_join_link"]=t; context.user_data["await_add_check"]=True
        await update.message.reply_text("Send check id or @username"); return
    if context.user_data.get("await_add_check") and is_admin(uid):
        context.user_data.pop("await_add_check",None)
        kind=context.user_data.pop("await_add_kind","channel"); link=context.user_data.pop("new_join_link","")
        c=conn.cursor(); c.execute("INSERT OR IGNORE INTO channels(kind,join_link,check_id) VALUES(?,?,?)",(kind,link,t)); conn.commit()
        await update.message.reply_text("Saved.", reply_markup=admin_join_kb()); return
    if context.user_data.get("await_del_check") and is_admin(uid):
        context.user_data.pop("await_del_check",None)
        c=conn.cursor(); c.execute("DELETE FROM channels WHERE check_id=?", (t,)); conn.commit()
        await update.message.reply_text("Removed.", reply_markup=admin_join_kb()); return
    if context.user_data.get("await_broadcast") and is_admin(uid):
        context.user_data.pop("await_broadcast",None)
        c=conn.cursor(); c.execute("SELECT user_id FROM users"); ids=[r[0] for r in c.fetchall()]
        ok=0
        for i in ids:
            try:
                await context.bot.send_message(i, t); ok+=1
            except: pass
        await update.message.reply_text(f"Sent: {ok}", reply_markup=admin_kb()); return
    if context.user_data.get("await_rules") and is_admin(uid):
        context.user_data.pop("await_rules",None); sset("rules_text", t)
        await update.message.reply_text("Rules updated.", reply_markup=admin_kb()); return
    if context.user_data.get("prom_wait_link"):
        context.user_data.pop("prom_wait_link",None); context.user_data["prom_link"]=t; context.user_data["prom_wait_check"]=True
        await update.message.reply_text("Send channel check ID (@username or -100..)"); return
    if context.user_data.get("prom_wait_check"):
        context.user_data.pop("prom_wait_check",None); context.user_data["prom_check"]=t; context.user_data["prom_wait_proof"]=True
        await update.message.reply_text("Send payment proof photo"); return
    if context.user_data.get("await_add_admin") or context.user_data.get("await_rm_admin"): return

async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id; ensure_user(update.effective_user)
    ph = update.message.photo[-1].file_id if update.message.photo else None
    if context.user_data.get("prom_wait_proof"):
        context.user_data.pop("prom_wait_proof",None)
        link=context.user_data.pop("prom_link",""); chk=context.user_data.pop("prom_check","")
        pid=str(uuid.uuid4())
        c=conn.cursor(); c.execute("INSERT OR REPLACE INTO promotions(id,user_id,channel_link,check_id,proof_photo,status,created_at) VALUES(?,?,?,?,?,?,?)",(pid,uid,link,chk,ph,"pending",datetime.now(timezone.utc).isoformat())); conn.commit()
        await update.message.reply_text("Promotion request submitted. Wait for approval.", reply_markup=main_kb()); return
    if context.user_data.get("wd_wait_qr"):
        context.user_data.pop("wd_wait_qr",None)
        amt=context.user_data.pop("wd_amount",0)
        wid=str(uuid.uuid4()); c=conn.cursor()
        c.execute("INSERT OR REPLACE INTO withdraws(id,user_id,amount,method,data,photo,status,requested_at) VALUES(?,?,?,?,?,?,?,?)",(wid,uid,amt,"qr","",ph,"pending",datetime.now(timezone.utc).isoformat())); conn.commit()
        await update.message.reply_text("Withdraw request submitted.", reply_markup=main_kb()); return

async def on_cb2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; d=q.data; uid=q.from_user.id
    if d=="wd_m_upi":
        context.user_data["wd_wait_upi"]=True
        await q.message.reply_text("Send your UPI ID"); return
    if d=="wd_m_qr":
        context.user_data["wd_wait_qr"]=True
        await q.message.reply_text("Send QR screenshot/photo"); return

async def on_text2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id; t=(update.message.text or "").strip()
    if context.user_data.get("wd_wait_upi"):
        context.user_data.pop("wd_wait_upi",None)
        amt=context.user_data.pop("wd_amount",0)
        wid=str(uuid.uuid4()); c=conn.cursor()
        c.execute("INSERT OR REPLACE INTO withdraws(id,user_id,amount,method,data,photo,status,requested_at) VALUES(?,?,?,?,?,?,?,?)",(wid,uid,amt,"upi",t,"","pending",datetime.now(timezone.utc).isoformat())); conn.commit()
        await update.message.reply_text("Withdraw request submitted.", reply_markup=main_kb()); return

async def on_text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await on_text(update, context)
    await on_text2(update, context)

async def on_cb_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await on_cb(update, context)
    await on_cb2(update, context)

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", cmd_start))
app.add_handler(CommandHandler("menu", cmd_menu))
app.add_handler(CallbackQueryHandler(on_cb_router))
app.add_handler(MessageHandler(filters.PHOTO, on_photo))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text_router))
app.run_polling()