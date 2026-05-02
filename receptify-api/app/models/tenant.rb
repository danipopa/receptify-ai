class Tenant < ApplicationRecord
  has_secure_password

  has_many :dids, dependent: :destroy
  has_many :call_logs, dependent: :destroy
  has_one  :tenant_config, dependent: :destroy

  before_create :generate_api_key
  after_create  :create_default_config

  PLANS   = %w[free starter pro enterprise].freeze
  STATUSES = %w[active inactive suspended].freeze

  validates :name,      presence: true
  validates :email,     presence: true, uniqueness: true,
                        format: { with: URI::MailTo::EMAIL_REGEXP }
  validates :subdomain, presence: true, uniqueness: true,
                        format: { with: /\A[a-z0-9\-]+\z/, message: "only lowercase letters, numbers, and hyphens" }
  validates :plan,   inclusion: { in: PLANS }
  validates :status, inclusion: { in: STATUSES }

  private

  def generate_api_key
    self.api_key = SecureRandom.hex(32)
  end

  def create_default_config
    create_tenant_config!
  end
end
