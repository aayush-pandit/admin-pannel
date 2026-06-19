# === IS CODE KO SERVER.PY KE SABSE UPAR (LINE 1 PAR) PASTE KAREIN ===
import sys
import os

# Termux/Android path issue ko fix karne ke liye
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)
# ===================================================================

import datetime
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from config.database import Base, engine, get_db
from models.admin_model import Admin, User, Worker, Booking, AuditLog
from routes.auth_route import router as auth_router
from middleware.jwt_auth import get_current_admin
from services.bcrypt_service import BcryptService

# Auto create database schema on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Mistri Adda Admin Panel")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")

# Database initializer (Startup Seed Data)
@app.on_event("startup")
def startup_db_seed():
    db = next(get_db())
    # Create Default Admin if empty
    admin_exists = db.query(Admin).first()
    if not admin_exists:
        hashed_pwd = BcryptService.hash_password("admin123")
        default_admin = Admin(username="admin", email="admin@mistriadda.com", hashed_password=hashed_pwd, role="super_admin")
        db.add(default_admin)
        db.commit()

    # Seed Mock Users if empty
    if not db.query(User).first():
        users = [
            User(name="Aman Sharma", email="aman@example.com", phone="9876543210", status="active", kyc_status="verified"),
            User(name="Vikram Singh", email="vikram@example.com", phone="8765432109", status="active", kyc_status="verified"),
            User(name="Rahul Verma", email="rahul@example.com", phone="7654321098", status="suspended", kyc_status="pending")
        ]
        db.add_all(users)
        db.commit()

    # Seed Mock Workers if empty
    if not db.query(Worker).first():
        workers = [
            Worker(name="Ramesh Kumar", email="ramesh@example.com", phone="9988776655", skill_category="Electrician", status="active", kyc_status="verified", rating=4.8, completed_jobs=24),
            Worker(name="Sohan Lal", email="sohan@example.com", phone="8877665544", skill_category="Plumber", status="pending", kyc_status="pending", rating=4.2, completed_jobs=12),
            Worker(name="Karan Mistri", email="karan@example.com", phone="7766554433", skill_category="Mason", status="active", kyc_status="verified", rating=4.9, completed_jobs=40)
        ]
        db.add_all(workers)
        db.commit()

    # Seed Mock Bookings if empty
    if not db.query(Booking).first():
        bookings = [
            Booking(user_id=1, worker_id=1, status="completed", payment_status="paid", total_amount=450.0),
            Booking(user_id=2, worker_id=3, status="assigned", payment_status="pending", total_amount=1200.0)
        ]
        db.add_all(bookings)
        db.commit()
    db.close()


# Core Analytics Dashboard APIs
@app.get("/api/dashboard/stats")
def get_dashboard_stats(db: Session = Depends(get_db), current_admin: Admin = Depends(get_current_admin)):
    u_count = db.query(User).count()
    w_count = db.query(Worker).count()
    b_count = db.query(Booking).count()
    
    # Calculate revenue safely
    revenue_sum = db.query(Booking).filter(Booking.payment_status == "paid").all()
    total_rev = sum(b.total_amount for b in revenue_sum)

    # Fetch recent active items
    recent_logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(5).all()

    return {
        "total_users": u_count,
        "total_workers": w_count,
        "total_bookings": b_count,
        "total_revenue": total_rev,
        "recent_activities": [{"action": l.action, "details": l.details, "time": l.created_at.strftime("%Y-%m-%d %H:%M:%S")} for l in recent_logs]
    }

# --- USER MANAGEMENT APIs ---
@app.get("/api/users")
def list_users(db: Session = Depends(get_db), current_admin: Admin = Depends(get_current_admin)):
    return db.query(User).all()

