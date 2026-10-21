class AddPlatformAdminToTenants < ActiveRecord::Migration[8.1]
  def change
    add_column :tenants, :platform_admin, :boolean, default: false, null: false
  end
end
