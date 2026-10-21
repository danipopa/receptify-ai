# This file is auto-generated from the current state of the database. Instead
# of editing this file, please use the migrations feature of Active Record to
# incrementally modify your database, and then regenerate this schema definition.
#
# This file is the source Rails uses to define your schema when running `bin/rails
# db:schema:load`. When creating a new database, `bin/rails db:schema:load` tends to
# be faster and is potentially less error prone than running all of your
# migrations from scratch. Old migrations may fail to apply correctly if those
# migrations use external dependencies or application code.
#
# It's strongly recommended that you check this file into your version control system.

ActiveRecord::Schema[8.1].define(version: 2026_10_19_000001) do
  # These are extensions that must be enabled in order to support this database
  enable_extension "pg_catalog.plpgsql"

  create_table "appointment_types", force: :cascade do |t|
    t.boolean "active", default: true, null: false
    t.bigint "client_workspace_id", null: false
    t.datetime "created_at", null: false
    t.integer "duration_minutes", null: false
    t.string "name", null: false
    t.datetime "updated_at", null: false
    t.index ["client_workspace_id"], name: "index_appointment_types_on_client_workspace_id"
  end

  create_table "appointments", force: :cascade do |t|
    t.bigint "appointment_type_id", null: false
    t.string "callback_number", null: false
    t.string "caller_name", null: false
    t.bigint "client_workspace_id", null: false
    t.datetime "created_at", null: false
    t.datetime "ends_at", null: false
    t.text "purpose"
    t.datetime "starts_at", null: false
    t.string "status", default: "confirmed", null: false
    t.datetime "updated_at", null: false
    t.index ["appointment_type_id"], name: "index_appointments_on_appointment_type_id"
    t.index ["client_workspace_id", "starts_at"], name: "index_appointments_on_client_workspace_id_and_starts_at"
    t.index ["client_workspace_id"], name: "index_appointments_on_client_workspace_id"
    t.index ["starts_at"], name: "index_appointments_on_starts_at"
  end

  create_table "availability_exceptions", force: :cascade do |t|
    t.boolean "all_day", default: true, null: false
    t.bigint "client_workspace_id", null: false
    t.datetime "created_at", null: false
    t.date "date", null: false
    t.string "description"
    t.string "end_time"
    t.string "start_time"
    t.datetime "updated_at", null: false
    t.index ["client_workspace_id", "date"], name: "index_availability_exceptions_on_client_workspace_id_and_date"
    t.index ["client_workspace_id"], name: "index_availability_exceptions_on_client_workspace_id"
  end

  create_table "availability_rules", force: :cascade do |t|
    t.bigint "client_workspace_id", null: false
    t.datetime "created_at", null: false
    t.integer "day_of_week", null: false
    t.string "end_time", null: false
    t.string "start_time", null: false
    t.datetime "updated_at", null: false
    t.index ["client_workspace_id", "day_of_week", "start_time", "end_time"], name: "index_availability_rules_on_workspace_and_hours", unique: true
    t.index ["client_workspace_id"], name: "index_availability_rules_on_client_workspace_id"
  end

  create_table "call_logs", force: :cascade do |t|
    t.string "caller_number", null: false
    t.datetime "created_at", null: false
    t.bigint "did_id", null: false
    t.string "direction", default: "inbound", null: false
    t.integer "duration", default: 0
    t.datetime "ended_at"
    t.datetime "started_at", null: false
    t.text "summary"
    t.bigint "tenant_id", null: false
    t.text "transcript"
    t.datetime "updated_at", null: false
    t.index ["caller_number"], name: "index_call_logs_on_caller_number"
    t.index ["did_id"], name: "index_call_logs_on_did_id"
    t.index ["started_at"], name: "index_call_logs_on_started_at"
    t.index ["tenant_id"], name: "index_call_logs_on_tenant_id"
  end

  create_table "client_workspaces", force: :cascade do |t|
    t.datetime "created_at", null: false
    t.text "knowledge_content", default: "", null: false
    t.string "knowledge_source"
    t.string "knowledge_status", default: "draft", null: false
    t.string "locale", default: "en-GB", null: false
    t.string "name", null: false
    t.bigint "tenant_id", null: false
    t.string "timezone", default: "UTC", null: false
    t.datetime "updated_at", null: false
    t.string "website_url"
    t.index ["tenant_id", "website_url"], name: "index_client_workspaces_on_tenant_id_and_website_url", unique: true
    t.index ["tenant_id"], name: "index_client_workspaces_on_tenant_id"
  end

  create_table "dids", force: :cascade do |t|
    t.bigint "client_workspace_id"
    t.datetime "created_at", null: false
    t.string "gateway_host"
    t.string "gateway_password"
    t.integer "gateway_port", default: 5060
    t.string "gateway_realm"
    t.string "gateway_type", default: "none", null: false
    t.string "gateway_user"
    t.string "number", null: false
    t.string "provider", default: "twilio", null: false
    t.string "status", default: "active", null: false
    t.bigint "tenant_id", null: false
    t.datetime "updated_at", null: false
    t.index ["client_workspace_id"], name: "index_dids_on_client_workspace_id"
    t.index ["number"], name: "index_dids_on_number", unique: true
    t.index ["status"], name: "index_dids_on_status"
    t.index ["tenant_id"], name: "index_dids_on_tenant_id"
  end

  create_table "mock_number_requests", force: :cascade do |t|
    t.bigint "client_workspace_id", null: false
    t.string "country_code", null: false
    t.string "country_name", null: false
    t.datetime "created_at", null: false
    t.string "locale", null: false
    t.string "number", null: false
    t.boolean "simulated", default: true, null: false
    t.datetime "updated_at", null: false
    t.index ["client_workspace_id"], name: "index_mock_number_requests_on_client_workspace_id"
    t.index ["number"], name: "index_mock_number_requests_on_number", unique: true
  end

  create_table "tenant_configs", force: :cascade do |t|
    t.datetime "created_at", null: false
    t.string "llm_model", default: "llama3.2:1b"
    t.integer "rag_chunk_words", default: 30
    t.integer "rag_top_k", default: 4
    t.bigint "tenant_id", null: false
    t.string "timezone", default: "America/New_York"
    t.datetime "updated_at", null: false
    t.string "voice", default: "en_US-lessac-medium"
    t.text "welcome_message", default: "Thank you for calling. How can I help you today?"
    t.index ["tenant_id"], name: "index_tenant_configs_on_tenant_id", unique: true
  end

  create_table "tenants", force: :cascade do |t|
    t.string "api_key", null: false
    t.datetime "created_at", null: false
    t.string "email", null: false
    t.string "name", null: false
    t.string "password_digest", default: "", null: false
    t.string "paypal_subscription_id"
    t.string "plan", default: "free", null: false
    t.datetime "plan_expires_at"
    t.boolean "platform_admin", default: false, null: false
    t.string "status", default: "active", null: false
    t.string "subdomain", null: false
    t.string "subscription_status", default: "none", null: false
    t.datetime "updated_at", null: false
    t.index ["api_key"], name: "index_tenants_on_api_key", unique: true
    t.index ["email"], name: "index_tenants_on_email", unique: true
    t.index ["paypal_subscription_id"], name: "index_tenants_on_paypal_subscription_id"
    t.index ["status"], name: "index_tenants_on_status"
    t.index ["subdomain"], name: "index_tenants_on_subdomain", unique: true
  end

  add_foreign_key "appointment_types", "client_workspaces"
  add_foreign_key "appointments", "appointment_types"
  add_foreign_key "appointments", "client_workspaces"
  add_foreign_key "availability_exceptions", "client_workspaces"
  add_foreign_key "availability_rules", "client_workspaces"
  add_foreign_key "call_logs", "dids"
  add_foreign_key "call_logs", "tenants"
  add_foreign_key "client_workspaces", "tenants"
  add_foreign_key "dids", "client_workspaces"
  add_foreign_key "dids", "tenants"
  add_foreign_key "mock_number_requests", "client_workspaces"
  add_foreign_key "tenant_configs", "tenants"
end
