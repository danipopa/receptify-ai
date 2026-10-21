class AvailabilityRule < ApplicationRecord
  belongs_to :client_workspace

  validates :day_of_week, inclusion: { in: 0..6 }
  validates :start_time, :end_time, format: { with: /\A(?:[01]\d|2[0-3]):[0-5]\d\z/ }
  validate :end_after_start
  validate :does_not_overlap_existing_rule

  private

  def end_after_start
    return if start_time.blank? || end_time.blank? || end_time > start_time

    errors.add(:end_time, "must be after the start time")
  end

  def does_not_overlap_existing_rule
    return if client_workspace.nil? || day_of_week.nil? || start_time.blank? || end_time.blank?

    overlap = client_workspace.availability_rules
                              .where(day_of_week: day_of_week)
                              .where.not(id: id)
                              .where("start_time < ? AND end_time > ?", end_time, start_time)
                              .exists?
    errors.add(:base, "Availability hours cannot overlap") if overlap
  end
end
