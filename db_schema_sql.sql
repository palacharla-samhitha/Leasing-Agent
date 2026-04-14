-- ============================================================================
-- AI Leasing Agent — Database Schema (Yardi Voyager Aligned)
-- MAF Properties · ReKnew · April 2026
-- 
-- Field naming follows Yardi's Commercial API conventions (camelCase)
-- Relationships follow Yardi's entity hierarchy:
--   Property → Unit → Lease → Charges + EJARI
--   Inquiry → Lead Score + Documents → Lease
-- ============================================================================


-- 1. PROPERTIES
-- Equivalent to Yardi's Property entity. One record per mall.
-- In Yardi: GET /properties
-- In our mock: data/malls.json

CREATE TABLE properties (
    property_id         VARCHAR(20)     PRIMARY KEY,        -- "prop_MOE"
    code                VARCHAR(10)     NOT NULL UNIQUE,    -- "MOE" (short display code)
    name                VARCHAR(100)    NOT NULL,           -- "Mall of the Emirates"
    address_line1       VARCHAR(200),
    address_city        VARCHAR(50)     NOT NULL,           -- "Dubai"
    address_region      VARCHAR(50),                        -- "Dubai" (emirate)
    address_country     VARCHAR(5)      NOT NULL,           -- "UAE"
    address_postal_code VARCHAR(20),
    portfolio           VARCHAR(100)    DEFAULT 'MAF Properties',
    management_company  VARCHAR(100)    DEFAULT 'Majid Al Futtaim Properties LLC',
    status              VARCHAR(20)     DEFAULT 'active',   -- active | inactive
    ejari_applicable    BOOLEAN         DEFAULT FALSE,      -- Dubai properties only
    rera_applicable     BOOLEAN         DEFAULT FALSE,
    created_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
);


-- 2. UNITS
-- Equivalent to Yardi's Unit entity. Individual leasable spaces.
-- In Yardi: GET /units?propertyId=...
-- In our mock: data/units.json
-- Key diff: Yardi stores marketRent as total monthly; we store per sqm

CREATE TABLE units (
    unit_id             VARCHAR(20)     PRIMARY KEY,        -- "MOE-L1-107"
    property_id         VARCHAR(20)     NOT NULL REFERENCES properties(property_id),
    unit_number         VARCHAR(20),                        -- "L1-107"
    floor               VARCHAR(20),                        -- "Level 1"
    zone                VARCHAR(50),                        -- "Sports & Outdoor"
    unit_type           VARCHAR(20)     NOT NULL,           -- "retail" | "f&b"
    sqm                 DECIMAL(10,2)   NOT NULL,           -- size in square metres
    frontage_m          DECIMAL(5,1),                       -- storefront width
    status              VARCHAR(30)     NOT NULL,           -- vacant | expiring_soon | 
                                                            -- reserved_informally | 
                                                            -- signed_unoccupied | 
                                                            -- held_strategically
    market_rent_monthly DECIMAL(12,2),                      -- Yardi convention: total monthly
    base_rent_sqm       DECIMAL(10,2),                      -- MAF convention: per sqm annual
    service_charge_sqm  DECIMAL(10,2),
    marketing_levy_sqm  DECIMAL(10,2),
    turnover_rent_pct   DECIMAL(4,1),
    fit_out_allowance   DECIMAL(12,2),
    typical_fit_out_months INT,
    last_tenant         VARCHAR(100),
    availability_date   DATE,                               -- Yardi: when unit becomes available
    lease_expiry        DATE,                               -- for expiring_soon units
    category_fit        TEXT[],                              -- ["sports", "outdoor", "fitness"]
    notes               TEXT,
    created_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
);


-- 3. VACANCY_PLAN
-- Simulates the ML demand model output from Databricks.
-- No Yardi equivalent — this is MAF-specific predictive intelligence.
-- In our mock: vacancy_plan object nested in units.json
-- In production: Databricks scheduled job writes to this table

CREATE TABLE vacancy_plan (
    unit_id             VARCHAR(20)     PRIMARY KEY REFERENCES units(unit_id),
    priority            BOOLEAN         DEFAULT FALSE,
    demand_category     VARCHAR(100),                       -- "sports & outdoor"
    demand_score        DECIMAL(3,2),                       -- 0.00 to 1.00
    demand_signal       TEXT,                               -- human-readable explanation
    vacancy_days        INT             DEFAULT 0,
    footfall_tier       VARCHAR(20),                        -- "premium" | "high" | "standard"
    target_tenant_profile TEXT,
    scored_at           TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
);


-- 4. INQUIRIES
-- Tenant leasing inquiries. Arrives via Partner Connect, Broker Portal,
-- WhatsApp, or manual entry.
-- In Yardi: closest equivalent is Guest Card / Lead via ILS interface
-- In our mock: data/inquiries.json

