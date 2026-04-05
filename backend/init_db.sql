-- Initialize Copilot Database Schema
-- Run on container startup

CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(6) UNIQUE NOT NULL,
    host_name VARCHAR(255) NOT NULL,
    company VARCHAR(255) NOT NULL,
    industry VARCHAR(100) NOT NULL,
    participant_count INT NOT NULL,
    duration_mins INT DEFAULT 90,
    current_phase INT DEFAULT 0,
    status VARCHAR(50) DEFAULT 'waiting',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    revealed_phases TEXT[] DEFAULT ARRAY[]::TEXT[],
    workshop_data JSONB DEFAULT '{}',
    INDEX idx_code (code),
    INDEX idx_created_at (created_at)
);

CREATE TABLE IF NOT EXISTS company_dna (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    company_name VARCHAR(255) NOT NULL,
    vision TEXT,
    goals TEXT[] DEFAULT ARRAY[]::TEXT[],
    products TEXT[] DEFAULT ARRAY[]::TEXT[],
    tone VARCHAR(100),
    recent_news TEXT[] DEFAULT ARRAY[]::TEXT[],
    confidence VARCHAR(20) CHECK (confidence IN ('complete', 'partial', 'fallback')),
    source_url VARCHAR(2048),
    scraped_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    INDEX idx_session_id (session_id),
    INDEX idx_expires_at (expires_at),
    INDEX idx_company_name (company_name)
);

CREATE TABLE IF NOT EXISTS participants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(100),
    company VARCHAR(255),
    headline VARCHAR(255),
    summary TEXT,
    skills TEXT[] DEFAULT ARRAY[]::TEXT[],
    location VARCHAR(255),
    industry VARCHAR(100),
    confidence VARCHAR(20) CHECK (confidence IN ('complete', 'partial', 'fallback')),
    source VARCHAR(50) DEFAULT 'manual' CHECK (source IN ('linkedin', 'manual')),
    linkedin_url VARCHAR(2048),
    scraped_at TIMESTAMP,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    INDEX idx_session_id (session_id),
    INDEX idx_name (name),
    INDEX idx_expires_at (expires_at)
);

CREATE TABLE IF NOT EXISTS participant_extras (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_id UUID UNIQUE REFERENCES participants(id) ON DELETE CASCADE,
    fun_fact TEXT,
    local_context JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS phase_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    phase_key VARCHAR(100) NOT NULL,
    participant_id UUID REFERENCES participants(id) ON DELETE SET NULL,
    submission JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session_phase (session_id, phase_key),
    INDEX idx_participant_id (participant_id)
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_sessions_code ON sessions(code);
CREATE INDEX IF NOT EXISTS idx_company_dna_session ON company_dna(session_id) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_participants_session ON participants(session_id) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_phase_data_session ON phase_data(session_id);

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply update trigger to sessions table
CREATE TRIGGER update_sessions_updated_at BEFORE UPDATE ON sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Apply update trigger to company_dna table
CREATE TRIGGER update_company_dna_updated_at BEFORE UPDATE ON company_dna
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Apply update trigger to participants table
CREATE TRIGGER update_participants_updated_at BEFORE UPDATE ON participants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Apply update trigger to participant_extras table
CREATE TRIGGER update_participant_extras_updated_at BEFORE UPDATE ON participant_extras
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Apply update trigger to phase_data table
CREATE TRIGGER update_phase_data_updated_at BEFORE UPDATE ON phase_data
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO copilot_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO copilot_user;
