-- =====================================================
-- Telegram Notifications Table
-- Simple version untuk tracking notifikasi jadwal
-- =====================================================

CREATE TABLE IF NOT EXISTS telegram_notifications (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    schedule_id INT NULL,
    
    -- Tipe notifikasi
    notification_type VARCHAR(50) NOT NULL,
    -- 'schedule_created' = jadwal baru dibuat
    -- 'schedule_updated' = jadwal diubah
    -- 'reminder_1day' = reminder 1 hari sebelum
    -- 'reminder_today_7am' = reminder pagi hari-H jam 07:00
    -- 'reminder_10min' = reminder 10 menit sebelum shift
    -- 'reminder_5min' = reminder 5 menit sebelum shift
    
    -- Isi pesan
    title VARCHAR(255),
    message TEXT NOT NULL,
    
    -- Status pengiriman
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP NULL,
    status VARCHAR(20) DEFAULT 'pending',  -- pending, sent, failed
    
    -- Error log (jika gagal)
    error_message TEXT NULL,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (schedule_id) REFERENCES schedules(id) ON DELETE SET NULL,
    
    INDEX idx_user_id (user_id),
    INDEX idx_schedule_id (schedule_id),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at),
    INDEX idx_schedule_notification_type (schedule_id, notification_type)
);

-- =====================================================
-- Telegram Verification Logs
-- For audit trail & troubleshooting
-- =====================================================

CREATE TABLE IF NOT EXISTS telegram_verification_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL UNIQUE,
    
    telegram_id VARCHAR(50) NOT NULL UNIQUE,
    telegram_username VARCHAR(100),
    
    verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    
    INDEX idx_verified_at (verified_at)
);

-- =====================================================
-- INFO
-- =====================================================
-- Jalankan query ini di MySQL:
-- 
-- mysql -u root rritmb < migrations/create_notification_table.sql
-- 
-- Atau copy-paste langsung ke MySQL client
-- =====================================================
