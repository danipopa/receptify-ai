class Appointment < ApplicationRecord
  belongs_to :client_workspace
  belongs_to :appointment_type

  STATUSES = %w[confirmed cancelled].freeze

  validates :caller_name, :callback_number, :starts_at, :ends_at, presence: true
  validates :status, inclusion: { in: STATUSES }
  validate :appointment_type_belongs_to_workspace
  validate :end_after_start

  private

  def appointment_type_belongs_to_workspace
    return unless appointment_type && client_workspace
    return if appointment_type.client_workspace_id == client_workspace_id

    errors.add(:appointment_type, "must belong to the client workspace")
  end

  def end_after_start
    return if starts_at.blank? || ends_at.blank? || ends_at > starts_at

    errors.add(:ends_at, "must be after the start time")
  end
end
