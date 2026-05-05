class AddGatewayToDids < ActiveRecord::Migration[8.1]
  def change
    add_column :dids, :gateway_type,     :string, default: "none", null: false
    add_column :dids, :gateway_host,     :string
    add_column :dids, :gateway_user,     :string
    add_column :dids, :gateway_password, :string
    add_column :dids, :gateway_realm,    :string
    add_column :dids, :gateway_port,     :integer, default: 5060
  end
end
