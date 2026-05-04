class CreateDids < ActiveRecord::Migration[8.1]
  def change
    create_table :dids do |t|
      t.references :tenant, null: false, foreign_key: true
      t.string :number,   null: false
      t.string :provider, null: false, default: "twilio"
      t.string :status,   null: false, default: "active"

      t.timestamps
    end
    add_index :dids, :number, unique: true
    add_index :dids, :status
  end
end
