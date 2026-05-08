# This file should ensure the existence of records required to run the application in every environment (production,
# development, test). The code here should be idempotent so that it can be executed at any point in every environment.
# The data can then be loaded with the bin/rails db:seed command (or created alongside the database with db:setup).

tenant = Tenant.find_or_initialize_by(email: "admin@receptify.local")

if tenant.new_record?
  tenant.assign_attributes(
    name:                  "Demo Business",
    subdomain:             "demo",
    password:              "receptify123",
    password_confirmation: "receptify123",
    plan:                  "free",
    status:                "active"
  )
  tenant.save!
  puts "Seed tenant created:"
else
  puts "Seed tenant already exists:"
end

puts "  Email:    admin@receptify.local"
puts "  Password: receptify123"
puts "  API Key:  #{tenant.api_key}"

did = Did.find_or_initialize_by(number: "+17735414761")
did.assign_attributes(
  provider:         "twilio",
  status:           "active",
  tenant:           tenant,
  gateway_type:     "sip_registration",
  gateway_host:     "sip.callcentric.net",
  gateway_user:     "17778763557",
  gateway_password: ENV.fetch("SEED_DID_PASSWORD", "changeme"),
  gateway_realm:    "sip.callcentric.net",
  gateway_port:     5060
)
did.save!
puts "Seed DID: #{did.number} (#{did.gateway_type} via #{did.gateway_host})"
