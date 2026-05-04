class CallLog < ApplicationRecord
  belongs_to :tenant
  belongs_to :did, optional: true

  DIRECTIONS = %w[inbound outbound].freeze

  validates :caller_number, presence: true
  validates :direction,     inclusion: { in: DIRECTIONS }
  validates :started_at,    presence: true

  scope :recent,   -> { order(started_at: :desc) }
  scope :inbound,  -> { where(direction: "inbound") }
  scope :outbound, -> { where(direction: "outbound") }
end
