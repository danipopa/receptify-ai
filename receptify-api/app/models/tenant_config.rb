class TenantConfig < ApplicationRecord
  belongs_to :tenant

  validates :llm_model,       presence: true
  validates :rag_chunk_words, numericality: { greater_than: 0 }
  validates :rag_top_k,       numericality: { greater_than: 0 }
end
