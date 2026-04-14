-- ============================================================================
-- MOCK DATA — AI Leasing Agent · Yardi-Aligned Schema
-- MAF Properties · ReKnew · April 2026
-- ============================================================================


-- ── 1. PROPERTIES (4 rows) ───────────────────────────────────────────────────

INSERT INTO properties (property_id, code, name, address_city, address_country, ejari_applicable, rera_applicable) VALUES
('prop_MOE', 'MOE', 'Mall of the Emirates',   'Dubai',  'UAE', TRUE,  TRUE),
('prop_CCD', 'CCD', 'City Centre Deira',      'Dubai',  'UAE', TRUE,  TRUE),
('prop_CCM', 'CCM', 'City Centre Mirdif',     'Dubai',  'UAE', TRUE,  TRUE),
('prop_CCA', 'CCA', 'City Centre Ajman',      'Ajman',  'UAE', FALSE, FALSE);


-- ── 2. UNITS (8 rows) ───────────────────────────────────────────────────────

INSERT INTO units (unit_id, property_id, unit_number, floor, zone, unit_type, sqm, frontage_m, status, base_rent_sqm, service_charge_sqm, marketing_levy_sqm, turnover_rent_pct, fit_out_allowance, typical_fit_out_months, last_tenant, availability_date, lease_expiry, category_fit, notes) VALUES
('MOE-L1-042', 'prop_MOE', 'L1-042', 'Level 1', 'Fashion District',          'retail', 265, 8.5, 'vacant',              2800, 420, 85, 8, 120000, 3, 'Zara',                '2026-01-15', NULL,         ARRAY['fashion','premium retail','accessories'],              'Corner unit, high footfall, near VOX entrance'),
('MOE-L1-107', 'prop_MOE', 'L1-107', 'Level 1', 'Sports & Outdoor',          'retail', 210, 7.0, 'expiring_soon',       2600, 420, 85, 7,  95000, 3, 'Intersport',           NULL,         '2026-06-30', ARRAY['sports','outdoor','adventure gear','fitness'],         'Adjacent to Ski Dubai entrance'),
('MOE-L1-031', 'prop_MOE', 'L1-031', 'Level 1', 'Beauty & Wellness',         'retail',  95, 5.5, 'vacant',              3000, 420, 85, 8,  75000, 2, 'Kiehls',               '2026-01-20', NULL,         ARRAY['beauty','skincare','cosmetics','wellness'],            'High-traffic corridor near Sephora'),
('CCD-GF-018', 'prop_CCD', 'GF-018', 'Ground Floor', 'Sports Zone',          'retail', 290, 9.2, 'vacant',              1950, 380, 70, 7, 110000, 3, 'Decathlon',            '2026-02-01', NULL,         ARRAY['sports','outdoor','adventure gear','camping'],         'Large GF unit, family footfall, parking access'),
('CCM-L2-055', 'prop_CCM', 'L2-055', 'Level 2', 'Lifestyle & Leisure',       'retail', 175, 6.0, 'reserved_informally', 2100, 390, 75, 6,  80000, 2, 'Columbia Sportswear',  '2026-03-01', NULL,         ARRAY['lifestyle','outdoor','sports','adventure'],            'Informal hold — not available without clearance'),
('CCM-GF-012', 'prop_CCM', 'GF-012', 'Ground Floor', 'Dining & Lifestyle',   'f&b',   120, 5.0, 'vacant',              2300, 400, 80, 8,  90000, 3, 'The Coffee Club',      '2026-02-15', NULL,         ARRAY['f&b','cafe','coffee','wellness','specialty dining'],   'Good visibility from main atrium'),
('MOE-L2-088', 'prop_MOE', 'L2-088', 'Level 2', 'Premium Dining & Lifestyle','f&b',   320, 11.0,'signed_unoccupied',   3200, 450, 90, 10, 160000, 4, NULL,                   NULL,         NULL,         ARRAY['f&b','dining','cafe'],                                 'Already signed — NOT available'),
('CCA-GF-003', 'prop_CCA', 'GF-003', 'Ground Floor', 'General Retail',       'retail', 140, 5.5, 'held_strategically',  1600, 320, 60, 6,  55000, 2, NULL,                   NULL,         NULL,         ARRAY['general retail'],                                      'Held for anchor reconfiguration');


