class CreateTenantConfigs < ActiveRecord::Migration[8.1]
  def change
    create_table :tenant_configs do |t|
      t.references :tenant, null: false, foreign_key: true, index: { unique: true }
      t.text    :welcome_message, default: "Thank you for calling. How can I help you today?"
      t.string  :llm_model,       default: "llama3.2:1b"
      t.integer :rag_chunk_words, default: 30
      t.integer :rag_top_k,       default: 4
      t.string  :voice,           default: "en_US-lessac-medium"
      t.string  :timezone,        default: "America/New_York"

      t.timestamps
    end
  end
end