CREATE TABLE inquiries (
    inquiry_id          VARCHAR(30)     PRIMARY KEY,        -- "INQ-2026-0041"
    received_at         TIMESTAMP       NOT NULL,
    channel             VARCHAR(30)     NOT NULL,           -- partner_connect | broker_portal |
                                                            -- whatsapp | walk_in | email
    status              VARCHAR(30)     NOT NULL,           -- in_progress | pending_gate_1 |
                                                            -- blocked_documents | unit_matched |
                                                            -- completed | cancelled
    brand_name          VARCHAR(100)    NOT NULL,
    legal_entity_name   VARCHAR(200)    NOT NULL,
    contact_name        VARCHAR(100),
    contact_email       VARCHAR(100),
    contact_phone       VARCHAR(30),
    contact_role        VARCHAR(100),
    category            VARCHAR(100)    NOT NULL,           -- "premium outdoor & adventure gear"
    preferred_mall      VARCHAR(20)     REFERENCES properties(property_id),
    preferred_zone      VARCHAR(50),
    size_min_sqm        INT,
    size_max_sqm        INT,
    target_opening      VARCHAR(20),                        -- "Q4 2026"
    first_uae_store     BOOLEAN         DEFAULT FALSE,
    priority            VARCHAR(10)     DEFAULT 'medium',   -- high | medium | low
    risk_flag           VARCHAR(50),                        -- new_market_entrant | documents_expired
    assigned_unit       VARCHAR(20)     REFERENCES units(unit_id),
    agent_note          TEXT,
    created_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
);


-- 5. LEAD_SCORES
-- Output of the lead scoring model. One per inquiry.
-- In production: Databricks ML model endpoint
-- In our mock: tools/scoring.py → calculate_lead_score()

CREATE TABLE lead_scores (
    inquiry_id          VARCHAR(30)     PRIMARY KEY REFERENCES inquiries(inquiry_id),
    lead_score          DECIMAL(3,2)    NOT NULL,           -- 0.00 to 1.00
    lead_grade          CHAR(1)         NOT NULL,           -- A | B | C
    signals_positive    TEXT[],
    signals_negative    TEXT[],
    reasoning           TEXT,
    scored_at           TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
);


-- 6. DOCUMENTS
-- Tenant-submitted documents for compliance verification.
-- In Yardi: managed via Document Management module
-- In our mock: data/documents.json

CREATE TABLE documents (
    document_id         VARCHAR(30)     PRIMARY KEY,        -- auto-generated
    inquiry_id          VARCHAR(30)     NOT NULL REFERENCES inquiries(inquiry_id),
    doc_type            VARCHAR(50)     NOT NULL,           -- trade_license | vat_certificate |
                                                            -- emirates_id | power_of_attorney |
                                                            -- memorandum_of_association |
                                                            -- board_resolution | parent_guarantee
    status              VARCHAR(20)     NOT NULL,           -- valid | expired | missing | warning
    expiry_date         DATE,
    flag                TEXT,                               -- specific issue description
    submitted_at        TIMESTAMP,
    verified_at         TIMESTAMP,
    verified_by         VARCHAR(50)                         -- "agent" | "lcm_manual"
);


-- 7. PRICING_RULES
-- Allowed commercial terms per mall and category.
-- In Yardi: Charge Code configuration + custom business rules
-- In our mock: data/pricing.json

CREATE TABLE pricing_rules (
    rule_id             VARCHAR(30)     PRIMARY KEY,
    property_id         VARCHAR(20)     NOT NULL REFERENCES properties(property_id),
    category            VARCHAR(100)    NOT NULL,           -- "sports & outdoor"
    base_rent_sqm_min   DECIMAL(10,2)   NOT NULL,
    base_rent_sqm_max   DECIMAL(10,2)   NOT NULL,
    max_fit_out_months   INT            DEFAULT 3,
    rent_free_months_allowed INT        DEFAULT 0,
    annual_escalation_pct DECIMAL(4,1)  DEFAULT 5.0,
    security_deposit_months INT         DEFAULT 3,
    UNIQUE (property_id, category)
);


-- 8. LEASES
-- The central entity — links tenant to unit with commercial terms.
-- In Yardi: POST /leases (create), GET /leases (read)
-- In our mock: node_lease_gen output + data/leases.json
-- Key diff: Yardi uses rentCharges[] array; we use flat fields

CREATE TABLE leases (
    lease_id            VARCHAR(30)     PRIMARY KEY,        -- system-generated
    lease_number        VARCHAR(30)     NOT NULL UNIQUE,    -- "MAF-LEASE-2026-0041"
    property_id         VARCHAR(20)     NOT NULL REFERENCES properties(property_id),
    unit_id             VARCHAR(20)     NOT NULL REFERENCES units(unit_id),
    inquiry_id          VARCHAR(30)     NOT NULL REFERENCES inquiries(inquiry_id),
    tenant_legal_name   VARCHAR(200)    NOT NULL,
    tenant_brand_name   VARCHAR(100),
    start_date          DATE            NOT NULL,           -- Yardi: startDate
    end_date            DATE            NOT NULL,           -- Yardi: endDate
    rent_commencement   DATE            NOT NULL,
    fit_out_months      INT             DEFAULT 3,
    lease_duration_years INT            NOT NULL,
    status              VARCHAR(30)     DEFAULT 'pending_signature',  -- pending_signature |
                                                            -- active | expired | terminated
    security_deposit    DECIMAL(12,2),
    fit_out_deposit     DECIMAL(12,2),
    turnover_rent_pct   DECIMAL(4,1),
    turnover_threshold  DECIMAL(14,2),
    annual_escalation_pct DECIMAL(4,1),
    signatory_tenant    VARCHAR(100),
    signatory_landlord  VARCHAR(100)    DEFAULT 'Leasing Director, MAF Properties',
    created_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    approved_at         TIMESTAMP,
    approved_by         VARCHAR(50)
);