-- ── 3. VACANCY_PLAN (8 rows — one per unit) ──────────────────────────────────

INSERT INTO vacancy_plan (unit_id, priority, demand_category, demand_score, demand_signal, vacancy_days, footfall_tier, target_tenant_profile) VALUES
('MOE-L1-042', TRUE,  'fashion & premium retail',    0.82, 'Fashion District anchor vacancy since Jan — footfall steady but conversion dropping. Premium fashion or lifestyle brand needed.',                          83,  'premium',  'Premium fashion, lifestyle or accessories brand, 200–300 sqm'),
('MOE-L1-107', TRUE,  'sports & outdoor',            0.91, 'Ski Dubai adjacency drives 34% higher footfall YoY. Only 3 sports tenants remain — category undersupplied. Intersport exit creates gap.',               0,   'premium',  'Premium to mid-market sports or outdoor brand, 150–250 sqm'),
('MOE-L1-031', TRUE,  'premium beauty & skincare',   0.85, 'Beauty zone lost anchor in Jan — premium skincare brands actively sought. High footfall corridor near Sephora flagship.',                                 78,  'premium',  'Premium skincare or beauty brand, 60–120 sqm'),
('CCD-GF-018', TRUE,  'sports & outdoor',            0.78, 'Decathlon exit left Sports Zone anchor gap. Family footfall strong but zone needs category refresh.',                                                     67,  'high',     'Mid-market sports or outdoor brand, 200–350 sqm'),
('CCM-L2-055', FALSE, 'lifestyle & family',          0.55, 'Unit held informally — demand assessment paused. Lifestyle & Leisure zone at 94% occupancy.',                                                            38,  'high',     'Lifestyle, kids or family brand, 120–200 sqm'),
('CCM-GF-012', TRUE,  'specialty f&b & wellness',    0.80, 'Dining zone at 88% occupancy — specialty coffee and wellness F&B strongly demanded. Previous tenant exit left gap.',                                      52,  'high',     'Specialty coffee, wellness cafe or healthy dining, 80–150 sqm'),
('MOE-L2-088', FALSE, 'f&b & dining',                0.00, 'Unit signed — no vacancy. New F&B tenant onboarding in progress.',                                                                                        0,  'premium',  'N/A — unit occupied'),
('CCA-GF-003', FALSE, 'anchor reconfiguration',      0.30, 'Strategic hold — not in active leasing pipeline until reconfiguration decision.',                                                                          0,  'high',     'N/A — strategic hold');


-- ── 4. INQUIRIES (4 rows) ────────────────────────────────────────────────────

INSERT INTO inquiries (inquiry_id, received_at, channel, status, brand_name, legal_entity_name, contact_name, contact_email, contact_phone, contact_role, category, preferred_mall, preferred_zone, size_min_sqm, size_max_sqm, target_opening, first_uae_store, priority, risk_flag, assigned_unit, agent_note) VALUES
('INQ-2026-0041', '2026-04-02 09:14:00', 'partner_connect', 'in_progress',       'Summit Gear Co.',  'Summit Gear Trading LLC',     'James Whitfield', 'j.whitfield@summitgear.com',  '+971501234567', 'Regional Director — MENA',  'premium outdoor & adventure gear',      'prop_MOE', 'Sports & Outdoor',   200, 300, 'Q4 2026', TRUE,  'high',   'new_market_entrant', 'MOE-L1-042', 'Strong brand, new UAE entity — verify PoA and parent guarantee at Gate 2'),
('INQ-2026-0039', '2026-04-01 14:30:00', 'whatsapp',         'pending_gate_1',    'Brew & Bloom',     'Brew & Bloom Hospitality FZE','Fatima Al Rashid', 'fatima@brewandbloom.ae',      '+971554321098', 'CEO',                       'specialty coffee & wellness cafe',      'prop_CCM', 'Dining & Lifestyle', 80,  150, 'Q3 2026', FALSE, 'medium', NULL,                  NULL,         'Established operator with 2 existing UAE locations'),
('INQ-2026-0037', '2026-03-28 11:00:00', 'partner_connect', 'blocked_documents',  'NovaSkin',         'NovaSkin Beauty FZCO',        'Li Wei',           'li.wei@novaskin.com',         '+971556789012', 'VP Expansion — Middle East','premium skincare & beauty retail',      'prop_MOE', 'Beauty & Wellness',  60,  120, 'Q3 2026', TRUE,  'medium', 'documents_expired',   NULL,         'Trade license expired Dec 2025, PoA expired Sep 2025'),
('INQ-2026-0035', '2026-03-25 10:00:00', 'broker_portal',   'unit_matched',       'KidsWorld',        'KidsWorld Retail LLC',        'Rania Saad',       'rania.saad@kidsworld.ae',     '+971529876543', 'Expansion Manager',         'childrens toys, apparel & play',       'prop_CCM', 'Kids & Family',      150, 250, 'Q3 2026', FALSE, 'medium', NULL,                  'CCM-L2-055', 'Unit informally reserved — confirm clearance before HoT');


