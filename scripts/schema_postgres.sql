CREATE TABLE organizations (
	id SERIAL NOT NULL, 
	name VARCHAR(150) NOT NULL, 
	slug VARCHAR(100) NOT NULL, 
	owner_user_id INTEGER, 
	plan VARCHAR(50) NOT NULL, 
	trial_ends_at TIMESTAMP WITH TIME ZONE, 
	subscription_status VARCHAR(50) NOT NULL, 
	stripe_customer_id VARCHAR(100), 
	stripe_subscription_id VARCHAR(100), 
	logo_url VARCHAR(255), 
	brand_color VARCHAR(20), 
	timezone VARCHAR(50) NOT NULL, 
	currency VARCHAR(10) NOT NULL, 
	address TEXT, 
	tax_id VARCHAR(50), 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id)
);

CREATE TABLE users (
	id SERIAL NOT NULL, 
	organization_id INTEGER, 
	email VARCHAR(255) NOT NULL, 
	username VARCHAR(100) NOT NULL, 
	hashed_password VARCHAR(255) NOT NULL, 
	full_name VARCHAR(255) NOT NULL, 
	role VARCHAR(50) NOT NULL, 
	tour_completed BOOLEAN NOT NULL, 
	email_verified BOOLEAN NOT NULL, 
	verification_token VARCHAR(100), 
	reset_token VARCHAR(100), 
	reset_token_expires_at TIMESTAMP WITH TIME ZONE, 
	is_active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE SET NULL
);

