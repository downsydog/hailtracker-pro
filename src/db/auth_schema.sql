-- ============================================================================
-- AUTHENTICATION & USER MANAGEMENT SCHEMA
-- ============================================================================

-- USERS TABLE (enhanced)
DROP TABLE IF EXISTS users;
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'sales',  -- 'admin', 'manager', 'sales', 'technician'
    phone TEXT,
    company_id INTEGER,
    active BOOLEAN DEFAULT 1,
    email_verified BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    login_count INTEGER DEFAULT 0,
    reset_token TEXT,
    reset_token_expires TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_active ON users(active);

-- COMPANIES TABLE
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    subscription_plan TEXT DEFAULT 'basic',  -- 'basic', 'professional', 'enterprise'
    subscription_status TEXT DEFAULT 'trial',  -- 'trial', 'active', 'cancelled', 'expired'
    max_users INTEGER DEFAULT 5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    trial_ends_at TIMESTAMP,
    billing_email TEXT,
    phone TEXT,
    address TEXT,
    city TEXT,
    state TEXT,
    zip_code TEXT
);

-- SESSIONS TABLE
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    session_token TEXT UNIQUE NOT NULL,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX idx_sessions_token ON sessions(session_token);
CREATE INDEX idx_sessions_user ON sessions(user_id);

-- AUDIT LOG TABLE
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    resource_type TEXT,
    resource_id INTEGER,
    details TEXT,
    ip_address TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX idx_audit_user ON audit_log(user_id);
CREATE INDEX idx_audit_timestamp ON audit_log(timestamp);
CREATE INDEX idx_audit_action ON audit_log(action);

-- PERMISSIONS TABLE
CREATE TABLE IF NOT EXISTS permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL,
    resource TEXT NOT NULL,
    action TEXT NOT NULL,
    allowed BOOLEAN DEFAULT 1
);

CREATE INDEX idx_permissions_role ON permissions(role);

-- Insert default permissions
INSERT INTO permissions (role, resource, action, allowed) VALUES
-- Admin: Full access
('admin', 'deals', 'create', 1),
('admin', 'deals', 'read', 1),
('admin', 'deals', 'update', 1),
('admin', 'deals', 'delete', 1),
('admin', 'locations', 'read', 1),
('admin', 'locations', 'update', 1),
('admin', 'locations', 'export', 1),
('admin', 'users', 'create', 1),
('admin', 'users', 'read', 1),
('admin', 'users', 'update', 1),
('admin', 'users', 'delete', 1),

-- Manager: Most access
('manager', 'deals', 'create', 1),
('manager', 'deals', 'read', 1),
('manager', 'deals', 'update', 1),
('manager', 'deals', 'delete', 1),
('manager', 'locations', 'read', 1),
('manager', 'locations', 'export', 1),
('manager', 'users', 'read', 1),

-- Sales: Own deals only
('sales', 'deals', 'create', 1),
('sales', 'deals', 'read', 1),
('sales', 'deals', 'update', 1),
('sales', 'locations', 'read', 1),
('sales', 'locations', 'export', 1),

-- Technician: Read-only
('technician', 'deals', 'read', 1),
('technician', 'locations', 'read', 1);

-- Insert default admin user
-- Password: admin123 (CHANGE IN PRODUCTION!)
INSERT INTO users (email, username, password_hash, full_name, role, active, email_verified)
VALUES ('admin@hailtracker.com', 'admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5ztpJAoFzOqje', 'System Administrator', 'admin', 1, 1);

-- Insert demo company
INSERT INTO companies (name, subscription_plan, subscription_status, max_users, billing_email)
VALUES ('Demo PDR Company', 'professional', 'active', 10, 'admin@hailtracker.com');

-- Link admin to company
UPDATE users SET company_id = 1 WHERE id = 1;