-- ── 5. LEAD_SCORES (4 rows — one per inquiry) ───────────────────────────────

INSERT INTO lead_scores (inquiry_id, lead_score, lead_grade, signals_positive, signals_negative, reasoning) VALUES
('INQ-2026-0041', 0.55, 'B', ARRAY['Clear size requirement: 200–300 sqm','Inquiry via Partner Connect — qualified channel','Target opening Q4 2026 — 6 months out, healthy timeline'], ARRAY['New market entrant — no local trading history'], 'Summit Gear Co. scores 0.55 (Grade B). Solid brand with qualified channel and clear requirements, but new to UAE market — parent guarantee verification needed.'),
('INQ-2026-0039', 0.65, 'B', ARRAY['Established brand with existing UAE presence','No risk flags — financial profile assumed strong','Clear size requirement: 80–150 sqm'], ARRAY['Inquiry via WhatsApp — unqualified channel'], 'Brew & Bloom scores 0.65 (Grade B). Established operator, clean profile, but came through informal channel.'),
('INQ-2026-0037', 0.25, 'C', ARRAY['Clear size requirement: 60–120 sqm','Inquiry via Partner Connect — qualified channel'], ARRAY['Expired documents — compliance risk until renewed','New market entrant — no local trading history'], 'NovaSkin scores 0.25 (Grade C). Significant compliance risk — expired trade license and PoA. Must not proceed past Gate 2 until documents renewed.'),
('INQ-2026-0035', 0.75, 'A', ARRAY['Established brand with existing UAE presence','No risk flags — financial profile assumed strong','Clear size requirement: 150–250 sqm','Inquiry via Broker Portal — qualified channel','Target opening Q3 2026 — healthy timeline'], ARRAY[]::TEXT[], 'KidsWorld scores 0.75 (Grade A). High-confidence tenant — established, clean profile, qualified channel. Fast-track candidate.');


-- ── 6. DOCUMENTS (12 rows — across all 4 inquiries) ─────────────────────────

-- Summit Gear — new entrant, docs mostly clean but needs parent guarantee
INSERT INTO documents (document_id, inquiry_id, doc_type, status, expiry_date, flag, submitted_at) VALUES
('DOC-0041-01', 'INQ-2026-0041', 'trade_license',           'valid',   '2027-03-15', NULL, '2026-04-03 10:00:00'),
('DOC-0041-02', 'INQ-2026-0041', 'vat_certificate',         'valid',   '2027-06-30', NULL, '2026-04-03 10:00:00'),
('DOC-0041-03', 'INQ-2026-0041', 'passport',                'valid',   '2030-11-20', NULL, '2026-04-03 10:00:00'),
('DOC-0041-04', 'INQ-2026-0041', 'power_of_attorney',       'valid',   '2027-04-01', NULL, '2026-04-03 10:00:00'),
('DOC-0041-05', 'INQ-2026-0041', 'parent_company_guarantee','missing', NULL,          'Required for first UAE store — not yet submitted', NULL);