CREATE TABLE webhook_events (
	id VARCHAR(100) NOT NULL, 
	event_type VARCHAR(100) NOT NULL, 
	processed_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE activity_logs (
	id SERIAL NOT NULL, 
	organization_id INTEGER NOT NULL, 
	event_type VARCHAR(50) NOT NULL, 
	description VARCHAR(255) NOT NULL, 
	actor VARCHAR(100) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE
);

CREATE TABLE audit_logs (
	id SERIAL NOT NULL, 
	organization_id INTEGER NOT NULL, 
	user_id INTEGER, 
	action VARCHAR(50) NOT NULL, 
	entity_type VARCHAR(50) NOT NULL, 
	entity_id INTEGER, 
	before_json TEXT, 
	after_json TEXT, 
	ip_address VARCHAR(50), 
	user_agent VARCHAR(255), 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE backups (
	id SERIAL NOT NULL, 
	organization_id INTEGER NOT NULL, 
	s3_key VARCHAR(255) NOT NULL, 
	size_bytes INTEGER NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE
);

CREATE TABLE booking_groups (
	id SERIAL NOT NULL, 
	organization_id INTEGER NOT NULL, 
	hotel_id INTEGER NOT NULL, 
	name VARCHAR(150) NOT NULL, 
	contact_name VARCHAR(100) NOT NULL, 
	contact_email VARCHAR(255) NOT NULL, 
	contact_phone VARCHAR(50) NOT NULL, 
	check_in DATE NOT NULL, 
	check_out DATE NOT NULL, 
	cutoff_date DATE NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	notes TEXT, 
	is_demo BOOLEAN NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE
);

CREATE TABLE business_dates (
	id SERIAL NOT NULL, 
	organization_id INTEGER NOT NULL, 
	hotel_id INTEGER NOT NULL, 
	date DATE NOT NULL, 
	closed_at TIMESTAMP WITH TIME ZONE, 
	closed_by_user_id INTEGER, 
	status VARCHAR(20) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(closed_by_user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE cancellation_policies (
	id SERIAL NOT NULL, 
	organization_id INTEGER NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	description TEXT, 
	free_cancel_days INTEGER NOT NULL, 
	penalty_type VARCHAR(30) NOT NULL, 
	penalty_value NUMERIC(10, 2) NOT NULL, 
	no_show_penalty VARCHAR(30) NOT NULL, 
	no_show_value NUMERIC(10, 2) NOT NULL, 
	active BOOLEAN NOT NULL, 
	is_demo BOOLEAN NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE
);

CREATE TABLE daily_snapshots (
	id SERIAL NOT NULL, 
	organization_id INTEGER NOT NULL, 
	hotel_id INTEGER NOT NULL, 
	business_date DATE NOT NULL, 
	occupancy_rate NUMERIC(5, 2) NOT NULL, 
	adr NUMERIC(10, 2) NOT NULL, 
	revpar NUMERIC(10, 2) NOT NULL, 
	arrivals INTEGER NOT NULL, 
	departures INTEGER NOT NULL, 
	room_revenue NUMERIC(10, 2) NOT NULL, 
	total_revenue NUMERIC(10, 2) NOT NULL, 
	tax_collected NUMERIC(10, 2) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE
);

CREATE TABLE email_templates (
	id SERIAL NOT NULL, 
	organization_id INTEGER NOT NULL, 
	key VARCHAR(50) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	subject VARCHAR(255) NOT NULL, 
	body TEXT NOT NULL, 
	variables_hint TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_email_template_org_key UNIQUE (organization_id, key), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE
);

CREATE TABLE export_jobs (
	id VARCHAR(50) NOT NULL, 
	organization_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	file_path VARCHAR(255), 
	s3_key VARCHAR(255), 
	error_message TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE guests (
	id SERIAL NOT NULL, 
	organization_id INTEGER NOT NULL, 
	first_name VARCHAR(100) NOT NULL, 
	last_name VARCHAR(100) NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	phone VARCHAR(50) NOT NULL, 
	address TEXT, 
	id_number VARCHAR(100), 
	notes TEXT, 
	is_demo BOOLEAN NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE
);

CREATE TABLE room_types (
	id SERIAL NOT NULL, 
	organization_id INTEGER NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	code VARCHAR(20) NOT NULL, 
	description TEXT, 
	base_rate NUMERIC(10, 2) NOT NULL, 
	max_occupancy INTEGER NOT NULL, 
	is_demo BOOLEAN NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_room_type_org_code UNIQUE (organization_id, code), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE
);

CREATE TABLE tax_rates (
	id SERIAL NOT NULL, 
	organization_id INTEGER NOT NULL, 
	hotel_id INTEGER NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	rate NUMERIC(5, 2) NOT NULL, 
	fixed_amount NUMERIC(10, 2) NOT NULL, 
	applies_to VARCHAR(30) NOT NULL, 
	type VARCHAR(20) NOT NULL, 
	per VARCHAR(30) NOT NULL, 
	active BOOLEAN NOT NULL, 
	sort_order INTEGER NOT NULL, 
	is_demo BOOLEAN NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE
);

CREATE TABLE user_org_memberships (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	organization_id INTEGER NOT NULL, 
	role VARCHAR(50) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_user_organization UNIQUE (user_id, organization_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE
);

CREATE TABLE group_blocks (
	id SERIAL NOT NULL, 
	organization_id INTEGER NOT NULL, 
	group_id INTEGER NOT NULL, 
	room_type_id INTEGER NOT NULL, 
	count INTEGER NOT NULL, 
	rate NUMERIC(10, 2) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(group_id) REFERENCES booking_groups (id) ON DELETE CASCADE, 
	FOREIGN KEY(room_type_id) REFERENCES room_types (id) ON DELETE RESTRICT
);

CREATE TABLE rate_overrides (
	id SERIAL NOT NULL, 
	organization_id INTEGER NOT NULL, 
	room_type_id INTEGER NOT NULL, 
	date DATE NOT NULL, 
	rate NUMERIC(10, 2) NOT NULL, 
	min_stay INTEGER, 
	closed BOOLEAN NOT NULL, 
	closed_to_arrival BOOLEAN NOT NULL, 
	closed_to_departure BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_rate_override_room_type_date UNIQUE (room_type_id, date), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(room_type_id) REFERENCES room_types (id) ON DELETE CASCADE
);

CREATE TABLE rate_plans (
	id SERIAL NOT NULL, 
	organization_id INTEGER NOT NULL, 
	hotel_id INTEGER NOT NULL, 
	code VARCHAR(20) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	description TEXT, 
	room_type_id INTEGER, 
	modifier_type VARCHAR(20) NOT NULL, 
	modifier_value NUMERIC(10, 2) NOT NULL, 
	meal_plan VARCHAR(30) NOT NULL, 
	min_stay INTEGER NOT NULL, 
	max_stay INTEGER, 
	cancellation_policy_id INTEGER, 
	refundable BOOLEAN NOT NULL, 
	valid_from DATE, 
	valid_to DATE, 
	closed_to_arrival BOOLEAN NOT NULL, 
	closed_to_departure BOOLEAN NOT NULL, 
	active BOOLEAN NOT NULL, 
	requires_deposit BOOLEAN NOT NULL, 
	deposit_percent NUMERIC(5, 2), 
	deposit_fixed_amount NUMERIC(10, 2), 
	is_demo BOOLEAN NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(room_type_id) REFERENCES room_types (id) ON DELETE SET NULL, 
	FOREIGN KEY(cancellation_policy_id) REFERENCES cancellation_policies (id) ON DELETE SET NULL
);

CREATE TABLE rooms (
	id SERIAL NOT NULL, 
	organization_id INTEGER NOT NULL, 
	number VARCHAR(20) NOT NULL, 
	floor INTEGER NOT NULL, 
	room_type_id INTEGER NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	notes TEXT, 
	version INTEGER NOT NULL, 
	is_demo BOOLEAN NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_room_org_number UNIQUE (organization_id, number), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(room_type_id) REFERENCES room_types (id) ON DELETE RESTRICT
);

CREATE TABLE housekeeping_tasks (
	id SERIAL NOT NULL, 
	organization_id INTEGER NOT NULL, 
	room_id INTEGER NOT NULL, 
	task_type VARCHAR(50) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	priority VARCHAR(20) NOT NULL, 
	assigned_to VARCHAR(100), 
	notes TEXT, 
	token VARCHAR(100), 
	token_expires_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(room_id) REFERENCES rooms (id) ON DELETE RESTRICT
);

CREATE TABLE reservations (
	id SERIAL NOT NULL, 
	organization_id INTEGER NOT NULL, 
	confirmation_number VARCHAR(30) NOT NULL, 
	guest_id INTEGER NOT NULL, 
	room_id INTEGER NOT NULL, 
	rate_plan_id INTEGER, 
	group_id INTEGER, 
	is_group_master BOOLEAN NOT NULL, 
	check_in_date DATE NOT NULL, 
	check_out_date DATE NOT NULL, 
	adults INTEGER NOT NULL, 
	children INTEGER NOT NULL, 
	nightly_rate NUMERIC(10, 2) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	deposit_required NUMERIC(10, 2) NOT NULL, 
	deposit_paid NUMERIC(10, 2) NOT NULL, 
	deposit_due_at DATE, 
	notes TEXT, 
	version INTEGER NOT NULL, 
	is_demo BOOLEAN NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	CONSTRAINT chk_reservation_dates CHECK (check_out_date > check_in_date), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(guest_id) REFERENCES guests (id) ON DELETE RESTRICT, 
	FOREIGN KEY(room_id) REFERENCES rooms (id) ON DELETE RESTRICT, 
	FOREIGN KEY(rate_plan_id) REFERENCES rate_plans (id) ON DELETE SET NULL, 
	FOREIGN KEY(group_id) REFERENCES booking_groups (id) ON DELETE SET NULL
);

CREATE TABLE folios (
	id SERIAL NOT NULL, 
	organization_id INTEGER NOT NULL, 
	reservation_id INTEGER NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	is_master BOOLEAN NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(reservation_id) REFERENCES reservations (id) ON DELETE CASCADE
);

CREATE TABLE invoice_logs (
	id SERIAL NOT NULL, 
	organization_id INTEGER NOT NULL, 
	reservation_id INTEGER NOT NULL, 
	invoice_number VARCHAR(50) NOT NULL, 
	generated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	generated_by VARCHAR(100) NOT NULL, 
	pdf_path VARCHAR(255), 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(reservation_id) REFERENCES reservations (id) ON DELETE CASCADE
);

CREATE TABLE folio_items (
	id SERIAL NOT NULL, 
	organization_id INTEGER NOT NULL, 
	reservation_id INTEGER NOT NULL, 
	folio_id INTEGER, 
	date DATE NOT NULL, 
	description VARCHAR(255) NOT NULL, 
	category VARCHAR(50) NOT NULL, 
	amount NUMERIC(10, 2) NOT NULL, 
	subtotal NUMERIC(10, 2), 
	tax_total NUMERIC(10, 2) NOT NULL, 
	tax_breakdown TEXT, 
	version INTEGER NOT NULL, 
	is_demo BOOLEAN NOT NULL, 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(reservation_id) REFERENCES reservations (id) ON DELETE CASCADE, 
	FOREIGN KEY(folio_id) REFERENCES folios (id) ON DELETE CASCADE
);

CREATE TABLE payments (
	id SERIAL NOT NULL, 
	organization_id INTEGER NOT NULL, 
	reservation_id INTEGER NOT NULL, 
	folio_id INTEGER, 
	date DATE NOT NULL, 
	amount NUMERIC(10, 2) NOT NULL, 
	method VARCHAR(50) NOT NULL, 
	reference VARCHAR(100), 
	is_deposit BOOLEAN NOT NULL, 
	is_refund BOOLEAN NOT NULL, 
	stripe_payment_intent_id VARCHAR(100), 
	stripe_charge_id VARCHAR(100), 
	deleted_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT chk_payment_amount_nonzero CHECK (amount != 0), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(reservation_id) REFERENCES reservations (id) ON DELETE CASCADE, 
	FOREIGN KEY(folio_id) REFERENCES folios (id) ON DELETE SET NULL
);

ALTER TABLE organizations ADD CONSTRAINT fk_org_owner FOREIGN KEY (owner_user_id) REFERENCES users (id) ON DELETE SET NULL;