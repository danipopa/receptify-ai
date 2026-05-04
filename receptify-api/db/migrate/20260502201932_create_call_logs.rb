class CreateCallLogs < ActiveRecord::Migration[8.1]
  def change
    create_table :call_logs do |t|
      t.references :tenant, null: false, foreign_key: true
      t.references :did,    null: false, foreign_key: true
      t.string   :caller_number, null: false
      t.string   :direction,     null: false, default: "inbound"
      t.integer  :duration,      default: 0
      t.text     :transcript
      t.text     :summary
      t.datetime :started_at,    null: false
      t.datetime :ended_at

      t.timestamps
    end
    add_index :call_logs, :started_at
    add_index :call_logs, :caller_number
  end
end
