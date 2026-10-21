class Did < ApplicationRecord
  belongs_to :tenant
  belongs_to :client_workspace, optional: true
  has_many   :call_logs, dependent: :nullify

  PROVIDERS     = %w[twilio vonage signalwire bandwidth custom].freeze
  STATUSES      = %w[active inactive].freeze
  GATEWAY_TYPES = %w[none sip_trunk sip_registration].freeze

  validates :number,       presence: true, uniqueness: true
  validates :provider,     inclusion: { in: PROVIDERS }
  validates :status,       inclusion: { in: STATUSES }
  validates :gateway_type, inclusion: { in: GATEWAY_TYPES }

  validates :gateway_host, :gateway_user, :gateway_password,
            presence: true, if: -> { gateway_type == "sip_registration" }
  validates :gateway_host,
            presence: true, if: -> { gateway_type == "sip_trunk" }
  validate :client_workspace_belongs_to_tenant

  # Returns the FreeSWITCH gateway name derived from the DID number
  def fs_gateway_name
    "did-#{number.gsub(/\D/, '')}"
  end

  private

  def client_workspace_belongs_to_tenant
    return unless client_workspace && tenant
    return if client_workspace.tenant_id == tenant_id

    errors.add(:client_workspace, "must belong to the same account")
  end
end
