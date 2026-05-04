class Did < ApplicationRecord
  belongs_to :tenant
  has_many   :call_logs, dependent: :nullify

  PROVIDERS = %w[twilio vonage signalwire bandwidth].freeze
  STATUSES  = %w[active inactive].freeze

  validates :number,   presence: true, uniqueness: true
  validates :provider, inclusion: { in: PROVIDERS }
  validates :status,   inclusion: { in: STATUSES }
end
