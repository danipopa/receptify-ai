class ClientWorkspace < ApplicationRecord
  belongs_to :tenant
  has_many :dids, dependent: :nullify
  has_many :mock_number_requests, dependent: :destroy
  has_many :appointments, dependent: :destroy
  has_many :appointment_types, dependent: :destroy
  has_many :availability_rules, dependent: :destroy
  has_many :availability_exceptions, dependent: :destroy

  LOCALES = %w[en-GB en-US fr-FR it-IT es-ES ro-RO].freeze

  validates :name, presence: true
  validates :website_url, uniqueness: { scope: :tenant_id }, allow_blank: true
  validates :timezone, presence: true
  validates :locale, inclusion: { in: LOCALES }
  validates :knowledge_status, inclusion: { in: %w[draft ready] }
  validate :timezone_is_known

  private

  def timezone_is_known
    errors.add(:timezone, "is not a recognised time zone") unless ActiveSupport::TimeZone[timezone]
  end
end