@app.post("/api/users/{user_id}/status")
def change_user_status(user_id: int, status: str, db: Session = Depends(get_db), current_admin: Admin = Depends(get_current_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.status = status
    db.commit()
    return {"message": f"User status updated to {status}"}

@app.delete("/api/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_admin: Admin = Depends(get_current_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
         raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully."}

# --- WORKER MANAGEMENT APIs ---
@app.get("/api/workers")
def list_workers(db: Session = Depends(get_db), current_admin: Admin = Depends(get_current_admin)):
    return db.query(Worker).all()

@app.post("/api/workers/{worker_id}/approve")
def approve_worker(worker_id: int, db: Session = Depends(get_db), current_admin: Admin = Depends(get_current_admin)):
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    worker.status = "active"
    worker.kyc_status = "verified"
    db.commit()
    return {"message": "Worker approved and verified successfully"}

@app.post("/api/workers/{worker_id}/status")
def change_worker_status(worker_id: int, status: str, db: Session = Depends(get_db), current_admin: Admin = Depends(get_current_admin)):
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    worker.status = status
    db.commit()
    return {"message": f"Worker status changed to {status}"}

# --- AUDIT LOGS ---
@app.get("/api/audit-logs")
def get_audit_logs(db: Session = Depends(get_db), current_admin: Admin = Depends(get_current_admin)):
    return db.query(AuditLog).order_by(AuditLog.id.desc()).all()


# --- INTERACTIVE DASHBOARD FRONTEND UI (Embedded Single-Page Webpage) ---
@app.get("/", response_class=HTMLResponse)
def serve_dashboard_ui():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Mistri Adda - Premium Admin Panel</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    </head>
    <body class="bg-slate-900 text-slate-100 font-sans min-h-screen">

        <!-- LOGIN MODAL SCREEN -->
        <div id="login-screen" class="fixed inset-0 bg-slate-950 flex justify-center items-center z-50">
            <div class="bg-slate-800 p-8 rounded-xl shadow-2xl w-full max-w-md border border-orange-500/30">
                <div class="text-center mb-6">
                    <h1 class="text-orange-500 font-bold text-3xl tracking-wide"><i class="fa-solid fa-wrench mr-2"></i>MISTRI ADDA</h1>
                    <p class="text-slate-400 text-sm mt-1">Administrative Control System</p>
                </div>
                <div class="space-y-4">
                    <div>
                        <label class="block text-xs font-semibold uppercase text-slate-400 mb-1">Username</label>
                        <input id="login-username" type="text" placeholder="Enter username (Default: admin)" class="w-full px-4 py-2.5 bg-slate-700 text-white rounded focus:outline-none focus:ring-2 focus:ring-orange-500">
                    </div>
                    <div>
                        <label class="block text-xs font-semibold uppercase text-slate-400 mb-1">Password</label>
                        <input id="login-password" type="password" placeholder="Enter password (Default: admin123)" class="w-full px-4 py-2.5 bg-slate-700 text-white rounded focus:outline-none focus:ring-2 focus:ring-orange-500">
                    </div>
                    <button onclick="performLogin()" class="w-full py-3 mt-2 bg-gradient-to-r from-orange-600 to-amber-500 hover:from-orange-500 hover:to-amber-400 font-bold rounded shadow transition-all">SIGN IN TO PANEL</button>
                    <p id="login-error" class="text-red-500 text-sm text-center hidden mt-2"></p>
                </div>
            </div>
        </div>

        <!-- MAIN PANEL DASHBOARD PAGE -->
        <div id="main-panel" class="hidden flex min-h-screen">
            
            <!-- Sidebar Navigation -->
            <aside class="w-64 bg-slate-950 border-r border-slate-800 flex flex-col justify-between shrink-0">
                <div>
                    <div class="p-5 border-b border-slate-800">
                        <h2 class="text-orange-500 font-bold text-xl tracking-wider"><i class="fa-solid fa-wrench mr-2"></i>MISTRI ADDA</h2>
                        <span class="text-xs text-emerald-400"><i class="fa-solid fa-circle text-[8px] mr-1 animate-pulse"></i> Admin Engine Running</span>
                    </div>
                    <nav class="p-4 space-y-2">
                        <button onclick="switchTab('dashboard')" class="tab-btn w-full text-left py-2.5 px-4 rounded font-medium flex items-center bg-slate-800 text-orange-500"><i class="fa-solid fa-chart-line w-6"></i> Dashboard</button>
                        <button onclick="switchTab('users')" class="tab-btn w-full text-left py-2.5 px-4 rounded font-medium flex items-center text-slate-400 hover:bg-slate-900 hover:text-slate-100"><i class="fa-solid fa-users w-6"></i> Manage Users</button>
                        <button onclick="switchTab('workers')" class="tab-btn w-full text-left py-2.5 px-4 rounded font-medium flex items-center text-slate-400 hover:bg-slate-900 hover:text-slate-100"><i class="fa-solid fa-user-ninja w-6"></i> Manage Workers</button>
                        <button onclick="switchTab('audit')" class="tab-btn w-full text-left py-2.5 px-4 rounded font-medium flex items-center text-slate-400 hover:bg-slate-900 hover:text-slate-100"><i class="fa-solid fa-shield-halved w-6"></i> Audit Logging</button>
                    </nav>
                </div>
                <div class="p-4 border-t border-slate-800 flex items-center justify-between">
                    <div>
                        <p class="text-xs text-slate-400">Logged in as:</p>
                        <p class="text-sm font-bold text-slate-200" id="current-user-display">Admin</p>
                    </div>
                    <button onclick="performLogout()" class="text-red-500 hover:text-red-400 p-2"><i class="fa-solid fa-power-off text-lg"></i></button>
                </div>
            </aside>

            <!-- Workspace Content area -->
            <main class="flex-1 p-8 overflow-y-auto">

                <!-- TAB 1: DASHBOARD ANALYTICS OVERVIEW -->
                <div id="tab-dashboard" class="space-y-6">
                    <div class="flex items-center justify-between mb-2">
                        <h1 class="text-2xl font-bold tracking-tight">Main Analytics Engine</h1>
                        <span id="update-indicator" class="text-xs text-slate-400">Status: Realtime Auto-sync Active</span>
                    </div>

                    <!-- Metrics Grid -->
                    <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
                        <div class="bg-slate-800/80 p-6 rounded-xl border border-slate-700">
                            <p class="text-slate-400 text-sm font-semibold uppercase">Total Users Active</p>
                            <h3 class="text-3xl font-extrabold mt-1 text-slate-50" id="stat-users">0</h3>
                        </div>
                        <div class="bg-slate-800/80 p-6 rounded-xl border border-slate-700">
                            <p class="text-slate-400 text-sm font-semibold uppercase">Registered Workers</p>
                            <h3 class="text-3xl font-extrabold mt-1 text-orange-400" id="stat-workers">0</h3>
                        </div>
                        <div class="bg-slate-800/80 p-6 rounded-xl border border-slate-700">
                            <p class="text-slate-400 text-sm font-semibold uppercase">Completed Bookings</p>
                            <h3 class="text-3xl font-extrabold mt-1 text-amber-400" id="stat-bookings">0</h3>
                        </div>
                        <div class="bg-slate-800/80 p-6 rounded-xl border border-slate-700">
                            <p class="text-slate-400 text-sm font-semibold uppercase">Total Platform Revenue</p>
                            <h3 class="text-3xl font-extrabold mt-1 text-emerald-400" id="stat-revenue">₹0</h3>
                        </div>
                    </div>

                    <!-- Activity History Log -->
                    <div class="bg-slate-800/50 rounded-xl p-6 border border-slate-700">
                        <h2 class="text-lg font-bold mb-4">Recent Audit Actions</h2>
                        <div class="space-y-3" id="recent-logs-list">
                            <!-- Populated dynamically via endpoint -->
                        </div>
                    </div>
                </div>

                <!-- TAB 2: USER MANAGEMENT -->
                <div id="tab-users" class="hidden space-y-6">
                    <h1 class="text-2xl font-bold">User Management System</h1>
                    <div class="bg-slate-800 border border-slate-700 rounded-xl overflow-hidden shadow">
                        <table class="w-full text-left">
                            <thead class="bg-slate-700 text-xs font-semibold uppercase text-slate-300">
                                <tr>
                                    <th class="p-4">User Name</th>
                                    <th class="p-4">Email</th>
                                    <th class="p-4">Phone</th>
                                    <th class="p-4">Verification</th>
                                    <th class="p-4">Account Status</th>
                                    <th class="p-4 text-right">Perform actions</th>
                                </tr>
                            </thead>
                            <tbody id="users-table-body" class="divide-y divide-slate-700 text-sm">
                                <!-- User records dynamically placed here -->
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- TAB 3: WORKER MANAGEMENT -->
                <div id="tab-workers" class="hidden space-y-6">
                    <h1 class="text-2xl font-bold">Worker Verification Desk</h1>
                    <div class="bg-slate-800 border border-slate-700 rounded-xl overflow-hidden shadow">
                        <table class="w-full text-left">
                            <thead class="bg-slate-700 text-xs font-semibold uppercase text-slate-300">
                                <tr>
                                    <th class="p-4">Worker details</th>
                                    <th class="p-4">Category</th>
                                    <th class="p-4">KYC Review</th>
                                    <th class="p-4">Rating</th>
                                    <th class="p-4">Jobs</th>
                                    <th class="p-4">Status</th>
                                    <th class="p-4 text-right">Moderator Control</th>
                                </tr>
                            </thead>
                            <tbody id="workers-table-body" class="divide-y divide-slate-700 text-sm">
                                <!-- Worker records dynamically placed here -->
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- TAB 4: AUDIT LOGS -->
                <div id="tab-audit" class="hidden space-y-6">
                    <h1 class="text-2xl font-bold">System Audit Logs</h1>
                    <div class="bg-slate-800/80 rounded-xl p-6 border border-slate-700">
                        <div class="space-y-4 max-h-[500px] overflow-y-auto pr-2" id="full-audit-logs">
                            <!-- Populated dynamically -->
                        </div>
                    </div>
                </div>

            </main>
        </div>

        <!-- CONTROL LOGIC FOR FRONTEND OPERATIONS -->
        <script>
            let currentToken = localStorage.getItem("admin_token") || "";

            window.onload = function() {
                if (currentToken) {
                    showMainPanel();
                } else {
                    document.getElementById("login-screen").classList.remove("hidden");
                }
            };

            function getAuthHeaders() {
                return {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${currentToken}`
                };
            }

            async function performLogin() {
                const user = document.getElementById("login-username").value;
                const pass = document.getElementById("login-password").value;
                const err = document.getElementById("login-error");

                try {
                    const res = await fetch("/api/auth/login", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ username: user, password: pass })
                    });
                    if (!res.ok) throw new Error("Invalid username/password combinations.");
                    const data = await res.json();
                    
                    currentToken = data.access_token;
                    localStorage.setItem("admin_token", currentToken);
                    document.getElementById("current-user-display").innerText = data.username;
                    showMainPanel();
                } catch(e) {
                    err.innerText = e.message;
                    err.classList.remove("hidden");
                }
            }

            function performLogout() {
                localStorage.removeItem("admin_token");
                currentToken = "";
                document.getElementById("main-panel").classList.add("hidden");
                document.getElementById("login-screen").classList.remove("hidden");
            }

            function showMainPanel() {
                document.getElementById("login-screen").classList.add("hidden");
                document.getElementById("main-panel").classList.remove("hidden");
                fetchStats();
            }

            function switchTab(tabId) {
                // Hide all tabs
                document.getElementById("tab-dashboard").classList.add("hidden");
                document.getElementById("tab-users").classList.add("hidden");
                document.getElementById("tab-workers").classList.add("hidden");
                document.getElementById("tab-audit").classList.add("hidden");

                // Deactivate buttons
                document.querySelectorAll(".tab-btn").forEach(btn => {
                    btn.classList.remove("bg-slate-800", "text-orange-500");
                    btn.classList.add("text-slate-400");
                });

                // Show active tab
                document.getElementById("tab-" + tabId).classList.remove("hidden");
                event.currentTarget.classList.add("bg-slate-800", "text-orange-500");

                if (tabId === 'dashboard') fetchStats();
                if (tabId === 'users') fetchUsers();
                if (tabId === 'workers') fetchWorkers();
                if (tabId === 'audit') fetchAuditLogs();
            }

            // Fetch Dashboard Level Statistics
            async function fetchStats() {
                try {
                    const res = await fetch("/api/dashboard/stats", { headers: getAuthHeaders() });
                    if(res.status === 401) return performLogout();
                    const d = await res.json();
                    
                    document.getElementById("stat-users").innerText = d.total_users;
                    document.getElementById("stat-workers").innerText = d.total_workers;
                    document.getElementById("stat-bookings").innerText = d.total_bookings;
                    document.getElementById("stat-revenue").innerText = "₹" + d.total_revenue;

                    let logsHtml = "";
                    d.recent_activities.forEach(log => {
                        logsHtml += `
                            <div class="flex items-center justify-between p-3 bg-slate-800 rounded border-l-4 border-orange-500">
                                <div>
                                    <p class="font-bold text-slate-100 text-sm">${log.action}</p>
                                    <p class="text-xs text-slate-400 mt-0.5">${log.details}</p>
                                </div>
                                <span class="text-xs text-slate-500">${log.time}</span>
                            </div>
                        `;
                    });
                    document.getElementById("recent-logs-list").innerHTML = logsHtml || "<p class='text-sm text-slate-500'>No active logs stored yet.</p>";
                } catch(e) { console.error(e); }
            }

            // Fetch User Management lists
            async function fetchUsers() {
                try {
                    const res = await fetch("/api/users", { headers: getAuthHeaders() });
                    const users = await res.json();
                    let html = "";
                    users.forEach(u => {
                        let statusColor = u.status === 'active' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400';
                        html += `
                            <tr class="hover:bg-slate-700/30">
                                <td class="p-4 font-semibold text-slate-100">${u.name}</td>
                                <td class="p-4 text-slate-300">${u.email}</td>
                                <td class="p-4 text-slate-300">${u.phone}</td>
                                <td class="p-4">
                                    <span class="px-2.5 py-1 text-xs font-semibold rounded bg-blue-500/20 text-blue-400">${u.kyc_status}</span>
                                </td>
                                <td class="p-4">
                                    <span class="px-2.5 py-1 text-xs font-semibold rounded ${statusColor}">${u.status}</span>
                                </td>
                                <td class="p-4 text-right space-x-2">
                                    <button onclick="updateUserStatus(${u.id}, 'active')" class="text-emerald-500 hover:text-emerald-400 text-xs font-bold mr-1"><i class="fa-solid fa-check"></i> Unblock</button>
                                    <button onclick="updateUserStatus(${u.id}, 'blocked')" class="text-red-500 hover:text-red-400 text-xs font-bold mr-1"><i class="fa-solid fa-ban"></i> Block</button>
                                    <button onclick="deleteUser(${u.id})" class="text-slate-400 hover:text-red-500 text-xs"><i class="fa-solid fa-trash"></i></button>
                                </td>
                            </tr>
                        `;
                    });
                    document.getElementById("users-table-body").innerHTML = html || "<tr><td colspan='6' class='p-4 text-center'>No Users on platform</td></tr>";
                } catch(e) { console.error(e); }
            }

            async function updateUserStatus(userId, status) {
                if(confirm(`Are you sure you want to set user state as: ${status}?`)) {
                    await fetch(`/api/users/${userId}/status?status=${status}`, { method: "POST", headers: getAuthHeaders() });
                    fetchUsers();
                }
            }

            async function deleteUser(userId) {
                if(confirm("Confirm action: permanently delete User database metadata?")) {
                    await fetch(`/api/users/${userId}`, { method: "DELETE", headers: getAuthHeaders() });
                    fetchUsers();
                }
            }

            // Fetch Worker Management list
            async function fetchWorkers() {
                try {
                    const res = await fetch("/api/workers", { headers: getAuthHeaders() });
                    const workers = await res.json();
                    let html = "";
                    workers.forEach(w => {
                        let statusColor = w.status === 'active' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400';
                        html += `
                            <tr class="hover:bg-slate-700/30">
                                <td class="p-4">
                                    <div class="font-semibold text-slate-100">${w.name}</div>
                                    <div class="text-xs text-slate-400">${w.email} | ${w.phone}</div>
                                </td>
                                <td class="p-4 text-slate-300 font-medium">${w.skill_category}</td>
                                <td class="p-4">
                                    <span class="px-2.5 py-1 text-xs font-semibold rounded ${w.kyc_status === 'verified' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-yellow-500/20 text-yellow-400'}">${w.kyc_status}</span>
                                </td>
                                <td class="p-4 font-bold text-amber-400">${w.rating} ★</td>
                                <td class="p-4 text-slate-300">${w.completed_jobs}</td>
                                <td class="p-4">
                                    <span class="px-2.5 py-1 text-xs font-semibold rounded ${statusColor}">${w.status}</span>
                                </td>
                                <td class="p-4 text-right space-x-2">
                                    <button onclick="approveWorker(${w.id})" class="bg-emerald-600 hover:bg-emerald-500 text-white px-3 py-1 rounded text-xs font-bold">Verify & Approve</button>
                                    <button onclick="updateWorkerStatus(${w.id}, 'blocked')" class="bg-red-600/30 hover:bg-red-500/50 text-red-400 px-3 py-1 rounded text-xs">Block</button>
                                </td>
                            </tr>
                        `;
                    });
                    document.getElementById("workers-table-body").innerHTML = html || "<tr><td colspan='7' class='p-4 text-center'>No active service workers recorded.</td></tr>";
                } catch(e) { console.error(e); }
            }

            async function approveWorker(workerId) {
                await fetch(`/api/workers/${workerId}/approve`, { method: "POST", headers: getAuthHeaders() });
                fetchWorkers();
            }

            async function updateWorkerStatus(workerId, status) {
                await fetch(`/api/workers/${workerId}/status?status=${status}`, { method: "POST", headers: getAuthHeaders() });
                fetchWorkers();
            }

            // Fetch Audit logging history lists
            async function fetchAuditLogs() {
                try {
                    const res = await fetch("/api/audit-logs", { headers: getAuthHeaders() });
                    const logs = await res.json();
                    let html = "";
                    logs.forEach(log => {
                        html += `
                            <div class="flex flex-col p-4 bg-slate-800 rounded border border-slate-700">
                                <div class="flex justify-between">
                                    <span class="font-bold text-slate-100">${log.action}</span>
                                    <span class="text-xs text-slate-500">${new Date(log.created_at).toLocaleString()}</span>
                                </div>
                                <p class="text-sm text-slate-400 mt-1">${log.details || 'No additional details provided'}</p>
                                ${log.ip_address ? `<span class="text-[10px] text-orange-400 font-semibold mt-1">Source IP: ${log.ip_address}</span>` : ''}
                            </div>
                        `;
                    });
                    document.getElementById("full-audit-logs").innerHTML = html || "<p class='text-slate-500 text-center'>No system events saved yet.</p>";
                } catch(e) { console.error(e); }
            }
        </script>
    </body>
    </html>
    """