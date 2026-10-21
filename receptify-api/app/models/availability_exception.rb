class AvailabilityException < ApplicationRecord
  belongs_to :client_workspace

  validates :date, presence: true
  validates :start_time, :end_time,
            format: { with: /\A(?:[01]\d|2[0-3]):[0-5]\d\z/ },
            allow_blank: true
  validate :blocked_hours_are_valid

  private

  def blocked_hours_are_valid
    if all_day
      errors.add(:base, "All-day closures cannot include hours") if start_time.present? || end_time.present?
      return
    end

    errors.add(:start_time, "and end time are required for a partial-day block") if start_time.blank? || end_time.blank?
    if start_time.present? && end_time.present? && end_time <= start_time
      errors.add(:end_time, "must be after the start time")
    end
  end
end
