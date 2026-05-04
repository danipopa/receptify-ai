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
