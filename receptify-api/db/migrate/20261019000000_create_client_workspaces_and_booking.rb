class CreateClientWorkspacesAndBooking < ActiveRecord::Migration[8.1]
  def change
    create_table :client_workspaces do |t|
      t.references :tenant, null: false, foreign_key: true
      t.string :name, null: false
      t.string :website_url
      t.string :timezone, null: false, default: "UTC"
      t.string :locale, null: false, default: "en-GB"
      t.text :knowledge_content, null: false, default: ""
      t.string :knowledge_source
      t.string :knowledge_status, null: false, default: "draft"
      t.timestamps
    end
    add_index :client_workspaces, %i[tenant_id website_url], unique: true

    create_table :mock_number_requests do |t|
      t.references :client_workspace, null: false, foreign_key: true
      t.string :country_code, null: false
      t.string :country_name, null: false
      t.string :locale, null: false
      t.string :number, null: false
      t.boolean :simulated, null: false, default: true
      t.timestamps
    end
    add_index :mock_number_requests, :number, unique: true

    create_table :appointment_types do |t|
      t.references :client_workspace, null: false, foreign_key: true
      t.string :name, null: false
      t.integer :duration_minutes, null: false
      t.boolean :active, null: false, default: true
      t.timestamps
    end

    create_table :availability_rules do |t|
      t.references :client_workspace, null: false, foreign_key: true
      t.integer :day_of_week, null: false
      t.string :start_time, null: false
      t.string :end_time, null: false
      t.timestamps
    end
    add_index :availability_rules,
              %i[client_workspace_id day_of_week start_time end_time],
              unique: true,
              name: "index_availability_rules_on_workspace_and_hours"

    create_table :availability_exceptions do |t|
      t.references :client_workspace, null: false, foreign_key: true
      t.date :date, null: false
      t.boolean :all_day, null: false, default: true
      t.string :start_time
      t.string :end_time
      t.string :description
      t.timestamps
    end
    add_index :availability_exceptions, %i[client_workspace_id date]

    create_table :appointments do |t|
      t.references :client_workspace, null: false, foreign_key: true
      t.references :appointment_type, null: false, foreign_key: true
      t.string :caller_name, null: false
      t.string :callback_number, null: false
      t.text :purpose
      t.datetime :starts_at, null: false
      t.datetime :ends_at, null: false
      t.string :status, null: false, default: "confirmed"
      t.timestamps
    end
    add_index :appointments, %i[client_workspace_id starts_at]
    add_index :appointments, :starts_at

    add_reference :dids, :client_workspace, foreign_key: true
  end
end
