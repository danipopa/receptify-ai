class AddBillingToTenants < ActiveRecord::Migration[8.1]
  def change
    add_column :tenants, :paypal_subscription_id, :string
    add_column :tenants, :subscription_status, :string, default: "none", null: false
    add_column :tenants, :plan_expires_at, :datetime

    add_index :tenants, :paypal_subscription_id
  end
end