-- Brew & Bloom — established, clean docs
INSERT INTO documents (document_id, inquiry_id, doc_type, status, expiry_date, flag, submitted_at) VALUES
('DOC-0039-01', 'INQ-2026-0039', 'trade_license',   'valid', '2027-08-10', NULL, '2026-04-02 09:00:00'),
('DOC-0039-02', 'INQ-2026-0039', 'vat_certificate', 'valid', '2027-12-31', NULL, '2026-04-02 09:00:00'),
('DOC-0039-03', 'INQ-2026-0039', 'emirates_id',     'valid', '2028-05-15', NULL, '2026-04-02 09:00:00');

-- NovaSkin — expired documents, should block at Gate 2
INSERT INTO documents (document_id, inquiry_id, doc_type, status, expiry_date, flag, submitted_at) VALUES
('DOC-0037-01', 'INQ-2026-0037', 'trade_license',      'expired', '2025-12-31', 'Expired Dec 2025 — renewal required before proceeding',  '2026-03-29 14:00:00'),
('DOC-0037-02', 'INQ-2026-0037', 'power_of_attorney',  'expired', '2025-09-30', 'Expired Sep 2025 — must be reissued',                    '2026-03-29 14:00:00');

-- KidsWorld — established, clean
INSERT INTO documents (document_id, inquiry_id, doc_type, status, expiry_date, flag, submitted_at) VALUES
('DOC-0035-01', 'INQ-2026-0035', 'trade_license',   'valid', '2027-02-28', NULL, '2026-03-26 11:00:00'),
('DOC-0035-02', 'INQ-2026-0035', 'vat_certificate', 'valid', '2027-06-30', NULL, '2026-03-26 11:00:00');


-- ── 7. PRICING_RULES (5 rows) ───────────────────────────────────────────────

INSERT INTO pricing_rules (rule_id, property_id, category, base_rent_sqm_min, base_rent_sqm_max, max_fit_out_months, rent_free_months_allowed, annual_escalation_pct, security_deposit_months) VALUES
('PR-MOE-SPORT', 'prop_MOE', 'sports & outdoor',             2400, 3000, 3, 1, 5.0, 3),
('PR-MOE-FASH',  'prop_MOE', 'fashion & premium retail',     2600, 3200, 3, 1, 6.0, 3),
('PR-MOE-BEAUT', 'prop_MOE', 'beauty & skincare',            2800, 3400, 2, 0, 5.0, 3),
('PR-CCD-SPORT', 'prop_CCD', 'sports & outdoor',             1800, 2200, 3, 1, 5.0, 3),
('PR-CCM-FB',    'prop_CCM', 'f&b & specialty dining',       2100, 2600, 3, 1, 5.0, 2);


-- ── 8. LEASES (2 rows — completed deals) ────────────────────────────────────

INSERT INTO leases (lease_id, lease_number, property_id, unit_id, inquiry_id, tenant_legal_name, tenant_brand_name, start_date, end_date, rent_commencement, fit_out_months, lease_duration_years, status, security_deposit, fit_out_deposit, turnover_rent_pct, turnover_threshold, annual_escalation_pct, signatory_tenant, approved_at, approved_by) VALUES
('LSE-2026-001', 'MAF-LEASE-2026-0041', 'prop_MOE', 'MOE-L1-107', 'INQ-2026-0041', 'Summit Gear Trading LLC',      'Summit Gear Co.', '2026-05-09', '2029-05-08', '2026-08-09', 3, 3, 'active',  136500, 95000,  7, 7800000, 5.0, 'James Whitfield — Regional Director', '2026-04-08 16:00:00', 'senior_manager'),
('LSE-2026-002', 'MAF-LEASE-2026-0039', 'prop_CCM', 'CCM-GF-012', 'INQ-2026-0039', 'Brew & Bloom Hospitality FZE', 'Brew & Bloom',    '2026-05-15', '2029-05-14', '2026-08-15', 3, 3, 'active',   69000, 90000,  8, 3300000, 5.0, 'Fatima Al Rashid — CEO',              '2026-04-09 10:00:00', 'senior_manager');


-- ── 9. RENT_CHARGES (12 rows — 6 per lease) ─────────────────────────────────

