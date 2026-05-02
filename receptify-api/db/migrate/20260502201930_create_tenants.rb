class CreateTenants < ActiveRecord::Migration[8.1]
  def change
    create_table :tenants do |t|
      t.string :name,      null: false
      t.string :subdomain, null: false
      t.string :email,     null: false
      t.string :plan,      null: false, default: "free"
      t.string :status,    null: false, default: "active"
      t.string :api_key,   null: false

      t.timestamps
    end
    add_index :tenants, :subdomain, unique: true
    add_index :tenants, :email,     unique: true
    add_index :tenants, :api_key,   unique: true
    add_index :tenants, :status
  end
end