-- 9. RENT_CHARGES
-- Individual charge items on a lease. Follows Yardi's charge code model.
-- In Yardi: rentCharges[] array on the lease object
-- In our mock: flat fields (base_rent, service_charge, marketing_levy)
-- This table is the KEY structural change from our current mock data

CREATE TABLE rent_charges (
    charge_id           VARCHAR(30)     PRIMARY KEY,
    lease_id            VARCHAR(30)     NOT NULL REFERENCES leases(lease_id),
    code                VARCHAR(20)     NOT NULL,           -- RENT | SRVC | MKTG | TURNOVER
    description         VARCHAR(100),                       -- "Base rent" | "Service charge"
    amount              DECIMAL(12,2)   NOT NULL,           -- monthly amount (Yardi convention)
    frequency           VARCHAR(20)     DEFAULT 'monthly',  -- monthly | quarterly | annual
    due_day             INT             DEFAULT 1,
    effective_from      DATE            NOT NULL,           -- for stepped rent schedules
    effective_to        DATE            NOT NULL,
    escalation_applied  BOOLEAN         DEFAULT FALSE
);

-- Example: A 3-year lease with 5% annual escalation creates 3 RENT charge rows:
--   RENT  | 45,500/mo | 2026-08-09 to 2027-05-08  (year 1)
--   RENT  | 47,775/mo | 2027-05-09 to 2028-05-08  (year 2 = +5%)
--   RENT  | 50,164/mo | 2028-05-09 to 2029-05-08  (year 3 = +5%)
-- Plus separate rows for SRVC and MKTG charges.


-- 10. EJARI_REGISTRATIONS
-- Dubai government lease registration. One per lease (Dubai properties only).
-- In our mock: tools/ejari.py output
-- In production: Dubai Land Department EJARI API

CREATE TABLE ejari_registrations (
    registration_number VARCHAR(50)     PRIMARY KEY,        -- "EJARI-2026-MOE-L1-107-4821"
    lease_id            VARCHAR(30)     NOT NULL REFERENCES leases(lease_id),
    property_id         VARCHAR(20)     NOT NULL REFERENCES properties(property_id),
    unit_id             VARCHAR(20)     NOT NULL REFERENCES units(unit_id),
    tenant_legal_name   VARCHAR(200)    NOT NULL,
    annual_rent         DECIMAL(14,2)   NOT NULL,
    registration_date   DATE            NOT NULL,
    status              VARCHAR(20)     NOT NULL,           -- Registered | Failed
    message             TEXT,
    filed_at            TIMESTAMP
);


-- ============================================================================
-- INDEXES for common query patterns
-- ============================================================================

CREATE INDEX idx_units_property      ON units(property_id);
CREATE INDEX idx_units_status        ON units(status);
CREATE INDEX idx_inquiries_status    ON inquiries(status);
CREATE INDEX idx_inquiries_mall      ON inquiries(preferred_mall);
CREATE INDEX idx_leases_unit         ON leases(unit_id);
CREATE INDEX idx_leases_inquiry      ON leases(inquiry_id);
CREATE INDEX idx_leases_status       ON leases(status);
CREATE INDEX idx_charges_lease       ON rent_charges(lease_id);
CREATE INDEX idx_documents_inquiry   ON documents(inquiry_id);
CREATE INDEX idx_ejari_lease         ON ejari_registrations(lease_id);


-- ============================================================================
-- VIEWS for common agent queries
-- ============================================================================

-- Available units with vacancy plan (what node_unit_match queries)
CREATE VIEW v_available_units AS
SELECT u.*, vp.priority, vp.demand_category, vp.demand_score,
       vp.demand_signal, vp.vacancy_days, vp.footfall_tier,
       vp.target_tenant_profile, p.name as property_name, p.code as property_code
FROM units u
LEFT JOIN vacancy_plan vp ON u.unit_id = vp.unit_id
JOIN properties p ON u.property_id = p.property_id
WHERE u.status IN ('vacant', 'expiring_soon');

-- Active leases with charges summary
CREATE VIEW v_active_leases AS
SELECT l.*, 
       SUM(CASE WHEN rc.code = 'RENT' THEN rc.amount ELSE 0 END) as monthly_rent,
       SUM(CASE WHEN rc.code = 'SRVC' THEN rc.amount ELSE 0 END) as monthly_service,
       SUM(CASE WHEN rc.code = 'MKTG' THEN rc.amount ELSE 0 END) as monthly_marketing
FROM leases l
LEFT JOIN rent_charges rc ON l.lease_id = rc.lease_id
WHERE l.status = 'active'
GROUP BY l.lease_id;