-- Summit Gear — 3 years stepped rent + service + marketing
INSERT INTO rent_charges (charge_id, lease_id, code, description, amount, frequency, due_day, effective_from, effective_to, escalation_applied) VALUES
-- Year 1
('CHG-001-RENT-Y1', 'LSE-2026-001', 'RENT', 'Base rent — year 1',     45500.00, 'monthly', 1, '2026-08-09', '2027-05-08', FALSE),
('CHG-001-SRVC-Y1', 'LSE-2026-001', 'SRVC', 'Service charge',          7350.00, 'monthly', 1, '2026-08-09', '2029-05-08', FALSE),
('CHG-001-MKTG-Y1', 'LSE-2026-001', 'MKTG', 'Marketing levy',          1487.50, 'monthly', 1, '2026-08-09', '2029-05-08', FALSE),
-- Year 2 (+5%)
('CHG-001-RENT-Y2', 'LSE-2026-001', 'RENT', 'Base rent — year 2',     47775.00, 'monthly', 1, '2027-05-09', '2028-05-08', TRUE),
-- Year 3 (+5%)
('CHG-001-RENT-Y3', 'LSE-2026-001', 'RENT', 'Base rent — year 3',     50163.75, 'monthly', 1, '2028-05-09', '2029-05-08', TRUE),
-- Turnover
('CHG-001-TURN',    'LSE-2026-001', 'TURNOVER', 'Turnover rent (7% above threshold)', 0.00, 'quarterly', 15, '2026-08-09', '2029-05-08', FALSE),

-- Brew & Bloom — 3 years stepped rent + service + marketing
('CHG-002-RENT-Y1', 'LSE-2026-002', 'RENT', 'Base rent — year 1',     23000.00, 'monthly', 1, '2026-08-15', '2027-05-14', FALSE),
('CHG-002-SRVC-Y1', 'LSE-2026-002', 'SRVC', 'Service charge',          4000.00, 'monthly', 1, '2026-08-15', '2029-05-14', FALSE),
('CHG-002-MKTG-Y1', 'LSE-2026-002', 'MKTG', 'Marketing levy',           800.00, 'monthly', 1, '2026-08-15', '2029-05-14', FALSE),
('CHG-002-RENT-Y2', 'LSE-2026-002', 'RENT', 'Base rent — year 2',     24150.00, 'monthly', 1, '2027-05-15', '2028-05-14', TRUE),
('CHG-002-RENT-Y3', 'LSE-2026-002', 'RENT', 'Base rent — year 3',     25357.50, 'monthly', 1, '2028-05-15', '2029-05-14', TRUE),
('CHG-002-TURN',    'LSE-2026-002', 'TURNOVER', 'Turnover rent (8% above threshold)', 0.00, 'quarterly', 15, '2026-08-15', '2029-05-14', FALSE);


-- ── 10. EJARI_REGISTRATIONS (2 rows) ────────────────────────────────────────

INSERT INTO ejari_registrations (registration_number, lease_id, property_id, unit_id, tenant_legal_name, annual_rent, registration_date, status, message, filed_at) VALUES
('EJARI-2026-MOE-L1107-4821', 'LSE-2026-001', 'prop_MOE', 'MOE-L1-107', 'Summit Gear Trading LLC',      546000.00, '2026-04-08', 'Registered', 'Successfully registered with Dubai Land Department', '2026-04-08 16:15:00'),
('EJARI-2026-CCM-GF012-7293', 'LSE-2026-002', 'prop_CCM', 'CCM-GF-012', 'Brew & Bloom Hospitality FZE', 276000.00, '2026-04-09', 'Registered', 'Successfully registered with Dubai Land Department', '2026-04-09 10:30:00');


-- ============================================================================
-- ROW COUNT SUMMARY
-- ============================================================================
-- properties:          4 rows
-- units:               8 rows
-- vacancy_plan:        8 rows
-- inquiries:           4 rows
-- lead_scores:         4 rows
-- documents:          12 rows
-- pricing_rules:       5 rows
-- leases:              2 rows
-- rent_charges:       12 rows
-- ejari_registrations: 2 rows
-- ─────────────────────────────
-- TOTAL:              61 rows
-- ============================================================================
